"""Statement persistence repository."""

from pathlib import Path
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.statement import Statement, StatementStatus


class StatementRepository:
    """Repository managing statement record lifecycle."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        original_filename: str,
        status: str = StatementStatus.PENDING,
        currency: Optional[str] = "USD",
    ) -> Statement:
        """Create a new statement tracking record.

        Extracts a safe basename from any provided path to avoid storing raw local paths.
        """
        safe_filename = Path(original_filename).name or "unknown_statement.csv"

        if status not in StatementStatus.ALL:
            raise ValueError(
                f"Invalid statement status '{status}'. Must be one of: {StatementStatus.ALL}"
            )

        statement = Statement(
            original_filename=safe_filename,
            status=status,
            transaction_count=0,
            currency=currency,
        )
        self.session.add(statement)
        self.session.flush()
        return statement

    def get_by_id(self, statement_id: int) -> Optional[Statement]:
        """Retrieve statement record by ID."""
        return self.session.get(Statement, statement_id)

    def list_statements(self, limit: int = 50, offset: int = 0) -> List[Statement]:
        """List statements with bounded pagination."""
        bounded_limit = max(1, min(limit, 100))
        stmt = (
            select(Statement)
            .order_by(Statement.created_at.desc(), Statement.id.desc())
            .offset(offset)
            .limit(bounded_limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_status(
        self,
        statement_id: int,
        status: str,
        transaction_count: Optional[int] = None,
    ) -> Optional[Statement]:
        """Update statement status and transaction count."""
        statement = self.get_by_id(statement_id)
        if not statement:
            return None

        if status not in StatementStatus.ALL:
            raise ValueError(
                f"Invalid statement status '{status}'. Must be one of: {StatementStatus.ALL}"
            )

        statement.status = status
        if transaction_count is not None:
            if transaction_count < 0:
                raise ValueError("transaction_count cannot be negative.")
            statement.transaction_count = transaction_count

        self.session.flush()
        return statement
