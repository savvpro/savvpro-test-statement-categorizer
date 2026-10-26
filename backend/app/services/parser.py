import csv
import re
from datetime import date, datetime
from typing import Optional
from app.models.transaction import RawTransaction, TransactionType


class StatementParseError(Exception):
    """Custom exception raised when statement parsing fails."""
    def __init__(self, message: str, line_number: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line_number = line_number


DATE_COLUMN_PATTERNS = [
    r"^(?:TRANS(?:ACTION)?[\s_]*)?DATE$",
    r"^POST(?:ING)?[\s_]*DATE$",
    r"^VALUE[\s_]*DATE$",
    r"^DATE[\s_]*POSTED$",
]

DESCRIPTION_COLUMN_PATTERNS = [
    r"^DESC(?:RIPTION)?$",
    r"^TRANSACTION[\s_]*DESC(?:RIPTION)?$",
    r"^DETAILS?$",
    r"^MERCHANT(?:[\s_]*NAME)?$",
    r"^PAYEE$",
    r"^MEMO$",
    r"^NARRATIVE$",
    r"^PARTICULARS?$",
    r"^TRANSACTION[\s_]*DETAILS?$",
]

AMOUNT_COLUMN_PATTERNS = [
    r"^AMOUNT$",
    r"^TRANS(?:ACTION)?[\s_]*AMOUNT$",
    r"^TOTAL[\s_]*AMOUNT$",
    r"^SUM$",
]

DEBIT_COLUMN_PATTERNS = [
    r"^DEBIT(?:S)?$",
    r"^WITHDRAWAL(?:S)?$",
    r"^CHARGES?$",
    r"^MONEY[\s_]*OUT$",
    r"^PAID[\s_]*OUT$",
]

CREDIT_COLUMN_PATTERNS = [
    r"^CREDIT(?:S)?$",
    r"^DEPOSIT(?:S)?$",
    r"^PAYMENTS?$",
    r"^MONEY[\s_]*IN$",
    r"^PAID[\s_]*IN$",
]

DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%m/%d/%y",
    "%d/%m/%y",
]


