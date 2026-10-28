"""Upload pipeline: parse -> normalize -> brain -> persist."""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.brain.context import BrainContext, BrainSettings
from app.brain.rules import RuleSet
from app.core.config import Settings
from app.core.errors import DuplicateStatement, ParseError
from app.core.logging import statement_id_var
from app.core.security import sanitize_filename
from app.db.models import Statement, TransactionRow
from app.db.repositories import MerchantRuleRepo, StatementRepo, TransactionRepo, new_id
from app.domain.enums import AccountType, Category, Flag
from app.domain.models import Decision, Transaction
from app.ingest import parse_statement
from app.normalize.normalizer import normalize

CategorizeFn = Callable[[Sequence[Transaction], BrainContext], list[Decision]]


def default_categorize() -> CategorizeFn:
    from app.brain.engine import categorize

    return categorize


def brain_settings(settings: Settings) -> BrainSettings:
    return BrainSettings(
        auto_threshold=settings.auto_threshold,
        margin_threshold=settings.margin_threshold,
        de_minimis_cents=settings.de_minimis_cents,
        contractor_1099_cents=settings.contractor_1099_cents,
        fuzzy_min_ratio=settings.fuzzy_min_ratio,
    )


def build_context(
    session: Session,
    ruleset: RuleSet,
    settings: Settings,
    *,
    years: Sequence[int],
    account_type: AccountType | None = None,
) -> BrainContext:
    txn_repo = TransactionRepo(session)
    ytd: dict[str, int] = {}
    for year in sorted(set(years)):
        for cp, cents in txn_repo.ytd_by_counterparty(year).items():
            ytd[cp] = ytd.get(cp, 0) + cents
    return BrainContext(
        rules=ruleset,
        settings=brain_settings(settings),
        memory=MerchantRuleRepo(session).memory(),
        prior_fingerprints=txn_repo.prior_fingerprints(
            account_type.value if account_type else None
        ),
        ytd_by_counterparty=ytd,
    )


def _value(category: Category | None) -> str | None:
    return category.value if category else None


def _duplicate(existing_id: str) -> DuplicateStatement:
    return DuplicateStatement(
        f"This exact file was already uploaded as statement {existing_id}",
        extra={"existing_id": existing_id},
    )


def process_upload(
    session: Session,
    *,
    data: bytes,
    filename: str,
    account_type: AccountType,
    settings: Settings,
    ruleset: RuleSet,
    categorize: CategorizeFn | None = None,
) -> Statement:
    """Run the whole pipeline; the caller commits. Raw bytes are discarded after parsing."""
    sha = hashlib.sha256(data).hexdigest()
    statements = StatementRepo(session)
    existing = statements.find_by_sha(sha)
    if existing is not None:
        raise _duplicate(existing.id)
    safe_name = sanitize_filename(filename)
    fmt, parsed = parse_statement(data, safe_name, max_rows=settings.max_rows)
    txns, norm_warnings = normalize(parsed, account_type)
    if not txns:
        raise ParseError("No usable transactions in the file", code="NO_TRANSACTIONS")

    ctx = build_context(
        session,
        ruleset,
        settings,
        years=[t.posted_date.year for t in txns],
        account_type=account_type,
    )
    decisions = (categorize or default_categorize())(txns, ctx)
    if len(decisions) != len(txns):
        raise RuntimeError("categorize returned a different number of decisions")

    statement = Statement(
        id=new_id(),
        filename=safe_name,
        source_format=fmt.value,
        account_type=account_type.value,
        file_sha256=sha,
        uploaded_at=datetime.now(UTC),
        period_start=min(t.posted_date for t in txns),
        period_end=max(t.posted_date for t in txns),
        row_count=len(txns),
        warnings=[asdict(w) for w in (*parsed.warnings, *norm_warnings)],
    )
    try:
        statements.add(statement)
    except IntegrityError:
        # A concurrent identical upload won the race on the unique file_sha256.
        session.rollback()
        winner = statements.find_by_sha(sha)
        if winner is None:
            raise
        raise _duplicate(winner.id) from None
    statement_id_var.set(statement.id)

    ids = {t.row_index: new_id() for t in txns}
    rows = [
        _to_row(statement.id, ids, txn, dec, ctx) for txn, dec in zip(txns, decisions, strict=True)
    ]
    TransactionRepo(session).add_all(rows)
    return statement


def _to_row(
    statement_id: str,
    ids: dict[int, str],
    txn: Transaction,
    dec: Decision,
    ctx: BrainContext,
) -> TransactionRow:
    duplicate_of: str | None = None
    if Flag.DUPLICATE_PRIOR_UPLOAD in dec.flags:
        duplicate_of = ctx.prior_fingerprints.get(txn.fingerprint)
    elif dec.duplicate_of_row is not None:
        duplicate_of = ids.get(dec.duplicate_of_row)
    return TransactionRow(
        id=ids[txn.row_index],
        statement_id=statement_id,
        row_index=txn.row_index,
        posted_date=txn.posted_date,
        amount_cents=txn.amount_cents,
        direction=txn.direction.value,
        description=txn.description,
        memo=txn.memo,
        merchant_key=txn.merchant_key,
        channel=txn.channel,
        counterparty=txn.counterparty,
        fitid=txn.fitid,
        fingerprint=txn.fingerprint,
        is_pending=txn.is_pending,
        brain_category=_value(dec.category or dec.suggestion),
        category=_value(dec.category),
        status=dec.status.value,
        confidence=dec.confidence,
        reasons=list(dec.reasons),
        rule_ids=list(dec.rule_ids),
        flags=sorted(f.value for f in dec.flags),
        is_refund=dec.is_refund,
        duplicate_of_id=duplicate_of,
    )
