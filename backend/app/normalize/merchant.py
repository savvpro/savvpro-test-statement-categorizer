"""Merchant cleaning: raw bank description -> (merchant_key, channel, counterparty).

Ordered steps (03-ingestion section 8). All regexes are linear-time (no nested quantifiers).
"""

import re
import unicodedata

MAX_KEY = 128
MAX_COUNTERPARTY = 64

US_STATES = frozenset(
    [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    ]
)
BUSINESS_TOKENS = frozenset(
    [
        "LLC",
        "INC",
        "CO",
        "CORP",
        "LTD",
        "LP",
        "LLP",
        "SERVICES",
        "SERVICE",
        "PLUMBING",
        "ELECTRIC",
        "ELECTRICAL",
        "HVAC",
        "ROOFING",
        "CONSTRUCTION",
        "PROPERTIES",
        "PROPERTY",
        "MANAGEMENT",
        "REALTY",
        "REAL",
        "ESTATE",
        "INSURANCE",
        "BANK",
        "SUPPLY",
        "SUPPLIES",
        "REPAIR",
        "REPAIRS",
        "MAINTENANCE",
        "CLEANING",
        "LANDSCAPING",
        "LAWN",
        "PEST",
        "CONTROL",
        "LAW",
        "OFFICE",
        "OFFICES",
        "GROUP",
        "HOLDINGS",
        "ENTERPRISES",
        "COMPANY",
        "TRUST",
        "UTILITIES",
        "WATER",
        "POWER",
        "GAS",
        "ENERGY",
        "CABLE",
        "INTERNET",
        "MORTGAGE",
        "LOAN",
        "PAYMENT",
        "PAYMENTS",
        "TAX",
        "TAXES",
        "STORE",
        "MARKET",
        "DEPOT",
        "HARDWARE",
    ]
)

# alias regex -> (replacement, implied channel)
_ALIASES: tuple[tuple[re.Pattern[str], str, str | None], ...] = tuple(
    (re.compile(p), r, c)
    for p, r, c in (
        (r"\bAMZN MKTP( US)?\b", "AMAZON", "CARD"),
        (r"\bAMZN\b", "AMAZON", None),
        (r"\bAMAZON (COM|MKTPLACE|PRIME)\b", "AMAZON", None),
        (r"\bWM SUPERCENTER\b", "WALMART", None),
        (r"\bWAL MART\b", "WALMART", None),
        (r"\bWALMART (SUPERCENTER|NEIGHBORHOOD MARKET)\b", "WALMART", None),
        (r"^THE HOME DEPOT\b", "HOME DEPOT", None),
        (r"\bHOMEDEPOT\b", "HOME DEPOT", None),
        (r"^LOWES\b.*", "LOWES", None),
        (r"^HOME DEPOT\b.*", "HOME DEPOT", None),
        (r"^WALMART\b.*", "WALMART", None),
        (r"^TARGET\b.*", "TARGET", None),
    )
)

_ZELLE_RE = re.compile(
    r"^ZELLE\s+(?:PAYMENT\s+)?(?:FROM|TO)\s+(?P<cp>.+?)(?:\s+(?:CONF|REF|ID)\b.*)?$"
)
_VENMO_RE = re.compile(r"^VENMO\s+(?:PAYMENT\s+)?(?:(?:FROM|TO)\s+(?P<cp>.+?))?(?:\s+ID\b.*)?$")
_CASHAPP_RE = re.compile(
    r"^(?:SQC\s*\*\s*)?CASH APP(?:\s+(?:PAYMENT\s+)?(?:FROM|TO)\s+(?P<cp>.+?))?(?:\s+ID\b.*)?$"
)
_CHECK_RE = re.compile(r"^CHECK\s*#?\s*\d+\b")
_PREFIX_CHANNELS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^ACH\s+(?:DEBIT|CREDIT|PAYMENT|DEPOSIT|WITHDRAWAL)\b\s*"), "ACH"),
    (re.compile(r"^DIRECT\s+DEP(?:OSIT)?\b\s*"), "ACH"),
    (re.compile(r"^(?:INCOMING\s+|OUTGOING\s+)?WIRE\s+(?:IN|OUT)\b\s*"), "WIRE"),
    (re.compile(r"^POS\s+(?:DEBIT|PURCHASE)\b\s*"), "CARD"),
    (re.compile(r"^DEBIT CARD PURCHASE\b\s*"), "CARD"),
    (re.compile(r"^CHECKCARD\s+\d{4}\b\s*"), "CARD"),
    (re.compile(r"^PURCHASE AUTHORIZED ON\s+\d{1,2}/\d{1,2}\b\s*"), "CARD"),
)
_PROCESSOR_PREFIX_RE = re.compile(r"^(?:SQ|TST|SP|PY|PP|IN|DD|BT|EB|FS|PAYPAL|GOOGLE|APL)\s*\*\s*")

