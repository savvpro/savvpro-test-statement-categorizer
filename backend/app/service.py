"""Turn a statement file into categorized rows and totals."""

from __future__ import annotations

import uuid
from decimal import Decimal

from .brain import Decision, categorize
from .categories import BUCKETS, EXPENSE_IDS, SELECTABLE_IDS, bucket, label
from .memory import Memory
from .parser import ParseError, parse_statement

MONEY = Decimal("0.01")


class CorrectionError(Exception):
    """The user asked for a category this app does not keep."""


def build_statement(filename: str, text: str, account_type: str, memory: Memory) -> dict:
    parsed = parse_statement(text, account_type)
    saved = memory.as_dict()
    transactions: list[dict] = []
    seen: dict[tuple[str | None, str, str], str] = {}

    for row in parsed.rows:
        decision = categorize(row.description, float(row.amount), saved)
        amount = row.amount
        if decision.sign_flip:
            amount = -abs(amount)
        item = _present_row(row.row_number, row.date, row.description, amount, row.pending, decision)
        if item["amount"] == 0:
            item = _force_review(
                item,
                "The amount is zero, so this row is not in any total.",
                suggestion=decision.category if decision.category != "needs_review" else decision.suggestion,
            )
        if not item["date"]:
            item = _force_review(item, "This row has no date, so confirm it before it counts.", suggestion=item["suggestion"])
        if not item["description"]:
            item = _force_review(item, "The description is empty.", suggestion=None)

        key = (item["date"], item["fingerprint"], f"{Decimal(str(item['amount'])).quantize(MONEY)}")
        if item["fingerprint"] and key in seen:
            item = _force_review(
                item,
                "Same date, merchant, and amount as another row. Confirm it is a second charge before it counts. "
                + item["reason"],
                suggestion=item["category"] if item["category"] != "needs_review" else item["suggestion"],
            )
            item["duplicate"] = True
        else:
            seen[key] = item["id"]
        transactions.append(item)

    return {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "account_type": account_type,
        "warnings": parsed.warnings,
        "transactions": transactions,
        "summary": summarize(transactions),
    }


def apply_correction(
    statement: dict,
    transaction_id: str,
    category: str,
    remember: bool,
    memory: Memory,
) -> dict:
    if category not in SELECTABLE_IDS:
        raise CorrectionError(f"Unknown category {category!r}.")
    target = next((item for item in statement["transactions"] if item["id"] == transaction_id), None)
    if target is None:
        raise KeyError(transaction_id)

    _assign(target, category)
    saved_category = target["offsets_category"] or target["category"]
    if target["category"] == "refund" and target["offsets_category"]:
        saved_category = target["offsets_category"]
    elif target["category"] == "refund":
        saved_category = "refund"

    if remember and target["fingerprint"]:
        memory.put(target["fingerprint"], saved_category)
        for other in statement["transactions"]:
            if other["id"] == target["id"]:
                continue
            if other["needs_review"] and other["fingerprint"] == target["fingerprint"]:
                _assign(other, category)
                other["reason"] = "Set from the merchant you just confirmed."
                other["source"] = "memory"

    statement["summary"] = summarize(statement["transactions"])
    return statement


