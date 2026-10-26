import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, model_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .engine import CATEGORIES, PURPOSES, TYPES, classify, normalize
from .parsers import MAX_BYTES, ImportProblem, extract, parse_rows
from .reports import summarize
from .store import database, rules, transactions

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="SortedHisab", version="0.1.0")


class LocalRequestGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin not in {
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            }:
                return Response("Origin not allowed", status_code=403)
            length = request.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > MAX_BYTES + 131072):
                return Response("Request exceeds the upload limit", status_code=413)
        return await call_next(request)


app.add_middleware(LocalRequestGuard)


class ImportOptions(BaseModel):
    account: str = Field(min_length=1, max_length=80)
    account_type: Literal["bank", "credit_card", "wallet", "international"] = "credit_card"
    currency: Literal["PKR", "USD", "EUR", "GBP", "AED"] = "PKR"
    date_order: Literal["day_first", "month_first"] = "day_first"
    amount_direction: Literal["out_positive", "in_positive"] = "out_positive"
    mapping: dict[str, str]

    @model_validator(mode="after")
    def validate_account(self):
        self.account = self.account.strip()
        if not self.account:
            raise ValueError("Account name cannot be blank.")
        return self


class Review(BaseModel):
    kind: str
    category: str
    purpose: str
    business_percent: int = Field(ge=0, le=100, strict=True)
    note: str = Field(default="", max_length=1000)
    remember: bool = False

    @model_validator(mode="after")
    def validate_decision(self):
        if self.kind not in TYPES or self.category not in CATEGORIES or self.purpose not in PURPOSES:
            raise ValueError("Choose a valid type, category, and purpose.")
        if self.kind == "unresolved" or self.purpose == "unknown" or self.category == "Uncategorized":
            raise ValueError("Resolve the type, category, and purpose before confirming.")
        if self.purpose == "business" and self.business_percent != 100:
            raise ValueError("Business purpose requires 100% business share.")
        if self.purpose == "mixed" and not 0 < self.business_percent < 100:
            raise ValueError("Mixed purpose requires a business share between 1% and 99%.")
        if self.purpose in {"personal", "excluded"} and self.business_percent != 0:
            raise ValueError("Personal/excluded transactions require 0% business share.")
        if self.kind in {"transfer", "card_payment", "cash"} and self.business_percent:
            raise ValueError("Movements cannot be allocated as business expenses.")
        if self.kind in {"expense", "refund", "income"} and self.purpose == "excluded":
            raise ValueError("Expenses, refunds, and income need a business/personal purpose.")
        movement_categories = {"Own-account transfer", "Transfer", "Card payment", "Cash withdrawal"}
        if self.kind in {"expense", "refund"} and self.category in movement_categories | {"Freelance income"}:
            raise ValueError("Choose an expense category for a purchase or refund.")
        if self.kind == "transfer" and (
            self.category not in {"Transfer", "Own-account transfer"} or self.purpose != "excluded"
        ):
            raise ValueError(
                "Transfers need a transfer category and excluded purpose. Family support is a personal expense."
            )
        if self.kind == "card_payment" and (self.category != "Card payment" or self.purpose != "excluded"):
            raise ValueError("Card payments need the Card payment category and excluded purpose.")
        if self.kind == "cash" and (self.category != "Cash withdrawal" or self.purpose != "excluded"):
            raise ValueError("Cash movements need the Cash withdrawal category and excluded purpose.")
        if self.kind == "income" and self.category != "Freelance income":
            raise ValueError("Choose Freelance income for an income receipt.")
        return self


async def upload_bytes(file: UploadFile) -> bytes:
    try:
        content = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Maximum statement size is 5 MB.")
    return content


def parsed(content, filename, options):
    try:
        extracted = extract(filename, content)
        rows, errors = parse_rows(extracted, options.model_dump())
        return extracted, rows, errors
    except ImportProblem as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/health")
def health():
    return {"status": "ok", "classifier": "deterministic", "version": "rules-1.0"}


@app.get("/api/workspace")
def workspace():
    with database() as db:
        rows = transactions(db)
        statements = [
            json.loads(row["data"]) for row in db.execute("SELECT data FROM statements ORDER BY rowid DESC")
        ]
        return {
            "transactions": rows,
            "statements": statements,
            "rules": rules(db),
            "summary": summarize(rows),
            "categories": CATEGORIES,
            "types": TYPES,
            "purposes": PURPOSES,
        }


