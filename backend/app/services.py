"""Use cases: glue between the parser, the brain and the database."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict

from sqlmodel import Session, select

from app.engine.categories import (
    CATEGORIES,
    NEEDS_REVIEW,
    SPENDING_CATEGORIES,
    category_kind,
)
from app.engine.classifier import StatementRow, classify_statement
from app.models import (
    CategoryTotal,
    LearnedRule,
    Statement,
    Summary,
    Totals,
    Transaction,
    utcnow,
)
from app.parsing.csv_parser import parse_statement

KIND_ORDER = {"spending": 0, "refund": 1, "income": 2, "not_spending": 3, "review": 4}


class NotFoundError(LookupError):
    pass


def learned_rules_map(session: Session) -> dict[str, str]:
    return {rule.merchant: rule.category for rule in session.exec(select(LearnedRule))}


def ingest_statement(session: Session, filename: str, content: bytes) -> Statement:
    """Parse + classify + store. Raises CSVParseError for unreadable files."""
    parsed = parse_statement(content)
    learned = learned_rules_map(session)
    rows = [
        StatementRow(t.date, t.description, t.amount, t.currency, t.row_number)
        for t in parsed.transactions
    ]
    results = classify_statement(rows, learned=learned)

    statement = Statement(
        filename=filename,
        row_count=len(rows),
        warnings_json=json.dumps(parsed.warnings),
    )
    session.add(statement)
    session.flush()

    applied: dict[str, int] = defaultdict(int)
    for raw, result in zip(parsed.transactions, results, strict=True):
        if result.source == "learned":
            applied[result.normalized_merchant] += 1
        session.add(
            Transaction(
                statement_id=statement.id,
                row_number=raw.row_number,
                date=raw.date,
                description=raw.description,
                normalized_merchant=result.normalized_merchant,
                amount=raw.amount,
                currency=raw.currency,
                category=result.category,
                confidence=result.confidence,
                reason=result.reason,
                needs_review=result.needs_review,
                is_duplicate=result.is_duplicate,
                source=result.source,
                notes_json=json.dumps([*raw.notes, *result.notes]),
            )
        )
    if applied:
        for rule in session.exec(select(LearnedRule).where(LearnedRule.merchant.in_(applied))):
            rule.times_applied += applied[rule.merchant]
            session.add(rule)
    session.commit()
    session.refresh(statement)
    return statement


def get_statement(session: Session, statement_id: int) -> Statement:
    statement = session.get(Statement, statement_id)
    if statement is None:
        raise NotFoundError(f"Statement {statement_id} not found")
    return statement


def statement_transactions(session: Session, statement_id: int) -> list[Transaction]:
    query = (
        select(Transaction)
        .where(Transaction.statement_id == statement_id)
        .order_by(Transaction.row_number, Transaction.id)
    )
    return list(session.exec(query))


def update_category(
    session: Session, transaction_id: int, category: str
) -> tuple[Transaction, LearnedRule | None, list[int]]:
    """Apply a user's fix and remember it for this merchant."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    txn = session.get(Transaction, transaction_id)
    if txn is None:
        raise NotFoundError(f"Transaction {transaction_id} not found")

    txn.category = category
    txn.source = "user"
    txn.is_duplicate = False
    if category == NEEDS_REVIEW:
        txn.needs_review, txn.confidence, txn.reason = True, 0.0, "Marked for review by you"
    else:
        txn.needs_review, txn.confidence, txn.reason = False, 1.0, "Set by you"
    session.add(txn)

    rule: LearnedRule | None = None
    also_updated: list[int] = []
    if category != NEEDS_REVIEW:
        merchant = txn.normalized_merchant
        rule = session.exec(select(LearnedRule).where(LearnedRule.merchant == merchant)).first()
        if rule is None:
            rule = LearnedRule(merchant=merchant, category=category)
        else:
            rule.category, rule.created_at = category, utcnow()
        session.add(rule)

        siblings = session.exec(
            select(Transaction).where(
                Transaction.statement_id == txn.statement_id,
                Transaction.normalized_merchant == merchant,
                Transaction.id != txn.id,
                Transaction.source != "user",
                Transaction.is_duplicate == False,  # noqa: E712 - SQL expression
            )
        )
        for other in siblings:
            other.category = category
            other.source = "learned"
            other.confidence = 1.0
            other.needs_review = False
            other.reason = f"You categorized '{merchant}' as {category}"
            session.add(other)
            also_updated.append(other.id)
        rule.times_applied += len(also_updated)

    session.commit()
    session.refresh(txn)
    if rule is not None:
        session.refresh(rule)
    return txn, rule, also_updated


def summarize(statement_id: int, transactions: list[Transaction]) -> Summary:
    by_category: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        by_category[txn.category].append(txn)

    def category_total(category: str, rows: list[Transaction]) -> float:
        # Money moved (transfers, card payments) and unreviewed rows are shown as volume;
        # real categories are netted so a refunded purchase lowers its own total.
        if category_kind(category) in ("not_spending", "review"):
            return round(sum(abs(t.amount) for t in rows), 2)
        return round(abs(sum(t.amount for t in rows)), 2)

    categories = [
        CategoryTotal(
            category=category,
            kind=category_kind(category),
            total=category_total(category, rows),
            count=len(rows),
        )
        for category, rows in by_category.items()
    ]
    categories.sort(key=lambda c: (KIND_ORDER[c.kind], -c.total, c.category))

    def signed_sum(names: tuple[str, ...] | list[str]) -> float:
        return sum(t.amount for name in names for t in by_category.get(name, []))

    spending = round(-signed_sum(SPENDING_CATEGORIES), 2)
    refunds = round(signed_sum(["Refund"]), 2)
    totals = Totals(
        transactions=len(transactions),
        auto_categorized=sum(1 for t in transactions if not t.needs_review),
        needs_review=sum(1 for t in transactions if t.needs_review),
        duplicates=sum(1 for t in transactions if t.is_duplicate),
        spending=spending,
        refunds=refunds,
        net_spending=round(spending - refunds, 2),
        income=round(signed_sum(["Income"]), 2),
        not_spending=round(sum(c.total for c in categories if c.kind == "not_spending"), 2),
    )
    return Summary(statement_id=statement_id, totals=totals, categories=categories)


EXPORT_COLUMNS = [
    "row_number",
    "date",
    "description",
    "merchant",
    "amount",
    "currency",
    "category",
    "confidence",
    "needs_review",
    "is_duplicate",
    "source",
    "reason",
    "notes",
]


def export_csv(transactions: list[Transaction]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for t in transactions:
        writer.writerow(
            [
                t.row_number,
                t.date.isoformat(),
                t.description,
                t.normalized_merchant,
                f"{t.amount:.2f}",
                t.currency,
                t.category,
                f"{t.confidence:.2f}",
                "yes" if t.needs_review else "no",
                "yes" if t.is_duplicate else "no",
                t.source,
                t.reason,
                "; ".join(t.notes),
            ]
        )
    return buffer.getvalue()
