"""Transaction and classification event persistence repository."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.classification_event import ClassificationEvent, ClassificationEventType
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction
from app.schemas.transaction import CategorizationResult, TransactionInput


ALLOWED_SORT_FIELDS: Set[str] = {
    "date",
    "amount",
    "description",
    "confidence",
    "category",
    "status",
    "id",
}


class TransactionRepository:
    """Repository managing transaction persistence, querying, and audit events."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        statement_id: int,
        transaction_input: TransactionInput,
        categorization_result: CategorizationResult,
        category_id: Optional[int],
    ) -> Transaction:
        """Persist a single validated and categorized transaction."""
        # Map review requirement to review_status
        review_status = (
            ReviewStatus.PENDING
            if categorization_result.review_required
            else ReviewStatus.NOT_REQUIRED
        )

        tx = Transaction(
            statement_id=statement_id,
            transaction_date=transaction_input.date,
            original_description=transaction_input.original_description,
            normalized_description=categorization_result.normalized_description,
            amount=transaction_input.amount,
            currency=transaction_input.currency or "USD",
            category_id=category_id,
            confidence_score=categorization_result.confidence_score,
            classification_reason=categorization_result.explanation,
            review_status=review_status,
            was_manually_categorized=False,
        )
        self.session.add(tx)
        self.session.flush()

        # Record initial automatic classification event if category assigned
        if category_id is not None:
            self.record_classification_event(
                transaction_id=tx.id,
                new_category_id=category_id,
                event_type=ClassificationEventType.AUTO_CLASSIFIED,
                reason=categorization_result.explanation,
            )

        return tx

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Retrieve a transaction by ID with eager-loaded relationships."""
        stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.statement),
                joinedload(Transaction.classification_events).joinedload(
                    ClassificationEvent.previous_category
                ),
                joinedload(Transaction.classification_events).joinedload(
                    ClassificationEvent.new_category
                ),
            )
            .where(Transaction.id == transaction_id)
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_statement(
        self, statement_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Retrieve transactions for a given statement with bounded pagination."""
        bounded_limit = max(1, min(limit, 200))
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.statement_id == statement_id)
            .order_by(Transaction.id)
            .offset(offset)
            .limit(bounded_limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def search_and_filter(
        self,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = "date",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Transaction], int]:
        """Search and filter transactions with server-side pagination and stable sorting.

        Args:
            q: Optional search query matching original or normalized description.
            category_id: Filter by specific category ID.
            status: Filter by review status ('PENDING', 'REVIEWED', 'NOT_REQUIRED').
            tx_type: Filter by amount sign ('income' -> >0, 'expense' -> <0).
            statement_id: Filter by parent statement ID.
            start_date: Inclusive lower bound on transaction_date.
            end_date: Inclusive upper bound on transaction_date.
            sort_by: Column to sort by (from whitelist).
            sort_dir: 'asc' or 'desc'.
            page: 1-indexed page number.
            page_size: Number of items per page.

        Returns:
            Tuple of (transactions_page, total_matching_count)
        """
        # Validate pagination
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        offset = (safe_page - 1) * safe_page_size

        # Validate sorting
        normalized_sort = sort_by.lower() if sort_by else "date"
        if normalized_sort not in ALLOWED_SORT_FIELDS:
            normalized_sort = "date"

        is_desc = (sort_dir or "desc").lower() == "desc"

        # Build filter expressions
        filters = []

        if q and q.strip():
            cleaned_q = q.strip()
            pattern = f"%{cleaned_q}%"
            filters.append(
                or_(
                    Transaction.original_description.ilike(pattern),
                    Transaction.normalized_description.ilike(pattern),
                )
            )

        if category_id is not None:
            if category_id == 0:
                # 0 signifies unassigned or Needs Review
                filters.append(
                    or_(
                        Transaction.category_id.is_(None),
                        Category.name == "Needs Review",
                    )
                )
            else:
                filters.append(Transaction.category_id == category_id)

        if status and status.strip():
            st_norm = status.strip().upper()
            if st_norm in ReviewStatus.ALL:
                filters.append(Transaction.review_status == st_norm)

        if tx_type and tx_type.strip():
            type_norm = tx_type.strip().lower()
            if type_norm == "income":
                filters.append(Transaction.amount > 0)
            elif type_norm == "expense":
                filters.append(Transaction.amount < 0)

        if statement_id is not None and statement_id > 0:
            filters.append(Transaction.statement_id == statement_id)

        if start_date is not None:
            filters.append(Transaction.transaction_date >= start_date)

        if end_date is not None:
            filters.append(Transaction.transaction_date <= end_date)

        # 1. Total matching count query
        count_stmt = (
            select(func.count(Transaction.id))
            .join(Transaction.category, isouter=True)
            .where(*filters)
        )
        total_count = self.session.execute(count_stmt).scalar() or 0

        # 2. Sort expression resolution
        sort_column_map = {
            "date": Transaction.transaction_date,
            "amount": Transaction.amount,
            "description": Transaction.original_description,
            "confidence": Transaction.confidence_score,
            "category": Category.name,
            "status": Transaction.review_status,
            "id": Transaction.id,
        }
        primary_col = sort_column_map.get(normalized_sort, Transaction.transaction_date)

        if is_desc:
            order_clause = [primary_col.desc(), Transaction.id.desc()]
        else:
            order_clause = [primary_col.asc(), Transaction.id.asc()]

        # 3. Paginated transactions query
        data_stmt = (
            select(Transaction)
            .join(Transaction.category, isouter=True)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.statement),
            )
            .where(*filters)
            .order_by(*order_clause)
            .offset(offset)
            .limit(safe_page_size)
        )

        transactions = list(self.session.execute(data_stmt).scalars().all())
        return transactions, total_count

    def get_all_matching(
        self,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = "date",
        sort_dir: str = "desc",
        max_limit: int = 50000,
    ) -> List[Transaction]:
        """Fetch all matching transactions without pagination for CSV export.

        Shares exact filter and sorting logic with search_and_filter to guarantee consistency.
        """
        normalized_sort = sort_by.lower() if sort_by else "date"
        if normalized_sort not in ALLOWED_SORT_FIELDS:
            normalized_sort = "date"

        is_desc = (sort_dir or "desc").lower() == "desc"

        filters = []
        if q and q.strip():
            cleaned_q = q.strip()
            pattern = f"%{cleaned_q}%"
            filters.append(
                or_(
                    Transaction.original_description.ilike(pattern),
                    Transaction.normalized_description.ilike(pattern),
                )
            )

        if category_id is not None:
            if category_id == 0:
                filters.append(
                    or_(
                        Transaction.category_id.is_(None),
                        Category.name == "Needs Review",
                    )
                )
            else:
                filters.append(Transaction.category_id == category_id)

        if status and status.strip():
            st_norm = status.strip().upper()
            if st_norm in ReviewStatus.ALL:
                filters.append(Transaction.review_status == st_norm)

        if tx_type and tx_type.strip():
            type_norm = tx_type.strip().lower()
            if type_norm == "income":
                filters.append(Transaction.amount > 0)
            elif type_norm == "expense":
                filters.append(Transaction.amount < 0)

        if statement_id is not None and statement_id > 0:
            filters.append(Transaction.statement_id == statement_id)

        if start_date is not None:
            filters.append(Transaction.transaction_date >= start_date)

        if end_date is not None:
            filters.append(Transaction.transaction_date <= end_date)

        sort_column_map = {
            "date": Transaction.transaction_date,
            "amount": Transaction.amount,
            "description": Transaction.original_description,
            "confidence": Transaction.confidence_score,
            "category": Category.name,
            "status": Transaction.review_status,
            "id": Transaction.id,
        }
        primary_col = sort_column_map.get(normalized_sort, Transaction.transaction_date)

        if is_desc:
            order_clause = [primary_col.desc(), Transaction.id.desc()]
        else:
            order_clause = [primary_col.asc(), Transaction.id.asc()]

        data_stmt = (
            select(Transaction)
            .join(Transaction.category, isouter=True)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.statement),
            )
            .where(*filters)
            .order_by(*order_clause)
            .limit(max_limit)
        )

        return list(self.session.execute(data_stmt).scalars().all())

    def record_classification_event(

        self,
        transaction_id: int,
        new_category_id: int,
        event_type: str = ClassificationEventType.AUTO_CLASSIFIED,
        previous_category_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> ClassificationEvent:
        """Record a classification audit event."""
        if event_type not in ClassificationEventType.ALL:
            raise ValueError(
                f"Invalid event_type '{event_type}'. Must be one of: {ClassificationEventType.ALL}"
            )

        event = ClassificationEvent(
            transaction_id=transaction_id,
            previous_category_id=previous_category_id,
            new_category_id=new_category_id,
            event_type=event_type,
            reason=reason,
        )
        self.session.add(event)
        self.session.flush()
        return event
