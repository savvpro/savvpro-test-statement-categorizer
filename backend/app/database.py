import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .categorizer import categorize
from .csv_parser import ParsedTransaction
from .models import Category, Statement, Transaction


@contextmanager
def connect(path: Path):
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS statements (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                transaction_count INTEGER NOT NULL,
                duplicate_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                statement_id INTEGER NOT NULL REFERENCES statements(id),
                row_number INTEGER NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                automatic_category TEXT NOT NULL,
                automatic_explanation TEXT NOT NULL,
                manual_category TEXT,
                possible_duplicate INTEGER NOT NULL,
                duplicate_confirmed INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS transactions_statement
            ON transactions(statement_id);
        """)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(transactions)")
        }
        if "duplicate_confirmed" not in columns:
            connection.execute(
                "ALTER TABLE transactions ADD COLUMN duplicate_confirmed INTEGER NOT NULL DEFAULT 0"
            )


def import_statement(path: Path, filename: str, rows: list[ParsedTransaction]) -> int:
    with connect(path) as connection:
        cursor = connection.execute(
            "INSERT INTO statements (filename, created_at, transaction_count, duplicate_count) VALUES (?, ?, ?, ?)",
            (
                filename,
                datetime.now(timezone.utc).isoformat(),
                len(rows),
                sum(row.possible_duplicate for row in rows),
            ),
        )
        statement_id = cursor.lastrowid
        for row in rows:
            decision = categorize(row.description, row.amount, row.transaction_type)
            connection.execute(
                """INSERT INTO transactions
                (statement_id, row_number, date, description, amount, transaction_type,
                 automatic_category, automatic_explanation, possible_duplicate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    statement_id,
                    row.row_number,
                    row.date,
                    row.description,
                    f"{row.amount:.2f}",
                    row.transaction_type,
                    decision.category,
                    decision.explanation,
                    row.possible_duplicate,
                ),
            )
    return statement_id


def list_statements(path: Path) -> list[Statement]:
    with connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM statements ORDER BY id DESC"
        ).fetchall()
    return [Statement(**dict(row)) for row in rows]


def get_statement(path: Path, statement_id: int) -> Statement | None:
    with connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM statements WHERE id = ?", (statement_id,)
        ).fetchone()
    return Statement(**dict(row)) if row else None


def get_transactions(path: Path, statement_id: int) -> list[Transaction]:
    with connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM transactions WHERE statement_id = ? ORDER BY row_number",
            (statement_id,),
        ).fetchall()
    transactions = []
    for row in rows:
        corrected = row["manual_category"] is not None
        category = row["manual_category"] if corrected else row["automatic_category"]
        explanation = (
            "Category confirmed by you." if corrected else row["automatic_explanation"]
        )
        if row["possible_duplicate"]:
            explanation += " Similar date, description and amount in this statement; all matching entries retained."
        transactions.append(
            Transaction(
                **{
                    key: row[key]
                    for key in (
                        "id",
                        "statement_id",
                        "row_number",
                        "date",
                        "description",
                        "amount",
                        "transaction_type",
                        "automatic_category",
                        "automatic_explanation",
                    )
                },
                category=category,
                manual_category=row["manual_category"],
                explanation=explanation,
                needs_review=category == Category.REVIEW
                or (bool(row["possible_duplicate"]) and not row["duplicate_confirmed"]),
                manually_corrected=corrected,
                possible_duplicate=bool(row["possible_duplicate"]),
                duplicate_confirmed=bool(row["duplicate_confirmed"]),
            )
        )
    return transactions


def update_category(
    path: Path, statement_id: int, transaction_id: int, category: Category
) -> bool:
    with connect(path) as connection:
        cursor = connection.execute(
            "UPDATE transactions SET manual_category = ? WHERE id = ? AND statement_id = ?",
            (category, transaction_id, statement_id),
        )
    return cursor.rowcount == 1


def confirm_duplicate(path: Path, statement_id: int, transaction_id: int) -> None:
    with connect(path) as connection:
        connection.execute(
            "UPDATE transactions SET duplicate_confirmed = 1 WHERE id = ? AND statement_id = ?",
            (transaction_id, statement_id),
        )
