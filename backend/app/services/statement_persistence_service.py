"""Statement persistence orchestration service.

Binds the Phase 2 statement parser output to the MySQL database layer,
persisting statements, transactions, and audit events within an explicit atomic transaction.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import io
from sqlalchemy.orm import Session

from app.models.statement import StatementStatus
from app.schemas.import_result import ImportResult
from app.services.category_repository import CategoryRepository
from app.services.statement_parser import StatementParser
from app.services.statement_repository import StatementRepository
from app.services.transaction_repository import TransactionRepository


@dataclass(frozen=True)
class PersistedImportResult:
    """Summary of an import and database persistence operation."""

    statement_id: Optional[int]
    statement_status: str
    import_result: ImportResult
    stored_transaction_count: int


class StatementPersistenceService:
    """Orchestrates parsing, categorization, and atomic database persistence."""

    def __init__(
        self,
        session: Session,
        parser: Optional[StatementParser] = None,
    ) -> None:
        self.session = session
        self.parser = parser or StatementParser()
        self.statement_repo = StatementRepository(session)
        self.category_repo = CategoryRepository(session)
        self.transaction_repo = TransactionRepository(session)

    def process_and_persist(
        self,
        file_input: Union[str, Path, bytes, io.IOBase],
        filename: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> PersistedImportResult:
        """Parse statement CSV and persist valid transactions to MySQL in an atomic transaction."""
        # 1. Parse and categorize using Phase 2 pipeline
        import_result = self.parser.parse_file(file_input, filename=filename, encoding=encoding)
        return self.persist_import_result(import_result)

    def persist_import_result(self, import_result: ImportResult) -> PersistedImportResult:
        """Persist an existing ImportResult to the database atomically."""
        # Ensure default categories are seeded in the database
        self.category_repo.seed_default_categories()
        category_map = self.category_repo.get_category_map()

        safe_filename = import_result.filename or "statement.csv"

        # Determine statement status
        if not import_result.is_success and import_result.valid_row_count == 0:
            final_status = StatementStatus.FAILED
        elif import_result.has_errors:
            final_status = StatementStatus.COMPLETED_WITH_ERRORS
        else:
            final_status = StatementStatus.COMPLETED

        try:
            # Create statement record
            statement = self.statement_repo.create(
                original_filename=safe_filename,
                status=final_status,
                currency="USD",
            )

            stored_count = 0
            if import_result.valid_row_count > 0:
                for item in import_result.transactions:
                    tx_in = item.transaction
                    cat_res = item.result

                    # Resolve category ID from database
                    cat_record = category_map.get(cat_res.category)
                    cat_id = cat_record.id if cat_record else None

                    self.transaction_repo.create(
                        statement_id=statement.id,
                        transaction_input=tx_in,
                        categorization_result=cat_res,
                        category_id=cat_id,
                    )
                    stored_count += 1

                # Update transaction count
                self.statement_repo.update_status(
                    statement_id=statement.id,
                    status=final_status,
                    transaction_count=stored_count,
                )

            self.session.commit()

            return PersistedImportResult(
                statement_id=statement.id,
                statement_status=final_status,
                import_result=import_result,
                stored_transaction_count=stored_count,
            )
        except Exception:
            self.session.rollback()
            raise