@app.post("/api/imports/inspect")
async def inspect(file: UploadFile = File(...)):
    content = await upload_bytes(file)
    try:
        result = extract(file.filename or "", content)
    except ImportProblem as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**result, "rows": result["rows"][:6]}


def options_from_json(value):
    try:
        return ImportOptions.model_validate_json(value)
    except ValueError as exc:
        raise HTTPException(422, "Invalid import settings. Check account and column mapping.") from exc


@app.post("/api/imports/preview")
async def preview(file: UploadFile = File(...), options: str = Form(...)):
    settings = options_from_json(options)
    extracted, rows, errors = parsed(await upload_bytes(file), file.filename or "", settings)
    return {
        "rows": rows[:10],
        "valid_count": len(rows),
        "errors": errors,
        "source_count": extracted["row_count"],
        "summary": {
            currency: sum(row["amount_minor"] for row in rows if row["currency"] == currency)
            for currency in sorted({row["currency"] for row in rows})
        },
    }


def commit_import(content, filename, settings):
    extracted, rows, errors = parsed(content, filename, settings)
    if errors:
        raise HTTPException(
            422, {"message": "Import blocked: correct every invalid row first.", "errors": errors}
        )
    digest = hashlib.sha256(content).hexdigest()
    statement_id = uuid4().hex
    statement = {
        "id": statement_id,
        "account": settings.account.strip(),
        "account_type": settings.account_type,
        "filename": Path(filename).name,
        "row_count": len(rows),
        "digest": digest,
        "period_start": min(row["date"] for row in rows),
        "period_end": max(row["date"] for row in rows),
        "mapping": settings.mapping,
        "date_order": settings.date_order,
        "amount_direction": settings.amount_direction,
        "currency": settings.currency,
    }
    with database() as db:
        if db.execute(
            "SELECT id FROM statements WHERE account=? AND digest=?", (statement["account"], digest)
        ).fetchone():
            raise HTTPException(409, "This exact file has already been imported for this account.")
        existing = transactions(db)
        account_rules = rules(db, statement["account"])
        db.execute(
            "INSERT INTO statements(id,account,filename,digest,data) VALUES(?,?,?,?,?)",
            (statement_id, statement["account"], statement["filename"], digest, json.dumps(statement)),
        )
        for row in rows:
            decision = classify(row["description"], row["amount_minor"], account_rules)
            duplicate = any(
                old["account"] == statement["account"]
                and all(old[key] == row[key] for key in ("date", "description", "amount_minor", "currency"))
                for old in existing
            )
            row |= decision | {
                "id": uuid4().hex,
                "statement_id": statement_id,
                "account": statement["account"],
                "review_status": "categorized",
                "note": "",
                "possible_duplicate": duplicate,
            }
            if duplicate:
                row |= {
                    "needs_review": True,
                    "reason": row["reason"] + " Possible overlap with an earlier import; verify both rows.",
                }
            db.execute("INSERT INTO transactions VALUES(?,?,?)", (row["id"], statement_id, json.dumps(row)))
    return statement


@app.post("/api/imports", status_code=201)
async def import_statement(file: UploadFile = File(...), options: str = Form(...)):
    settings = options_from_json(options)
    return commit_import(await upload_bytes(file), file.filename or "", settings)


@app.post("/api/demo", status_code=201)
def demo():
    filename = "developer-credit-card.csv"
    settings = ImportOptions(
        account="Demo credit card",
        mapping={
            "date": "Date",
            "description": "Description",
            "debit": "Debit",
            "credit": "Credit",
            "currency": "Currency",
            "original_amount": "Original Amount",
            "original_currency": "Original Currency",
        },
    )
    return commit_import((ROOT / "sample_data" / filename).read_bytes(), filename, settings)


