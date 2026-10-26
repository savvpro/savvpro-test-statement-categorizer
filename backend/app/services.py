"""Application services: import, review, learning and reporting."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from .brain import Categorizer, Decision, Flag, TransactionInput
from .brain import categories as cats
from .brain.categories import Kind
from .db import Database
from .ingest.reader import ParsedStatement, SignConvention, SkippedRow, read_statement
from .schemas import (
    CategoryTotal,
    RuleOut,
    SkippedRowOut,
    StatementListItem,
    StatementOut,
    Summary,
    TransactionOut,
)

# Flags raised by statement-level checks; they survive re-categorisation.
_STATEMENT_FLAGS = {
    Flag.POSSIBLE_DUPLICATE: (
        "Same date, amount and description as an earlier row - possible duplicate."
    ),
    Flag.ALREADY_IMPORTED: "This exact transaction was already imported from another statement.",
}


class NotFoundError(LookupError):
    pass


class InvalidInputError(ValueError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _status(decision: Decision) -> str:
    return "needs_review" if decision.needs_review else "auto"


class StatementService:
    def __init__(self, db: Database, *, threshold: float = 0.75) -> None:
        self.db = db
        self.threshold = threshold

    # ------------------------------------------------------------------ rules
    def _user_rules(self, conn: sqlite3.Connection) -> dict[tuple[str, str], str]:
        rows = conn.execute("SELECT merchant_key, direction, category FROM user_rules")
        return {(r["merchant_key"], r["direction"]): r["category"] for r in rows}

    def _categorizer(self, conn: sqlite3.Connection) -> Categorizer:
        return Categorizer(self._user_rules(conn), threshold=self.threshold)

    def list_rules(self) -> list[RuleOut]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM user_rules ORDER BY updated_at DESC").fetchall()
        return [RuleOut(**dict(r)) for r in rows]

    def delete_rule(self, merchant_key: str, direction: str) -> None:
        with self.db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM user_rules WHERE merchant_key = ? AND direction = ?",
                (merchant_key, direction),
            )
            if cur.rowcount == 0:
                raise NotFoundError("Rule not found.")

    # ----------------------------------------------------------------- import
    def import_statement(
        self,
        filename: str,
        data: bytes,
        sign_convention: SignConvention = SignConvention.AUTO,
    ) -> int:
        parsed = read_statement(data, sign_convention=sign_convention)
        with self.db.connect() as conn:
            categorizer = self._categorizer(conn)
            statement_id = self._insert_statement(conn, filename, parsed)
            seen: dict[tuple, int] = {}
            for tx in parsed.transactions:
                decision = categorizer.categorize(
                    TransactionInput(tx.description, tx.amount, tx.bank_category)
                )
                fingerprint = (
                    tx.date.isoformat(),
                    _cents(tx.amount),
                    tx.description.strip().upper(),
                )
                if fingerprint in seen:
                    decision.send_to_review(
                        f"Same date, amount and description as line {seen[fingerprint]} "
                        "- possible duplicate.",
                        cap=0.5,
                        flag=Flag.POSSIBLE_DUPLICATE,
                    )
                else:
                    seen[fingerprint] = tx.line
                    if self._imported_elsewhere(conn, statement_id, fingerprint):
                        decision.send_to_review(
                            _STATEMENT_FLAGS[Flag.ALREADY_IMPORTED],
                            cap=0.5,
                            flag=Flag.ALREADY_IMPORTED,
                        )
                conn.execute(
                    """INSERT INTO transactions (statement_id, line, date, description, merchant,
                       merchant_key, amount_cents, direction, bank_category, category, status,
                       confidence, source, reasons, suggestions, flags, engine_category)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        statement_id,
                        tx.line,
                        tx.date.isoformat(),
                        tx.description,
                        decision.merchant,
                        decision.merchant_key,
                        _cents(tx.amount),
                        "in" if tx.amount > 0 else "out",
                        tx.bank_category,
                        decision.category,
                        _status(decision),
                        decision.confidence,
                        decision.source.value,
                        json.dumps(decision.reasons),
                        json.dumps(decision.suggestions),
                        json.dumps([f.value for f in decision.flags]),
                        decision.category,
                    ),
                )
        return statement_id

    @staticmethod
    def _insert_statement(conn: sqlite3.Connection, filename: str, parsed: ParsedStatement) -> int:
        cur = conn.execute(
            """INSERT INTO statements (filename, uploaded_at, file_format, sign_convention,
               warnings, skipped) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                filename,
                _now(),
                parsed.file_format,
                parsed.sign_convention.value,
                json.dumps(parsed.warnings),
                json.dumps([_skipped(s) for s in parsed.skipped]),
            ),
        )
        return int(cur.lastrowid)

    @staticmethod
    def _imported_elsewhere(
        conn: sqlite3.Connection, statement_id: int, fingerprint: tuple
    ) -> bool:
        date, cents, description = fingerprint
        row = conn.execute(
            """SELECT 1 FROM transactions WHERE date = ? AND amount_cents = ?
               AND UPPER(TRIM(description)) = ? AND statement_id != ? LIMIT 1""",
            (date, cents, description, statement_id),
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------ read
    def list_statements(self) -> list[StatementListItem]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT s.id, s.filename, s.uploaded_at,
                          COUNT(t.id) AS transaction_count,
                          SUM(CASE WHEN t.status = 'needs_review' THEN 1 ELSE 0 END)
                              AS needs_review_count,
                          MIN(t.date) AS period_start, MAX(t.date) AS period_end
                   FROM statements s LEFT JOIN transactions t ON t.statement_id = s.id
                   GROUP BY s.id ORDER BY s.id DESC"""
            ).fetchall()
        return [
            StatementListItem(**{**dict(r), "needs_review_count": r["needs_review_count"] or 0})
            for r in rows
        ]

    def get_statement(self, statement_id: int) -> StatementOut:
        with self.db.connect() as conn:
            return self._load(conn, statement_id)

    def _load(self, conn: sqlite3.Connection, statement_id: int) -> StatementOut:
        st = conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
        if st is None:
            raise NotFoundError(f"Statement {statement_id} not found.")
        rows = conn.execute(
            "SELECT * FROM transactions WHERE statement_id = ? ORDER BY date, line", (statement_id,)
        ).fetchall()
        transactions = [_tx_out(r) for r in rows]
        dates = [t.date for t in transactions]
        return StatementOut(
            id=st["id"],
            filename=st["filename"],
            uploaded_at=st["uploaded_at"],
            file_format=st["file_format"],
            sign_convention=st["sign_convention"],
            warnings=json.loads(st["warnings"]),
            skipped=[SkippedRowOut(**s) for s in json.loads(st["skipped"])],
            transactions=transactions,
            transaction_count=len(transactions),
            needs_review_count=sum(1 for t in transactions if t.status == "needs_review"),
            period_start=min(dates) if dates else None,
            period_end=max(dates) if dates else None,
            summary=summarize(transactions),
        )

    def delete_statement(self, statement_id: int) -> None:
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,))
            if cur.rowcount == 0:
                raise NotFoundError(f"Statement {statement_id} not found.")

    # ---------------------------------------------------------------- review
    def update_transaction(
        self, statement_id: int, tx_id: int, category: str | None, remember: bool
    ) -> StatementOut:
        if category is not None and not cats.is_valid(category):
            raise InvalidInputError(f"Unknown category '{category}'.")
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE id = ? AND statement_id = ?",
                (tx_id, statement_id),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"Transaction {tx_id} not found in statement {statement_id}.")

            reasons = [r for r in json.loads(row["reasons"]) if not r.startswith("Set by you")]
            if category is None:
                conn.execute(
                    "UPDATE transactions SET category = NULL, status = 'needs_review', "
                    "confidence = 0, source = 'user', reasons = ? WHERE id = ?",
                    (json.dumps(["Sent back to review by you.", *reasons]), tx_id),
                )
                return self._load(conn, statement_id)

            conn.execute(
                "UPDATE transactions SET category = ?, status = 'reviewed', confidence = 1.0, "
                "source = 'user', reasons = ? WHERE id = ?",
                (
                    category,
                    json.dumps([f"Set by you: {cats.get(category).label}.", *reasons]),
                    tx_id,
                ),
            )
            if remember:
                conn.execute(
                    """INSERT INTO user_rules
                           (merchant_key, direction, category, example, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(merchant_key, direction)
                       DO UPDATE SET category = excluded.category, example = excluded.example,
                                     updated_at = excluded.updated_at""",
                    (row["merchant_key"], row["direction"], category, row["description"], _now()),
                )
                self._reapply(conn, statement_id, row["merchant_key"], row["direction"], tx_id)
            return self._load(conn, statement_id)

    def _reapply(
        self, conn: sqlite3.Connection, statement_id: int, key: str, direction: str, skip_id: int
    ) -> None:
        """Re-run the brain on the same merchant's rows the user has not touched yet."""
        categorizer = self._categorizer(conn)
        rows = conn.execute(
            """SELECT * FROM transactions WHERE statement_id = ? AND merchant_key = ?
               AND direction = ? AND status != 'reviewed' AND id != ?""",
            (statement_id, key, direction, skip_id),
        ).fetchall()
        for r in rows:
            decision = categorizer.categorize(
                TransactionInput(
                    r["description"], Decimal(r["amount_cents"]) / 100, r["bank_category"]
                )
            )
            for flag in json.loads(r["flags"]):
                if flag in _STATEMENT_FLAGS:
                    decision.send_to_review(_STATEMENT_FLAGS[Flag(flag)], cap=0.5, flag=Flag(flag))
            conn.execute(
                """UPDATE transactions SET category = ?, status = ?, confidence = ?, source = ?,
                   reasons = ?, suggestions = ?, flags = ? WHERE id = ?""",
                (
                    decision.category,
                    _status(decision),
                    decision.confidence,
                    decision.source.value,
                    json.dumps(decision.reasons),
                    json.dumps(decision.suggestions),
                    json.dumps([f.value for f in decision.flags]),
                    r["id"],
                ),
            )

    # --------------------------------------------------------------- export
    def export_csv(self, statement_id: int) -> str:
        statement = self.get_statement(statement_id)
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(
            [
                "Date",
                "Description",
                "Merchant",
                "Amount",
                "Category",
                "Schedule C line",
                "Status",
                "Confidence",
                "Refund",
                "Notes",
            ]
        )
        for t in statement.transactions:
            category = cats.get(t.category) if t.category else None
            writer.writerow(
                [
                    t.date,
                    _csv_safe(t.description),
                    _csv_safe(t.merchant),
                    f"{t.amount_cents / 100:.2f}",
                    category.label if category else "NEEDS REVIEW",
                    (category.schedule_c_line or "") if category else "",
                    t.status,
                    f"{t.confidence:.2f}",
                    "yes" if Flag.REFUND.value in t.flags else "",
                    _csv_safe(" ".join(t.reasons)),
                ]
            )
        writer.writerow([])
        writer.writerow(["Summary"])
        s = statement.summary
        for label, cents in (
            ("Gig income", s.income_cents),
            ("Deductible expenses", s.deductible_expenses_cents),
            ("Estimated net profit", s.net_profit_cents),
            ("Personal (excluded)", s.personal_cents),
        ):
            writer.writerow([label, "", "", f"{cents / 100:.2f}"])
        for c in s.categories:
            writer.writerow(
                [c.label, "", "", f"{c.total_cents / 100:.2f}", "", c.schedule_c_line or ""]
            )
        if s.needs_review_count:
            writer.writerow([f"{s.needs_review_count} transaction(s) still need review"])
        return buf.getvalue()


