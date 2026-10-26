"""What the API does: import a statement, fix a row, manage rules, add up totals."""

import csv
import hashlib
import io
import json
import logging
from dataclasses import asdict
from datetime import date

from . import storage
from .categorizer.engine import AUTO, CORRECTED, REVIEW, Engine, PastTxn, Txn
from .categorizer.rules import MATCH_TYPES, Rule, RuleBook, contains_words, load_rulebook, user_rule
from .parsing import NeedsUserChoice, UnsupportedFile, clean_rows, read_statement
from .parsing.values import AUTO as AUTO_CHOICE
from .parsing.values import DAY_FIRST, MONTH_FIRST, from_minor, normalize_description, suggest_rule_pattern, to_minor

log = logging.getLogger(__name__)


class AppError(Exception):
    status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(AppError):
    status = 404


class Conflict(AppError):
    status = 409


class BadInput(AppError):
    status = 422


# --- helpers -----------------------------------------------------------------

def rulebook(conn) -> RuleBook:
    rules = [user_rule(r) for r in storage.list_user_rules(conn, enabled_only=True)]
    return load_rulebook().with_user_rules(rules)


def _history(conn) -> list[PastTxn]:
    book = load_rulebook()
    return [
        PastTxn(r["id"], date.fromisoformat(r["txn_date"]), from_minor(r["amount_minor"]), r["currency"],
                r["rule_id"], r["category"], book.is_refund(normalize_description(r["description"])))
        for r in storage.refund_history(conn)
    ]


def _txn(row) -> Txn:
    amount = from_minor(row["amount_minor"])
    return Txn(date.fromisoformat(row["txn_date"]), row["description"], amount, row["currency"])


def _decision_values(decision) -> dict:
    return {
        "txn_type": decision.txn_type,
        "category": decision.category,
        "suggested_category": decision.suggested_category,
        "status": decision.status,
        "rule_id": decision.rule_id,
        "reason": decision.reason,
        "linked_txn_id": decision.linked_txn_id,
        "app_category": decision.category or decision.suggested_category,
        "app_reason": decision.reason,
    }


def txn_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "statement_id": row["statement_id"],
        "source_file": row["source_file"],
        "source_row": row["source_row"],
        "date": row["txn_date"],
        "description": row["description"],
        "amount": str(from_minor(row["amount_minor"])),
        "currency": row["currency"],
        "balance": str(from_minor(row["balance_minor"])) if row["balance_minor"] is not None else None,
        "type": row["txn_type"],
        "category": row["category"],
        "suggested_category": row["suggested_category"],
        "status": row["status"],
        "rule_id": row["rule_id"],
        "reason": row["reason"],
        "flags": json.loads(row["flags_json"]),
        "linked_txn_id": row["linked_txn_id"],
        "app_category": row["app_category"],
        "suggested_pattern": suggest_rule_pattern(row["description"]),
    }


def statement_to_dict(row) -> dict:
    keys = row.keys()
    return {
        "id": row["id"],
        "filename": row["filename"],
        "source_kind": row["source_kind"],
        "account_type": row["account_type"],
        "currency": row["currency"],
        "imported_at": row["imported_at"],
        "row_count": row["row_count"] if "row_count" in keys else None,
        "review_count": (row["review_count"] or 0) if "review_count" in keys else None,
        "report": json.loads(row["report_json"]),
    }


# --- import ------------------------------------------------------------------

