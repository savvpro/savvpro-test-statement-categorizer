import csv
import io
from datetime import datetime
from decimal import Decimal
from app.brain.models import Transaction
from app.parsers.base import StatementParser

class CSVParser(StatementParser):
    """Expects columns: Date, Description, Amount"""

    def parse(self, file_bytes: bytes) -> list[Transaction]:
        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows: list[Transaction] = []
        for r in reader:
            rows.append(Transaction(
                date=self._date(r["Date"]),
                description=r["Description"].strip(),
                amount=Decimal(r["Amount"].strip()),
            ))
        return rows

    @staticmethod
    def _date(s: str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unrecognized date: {s}")