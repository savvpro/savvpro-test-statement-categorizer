import sqlite3
import os
import secrets
import hashlib
import hmac
import base64
import json
import time
from pathlib import Path
from .models import CategorizationRule, Statement, Transaction

DB_PATH = Path(os.getenv("FREELANCEBOOKS_DB_PATH", Path(__file__).resolve().parents[2] / "freelancebooks.sqlite3"))
SESSION_SECRET = os.getenv("FREELANCEBOOKS_SESSION_SECRET", "local-development-secret-change-me")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS workspace_members (
                user_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                PRIMARY KEY (user_id, workspace_id)
            );
            CREATE TABLE IF NOT EXISTS statements (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL DEFAULT 'freelancer-demo' REFERENCES workspaces(id),
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
                transaction_date TEXT,
                description TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                direction TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                rule_id TEXT,
                rule_scope TEXT,
                needs_review INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                scope TEXT NOT NULL,
                source TEXT NOT NULL,
                exact INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                statement_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                old_category TEXT NOT NULL,
                new_category TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS shared_rule_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO workspaces (id, name) VALUES (?, ?)",
            ("freelancer-demo", "Freelancer Demo"),
        )
        connection.execute(
            "INSERT OR IGNORE INTO workspaces (id, name) VALUES (?, ?)",
            ("agency-demo", "Small Agency Demo"),
        )
        seed_user(connection, "demo", "demo-password-change-me", 0)
        seed_user(connection, "admin", "admin-password-change-me", 1)
        demo_id = connection.execute("SELECT id FROM users WHERE username='demo'").fetchone()["id"]
        admin_id = connection.execute("SELECT id FROM users WHERE username='admin'").fetchone()["id"]
        for user_id in (demo_id, admin_id):
            for workspace_id in ("freelancer-demo", "agency-demo"):
                connection.execute(
                    "INSERT OR IGNORE INTO workspace_members (user_id, workspace_id) VALUES (?, ?)",
                    (user_id, workspace_id),
                )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(statements)").fetchall()
        }
        if "workspace_id" not in columns:
            connection.execute(
                "ALTER TABLE statements ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'freelancer-demo'"
            )


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    actual = password_hash(password, base64.b64decode(salt)).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def seed_user(connection: sqlite3.Connection, username: str, password: str, is_admin: int) -> None:
    if not connection.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        connection.execute(
            "INSERT INTO users (id, username, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (secrets.token_hex(16), username, password_hash(password), is_admin),
        )


def authenticate(username: str, password: str) -> dict[str, str | int] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "username": row["username"], "is_admin": row["is_admin"]}


def make_session(user: dict[str, str | int]) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"user_id": user["id"], "exp": int(time.time()) + 86400}).encode()
    ).decode().rstrip("=")
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def user_from_session(token: str) -> dict[str, str | int] | None:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            return None
        with connect() as connection:
            row = connection.execute("SELECT id, username, is_admin FROM users WHERE id=?", (data["user_id"],)).fetchone()
        return dict(row) if row else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def user_has_workspace(user_id: str, workspace_id: str) -> bool:
    with connect() as connection:
        return bool(connection.execute(
            "SELECT 1 FROM workspace_members WHERE user_id=? AND workspace_id=?",
            (user_id, workspace_id),
        ).fetchone())