_NOISE: tuple[re.Pattern[str], ...] = (
    re.compile(r"HTTPS?://\S+"),
    re.compile(r"\bX{2,}\d{2,4}\b"),
    re.compile(r"\*\d{4}\b"),
    re.compile(r"\b(?:REF|CONF|ID|TRACE|AUTH)\b[#:]?\s*\w+"),
    re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    re.compile(r"#\s*\d+"),
)
_DOMAIN_RE = re.compile(r"\b(?:WWW\.)?([A-Z0-9-]+)\.(?:COM|NET|ORG|IO|CO)\b(?:/\S*)?")
_QUOTES_RE = re.compile("[’‘'\"`]")
_SPACE_RE = re.compile(r"\s+")


def _normalise(raw: str) -> str:
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = unicodedata.normalize("NFKC", text).upper()
    text = _QUOTES_RE.sub("", text).replace("&", " AND ")
    text = "".join(c if (c.isalnum() or c in " *#/.:-()") else " " for c in text)
    return _SPACE_RE.sub(" ", text).strip()


def _letters_only(text: str) -> str:
    return _SPACE_RE.sub(" ", "".join(c if c.isalpha() else " " for c in text)).strip()


def _final_tokens(text: str) -> list[str]:
    text = "".join(c if c.isalnum() else " " for c in text)
    tokens = [t for t in text.split() if sum(ch.isdigit() for ch in t) < 4]
    deduped: list[str] = []
    for t in tokens:
        if not deduped or deduped[-1] != t:
            deduped.append(t)
    return deduped


def _strip_location(tokens: list[str]) -> list[str]:
    if len(tokens) >= 2 and tokens[-1] in US_STATES:
        rest = tokens[:-1]
        if len(rest) >= 3 and rest[-1] not in BUSINESS_TOKENS and rest[-1].isalpha():
            return rest[:-1]
        return rest
    return tokens


def _core(raw: str) -> tuple[str, str | None, str | None]:
    text = _normalise(raw)
    channel: str | None = None
    counterparty: str | None = None
    head = ""

    for pattern, label in (
        (_ZELLE_RE, "ZELLE"),
        (_VENMO_RE, "VENMO"),
        (_CASHAPP_RE, "CASHAPP"),
    ):
        m = pattern.match(text)
        if m:
            cp = _letters_only(m.group("cp") or "")[:MAX_COUNTERPARTY].strip()
            channel = label
            counterparty = cp or None
            head = "CASH APP" if label == "CASHAPP" else label
            text = cp if cp else ""
            break
    else:
        if text.startswith("ZELLE"):
            channel, head, text = "ZELLE", "ZELLE", text[5:].strip()
        elif _CHECK_RE.match(text):
            return "CHECK", "CHECK", None
        else:
            for pattern, label in _PREFIX_CHANNELS:
                m2 = pattern.match(text)
                if m2:
                    channel = label
                    text = text[m2.end() :]
                    break
            if text.startswith("PAYPAL") and "*" not in text:
                channel = channel or "PAYPAL"
            m3 = _PROCESSOR_PREFIX_RE.match(text)
            if m3:
                channel = channel or ("PAYPAL" if text.startswith("PAYPAL") else "CARD")
                text = text[m3.end() :]

    for noise in _NOISE:
        text = noise.sub(" ", text)
    text = _DOMAIN_RE.sub(r" \1 ", text)

    if head and counterparty:
        key_tokens = [head, *_final_tokens(counterparty)]
        key = " ".join(key_tokens)
        return key[:MAX_KEY].strip() or head, channel, counterparty

    tokens = _strip_location(_final_tokens(text))
    key = " ".join(tokens)
    for pattern, repl, implied in _ALIASES:
        if pattern.search(key):
            key = pattern.sub(repl, key)
            channel = channel or implied
    key = " ".join(_dedupe(key.split()))
    if head and not key:
        key = head
    elif head and head not in key.split()[:1]:
        key = f"{head} {key}"
    if not key:
        key = channel if channel in {"WIRE", "ACH"} and channel else "UNKNOWN"
    return key[:MAX_KEY].strip() or "UNKNOWN", channel, counterparty


def _dedupe(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        if not out or out[-1] != t:
            out.append(t)
    return out


def clean_description(raw: str) -> tuple[str, str | None, str | None]:
    """Return (merchant_key, channel, counterparty). Idempotent on the key."""
    key, channel, counterparty = _core(raw)
    for _ in range(8):
        again, _c, _p = _core(key)
        if again == key:
            break
        key = again
    return key, channel, counterparty


def is_person_like(name: str) -> bool:
    """2-3 alphabetic tokens, none of which is a business word."""
    tokens = name.upper().split()
    return (
        2 <= len(tokens) <= 3
        and all(t.isalpha() or (len(t) == 1) for t in tokens)
        and not any(t in BUSINESS_TOKENS for t in tokens)
    )
