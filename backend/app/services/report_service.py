"""Financial reporting and analytics service for LedgerLens.

Provides database-level aggregations for:
- Summary financial metrics (Total Income, Total Expenses, Net Movement, Review Counts)
- Category-wise reports with spending, income, net amounts, and review statuses
- Monthly financial trend analysis (Income vs Expenses vs Net Movement over time)
- Date range, category, transaction type, and statement filtering
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction
from app.services.dashboard_service import _to_decimal, _to_int


@dataclass(frozen=True)
class FinancialSummary:
    """Summary of financial metrics for reporting."""

    total_transactions: int
    total_income: Decimal
    total_expenses: Decimal
    net_movement: Decimal
    categorized_count: int
    uncategorized_count: int
    review_required_count: int
    total_transfers: Decimal
    total_refunds: Decimal
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass(frozen=True)
class CategoryReportItem:
    """Aggregated financial report item per category."""

    category_id: Optional[int]
    category_name: str
    transaction_count: int
    total_expenses: Decimal
    total_income: Decimal
    net_amount: Decimal
    review_required_count: int
    percentage_of_expenses: float


@dataclass(frozen=True)
class MonthlyTrendItem:
    """Monthly financial performance record."""

    month_key: str  # YYYY-MM
    month_label: str  # e.g. "Aug 2026"
    transaction_count: int
    income: Decimal
    expenses: Decimal
    net: Decimal


class ReportService:
    """Service providing financial reporting aggregations."""

    # Category names excluded from ordinary income/expense per application specifications
    NON_INCOME_CATEGORIES = ["Internal Transfer", "Reversal", "Refund"]
    NON_EXPENSE_CATEGORIES = ["Internal Transfer", "Reversal"]

    def __init__(self, session: Session) -> None:
        self.session = session

    def _build_filter_clauses(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
    ) -> List[Any]:
        """Construct SQLAlchemy WHERE clauses for filtering."""
        filters = []
        if start_date is not None:
            filters.append(Transaction.transaction_date >= start_date)
        if end_date is not None:
            filters.append(Transaction.transaction_date <= end_date)
        if statement_id is not None and statement_id > 0:
            filters.append(Transaction.statement_id == statement_id)
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
        if tx_type and tx_type.strip():
            type_norm = tx_type.strip().lower()
            if type_norm == "income":
                filters.append(Transaction.amount > 0)
            elif type_norm == "expense":
                filters.append(Transaction.amount < 0)

        return filters

    def get_financial_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
    ) -> FinancialSummary:
        """Calculate overall financial summary metrics using database aggregation."""
        filters = self._build_filter_clauses(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            tx_type=tx_type,
            statement_id=statement_id,
        )

        # 1. Total transaction count
        total_tx_query = (
            select(func.count(Transaction.id))
            .join(Transaction.category, isouter=True)
            .where(*filters)
        )
        total_transactions = _to_int(self.session.execute(total_tx_query).scalar())

        # 2. Categorized count (not None and not 'Needs Review')
        cat_query = (
            select(func.count(Transaction.id))
            .join(Transaction.category, isouter=True)
            .where(
                Transaction.category_id.isnot(None),
                Category.name != "Needs Review",
                *filters,
            )
        )
        categorized_count = _to_int(self.session.execute(cat_query).scalar())

        # 3. Uncategorized count (None or 'Needs Review')
        uncat_query = (
            select(func.count(Transaction.id))
            .join(Transaction.category, isouter=True)
            .where(
                or_(
                    Transaction.category_id.is_(None),
                    Category.name == "Needs Review",
                ),
                *filters,
            )
        )
        uncategorized_count = _to_int(self.session.execute(uncat_query).scalar())

        # 4. Review required count
        review_query = (
            select(func.count(Transaction.id))
            .join(Transaction.category, isouter=True)
            .where(
                or_(
                    Transaction.review_status == ReviewStatus.PENDING,
                    Category.name == "Needs Review",
                    Transaction.category_id.is_(None),
                ),
                *filters,
            )
        )
        review_required_count = _to_int(self.session.execute(review_query).scalar())

        # 5. Total Income
        income_query = (
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00")))
            .join(Transaction.category, isouter=True)
            .where(
                Transaction.amount > 0,
                or_(
                    Category.name.is_(None),
                    Category.name.notin_(self.NON_INCOME_CATEGORIES),
                ),
                *filters,
            )
        )
        total_income = _to_decimal(self.session.execute(income_query).scalar())

        # 6. Total Expenses
        expense_query = (
            select(func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0.00")))
            .join(Transaction.category, isouter=True)
            .where(
                Transaction.amount < 0,
                or_(
                    Category.name.is_(None),
                    Category.name.notin_(self.NON_EXPENSE_CATEGORIES),
                ),
                *filters,
            )
        )
        total_expenses = _to_decimal(self.session.execute(expense_query).scalar())

        # 7. Total Transfers (isolated from ordinary revenue/expense)
        transfer_query = (
            select(func.coalesce(func.sum(func.abs(Transaction.amount)), Decimal("0.00")))
            .join(Transaction.category, isouter=True)
            .where(
                Category.name == "Internal Transfer",
                *filters,
            )
        )
        total_transfers = _to_decimal(self.session.execute(transfer_query).scalar())

        # 8. Total Refunds
        refund_query = (
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00")))
            .join(Transaction.category, isouter=True)
            .where(
                Category.name == "Refund",
                *filters,
            )
        )
        total_refunds = _to_decimal(self.session.execute(refund_query).scalar())

        # 9. Net Movement
        net_movement = total_income - total_expenses

        return FinancialSummary(
            total_transactions=total_transactions,
            total_income=total_income,
            total_expenses=total_expenses,
            net_movement=net_movement,
            categorized_count=categorized_count,
            uncategorized_count=uncategorized_count,
            review_required_count=review_required_count,
            total_transfers=total_transfers,
            total_refunds=total_refunds,
            start_date=start_date,
            end_date=end_date,
        )

    def get_category_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
    ) -> List[CategoryReportItem]:
        """Aggregate expenses, income, net amounts, and counts per category."""
        filters = self._build_filter_clauses(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            tx_type=tx_type,
            statement_id=statement_id,
        )

        # Aggregate per category
        query = (
            select(
                Transaction.category_id,
                func.coalesce(Category.name, "Needs Review").label("cat_name"),
                func.count(Transaction.id).label("tx_count"),
                func.coalesce(
                    func.sum(
                        case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=Decimal("0.00"))
                    ),
                    Decimal("0.00"),
                ).label("total_expenses"),
                func.coalesce(
                    func.sum(
                        case((Transaction.amount > 0, Transaction.amount), else_=Decimal("0.00"))
                    ),
                    Decimal("0.00"),
                ).label("total_income"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                or_(
                                    Transaction.review_status == ReviewStatus.PENDING,
                                    Category.name == "Needs Review",
                                    Transaction.category_id.is_(None),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("review_count"),
            )
            .join(Transaction.category, isouter=True)
            .where(*filters)
            .group_by(Transaction.category_id, Category.name)
            .order_by(func.sum(func.abs(Transaction.amount)).desc())
        )

        rows = self.session.execute(query).all()

        # Calculate overall expense total to derive percentages
        overall_expenses = sum((_to_decimal(r.total_expenses) for r in rows), Decimal("0.00"))

        results = []
        for r in rows:
            expenses = _to_decimal(r.total_expenses)
            income = _to_decimal(r.total_income)
            net_amt = income - expenses
            pct = (
                float(expenses / overall_expenses * 100)
                if overall_expenses > Decimal("0.00")
                else 0.0
            )

            results.append(
                CategoryReportItem(
                    category_id=r.category_id,
                    category_name=r.cat_name,
                    transaction_count=_to_int(r.tx_count),
                    total_expenses=expenses,
                    total_income=income,
                    net_amount=net_amt,
                    review_required_count=_to_int(r.review_count),
                    percentage_of_expenses=round(pct, 1),
                )
            )

        return results

    def get_monthly_trends(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        tx_type: Optional[str] = None,
        statement_id: Optional[int] = None,
    ) -> List[MonthlyTrendItem]:
        """Aggregate monthly income, expenses, and net movement over time."""
        filters = self._build_filter_clauses(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            tx_type=tx_type,
            statement_id=statement_id,
        )
        # Transactions must have a valid transaction date for monthly trends
        filters.append(Transaction.transaction_date.isnot(None))

        # Fetch all filtered transactions ordered by date for database-agnostic monthly grouping
        stmt = (
            select(
                Transaction.transaction_date,
                Transaction.amount,
                Category.name.label("cat_name"),
            )
            .join(Transaction.category, isouter=True)
            .where(*filters)
            .order_by(Transaction.transaction_date.asc())
        )
        rows = self.session.execute(stmt).all()

        monthly_buckets: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            tx_date: date = r.transaction_date
            month_key = tx_date.strftime("%Y-%m")
            if month_key not in monthly_buckets:
                monthly_buckets[month_key] = {
                    "count": 0,
                    "income": Decimal("0.00"),
                    "expenses": Decimal("0.00"),
                    "date": tx_date,
                }

            amt = _to_decimal(r.amount)
            cat_name = r.cat_name
            monthly_buckets[month_key]["count"] += 1

            if amt > 0 and (cat_name is None or cat_name not in self.NON_INCOME_CATEGORIES):
                monthly_buckets[month_key]["income"] += amt
            elif amt < 0 and (cat_name is None or cat_name not in self.NON_EXPENSE_CATEGORIES):
                monthly_buckets[month_key]["expenses"] += abs(amt)

        results: List[MonthlyTrendItem] = []
        for m_key in sorted(monthly_buckets.keys()):
            bucket = monthly_buckets[m_key]
            d = bucket["date"]
            label = d.strftime("%b %Y")
            inc = bucket["income"]
            exp = bucket["expenses"]
            net = inc - exp
            results.append(
                MonthlyTrendItem(
                    month_key=m_key,
                    month_label=label,
                    transaction_count=bucket["count"],
                    income=inc,
                    expenses=exp,
                    net=net,
                )
            )

        return results
