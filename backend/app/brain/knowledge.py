"""Hand-curated knowledge about the merchants a gig driver typically sees.

Three kinds of rules live here:

* **Merchant rules** - a known merchant or pattern that maps to one category.
* **Ambiguous rules** - a known merchant that sells both business and personal things
  (Amazon, Walmart, Venmo...). These never auto-categorise; they go to review with
  suggestions, because a wrong guess is worse than asking.
* **Keyword rules** - generic words (``TOLL``, ``CAR WASH``, ``CAFE``) that are weaker
  evidence than a known merchant.

Patterns run against the normalised description (see ``normalize.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from .models import Direction

IN, OUT, ANY = Direction.IN, Direction.OUT, Direction.ANY


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    category: str | None  # None = ambiguous merchant, needs the user
    confidence: float
    direction: Direction = OUT
    note: str = ""
    suggestions: tuple[str, ...] = ()
    # Purchases below this amount are suspicious for the category (snacks at a gas station).
    min_typical_amount: Decimal | None = None
    fuzzy: bool = False  # offer this name as a target for typo matching

    @property
    def ambiguous(self) -> bool:
        return self.category is None


def _brand_regex(name: str) -> str:
    """``O'REILLY AUTO`` -> regex tolerant to optional apostrophes, dashes and spaces."""
    body = re.escape(name)
    body = body.replace("'", "'?").replace(r"\-", "[- ]?").replace(r"\ ", r"\s?")
    return rf"(?<![A-Z0-9]){body}(?![A-Z0-9])"


def brands(
    names: str,
    category: str | None,
    confidence: float,
    *,
    direction: Direction = OUT,
    note: str = "",
    suggestions: tuple[str, ...] = (),
    min_typical_amount: str | None = None,
) -> list[Rule]:
    """One rule per ``|``-separated brand name."""
    minimum = Decimal(min_typical_amount) if min_typical_amount else None
    return [
        Rule(
            name=name,
            pattern=re.compile(_brand_regex(name)),
            category=category,
            confidence=confidence,
            direction=direction,
            note=note,
            suggestions=suggestions,
            min_typical_amount=minimum,
            fuzzy=len(name.replace(" ", "")) >= 5,
        )
        for name in (n.strip() for n in names.split("|"))
        if name
    ]


def pattern(
    name: str,
    regex: str,
    category: str | None,
    confidence: float,
    *,
    direction: Direction = OUT,
    note: str = "",
    suggestions: tuple[str, ...] = (),
) -> Rule:
    return Rule(
        name=name,
        pattern=re.compile(regex),
        category=category,
        confidence=confidence,
        direction=direction,
        note=note,
        suggestions=suggestions,
    )


_PAYOUT_WORDS = (
    r"(?:PAYOUT|PAY ?OUT|PYMNTS?|PAYMENTS?|EDI|DIR(?:ECT)? ?DEP|DIRECT DEPOSIT|INSTANT ?PAY|"
    r"FAST ?PAY|EXPRESS ?PAY|CASH ?OUT|EARNINGS|PAYROLL|DRIVER|DASHER|SHOPPER|COURIER)"
)


def _payout(name: str, platform: str) -> Rule:
    return pattern(
        f"{name} payout",
        rf"\b(?:{platform})\b.*\b{_PAYOUT_WORDS}\b|\b{_PAYOUT_WORDS}\b.*\b(?:{platform})\b",
        "platform_income",
        0.96,
        direction=IN,
        note=f"{name} driver payout.",
    )


