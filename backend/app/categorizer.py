"""
Rule-based transaction categorizer for freelance software engineers.

This is the "brain". It never calls a large language model.
All decisions are deterministic Python rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

CATEGORY_SOFTWARE = "Software & Subscriptions"
CATEGORY_CLOUD = "Cloud & Infrastructure"
CATEGORY_HARDWARE = "Hardware & Equipment"
CATEGORY_TRAVEL = "Travel & Transportation"
CATEGORY_MEALS = "Meals & Entertainment"
CATEGORY_OFFICE = "Office & Co-working"
CATEGORY_PROFESSIONAL = "Professional Services"
CATEGORY_MARKETING = "Marketing & Advertising"
CATEGORY_BANK = "Bank Fees & Transfers"
CATEGORY_INCOME = "Income"
CATEGORY_REFUNDS = "Refunds & Chargebacks"
CATEGORY_PERSONAL = "Personal"
CATEGORY_NEEDS_REVIEW = "Needs Review"


ALL_CATEGORIES = [
    CATEGORY_SOFTWARE,
    CATEGORY_CLOUD,
    CATEGORY_HARDWARE,
    CATEGORY_TRAVEL,
    CATEGORY_MEALS,
    CATEGORY_OFFICE,
    CATEGORY_PROFESSIONAL,
    CATEGORY_MARKETING,
    CATEGORY_BANK,
    CATEGORY_INCOME,
    CATEGORY_REFUNDS,
    CATEGORY_PERSONAL,
    CATEGORY_NEEDS_REVIEW,
]


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

# High-confidence exact / strong patterns (order matters within a group)
RULES: list[tuple[str, list[str]]] = [
    # Income sources first (positive amounts usually)
    (
        CATEGORY_INCOME,
        [
            r"\bSTRIPE\b",
            r"\bPAYPAL\b.*PAYOUT",
            r"\bPAYPAL\b.*TRANSFER",
            r"\bGUSTO\b",
            r"\bDEEL\b",
            r"\bWISE\b.*PAYMENT",
            r"\bCLIENT\b.*PAYMENT",
            r"\bINVOICE\b.*PAID",
            r"\bACH\b.*CREDIT",
            r"\bDIRECT\s+DEPOSIT\b",
        ],
    ),
    # Refunds / credits (usually positive amount coming back)
    (
        CATEGORY_REFUNDS,
        [
            r"\bREFUND\b",
            r"\bRETURN\b",
            r"\bCREDIT\b",
            r"\bCHARGEBACK\b",
            r"\bREVERSAL\b",
            r"\bCASHBACK\b",
        ],
    ),
    # Bank / transfers
    (
        CATEGORY_BANK,
        [
            r"\bTRANSFER\b",
            r"\bACH\b",
            r"\bWIRE\b",
            r"\bFEE\b",
            r"\bINTEREST\b",
            r"\bOVERDRAFT\b",
            r"\bPAYMENT\s+TO\b",
            r"\bPAYMENT\s+FROM\b",
            r"\bZELLE\b",
            r"\bVENMO\b",
            r"\bCASH\s+APP\b",
        ],
    ),
    # Software & SaaS
    (
        CATEGORY_SOFTWARE,
        [
            r"\bADOBE\b",
            r"\bGITHUB\b",
            r"\bVERCEL\b",
            r"\bNETLIFY\b",
            r"\bFIGMA\b",
            r"\bNOTION\b",
            r"\bLINEAR\.APP\b",
            r"\bLINEAR\b",
            r"\bSLACK\b",
            r"\bZOOM\.US\b",
            r"\bZOOM\b",
            r"\bOPENAI\b",
            r"\bCHATGPT\b",
            r"\bANTHROPIC\b",
            r"\bCLAUDE\.AI\b",
            r"\bCURSOR\.SH\b",
            r"\bCURSOR\b",
            r"\bJETBRAINS\b",
            r"\bINTELLIJ\b",
            r"\bPYCHARM\b",
            r"\bWEBSTORM\b",
            r"\bSUBLIME\b",
            r"\bPOSTMAN\b",
            r"\b1PASSWORD\b",
            r"\bLASTPASS\b",
            r"\bBITWARDEN\b",
            r"\bDROPBOX\b",
            r"\bGOOGLE\s+WORKSPACE\b",
            r"\bGSUITE\b",
            r"\bMICROSOFT\s+365\b",
            r"\bOFFICE\s+365\b",
            r"\bCANVA\b",
            r"\bGRAMMARLY\b",
            r"\bHEROKU\b",  # sometimes treated as software platform
            r"\bRENDER\.COM\b",
            r"\bRAILWAY\.APP\b",
            r"\bSUPABASE\b",
            r"\bPLANETSCALE\b",
            r"\bMONGODB\b",
            r"\bREDIS\b",
            r"\bDATADOG\b",
            r"\bSENTRY\b",
            r"\bNEW\s+RELIC\b",
        ],
    ),
    # Cloud & infrastructure
    (
        CATEGORY_CLOUD,
        [
            r"\bAMAZON\s+WEB\s+SERVICES\b",
            r"\bAWS\b",
            r"\bAMAZON\s+AWS\b",
            r"\bDIGITALOCEAN\b",
            r"\bDIGITAL\s+OCEAN\b",
            r"\bCLOUDFLARE\b",
            r"\bGOOGLE\s+CLOUD\b",
            r"\bGCP\b",
            r"\bMICROSOFT\s+AZURE\b",
            r"\bAZURE\b",
            r"\bLINODE\b",
            r"\bVULTR\b",
            r"\bOVH\b",
            r"\bHETZNER\b",
            r"\bFASTLY\b",
            r"\bAKAMAI\b",
        ],
    ),
    # Hardware
    (
        CATEGORY_HARDWARE,
        [
            r"\bAPPLE\.COM\b",
            r"\bAPPLE\s+STORE\b",
            r"\bBEST\s+BUY\b",
            r"\bBESTBUY\b",
            r"\bMICRO\s+CENTER\b",
            r"\bNEWEGG\b",
            r"\bBH\s+PHOTO\b",
            r"\bB&H\b",
            r"\bAMAZON\.COM\b.*(?:MACBOOK|IPHONE|IPAD|MONITOR|KEYBOARD|MOUSE|SSD|RAM)",
            r"\bLENOVO\b",
            r"\bDELL\b",
            r"\bHP\.COM\b",
            r"\bFRAMEWORK\b",  # Framework laptop
        ],
    ),
    # Travel
    (
        CATEGORY_TRAVEL,
        [
            r"\bUBER\b",
            r"\bLYFT\b",
            r"\bUNITED\s+AIRLINES\b",
            r"\bUNITED\b",
            r"\bDELTA\b",
            r"\bAMERICAN\s+AIRLINES\b",
            r"\bSOUTHWEST\b",
            r"\bJETBLUE\b",
            r"\bAIRBNB\b",
            r"\bHOTELS\.COM\b",
            r"\bBOOKING\.COM\b",
            r"\bEXPEDIA\b",
            r"\bAMTRAK\b",
            r"\bHERTZ\b",
            r"\bENTERPRISE\b",
            r"\bAVIS\b",
            r"\bMARRIOTT\b",
            r"\bHILTON\b",
            r"\bHYATT\b",
        ],
    ),
    # Meals – only well-known chains (broad words like CAFE go to Needs Review)
    (
        CATEGORY_MEALS,
        [
            r"\bSTARBUCKS\b",
            r"\bDOORDASH\b",
            r"\bUBER\s+EATS\b",
            r"\bGRUBHUB\b",
            r"\bPOSTMATES\b",
            r"\bCHIPOTLE\b",
            r"\bSWEETGREEN\b",
            r"\bMCDONALD\b",
            r"\bSUBWAY\b",
        ],
    ),
    # Office / co-working
    (
        CATEGORY_OFFICE,
        [
            r"\bWEWORK\b",
            r"\bREGUS\b",
            r"\bINDUSTRIOUS\b",
            r"\bSTAPLES\b",
            r"\bOFFICE\s+DEPOT\b",
            r"\bUPS\s+STORE\b",
            r"\bFEDEX\s+OFFICE\b",
            r"\bCOMCAST\b",
            r"\bVERIZON\b",
            r"\bAT&T\b",
            r"\bSPECTRUM\b",
            r"\bGOOGLE\s+FIBER\b",
        ],
    ),
    # Professional services
    (
        CATEGORY_PROFESSIONAL,
        [
            r"\bUPWORK\b",
            r"\bFIVERR\b",
            r"\bLEGALZOOM\b",
            r"\bROCKET\s+LAWYER\b",
            r"\bACCOUNTANT\b",
            r"\bCPA\b",
            r"\bLAWYER\b",
            r"\bATTORNEY\b",
            r"\bCONSULTING\b",
        ],
    ),
    # Marketing
    (
        CATEGORY_MARKETING,
        [
            r"\bGOOGLE\s+ADS\b",
            r"\bGOOGLE\s+ADWORDS\b",
            r"\bMETA\s+ADS\b",
            r"\bFACEBOOK\s+ADS\b",
            r"\bLINKEDIN\s+ADS\b",
            r"\bTWITTER\s+ADS\b",
            r"\bX\s+ADS\b",
            r"\bNAMECHEAP\b",
            r"\bGODADDY\b",
            r"\bGOOGLE\s+DOMAINS\b",
            r"\bCLOUDFLARE\s+REGISTRAR\b",
            r"\bMAILCHIMP\b",
            r"\bKLAVIYO\b",
            r"\bCONVERTKIT\b",
        ],
    ),
    # Personal (common personal merchants that sometimes appear on business cards)
    (
        CATEGORY_PERSONAL,
        [
            r"\bNETFLIX\b",
            r"\bSPOTIFY\b",
            r"\bHULU\b",
            r"\bDISNEY\+\b",
            r"\bAMAZON\s+PRIME\b",
            r"\bWHOLE\s+FOODS\b",
            r"\bTRADER\s+JOE\b",
            r"\bCOSTCO\b",
            r"\bWALMART\b",
            r"\bTARGET\b",
            r"\bCVS\b",
            r"\bWALGREENS\b",
        ],
    ),
]


@dataclass
class CategorizationResult:
    category: str
    confidence: str  # "high" | "medium" | "low"
    reason: str
    normalized_description: str


def normalize_description(raw: str) -> str:
    """Clean transaction description for matching."""
    if not raw:
        return ""

    text = raw.upper().strip()

    # Remove common noise
    text = re.sub(r"[*#]+", " ", text)
    text = re.sub(r"\b\d{4,}\b", " ", text)          # long numbers / transaction ids
    text = re.sub(r"\b\d{1,2}/\d{1,2}\b", " ", text)  # dates
    text = re.sub(r"\b[A-Z]{2}\s+\d{5}\b", " ", text)  # state + zip
    text = re.sub(r"\s+", " ", text).strip()

    return text


def categorize_transaction(
    description: str,
    amount: float,
    date: Optional[str] = None,
) -> CategorizationResult:
    """
    Main entry point of the brain.

    Returns a category + confidence + human-readable reason.
    Never guesses when unsure → "Needs Review".
    """
    normalized = normalize_description(description)

    if not normalized:
        return CategorizationResult(
            category=CATEGORY_NEEDS_REVIEW,
            confidence="low",
            reason="Empty or unreadable description",
            normalized_description=normalized,
        )

    # ------------------------------------------------------------------
    # 1. Special handling for refunds based on amount sign + keywords
    # ------------------------------------------------------------------
    is_credit = amount > 0  # money coming into the account

    for category, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                # Special logic for refunds vs income
                if category == CATEGORY_REFUNDS:
                    if is_credit:
                        return CategorizationResult(
                            category=CATEGORY_REFUNDS,
                            confidence="high",
                            reason=f"Matched refund/credit pattern: {pattern}",
                            normalized_description=normalized,
                        )
                    # Debit that looks like a refund keyword is unusual → review
                    return CategorizationResult(
                        category=CATEGORY_NEEDS_REVIEW,
                        confidence="low",
                        reason=f"Refund keyword found but amount is a debit: {pattern}",
                        normalized_description=normalized,
                    )

                if category == CATEGORY_INCOME:
                    if is_credit:
                        return CategorizationResult(
                            category=CATEGORY_INCOME,
                            confidence="high",
                            reason=f"Matched income source: {pattern}",
                            normalized_description=normalized,
                        )
                    # Debit that looks like income is suspicious
                    return CategorizationResult(
                        category=CATEGORY_NEEDS_REVIEW,
                        confidence="low",
                        reason=f"Income keyword found but amount is a debit: {pattern}",
                        normalized_description=normalized,
                    )

                # Normal expense categories (usually debits)
                return CategorizationResult(
                    category=category,
                    confidence="high",
                    reason=f"Strong match: {pattern}",
                    normalized_description=normalized,
                )

    # ------------------------------------------------------------------
    # 2. No strong rule matched → Needs Review
    # ------------------------------------------------------------------
    return CategorizationResult(
        category=CATEGORY_NEEDS_REVIEW,
        confidence="low",
        reason="No confident rule matched",
        normalized_description=normalized,
    )


def categorize_batch(transactions: list[dict]) -> list[dict]:
    """
    Categorize a list of transactions.

    Expected input shape:
        {"date": "...", "description": "...", "amount": -12.34, ...}

    Returns the same list with added fields:
        category, confidence, reason, normalized_description
    """
    results = []
    for tx in transactions:
        result = categorize_transaction(
            description=tx.get("description", ""),
            amount=float(tx.get("amount", 0)),
            date=tx.get("date"),
        )
        enriched = {
            **tx,
            "category": result.category,
            "confidence": result.confidence,
            "reason": result.reason,
            "normalized_description": result.normalized_description,
        }
        results.append(enriched)
    return results