def import_statement(conn, *, filename: str, data: bytes, account_type: str, currency: str, date_format: str) -> dict:
    if account_type not in ("business", "mixed"):
        raise BadInput("Account type must be 'business' or 'mixed'.")
    if currency not in (AUTO_CHOICE, "PKR", "USD"):
        raise BadInput("Currency must be auto, PKR or USD.")
    if date_format not in (AUTO_CHOICE, DAY_FIRST, MONTH_FIRST):
        raise BadInput("Date format must be auto, day_first or month_first.")
    if not data:
        raise BadInput("The file is empty.")

    file_hash = hashlib.sha256(data).hexdigest()
    existing = storage.find_statement_by_hash(conn, file_hash)
    if existing:
        raise Conflict(
            f"This file was already imported as '{existing['filename']}' on {existing['imported_at'][:10]}. "
            "Delete that import first if you want to load it again."
        )

    try:
        parsed = read_statement(filename, data)
        cleaned = clean_rows(parsed, currency, date_format)
    except (UnsupportedFile, NeedsUserChoice) as problem:
        raise BadInput(str(problem)) from problem
    if not cleaned.rows and not cleaned.errors:
        raise BadInput("No transactions were found in this file.")

    engine = Engine(rulebook(conn), account_type, _history(conn))
    with conn:
        statement_id = storage.insert_statement(
            conn, filename=filename, file_hash=file_hash, source_kind=parsed.source_kind,
            account_type=account_type, currency=cleaned.currency, report={},
        )
        counts = {AUTO: 0, REVIEW: 0}
        for row in cleaned.rows:
            flags = list(row.flags)
            earlier = storage.find_by_fingerprint(conn, row.fingerprint, statement_id)
            if earlier:
                flags.append(
                    f"Same date, amount and description as {earlier['source_row']} in {earlier['filename']}, "
                    "imported earlier. It may be a duplicate. Nothing was deleted."
                )
            decision = engine.decide(Txn(row.txn_date, row.description, row.amount, row.currency), flags)
            txn_id = storage.insert_transaction(conn, {
                "statement_id": statement_id,
                "source_row": row.source_row,
                "txn_date": row.txn_date.isoformat(),
                "description": row.description,
                "amount_minor": to_minor(row.amount),
                "currency": row.currency,
                "balance_minor": to_minor(row.balance) if row.balance is not None else None,
                "flags_json": json.dumps(flags),
                "fingerprint": row.fingerprint,
                **_decision_values(decision),
            })
            counts[decision.status] += 1
            if row.amount < 0:
                engine.history.append(PastTxn(
                    txn_id, row.txn_date, row.amount, row.currency, decision.rule_id, decision.category,
                    engine.book.is_refund(normalize_description(row.description)),
                ))

        report = {
            "rows_imported": len(cleaned.rows),
            "auto": counts[AUTO],
            "needs_review": counts[REVIEW],
            "skipped": [asdict(i) for i in cleaned.skipped],
            "errors": [asdict(i) for i in cleaned.errors],
            "warnings": cleaned.warnings,
        }
        storage.update_statement_report(conn, statement_id, report)

    log.info("imported statement id=%s kind=%s rows=%d review=%d errors=%d",
             statement_id, parsed.source_kind, len(cleaned.rows), counts[REVIEW], len(cleaned.errors))
    statement = next(s for s in storage.list_statements(conn) if s["id"] == statement_id)
    return statement_to_dict(statement)


# --- corrections -------------------------------------------------------------

def correct_transaction(conn, txn_id: int, category: str | None) -> dict:
    row = storage.get_transaction(conn, txn_id)
    if row is None:
        raise NotFound("Transaction not found.")
    book = rulebook(conn)

    with conn:
        if category is None:
            # Undo the user's change and let the rules decide again.
            engine = Engine(book, row["account_type"], [p for p in _history(conn) if p.id != txn_id])
            decision = engine.decide(_txn(row), json.loads(row["flags_json"]))
            storage.update_transaction(conn, txn_id, _decision_values(decision))
        else:
            kind = book.kind(category)
            if kind is None:
                raise BadInput(f"'{category}' is not a category.")
            money_in = row["amount_minor"] > 0
            if kind == "income" and not money_in:
                raise BadInput("Business Income is for money coming in. This row is money going out.")
            if money_in and kind in ("expense", "tax"):
                txn_type = "refund"  # money back that reduces a spending category
            else:
                txn_type = {"income": "income", "expense": "expense", "tax": "expense",
                            "transfer": "transfer", "personal": "personal"}[kind]
            storage.update_transaction(conn, txn_id, {
                "category": category,
                "suggested_category": None,
                "status": CORRECTED,
                "txn_type": txn_type,
                "reason": f"You set this to {category}.",
            })

    updated = txn_to_dict(storage.get_transaction(conn, txn_id))
    pattern = updated["suggested_pattern"]
    updated["rule_offer"] = (
        {"pattern": pattern, "match_type": "contains", "category": category}
        if category and pattern and len(pattern) >= 3 else None
    )
    return updated