def save_statement(statement: Statement, workspace_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO statements (id, workspace_id, filename) VALUES (?, ?, ?)",
            (statement.id, workspace_id, statement.filename),
        )
        connection.executemany(
            """
            INSERT INTO transactions (
                id, statement_id, transaction_date, description, amount, currency,
                direction, category, confidence, explanation, rule_id, rule_scope, needs_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.id,
                    statement.id,
                    item.date.isoformat() if item.date else None,
                    item.description,
                    str(item.amount),
                    item.currency,
                    item.direction,
                    item.category,
                    item.confidence,
                    item.explanation,
                    item.rule_id,
                    item.rule_scope,
                    int(item.needs_review),
                )
                for item in statement.transactions
            ],
        )


def _transaction(row: sqlite3.Row) -> Transaction:
    from datetime import date
    from decimal import Decimal

    return Transaction(
        id=row["id"],
        date=date.fromisoformat(row["transaction_date"]) if row["transaction_date"] else None,
        description=row["description"],
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        direction=row["direction"],
        category=row["category"],
        confidence=row["confidence"],
        explanation=row["explanation"],
        rule_id=row["rule_id"],
        rule_scope=row["rule_scope"],
        needs_review=bool(row["needs_review"]),
    )


def get_statement(statement_id: str, workspace_id: str) -> Statement | None:
    with connect() as connection:
        statement_row = connection.execute(
            "SELECT id, filename FROM statements WHERE id = ? AND workspace_id = ?",
            (statement_id, workspace_id),
        ).fetchone()
        if not statement_row:
            return None
        rows = connection.execute(
            "SELECT * FROM transactions WHERE statement_id = ? ORDER BY rowid",
            (statement_id,),
        ).fetchall()
    return Statement(
        statement_row["id"],
        statement_row["filename"],
        [_transaction(row) for row in rows],
    )


def get_statements(workspace_id: str) -> list[dict[str, str | int]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT s.id, s.filename, s.created_at, COUNT(t.id) AS transaction_count,
                   SUM(t.needs_review) AS review_count
            FROM statements s
            LEFT JOIN transactions t ON t.statement_id = s.id
            WHERE s.workspace_id = ?
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """,
            (workspace_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "created_at": row["created_at"],
            "transaction_count": row["transaction_count"],
            "review_count": row["review_count"] or 0,
        }
        for row in rows
    ]


def update_transaction(transaction: Transaction) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE transactions
            SET category = ?, confidence = ?, explanation = ?, rule_id = ?,
                rule_scope = ?, needs_review = ?
            WHERE id = ?
            """,
            (
                transaction.category,
                transaction.confidence,
                transaction.explanation,
                transaction.rule_id,
                transaction.rule_scope,
                int(transaction.needs_review),
                transaction.id,
            ),
        )


def save_audit_event(
    workspace_id: str,
    statement_id: str,
    transaction_id: str,
    old_category: str,
    new_category: str,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO audit_events
            (workspace_id, statement_id, transaction_id, old_category, new_category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (workspace_id, statement_id, transaction_id, old_category, new_category),
        )


def get_audit_events(workspace_id: str) -> list[dict[str, str | int]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, statement_id, transaction_id, old_category, new_category, created_at
            FROM audit_events WHERE workspace_id = ? ORDER BY id DESC LIMIT 100
            """,
            (workspace_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_shared_rule_candidate(workspace_id: str, pattern: str, category: str) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO shared_rule_candidates (workspace_id, pattern, category)
            VALUES (?, ?, ?)
            """,
            (workspace_id, pattern, category),
        )


def get_shared_rule_candidates() -> list[dict[str, str | int]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, workspace_id, pattern, category, status, created_at
            FROM shared_rule_candidates ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_rules(user_id: str) -> list[CategorizationRule]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM rules WHERE user_id = ? ORDER BY rowid", (user_id,)
        ).fetchall()
    return [
        CategorizationRule(
            id=row["id"],
            pattern=row["pattern"],
            category=row["category"],
            scope=row["scope"],
            source=row["source"],
            user_id=row["user_id"],
            exact=bool(row["exact"]),
        )
        for row in rows
    ]


def get_workspaces() -> list[dict[str, str]]:
    with connect() as connection:
        rows = connection.execute("SELECT id, name FROM workspaces ORDER BY name").fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def save_rule(rule: CategorizationRule) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO rules
            (id, user_id, pattern, category, scope, source, exact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.id,
                rule.user_id,
                rule.pattern,
                rule.category,
                rule.scope,
                rule.source,
                int(rule.exact),
            ),
        )


def replace_user_rule(rule: CategorizationRule) -> None:
    with connect() as connection:
        connection.execute(
            "DELETE FROM rules WHERE user_id = ? AND lower(pattern) = lower(?)",
            (rule.user_id, rule.pattern),
        )
    save_rule(rule)
