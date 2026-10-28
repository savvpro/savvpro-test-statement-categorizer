"""Transaction corrections."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import (
    CategorizeDep,
    RuleSetDep,
    SessionDep,
    SettingsDep,
    transactions_out,
)
from app.api.schemas import PatchResult, ProblemDetail, TransactionOut, TransactionPatch
from app.services import review

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

PROBLEMS: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetail, "description": "Transaction not found"},
    422: {"model": ProblemDetail, "description": "Invalid correction"},
}


@router.patch("/{transaction_id}", response_model=PatchResult, responses=PROBLEMS)
def patch_transaction(
    transaction_id: str, body: TransactionPatch, session: SessionDep
) -> PatchResult:
    rows, rule_created = review.update_transaction(
        session,
        transaction_id,
        body.category,
        remember=body.remember,
        apply_to_similar=body.apply_to_similar,
    )
    session.commit()
    return PatchResult(updated=transactions_out(session, rows), rule_created=rule_created)


@router.post(
    "/{transaction_id}/restore-duplicate", response_model=TransactionOut, responses=PROBLEMS
)
def restore_duplicate(
    transaction_id: str,
    session: SessionDep,
    settings: SettingsDep,
    ruleset: RuleSetDep,
    categorize: CategorizeDep,
) -> TransactionOut:
    row = review.restore_duplicate(
        session, transaction_id, settings=settings, ruleset=ruleset, categorize=categorize
    )
    session.commit()
    return transactions_out(session, [row])[0]
