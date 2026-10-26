"""Secure CSV Export Service for LedgerLens transactions.

Features:
- Streamlined export of filtered transaction records matching user criteria
- Comprehensive spreadsheet formula injection protection (CSV Injection / CWE-1236)
- Preserves negative numeric monetary values and standard date formatting
- Stable sorting and UTF-8 output encoding
"""

import csv
from datetime import date, datetime
from decimal import Decimal
import io
from typing import Any, Iterable, List, Optional

from app.models.transaction import Transaction


DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_text_for_csv(val: Any) -> str:
    """Sanitize user-controlled text fields to prevent CSV formula injection.

    If a text value starts with '=', '+', '-', '@', tab, or carriage return
    (even with leading whitespace), prepends a single quote "'" to force
    spreadsheet applications (Excel, Calc, Google Sheets) to treat it as a literal string.

    CRITICAL SECURITY & DATA INTEGRITY RULE:
    This function must ONLY be applied to textual, user-controlled strings
    (e.g. descriptions, category names, reasons).
    It must NEVER be applied to raw numbers, monetary amounts, or date objects.
    """
    if val is None:
        return ""

    text = str(val)
    if text.startswith(("\t", "\r")):
        return f"'{text}"

    # Check first non-whitespace character for formula triggers
    stripped = text.lstrip(" \t\r\n")
    if stripped and stripped.startswith(DANGEROUS_FORMULA_PREFIXES):
        return f"'{text}"
    return text



def format_monetary_amount(amount: Any) -> str:
    """Format monetary decimal cleanly as standard numeric string.

    Legitimate negative numbers (e.g. -25.00) are NOT escaped with quotes,
    preserving numeric spreadsheet formulas, charting, and accounting functions.
    """
    if amount is None:
        return "0.00"
    if isinstance(amount, (int, float, Decimal)):
        return f"{Decimal(str(amount)):.2f}"
    try:
        return f"{Decimal(str(amount)):.2f}"
    except Exception:
        return "0.00"


def format_date(dt: Any) -> str:
    """Format date in ISO format YYYY-MM-DD."""
    if dt is None:
        return ""
    if isinstance(dt, (date, datetime)):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


class CsvExportService:
    """Service generating secure CSV exports of transaction records."""

    HEADERS = [
        "Transaction ID",
        "Date",
        "Original Description",
        "Normalized Description",
        "Amount",
        "Currency",
        "Debit",
        "Credit",
        "Category",
        "Transaction Type",
        "Confidence Score",
        "Review Status",
        "Manually Categorized",
        "Classification Reason",
        "Statement ID",
        "Statement Filename",
    ]

    @classmethod
    def export_transactions(cls, transactions: Iterable[Transaction]) -> str:
        """Export an iterable of transactions into a secure CSV string.

        Args:
            transactions: Iterable of Transaction ORM models with eagerly loaded category & statement.

        Returns:
            CSV formatted string with safe headers and sanitized text cells.
        """
        output = io.StringIO()
        # Use standard RFC 4180 CSV writer with excel dialect
        writer = csv.writer(output, dialect="excel", quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(cls.HEADERS)

        for tx in transactions:
            amt = Decimal(str(tx.amount)) if tx.amount is not None else Decimal("0.00")
            amt_str = format_monetary_amount(amt)

            # Separate debit (positive expense) and credit (positive income)
            debit_str = format_monetary_amount(abs(amt)) if amt < 0 else ""
            credit_str = format_monetary_amount(amt) if amt > 0 else ""

            cat_name = tx.category.name if tx.category else "Needs Review"
            stmt_name = tx.statement.original_filename if getattr(tx, "statement", None) else ""

            # Determine transaction type label
            if cat_name == "Internal Transfer":
                tx_type = "Transfer"
            elif amt > 0:
                tx_type = "Income"
            elif amt < 0:
                tx_type = "Expense"
            else:
                tx_type = "Zero"

            row = [
                tx.id,
                format_date(tx.transaction_date),
                sanitize_text_for_csv(tx.original_description),
                sanitize_text_for_csv(tx.normalized_description),
                amt_str,
                tx.currency or "USD",
                debit_str,
                credit_str,
                sanitize_text_for_csv(cat_name),
                tx_type,
                f"{float(tx.confidence_score or 0.0):.2f}",
                tx.review_status,
                "Yes" if tx.was_manually_categorized else "No",
                sanitize_text_for_csv(tx.classification_reason),
                tx.statement_id,
                sanitize_text_for_csv(stmt_name),
            ]
            writer.writerow(row)

        return output.getvalue()
