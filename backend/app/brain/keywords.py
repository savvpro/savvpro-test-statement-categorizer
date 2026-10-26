"""Keyword-based scoring rules applied to normalized merchant names.

Weights:
  strong_keyword = 0.85
  weak_keyword   = 0.65
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordRule:
    category_slug: str
    confidence: float
    pattern: str  # substring to search (uppercase)


# Order matters – first match on same slug wins; cross-slug, all apply and scorer picks highest
KEYWORD_RULES: list[KeywordRule] = [
    # ── Software ──────────────────────────────────────────────────────────────
    KeywordRule("software", 0.85, "SOFTWARE"),
    KeywordRule("software", 0.85, "SUBSCR"),
    KeywordRule("software", 0.85, "SAAS"),
    KeywordRule("software", 0.85, "CLOUD"),
    KeywordRule("software", 0.75, "APP"),
    KeywordRule("software", 0.75, "DIGITAL"),
    KeywordRule("software", 0.75, "PLUGIN"),
    # ── Advertising ───────────────────────────────────────────────────────────
    KeywordRule("advertising", 0.85, "ADVERTISING"),
    KeywordRule("advertising", 0.85, "MARKETING"),
    KeywordRule("advertising", 0.75, "PROMO"),
    KeywordRule("advertising", 0.75, "CAMPAIGN"),
    # ── Travel ────────────────────────────────────────────────────────────────
    KeywordRule("travel", 0.85, "AIRLINE"),
    KeywordRule("travel", 0.85, "AIRWAYS"),
    KeywordRule("travel", 0.85, "HOTEL"),
    KeywordRule("travel", 0.85, "RESORT"),
    KeywordRule("travel", 0.85, "MOTEL"),
    KeywordRule("travel", 0.85, "INN"),
    KeywordRule("travel", 0.75, "RENTAL CAR"),
    KeywordRule("travel", 0.75, "CAR RENTAL"),
    KeywordRule("travel", 0.75, "PARKING"),
    KeywordRule("travel", 0.65, "TAXI"),
    KeywordRule("travel", 0.65, "TRANSIT"),
    KeywordRule("travel", 0.65, "TRANSPORT"),
    # ── Meals ─────────────────────────────────────────────────────────────────
    KeywordRule("meals", 0.85, "RESTAURANT"),
    KeywordRule("meals", 0.85, "CAFE"),
    KeywordRule("meals", 0.85, "COFFEE"),
    KeywordRule("meals", 0.85, "BAKERY"),
    KeywordRule("meals", 0.85, "BISTRO"),
    KeywordRule("meals", 0.85, "DINER"),
    KeywordRule("meals", 0.85, "BAR & GRILL"),
    KeywordRule("meals", 0.75, "SUSHI"),
    KeywordRule("meals", 0.75, "PIZZA"),
    KeywordRule("meals", 0.75, "BURGER"),
    KeywordRule("meals", 0.75, "GRILL"),
    KeywordRule("meals", 0.75, "KITCHEN"),
    KeywordRule("meals", 0.75, "EATERY"),
    KeywordRule("meals", 0.65, "FOOD"),
    KeywordRule("meals", 0.65, "DELI"),
    # ── Legal & Professional ───────────────────────────────────────────────────
    KeywordRule("legal_professional", 0.85, "LAW"),
    KeywordRule("legal_professional", 0.85, "ATTORNEY"),
    KeywordRule("legal_professional", 0.85, "LEGAL"),
    KeywordRule("legal_professional", 0.85, "NOTARY"),
    KeywordRule("legal_professional", 0.85, "ACCOUNTING"),
    KeywordRule("legal_professional", 0.85, "CPA"),
    KeywordRule("legal_professional", 0.75, "CONSULTING"),
    KeywordRule("legal_professional", 0.75, "CONSULTANT"),
    # ── Office / Supplies ──────────────────────────────────────────────────────
    KeywordRule("office_expense", 0.85, "PRINT"),
    KeywordRule("office_expense", 0.85, "COPY CENTER"),
    KeywordRule("office_expense", 0.85, "SHIPPING"),
    KeywordRule("office_expense", 0.85, "POSTAGE"),
    KeywordRule("office_expense", 0.85, "FREIGHT"),
    KeywordRule("supplies", 0.75, "SUPPLIES"),
    KeywordRule("supplies", 0.65, "STORE"),
    # ── Utilities ─────────────────────────────────────────────────────────────
    KeywordRule("utilities", 0.85, "INTERNET"),
    KeywordRule("utilities", 0.85, "WIRELESS"),
    KeywordRule("utilities", 0.85, "CELLULAR"),
    KeywordRule("utilities", 0.85, "MOBILE"),
    KeywordRule("utilities", 0.75, "ELECTRIC"),
    KeywordRule("utilities", 0.75, "GAS CO"),
    KeywordRule("utilities", 0.75, "WATER SVC"),
    # ── Education ─────────────────────────────────────────────────────────────
    KeywordRule("education", 0.85, "LEARNING"),
    KeywordRule("education", 0.85, "TRAINING"),
    KeywordRule("education", 0.85, "COURSE"),
    KeywordRule("education", 0.85, "BOOTCAMP"),
    KeywordRule("education", 0.75, "ACADEMY"),
    KeywordRule("education", 0.75, "SEMINAR"),
    KeywordRule("education", 0.75, "CONFERENCE"),
    KeywordRule("education", 0.65, "WORKSHOP"),
    # ── Insurance ─────────────────────────────────────────────────────────────
    KeywordRule("insurance", 0.85, "INSURANCE"),
    KeywordRule("insurance", 0.85, "INSUR"),
    # ── Rent ──────────────────────────────────────────────────────────────────
    KeywordRule("rent_cowork", 0.85, "COWORK"),
    KeywordRule("rent_cowork", 0.85, "CO-WORK"),
    KeywordRule("rent_cowork", 0.75, "SHARED OFFICE"),
    # ── Equipment ─────────────────────────────────────────────────────────────
    KeywordRule("equipment", 0.75, "CAMERA"),
    KeywordRule("equipment", 0.75, "LAPTOP"),
    KeywordRule("equipment", 0.75, "MONITOR"),
    KeywordRule("equipment", 0.75, "MICROPHONE"),
    KeywordRule("equipment", 0.65, "HARDWARE"),
    # ── Bank fees ─────────────────────────────────────────────────────────────
    KeywordRule("bank_fees", 0.85, "SERVICE FEE"),
    KeywordRule("bank_fees", 0.85, "MONTHLY FEE"),
    KeywordRule("bank_fees", 0.85, "ANNUAL FEE"),
    KeywordRule("bank_fees", 0.85, "FOREIGN TRANSACTION"),
    KeywordRule("bank_fees", 0.85, "WIRE FEE"),
    KeywordRule("bank_fees", 0.75, "OVERDRAFT"),
    KeywordRule("bank_fees", 0.65, "NSF"),
]
