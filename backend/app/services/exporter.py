import csv
import io

from app.models.response import CategorizationResponse


class ExporterService:
    """Exports categorized transactions and tax summaries into clean, accountant-ready CSV format."""

    @classmethod
    def export_to_csv(cls, response: CategorizationResponse) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write Transactions Table Header
        writer.writerow([
            "Line #",
            "Date",
            "Raw Description",
            "Normalized Merchant",
            "Amount",
            "Type",
            "Category",
            "Confidence",
            "Reason",
            "Needs Review",
            "Is Refund",
            "Is Transfer",
            "Is Duplicate",
            "User Overridden",
        ])

        # Write Transaction Rows
        for tx in response.transactions:
            writer.writerow([
                tx.line_number,
                tx.date.isoformat(),
                tx.raw_description,
                tx.normalized_description,
                f"{tx.amount:.2f}",
                tx.transaction_type.value,
                tx.category,
                f"{tx.confidence:.2f}",
                tx.reason,
                "YES" if tx.needs_review else "NO",
                "YES" if tx.is_refund else "NO",
                "YES" if tx.is_transfer else "NO",
                "YES" if tx.is_duplicate else "NO",
                "YES" if tx.user_overridden else "NO",
            ])

        # Blank separating lines
        writer.writerow([])
        writer.writerow(["--- TAX SUMMARY BREAKDOWN ---"])
        writer.writerow(["Category", "Count", "Total Amount ($)", "% of Business Expenses"])

        for total in response.category_totals:
            writer.writerow([
                total.category,
                total.count,
                f"{total.total_amount:.2f}",
                f"{total.percentage_of_expenses:.1f}%",
            ])

        # Summary Totals
        writer.writerow([])
        writer.writerow(["--- OVERALL FINANCIAL METRICS ---"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Transactions", response.summary.total_transactions])
        writer.writerow(["Gross Income / Client Revenue ($)", f"{response.summary.total_income:.2f}"])
        writer.writerow(["Total Deductible Expenses ($)", f"{response.summary.total_expenses:.2f}"])
        writer.writerow(["Non-Taxable Transfers ($)", f"{response.summary.total_transfers:.2f}"])
        writer.writerow(["Expense Refunds / Reversals ($)", f"{response.summary.total_refunds:.2f}"])
        writer.writerow(["Items Needing Review", response.summary.needs_review_count])
        writer.writerow(["Review Completion Progress", f"{response.summary.review_progress_percent:.1f}%"])

        return output.getvalue()
