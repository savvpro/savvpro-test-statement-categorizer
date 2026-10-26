"""Import service – orchestrates file ingestion, categorization, and DB persistence."""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brain import BrainContext, RawTransaction, categorize
from app.core.config import settings
from app.ingest.csv_reader import parse_csv
from app.ingest.sniff import sniff
from app.models.import_draft import ImportDraft
from app.models.statement import Statement
from app.models.transaction import Transaction


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fingerprint(account_id: str, posted_date: object, amount_cents: int,
                 merchant: str, occurrence: int) -> str:
    raw = f"{account_id}|{posted_date}|{amount_cents}|{merchant}|{occurrence}"
    return hashlib.md5(raw.encode()).hexdigest()


async def create_draft(
    db: AsyncSession,
    file_data: bytes,
    filename: str,
) -> dict[str, Any]:
    """Step 1: sniff, parse preview, return draft id + mapping + preview rows."""
    if len(file_data) > settings.max_upload_bytes:
        raise ValueError(f"File exceeds {settings.max_upload_bytes // 1024 // 1024} MB limit")

    sha = _sha256(file_data)

    # Check if already imported
    existing = await db.scalar(select(Statement).where(Statement.file_sha256 == sha))
    if existing:
        raise ValueError(f"DUPLICATE_FILE:{existing.id}")

    sniff_result = sniff(file_data, filename)

    if sniff_result.fmt == "csv":
        parsed = parse_csv(
            file_data,
            sniff_result.encoding,
            sniff_result.delimiter or ",",
        )
        preview_rows = parsed.rows[:10]
        mapping_display = dict(parsed.column_mapping)
        warnings = parsed.warnings
    else:
        # OFX: minimal preview
        preview_rows = []
        mapping_display = {}
        warnings = []

    draft = ImportDraft(
        id=str(uuid.uuid4()),
        filename=filename,
        file_sha256=sha,
        file_data=base64.b64encode(file_data).decode(),
        detected_mapping=json.dumps(mapping_display),
        preview_rows=json.dumps(
            [
                {
                    **r,
                    "posted_date": r["posted_date"].isoformat() if hasattr(r.get("posted_date"), "isoformat") else str(r.get("posted_date", "")),
                }
                for r in preview_rows
            ],
            default=str,
        ),
        warnings=json.dumps(warnings),
        fmt=sniff_result.fmt,
        encoding=sniff_result.encoding,
        delimiter=sniff_result.delimiter or ",",
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.import_draft_ttl_minutes),
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return {
        "draft_id": draft.id,
        "filename": filename,
        "fmt": sniff_result.fmt,
        "detected_mapping": mapping_display,
        "preview_rows": json.loads(draft.preview_rows),
        "warnings": warnings,
    }


