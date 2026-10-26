"""Standalone demonstration of the Phase 2 CSV Statement Import Pipeline.

Demonstrates reading, validating, duplicate checking, and categorizing
transactions from sample_data/sample_statement.csv without any database or web server.
"""

from pathlib import Path
import sys

from app.services.statement_parser import StatementParser


def main() -> None:
    # Resolve statement path relative to project root or current working dir
    possible_paths = [
        Path("sample_data/sample_statement.csv"),
        Path("../sample_data/sample_statement.csv"),
        Path(__file__).resolve().parent.parent / "sample_data" / "sample_statement.csv",
    ]

    sample_csv: Path | None = None
    for p in possible_paths:
        if p.exists():
            sample_csv = p
            break

    if sample_csv is None:
        print("Error: Could not locate sample_data/sample_statement.csv", file=sys.stderr)
        sys.exit(1)

    print("=" * 105)
    print(" LedgerLens -- Phase 2 CSV Statement Import & Categorization Pipeline")
    print("=" * 105)
    print(f"Loading statement file: {sample_csv.resolve()}\n")

    parser = StatementParser()
    result = parser.parse_file(sample_csv)

    print("--- IMPORT STATISTICS ---")
    print(f"Filename:               {result.filename}")
    print(f"Total Rows Encountered: {result.total_rows}")
    print(f"Valid Transactions:     {result.valid_row_count}")
    print(f"Categorized Count:      {result.categorized_count}")
    print(f"Invalid Rows Rejected:  {result.invalid_row_count}")
    print(f"Potential Duplicates:   {result.duplicate_count}")
    print(f"Overall Status:         {'SUCCESS' if result.is_success else 'FAILED'}\n")

    print("--- CATEGORIZED TRANSACTIONS ---")
    header = (
        f"{'Row':<4} | {'Date':<10} | {'Description':<32} | {'Amount':>10} | "
        f"{'Category':<16} | {'Conf':>5} | {'Review?':<7} | {'Dup?'}"
    )
    print(header)
    print("-" * len(header))

    for item in result.transactions:
        tx = item.transaction
        res = item.result
        date_str = tx.date.isoformat() if tx.date else "N/A"
        rev_str = "YES" if res.review_required else "No"
        dup_str = "YES" if item.is_potential_duplicate else "No"

        print(
            f"{item.row_number:<4} | {date_str:<10} | {tx.original_description[:32]:<32} | "
            f"{str(tx.amount):>10} | {res.category:<16} | {res.confidence_score:>5.2f} | "
            f"{rev_str:<7} | {dup_str}"
        )

    if result.warnings:
        print("\n--- WARNINGS & DUPLICATE ADVISORIES ---")
        for w in result.warnings:
            row_prefix = f"Row {w.row_number}: " if w.row_number else ""
            print(f"[{w.warning_code}] {row_prefix}{w.message}")

    if result.errors:
        print("\n--- ROW-LEVEL VALIDATION ERRORS ---")
        for err in result.errors:
            field_info = f" (field: '{err.field_name}')" if err.field_name else ""
            print(f"Row {err.row_number}: [{err.error_code}]{field_info} {err.message}")

    print("=" * 105)


if __name__ == "__main__":
    main()
