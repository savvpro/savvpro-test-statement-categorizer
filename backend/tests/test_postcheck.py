from datetime import date
from decimal import Decimal

import pytest

from app.brain.models import Decision
from app.brain.postcheck import postcheck
from app.ingest.models import ParsedRow


def row(n: int, description="ADOBE", amount="-59.99", day=1) -> ParsedRow:
    return ParsedRow(
        row_number=n,
        date=date(2026, 9, day),
        raw_description=description,
        amount=Decimal(amount),
        currency="USD",
        account_type="card",
    )


def decision(category="Software & Subscriptions", needs_review=False, reason="adobe") -> Decision:
    return Decision(
        category=category,
        kind="expense",
        confidence=0.95,
        rule_id="adobe",
        reason=reason,
        needs_review=needs_review,
    )


def test_second_occurrence_is_flagged_and_keeps_its_category() -> None:
    out = postcheck([row(1), row(2)], [decision(), decision()])
    assert out[0] == decision()
    assert out[1].needs_review is True
    assert out[1].category == "Software & Subscriptions"
    assert out[1].reason == "possible duplicate of row 1"
    assert out[1].rule_id == "adobe"


def test_later_copies_all_point_to_the_first() -> None:
    out = postcheck([row(3), row(5), row(9)], [decision()] * 3)
    assert [d.needs_review for d in out] == [False, True, True]
    assert out[2].reason == "possible duplicate of row 3"


@pytest.mark.parametrize(
    "other",
    [
        row(2, amount="-60.00"),
        row(2, day=2),
        row(2, description="ADOBE INC"),
        row(2, amount="59.99"),
    ],
)
def test_not_a_duplicate_if_anything_differs(other: ParsedRow) -> None:
    out = postcheck([row(1), other], [decision(), decision()])
    assert [d.needs_review for d in out] == [False, False]


def test_comparison_uses_normalized_text_and_decimal_value() -> None:
    a = row(1, description="Adobe  Creative Cloud", amount="-59.9")
    b = row(2, description="  ADOBE CREATIVE   CLOUD ", amount="-59.90")
    assert postcheck([a, b], [decision(), decision()])[1].needs_review is True


def test_already_review_row_keeps_its_own_reason() -> None:
    unknown = decision(category="Needs Review", needs_review=True, reason="no rule matched")
    out = postcheck([row(1), row(2)], [unknown, unknown])
    assert out[1].reason == "possible duplicate of row 1; no rule matched"


def test_no_rows() -> None:
    assert postcheck([], []) == []


def test_length_mismatch_is_an_error() -> None:
    with pytest.raises(ValueError):
        postcheck([row(1)], [])


def test_inputs_are_not_modified() -> None:
    original = [decision(), decision()]
    postcheck([row(1), row(2)], original)
    assert original[1].needs_review is False
