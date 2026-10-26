from dataclasses import asdict
from decimal import Decimal
from typing import Any

import os
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .brain import categorize
from .db import (
    get_rules as get_user_rules,
    get_audit_events,
    get_statements,
    get_shared_rule_candidates,
    get_statement,
    get_workspaces,
    initialize,
    replace_user_rule,
    save_rule,
    save_statement,
    save_audit_event,
    save_shared_rule_candidate,
    update_transaction,
    authenticate,
    make_session,
    user_from_session,
    user_has_workspace,
)
from .models import CategorizationRule, Statement
from .parser import parse_csv

app = FastAPI(title="FreelanceBooks API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response

initialize()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class Credentials(BaseModel):
    username: str
    password: str


class Correction(BaseModel):
    category: str
    learn: bool = True


def current_user(authorization: str | None) -> dict[str, str | int]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in required.")
    user = user_from_session(authorization[7:])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return user


def workspace_from_header(workspace_id: str | None, user: dict[str, str | int]) -> str:
    if not workspace_id or not user_has_workspace(str(user["id"]), workspace_id):
        raise HTTPException(status_code=403, detail="You are not a member of this workspace.")
    if workspace_id not in {workspace["id"] for workspace in get_workspaces()}:
        raise HTTPException(status_code=403, detail="Unknown workspace.")
    return workspace_id


def serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(credentials: Credentials) -> dict[str, str]:
    user = authenticate(credentials.username.strip(), credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {"token": make_session(user), "username": str(user["username"])}


@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None)) -> dict[str, str | int]:
    return current_user(authorization)


@app.get("/api/workspaces")
def workspaces(authorization: str | None = Header(default=None)) -> list[dict[str, str]]:
    user = current_user(authorization)
    return get_workspaces()


@app.get("/api/statements")
def statement_history(
    workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None),
) -> list[dict[str, str | int]]:
    return get_statements(workspace_from_header(workspace_id, current_user(authorization)))


@app.post("/api/statements")
async def upload_statement(
    file: UploadFile = File(...),
    workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    user = current_user(authorization)
    workspace_id = workspace_from_header(workspace_id, user)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV statement.")
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("CSV file is too large; maximum size is 10 MB.")
        transactions = parse_csv(content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    rules = get_user_rules(workspace_id)
    for transaction in transactions:
        categorize(transaction, rules)
    from uuid import uuid4

    statement = Statement(str(uuid4()), file.filename, transactions)
    save_statement(statement, workspace_id)
    return serialize(statement)


@app.get("/api/statements/{statement_id}")
def read_statement(
    statement_id: str,
    workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    workspace_id = workspace_from_header(workspace_id, current_user(authorization))
    statement = get_statement(statement_id, workspace_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found.")
    return serialize(statement)


@app.patch("/api/statements/{statement_id}/transactions/{transaction_id}")
def correct_transaction(
    statement_id: str, transaction_id: str, correction: Correction
    , workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    workspace_id = workspace_from_header(workspace_id, current_user(authorization))
    statement = get_statement(statement_id, workspace_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found.")
    transaction = next((item for item in statement.transactions if item.id == transaction_id), None)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    valid_categories = {
        "Client Income", "Software", "Advertising & Marketing", "Internet & Phone",
        "Equipment", "Payment Processing Fees", "Travel & Transport", "Meals",
        "Travel", "Food & Dining", "Transport", "Shopping", "Utilities", "Health",
        "Entertainment", "Education", "Personal Care", "Electronics", "Other",
        "Office Expenses", "Taxes", "Transfer", "Refund", "Personal Expense",
        "Needs Review",
    }
    if correction.category not in valid_categories:
        raise HTTPException(status_code=400, detail="Invalid category.")
    old_category = transaction.category
    transaction.category = correction.category  # type: ignore[assignment]
    transaction.confidence = 100
    transaction.explanation = "Set by you and saved as a personal correction."
    transaction.needs_review = False
    transaction.rule_scope = "user" if correction.learn else None
    if correction.learn:
        rule = CategorizationRule(
            pattern=transaction.description,
            category=correction.category,  # type: ignore[arg-type]
            scope="user",
            source="user_correction",
            user_id=workspace_id,
            exact=True,
        )
        replace_user_rule(rule)
        candidate_pattern = transaction.description.split(" - ", 1)[0].strip()
        if candidate_pattern and not any(character.isdigit() for character in candidate_pattern):
            save_shared_rule_candidate(workspace_id, candidate_pattern, correction.category)
        transaction.rule_id = rule.id
    update_transaction(transaction)
    if old_category != correction.category:
        save_audit_event(
            workspace_id, statement_id, transaction_id, old_category, correction.category
        )
    return serialize(transaction)


@app.get("/api/rules")
def get_rules(
    workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    return serialize(get_user_rules(workspace_from_header(workspace_id, current_user(authorization))))


@app.get("/api/audit")
def audit_history(
    workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    authorization: str | None = Header(default=None),
) -> list[dict[str, str | int]]:
    return get_audit_events(workspace_from_header(workspace_id, current_user(authorization)))


@app.get("/api/admin/shared-rule-candidates")
def shared_rule_candidates(authorization: str | None = Header(default=None)) -> list[dict[str, str | int]]:
    if not current_user(authorization)["is_admin"]:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return get_shared_rule_candidates()
