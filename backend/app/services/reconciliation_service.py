"""Statement reconciliation service for LedgerLens.

Provides statement-level and batch reconciliation auditing:
- Stored transaction counts vs statement totals
- Total credits (deposits) and debits (withdrawals)
- Net movement across statements
- Categorization and review status audit
- Transfer, refund, and reversal tracking
- Optional balance reconciliation (opening balance + net movement == closing balance)
- Read-only calculations preserving data integrity
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction
from app.services.dashboard_service import _to_decimal, _to_int


@dataclass(frozen=True)
class StatementReconciliationSummary:
    """Detailed reconciliation breakdown for a single statement."""

    statement_id: int
    original_filename: str
    status: str
    currency: str
    created_at: datetime
    transaction_count: int
    total_credits: Decimal  # Positive transactions
    total_debits: Decimal  # Positive sum of negative transactions
    net_movement: Decimal  # credits - debits
    transfers_total: Decimal
    transfers_count: int
    refunds_total: Decimal
    refunds_count: int
    reversals_total: Decimal
    reversals_count: int
    reviewed_count: int
    pending_count: int
    needs_review_count: int
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    expected_closing_balance: Optional[Decimal] = None
    discrepancy: Optional[Decimal] = None
    is_balanced: Optional[bool] = None


class ReconciliationService:
    """Service providing statement reconciliation metrics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def reconcile_statement(
        self,
        statement_id: int,
        opening_balance: Optional[Decimal] = None,
        closing_balance: Optional[Decimal] = None,
    ) -> Optional[StatementReconciliationSummary]:
        """Perform reconciliation audit for a specific statement."""
        statement = self.session.get(Statement, statement_id)
        if not statement:
            return None

        # Fetch transaction aggregations for this statement
        agg_stmt = (
            select(
                func.count(Transaction.id).label("tx_count"),
                func.coalesce(
                    func.sum(case((Transaction.amount > 0, Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("credits"),
                func.coalesce(
                    func.sum(
                        case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=Decimal("0.00"))
                    ),
                    Decimal("0.00"),
                ).label("debits"),
                func.coalesce(
                    func.sum(
                        case(
                            (Category.name == "Internal Transfer", func.abs(Transaction.amount)),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ).label("transfers_total"),
                func.coalesce(
                    func.sum(case((Category.name == "Internal Transfer", 1), else_=0)),
                    0,
                ).label("transfers_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (Category.name == "Refund", Transaction.amount),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ).label("refunds_total"),
                func.coalesce(
                    func.sum(case((Category.name == "Refund", 1), else_=0)),
                    0,
                ).label("refunds_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (Category.name == "Reversal", func.abs(Transaction.amount)),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ).label("reversals_total"),
                func.coalesce(
                    func.sum(case((Category.name == "Reversal", 1), else_=0)),
                    0,
                ).label("reversals_count"),
                func.coalesce(
                    func.sum(case((Transaction.review_status == ReviewStatus.REVIEWED, 1), else_=0)),
                    0,
                ).label("reviewed_count"),
                func.coalesce(
                    func.sum(case((Transaction.review_status == ReviewStatus.PENDING, 1), else_=0)),
                    0,
                ).label("pending_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                or_(
                                    Transaction.category_id.is_(None),
                                    Category.name == "Needs Review",
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("needs_review_count"),
            )
            .join(Transaction.category, isouter=True)
            .where(Transaction.statement_id == statement_id)
        )

        res = self.session.execute(agg_stmt).one()

        tx_count = _to_int(res.tx_count)
        credits = _to_decimal(res.credits)
        debits = _to_decimal(res.debits)
        net_mov = credits - debits

        expected_closing = None
        discrepancy = None
        is_balanced = None

        if opening_balance is not None and closing_balance is not None:
            expected_closing = opening_balance + net_mov
            discrepancy = closing_balance - expected_closing
            is_balanced = (discrepancy == Decimal("0.00"))

        return StatementReconciliationSummary(
            statement_id=statement.id,
            original_filename=statement.original_filename,
            status=statement.status,
            currency=statement.currency or "USD",
            created_at=statement.created_at,
            transaction_count=tx_count,
            total_credits=credits,
            total_debits=debits,
            net_movement=net_mov,
            transfers_total=_to_decimal(res.transfers_total),
            transfers_count=_to_int(res.transfers_count),
            refunds_total=_to_decimal(res.refunds_total),
            refunds_count=_to_int(res.refunds_count),
            reversals_total=_to_decimal(res.reversals_total),
            reversals_count=_to_int(res.reversals_count),
            reviewed_count=_to_int(res.reviewed_count),
            pending_count=_to_int(res.pending_count),
            needs_review_count=_to_int(res.needs_review_count),
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            expected_closing_balance=expected_closing,
            discrepancy=discrepancy,
            is_balanced=is_balanced,
        )

    def reconcile_all_statements(self) -> List[StatementReconciliationSummary]:
        """Generate reconciliation summaries across all imported statements."""
        stmt_query = (
            select(Statement)
            .order_by(Statement.created_at.desc(), Statement.id.desc())
        )
        statements = list(self.session.execute(stmt_query).scalars().all())

        results = []
        for s in statements:
            rec = self.reconcile_statement(s.id)
            if rec:
                results.append(rec)
        return results
