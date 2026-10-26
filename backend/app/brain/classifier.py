"""The brain: decide a category for one transaction, or admit it is not sure.

Order of evidence, strongest first:
  1. rules the user saved by correcting an earlier statement
  2. structure of the line (card payment, transfer, fee, payout), which is not spending
  3. known merchants, with the longest matching phrase winning
  4. ambiguous merchants (Amazon, PayPal...) which always go to review with candidates
  5. weak keywords (CAFE, HOTEL...) which only produce a suggestion, never a decision
  6. anything else is unknown and goes to review

Nothing here calls out to a model or a network service: the same input always gives the
same decision, and every decision carries the reasons behind it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from app.brain.categories import (
    BANK_FEES,
    CARD_PAYMENT,
    CATEGORIES,
    INCOME,
    NEEDS_REVIEW,
    TRANSFER,
)
from app.brain.normalize import Normalized, normalize
from app.brain.rules import Rule, RuleKind, RuleTable
from app.domain.models import Flag

_CARD_PAYMENT_IN = re.compile(
    r"\b(PAYMENT\b.{0,20}\bTHANK|AUTO ?PAY|ONLINE PAYMENT|PAYMENT RECEIVED|MOBILE PAYMENT|"
    r"ACH PAYMENT|BILL PAYMENT|ELECTRONIC PAYMENT|PAYMENT - )"
)
_CARD_PAYMENT_OUT = re.compile(
    r"\b(CREDIT CARD PAYMENT|CARD PAYMENT|PAYMENT TO .{0,30}\bCARD|AMEX EPAYMENT|CARD SERVICES)\b"
)
_TRANSFER = re.compile(r"\b(TRANSFER|XFER|TFR)\b")
_OWN_ACCOUNT = re.compile(
    r"\b(SAVINGS|CHECKING|CURRENT ACCOUNT|INTERNAL|OWN ACCOUNT|BROKERAGE|RESERVE|TAX ACCOUNT|"
    r"MONEY MARKET|BUSINESS ACCOUNT)\b"
)
_FEE = re.compile(
    r"\b(INTEREST CHARGE[D]?|FINANCE CHARGE|LATE FEE|LATE PAYMENT FEE|ANNUAL FEE|MEMBERSHIP FEE|"
    r"FOREIGN TRANSACTION FEE|FX FEE|SERVICE FEE|SERVICE CHARGE|MONTHLY FEE|MAINTENANCE FEE|"
    r"OVERDRAFT|NSF FEE|WIRE FEE|ATM FEE|PURCHASE INTEREST|CASH ADVANCE FEE)\b"
)
_INCOME_IN = re.compile(r"\b(INVOICE|PAYOUT|CLIENT PAYMENT|CLIENT|PAYROLL|SALARY|CONSULTING FEE)\b")
_DEPOSIT_IN = re.compile(r"\b(DEPOSIT|DIRECT DEP|ACH CREDIT|INTEREST PAID|INTEREST EARNED)\b")
REFUND_WORDS = re.compile(
    r"\b(REFUND|REFUNDED|RETURN|RETURNED|REVERSAL|REVERSED|CHARGEBACK|CASHBACK|CASH BACK|REBATE|"
    r"STATEMENT CREDIT|CREDIT ADJUSTMENT|PRICE ADJUSTMENT|PURCHASE CREDIT|MERCHANT CREDIT|"
    r"CREDIT VOUCHER)\b"
)


class UserRuleLookup(Protocol):
    def get(self, key: str) -> str | None: ...


class _NoUserRules:
    def get(self, key: str) -> str | None:
        return None


@dataclass
class Decision:
    category_id: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    refund_candidate: bool = False  # money in that is probably a refund of an earlier purchase


def _name(category_id: str) -> str:
    return CATEGORIES[category_id].name


def _upper(description: str) -> str:
    return re.sub(r"\s+", " ", description.upper().replace("'", "")).strip()


class Classifier:
    def __init__(self, rules: RuleTable, user_rules: UserRuleLookup | None = None):
        self._rules = rules
        self._user_rules: UserRuleLookup = user_rules or _NoUserRules()

    def classify(self, description: str, *, money_in: bool) -> tuple[Decision, Normalized]:
        upper = _upper(description)
        if money_in:
            # "REFUND ADOBE" and "ADOBE CREATIVE CLOUD" should share one merchant key.
            cleaned = REFUND_WORDS.sub(" ", upper)
            norm = normalize(cleaned if cleaned.strip() else description)
        else:
            norm = normalize(description)

        saved = self._user_rules.get(norm.key)
        if saved is not None and saved in CATEGORIES:
            return (
                Decision(
                    saved,
                    1.0,
                    [f"Matches a rule you saved for {norm.key!r}: {_name(saved)}"],
                ),
                norm,
            )

        decision = self._money_in(upper, norm) if money_in else self._money_out(upper, norm)
        return decision, norm

    # -- money in -------------------------------------------------------------------------

    def _money_in(self, upper: str, norm: Normalized) -> Decision:
        if _CARD_PAYMENT_IN.search(upper):
            return Decision(
                CARD_PAYMENT,
                0.95,
                ["Payment toward the card balance, which is not spending"],
            )
        if _INCOME_IN.search(upper) and not REFUND_WORDS.search(upper):
            return Decision(
                INCOME, 0.85, ["Looks like a client payment or payout (invoice, payout, client)"]
            )
        if _TRANSFER.search(upper):
            return self._transfer(upper, direction="in")
        if REFUND_WORDS.search(upper):
            decision = self._merchant(norm, money_in=True)
            decision.refund_candidate = True
            decision.flags.append(Flag.REFUND)
            decision.reasons.insert(
                0, "Money back from a merchant, so it is a refund and not income"
            )
            return decision
        if _DEPOSIT_IN.search(upper):
            return Decision(
                NEEDS_REVIEW,
                0.5,
                ["A deposit could be client income or something else; the statement does not say"],
                suggestions=[INCOME],
            )
        decision = self._merchant(norm, money_in=True)
        if decision.category_id != NEEDS_REVIEW:
            # Known merchant paying you: almost always a refund, but only the original can confirm.
            decision.refund_candidate = True
            decision.flags.append(Flag.REFUND)
            decision.reasons.insert(0, "Money in from a known merchant, treated as a refund")
            return decision
        decision.refund_candidate = True
        decision.flags.append(Flag.REFUND)
        decision.reasons.insert(
            0, "Money in from an unrecognised source; it may be a refund, income or a transfer"
        )
        return decision

    # -- money out ------------------------------------------------------------------------

    def _money_out(self, upper: str, norm: Normalized) -> Decision:
        if _FEE.search(upper):
            return Decision(BANK_FEES, 0.95, ["Bank or card fee or interest charge"])
        if _CARD_PAYMENT_OUT.search(upper):
            return Decision(
                CARD_PAYMENT, 0.9, ["Payment to a credit card account, which is not spending"]
            )
        if _TRANSFER.search(upper):
            own = _OWN_ACCOUNT.search(upper) is not None
            merchant = self._merchant(norm, money_in=False)
            if own or merchant.category_id == NEEDS_REVIEW and not merchant.suggestions:
                return self._transfer(upper, direction="out")
            return merchant
        return self._merchant(norm, money_in=False)

    def _transfer(self, upper: str, *, direction: str) -> Decision:
        if _OWN_ACCOUNT.search(upper):
            return Decision(
                TRANSFER, 0.95, ["Move of money between your own accounts, which is not spending"]
            )
        return Decision(
            NEEDS_REVIEW,
            0.6,
            [
                "A transfer, but the statement does not say if it is between your own accounts "
                "or a payment to someone else"
            ],
            suggestions=[TRANSFER],
        )

    # -- merchants ------------------------------------------------------------------------

    def _merchant(self, norm: Normalized, *, money_in: bool) -> Decision:
        matches = self._rules.match(norm.all_tokens)
        strong = [r for r in matches if r.kind is not RuleKind.KEYWORD]
        if strong:
            return self._from_strong(strong, norm)
        keywords = [r for r in matches if r.kind is RuleKind.KEYWORD]
        if keywords:
            return self._from_keywords(keywords)
        return Decision(
            NEEDS_REVIEW,
            0.0,
            [f"Merchant {norm.key!r} is not recognised"],
        )

    def _from_strong(self, strong: list[Rule], norm: Normalized) -> Decision:
        top = max(r.specificity for r in strong)
        best = [r for r in strong if r.specificity == top]
        brands = [r for r in best if r.kind is RuleKind.BRAND]
        ambiguous = [r for r in best if r.kind is RuleKind.AMBIGUOUS]
        brand_categories = {r.category for r in brands if r.category}

        if brands and not ambiguous and len(brand_categories) == 1:
            rule = brands[0]
            assert rule.category is not None
            return Decision(
                rule.category,
                rule.confidence,
                [f"Known merchant {rule.text!r}: {_name(rule.category)}"],
            )

        candidates: list[str] = []
        for rule in ambiguous:
            candidates.extend(rule.candidates)
        candidates.extend(sorted(c for c in brand_categories if c))
        unique = list(dict.fromkeys(candidates))
        note = ambiguous[0].note if ambiguous else "Matches merchants from more than one category"
        label = ambiguous[0].text if ambiguous else norm.key
        names = " or ".join(_name(c) for c in unique)
        return Decision(
            NEEDS_REVIEW,
            0.5,
            [f"{label!r} is ambiguous: could be {names}. {note}."],
            flags=[Flag.AMBIGUOUS_MERCHANT],
            suggestions=unique,
        )

    def _from_keywords(self, keywords: list[Rule]) -> Decision:
        keywords = sorted(keywords, key=lambda r: (r.confidence, r.specificity), reverse=True)
        best = keywords[0]
        assert best.category is not None
        suggestions = list(dict.fromkeys(r.category for r in keywords if r.category))
        return Decision(
            NEEDS_REVIEW,
            best.confidence,
            [
                f"Looks like {_name(best.category)} (matched {best.text!r}) but the merchant "
                "is not recognised, so please confirm"
            ],
            suggestions=suggestions,
        )
