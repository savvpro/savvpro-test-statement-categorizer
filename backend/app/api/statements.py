"""
Statements API – upload, list, recategorize.
"""

from __future__ import annotations

import hashlib
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.brain.normalize import (
    NormalizedRow,
    compute_fingerprint,
    normalize_description,
)
from app.brain.pipeline import BrainResult, UserRuleSpec, run_pipeline
from app.db import get_session
from app.models import AccountType, Statement, Transaction, TxnStatus, UserRule
from app.parsers.base import ParseError
from app.parsers.csv_parser import CsvParser
from app.parsers.pdf_parser import PdfParser
from app.schemas import (
    ColumnMapping,
    StatementOut,
    StatusCounts,
    UploadResult,
)

router = APIRouter(prefix="/statements", tags=["statements"])

_PARSERS = [CsvParser(), PdfParser()]


@router.post("", response_model=UploadResult)
def upload_statement(
    file: UploadFile = File(...),
    account_type: str = Form("credit_card"),
    column_mapping: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    """
    Upload a CSV or PDF statement.

    Parses, normalizes, categorizes, and persists all rows.
    Returns the statement and status counts.
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    # Find a parser
    parser = None
    for p in _PARSERS:
        if p.can_handle(file.filename, file.content_type):
            parser = p
            break
    if parser is None:
        raise HTTPException(400, f"Unsupported file type: {file.filename}")

    # Read file content
    content = file.file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate upload
    existing = session.exec(
        select(Statement).where(Statement.file_hash == file_hash)
    ).first()
    if existing:
        raise HTTPException(
            409,
            f"This file has already been uploaded as statement #{existing.id}"
        )

    # Parse
    try:
        col_map = None
        if column_mapping:
            col_map = json.loads(column_mapping)

        if isinstance(parser, CsvParser) and col_map:
            raw_rows = parser.parse(
                io.BytesIO(content),
                account_type=account_type,
                column_mapping=col_map,
            )
        else:
            raw_rows = parser.parse(io.BytesIO(content), account_type=account_type)
    except ParseError as exc:
        if exc.available_columns:
            raise HTTPException(422, detail={
                "message": str(exc),
                "available_columns": exc.available_columns,
                "required_fields": ["date", "description", "amount"],
            })
        raise HTTPException(400, str(exc))

    # Normalize
    normalized: list[NormalizedRow] = []
    for raw in raw_rows:
        merchant_key = normalize_description(raw.raw_description)
        fp = compute_fingerprint(raw.posted_date, raw.raw_description, raw.amount_cents)
        normalized.append(NormalizedRow(
            row_index=raw.row_index,
            posted_date=raw.posted_date,
            raw_description=raw.raw_description,
            merchant_key=merchant_key,
            amount_cents=raw.amount_cents,
            currency=raw.currency,
            fingerprint=fp,
        ))

    # Load user rules
    user_rules_db = session.exec(select(UserRule)).all()
    user_rules = [
        UserRuleSpec(
            id=r.id,
            match_type=r.match_type,
            pattern=r.pattern,
            category=r.category,
            min_cents=r.min_cents,
            max_cents=r.max_cents,
        )
        for r in user_rules_db
    ]

    # Run brain pipeline
    brain_results = run_pipeline(normalized, user_rules)

    # Detect period
    dates = [n.posted_date for n in normalized]
    period_start = min(dates) if dates else None
    period_end = max(dates) if dates else None

    # Create statement
    statement = Statement(
        filename=file.filename,
        account_type=AccountType(account_type),
        file_hash=file_hash,
        period_start=period_start,
        period_end=period_end,
        row_count=len(normalized),
    )
    session.add(statement)
    session.flush()  # get the ID

    # Create transactions
    result_map = {br.row_index: br for br in brain_results}

    for norm in normalized:
        br = result_map.get(norm.row_index)
        if not br:
            continue

        # Check for duplicate fingerprint in DB
        dup = session.exec(
            select(Transaction).where(Transaction.fingerprint == norm.fingerprint)
        ).first()
        flags = list(br.flags)
        if dup:
            flags.append("possible_duplicate")

        txn = Transaction(
            statement_id=statement.id,
            row_index=norm.row_index,
            posted_date=norm.posted_date,
            raw_description=norm.raw_description,
            merchant_key=norm.merchant_key,
            amount_cents=norm.amount_cents,
            currency=norm.currency,
            category=br.category,
            confidence=br.confidence,
            status=TxnStatus(br.status),
            reason=br.reason,
            rule_id=br.rule_id,
            flags_json=json.dumps(flags),
            deductible_pct=br.deductible_pct,
            fingerprint=norm.fingerprint,
        )
        session.add(txn)

    # Update rule hit counts
    for br in brain_results:
        if br.rule_id:
            rule = session.get(UserRule, br.rule_id)
            if rule:
                rule.hit_count += 1

    session.commit()
    session.refresh(statement)

    # Compute status counts
    counts = _compute_status_counts(session, statement.id)

    return UploadResult(
        statement=StatementOut.model_validate(statement),
        counts=counts,
    )


@router.get("", response_model=list[StatementOut])
def list_statements(session: Session = Depends(get_session)):
    """List all uploaded statements, most recent first."""
    stmts = session.exec(
        select(Statement).order_by(Statement.uploaded_at.desc())
    ).all()
    return [StatementOut.model_validate(s) for s in stmts]


@router.get("/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: int, session: Session = Depends(get_session)):
    """Get a single statement by ID."""
    stmt = session.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(404, "Statement not found")
    return StatementOut.model_validate(stmt)


@router.post("/{statement_id}/recategorize", response_model=StatusCounts)
def recategorize_statement(
    statement_id: int,
    session: Session = Depends(get_session),
):
    """Re-run the brain pipeline on all rows (e.g., after adding new rules)."""
    stmt = session.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(404, "Statement not found")

    txns = session.exec(
        select(Transaction)
        .where(Transaction.statement_id == statement_id)
        .order_by(Transaction.row_index)
    ).all()

    # Don't re-categorize user-confirmed rows
    rows_to_recat = []
    confirmed_ids = set()
    for t in txns:
        if t.status == TxnStatus.USER_CONFIRMED:
            confirmed_ids.add(t.id)
        else:
            rows_to_recat.append(t)

    if not rows_to_recat:
        return _compute_status_counts(session, statement_id)

    # Build normalized rows
    normalized = [
        NormalizedRow(
            row_index=t.row_index,
            posted_date=t.posted_date,
            raw_description=t.raw_description,
            merchant_key=t.merchant_key,
            amount_cents=t.amount_cents,
            currency=t.currency,
            fingerprint=t.fingerprint,
        )
        for t in rows_to_recat
    ]

    # Load user rules
    user_rules_db = session.exec(select(UserRule)).all()
    user_rules = [
        UserRuleSpec(
            id=r.id,
            match_type=r.match_type,
            pattern=r.pattern,
            category=r.category,
            min_cents=r.min_cents,
            max_cents=r.max_cents,
        )
        for r in user_rules_db
    ]

    results = run_pipeline(normalized, user_rules)
    result_map = {br.row_index: br for br in results}

    for t in rows_to_recat:
        br = result_map.get(t.row_index)
        if not br:
            continue
        t.category = br.category
        t.confidence = br.confidence
        t.status = TxnStatus(br.status)
        t.reason = br.reason
        t.rule_id = br.rule_id
        t.flags = br.flags
        t.deductible_pct = br.deductible_pct

    session.commit()
    return _compute_status_counts(session, statement_id)


@router.delete("/{statement_id}")
def delete_statement(statement_id: int, session: Session = Depends(get_session)):
    """Delete a statement and all its transactions."""
    stmt = session.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(404, "Statement not found")

    txns = session.exec(
        select(Transaction).where(Transaction.statement_id == statement_id)
    ).all()
    for t in txns:
        session.delete(t)
    session.delete(stmt)
    session.commit()
    return {"ok": True}


def _compute_status_counts(session: Session, statement_id: int) -> StatusCounts:
    """Count transactions by status for a statement."""
    txns = session.exec(
        select(Transaction).where(Transaction.statement_id == statement_id)
    ).all()

    from app.brain.categories import EXCLUDED_KEYS

    counts = StatusCounts(total=len(txns))
    for t in txns:
        if t.category in EXCLUDED_KEYS:
            counts.excluded += 1
        elif t.status in (TxnStatus.AUTO, TxnStatus.USER_CONFIRMED):
            counts.auto += 1
        elif t.status == TxnStatus.SUGGESTED:
            counts.suggested += 1
        elif t.status == TxnStatus.NEEDS_REVIEW:
            counts.needs_review += 1
    return counts
