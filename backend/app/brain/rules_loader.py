import json
import re
from functools import lru_cache

from app.config import RULES_PATH


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def keyword_in(description: str, keyword: str) -> bool:
    """Poora lafz match karta hai (TRANSFER, 'RETRANSFERRED' mai nahi milega)."""
    return re.search(rf"\b{re.escape(keyword)}\b", description) is not None


def find_keyword(description: str, keywords: list[str]) -> str | None:
    """Sab se lamba matching keyword wapas karta hai."""
    hits = [k for k in keywords if keyword_in(description, k)]
    return max(hits, key=len) if hits else None