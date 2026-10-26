from decimal import Decimal

import pytest

from app.brain.models import AccountType
from tests.parsing.helpers import parse_lines

CARD = AccountType.credit_card
CHECKING = AccountType.checking


def amounts(result) -> list[Decimal]:  # type: ignore[no-untyped-def]
    return [row.amount for row in result.rows]


def test_debit_credit_columns() -> None:
    result = parse_lines(
        "Date,Description,Debit,Credit",
        "01/05/2026,FAKE CLIENT,,500.00",
        "01/06/2026,FAKE VENDOR,25.00,",
        "01/07/2026,TRAILING MINUS,25.00-,",  # abs() makes the debit's own sign irrelevant
        "01/08/2026,BOTH,10.00,4.00",
    )

    assert result.detected.sign_convention == "debit_credit_columns"
    assert amounts(result) == [Decimal("500.00"), Decimal("-25.00"), Decimal("-25.00"), -6]


@pytest.mark.parametrize("type_cr", ["CR", "Credit", "cr"])
def test_type_column(type_cr: str) -> None:
    result = parse_lines(
        "Date,Description,Amount,Type",
        f"01/05/2026,FAKE CLIENT,500.00,{type_cr}",
        "01/06/2026,FAKE VENDOR,25.00,DR",
        "01/07/2026,FAKE VENDOR,-25.00,Debit",
        account_type=CARD,
    )

    assert result.detected.sign_convention == "type_column"
    assert amounts(result) == [Decimal("500.00"), Decimal("-25.00"), Decimal("-25.00")]


def test_type_column_with_other_values_is_ignored() -> None:
    result = parse_lines(
        "Date,Description,Amount,Type",
        "01/05/2026,FAKE STORE,-25.00,Sale",
        "01/06/2026,PAYMENT THANK YOU,100.00,Payment",
        account_type=CARD,
    )

    assert result.detected.sign_convention == "charges_negative"
    assert result.rows[0].raw["Type"] == "Sale"


def test_missing_type_value_is_row_error() -> None:
    result = parse_lines(
        "Date,Description,Amount,Type",
        "01/05/2026,FAKE CLIENT,500.00,CR",
        "01/06/2026,FAKE VENDOR,25.00,",
    )

    assert len(result.rows) == 1
    assert result.errors[0].reason == "missing DR/CR type"


def test_cr_dr_markers_on_card() -> None:
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE STORE,25.00",
        "01/06/2026,PAYMENT THANK YOU,100.00 CR",
        account_type=CARD,
    )

    assert result.detected.sign_convention == "cr_dr_markers"
    assert amounts(result) == [Decimal("-25.00"), Decimal("100.00")]


def test_checking_is_as_is() -> None:
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE CLIENT,500.00",
        "01/06/2026,FAKE VENDOR,-25.00",
        account_type=CHECKING,
    )

    assert result.detected.sign_convention == "as_is"
    assert amounts(result) == [Decimal("500.00"), Decimal("-25.00")]
    assert result.warnings == []


def test_card_payments_negative_means_charges_positive() -> None:
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE STORE,25.00",
        "01/06/2026,AUTOPAY PAYMENT,-100.00",
        "01/07/2026,REFUNDED THING,-5.00",
        "01/08/2026,ANOTHER REFUND,-5.00",
        account_type=CARD,
    )

    # Payment rows decide even though most rows are negative.
    assert result.detected.sign_convention == "charges_positive"
    assert "card payment rows are negative" in result.detected.sign_reason
    assert amounts(result) == [Decimal("-25.00"), Decimal("100.00"), Decimal("5.00"), 5]
    assert result.warnings == []


def test_card_payments_positive_means_charges_negative() -> None:
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE STORE,-25.00",
        "01/06/2026,PAYMENT - THANK YOU,100.00",
        account_type=CARD,
    )

    assert result.detected.sign_convention == "charges_negative"
    assert amounts(result) == [Decimal("-25.00"), Decimal("100.00")]


@pytest.mark.parametrize(
    ("values", "convention", "first"),
    [
        (["25.00", "10.00", "-3.00"], "charges_positive", Decimal("-25.00")),
        (["-25.00", "-10.00", "3.00"], "charges_negative", Decimal("-25.00")),
    ],
)
def test_card_majority_vote_warns(values: list[str], convention: str, first: Decimal) -> None:
    lines = [f"01/0{i + 1}/2026,FAKE {i},{v}" for i, v in enumerate(values)]
    result = parse_lines("Date,Description,Amount", *lines, account_type=CARD)

    assert result.detected.sign_convention == convention
    assert result.detected.sign_reason.startswith("majority vote")
    assert result.rows[0].amount == first
    assert any("majority vote" in w for w in result.warnings)


@pytest.mark.parametrize(
    ("charges_positive", "convention", "first"),
    [(True, "charges_positive", Decimal("-25.00")), (False, "charges_negative", 25)],
)
def test_charges_positive_override_wins(
    charges_positive: bool, convention: str, first: Decimal
) -> None:
    # Payment rows would say "charges positive"; the explicit setting overrides that.
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE STORE,25.00",
        "01/06/2026,PAYMENT THANK YOU,-100.00",
        account_type=CARD,
        charges_positive=charges_positive,
    )

    assert result.detected.sign_convention == convention
    assert result.detected.sign_reason == "set explicitly by the uploader"
    assert result.rows[0].amount == first
    assert result.warnings == []


def test_charges_positive_ignored_for_checking() -> None:
    result = parse_lines(
        "Date,Description,Amount",
        "01/05/2026,FAKE VENDOR,-25.00",
        account_type=CHECKING,
        charges_positive=True,
    )

    assert result.detected.sign_convention == "as_is"
    assert result.rows[0].amount == Decimal("-25.00")
    assert any("ignored" in w for w in result.warnings)
