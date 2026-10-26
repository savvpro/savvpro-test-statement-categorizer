"""Decide a category without calling an AI model.

A confident wrong filing is worse than a question, so a row is filed only when
one rule clears the confidence threshold and is not in a near-tie. Everything
else stays in Needs review, sometimes with a suggestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .categories import EXPENSE_IDS, label

THRESHOLD = 0.78
MARGIN = 0.12

GENERIC_ROOTS = {"AMAZON", "AMZN", "PAYPAL", "VENMO", "ZELLE", "APPLE", "SQ", "TST", "ATM"}


@dataclass(frozen=True)
class Rule:
    key: str
    pattern: re.Pattern[str]
    category: str
    weight: float
    name: str
    unless: re.Pattern[str] | None = None
    ambiguous: bool = False
    reason: str | None = None


def _rule(
    key: str,
    pattern: str,
    category: str,
    weight: float,
    name: str,
    *,
    unless: str | None = None,
    ambiguous: bool = False,
    reason: str | None = None,
) -> Rule:
    return Rule(
        key=key,
        pattern=re.compile(pattern),
        category=category,
        weight=weight,
        name=name,
        unless=re.compile(unless) if unless else None,
        ambiguous=ambiguous,
        reason=reason,
    )


RULES: list[Rule] = [
    _rule("uber_eats", r"\bUBER\s+EATS\b", "meals", 0.94, "Uber Eats"),
    _rule("doordash", r"\bDOORDASH\b", "meals", 0.94, "DoorDash"),
    _rule("grubhub", r"\bGRUBHUB\b", "meals", 0.93, "Grubhub"),
    _rule("starbucks", r"\bSTARBUCKS\b", "meals", 0.92, "Starbucks"),
    _rule("sweetgreen", r"\bSWEETGREEN\b", "meals", 0.91, "Sweetgreen"),
    _rule("chipotle", r"\bCHIPOTLE\b", "meals", 0.91, "Chipotle"),
    _rule("dunkin", r"\bDUNKIN\b", "meals", 0.88, "Dunkin"),
    _rule("uber", r"\bUBER\b", "travel", 0.92, "Uber", unless=r"\bUBER\s+EATS\b"),
    _rule("lyft", r"\bLYFT\b", "travel", 0.92, "Lyft"),
    _rule("delta", r"\bDELTA\s+AIR\b", "travel", 0.93, "Delta"),
    _rule("united", r"\bUNITED\s+AIR\b", "travel", 0.93, "United"),
    _rule("southwest", r"\bSOUTHWEST\s+AIR\b", "travel", 0.93, "Southwest"),
    _rule("amtrak", r"\bAMTRAK\b", "travel", 0.93, "Amtrak"),
    _rule("airbnb", r"\bAIRBNB\b", "travel", 0.92, "Airbnb"),
    _rule("marriott", r"\bMARRIOTT\b", "travel", 0.92, "Marriott"),
    _rule("hilton", r"\bHILTON\b", "travel", 0.92, "Hilton"),
    _rule("hyatt", r"\bHYATT\b", "travel", 0.92, "Hyatt"),
    _rule("hertz", r"\bHERTZ\b", "travel", 0.9, "Hertz"),
    _rule("enterprise", r"\bENTERPRISE\s+RENT\b", "travel", 0.9, "Enterprise"),
    _rule("spothero", r"\bSPOTHERO\b|\bSPOT\s+HERO\b", "travel", 0.9, "SpotHero"),
    _rule("shell", r"\bSHELL\s+OIL\b", "travel", 0.9, "Shell"),
    _rule("chevron", r"\bCHEVRON\b", "travel", 0.88, "Chevron"),
    _rule("exxon", r"\bEXXON\b", "travel", 0.88, "Exxon"),
    _rule("parking", r"\bPARKING\b", "travel", 0.82, "Parking"),
    _rule("adobe", r"\bADOBE\b", "software", 0.95, "Adobe"),
    _rule("figma", r"\bFIGMA\b", "software", 0.95, "Figma"),
    _rule("canva", r"\bCANVA\b", "software", 0.93, "Canva"),
    _rule("dropbox", r"\bDROPBOX\b", "software", 0.93, "Dropbox"),
    _rule("notion", r"\bNOTION\b", "software", 0.9, "Notion"),
    _rule("slack", r"\bSLACK\b", "software", 0.88, "Slack"),
    _rule("zoom", r"\bZOOM(?:\s+US)?\b", "software", 0.9, "Zoom"),
    _rule("shutterstock", r"\bSHUTTERSTOCK\b", "software", 0.93, "Shutterstock"),
    _rule("envato", r"\bENVATO\b", "software", 0.93, "Envato"),
    _rule("webflow", r"\bWEBFLOW\b", "software", 0.92, "Webflow"),
    _rule("framer", r"\bFRAMER\b", "software", 0.9, "Framer"),
    _rule("miro", r"\bMIRO\b", "software", 0.88, "Miro"),
    _rule("grammarly", r"\bGRAMMARLY\b", "software", 0.9, "Grammarly"),
    _rule("quickbooks", r"\bQUICKBOOKS\b", "software", 0.9, "QuickBooks"),
    _rule("google_workspace", r"\bGOOGLE\s+(WORKSPACE|GSUITE)\b", "software", 0.93, "Google Workspace"),
    _rule("microsoft_365", r"\bMICROSOFT\s*365\b|\bMSFT\s*\*?\s*365\b", "software", 0.9, "Microsoft 365"),
    _rule("staples", r"\bSTAPLES\b", "supplies", 0.93, "Staples"),
    _rule("office_depot", r"\bOFFICE\s*DEPOT\b|\bOFFICEMAX\b", "supplies", 0.93, "Office Depot"),
    _rule("uline", r"\bULINE\b", "supplies", 0.92, "Uline"),
    _rule("blick", r"\bBLICK\s+ART\b", "supplies", 0.9, "Blick"),
    _rule("bh_photo", r"\bB&H\s+PHOTO\b|\bBHPHOTO\b|\bB\s+H\s+PHOTO\b", "equipment", 0.94, "B&H Photo"),
    _rule("adorama", r"\bADORAMA\b", "equipment", 0.94, "Adorama"),
    _rule("upwork", r"\bUPWORK\b", "contractors", 0.94, "Upwork"),
    _rule("fiverr", r"\bFIVERR\b", "contractors", 0.94, "Fiverr"),
    _rule("ninetynine", r"\b99DESIGNS\b", "contractors", 0.92, "99designs"),
    _rule("google_ads", r"\bGOOGLE\s+ADS\b", "marketing", 0.94, "Google Ads"),
    _rule("meta_ads", r"\b(?:FACEBOOK|FACEBK|META)\s+ADS\b", "marketing", 0.93, "Meta ads"),
    _rule("mailchimp", r"\bMAILCHIMP\b", "marketing", 0.92, "Mailchimp"),
    _rule("klaviyo", r"\bKLAVIYO\b", "marketing", 0.92, "Klaviyo"),
    _rule("vistaprint", r"\bVISTAPRINT\b", "marketing", 0.88, "VistaPrint"),
    _rule("linkedin_ads", r"\b(?:LINKEDIN|LNKD)\b.{0,16}\bADS\b", "marketing", 0.9, "LinkedIn ads"),
    _rule("legalzoom", r"\bLEGALZOOM\b", "professional", 0.92, "LegalZoom"),
    _rule("hrblock", r"\bH&R\s*BLOCK\b|\bH\s+R\s+BLOCK\b", "professional", 0.93, "H&R Block"),
    _rule("turbotax", r"\bTURBOTAX\b", "professional", 0.93, "TurboTax"),
    _rule("gusto", r"\bGUSTO\b", "professional", 0.86, "Gusto"),
    _rule("comcast", r"\bCOMCAST\b|\bXFINITY\b", "utilities", 0.92, "Comcast"),
    _rule("verizon_fios", r"\bVERIZON\s+(FIOS|INTERNET)\b", "utilities", 0.9, "Verizon internet"),
    _rule("spectrum", r"\bSPECTRUM\b", "utilities", 0.86, "Spectrum"),
    _rule("skillshare", r"\bSKILLSHARE\b", "education", 0.93, "Skillshare"),
    _rule("domestika", r"\bDOMESTIKA\b", "education", 0.93, "Domestika"),
    _rule("udemy", r"\bUDEMY\b", "education", 0.9, "Udemy"),
    _rule("linkedin_learning", r"\b(?:LINKEDIN|LNKD)\b.{0,20}\bLEARN", "education", 0.88, "LinkedIn Learning"),
    _rule("sephora", r"\bSEPHORA\b", "personal", 0.9, "Sephora"),
    _rule("planet_fitness", r"\bPLANET\s+FITNESS\b", "personal", 0.92, "Planet Fitness"),
    _rule(
        "amazon",
        r"\bAMAZON\b|\bAMZN\b",
        "supplies",
        0.5,
        "Amazon",
        ambiguous=True,
        reason="Amazon sells supplies, equipment, and personal items. Confirm this order.",
    ),
    _rule(
        "paypal",
        r"\bPAYPAL\b",
        "contractors",
        0.45,
        "PayPal",
        ambiguous=True,
        reason="PayPal is a way to pay, not a merchant. Confirm who was paid.",
    ),
    _rule(
        "venmo",
        r"\bVENMO\b",
        "contractors",
        0.45,
        "Venmo",
        ambiguous=True,
        reason="Venmo does not say whether this was a contractor, a friend, or a purchase.",
    ),
    _rule(
        "zelle",
        r"\bZELLE\b",
        "contractors",
        0.45,
        "Zelle",
        ambiguous=True,
        reason="Zelle does not say what this payment was for.",
    ),
    _rule(
        "cash_app",
        r"\bCASH\s+APP\b",
        "contractors",
        0.4,
        "Cash App",
        ambiguous=True,
        reason="Cash App does not say what this payment was for.",
    ),
    _rule(
        "atm",
        r"\bATM\b|\bCASH\s+WITHDRAWAL\b",
        "personal",
        0.4,
        "ATM",
        ambiguous=True,
        reason="Cash withdrawal. The statement does not say what the cash was for.",
    ),
    _rule(
        "apple_store",
        r"\bAPPLE\s+STORE\b",
        "equipment",
        0.6,
        "Apple Store",
        ambiguous=True,
        reason="Apple Store purchases can be studio equipment or personal. Confirm this one.",
    ),
    _rule(
        "tmobile",
        r"\bT\s+MOBILE\b",
        "utilities",
        0.66,
        "T-Mobile",
        ambiguous=True,
        reason="Phone bills are often a mix of personal and business use.",
    ),
    _rule(
        "netflix",
        r"\bNETFLIX\b",
        "personal",
        0.7,
        "Netflix",
        ambiguous=True,
        reason="Streaming on a business card might be personal. Confirm it before leaving it out of expenses.",
    ),
    _rule(
        "spotify",
        r"\bSPOTIFY\b",
        "personal",
        0.66,
        "Spotify",
        ambiguous=True,
        reason="Spotify might be personal, or it might be played in the studio. Confirm it.",
    ),
    _rule(
        "toast",
        r"\bTST\b",
        "meals",
        0.64,
        "Toast POS",
        ambiguous=True,
        reason="This looks like a restaurant charge, but the restaurant is not a known merchant.",
    ),
    _rule(
        "generic_cafe",
        r"\bCAFE\b|\bCOFFEE\b",
        "meals",
        0.58,
        "Cafe",
        ambiguous=True,
        reason="The name looks like a cafe, but it is not a known merchant.",
    ),
    _rule(
        "generic_restaurant",
        r"\bRESTAURANT\b",
        "meals",
        0.6,
        "Restaurant",
        ambiguous=True,
        reason="The name looks like a restaurant, but it is not a known merchant.",
    ),
    _rule(
        "generic_hotel",
        r"\bHOTEL\b",
        "travel",
        0.62,
        "Hotel",
        ambiguous=True,
        reason="This looks like lodging, but the property is not a known merchant.",
    ),
]

CARD_PAYMENT_RE = re.compile(
    r"\bPAYMENT\b.{0,30}\bTHANK\s+YOU\b|\bTHANK\s+YOU\b.{0,30}\bPAYMENT\b|"
    r"\bCREDIT\s+CARD\s+PAYMENT\b|\bCR\s+CARD\s+PMT\b"
)
CARD_AUTOPAY_RE = re.compile(r"\bAUTOPAY\b|\bAUTO\s+PAY\b|\bAUTOMATIC\s+PAYMENT\b|\bONLINE\s+PAYMENT\b")
TRANSFER_RE = re.compile(
    r"\bTRANSFER\s+(TO|FROM)\b|\bXFER\b|\bONLINE\s+TRANSFER\b|\bBALANCE\s+TRANSFER\b|\bTO\s+SAVINGS\b"
)
FEE_RE = re.compile(
    r"\bINTEREST\s+CHARGE|\bLATE\s+FEE\b|\bANNUAL\s+(MEMBERSHIP\s+)?FEE\b|"
    r"\bFOREIGN\s+TRANSACTION\s+FEE\b|\bOVERDRAFT\b|\bCASH\s+ADVANCE\s+FEE\b|"
    r"\bRETURNED\s+PAYMENT\b|\bFINANCE\s+CHARGE\b|\bMEMBERSHIP\s+FEE\b"
)
INCOME_RE = re.compile(r"\bSTRIPE\s+(PAYOUT|TRANSFER)\b|\bCLIENT\s+PAYMENT\b|\bINVOICE\s+PAID\b")
REFUND_RE = re.compile(r"\bREFUND\b|\bREVERSAL\b|\bCHARGEBACK\b|\bMERCHANDISE\s+RETURN\b|\bRETURN\b")
TOKEN_SKIP = {
    "POS",
    "DEBIT",
    "VISA",
    "MASTERCARD",
    "PURCHASE",
    "CARD",
    "PENDING",
    "USA",
    "US",
    "THE",
    "AND",
    "STORE",
    "INC",
    "LLC",
    "COM",
    "HELP",
    "ONLINE",
    "REFUND",
    "RETURN",
    "REVERSAL",
    "CHARGEBACK",
}


@dataclass
class Decision:
    category: str
    confidence: float
    reason: str
    source: str
    suggestion: str | None
    offsets_category: str | None
    needs_review: bool
    fingerprint: str
    remember_safe: bool
    sign_flip: bool = False

    @property
    def rule_note(self) -> str:
        return self.reason


def normalize(description: str) -> str:
    text = description.upper()
    text = re.sub(r"[^A-Z0-9&]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def categorize(description: str, amount: float, memory: dict[str, str] | None = None) -> Decision:
    """Classify one transaction. `amount` is positive for money out."""
    saved = memory or {}
    text = normalize(description)
    if not text:
        return _review("The description is empty.", None, "", False)

    if CARD_PAYMENT_RE.search(text) or (amount < 0 and CARD_AUTOPAY_RE.search(text)):
        return _confident(
            "card_payment",
            0.97,
            "This is a payment toward the card, so it is not a business expense.",
            "shape",
            _token_fingerprint(text),
            sign_flip=amount > 0,
        )
    if TRANSFER_RE.search(text):
        return _confident(
            "transfer",
            0.95,
            "This is a transfer between accounts, so it is not spending.",
            "shape",
            _token_fingerprint(text),
            sign_flip=amount > 0,
        )
    if FEE_RE.search(text):
        return _confident(
            "fees",
            0.93,
            "Matched an interest or card-fee description.",
            "shape",
            _token_fingerprint(text),
        )
    if INCOME_RE.search(text):
        if amount < 0:
            return _confident(
                "income",
                0.9,
                "Matched a client payout. This is income, not a refund and not an expense.",
                "shape",
                _token_fingerprint(text),
            )
        return _review(
            "The description looks like client income, but the amount is money out. Confirm it.",
            "income",
            _token_fingerprint(text),
            True,
        )

    hits = _match(text)
    strong = sorted((hit for hit in hits if not hit.ambiguous and hit.weight >= THRESHOLD), key=lambda hit: hit.weight, reverse=True)
    weak = sorted((hit for hit in hits if hit.ambiguous or hit.weight < THRESHOLD), key=lambda hit: hit.weight, reverse=True)
    fingerprint = strong[0].key if strong else _token_fingerprint(text)
    remember_safe = _is_remember_safe(fingerprint)
    learned = saved.get(fingerprint)

    money_back = amount < 0 or bool(REFUND_RE.search(text))
    if money_back and (REFUND_RE.search(text) or strong or learned):
        sign_flip = amount > 0 and bool(REFUND_RE.search(text))
        if learned and learned in EXPENSE_IDS:
            return _refund(
                learned,
                0.96,
                f"Refund. It reduces {label(learned)} because you saved that merchant.",
                "memory",
                fingerprint,
                remember_safe,
                sign_flip,
            )
        if strong:
            top = strong[0]
            if len(strong) > 1 and top.weight - strong[1].weight < MARGIN:
                return _review(
                    f"This is money back, and it is a close call between {top.name} and {strong[1].name}.",
                    top.category,
                    fingerprint,
                    remember_safe,
                    sign_flip=sign_flip,
                )
            return _refund(
                top.category,
                top.weight,
                f"Refund from {top.name}. It reduces {label(top.category)} and is not income.",
                "rule",
                fingerprint,
                remember_safe,
                sign_flip,
            )
        if REFUND_RE.search(text):
            return _refund(
                None,
                0.84,
                "The description says this is a refund. It is not income, but which expense it reduces is unclear.",
                "rule",
                fingerprint,
                remember_safe,
                sign_flip,
            )

    if learned:
        return _confident(
            learned,
            0.99,
            "Used the category you saved for this merchant.",
            "memory",
            fingerprint,
        )

    if money_back:
        suggestion = weak[0].category if weak else None
        why = "Money came in, and this is not a card payment, transfer, client payment, or a known refund."
        if weak and weak[0].reason:
            why = f"{why} {weak[0].reason}"
        return _review(why, suggestion, fingerprint, remember_safe)

    if len(strong) >= 2 and strong[0].weight - strong[1].weight < MARGIN:
        return _review(
            f"Close call between {strong[0].name} and {strong[1].name}.",
            strong[0].category,
            fingerprint,
            remember_safe,
        )
    if strong:
        top = strong[0]
        return _confident(
            top.category,
            top.weight,
            f"Matched {top.name}.",
            "rule",
            fingerprint,
        )
    if weak:
        top = weak[0]
        why = top.reason or f"Possible {label(top.category)}, but the match is not strong enough to file it."
        return _review(why, top.category if top.ambiguous else top.category, fingerprint, remember_safe)
    return _review(
        "No saved merchant and no known rule matched this description.",
        None,
        fingerprint,
        remember_safe,
    )


def _match(text: str) -> list[Rule]:
    found: list[Rule] = []
    for rule in RULES:
        if rule.unless and rule.unless.search(text):
            continue
        if rule.pattern.search(text):
            found.append(rule)
    return found


def _token_fingerprint(text: str) -> str:
    tokens = []
    for token in text.split():
        if token in TOKEN_SKIP or token.isdigit() or len(token) < 2:
            continue
        tokens.append(token)
    if tokens and tokens[0] == "TST":
        tokens = tokens[1:]
    return " ".join(tokens[:2])


def _is_remember_safe(fingerprint: str) -> bool:
    if not fingerprint:
        return False
    if " " not in fingerprint and fingerprint.islower():
        return fingerprint not in {"amazon", "paypal", "venmo", "zelle", "cash_app", "apple_store", "generic_cafe", "toast"}
    root = fingerprint.split()[0]
    return root not in GENERIC_ROOTS


def _confident(
    category: str,
    confidence: float,
    reason: str,
    source: str,
    fingerprint: str,
    sign_flip: bool = False,
) -> Decision:
    return Decision(
        category=category,
        confidence=confidence,
        reason=reason,
        source=source,
        suggestion=None,
        offsets_category=None,
        needs_review=False,
        fingerprint=fingerprint,
        remember_safe=_is_remember_safe(fingerprint),
        sign_flip=sign_flip,
    )


def _refund(
    offsets: str | None,
    confidence: float,
    reason: str,
    source: str,
    fingerprint: str,
    remember_safe: bool,
    sign_flip: bool,
) -> Decision:
    return Decision(
        category="refund",
        confidence=confidence,
        reason=reason,
        source=source,
        suggestion=None,
        offsets_category=offsets,
        needs_review=False,
        fingerprint=fingerprint,
        remember_safe=remember_safe,
        sign_flip=sign_flip,
    )


def _review(
    reason: str,
    suggestion: str | None,
    fingerprint: str,
    remember_safe: bool,
    sign_flip: bool = False,
) -> Decision:
    return Decision(
        category="needs_review",
        confidence=0.0 if suggestion is None else 0.5,
        reason=reason,
        source="review",
        suggestion=suggestion,
        offsets_category=None,
        needs_review=True,
        fingerprint=fingerprint,
        remember_safe=remember_safe,
        sign_flip=sign_flip,
    )