async def commit_draft(
    db: AsyncSession,
    draft_id: str,
    account_id: str,
    *,
    invert_sign: bool | None = None,
    prefer_mdy: bool = True,
) -> dict[str, Any]:
    """Step 2: parse full file, categorize, persist Statement + Transactions."""
    draft = await db.get(ImportDraft, draft_id)
    if not draft:
        raise ValueError("Draft not found or expired")

    expires_at_aware = draft.expires_at.replace(tzinfo=UTC) if draft.expires_at.tzinfo is None else draft.expires_at
    if datetime.now(UTC) > expires_at_aware:
        raise ValueError("Draft expired, please re-upload the file")

    file_data = base64.b64decode(draft.file_data)

    if draft.fmt == "csv":
        parsed = parse_csv(
            file_data,
            draft.encoding,
            draft.delimiter,
            invert_sign=invert_sign,
            prefer_mdy=prefer_mdy,
        )
        rows = parsed.rows
        skipped = [{"line": s.line_number, "reason": s.reason} for s in parsed.skipped]
        warnings = parsed.warnings
    else:
        rows = []
        skipped = []
        warnings = ["OFX parsing – basic support"]

    if not rows:
        raise ValueError("No valid transactions found in the file")

    # Fingerprint dedup (within this file + vs DB)
    occurrence_counter: dict[str, int] = {}
    fingerprints_in_file: set[str] = set()
    clean_rows: list[dict[str, Any]] = []
    dupes_in_file: list[dict[str, Any]] = []

    # Load existing fingerprints for this account
    from sqlalchemy import select as sel
    existing_fps_q = await db.execute(
        sel(Transaction.fingerprint).where(Transaction.account_id == account_id)
    )
    existing_fps: set[str] = {row[0] for row in existing_fps_q}

    from app.brain.normalize import normalize_merchant
    for row in rows:
        merchant = normalize_merchant(row["description_raw"])
        key = f"{account_id}|{row['posted_date']}|{row['amount_cents']}|{merchant}"
        occurrence_counter[key] = occurrence_counter.get(key, 0) + 1
        fp = _fingerprint(account_id, row["posted_date"], row["amount_cents"],
                          merchant, occurrence_counter[key])

        if fp in fingerprints_in_file:
            dupes_in_file.append({"line": row["line_number"], "fingerprint": fp})
            continue
        if fp in existing_fps:
            dupes_in_file.append({
                "line": row["line_number"], "fingerprint": fp, "reason": "already imported"
            })
            continue

        fingerprints_in_file.add(fp)
        clean_rows.append({**row, "fingerprint": fp, "merchant": merchant})

    if dupes_in_file:
        warnings.append(f"Skipped {len(dupes_in_file)} duplicate transaction(s)")

    # Load user rules for brain context
    from app.models.rule import Rule
    rules_q = await db.execute(
        sel(Rule).where(Rule.enabled == True).order_by(Rule.priority.desc())  # noqa: E712
    )
    rules = [
        {
            "match_type": r.match_type, "pattern": r.pattern,
            "category_slug": r.category_id, "priority": r.priority,
        }
        for r in rules_q.scalars()
    ]

    # Load prior debits for this account (for refund matching)
    from app.models.account import Account
    account = await db.get(Account, account_id)
    account_type = account.type if account else "checking"

    prior_txns_q = await db.execute(
        sel(Transaction)
        .where(Transaction.account_id == account_id, Transaction.amount_cents < 0)
        .order_by(Transaction.posted_date.desc())
        .limit(500)
    )
    prior_debits: dict[str, list[dict[str, Any]]] = {}
    for txn in prior_txns_q.scalars():
        prior_debits.setdefault(txn.merchant, []).append({
            "id": txn.id, "amount_cents": txn.amount_cents, "posted_date": txn.posted_date,
        })

    ctx = BrainContext(
        user_rules=rules,
        prior_debits_by_merchant=prior_debits,
        review_threshold=settings.review_threshold,
        review_margin=settings.review_margin,
        equipment_demin_cents=settings.equipment_demin_cents,
        account_type=account_type,
    )

    raw_batch = [
        RawTransaction(
            id=r["fingerprint"],
            description_raw=r["description_raw"],
            amount_cents=r["amount_cents"],
            posted_date=r["posted_date"],
            account_type=account_type,
        )
        for r in clean_rows
    ]

    decisions = categorize(raw_batch, ctx)
    decision_map = {d.id: d for d in decisions}

    # Derive period
    dates = [r["posted_date"] for r in clean_rows]
    period_start = min(dates) if dates else None
    period_end = max(dates) if dates else None

    stmt = Statement(
        id=str(uuid.uuid4()),
        account_id=account_id,
        filename=draft.filename,
        file_sha256=draft.file_sha256,
        format=draft.fmt,
        period_start=period_start,
        period_end=period_end,
        row_count=len(clean_rows),
        skipped_rows=json.dumps(skipped),
        warnings=json.dumps(warnings),
    )
    db.add(stmt)

    txn_objs: list[Transaction] = []
    for row in clean_rows:
        decision = decision_map.get(row["fingerprint"])
        txn = Transaction(
            id=str(uuid.uuid4()),
            statement_id=stmt.id,
            account_id=account_id,
            posted_date=row["posted_date"],
            description_raw=row["description_raw"],
            merchant=row["merchant"],
            amount_cents=row["amount_cents"],
            kind=decision.kind if decision else "unknown",
            category_id=decision.category_slug if decision else None,
            status=decision.status if decision else "needs_review",
            confidence=decision.confidence if decision else 0.0,
            reasons=json.dumps(decision.reasons if decision else []),
            review_reason=decision.review_reason if decision else None,
            fingerprint=row["fingerprint"],
        )
        db.add(txn)
        txn_objs.append(txn)

    # Soft-delete draft
    await db.delete(draft)
    await db.commit()
    await db.refresh(stmt)

    needs_review = sum(1 for t in txn_objs if t.status == "needs_review")
    auto = sum(1 for t in txn_objs if t.status == "auto")

    return {
        "statement_id": stmt.id,
        "row_count": len(txn_objs),
        "auto_count": auto,
        "needs_review_count": needs_review,
        "skipped_count": len(skipped) + len(dupes_in_file),
        "warnings": warnings,
    }
