"""Data access. Thin, typed wrappers over SQLAlchemy queries."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Correction, MerchantRule, Statement, TransactionRow, utcnow
from app.domain.enums import Category, Status

SORT_COLUMNS = {
    "date": TransactionRow.posted_date,
    "amount": TransactionRow.amount_cents,
    "confidence": TransactionRow.confidence,
}


def new_id() -> str:
    return str(uuid.uuid4())


class StatementRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(self, statement: Statement) -> Statement:
        self.s.add(statement)
        self.s.flush()
        return statement

    def get(self, statement_id: str) -> Statement | None:
        return self.s.get(Statement, statement_id)

    def list(self) -> Sequence[Statement]:
        q = select(Statement).order_by(Statement.uploaded_at.desc(), Statement.id)
        return self.s.scalars(q).all()

    def find_by_sha(self, sha: str) -> Statement | None:
        q = select(Statement).where(Statement.file_sha256 == sha).limit(1)
        return self.s.scalars(q).first()

    def delete(self, statement_id: str) -> bool:
        result = self.s.execute(delete(Statement).where(Statement.id == statement_id))
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def status_counts_for(self, statement_ids: Sequence[str]) -> dict[str, dict[str, int]]:
        """One grouped query: statement_id -> {status -> count} (all statuses present)."""
        out = {sid: {st.value: 0 for st in Status} for sid in statement_ids}
        if not out:
            return out
        q = (
            select(TransactionRow.statement_id, TransactionRow.status, func.count())
            .where(TransactionRow.statement_id.in_(list(out)))
            .group_by(TransactionRow.statement_id, TransactionRow.status)
        )
        for sid, status, n in self.s.execute(q).tuples():
            out[sid][status] = n
        return out

    def status_counts(self, statement_id: str) -> dict[str, int]:
        return self.status_counts_for([statement_id])[statement_id]


class TransactionRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add_all(self, rows: Sequence[TransactionRow]) -> None:
        self.s.add_all(rows)
        self.s.flush()

    def get(self, txn_id: str) -> TransactionRow | None:
        return self.s.get(TransactionRow, txn_id)

    def for_statement(self, statement_id: str) -> Sequence[TransactionRow]:
        q = (
            select(TransactionRow)
            .where(TransactionRow.statement_id == statement_id)
            .order_by(TransactionRow.row_index)
        )
        return self.s.scalars(q).all()

    def query(
        self,
        statement_id: str,
        *,
        status: str | None = None,
        category: str | None = None,
        q: str | None = None,
        sort: str = "date",
        order: str = "asc",
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[Sequence[TransactionRow], int]:
        base = select(TransactionRow).where(TransactionRow.statement_id == statement_id)
        if status:
            base = base.where(TransactionRow.status == status)
        if category:
            base = base.where(TransactionRow.category == category)
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            base = base.where(TransactionRow.description.ilike(f"%{escaped}%", escape="\\"))
        total = self.s.scalar(select(func.count()).select_from(base.subquery())) or 0
        col = SORT_COLUMNS.get(sort, TransactionRow.posted_date)
        ordering = col.desc() if order == "desc" else col.asc()
        base = base.order_by(ordering, TransactionRow.row_index).limit(limit).offset(offset)
        return self.s.scalars(base).all(), total

    def similar_counts(self, statement_id: str) -> dict[str, int]:
        """merchant_key -> number of rows eligible for 'apply to similar'."""
        q = (
            select(TransactionRow.merchant_key, func.count())
            .where(
                TransactionRow.statement_id == statement_id,
                TransactionRow.status.in_([Status.AUTO.value, Status.NEEDS_REVIEW.value]),
            )
            .group_by(TransactionRow.merchant_key)
        )
        return {key: n for key, n in self.s.execute(q).tuples()}  # noqa: C416

    def similar_rows(self, row: TransactionRow) -> Sequence[TransactionRow]:
        q = select(TransactionRow).where(
            TransactionRow.statement_id == row.statement_id,
            TransactionRow.merchant_key == row.merchant_key,
            TransactionRow.id != row.id,
            TransactionRow.status.in_([Status.AUTO.value, Status.NEEDS_REVIEW.value]),
        )
        return self.s.scalars(q.order_by(TransactionRow.row_index)).all()

    def prior_fingerprints(self, account_type: str | None = None) -> dict[str, str]:
        """fingerprint -> id of the earliest real (non-duplicate) stored transaction.

        Scoped to one account type when given (a checking row never duplicates a card row).
        Ordered newest-upload-first so the last write, the earliest upload, wins.
        """
        q = (
            select(TransactionRow.fingerprint, TransactionRow.id)
            .join(Statement, Statement.id == TransactionRow.statement_id)
            .where(TransactionRow.status != Status.DUPLICATE.value)
            .order_by(Statement.uploaded_at.desc(), Statement.id, TransactionRow.row_index.desc())
        )
        if account_type is not None:
            q = q.where(Statement.account_type == account_type)
        result: dict[str, str] = {}
        for fp, tid in self.s.execute(q):
            result[fp] = tid
        return result

    def ytd_by_counterparty(self, year: int) -> dict[str, int]:
        """counterparty -> absolute cents already paid out this year in stored statements."""
        q = (
            select(TransactionRow.counterparty, func.sum(func.abs(TransactionRow.amount_cents)))
            .where(
                TransactionRow.counterparty.is_not(None),
                TransactionRow.amount_cents < 0,
                TransactionRow.status.in_([Status.AUTO.value, Status.USER_CONFIRMED.value]),
                TransactionRow.posted_date >= datetime(year, 1, 1).date(),
                TransactionRow.posted_date <= datetime(year, 12, 31).date(),
            )
            .group_by(TransactionRow.counterparty)
        )
        return {cp: int(total) for cp, total in self.s.execute(q) if cp}


class MerchantRuleRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def memory(self) -> dict[str, Category]:
        out: dict[str, Category] = {}
        for rule in self.s.scalars(select(MerchantRule)):
            try:
                out[rule.merchant_key] = Category(rule.category)
            except ValueError:
                continue
        return out

    def upsert(
        self, merchant_key: str, category: Category, source_transaction_id: str | None
    ) -> bool:
        """Create or update the remembered rule. Returns True when a new rule was created."""
        rule = self.s.scalars(
            select(MerchantRule).where(MerchantRule.merchant_key == merchant_key)
        ).first()
        if rule is None:
            self.s.add(
                MerchantRule(
                    id=new_id(),
                    merchant_key=merchant_key,
                    category=category.value,
                    source_transaction_id=source_transaction_id,
                )
            )
            self.s.flush()
            return True
        rule.category = category.value
        rule.updated_at = utcnow()
        rule.source_transaction_id = source_transaction_id
        self.s.flush()
        return False


class CorrectionRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(
        self,
        *,
        transaction_id: str,
        from_category: str | None,
        to_category: str,
        from_status: str,
        remember: bool,
        applied_to_similar: int,
    ) -> None:
        self.s.add(
            Correction(
                id=new_id(),
                transaction_id=transaction_id,
                from_category=from_category,
                to_category=to_category,
                from_status=from_status,
                remember=remember,
                applied_to_similar=applied_to_similar,
            )
        )
