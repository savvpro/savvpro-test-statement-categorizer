"""Application service: the use cases the API exposes, free of HTTP concerns."""
from typing import List

from ..categorization.engine import CategorizationEngine
from ..categorization.normalizer import merchant_key, normalize
from ..domain.errors import FileTooLargeError
from ..domain.models import CategorizationResult, Category
from ..ingestion.base import ReaderRegistry
from ..learning.repository import MerchantRule, MerchantRuleRepository
from ..reporting.totals import compute_totals


class StatementService:
    def __init__(self, readers: ReaderRegistry, engine: CategorizationEngine, max_upload_bytes: int):
        self._readers = readers
        self._engine = engine
        self._max_upload_bytes = max_upload_bytes

    @property
    def max_upload_bytes(self) -> int:
        return self._max_upload_bytes

    def categorize(self, filename: str, content: bytes) -> CategorizationResult:
        if len(content) > self._max_upload_bytes:
            raise FileTooLargeError(f"File is larger than {self._max_upload_bytes // (1024 * 1024)} MB.")
        parsed = self._readers.for_filename(filename).read(content)
        transactions = self._engine.categorize(parsed.transactions)
        return CategorizationResult(
            transactions=transactions,
            issues=parsed.issues,
            totals=compute_totals(transactions),
            needs_review=sum(1 for t in transactions if t.category == Category.NEEDS_REVIEW),
        )


class MerchantRuleService:
    def __init__(self, repository: MerchantRuleRepository):
        self._repository = repository

    def remember(self, merchant: str, category: Category) -> MerchantRule:
        if category == Category.NEEDS_REVIEW:
            raise ValueError("Cannot save a rule that sends a merchant to review.")
        key = merchant_key(normalize(merchant))
        if not key:
            raise ValueError("Merchant name is empty.")
        return self._repository.save(MerchantRule(merchant=key, category=category))

    def list(self) -> List[MerchantRule]:
        return self._repository.list()

    def forget(self, merchant: str) -> bool:
        return self._repository.delete(merchant_key(normalize(merchant)))
