from datetime import UTC, datetime
from pathlib import PureWindowsPath

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.brain.classifier import classify
from app.brain.models import Decision, UserRule
from app.brain.normalizer import normalize
from app.brain.postcheck import postcheck
from app.core.money import from_minor, to_minor
from app.ingest.formats import PROFILES_BY_NAME
from app.ingest.models import ParsedRow
from app.ingest.parser import parse
from app.models import ParseErrorRow, Statement, Transaction, UserRuleRow
from app.schemas import ParseErrorOut, StatementDetail, StatementOut, TransactionOut
from app.services.errors import NotFoundError


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # stored as naive UTC


def load_user_rules(db: Session) -> list[UserRule]:
    return [
        UserRule(merchant_key=r.merchant_key, category=r.category, kind=r.kind)
        for r in db.scalars(select(UserRuleRow))
    ]


def to_parsed_row(t: Transaction, account_type: str) -> ParsedRow:
    return ParsedRow(
        row_number=t.row_number,
        date=t.date,
        raw_description=t.raw_description,
        amount=from_minor(t.amount_minor),
        currency=t.currency,
        account_type=account_type,  # type: ignore[arg-type]
    )


def apply_decision(t: Transaction, d: Decision) -> None:
    t.category = d.category
    t.kind = d.kind
    t.confidence = d.confidence
    t.rule_id = d.rule_id
    t.reason = d.reason
    t.needs_review = d.needs_review
    t.suggested_category = d.suggested_category


def ingest_statement(db: Session, filename: str, content: bytes) -> Statement:
    """Parse, classify (with the user's saved rules), post-check and save one upload.

    Raises IngestError (from the parser) when the file cannot be read at all.
    """
    result = parse(content)
    profile = PROFILES_BY_NAME[result.profile_name]
    user_rules = load_user_rules(db)
    decisions = postcheck(result.rows, [classify(row, user_rules) for row in result.rows])

    name = PureWindowsPath(filename.replace("/", "\\")).name or "statement.csv"
    statement = Statement(
        filename=name[:255],
        profile_name=profile.name,
        account_type=profile.account_type,
        uploaded_at=utcnow(),
        skipped_count=len(result.skipped),
    )
    db.add(statement)
    db.flush()

    for row, decision in zip(result.rows, decisions, strict=True):
        transaction = Transaction(
            statement_id=statement.id,
            row_number=row.row_number,
            date=row.date,
            raw_description=row.raw_description,
            merchant_key=normalize(row.raw_description).merchant_key,
            amount_minor=to_minor(row.amount),
            currency=row.currency,
            edited_by_user=False,
            category=decision.category,
            kind=decision.kind,
            confidence=decision.confidence,
            rule_id=decision.rule_id,
            reason=decision.reason,
            needs_review=decision.needs_review,
            suggested_category=decision.suggested_category,
        )
        db.add(transaction)
    for error in result.errors:
        db.add(
            ParseErrorRow(
                statement_id=statement.id,
                row_number=error.row_number,
                raw_line=error.raw_line,
                reason=error.reason,
            )
        )
    db.commit()
    return statement


def _counts(db: Session, statement_ids: list[int]) -> dict[int, tuple[int, int, int]]:
    rows = dict.fromkeys(statement_ids, (0, 0, 0))
    review = func.sum(case((Transaction.needs_review, 1), else_=0))
    for sid, total, reviewing in db.execute(
        select(Transaction.statement_id, func.count(), review)
        .where(Transaction.statement_id.in_(statement_ids))
        .group_by(Transaction.statement_id)
    ):
        rows[sid] = (total, 0, int(reviewing or 0))
    for sid, errors in db.execute(
        select(ParseErrorRow.statement_id, func.count())
        .where(ParseErrorRow.statement_id.in_(statement_ids))
        .group_by(ParseErrorRow.statement_id)
    ):
        total, _, reviewing = rows[sid]
        rows[sid] = (total, errors, reviewing)
    return rows


def list_statements(db: Session) -> list[StatementOut]:
    statements = list(db.scalars(select(Statement).order_by(Statement.id.desc())))
    counts = _counts(db, [s.id for s in statements])
    return [StatementOut.from_row(s, *counts[s.id]) for s in statements]


def get_statement(db: Session, statement_id: int) -> Statement:
    statement = db.get(Statement, statement_id)
    if statement is None:
        raise NotFoundError(f"Statement {statement_id} not found")
    return statement


def statement_detail(db: Session, statement_id: int) -> StatementDetail:
    statement = get_statement(db, statement_id)
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.statement_id == statement_id)
            .order_by(Transaction.row_number)
        )
    )
    errors = list(
        db.scalars(
            select(ParseErrorRow)
            .where(ParseErrorRow.statement_id == statement_id)
            .order_by(ParseErrorRow.row_number)
        )
    )
    summary = StatementOut.from_row(
        statement,
        row_count=len(transactions),
        parse_error_count=len(errors),
        needs_review_count=sum(t.needs_review for t in transactions),
    )
    return StatementDetail(
        **summary.model_dump(),
        transactions=[TransactionOut.from_row(t) for t in transactions],
        parse_errors=[ParseErrorOut.from_row(e) for e in errors],
    )