def summarize(transactions: list[dict]) -> dict:
    totals = {category_id: Decimal("0") for category_id in EXPENSE_IDS}
    counts = {category_id: 0 for category_id in EXPENSE_IDS}
    income = Decimal("0")
    excluded = Decimal("0")
    personal = Decimal("0")
    unassigned_refunds = Decimal("0")
    review_count = 0
    review_total = Decimal("0")

    for item in transactions:
        amount = Decimal(str(item["amount"]))
        if item["needs_review"] or item["duplicate"]:
            review_count += 1
            review_total += abs(amount)
            continue
        if amount == 0:
            continue
        category = item["category"]
        kind = bucket(category)
        if kind == "expense":
            totals[category] += amount
            counts[category] += 1
        elif kind == "refund":
            offset = item.get("offsets_category")
            if offset in totals:
                totals[offset] -= abs(amount)
                counts[offset] += 1
            elif bucket(offset) == "personal":
                personal -= abs(amount)
            else:
                unassigned_refunds += abs(amount)
        elif kind == "income":
            income += abs(amount)
        elif kind == "excluded":
            excluded += abs(amount)
        elif kind == "personal":
            personal += abs(amount)

    categories = []
    for category_id in EXPENSE_IDS:
        if counts[category_id] == 0 and totals[category_id] == 0:
            continue
        categories.append(
            {
                "id": category_id,
                "label": label(category_id),
                "bucket": "expense",
                "total": _money(totals[category_id]),
                "count": counts[category_id],
            }
        )
    categories.sort(key=lambda entry: abs(entry["total"]), reverse=True)
    deductible = sum(totals.values(), Decimal("0"))
    return {
        "deductible_total": _money(deductible),
        "income_total": _money(income),
        "excluded_total": _money(excluded),
        "personal_total": _money(personal),
        "unassigned_refunds": _money(unassigned_refunds),
        "needs_review_count": review_count,
        "needs_review_total": _money(review_total),
        "categories": categories,
    }


def _assign(item: dict, category: str) -> None:
    amount = Decimal(str(item["amount"]))
    if category in EXPENSE_IDS and amount < 0:
        item["category"] = "refund"
        item["offsets_category"] = category
        item["reason"] = f"You filed this money-back row against {label(category)}."
    else:
        item["category"] = category
        item["offsets_category"] = None
        item["reason"] = "You set this category."
    item["category_label"] = label(item["category"])
    item["offsets_label"] = label(item["offsets_category"])
    item["bucket"] = bucket(item["category"])
    item["needs_review"] = False
    item["duplicate"] = False
    item["confidence"] = 1
    item["source"] = "user"
    item["suggestion"] = None
    item["suggestion_label"] = None


def _present_row(
    row_number: int,
    date: str | None,
    description: str,
    amount: Decimal,
    pending: bool,
    decision: Decision,
) -> dict:
    return {
        "id": str(row_number),
        "date": date,
        "description": description,
        "amount": _money(amount),
        "category": decision.category,
        "category_label": label(decision.category),
        "bucket": bucket(decision.category),
        "confidence": round(decision.confidence, 2),
        "needs_review": decision.needs_review,
        "reason": decision.reason,
        "suggestion": decision.suggestion,
        "suggestion_label": label(decision.suggestion),
        "offsets_category": decision.offsets_category,
        "offsets_label": label(decision.offsets_category),
        "pending": pending,
        "duplicate": False,
        "source": decision.source,
        "fingerprint": decision.fingerprint,
        "remember_safe": decision.remember_safe,
    }


def _force_review(item: dict, reason: str, suggestion: str | None) -> dict:
    if suggestion == "needs_review":
        suggestion = None
    if item["category"] not in {"needs_review", None} and suggestion is None:
        suggestion = item["category"] if item["category"] in BUCKETS and item["category"] != "needs_review" else item["suggestion"]
    item["needs_review"] = True
    item["category"] = "needs_review"
    item["category_label"] = label("needs_review")
    item["bucket"] = "review"
    item["confidence"] = 0.5 if suggestion else 0
    item["suggestion"] = suggestion
    item["suggestion_label"] = label(suggestion)
    item["offsets_category"] = None
    item["offsets_label"] = None
    item["reason"] = reason
    item["source"] = "review"
    return item


def _money(value: Decimal) -> float:
    return float(value.quantize(MONEY))


def read_upload(filename: str, payload: bytes) -> str:
    if not filename.lower().endswith(".csv"):
        raise ParseError("Upload a CSV. In your bank's export menu, choose CSV.")
    if len(payload) > 5 * 1024 * 1024:
        raise ParseError("That file is larger than 5 MB.")
    if not payload.strip():
        raise ParseError("That file is empty.")
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return payload.decode("latin-1")
