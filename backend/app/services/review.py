"""User corrections: PATCH, remember, apply-to-similar, restore-duplicate."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.brain.context import BrainContext
from app.brain.rules import RuleSet
from app.core.config import Settings
from app.core.errors import InvalidCorrection, NotFound
from app.db.models import TransactionRow
from app.db.repositories import CorrectionRepo, MerchantRuleRepo, StatementRepo, TransactionRepo
from app.domain.enums import AccountType, Category, Direction, Flag, Status
from app.domain.models import Transaction
from app.domain.taxonomy import is_allowed
from app.services.ingestion import CategorizeFn, build_context, default_categorize

_DUPLICATE_FLAGS = {
    Flag.DUPLICATE_FITID.value,
    Flag.DUPLICATE_PENDING.value,
    Flag.DUPLICATE_PRIOR_UPLOAD.value,
}
UNREMEMBERABLE_KEYS = frozenset({"UNKNOWN"})


def get_or_404(session: Session, txn_id: str) -> TransactionRow:
    row = TransactionRepo(session).get(txn_id)
    if row is None:
        raise NotFound("Transaction not found")
    return row


def _compatible(row: TransactionRow, category: Category) -> bool:
    return is_allowed(
        category,
        Direction(row.direction),
        is_refund=row.is_refund or Flag.RENT_REVERSAL.value in row.flags,
    )


def _apply(
    row: TransactionRow, category: Category, corrections: CorrectionRepo, *, remember: bool, n: int
) -> None:
    corrections.add(
        transaction_id=row.id,
        from_category=row.category,
        to_category=category.value,
        from_status=row.status,
        remember=remember,
        applied_to_similar=n,
    )
    row.category = category.value
    row.status = Status.USER_CONFIRMED.value
    row.updated_at = datetime.now(UTC)


def update_transaction(
    session: Session,
    txn_id: str,
    category: Category,
    *,
    remember: bool = False,
    apply_to_similar: bool = False,
) -> tuple[list[TransactionRow], bool]:
    row = get_or_404(session, txn_id)
    if not _compatible(row, category):
        raise InvalidCorrection(
            f"{category.value} cannot be applied to an {row.direction} transaction"
        )
    repo = TransactionRepo(session)
    corrections = CorrectionRepo(session)
    similar: list[TransactionRow] = []
    if apply_to_similar:
        similar = [r for r in repo.similar_rows(row) if _compatible(r, category)]
    _apply(row, category, corrections, remember=remember, n=len(similar))
    for other in similar:
        _apply(other, category, corrections, remember=False, n=0)
    rule_created = False
    if remember and row.merchant_key not in UNREMEMBERABLE_KEYS:
        rule_created = MerchantRuleRepo(session).upsert(row.merchant_key, category, row.id)
    session.flush()
    return [row, *similar], rule_created


def restore_duplicate(
    session: Session,
    txn_id: str,
    *,
    settings: Settings,
    ruleset: RuleSet,
    categorize: CategorizeFn | None = None,
) -> TransactionRow:
    row = get_or_404(session, txn_id)
    if row.status != Status.DUPLICATE.value:
        raise InvalidCorrection("Only a duplicate transaction can be restored")
    statement = StatementRepo(session).get(row.statement_id)
    if statement is None:
        raise NotFound("Statement not found")
    txn = Transaction(
        row_index=row.row_index,
        posted_date=row.posted_date,
        amount_cents=row.amount_cents,
        direction=Direction(row.direction),
        description=row.description,
        memo=row.memo,
        merchant_key=row.merchant_key,
        channel=row.channel,
        counterparty=row.counterparty,
        account_type=AccountType(statement.account_type),
        fitid=row.fitid,
        fingerprint=row.fingerprint,
        is_pending=row.is_pending,
    )
    full = build_context(session, ruleset, settings, years=[row.posted_date.year])
    # Isolated re-run: no prior fingerprints, so it cannot be flagged as a duplicate again.
    ctx = BrainContext(
        rules=full.rules,
        settings=full.settings,
        memory=full.memory,
        ytd_by_counterparty=full.ytd_by_counterparty,
    )
    decision = (categorize or default_categorize())([txn], ctx)[0]
    status = Status.NEEDS_REVIEW if decision.status is Status.DUPLICATE else decision.status
    suggested = decision.category or decision.suggestion
    row.brain_category = suggested.value if suggested else None
    row.category = decision.category.value if decision.category else None
    row.status = status.value
    row.confidence = decision.confidence
    row.reasons = [*decision.reasons, "Restored by user as a real transaction"]
    row.rule_ids = list(decision.rule_ids)
    row.flags = sorted(f.value for f in decision.flags if f.value not in _DUPLICATE_FLAGS)
    row.is_refund = decision.is_refund
    row.duplicate_of_id = None
    row.updated_at = datetime.now(UTC)
    session.flush()
    return row
