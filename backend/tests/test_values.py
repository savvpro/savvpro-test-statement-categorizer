from datetime import date
from decimal import Decimal

import pytest

from app.parsing.values import (
    DAY_FIRST,
    MONTH_FIRST,
    NeedsUserChoice,
    ValueProblem,
    normalize_description,
    parse_amount,
    parse_date,
    resolve_date_order,
    suggest_rule_pattern,
)


@pytest.mark.parametrize("raw, expected", [
    ("1,250.00", "1250.00"),
    ("-1,250.00", "-1250.00"),
    ("(1,250.00)", "-1250.00"),
    ("1,250.00 DR", "-1250.00"),
    ("1,250.00 CR", "1250.00"),
    ("1250.00-", "-1250.00"),
    ("Rs. 500", "500"),
    ("PKR 2,000.50", "2000.50"),
    ("$12.99", "12.99"),
    ("USD 7", "7"),
    ("\u22125.00", "-5.00"),  # unicode minus sign
])
def test_amounts_in_bank_formats(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["", "abc", "31.2O", "12.345", "1,25,000", "(-5.00)", "1,250.00- DR", "1.2.3"])
def test_amounts_that_are_refused_instead_of_guessed(raw):
    with pytest.raises(ValueProblem):
        parse_amount(raw)


def test_amounts_are_decimal_not_float():
    assert parse_amount("0.10") + parse_amount("0.20") == Decimal("0.30")


def test_day_first_is_detected_from_a_day_above_12():
    assert resolve_date_order(["03/04/2026", "25/04/2026"]) == DAY_FIRST


def test_month_first_is_detected_from_a_second_part_above_12():
    assert resolve_date_order(["03/04/2026", "04/25/2026"]) == MONTH_FIRST


def test_all_ambiguous_dates_ask_the_user():
    with pytest.raises(NeedsUserChoice):
        resolve_date_order(["03/04/2026", "05/06/2026"])


def test_user_choice_settles_ambiguous_dates():
    assert resolve_date_order(["03/04/2026"], MONTH_FIRST) == MONTH_FIRST


def test_user_choice_that_contradicts_the_file_is_refused():
    with pytest.raises(NeedsUserChoice):
        resolve_date_order(["25/04/2026"], MONTH_FIRST)


def test_mixed_formats_in_one_file_are_refused():
    with pytest.raises(NeedsUserChoice):
        resolve_date_order(["25/04/2026", "04/25/2026"])


@pytest.mark.parametrize("raw, expected", [
    ("03/04/2026", date(2026, 4, 3)),
    ("2026-04-03", date(2026, 4, 3)),
    ("03 Apr 2026", date(2026, 4, 3)),
    ("03-APR-26", date(2026, 4, 3)),
    ("Apr 3, 2026", date(2026, 4, 3)),
])
def test_date_formats(raw, expected):
    assert parse_date(raw, DAY_FIRST) == expected


@pytest.mark.parametrize("raw", ["", "31/02/2026", "yesterday", "2026/13/45"])
def test_bad_dates_are_refused(raw):
    with pytest.raises(ValueProblem):
        parse_date(raw, DAY_FIRST)


def test_description_normalising_keeps_domain_dots():
    assert normalize_description("pos  GitHub.com, San-Francisco.") == "POS GITHUB.COM SAN FRANCISCO"


def test_rule_pattern_suggestion_drops_reference_numbers():
    assert suggest_rule_pattern("POS 4471 JOES CAFE 9921") == "JOES CAFE"