MERCHANT_RULES: list[Rule] = [
    # --- Money moving between the user's own accounts -------------------------------
    pattern(
        "Card payment",
        # Bare "AUTOPAY" is deliberately absent: "T-MOBILE AUTOPAY" is a phone bill.
        r"\b(?:PAYMENT\s*-?\s*THANK YOU|THANK YOU FOR YOUR PAYMENT|CRCARDPMT|"
        r"CREDIT CARD (?:PAYMENT|PMT)|PAYMENT RECEIVED)\b",
        "transfer",
        0.95,
        direction=ANY,
        note="Paying a credit card moves money; the spending was already counted.",
    ),
    pattern(
        "Card issuer payment",
        r"\b(?:CHASE|CAPITAL ONE|DISCOVER|AMEX|AMERICAN EXPRESS|CITI|BARCLAYCARD|BANK OF AMERICA)"
        r"\b.*\b(?:CARD )?(?:PMT|PAYMENT|AUTOPAY|EPAY)\b",
        "transfer",
        0.93,
        direction=ANY,
        note="Paying a credit card moves money; the spending was already counted.",
    ),
    pattern(
        "Own-account transfer",
        # Zelle/Venmo/PayPal "transfers" usually pay other people, so they are excluded here.
        r"^(?!.*\b(?:ZELLE|VENMO|CASH ?APP|PAYPAL|WIRE)\b).*"
        r"\b(?:ONLINE |MOBILE |INTERNAL |ACCOUNT |BANKING )?(?:TRANSFER|XFER|TFR)\b",
        "transfer",
        0.9,
        direction=ANY,
        note="Transfers between your own accounts are not income or spending.",
    ),
    pattern(
        "ATM withdrawal",
        r"\bATM\b(?!.*\bFEE\b)|\bCASH WITHDRAWAL\b|\bWITHDRAWAL\b.*\bATM\b",
        "transfer",
        0.88,
        direction=ANY,
        note="Cash withdrawal. Record any business cash spending separately.",
    ),
    pattern(
        "Venmo cash out",
        r"\b(?:VENMO|CASH ?APP|PAYPAL)\b.*\b(?:CASH ?OUT|INST(?:ANT)? XFER|STANDARD TRANSFER)\b",
        "transfer",
        0.9,
        direction=IN,
        note="Moving your own wallet balance to the bank.",
    ),
    # --- Gig platform income ---------------------------------------------------------
    _payout("Uber", "UBER"),
    _payout("Lyft", "LYFT"),
    _payout("DoorDash", "DOOR ?DASH"),
    _payout("Instacart", "INSTACART|MAPLEBEAR"),
    _payout("Grubhub", "GRUBHUB"),
    _payout("Shipt", "SHIPT"),
    _payout("Spark Driver", "SPARK DRIVER|BRANCH MESSENGER|SPARK"),
    pattern(
        "Amazon Flex payout",
        r"\b(?:AMAZON|AMZN)\b.*\bFLEX\b",
        "platform_income",
        0.95,
        direction=IN,
        note="Amazon Flex delivery payout.",
    ),
    # --- Bank fees & interest --------------------------------------------------------
    pattern(
        "ATM fee",
        r"\bATM\b.*\bFEE\b|\bFEE\b.*\bATM\b",
        "bank_fees",
        0.95,
        direction=ANY,
    ),
    pattern(
        "Foreign transaction fee",
        r"\b(?:FOREIGN|INTL|INTERNATIONAL|FX)\b.*\bFEE\b",
        "bank_fees",
        0.95,
    ),
    pattern(
        "Interest charge",
        r"\b(?:INTEREST CHARGE|PURCHASE INTEREST|INTEREST ON PURCHASES|FINANCE CHARGE)\b",
        "bank_fees",
        0.93,
        note="Interest on a card used for the business is deductible.",
    ),
    pattern(
        "Bank fee",
        r"\b(?:MONTHLY|SERVICE|MAINTENANCE|OVERDRAFT|NSF|WIRE|ANNUAL|LATE|RETURNED PAYMENT|"
        r"ACCOUNT)\b(?: SERVICE)? (?:CHARGE|FEE)\b",
        "bank_fees",
        0.92,
    ),
    pattern(
        "Fee reversal",
        r"\bFEE\b.*\b(?:REVERSAL|REFUND|REBATE)\b|\b(?:REVERSAL|REFUND)\b.*\bFEE\b",
        "bank_fees",
        0.93,
        direction=IN,
        note="A refunded fee reduces your fees total.",
    ),
    pattern(
        "Card rewards",
        r"\b(?:REWARDS? (?:REDEMPTION|CREDIT)|CASH ?BACK (?:REWARD|BONUS|REDEMPTION)|"
        r"STATEMENT CREDIT)\b",
        "personal",
        0.85,
        direction=IN,
        note="Card rewards are a price rebate, not taxable income.",
    ),
    # --- Fuel & EV charging ----------------------------------------------------------
    *brands(
        "SHELL|CHEVRON|EXXON|EXXONMOBIL|MOBIL|BP|ARCO|AMPM|VALERO|SUNOCO|MARATHON PETRO|"
        "SPEEDWAY|CIRCLE K|QUIKTRIP|CITGO|PHILLIPS 66|CONOCO|UNION 76|CASEYS|RACETRAC|"
        "LOVES TRAVEL|PILOT TRAVEL|FLYING J|MURPHY USA|MURPHY EXPRESS|KUM & GO|GULF OIL|"
        "TEXACO|SINCLAIR|HOLIDAY STATIONSTORES|WAWA|SHEETZ|QUICK TRIP|STEWARTS SHOPS|KWIK TRIP",
        "fuel",
        0.92,
        min_typical_amount="10",
        note="Gas station.",
    ),
    *brands(
        "COSTCO GAS|COSTCO FUEL|SAMS CLUB FUEL|SAMS FUEL|BJS FUEL|KROGER FUEL|SAFEWAY FUEL|"
        "WALMART FUEL|FRED MEYER FUEL|HEB FUEL|GIANT EAGLE GETGO|GETGO",
        "fuel",
        0.96,
    ),
    *brands(
        "TESLA SUPERCHARGER|TESLA SUPERCHGR|TESLA CHARGING|CHARGEPOINT|ELECTRIFY AMERICA|EVGO|"
        "BLINK CHARGING|EV CONNECT|SHELL RECHARGE|VOLTA CHARGING",
        "fuel",
        0.95,
        note="EV charging counts as fuel.",
    ),
    # --- Vehicle maintenance & car wash ----------------------------------------------
    *brands(
        "JIFFY LUBE|VALVOLINE|TAKE 5 OIL|GREASE MONKEY|QUICK LANE|AUTOZONE|O'REILLY AUTO|"
        "OREILLY AUTO|ADVANCE AUTO|NAPA AUTO|NAPA STORE|PEP BOYS|FIRESTONE|GOODYEAR|"
        "DISCOUNT TIRE|TIRE KINGDOM|BIG O TIRES|LES SCHWAB|MIDAS|MEINEKE|SAFELITE|MAACO|"
        "MONRO|NTB TIRE|CAR-X|CARQUEST|MISTER CAR WASH|ZIPS CAR WASH|TOMMYS EXPRESS|"
        "QUICK QUACK|SPLASH CAR WASH|WASH DEPOT|SPARKLING IMAGE",
        "vehicle_maintenance",
        0.92,
    ),
    # --- Tolls & parking -------------------------------------------------------------
    *brands(
        "E-ZPASS|EZPASS|EZ PASS|FASTRAK|SUNPASS|TXTAG|NTTA|TOLLTAG|PEACH PASS|I-PASS|IPASS|"
        "GOOD TO GO|PIKEPASS|K-TAG|TOLL BY PLATE|PAY BY PLATE|E-PASS|THE TOLL ROADS",
        "tolls_parking",
        0.94,
    ),
    *brands(
        "PARKMOBILE|SPOTHERO|PAYBYPHONE|PARKWHIZ|LAZ PARKING|SP PLUS|SP+|IMPARK|ABM PARKING|"
        "PREMIUM PARKING|METROPOLIS|PASSPORT PARKING|ACE PARKING|TOWNE PARK",
        "tolls_parking",
        0.92,
    ),
    pattern(
        "Traffic fine",
        r"\b(?:PARKING|TRAFFIC|TOLL|CAMERA|RED LIGHT)\b.*\b(?:CITATION|TICKET|VIOLATION|FINE)S?\b|"
        r"\bCITATION\b|\bCOURT FINE\b",
        "personal",
        0.95,
        note="Fines and penalties are never deductible, even on the job.",
    ),
    # --- Insurance -------------------------------------------------------------------
    *brands(
        "GEICO|PROGRESSIVE|ESURANCE|ROOT INSURANCE|ROOT INS|METROMILE|THE GENERAL|DAIRYLAND|"
        "MERCURY INS|INFINITY INS|DIRECT AUTO|BRISTOL WEST|GAINSCO",
        "vehicle_insurance",
        0.9,
        note="Auto insurer. Deduct the business-use share.",
    ),
    *brands(
        "STATE FARM|ALLSTATE|LIBERTY MUTUAL|FARMERS INS|NATIONWIDE|TRAVELERS|ERIE INS|USAA P&C|"
        "AMERICAN FAMILY|AMFAM",
        "vehicle_insurance",
        0.8,
        note="This insurer also sells home and life cover - check it is the car policy.",
    ),
    *brands(
        "BLUE CROSS|BLUE SHIELD|BCBS|AETNA|CIGNA|UNITEDHEALTH|UNITED HEALTHCARE|KAISER|HUMANA|"
        "AMBETTER|OSCAR HEALTH|DELTA DENTAL",
        "personal",
        0.88,
        note="Health insurance is claimed on Schedule 1, not as a Schedule C expense.",
    ),
    # --- Car lease, loan and rental (deductibility depends on the contract) ---------
    *brands(
        "TOYOTA FINANCIAL|TOYOTA FINL|TOYOTA MOTOR CREDIT|TMCC|HONDA FINANCIAL|HONDA FINL|"
        "AMERICAN HONDA|GM FINANCIAL|FORD CREDIT|FORD MOTOR CREDIT|ALLY AUTO|ALLY PAYMT|"
        "NISSAN MOTOR ACCEPTANCE|NISSAN FINANCE|HYUNDAI MOTOR FINANCE|KIA FINANCE|"
        "KIA MOTORS FINANCE|CARMAX AUTO FINANCE|CAPITAL ONE AUTO|SANTANDER CONSUMER|"
        "CHRYSLER CAPITAL|TESLA FINANCE",
        "vehicle_lease_loan",
        0.7,
        note="Lease payments are deductible, but for a loan only the interest is. Please confirm.",
        suggestions=("personal",),
    ),
    *brands(
        "HERTZ|AVIS|ENTERPRISE RENT|HYRECAR|GETAROUND|TURO|FAIR.COM|KINTO|FLEXDRIVE",
        "vehicle_lease_loan",
        0.72,
        note="Car rental. Rentals for driving shifts are deductible; personal trips are not.",
        suggestions=("personal",),
    ),
    # --- Phone & data ----------------------------------------------------------------
    *brands(
        "VERIZON WIRELESS|VERIZON|VZW|T-MOBILE|TMOBILE|AT&T|ATT|SPRINT|MINT MOBILE|"
        "CRICKET WIRELESS|VISIBLE|GOOGLE FI|US CELLULAR|METRO BY T-MOBILE|METROPCS|"
        "BOOST MOBILE|STRAIGHT TALK|TRACFONE",
        "phone_data",
        0.9,
        note="Phone plan. Deduct the business-use share.",
    ),
    *brands(
        "COMCAST|XFINITY|SPECTRUM|COX COMM|OPTIMUM|FRONTIER COMM|CENTURYLINK|VERIZON FIOS",
        None,
        0.0,
        note="Home internet / cable is usually personal for drivers.",
        suggestions=("personal", "phone_data"),
    ),
    *brands(
        "PG&E|PGANDE|CON EDISON|CONED|DUKE ENERGY|SOCALGAS|SO CAL GAS|SOUTHERN CALIFORNIA EDISON|"
        "XCEL ENERGY|COMED|NATIONAL GRID|GEORGIA POWER|FPL|DOMINION ENERGY",
        "personal",
        0.88,
        note="Home utilities are personal.",
    ),
    # --- Apps, software & tax prep --------------------------------------------------
    *brands(
        "GRIDWISE|MYSTRO|EVERLANCE|MILEIQ|HURDLR|TRIPLOG|QUICKBOOKS|QBOOKS|INTUIT QBO|TURBOTAX|"
        "INTUIT TURBOTAX|H&R BLOCK|HRBLOCK|TAXACT|FREETAXUSA|KEEPER TAX|SOLO APP|WAVE FINANCIAL",
        "software_services",
        0.92,
    ),
    # --- Licences, registration, background checks ---------------------------------
    *brands(
        "DMV|DEPT OF MOTOR|MOTOR VEHICLE|MVD|TAG OFFICE|TAG AGENCY|VEHICLE REGISTRATION|"
        "CHECKR|STERLING INFOTRACK|STERLING TALENT|HIRERIGHT|GOODHIRE|NYC TLC|LIVESCAN|"
        "DRIVING RECORD",
        "licenses_fees",
        0.9,
    ),
    # --- Driver supplies -------------------------------------------------------------
    *brands(
        "IOTTIE|ANKER|BELKIN|ULINE|SCOSCHE|SPIGEN",
        "supplies",
        0.85,
    ),
    # --- Personal spending -----------------------------------------------------------
    pattern(
        "Uber Eats / Uber rides",
        r"\bUBER ?(?:EATS|TRIP|ONE|RIDES?)\b|\bUBEREATS\b",
        "personal",
        0.9,
        note="Ordering food or taking a ride yourself is personal.",
    ),
    *brands(
        "UBER|LYFT|DOORDASH|DOOR DASH|DASHPASS|GRUBHUB|INSTACART|POSTMATES|SEAMLESS|CAVIAR",
        "personal",
        0.82,
        note="Paying a delivery/ride app as a customer is personal spending.",
    ),
    *brands(
        "KROGER|SAFEWAY|WHOLE FOODS|WFM|TRADER JOE|ALDI|PUBLIX|HEB|H-E-B|WEGMANS|FOOD LION|"
        "GIANT EAGLE|MEIJER|SPROUTS|ALBERTSONS|VONS|RALPHS|PIGGLY WIGGLY|HARRIS TEETER|"
        "STOP & SHOP|SHOPRITE|WINCO|FOOD 4 LESS|SMART & FINAL|LIDL",
        "personal",
        0.88,
        note="Groceries are personal.",
    ),
    *brands(
        "MCDONALDS|MCDONALD'S|STARBUCKS|CHIPOTLE|TACO BELL|CHICK-FIL-A|SUBWAY|WENDYS|"
        "BURGER KING|DUNKIN|PANERA|DOMINOS|PIZZA HUT|KFC|IN-N-OUT|FIVE GUYS|SHAKE SHACK|"
        "PANDA EXPRESS|POPEYES|SONIC DRIVE|DENNYS|IHOP|OLIVE GARDEN|APPLEBEES|JACK IN THE BOX|"
        "DUTCH BROS|PEETS|TIM HORTONS|WHATABURGER|ARBYS|CARLS JR|DEL TACO|WINGSTOP",
        "personal",
        0.88,
        note="Meals while driving locally are not deductible.",
    ),
    *brands(
        "NETFLIX|HULU|DISNEY PLUS|DISNEYPLUS|SPOTIFY|HBO MAX|PEACOCK|PARAMOUNT|YOUTUBE TV|"
        "YOUTUBE PREMIUM|APPLE MUSIC|AUDIBLE|XBOX|PLAYSTATION|NINTENDO|STEAM GAMES|STEAMPOWERED|"
        "SIRIUSXM|SIRIUS XM",
        "personal",
        0.88,
        note="Entertainment subscriptions are personal.",
    ),
    *brands(
        "PLANET FITNESS|LA FITNESS|24 HOUR FITNESS|ANYTIME FITNESS|EQUINOX|AMC|REGAL|CINEMARK|"
        "FANDANGO|TICKETMASTER",
        "personal",
        0.88,
    ),
    # --- Ambiguous merchants: always asked -------------------------------------------
    *brands(
        "AMAZON|AMZN|AMAZON MKTPL|AMZN MKTP|WALMART|WAL-MART|WM SUPERCENTER|TARGET|COSTCO|"
        "COSTCO WHSE|SAMS CLUB|BJS WHOLESALE|BEST BUY|HOME DEPOT|LOWES|DOLLAR TREE|"
        "DOLLAR GENERAL|EBAY|ETSY|TEMU|STAPLES|OFFICE DEPOT|CVS|WALGREENS|RITE AID|APPLE.COM",
        None,
        0.0,
        note="This store sells both business and personal items.",
        suggestions=("supplies", "personal"),
    ),
    *brands(
        "7-ELEVEN|SPEEDY STOP|AM PM MARKET",
        None,
        0.0,
        note="Convenience store that may also sell fuel.",
        suggestions=("fuel", "personal"),
    ),
    *brands(
        "VENMO|ZELLE|CASH APP|CASHAPP|SQUARE CASH|PAYPAL",
        None,
        0.0,
        direction=ANY,
        note="Person-to-person payment - only you know what it was for.",
        suggestions=("personal", "transfer", "vehicle_maintenance"),
    ),
    *brands(
        "UBER|LYFT|DOORDASH|DOOR DASH|INSTACART|GRUBHUB|SHIPT",
        None,
        0.0,
        direction=IN,
        note="Money from a gig platform without a payout label - earnings or a customer refund?",
        suggestions=("platform_income", "personal"),
    ),
    pattern(
        "Deposit",
        r"\b(?:MOBILE |REMOTE |ATM |BRANCH )?(?:CHECK )?DEPOSIT\b",
        None,
        0.0,
        direction=IN,
        note="A deposit with no payer named.",
        suggestions=("other_income", "transfer"),
    ),
]