def rerun_review_rows(conn) -> int:
    """Re-check rows that need review, e.g. after the user adds a rule.

    Rows the app already decided and rows the user corrected are never touched.
    Returns how many rows became decided.
    """
    book = rulebook(conn)
    decided = 0
    rows = storage.list_transactions(conn, status=REVIEW)
    history = _history(conn)
    for row in rows:
        engine = Engine(book, row["account_type"], [p for p in history if p.id != row["id"]])
        decision = engine.decide(_txn(row), json.loads(row["flags_json"]))
        if decision.status == AUTO:
            decided += 1
        storage.update_transaction(conn, row["id"], _decision_values(decision))
    return decided


# --- rules -------------------------------------------------------------------

def _rule_dict(stage: str, rule: Rule) -> dict:
    return {
        "id": rule.id, "stage": stage, "pattern": rule.pattern, "match_type": rule.match,
        "category": rule.category, "review": rule.review, "suggest": rule.suggest,
        "business_use": rule.business_use, "source": rule.source,
    }


def _user_rule_dict(row) -> dict:
    return {**dict(row), "enabled": bool(row["enabled"]), "rule_id": f"USER-{row['id']}"}


def list_rules(conn) -> dict:
    user = [_user_rule_dict(r) for r in storage.list_user_rules(conn)]
    built_in = [_rule_dict(stage, rule) for stage, rule in load_rulebook().all_rules()]
    return {"user": user, "built_in": built_in}


def _check_new_rule(conn, pattern: str, match_type: str, category: str) -> tuple[str, Rule]:
    normalized = normalize_description(pattern)
    if len(normalized) < 3:
        raise BadInput("The pattern needs at least 3 letters or digits, so it doesn't match everything.")
    if match_type not in MATCH_TYPES:
        raise BadInput("Match type must be contains, starts_with or exact.")
    if category not in load_rulebook().categories:
        raise BadInput(f"'{category}' is not a category.")
    for existing in storage.list_user_rules(conn):
        if existing["pattern"] == normalized and existing["match_type"] == match_type:
            raise Conflict(f"You already have a rule for '{normalized}' ({existing['category']}).")
    return normalized, Rule(id="USER-NEW", pattern=normalized, match=match_type, category=category, source="user")


def preview_rule(conn, pattern: str, match_type: str, category: str) -> dict:
    normalized, candidate = _check_new_rule(conn, pattern, match_type, category)

    overlaps = []
    current = rulebook(conn)
    for stage, rule in current.all_rules():
        overlap = contains_words(rule.pattern, normalized) or contains_words(normalized, rule.pattern)
        if overlap:
            if rule.source == "user":
                if rule.category == category:
                    note = "Same category, so they won't clash."
                elif rule.pattern == normalized:
                    note = "Both rules match the same rows with different categories. Those rows will go to review."
                else:
                    note = "The longer pattern is more specific and wins where both match."
            else:
                note = "Your rules are checked first, so yours wins where both match."
            overlaps.append({**_rule_dict(stage, rule), "note": note})

    with_new = current.with_user_rules([candidate])
    affected, already_decided = [], 0
    history = _history(conn)
    for row in storage.list_transactions(conn):
        if not candidate.matches(normalize_description(row["description"])):
            continue
        if row["status"] != REVIEW:
            already_decided += 1
            continue
        engine = Engine(with_new, row["account_type"], [p for p in history if p.id != row["id"]])
        after = engine.decide(_txn(row), json.loads(row["flags_json"]))
        affected.append({
            **txn_to_dict(row),
            "after": {
                "status": after.status,
                "category": after.category or after.suggested_category,
                "reason": after.reason,
            },
        })

    return {
        "pattern": normalized, "match_type": match_type, "category": category,
        "overlaps": overlaps, "affected": affected, "already_decided": already_decided,
    }


