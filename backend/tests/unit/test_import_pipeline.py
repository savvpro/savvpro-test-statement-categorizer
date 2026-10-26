"""Unit tests for the end-to-end statement import and categorization pipeline."""

from decimal import Decimal
import io
from pathlib import Path
import pytest

from app.schemas.category import DefaultCategory
from app.services.statement_parser import StatementParser

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SAMPLE_STATEMENT = PROJECT_ROOT / "sample_data" / "sample_statement.csv"


def test_pipeline_with_primary_sample_statement(engine):
    """Test importing the primary sample_statement.csv through the full pipeline."""
    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(SAMPLE_STATEMENT)

    assert result.is_success is True
    assert result.total_rows == 18
    assert result.valid_row_count == 18
    assert result.categorized_count == 18
    assert result.invalid_row_count == 0
    assert result.duplicate_count == 2  # The 2 coffee entries on 2026-08-16

    # Verify categorization integration
    categories_found = {item.result.category for item in result.transactions}
    assert DefaultCategory.SOFTWARE.value in categories_found
    assert DefaultCategory.CLOUD_HOSTING.value in categories_found
    assert DefaultCategory.BUSINESS_INCOME.value in categories_found
    assert DefaultCategory.BANK_FEES.value in categories_found
    assert DefaultCategory.REFUND.value in categories_found
    assert DefaultCategory.REVERSAL.value in categories_found
    assert DefaultCategory.INTERNAL_TRANSFER.value in categories_found


def test_unknown_merchant_in_csv_receives_needs_review(engine):
    """Verify unrecognized merchant descriptions are flagged as Needs Review by the engine."""
    csv_data = "date,description,amount\n2026-08-01,MYSTERY STORE #991,-30.00\n"
    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.valid_row_count == 1
    item = result.transactions[0]
    assert item.result.category == DefaultCategory.NEEDS_REVIEW.value
    assert item.result.confidence_score == 0.0
    assert item.result.review_required is True


def test_original_description_is_preserved_intact_through_pipeline(engine):
    """Verify original description in transaction model is not altered during import and categorization."""
    raw_desc = "   Mixed Case   *#  Description   "
    csv_data = f'date,description,amount\n2026-08-01,"{raw_desc}",-15.00\n'

    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.valid_row_count == 1
    assert result.transactions[0].transaction.original_description == raw_desc
    # Normalized text is stored in result
    assert result.transactions[0].result.normalized_description == "MIXED CASE *# DESCRIPTION"


def test_multiple_invalid_rows_do_not_block_valid_rows(engine):
    """Verify invalid rows produce errors while all valid rows are categorized."""
    csv_data = (
        "date,description,amount\n"
        "2026-08-01,VALID ROW 1,-10.00\n"
        "not-a-date,INVALID DATE ROW,-20.00\n"
        "2026-08-02,VALID ROW 2,500.00\n"
        "2026-08-03,,INVALID EMPTY DESC\n"
        "2026-08-04,INVALID AMOUNT ROW,not-an-amount\n"
        "2026-08-05,VALID ROW 3,-30.00\n"
    )
    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.total_rows == 6
    assert result.valid_row_count == 3
    assert result.categorized_count == 3
    assert result.invalid_row_count == 3

    # Check errors
    err_codes = {e.error_code for e in result.errors}
    assert "INVALID_DATE" in err_codes
    assert "MISSING_DESCRIPTION" in err_codes
    assert "INVALID_AMOUNT" in err_codes

    # Check valid rows were processed
    valid_descriptions = [t.transaction.original_description for t in result.transactions]
    assert valid_descriptions == ["VALID ROW 1", "VALID ROW 2", "VALID ROW 3"]


def test_statistics_internal_consistency(engine):
    """Verify import result statistics sum up consistently."""
    csv_data = (
        "date,description,amount\n"
        "2026-08-01,ROW 1,-10.00\n"
        "bad-date,ROW 2,-10.00\n"
        "2026-08-01,ROW 1,-10.00\n"  # Duplicate of row 1
    )
    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.total_rows == 3
    assert result.valid_row_count == 2
    assert result.categorized_count == 2
    assert result.invalid_row_count == 1
    assert result.duplicate_count == 2
    assert result.valid_row_count + result.invalid_row_count == result.total_rows
