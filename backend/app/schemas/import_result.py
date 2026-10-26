"""Import result schemas and error models for statement processing.

Defines structured models for parsed records, categorized outputs,
row-level validation errors, and import statistics.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.transaction import CategorizationResult, TransactionInput


class RowError(BaseModel):
    """Structured validation error for an invalid statement row."""

    model_config = ConfigDict(frozen=True)

    row_number: int = Field(..., description="1-indexed row number in the CSV statement")
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable description of the error")
    field_name: Optional[str] = Field(default=None, description="Specific column or field causing failure")
    raw_data: Optional[str] = Field(default=None, description="Raw content of the offending cell or row")


class ImportWarning(BaseModel):
    """Structured warning for potential issues that do not discard the transaction."""

    model_config = ConfigDict(frozen=True)

    warning_code: str = Field(..., description="Machine-readable warning identifier")
    message: str = Field(..., description="Human-readable warning explanation")
    row_number: Optional[int] = Field(default=None, description="Affected primary row number")
    related_rows: List[int] = Field(default_factory=list, description="Associated row numbers (e.g., duplicates)")


class CategorizedTransaction(BaseModel):
    """Pairing of a parsed statement row with its categorization engine result."""

    model_config = ConfigDict(frozen=True)

    row_number: int = Field(..., description="1-indexed row number from CSV")
    transaction: TransactionInput = Field(..., description="Validated transaction model")
    result: CategorizationResult = Field(..., description="Categorization engine output")
    is_potential_duplicate: bool = Field(default=False, description="Flag indicating potential duplicate status")


class ImportResult(BaseModel):
    """Complete summary of a statement import operation."""

    model_config = ConfigDict(frozen=True)

    filename: Optional[str] = Field(default=None, description="Original filename if available")
    total_rows: int = Field(default=0, description="Total data rows encountered (excluding header)")
    valid_row_count: int = Field(default=0, description="Count of successfully parsed transactions")
    categorized_count: int = Field(default=0, description="Count of successfully categorized transactions")
    invalid_row_count: int = Field(default=0, description="Count of rejected invalid rows")
    duplicate_count: int = Field(default=0, description="Count of rows identified as potential duplicates")
    transactions: List[CategorizedTransaction] = Field(
        default_factory=list, description="List of valid categorized transactions"
    )
    errors: List[RowError] = Field(default_factory=list, description="Row-level and file-level errors encountered")
    warnings: List[ImportWarning] = Field(default_factory=list, description="Non-fatal warnings (e.g., duplicates)")

    @property
    def has_errors(self) -> bool:
        """Return True if any errors occurred during import."""
        return len(self.errors) > 0

    @property
    def is_success(self) -> bool:
        """Return True if at least one transaction was successfully parsed and no fatal errors aborted import."""
        return self.valid_row_count > 0 and (
            not any(e.error_code in {"EMPTY_FILE", "HEADER_ONLY", "MISSING_REQUIRED_COLUMNS", "FILE_TOO_LARGE"} for e in self.errors)
        )
