import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.brain.models import AccountType, TxnStatus
from app.db.models import MerchantRule, Statement, Transaction


def make_statement(db: Session, rows: int = 2) -> Statement:
    statement = Statement(filename="fake_checking.csv", account_type=AccountType.checking)
    for index in range(rows):
        statement.transactions.append(
            Transaction(
                row_index=index,
                date=dt.date(2025, 1, 10 + index),
                description_raw=f"FAKE VENDOR {index}",
                merchant_key=f"FAKE VENDOR {index}",
                amount=Decimal("-19.99"),
                category_id="needs_review",
                status=TxnStatus.needs_review,
            )
        )
    statement.row_count = rows
    db.add(statement)
    db.commit()
    return statement


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_create_statement_with_transactions(db: Session) -> None:
    statement = make_statement(db)
    db.expire_all()

    loaded = db.get(Statement, statement.id)
    assert loaded is not None
    assert loaded.account_type is AccountType.checking
    assert loaded.parse_errors == []
    assert [t.row_index for t in loaded.transactions] == [0, 1]

    txn = loaded.transactions[0]
    assert txn.amount_cents == -1999
    assert txn.amount == Decimal("-19.99")
    assert txn.status is TxnStatus.needs_review
    assert txn.reasons == [] and txn.flags == []
    assert txn.updated_at is not None


def test_delete_statement_cascades(db: Session) -> None:
    statement = make_statement(db, rows=3)
    assert count(db, Transaction) == 3

    db.delete(statement)
    db.commit()

    assert count(db, Statement) == 0
    assert count(db, Transaction) == 0


def test_db_level_cascade_without_orm(db: Session) -> None:
    # Exercises ON DELETE CASCADE in SQLite itself (requires PRAGMA foreign_keys=ON).
    statement = make_statement(db)
    db.execute(Statement.__table__.delete().where(Statement.id == statement.id))
    db.commit()

    assert count(db, Transaction) == 0


def test_linked_refund(db: Session) -> None:
    statement = make_statement(db)
    original, refund = statement.transactions
    refund.linked_transaction = original
    db.commit()
    db.expire_all()

    assert db.get(Transaction, refund.id).linked_transaction_id == original.id


def test_row_index_unique_per_statement(db: Session) -> None:
    statement = make_statement(db, rows=1)
    db.add(
        Transaction(
            statement_id=statement.id,
            row_index=0,
            date=dt.date(2025, 1, 1),
            description_raw="DUP",
            amount_cents=100,
            category_id="needs_review",
            status=TxnStatus.needs_review,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_merchant_rule_defaults(db: Session) -> None:
    db.add(MerchantRule(merchant_key="FAKE CAFE", category_id="meals"))
    db.commit()

    rule = db.scalars(select(MerchantRule)).one()
    assert rule.source == "user"
    assert rule.hits == 0
    assert rule.created_at is not None


def test_merchant_key_unique(db: Session) -> None:
    db.add(MerchantRule(merchant_key="FAKE CAFE", category_id="meals"))
    db.commit()
    db.add(MerchantRule(merchant_key="FAKE CAFE", category_id="travel"))

    with pytest.raises(IntegrityError):
        db.commit()
