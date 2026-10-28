"""Turn a raw statement description into a stable merchant key.

"SQ *JOES CAFE #9921 DALLAS TX" and "JOES CAFE 0412" should both become
"JOES CAFE" so rules and learned fixes match every visit.
"""

import re

_PREFIXES = re.compile(
    r"^(POS\s+(PURCHASE|DEBIT)\s+|DEBIT\s+CARD\s+PURCHASE\s+|PURCHASE\s+AUTHORIZED\s+ON\s+\d{2}/\d{2}\s+|"
    r"CHECKCARD\s+\d{4}\s+|SQ\s*\*\s*|TST\s*\*\s*|SP\s*\*\s*|PAYPAL\s*\*\s*|PP\s*\*\s*)",
    re.I,
)
_NOISE = [
    re.compile(r"\b(X+|\*+)\d{2,4}\b"),  # masked card numbers
    re.compile(r"#\s*\d+"),  # store numbers
    re.compile(r"\b\d{2}/\d{2}(/\d{2,4})?\b"),  # dates inside the text
    re.compile(r"\b[A-Z]{2}\s*\d{5}(-\d{4})?\b"),  # state + zip
    re.compile(r"\b(CARD|REF|ID|TXN|AUTH)[\s#:]*\w*\d\w*\b", re.I),
    re.compile(r"\b\d{4,}\b"),  # long reference numbers
]
_REFUND_WORDS = {"REFUND", "RETURN", "REVERSAL", "REVERSED", "CREDIT"}
_STATES = re.compile(
    r"\s+(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|"
    r"NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)$"
)


def clean(description: str) -> str:
    """Upper-case, without processor prefixes, numbers, dates and locations."""
    s = " ".join(description.upper().split())
    s = _PREFIXES.sub("", s)
    for pattern in _NOISE:
        s = pattern.sub(" ", s)
    s = re.sub(r"[^A-Z0-9&'*.\- ]", " ", s)
    s = " ".join(s.split())
    s = _STATES.sub("", s)
    return s.strip(" *-.")


def merchant_key(description: str) -> str:
    """First words of the cleaned text: the part that names the merchant."""
    # Refund words are dropped so "AUTOZONE REFUND" matches the "AUTOZONE" purchase.
    words = [w for w in clean(description).replace("*", " ").split() if w not in _REFUND_WORDS]
    # Two words name the merchant; anything after is usually a city or a
    # store/terminal code that changes between visits.
    return " ".join(words[:2])
