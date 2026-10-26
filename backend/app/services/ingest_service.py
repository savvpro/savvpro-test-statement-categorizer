"""Upload -> parse -> categorize -> persist."""

import dataclasses
import hashlib
import logging
import time
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.brain.engine import categorize
from app.brain.models import AccountType, ParsedRow, TxnStatus
from app.db.models import Statement, Transaction
from app.db.money import to_cents
from app.parsing import ParseError, parse_statement
from app.services.categorization import apply_decision, count_rule_hits, learned_rules
from app.services.errors import DuplicateStatement, InvalidUpload, UploadTooLarge

logger = logging.getLogger(__name__)
ALLOWED_SUFFIXES = {".csv", ".xlsx"}


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def dedupe_hash(row: ParsedRow, merchant_key: str) -> str:
    """Same date + amount + merchant: the identity used to spot a row seen before."""
    text = f"{row.date.isoformat()}|{to_cents(row.amount)}|{merchant_key}"
    return hashlib.sha256(text.encode()).hexdigest()


def validate_upload(filename: str, content: bytes, max_bytes: int) -> None:
    if PurePath(filename).suffix.lower() not in ALLOWED_SUFFIXES:
        raise InvalidUpload("only .csv and .xlsx files are supported")
    if len(content) > max_bytes:
        raise UploadTooLarge(f"file is larger than {max_bytes // (1024 * 1024)} MB")


def ingest(
    db: Session,
    filename: str,
    content: bytes,
    account_type: AccountType,
    charges_positive: bool | None,
    max_bytes: int,
) -> Statement:
    started = time.perf_counter()
    validate_upload(filename, content, max_bytes)

    digest = file_hash(content)
    existing = db.scalar(select(Statement.id).where(Statement.file_hash == digest))
    if existing is not None:
        raise DuplicateStatement(existing)

    try:
        result = parse_statement(content, filename, account_type, charges_positive)
    except ParseError as exc:
        raise InvalidUpload(f"could not read {filename}: {exc}") from exc
    if not result.rows:
        raise InvalidUpload(f"{filename}: no transactions found ({len(result.errors)} bad rows)")

    decisions = categorize(result.rows, account_type, learned_rules(db))
    statement = Statement(
        filename=PurePath(filename).name,
        account_type=account_type,
        row_count=len(result.rows),
        parse_errors=[dataclasses.asdict(error) for error in result.errors],
        warnings=list(result.warnings),
        detected_format=dataclasses.asdict(result.detected),
        file_hash=digest,
    )
    by_row: dict[int, Transaction] = {}
    for row, decision in zip(result.rows, decisions, strict=True):
        txn = Transaction(
            row_index=row.row_index,
            date=row.date,
            description_raw=row.description,
            amount=row.amount,
            is_pending=row.is_pending,
            dedupe_hash=dedupe_hash(row, decision.merchant_key),
        )
        by_row[row.row_index] = txn
        statement.transactions.append(txn)
    for row, decision in zip(result.rows, decisions, strict=True):
        apply_decision(by_row[row.row_index], decision, by_row)
    count_rule_hits(db, decisions)

    db.add(statement)
    try:
        db.commit()
    except IntegrityError:  # a concurrent upload of the same file won the race
        db.rollback()
        existing = db.scalar(select(Statement.id).where(Statement.file_hash == digest))
        if existing is None:
            raise
        raise DuplicateStatement(existing) from None

    review = sum(d.status is TxnStatus.needs_review for d in decisions)
    logger.info(
        "statement uploaded",
        extra={
            "statement_id": statement.id,
            "upload_filename": statement.filename,
            "rows": len(result.rows),
            "row_errors": len(result.errors),
            "review_count": review,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    )
    return statement