@dataclass(frozen=True, slots=True)
class Keyword:
    pattern: re.Pattern[str]
    category: str
    confidence: float


def _kw(regex: str, category: str, confidence: float) -> Keyword:
    return Keyword(re.compile(regex), category, confidence)


KEYWORD_RULES: list[Keyword] = [
    _kw(r"\bTOLLS?\b|\bTOLLWAY\b|\bTURNPIKE\b|\bBRIDGE\b.*\bAUTHORITY\b", "tolls_parking", 0.82),
    _kw(r"\bPARKING\b|\bPARK METER\b|\bMETER\b.*\bPARK", "tolls_parking", 0.8),
    _kw(r"\bCAR ?WASH\b|\bAUTO ?WASH\b|\bDETAILING\b", "vehicle_maintenance", 0.84),
    _kw(
        r"\bAUTO ?(?:REPAIR|SERVICE|BODY|PARTS|CARE|GLASS)\b|\bOIL CHANGE\b|\bLUBE\b|\bTIRES?\b|"
        r"\bBRAKES?\b|\bMUFFLER\b|\bTRANSMISSION\b|\bCOLLISION\b|\bBODY SHOP\b|\bMECHANIC\b",
        "vehicle_maintenance",
        0.8,
    ),
    _kw(r"\bSMOG\b|\bEMISSIONS?\b|\bVEHICLE INSPECTION\b|\bREGISTRATION\b", "licenses_fees", 0.8),
    _kw(
        r"\bFUEL\b|\bGAS STATION\b|\bGASOLINE\b|\bDIESEL\b|\bPETRO(?:LEUM)?\b|\bEV CHARG\w*",
        "fuel",
        0.72,
    ),
    _kw(r"\bWIRELESS\b|\bCELLULAR\b|\bMOBILE PLAN\b", "phone_data", 0.72),
    _kw(r"\bAUTO INS(?:URANCE)?\b|\bCAR INSURANCE\b", "vehicle_insurance", 0.82),
    _kw(r"\bINSURANCE\b|\bINS PREM\b", "vehicle_insurance", 0.6),
    _kw(r"\bGROCERY\b|\bGROCERIES\b|\bSUPERMARKET\b", "personal", 0.74),
    _kw(
        r"\bRESTAURANT\b|\bCAFE\b|\bCOFFEE\b|\bPIZZA\b|\bGRILL\b|\bBURGER\b|\bTACOS?\b|\bDINER\b|"
        r"\bBAKERY\b|\bSUSHI\b|\bKITCHEN\b|\bBISTRO\b|\bDELI\b|\bTAQUERIA\b",
        "personal",
        0.68,
    ),
]