def create_rule(conn, *, pattern: str, match_type: str, category: str, from_txn_id: int | None, apply: bool) -> dict:
    normalized, _ = _check_new_rule(conn, pattern, match_type, category)
    with conn:
        rule_id = storage.insert_user_rule(
            conn, pattern=normalized, match_type=match_type, category=category, created_from_txn_id=from_txn_id
        )
        decided = rerun_review_rows(conn) if apply else 0
    return {"rule": _user_rule_dict(storage.get_user_rule(conn, rule_id)), "rows_decided": decided}


def set_rule_enabled(conn, rule_id: int, enabled: bool) -> dict:
    with conn:
        if not storage.set_user_rule_enabled(conn, rule_id, enabled):
            raise NotFound("Rule not found.")
    return _user_rule_dict(storage.get_user_rule(conn, rule_id))


def delete_rule(conn, rule_id: int) -> None:
    with conn:
        if not storage.delete_user_rule(conn, rule_id):
            raise NotFound("Rule not found.")


# --- totals and export ---------------------------------------------------------

def summary(conn, statement_id: int | None = None) -> dict:
    book = load_rulebook()
    per_currency: dict[str, dict] = {}
    for row in storage.list_transactions(conn, statement_id):
        cur = per_currency.setdefault(row["currency"], {
            "currency": row["currency"], "income": 0, "spending": 0, "tax_deducted": 0,
            "transfers_in": 0, "transfers_out": 0, "personal_in": 0, "personal_out": 0,
            "review_count": 0, "review_in": 0, "review_out": 0, "categories": {},
        })
        amount = row["amount_minor"]
        if row["status"] == REVIEW:
            cur["review_count"] += 1
            cur["review_in" if amount > 0 else "review_out"] += abs(amount)
            continue
        kind = book.kind(row["category"])
        bucket = cur["categories"].setdefault(
            row["category"], {"category": row["category"], "kind": kind, "total": 0, "count": 0}
        )
        bucket["total"] += amount
        bucket["count"] += 1
        if kind == "income":
            cur["income"] += amount
        elif kind == "expense":
            cur["spending"] -= amount  # refunds are positive, so they reduce spending
        elif kind == "tax":
            cur["tax_deducted"] -= amount
        elif kind == "transfer":
            cur["transfers_in" if amount > 0 else "transfers_out"] += abs(amount)
        elif kind == "personal":
            cur["personal_in" if amount > 0 else "personal_out"] += abs(amount)

    money = lambda minor: str(from_minor(minor))  # noqa: E731
    result = []
    for currency in sorted(per_currency):
        cur = per_currency[currency]
        categories = sorted(cur.pop("categories").values(), key=lambda c: -abs(c["total"]))
        result.append({
            **{k: (money(v) if k not in ("currency", "review_count") else v) for k, v in cur.items()},
            "net": money(cur["income"] - cur["spending"]),
            "categories": [{**c, "total": money(c["total"])} for c in categories],
        })

    statements = storage.list_statements(conn)
    if statement_id is not None:
        statements = [s for s in statements if s["id"] == statement_id]
    unreadable = sum(len(json.loads(s["report_json"]).get("errors", [])) for s in statements)
    return {"currencies": result, "unreadable_rows": unreadable}


EXPORT_COLUMNS = (
    "date", "description", "amount", "currency", "type", "category", "status", "suggested_category",
    "reason", "rule_id", "source_file", "source_row",
)


def _safe_cell(value) -> str:
    """Stop spreadsheet apps from running text that starts like a formula."""
    text = "" if value is None else str(value)
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def export_csv(conn, statement_id: int | None = None) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(EXPORT_COLUMNS)
    for row in storage.list_transactions(conn, statement_id):
        t = txn_to_dict(row)
        writer.writerow([
            t["date"], _safe_cell(t["description"]), t["amount"], t["currency"], t["type"],
            _safe_cell(t["category"]), t["status"], _safe_cell(t["suggested_category"]), _safe_cell(t["reason"]),
            _safe_cell(t["rule_id"]), _safe_cell(t["source_file"]), _safe_cell(t["source_row"]),
        ])
    return out.getvalue()