@app.patch("/api/transactions/{transaction_id}")
def review(transaction_id: str, update: Review):
    with database() as db:
        found = db.execute("SELECT data FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not found:
            raise HTTPException(404, "Transaction not found.")
        previous = json.loads(found["data"])
        if update.kind == "refund" and previous["amount_minor"] >= 0:
            raise HTTPException(422, "Refunds must be incoming amounts. Check your import direction.")
        if update.kind == "expense" and previous["amount_minor"] <= 0:
            raise HTTPException(422, "Expenses must be outgoing amounts.")
        if update.kind == "income" and previous["amount_minor"] >= 0:
            raise HTTPException(422, "Income must be incoming funds.")
        row = (
            previous
            | update.model_dump(exclude={"remember"})
            | {
                "needs_review": False,
                "review_status": "confirmed",
                "reason": "Confirmed by you. " + update.note,
                "rule_id": "user.review",
                "category_confidence": "confirmed",
            }
        )
        db.execute("UPDATE transactions SET data=? WHERE id=?", (json.dumps(row), transaction_id))
        db.execute(
            "INSERT INTO reviews(transaction_id,previous_data,new_data) VALUES(?,?,?)",
            (transaction_id, found["data"], json.dumps(row)),
        )
        if update.remember:
            if update.kind not in {"expense", "transfer"}:
                raise HTTPException(
                    422, "Remember rules only for purchases and transfers; credits require individual review."
                )
            if previous["rule_id"].startswith("type.") and previous["kind"] not in {"expense", "transfer"}:
                raise HTTPException(
                    422, "This structural transaction type cannot be saved as a merchant rule."
                )
            match_text = normalize(row["description"])
            rule = {
                "id": uuid4().hex,
                "account": row["account"],
                "match_text": match_text,
                **update.model_dump(exclude={"remember", "note"}),
            }
            db.execute(
                "INSERT INTO rules VALUES(?,?,?,?) ON CONFLICT(account,match_text) DO UPDATE SET data=excluded.data",
                (rule["id"], row["account"], match_text, json.dumps(rule)),
            )
    return row


@app.delete("/api/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str):
    with database() as db:
        for row in db.execute("SELECT id,data FROM rules").fetchall():
            if json.loads(row["data"])["id"] == rule_id:
                db.execute("DELETE FROM rules WHERE id=?", (row["id"],))
                return Response(status_code=204)
    raise HTTPException(404, "Rule not found.")


@app.delete("/api/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: str):
    with database() as db:
        cursor = db.execute("DELETE FROM statements WHERE id=?", (statement_id,))
        if not cursor.rowcount:
            raise HTTPException(404, "Statement not found.")
    return Response(status_code=204)


def safe_cell(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


@app.get("/api/export/{report}")
def export(report: Literal["transactions", "summary"]):
    with database() as db:
        rows = transactions(db)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if report == "transactions":
        fields = [
            "date",
            "description",
            "account",
            "currency",
            "amount",
            "original_amount",
            "original_currency",
            "statement_id",
            "kind",
            "category",
            "purpose",
            "business_percent",
            "needs_review",
            "reason",
            "rule_id",
            "rule_version",
            "source_row",
            "note",
        ]
        writer.writerow(fields)
        for row in rows:
            values = row | {
                "amount": f"{Decimal(row['amount_minor']) / 100:.2f}",
                "original_amount": f"{Decimal(row['original_amount_minor']) / 100:.2f}"
                if row["original_amount_minor"] is not None
                else "",
                "original_currency": row["original_currency"] or "",
            }
            writer.writerow(
                [
                    values[field]
                    if field in {"amount", "original_amount", "business_percent", "source_row"}
                    else safe_cell(values[field])
                    for field in fields
                ]
            )
    else:
        writer.writerow(["currency", "category", "net_amount", "outstanding_review_count"])
        summary = summarize(rows)
        for currency, totals in summary["currencies"].items():
            for category, amount in sorted(totals["categories"].items()):
                writer.writerow(
                    [currency, safe_cell(category), f"{Decimal(amount) / 100:.2f}", summary["needs_review"]]
                )
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sortedhisab-{report}.csv"'},
    )


@app.get("/api/samples/{filename}")
def sample(filename: str):
    allowed = {
        path.name for path in (ROOT / "sample_data").glob("*") if path.suffix in {".csv", ".xlsx", ".pdf"}
    }
    if filename not in allowed:
        raise HTTPException(404, "Sample not found.")
    return FileResponse(ROOT / "sample_data" / filename, filename=filename)


# Serve built frontend for the single-origin local production command.
@app.get("/{path:path}")
def frontend(path: str):
    dist = ROOT / "frontend" / "dist"
    target = (dist / path).resolve()
    if target.is_relative_to(dist.resolve()) and target.is_file():
        return FileResponse(target)
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found.")
    if (dist / "index.html").exists():
        return FileResponse(dist / "index.html")
    raise HTTPException(404, "Frontend not built. Run npm run build in frontend, or use the Vite dev server.")
