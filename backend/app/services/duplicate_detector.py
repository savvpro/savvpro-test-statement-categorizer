"""Duplicate detection service for imported statements.

Identifies potential duplicate transactions within the same statement
based on fingerprinting (date, normalized description, exact amount, and currency).
Preserves all transactions without automatic deletion or merging.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.import_result import ImportWarning
from app.schemas.transaction import TransactionInput
from app.services.transaction_normalizer import normalize_description


class DuplicateDetector:
    """Service to detect potential duplicate transactions within an imported statement."""

    @staticmethod
    def compute_fingerprint(transaction: TransactionInput) -> str:
        """Generate a deterministic fingerprint for transaction duplicate matching.

        Fingerprint components:
        - Date in ISO format (or 'NO_DATE' if None)
        - Normalized uppercase description
        - Exact Decimal amount formatted with high fidelity
        - Currency code (normalized uppercase)

        Args:
            transaction: The TransactionInput instance.

        Returns:
            A unique fingerprint string for comparison.
        """
        date_str = transaction.date.isoformat() if transaction.date else "NO_DATE"
        norm_desc = normalize_description(transaction.original_description)
        # Preserve exact Decimal representation
        amt_str = str(transaction.amount)
        curr_str = (transaction.currency or "").strip().upper()

        return f"{date_str}|{norm_desc}|{amt_str}|{curr_str}"

    def find_duplicates(
        self, parsed_rows: List[Tuple[int, TransactionInput]]
    ) -> Tuple[Set[int], List[ImportWarning]]:
        """Identify potential duplicate rows within the provided parsed transactions.

        Args:
            parsed_rows: List of tuples (row_number, TransactionInput).

        Returns:
            A tuple of:
            - Set of row_numbers that are part of a duplicate group.
            - List of ImportWarning objects detailing each duplicate occurrence.
        """
        fingerprint_map: Dict[str, List[int]] = defaultdict(list)

        for row_num, tx in parsed_rows:
            fp = self.compute_fingerprint(tx)
            fingerprint_map[fp].append(row_num)

        duplicate_row_numbers: Set[int] = set()
        warnings: List[ImportWarning] = []

        for fp, row_nums in fingerprint_map.items():
            if len(row_nums) > 1:
                duplicate_row_numbers.update(row_nums)
                for r in row_nums:
                    other_rows = [other for other in row_nums if other != r]
                    warnings.append(
                        ImportWarning(
                            warning_code="POTENTIAL_DUPLICATE",
                            message=(
                                f"Row {r} has identical date, description, and amount to "
                                f"row(s) {', '.join(map(str, other_rows))}. Please review to verify whether "
                                "this is a legitimate repeated transaction or an accidental duplicate entry."
                            ),
                            row_number=r,
                            related_rows=other_rows,
                        )
                    )

        return duplicate_row_numbers, warnings
