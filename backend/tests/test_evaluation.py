import importlib.util
from pathlib import Path

import pytest

from app.brain.models import AccountType, TxnStatus
from tests.brain.helpers import decide

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py"


@pytest.fixture(scope="module")
def report():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("evaluate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate()


def test_every_sample_row_is_labelled(report) -> None:  # type: ignore[no-untyped-def]
    assert {f.name for f in report.files} == {
        "checking_simple.csv",
        "credit_card.csv",
        "bank_messy.csv",
        "credit_card.xlsx",
    }
    assert report.total("rows") == 134


def test_auto_precision(report) -> None:  # type: ignore[no-untyped-def]
    assert report.precision >= 0.97, report.wrong


def test_no_confident_income_expense_flips(report) -> None:  # type: ignore[no-untyped-def]
    assert report.direction_errors == 0


def test_review_rate_is_sane(report) -> None:  # type: ignore[no-untyped-def]
    # Asking about everything would trivially be "precise"; make sure real work gets done.
    assert report.review_rate <= 0.35
    assert report.coverage >= 0.90


# Ten rows that appear in no sample file, written to check the rules generalize.
UNSEEN = [
    ("ZYLOPHANE STUDIOS 4471", "-80.00", "needs_review"),  # unknown vendor
    ("BLUEJAY OUTFITTERS LLC", "-230.00", "needs_review"),  # unknown vendor
    ("SQ *MARLOW BAKERY", "-12.50", "needs_review"),  # unknown restaurant
    ("CASH APP*TAYLOR FAKE", "-60.00", "needs_review"),  # person-to-person
    ("ACH DEPOSIT ORCHID LANE", "1200.00", "needs_review"),  # deposit, no invoice ref
    ("UNITED AIRLINES 0162", "-310.00", "travel"),
    ("HILTON GARDEN INN DENVER CO", "-180.00", "travel"),
    ("FIVERR WITHDRAWAL 88120", "300.00", "client_income"),
    ("TRANSFER FROM SAVINGS XXXX5521", "2000.00", "transfer"),
    ("GITHUB INC SAN FRANCISCO CA", "-4.00", "software_subscriptions"),
]


@pytest.mark.parametrize(("description", "amount", "expected"), UNSEEN)
def test_unseen_rows(description: str, amount: str, expected: str) -> None:
    d = decide((description, amount), account=AccountType.checking)[0]

    if expected == "needs_review":
        assert d.status is TxnStatus.needs_review, d.reasons
    else:
        assert (d.status, d.category_id) == (TxnStatus.auto, expected), d.reasons