def _skipped(s: SkippedRow) -> dict:
    return {"line": s.line, "reason": s.reason, "content": s.content}


def _csv_safe(value: str) -> str:
    """Stop spreadsheet apps from executing cells that start with a formula character."""
    return f"'{value}" if value and value[0] in "=+-@\t\r" else value


def _tx_out(r: sqlite3.Row) -> TransactionOut:
    return TransactionOut(
        id=r["id"],
        line=r["line"],
        date=r["date"],
        description=r["description"],
        merchant=r["merchant"],
        amount_cents=r["amount_cents"],
        direction=r["direction"],
        bank_category=r["bank_category"],
        category=r["category"],
        status=r["status"],
        confidence=r["confidence"],
        source=r["source"],
        reasons=json.loads(r["reasons"]),
        suggestions=json.loads(r["suggestions"]),
        flags=json.loads(r["flags"]),
        engine_category=r["engine_category"],
    )


def summarize(transactions: list[TransactionOut]) -> Summary:
    """Totals per category. Rows still in review are left out of every total."""
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    refunds: dict[str, int] = defaultdict(int)
    transfers_in = transfers_out = 0
    review_count = review_cents = auto = reviewed = 0

    for t in transactions:
        if t.status == "needs_review" or not t.category:
            review_count += 1
            review_cents += abs(t.amount_cents)
            continue
        auto += t.status == "auto"
        reviewed += t.status == "reviewed"
        kind = cats.get(t.category).kind
        counts[t.category] += 1
        if kind is Kind.INCOME:
            totals[t.category] += t.amount_cents
        elif kind is Kind.TRANSFER:
            if t.amount_cents > 0:
                transfers_in += t.amount_cents
            else:
                transfers_out -= t.amount_cents
        else:  # expense or personal: spending is positive, refunds reduce it
            totals[t.category] -= t.amount_cents
            if t.amount_cents > 0:
                refunds[t.category] += t.amount_cents

    category_totals = [
        CategoryTotal(
            category=c.id,
            label=c.label,
            kind=c.kind.value,
            schedule_c_line=c.schedule_c_line,
            total_cents=totals[c.id],
            count=counts[c.id],
            refund_cents=refunds[c.id],
        )
        for c in cats.CATEGORIES
        if counts[c.id] and c.kind is not Kind.TRANSFER
    ]
    income = sum(t.total_cents for t in category_totals if t.kind == Kind.INCOME)
    expenses = sum(t.total_cents for t in category_totals if t.kind == Kind.EXPENSE)
    personal = sum(t.total_cents for t in category_totals if t.kind == Kind.PERSONAL)
    return Summary(
        income_cents=income,
        deductible_expenses_cents=expenses,
        net_profit_cents=income - expenses,
        personal_cents=personal,
        transfers_in_cents=transfers_in,
        transfers_out_cents=transfers_out,
        needs_review_count=review_count,
        needs_review_cents=review_cents,
        auto_count=auto,
        reviewed_count=reviewed,
        categories=category_totals,
    )
