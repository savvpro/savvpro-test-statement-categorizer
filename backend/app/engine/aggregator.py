from typing import List, Dict
from ..models.schemas import (
    Transaction,
    CategoryName,
    TaxDeductibility,
    CategorySummary,
    StatementSummary
)


class StatementAggregator:
    """
    Computes financial summaries, category aggregations, and tax deduction metrics.
    """

    @classmethod
    def calculate_summary(cls, transactions: List[Transaction]) -> StatementSummary:
        total_tx = len(transactions)
        if total_tx == 0:
            return StatementSummary(
                total_transactions=0,
                total_income=0.0,
                total_expenses=0.0,
                net_tax_deductible_expenses=0.0,
                total_refunds=0.0,
                transfers_excluded=0.0,
                needs_review_count=0,
                accuracy_rate=100.0,
                categories=[]
            )

        total_income = 0.0
        total_expenses = 0.0
        total_refunds = 0.0
        transfers_excluded = 0.0
        needs_review_count = 0
        net_tax_deductible = 0.0

        # Group by category
        category_map: Dict[CategoryName, Dict[str, Any]] = {}
        for cat in CategoryName:
            category_map[cat] = {
                "total_amount": 0.0,
                "count": 0,
                "tax_status": TaxDeductibility.FULLY_DEDUCTIBLE
            }

        for tx in transactions:
            amt = abs(tx.amount)

            if tx.needs_review or tx.category == CategoryName.NEEDS_REVIEW:
                needs_review_count += 1

            if tx.category == CategoryName.GROSS_INCOME:
                total_income += amt
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.TAXABLE_INCOME

            elif tx.category == CategoryName.INTERNAL_TRANSFER:
                transfers_excluded += amt
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.NON_DEDUCTIBLE

            elif tx.category == CategoryName.REFUND_CREDIT:
                total_refunds += amt
                # Reduces taxable deductions
                net_tax_deductible -= amt
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.EXPENSE_OFFSET

            elif tx.category == CategoryName.MEALS_ENTERTAINMENT:
                total_expenses += amt
                # 50% deduction rule for business meals
                net_tax_deductible += (amt * 0.50)
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.PARTIALLY_DEDUCTIBLE

            elif tx.category == CategoryName.NEEDS_REVIEW:
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.PENDING_REVIEW

            else:
                # Fully deductible standard business expense
                total_expenses += amt
                net_tax_deductible += amt
                category_map[tx.category]["total_amount"] += amt
                category_map[tx.category]["count"] += 1
                category_map[tx.category]["tax_status"] = TaxDeductibility.FULLY_DEDUCTIBLE

        # Calculate category summaries and percentages
        cat_summaries: List[CategorySummary] = []
        for cat, data in category_map.items():
            if data["count"] > 0:
                pct = 0.0
                if total_expenses > 0 and cat not in [CategoryName.GROSS_INCOME, CategoryName.INTERNAL_TRANSFER]:
                    pct = round((data["total_amount"] / total_expenses) * 100, 1)

                cat_summaries.append(
                    CategorySummary(
                        category=cat,
                        total_amount=round(data["total_amount"], 2),
                        count=data["count"],
                        tax_status=data["tax_status"],
                        percentage_of_expenses=pct
                    )
                )

        # Sort categories by total amount descending
        cat_summaries.sort(key=lambda x: x.total_amount, reverse=True)

        accuracy_rate = round(((total_tx - needs_review_count) / total_tx) * 100, 1)

        return StatementSummary(
            total_transactions=total_tx,
            total_income=round(total_income, 2),
            total_expenses=round(total_expenses, 2),
            net_tax_deductible_expenses=round(max(0.0, net_tax_deductible), 2),
            total_refunds=round(total_refunds, 2),
            transfers_excluded=round(transfers_excluded, 2),
            needs_review_count=needs_review_count,
            accuracy_rate=accuracy_rate,
            categories=cat_summaries
        )
