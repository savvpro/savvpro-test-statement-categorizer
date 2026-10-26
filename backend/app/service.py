import hashlib
import json
import sqlite3
import uuid
from collections import Counter

from fastapi import HTTPException

from .database import connect
from .domain import KIND_CATEGORIES, ImportOptions, ReviewRequest
from .engine import classify, normalize
from .importer import parse_statement
from .summaries import summarize


def transaction_dict(row):
    result = dict(row)
    result["decision"] = json.loads(result.pop("decision_json"))
    result["reviewed"] = bool(result["reviewed"])
    result["needs_review"] = result["duplicate_status"] != "excluded" and (
        result["duplicate_status"] == "pending"
        or (not result["reviewed"] and result["decision"]["status"] == "needs_review")
    )
    return result


def get_statement(conn, statement_id):
    row = conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Statement not found.")
    result = dict(row)
    result["options"] = json.loads(result.pop("options_json"))
    return result


def get_transactions(conn, statement_id):
    return [
        transaction_dict(r)
        for r in conn.execute(
            "SELECT * FROM transactions WHERE statement_id = ? ORDER BY source_row", (statement_id,)
        )
    ]


def statement_summary(conn, statement_id):
    statement = get_statement(conn, statement_id)
    return {**summarize(get_transactions(conn, statement_id)), "currency": statement["currency"]}


def import_statement(content: bytes, filename: str, options: ImportOptions):
    parsed, blanks = parse_statement(content, options)
    options_json = json.dumps(options.model_dump(), sort_keys=True)
    fingerprint = hashlib.sha256(content + options_json.encode()).hexdigest()
    statement_id = str(uuid.uuid4())
    keys = [(r.date, r.amount_minor, normalize(r.description)) for r in parsed]
    duplicates = Counter(keys)
    records = []
    for row, key in zip(parsed, keys, strict=True):
        decision = classify(row.description, row.amount_minor)
        group = (
            hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
            if duplicates[key] > 1
            else None
        )
        records.append(
            (
                str(uuid.uuid4()),
                statement_id,
                row.source_row,
                row.date,
                row.description,
                normalize(row.description),
                row.amount_minor,
                json.dumps(decision.to_dict()),
                decision.kind,
                decision.category,
                group,
                "pending" if group else "none",
            )
        )
    with connect() as conn:
        # Serialize the hash check + insert; concurrent identical imports cannot partially commit.
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id FROM statements WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        if existing:
            return {"statement": get_statement(conn, existing["id"]), "already_imported": True}
        conn.execute(
            """INSERT INTO statements
            (id, fingerprint, filename, currency, options_json, row_count, blank_rows)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                statement_id,
                fingerprint,
                filename,
                options.currency,
                options_json,
                len(parsed),
                blanks,
            ),
        )
        conn.executemany(
            """INSERT INTO transactions
            (id, statement_id, source_row, date, description, normalized, amount_minor,
             decision_json, kind, category, duplicate_group, duplicate_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            records,
        )
        return {"statement": get_statement(conn, statement_id), "already_imported": False}


def review_transaction(transaction_id: str, request: ReviewRequest):
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Transaction not found.")
        before = transaction_dict(row)
        if request.version != before["version"]:
            raise HTTPException(409, "This transaction changed. Reload it before saving again.")
        kind, category = before["kind"], before["category"]
        reviewed, duplicate_status = before["reviewed"], before["duplicate_status"]
        if request.action == "save":
            if (
                request.kind in (None, "unknown")
                or request.category not in KIND_CATEGORIES[request.kind]
            ):
                raise HTTPException(422, "Choose a compatible transaction kind and category.")
            amount = before["amount_minor"]
            if (request.kind == "expense" and amount >= 0) or (
                request.kind in ("refund", "income") and amount <= 0
            ):
                raise HTTPException(422, "This kind conflicts with the transaction direction.")
            kind, category, reviewed = request.kind, request.category, True
        elif request.action == "reset":
            kind, category = before["decision"]["kind"], before["decision"]["category"]
            reviewed = False
        else:
            if not before["duplicate_group"] or request.duplicate_action is None:
                raise HTTPException(422, "This transaction has no duplicate warning to resolve.")
            duplicate_status = {"keep": "kept", "exclude": "excluded", "reset": "pending"}[
                request.duplicate_action
            ]
            if duplicate_status == "excluded":
                remaining = conn.execute(
                    """SELECT count(*) FROM transactions
                    WHERE statement_id = ? AND duplicate_group = ? AND id != ?
                    AND duplicate_status != 'excluded' """,
                    (before["statement_id"], before["duplicate_group"], transaction_id),
                ).fetchone()[0]
                if not remaining:
                    raise HTTPException(422, "Keep at least one transaction in a duplicate group.")
        conn.execute(
            """UPDATE transactions SET kind = ?, category = ?, reviewed = ?,
            duplicate_status = ?, version = version + 1 WHERE id = ?""",
            (kind, category, reviewed, duplicate_status, transaction_id),
        )
        after = transaction_dict(
            conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        )
        conn.execute(
            """INSERT INTO review_events
            (transaction_id, action, before_json, after_json) VALUES (?, ?, ?, ?)""",
            (transaction_id, request.action, json.dumps(before), json.dumps(after)),
        )
        return after


def delete_statement(statement_id):
    with connect() as conn:
        get_statement(conn, statement_id)
        conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,))


def storage_error_handler(_request, _error: sqlite3.OperationalError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Local storage is unavailable or busy. Try again; no partial change was saved."
            )
        },
    )
