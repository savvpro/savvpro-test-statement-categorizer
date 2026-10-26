import csv
import io
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from ..models.schemas import TransactionType


class StatementCSVParser:
    """
    Robust CSV parser that detects and normalizes bank and credit card statement formats.
    Handles:
    - Multiple column naming styles (Date, Post Date, Description, Payee, Memo, Amount, Debit, Credit)
    - Currency symbols ($), commas (1,234.56), negative formats (-$50 or ($50.00))
    - Flexible date formats (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, Mon DD YYYY)
    """

    DATE_HEADERS = ["date", "posting date", "transaction date", "post date", "trans date", "txn date"]
    DESC_HEADERS = ["description", "payee", "memo", "merchant", "details", "transaction details", "name"]
    AMOUNT_HEADERS = ["amount", "total", "net"]
    DEBIT_HEADERS = ["debit", "withdrawal", "outflow", "spend", "charge"]
    CREDIT_HEADERS = ["credit", "deposit", "inflow", "payment"]

    @classmethod
    def parse_csv_content(cls, content: str) -> List[Dict[str, Any]]:
        """
        Parses CSV string content and returns a list of raw transaction dicts:
        [{'date': 'YYYY-MM-DD', 'description': '...', 'amount': float, 'type': TransactionType}]
        """
        lines = content.strip().splitlines()
        if not lines:
            return []

        # Find the header row
        header_index = 0
        reader = csv.reader(lines)
        rows = list(reader)

        header_row = None
        for i, row in enumerate(rows):
            clean_cells = [c.strip().lower() for c in row if c.strip()]
            if any(h in clean_cells for h in cls.DATE_HEADERS) and (
                any(h in clean_cells for h in cls.DESC_HEADERS) or
                any(h in clean_cells for h in cls.AMOUNT_HEADERS + cls.DEBIT_HEADERS)
            ):
                header_row = [c.strip().lower() for c in row]
                header_index = i
                break

        if header_row is None:
            # Fallback: Assume first row is header if contains letters, else positional
            header_row = [c.strip().lower() for c in rows[0]]
            header_index = 0

        # Map column positions
        date_col = cls._find_col(header_row, cls.DATE_HEADERS)
        desc_col = cls._find_col(header_row, cls.DESC_HEADERS)
        amount_col = cls._find_col(header_row, cls.AMOUNT_HEADERS)
        debit_col = cls._find_col(header_row, cls.DEBIT_HEADERS)
        credit_col = cls._find_col(header_row, cls.CREDIT_HEADERS)

        # Fallback positional guesses if header names were absent
        if date_col is None:
            date_col = 0
        if desc_col is None:
            desc_col = 1
        if amount_col is None and debit_col is None and credit_col is None:
            amount_col = 2 if len(header_row) > 2 else 1

        parsed_records: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(rows[header_index + 1:], start=header_index + 1):
            if not row or all(not str(cell).strip() for cell in row):
                continue

            # Extract date
            raw_date = row[date_col].strip() if date_col < len(row) else ""
            normalized_date = cls._normalize_date(raw_date)

            # Extract description
            description = row[desc_col].strip() if desc_col < len(row) else "Unknown Transaction"

            # Extract amount and determine DEBIT vs CREDIT
            amount, tx_type = cls._extract_amount(row, amount_col, debit_col, credit_col)

            # Skip header repeats or invalid empty rows
            if not description and amount == 0.0:
                continue

            parsed_records.append({
                "date": normalized_date,
                "description": description,
                "amount": amount,
                "type": tx_type
            })

        return parsed_records

    @staticmethod
    def _find_col(headers: List[str], target_keywords: List[str]) -> Optional[int]:
        for i, header in enumerate(headers):
            for kw in target_keywords:
                if kw in header:
                    return i
        return None

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")

        clean = date_str.strip()
        formats = [
            "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y",
            "%Y/%m/%d", "%b %d, %Y", "%d-%b-%Y", "%d %b %Y",
            "%m/%d/%y", "%d/%m/%y"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(clean, fmt)
                # Handle 2-digit years if past 2030
                if dt.year < 1970:
                    dt = dt.replace(year=dt.year + 100)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If parsing fails, return sanitized string or today
        return clean

    @classmethod
    def _extract_amount(
        cls,
        row: List[str],
        amount_col: Optional[int],
        debit_col: Optional[int],
        credit_col: Optional[int]
    ) -> Tuple[float, TransactionType]:
        """
        Returns (amount, TransactionType)
        Conventions:
        - Outflows / Expenses: positive float, DEBIT
        - Inflows / Refunds / Incomes: negative float or positive credit, CREDIT
        """
        # Case A: Separate Debit and Credit columns
        if debit_col is not None and credit_col is not None:
            debit_val = cls._clean_number(row[debit_col]) if debit_col < len(row) else 0.0
            credit_val = cls._clean_number(row[credit_col]) if credit_col < len(row) else 0.0

            if debit_val > 0:
                return (debit_val, TransactionType.DEBIT)
            elif credit_val > 0:
                return (-credit_val, TransactionType.CREDIT)

        # Case B: Single Amount column
        if amount_col is not None and amount_col < len(row):
            raw_val = row[amount_col]
            num = cls._clean_number(raw_val)

            # Bank statements often use negative for expense or positive for expense
            # Check for explicitly signed strings
            is_parenthesized = "(" in raw_val and ")" in raw_val
            is_explicit_neg = "-" in raw_val or is_parenthesized

            if is_explicit_neg:
                # Typically negative in checking statements means expense, or in credit card it means payment
                return (abs(num), TransactionType.DEBIT)
            else:
                return (num, TransactionType.DEBIT)

        return (0.0, TransactionType.DEBIT)

    @staticmethod
    def _clean_number(val: str) -> float:
        if not val:
            return 0.0
        cleaned = re.sub(r"[^\d.-]", "", val.strip())
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
