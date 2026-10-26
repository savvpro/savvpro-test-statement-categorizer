"""
In-Memory Store and Summary Calculation Engine.

Manages parsed statement transactions and provides recalculation of totals
whenever a transaction category is updated manually by the user.
"""

from typing import Dict, List, Optional
import uuid
from .models import (
    Category,
    CategorySummary,
    StatementSummary,
    Transaction,
    TransactionStatus,
    UploadResponse,
)


class StatementStore:
    def __init__(self):
        self.statement_id: Optional[str] = None
        self.filename: Optional[str] = None
        self.transactions: Dict[str, Transaction] = {}
        self.warnings: List[str] = []

    def clear(self):
        self.statement_id = None
        self.filename = None
        self.transactions.clear()
        self.warnings.clear()

    def set_statement(
        self, filename: str, transactions: List[Transaction], warnings: Optional[List[str]] = None
    ) -> UploadResponse:
        self.statement_id = f"stmt_{uuid.uuid4().hex[:10]}"
        self.filename = filename
        self.transactions = {tx.id: tx for tx in transactions}
        self.warnings = warnings or []
        summary = self.calculate_summary(list(self.transactions.values()))
        return UploadResponse(
            statement_id=self.statement_id,
            filename=self.filename,
            transactions=list(self.transactions.values()),
            summary=summary,
            warnings=self.warnings,
        )

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        return self.transactions.get(tx_id)

    def get_all_transactions(self) -> List[Transaction]:
        return list(self.transactions.values())

    def update_category(self, tx_id: str, new_category: Category) -> Transaction:
        if tx_id not in self.transactions:
            raise KeyError(f"Transaction with ID '{tx_id}' not found.")

        current = self.transactions[tx_id]
        updated = current.model_copy(
            update={
                "category": new_category,
                "confidence": 1.0,
                "status": (
                    TransactionStatus.NEEDS_REVIEW
                    if new_category == Category.NEEDS_REVIEW
                    else TransactionStatus.MANUAL
                ),
                "matched_rule": f"Manually verified/updated to '{new_category.value}' by user.",
                "is_reviewed": True,
            }
        )
        self.transactions[tx_id] = updated
        return updated

    def calculate_summary(self, transactions: Optional[List[Transaction]] = None) -> StatementSummary:
        tx_list = transactions if transactions is not None else list(self.transactions.values())

        total_income = 0.0
        total_expenses = 0.0
        total_refunds = 0.0
        transfers_count = 0
        transfers_total = 0.0
        needs_review_count = 0

        # Category breakdowns map
        breakdown_data: Dict[Category, Dict[str, float]] = {
            cat: {"count": 0, "amount": 0.0} for cat in Category
        }

        for tx in tx_list:
            amt = tx.amount
            cat = tx.category
            breakdown_data[cat]["count"] += 1

            if cat == Category.INCOME:
                total_income += max(amt, 0.0)
                breakdown_data[cat]["amount"] += max(amt, 0.0)
            elif cat == Category.REFUND:
                total_refunds += abs(amt)
                breakdown_data[cat]["amount"] += abs(amt)
            elif cat == Category.TRANSFER:
                transfers_count += 1
                transfers_total += abs(amt)
                breakdown_data[cat]["amount"] += abs(amt)
            elif cat == Category.NEEDS_REVIEW:
                needs_review_count += 1
                # If an uncertain transaction is an outflow, track its spending potential
                if amt < 0:
                    total_expenses += abs(amt)
                breakdown_data[cat]["amount"] += abs(amt)
            else:
                # Business expenses: Software, Travel, Meals, Office Supplies, Other Business Expense
                expense_val = abs(amt)
                total_expenses += expense_val
                breakdown_data[cat]["amount"] += expense_val

        # Net expenses = gross expenses - refunds (refunds offset deductible expenses)
        net_expenses = max(0.0, total_expenses - total_refunds)
        net_cashflow = total_income + total_refunds - total_expenses

        # Generate category summaries with percentage of deductible business expense
        category_summaries: List[CategorySummary] = []
        for cat in Category:
            count = int(breakdown_data[cat]["count"])
            tot = round(breakdown_data[cat]["amount"], 2)
            pct = 0.0
            if total_expenses > 0 and cat in [
                Category.SOFTWARE,
                Category.TRAVEL,
                Category.MEALS,
                Category.OFFICE_SUPPLIES,
                Category.OTHER_BUSINESS_EXPENSE,
            ]:
                pct = round((tot / total_expenses) * 100, 1)

            category_summaries.append(
                CategorySummary(
                    category=cat,
                    count=count,
                    total_amount=tot,
                    percentage=pct,
                )
            )

        return StatementSummary(
            total_transactions=len(tx_list),
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            total_refunds=round(total_refunds, 2),
            net_expenses=round(net_expenses, 2),
            net_cashflow=round(net_cashflow, 2),
            transfers_count=transfers_count,
            transfers_total=round(transfers_total, 2),
            needs_review_count=needs_review_count,
            category_breakdown=category_summaries,
        )


# Global store instance for local single-user session
store = StatementStore()
