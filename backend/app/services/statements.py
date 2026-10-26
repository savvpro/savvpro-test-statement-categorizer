"""Use-cases: upload a statement, correct a row, export results."""

from __future__ import annotations

import csv
import io
import re
import threading
import uuid
from datetime import UTC, datetime

from app.brain.categories import CATEGORIES, NEEDS_REVIEW
from app.brain.classifier import Classifier
from app.brain.pipeline import categorize
from app.config import Settings
from app.domain.models import (
    Convention,
    Flag,
    ParsedStatement,
    SourceFormat,
    Statement,
    Status,
    Transaction,
)
from app.errors import FileProblem, InvalidCategory, NotFound
from app.parsing.camt053_reader import read_camt053
from app.parsing.csv_reader import read_csv
from app.parsing.detect import detect_format
from app.parsing.mt940_reader import read_mt940
from app.parsing.ofx_reader import read_ofx
from app.parsing.pdf_reader import read_pdf
from app.parsing.xlsx_reader import read_xlsx
from app.storage.repository import StatementRepository
from app.storage.user_rules import UserRuleStore

_FILENAME_UNSAFE = re.compile(r"[^\w.\- ()]+")
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def clean_filename(name: str | None) -> str:
    base = (name or "statement").replace("\\", "/").rsplit("/", 1)[-1]
    base = _FILENAME_UNSAFE.sub("_", base).strip(" ._")[:120]
    return base or "statement"


class StatementService:
    def __init__(
        self,
        settings: Settings,
        repository: StatementRepository,
        classifier: Classifier,
        user_rules: UserRuleStore,
    ):
        self._settings = settings
        self._repository = repository
        self._classifier = classifier
        self._user_rules = user_rules
        self._correction_lock = threading.Lock()

    # -- upload ---------------------------------------------------------------------------

    def upload(
        self, filename: str | None, data: bytes, requested_convention: Convention | None
    ) -> Statement:
        safe_name = clean_filename(filename)
        source, warnings = detect_format(safe_name, data)
        parsed = self._parse(source, data)
        warnings = [*warnings, *parsed.warnings]

        if not parsed.rows:
            detail = ""
            if parsed.rejected:
                detail = (
                    f" {len(parsed.rejected)} line(s) were rejected, "
                    f"for example: {parsed.rejected[0].reason}."
                )
            raise FileProblem(
                f"No transactions could be read from this file.{detail}",
                code="no_transactions_found",
            )

        result = categorize(parsed, self._classifier, self._settings, requested_convention)
        statement = Statement(
            id=uuid.uuid4().hex[:12],
            filename=safe_name,
            currency=result.currency,
            created_at=datetime.now(UTC),
            source_format=source,
            convention=result.convention,
            transactions=tuple(result.transactions),
            rejected_rows=tuple(parsed.rejected),
            warnings=tuple([*warnings, *result.warnings]),
        )
        self._repository.save(statement)
        return statement

    def _parse(self, source: SourceFormat, data: bytes) -> ParsedStatement:
        s = self._settings
        if source is SourceFormat.PDF:
            return read_pdf(data, max_rows=s.max_rows, max_pages=s.max_pdf_pages)
        if source is SourceFormat.XLSX:
            return read_xlsx(data, max_rows=s.max_rows)
        if source is SourceFormat.OFX:
            return read_ofx(data, max_rows=s.max_rows)
        if source is SourceFormat.CAMT053:
            return read_camt053(data, max_rows=s.max_rows)
        if source is SourceFormat.MT940:
            return read_mt940(data, max_rows=s.max_rows)
        return read_csv(data, max_rows=s.max_rows)

    # -- reads ----------------------------------------------------------------------------

    def get(self, statement_id: str) -> Statement:
        statement = self._repository.get(statement_id)
        if statement is None:
            raise NotFound("That statement was not found. It may have expired; upload it again.")
        return statement

    # -- corrections ----------------------------------------------------------------------

    def correct(
        self, statement_id: str, txn_id: str, category_id: str, apply_to_similar: bool
    ) -> tuple[Statement, int]:
        category = CATEGORIES.get(category_id)
        if category is None or category_id == NEEDS_REVIEW:
            raise InvalidCategory(f"{category_id!r} is not a category you can assign.")

        with self._correction_lock:
            statement = self.get(statement_id)
            target = next((t for t in statement.transactions if t.id == txn_id), None)
            if target is None:
                raise NotFound(
                    "That transaction was not found in this statement.",
                    code="transaction_not_found",
                )

            changed: dict[str, str] = {txn_id: f"Set manually to {category.name}"}
            if apply_to_similar and target.merchant:
                for t in statement.transactions:
                    if (
                        t.id != txn_id
                        and t.merchant == target.merchant
                        and t.status is not Status.USER_CORRECTED
                    ):
                        changed[t.id] = (
                            f"Applied from your correction of line {target.line} "
                            f"({target.merchant!r})"
                        )
                self._user_rules.set(target.merchant, category_id)
            # A refund follows the purchase it reverses.
            for t in statement.transactions:
                if t.refund_of in changed and t.id not in changed:
                    changed[t.id] = "Follows the purchase it refunds"

            updated = tuple(
                _apply_correction(t, category_id, changed[t.id]) if t.id in changed else t
                for t in statement.transactions
            )
            new_statement = Statement(
                id=statement.id,
                filename=statement.filename,
                currency=statement.currency,
                created_at=statement.created_at,
                source_format=statement.source_format,
                convention=statement.convention,
                transactions=updated,
                rejected_rows=statement.rejected_rows,
                warnings=statement.warnings,
            )
            self._repository.save(new_statement)
            return new_statement, len(changed)

    # -- export ---------------------------------------------------------------------------

    def export_csv(self, statement_id: str) -> str:
        statement = self.get(statement_id)
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(
            [
                "date",
                "description",
                "merchant",
                "amount",
                "currency",
                "category",
                "status",
                "confidence",
                "flags",
                "reasons",
            ]
        )
        for t in statement.transactions:
            writer.writerow(
                [
                    t.date.isoformat(),
                    _safe_cell(t.description),
                    _safe_cell(t.merchant),
                    f"{t.amount:.2f}",
                    t.currency,
                    t.category_name,
                    t.status.value,
                    f"{t.confidence:.2f}",
                    "; ".join(f.value for f in t.flags),
                    _safe_cell(" | ".join(t.reasons)),
                ]
            )
        return out.getvalue()


def _apply_correction(t: Transaction, category_id: str, reason: str) -> Transaction:
    category = CATEGORIES[category_id]
    flags = tuple(f for f in t.flags if f is not Flag.AMBIGUOUS_MERCHANT)
    return t.with_(
        category_id=category_id,
        category_name=category.name,
        kind=category.kind,
        status=Status.USER_CORRECTED,
        confidence=1.0,
        reasons=(reason,),
        flags=flags,
        suggestions=(),
    )


def _safe_cell(value: str) -> str:
    """Neutralise spreadsheet formulas in exported text so opening the CSV cannot run anything."""
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value
