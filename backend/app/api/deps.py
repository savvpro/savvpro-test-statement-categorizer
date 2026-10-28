"""Dependencies and ORM -> schema mappers."""

from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.schemas import (
    ParseWarningOut,
    StatementCounts,
    StatementOut,
    TransactionOut,
)
from app.brain.rules import RuleSet
from app.core.config import Settings
from app.db.models import Statement, TransactionRow
from app.db.repositories import StatementRepo, TransactionRepo
from app.db.session import get_session
from app.domain.enums import AccountType, Category, Direction, SourceFormat, Status
from app.services.ingestion import CategorizeFn

SessionDep = Annotated[Session, Depends(get_session)]


def get_settings_dep(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_ruleset(request: Request) -> RuleSet:
    return cast(RuleSet, request.app.state.ruleset)


def get_categorize(request: Request) -> CategorizeFn | None:
    return cast(CategorizeFn | None, request.app.state.categorize)


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
RuleSetDep = Annotated[RuleSet, Depends(get_ruleset)]
CategorizeDep = Annotated[CategorizeFn | None, Depends(get_categorize)]


def statement_out(
    session: Session, st: Statement, counts: dict[str, int] | None = None
) -> StatementOut:
    if counts is None:
        counts = StatementRepo(session).status_counts(st.id)
    return StatementOut(
        id=st.id,
        filename=st.filename,
        source_format=SourceFormat(st.source_format),
        account_type=AccountType(st.account_type),
        uploaded_at=st.uploaded_at,
        period_start=st.period_start,
        period_end=st.period_end,
        row_count=st.row_count,
        counts=StatementCounts(**counts),
        warnings=[ParseWarningOut(**w) for w in st.warnings or []],
    )


def similar_count(row: TransactionRow, by_key: dict[str, int]) -> int:
    eligible = row.status in {Status.AUTO.value, Status.NEEDS_REVIEW.value}
    return max(by_key.get(row.merchant_key, 0) - (1 if eligible else 0), 0)


def transaction_out(row: TransactionRow, by_key: dict[str, int]) -> TransactionOut:
    return TransactionOut(
        id=row.id,
        row_index=row.row_index,
        posted_date=row.posted_date,
        amount_cents=row.amount_cents,
        direction=Direction(row.direction),
        description=row.description,
        memo=row.memo,
        merchant_key=row.merchant_key,
        category=Category(row.category) if row.category else None,
        brain_category=Category(row.brain_category) if row.brain_category else None,
        status=Status(row.status),
        confidence=row.confidence,
        reasons=list(row.reasons or []),
        flags=list(row.flags or []),
        is_refund=row.is_refund,
        duplicate_of_id=row.duplicate_of_id,
        similar_count=similar_count(row, by_key),
    )


def transactions_out(session: Session, rows: list[TransactionRow]) -> list[TransactionOut]:
    repo = TransactionRepo(session)
    cache: dict[str, dict[str, int]] = {}
    out: list[TransactionOut] = []
    for r in rows:
        if r.statement_id not in cache:
            cache[r.statement_id] = repo.similar_counts(r.statement_id)
        out.append(transaction_out(r, cache[r.statement_id]))
    return out
