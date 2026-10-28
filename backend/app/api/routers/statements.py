"""Statement upload, listing, transactions listing, summary and export."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.deps import (
    CategorizeDep,
    RuleSetDep,
    SessionDep,
    SettingsDep,
    statement_out,
    transaction_out,
)
from app.api.schemas import (
    DuplicatesOut,
    ProblemDetail,
    ScheduleELine,
    StatementOut,
    SummaryOut,
    TransactionListOut,
    Unresolved,
)
from app.core.errors import NotFound
from app.core.ratelimit import current_limit, limiter
from app.core.security import read_upload_limited, safe_download_stem, sanitize_filename
from app.db.models import Statement
from app.db.repositories import StatementRepo, TransactionRepo
from app.domain.enums import AccountType, Category, Status
from app.services import ingestion
from app.services.export import export_csv
from app.services.summary import compute_summary

router = APIRouter(prefix="/api/v1/statements", tags=["statements"])

PROBLEMS: dict[int | str, dict[str, Any]] = {
    409: {"model": ProblemDetail, "description": "Identical file already uploaded"},
    413: {"model": ProblemDetail, "description": "Upload too large"},
    415: {"model": ProblemDetail, "description": "Unsupported file type"},
    422: {"model": ProblemDetail, "description": "Statement could not be parsed"},
    429: {"model": ProblemDetail, "description": "Rate limit exceeded"},
}

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetail, "description": "Statement not found"}
}


def _get_statement(session: SessionDep, statement_id: str) -> Statement:
    st = StatementRepo(session).get(statement_id)
    if st is None:
        raise NotFound("Statement not found")
    return st


@router.post("", status_code=201, response_model=StatementOut, responses=PROBLEMS)
@limiter.limit(current_limit)
async def upload_statement(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    ruleset: RuleSetDep,
    categorize: CategorizeDep,
    file: Annotated[UploadFile, File()],
    account_type: Annotated[AccountType, Form()],
) -> StatementOut:
    data = await read_upload_limited(file, settings.max_upload_bytes)
    filename = sanitize_filename(file.filename)

    def work() -> StatementOut:
        st = ingestion.process_upload(
            session,
            data=data,
            filename=filename,
            account_type=account_type,
            settings=settings,
            ruleset=ruleset,
            categorize=categorize,
        )
        out = statement_out(session, st)
        session.commit()
        return out

    return await run_in_threadpool(work)


@router.get("", response_model=list[StatementOut])
def list_statements(session: SessionDep) -> list[StatementOut]:
    repo = StatementRepo(session)
    statements = repo.list()
    counts = repo.status_counts_for([s.id for s in statements])
    return [statement_out(session, s, counts[s.id]) for s in statements]


@router.get("/{statement_id}", response_model=StatementOut, responses=NOT_FOUND)
def get_statement(statement_id: str, session: SessionDep) -> StatementOut:
    return statement_out(session, _get_statement(session, statement_id))


@router.delete("/{statement_id}", status_code=204, responses=NOT_FOUND)
def delete_statement(statement_id: str, session: SessionDep) -> Response:
    if not StatementRepo(session).delete(statement_id):
        raise NotFound("Statement not found")
    session.commit()
    return Response(status_code=204)


@router.get("/{statement_id}/transactions", response_model=TransactionListOut, responses=NOT_FOUND)
def list_transactions(
    statement_id: str,
    session: SessionDep,
    status: Status | None = None,
    category: Category | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: Literal["date", "amount", "confidence"] = "date",
    order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListOut:
    _get_statement(session, statement_id)
    repo = TransactionRepo(session)
    rows, total = repo.query(
        statement_id,
        status=status.value if status else None,
        category=category.value if category else None,
        q=q,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
    by_key = repo.similar_counts(statement_id)
    return TransactionListOut(items=[transaction_out(r, by_key) for r in rows], total=total)


@router.get("/{statement_id}/summary", response_model=SummaryOut, responses=NOT_FOUND)
def get_summary(statement_id: str, session: SessionDep) -> SummaryOut:
    _get_statement(session, statement_id)
    s = compute_summary(TransactionRepo(session).for_statement(statement_id))
    return SummaryOut(
        income=s.income,
        expenses=s.expenses,
        schedule_e=[ScheduleELine(**line) for line in s.schedule_e],
        total_income_cents=s.total_income_cents,
        total_expense_cents=s.total_expense_cents,
        net_cents=s.net_cents,
        excluded=s.excluded,
        unresolved=Unresolved(
            count=s.unresolved_count, total_abs_cents=s.unresolved_total_abs_cents
        ),
        duplicates=DuplicatesOut(count=s.duplicate_count),
    )


@router.get("/{statement_id}/export.csv", response_class=Response, responses=NOT_FOUND)
def export_statement(statement_id: str, session: SessionDep) -> Response:
    st = _get_statement(session, statement_id)
    body = export_csv(TransactionRepo(session).for_statement(statement_id))
    name = f"{safe_download_stem(st.filename)}-categorized.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
