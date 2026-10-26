import re

from pydantic import BaseModel, ConfigDict

_WHITESPACE = re.compile(r"\s+")
# Payment-processor prefixes, removed at the start only. "UBER *" is deliberately absent:
# there Uber is the merchant.
_PROCESSOR_PREFIX = re.compile(r"^(?:(?:SQ|PAYPAL|TST)\s*\*\s*|POS\s+)")


class NormalizedDescription(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str  # uppercase, spaces collapsed, processor prefix removed: what rules match on
    merchant_key: str  # text without any token that contains a digit: what user rules match on


def normalize(raw_description: str) -> NormalizedDescription:
    text = _WHITESPACE.sub(" ", raw_description.upper()).strip()
    text = _PROCESSOR_PREFIX.sub("", text, count=1).strip()
    merchant_key = " ".join(t for t in text.split(" ") if not any(c.isdigit() for c in t))
    return NormalizedDescription(text=text, merchant_key=merchant_key)