# Words that mark money coming back from a merchant rather than new income.
REFUND_MARKERS = re.compile(
    r"\b(?:REFUND(?:ED)?|RETURN(?:ED)?|RETURNS|CREDIT VOUCHER|MERCHANDISE CREDIT|REVERSAL|REVERSED|"
    r"CHARGEBACK|DISPUTE(?:D)? CREDIT|ADJUSTMENT|PRICE ADJ\w*|RFND|CR ADJ)\b"
)

# Category labels exported by common banks (Chase, Amex, Capital One, Discover...).
# Weak evidence only: banks use broad, sometimes wrong, buckets.
BANK_CATEGORY_HINTS: dict[str, str] = {
    "gas": "fuel",
    "gas/automotive": "fuel",
    "gas stations": "fuel",
    "fuel": "fuel",
    "automotive": "vehicle_maintenance",
    "auto & transport": "vehicle_maintenance",
    "parking": "tolls_parking",
    "tolls": "tolls_parking",
    "food & drink": "personal",
    "restaurants": "personal",
    "dining": "personal",
    "groceries": "personal",
    "supermarkets": "personal",
    "entertainment": "personal",
    "health & wellness": "personal",
    "personal": "personal",
    "home": "personal",
    "education": "personal",
    "gifts & donations": "personal",
    "fees & adjustments": "bank_fees",
    "fees": "bank_fees",
    "fee/interest charge": "bank_fees",
    "interest": "bank_fees",
    "payment": "transfer",
    "payment/credit": "transfer",
    "transfer": "transfer",
    "phone": "phone_data",
    "phone/cable": "phone_data",
}
