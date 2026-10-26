import json
import threading
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.models import Convention, Kind, SourceFormat, Statement, Status, Transaction
from app.storage.repository import InMemoryStatementRepository
from app.storage.user_rules import UserRuleStore
from app.summary import summarize


def txn(i, category, name, kind, spend, status=Status.CATEGORIZED):
    return Transaction(
        id=f"t-{i:04d}",
        line=i,
        date=date(2026, 3, i),
        description=f"row {i}",
        merchant="M",
        amount=Decimal(spend),
        spend_amount=Decimal(spend),
        currency="USD",
        category_id=category,
        category_name=name,
        kind=kind,
        status=status,
        confidence=0.9,
    )


def test_summary_numbers():
    rows = [
        txn(1, "software", "Software", Kind.EXPENSE, "100.00"),
        txn(2, "software", "Software", Kind.EXPENSE, "-25.00"),  # a refund reduces the category
        txn(3, "travel", "Travel", Kind.EXPENSE, "40.00"),
        txn(4, "transfer", "Transfer", Kind.NON_SPENDING, "500.00", Status.EXCLUDED),
        txn(5, "card_payment", "Card payment", Kind.NON_SPENDING, "-300.00", Status.EXCLUDED),
        txn(6, "income", "Income", Kind.INCOME, "-900.00"),
        txn(7, "needs_review", "Needs Review", Kind.REVIEW, "12.00", Status.NEEDS_REVIEW),
    ]
    s = summarize(rows)
    assert s.total_spending == Decimal("140.00")
    assert s.total_refunds == Decimal("25.00")
    assert s.net_spending == Decimal("115.00")
    assert s.excluded_total == Decimal("800.00")
    assert s.income_total == Decimal("900.00")
    assert s.needs_review_count == 1
    assert s.transaction_count == 7
    totals = {c.category_id: c.total for c in s.totals}
    assert totals["software"] == Decimal("75.00")
    assert [c.total for c in s.totals] == sorted((c.total for c in s.totals), reverse=True)


def test_summary_of_nothing():
    s = summarize([])
    assert s.net_spending == Decimal("0") and s.totals == ()


def statement(i):
    return Statement(
        id=f"s{i}",
        filename="a.csv",
        currency="USD",
        created_at=datetime.now(UTC),
        source_format=SourceFormat.CSV,
        convention=Convention.POSITIVE_IS_SPENDING,
        transactions=(),
        rejected_rows=(),
        warnings=(),
    )


def test_repository_evicts_the_oldest_statement():
    repo = InMemoryStatementRepository(capacity=2)
    for i in range(3):
        repo.save(statement(i))
    assert repo.get("s0") is None
    assert repo.get("s1") and repo.get("s2")


def test_repository_is_safe_under_concurrent_writes():
    repo = InMemoryStatementRepository(capacity=500)
    threads = [
        threading.Thread(target=lambda n=n: [repo.save(statement(n * 100 + j)) for j in range(50)])
        for n in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert repo.get("s749") is not None


def test_user_rules_persist_between_instances(tmp_path):
    path = tmp_path / "nested" / "rules.json"
    store = UserRuleStore(path)
    store.set("JOES CAFE", "meals")
    assert UserRuleStore(path).get("JOES CAFE") == "meals"


def test_user_rules_survive_a_corrupt_file(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text("{not json", encoding="utf-8")
    store = UserRuleStore(path)
    assert store.all() == {}
    store.set("A", "meals")
    assert json.loads(path.read_text(encoding="utf-8")) == {"A": "meals"}


def test_user_rules_drop_unknown_categories_on_load(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"A": "meals", "B": "not-a-category", "C": 5}), encoding="utf-8")
    assert UserRuleStore(path).all() == {"A": "meals"}


def test_user_rules_ignore_blank_keys_and_work_without_a_file():
    store = UserRuleStore(None)
    store.set("  ", "meals")
    store.set("X", "meals")
    assert store.all() == {"X": "meals"}