class StatementParser:
    """
    Robust CSV parser that handles real-world statement variations:
    - Multiple encodings (UTF-8, UTF-8-BOM, Latin-1, CP1252)
    - Auto-detects delimiters (comma, semicolon, tab, pipe)
    - Skips bank preamble/metadata lines before headers
    - Supports single Amount column or separate Debit/Credit columns
    - Cleans currency symbols, thousand commas, and DR/CR notations
    - Flexible date format recognition
    """

    @classmethod
    def parse_csv(cls, file_bytes: bytes, filename: str = "statement.csv") -> list[RawTransaction]:
        if not file_bytes or not file_bytes.strip():
            raise StatementParseError("Uploaded file is empty.", line_number=0)

        # Step 1: Decode using best-effort encodings
        text = cls._decode_bytes(file_bytes)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if not lines:
            raise StatementParseError("File contains no readable text or rows.", line_number=0)

        # Step 2: Auto-detect delimiter and find header row
        header_row_idx, col_map, delimiter = cls._find_header_and_delimiter(lines)
        if header_row_idx is None or col_map is None:
            raise StatementParseError(
                "Could not find valid statement column headers. Expected columns for Date, Description, and Amount (or Debit/Credit)."
            )

        # Step 3: Check whether dataset uses negative numbers for debits in Amount column
        has_negative_numbers = False
        if "amount" in col_map:
            amt_idx = col_map["amount"]
            sample_reader = csv.reader(lines[header_row_idx + 1 : header_row_idx + 35], delimiter=delimiter)
            for r in sample_reader:
                if len(r) > amt_idx:
                    c_val = r[amt_idx].strip()
                    if "-" in c_val or "(" in c_val or "DR" in c_val.upper():
                        has_negative_numbers = True
                        break

        # Step 4: Parse transaction rows
        transactions: list[RawTransaction] = []
        reader = csv.reader(lines[header_row_idx + 1 :], delimiter=delimiter)

        for offset, row in enumerate(reader):
            curr_line_num = header_row_idx + 2 + offset
            if not row or all(c.strip() == "" for c in row):
                continue  # skip blank lines

            # Skip footer/summary lines
            joined_row = " ".join(row).lower()
            if any(term in joined_row for term in ["total", "closing balance", "opening balance", "ending balance"]):
                continue

            try:
                tx = cls._parse_row(row, col_map, curr_line_num, has_negative_numbers)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                raise StatementParseError(
                    f"Error parsing row at line {curr_line_num}: {str(e)}",
                    line_number=curr_line_num,
                ) from e

        if not transactions:
            raise StatementParseError("No valid transaction rows found in statement.")

        return transactions

    @staticmethod
    def _decode_bytes(file_bytes: bytes) -> str:
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
        for enc in encodings:
            try:
                return file_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="replace")

    @classmethod
    def _find_header_and_delimiter(
        cls, lines: list[str]
    ) -> tuple[Optional[int], Optional[dict[str, int]], str]:
        candidates = [",", ";", "\t", "|"]
        for idx, line in enumerate(lines[:15]):
            for delim in candidates:
                tokens = [t.strip().strip('"').strip("'") for t in line.split(delim)]
                if len(tokens) >= 2:
                    col_map = cls._match_columns(tokens)
                    if col_map:
                        return idx, col_map, delim
        return None, None, ","

    @classmethod
    def _match_columns(cls, tokens: list[str]) -> Optional[dict[str, int]]:
        date_idx: Optional[int] = None
        desc_idx: Optional[int] = None
        amount_idx: Optional[int] = None
        debit_idx: Optional[int] = None
        credit_idx: Optional[int] = None

        for idx, col in enumerate(tokens):
            norm_col = col.strip()
            if not norm_col:
                continue

            if date_idx is None and any(re.match(p, norm_col, re.IGNORECASE) for p in DATE_COLUMN_PATTERNS):
                date_idx = idx
            elif desc_idx is None and any(re.match(p, norm_col, re.IGNORECASE) for p in DESCRIPTION_COLUMN_PATTERNS):
                desc_idx = idx
            elif amount_idx is None and any(re.match(p, norm_col, re.IGNORECASE) for p in AMOUNT_COLUMN_PATTERNS):
                amount_idx = idx
            elif debit_idx is None and any(re.match(p, norm_col, re.IGNORECASE) for p in DEBIT_COLUMN_PATTERNS):
                debit_idx = idx
            elif credit_idx is None and any(re.match(p, norm_col, re.IGNORECASE) for p in CREDIT_COLUMN_PATTERNS):
                credit_idx = idx

        if date_idx is not None and desc_idx is not None:
            if amount_idx is not None:
                return {"date": date_idx, "desc": desc_idx, "amount": amount_idx}
            if debit_idx is not None or credit_idx is not None:
                return {
                    "date": date_idx,
                    "desc": desc_idx,
                    "debit": debit_idx if debit_idx is not None else -1,
                    "credit": credit_idx if credit_idx is not None else -1,
                }
        return None

    @classmethod
    def _parse_row(
        cls,
        row: list[str],
        col_map: dict[str, int],
        line_num: int,
        has_negative_numbers: bool,
    ) -> Optional[RawTransaction]:
        max_idx = max(col_map.values())
        if len(row) <= max_idx:
            return None

        # 1. Date
        raw_date = row[col_map["date"]].strip()
        parsed_date = cls._parse_date(raw_date, line_num)

        # 2. Description
        raw_desc = row[col_map["desc"]].strip()
        if not raw_desc:
            raw_desc = "UNKNOWN DESCRIPTION"

        # 3. Amount & Type
        if "amount" in col_map:
            raw_amt_str = row[col_map["amount"]].strip()
            amount, tx_type = cls._clean_single_amount(raw_amt_str, line_num, has_negative_numbers)
        else:
            debit_idx = col_map.get("debit", -1)
            credit_idx = col_map.get("credit", -1)
            raw_debit = row[debit_idx].strip() if debit_idx >= 0 and debit_idx < len(row) else ""
            raw_credit = row[credit_idx].strip() if credit_idx >= 0 and credit_idx < len(row) else ""
            amount, tx_type = cls._clean_split_amount(raw_debit, raw_credit, line_num)

        tx_id = f"tx_{line_num}_{parsed_date.strftime('%Y%m%d')}_{abs(int(amount * 100))}"

        return RawTransaction(
            id=tx_id,
            line_number=line_num,
            date=parsed_date,
            description=raw_desc,
            amount=amount,
            transaction_type=tx_type,
            currency="USD",
        )

    @classmethod
    def _parse_date(cls, raw: str, line_num: int) -> date:
        cleaned = raw.strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format '{raw}' at line {line_num}")

    @classmethod
    def _clean_single_amount(
        cls, raw_str: str, line_num: int, has_negative_numbers: bool = False
    ) -> tuple[float, TransactionType]:
        val = raw_str.strip()
        if not val:
            raise ValueError(f"Missing amount value at line {line_num}")

        is_explicit_debit = False
        is_explicit_credit = False

        if re.search(r"\bDR\b", val, re.IGNORECASE):
            is_explicit_debit = True
        elif re.search(r"\bCR\b", val, re.IGNORECASE):
            is_explicit_credit = True

        if val.startswith("(") and val.endswith(")"):
            is_explicit_debit = True
            val = val[1:-1]

        if "-" in val:
            is_explicit_debit = True
            val = val.replace("-", "")
        if "+" in val:
            is_explicit_credit = True
            val = val.replace("+", "")

        val = re.sub(r"[^\d.,]", "", val)

        if "," in val and "." in val:
            val = val.replace(",", "")
        elif "," in val and "." not in val:
            parts = val.split(",")
            if len(parts) == 2 and len(parts[1]) in (2, 3):
                val = parts[0] + "." + parts[1]
            else:
                val = val.replace(",", "")

        try:
            amt = float(val)
        except ValueError:
            raise ValueError(f"Invalid numeric amount '{raw_str}' at line {line_num}")

        if is_explicit_credit:
            return amt, TransactionType.CREDIT
        if is_explicit_debit:
            return amt, TransactionType.DEBIT

        # In signed bank statements (statements that contain explicit negative amounts for debits),
        # an unsigned positive amount is CREDIT (incoming money/deposit).
        if has_negative_numbers:
            return amt, TransactionType.CREDIT

        # In standard positive-only credit card statements, all listed purchase amounts are DEBIT (spending).
        return amt, TransactionType.DEBIT

    @classmethod
    def _clean_split_amount(
        cls, raw_debit: str, raw_credit: str, line_num: int
    ) -> tuple[float, TransactionType]:
        debit_val = re.sub(r"[^\d.,]", "", raw_debit.strip()) if raw_debit else ""
        credit_val = re.sub(r"[^\d.,]", "", raw_credit.strip()) if raw_credit else ""

        if debit_val and debit_val not in ["0", "0.00"]:
            debit_val = debit_val.replace(",", "")
            return float(debit_val), TransactionType.DEBIT

        if credit_val and credit_val not in ["0", "0.00"]:
            credit_val = credit_val.replace(",", "")
            return float(credit_val), TransactionType.CREDIT

        raise ValueError(f"Both debit and credit amounts are empty or zero at line {line_num}")
