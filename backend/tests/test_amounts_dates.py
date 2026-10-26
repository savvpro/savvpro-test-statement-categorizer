from datetime import date
from decimal import Decimal

import pytest

from app.parsing.amounts import detect_currency, parse_amount
from app.parsing.dates import (
    DMY,
    MDY,
    fix_year_rollover,
    guess_year,
    has_year,
    infer_date_order,
    parse_date,
    split_date_prefix,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("54.99", "54.99"),
        ("-54.99", "-54.99"),
        ("+12", "12.00"),
        ("$1,250.00", "1250.00"),
        ("(45.10)", "-45.10"),
        ("45.10-", "-45.10"),
        ("USD 99.5", "99.50"),
        ("1.234,56", "1234.56"),
        ("12,50", "12.50"),
        ("1,234", "1234.00"),
        ("1.234.567", "1234567.00"),
        ("−12.00", "-12.00"),
        ("  7.10 ", "7.10"),
        ("0.005", "0.01"),
    ],
)
def test_parse_amount_formats(text, expected):
    result = parse_amount(text)
    assert result is not None
    assert result.value == Decimal(expected)


@pytest.mark.parametrize("text", [None, "", "   ", "abc", "12.3.4x", "--5", "N/A"])
def test_parse_amount_rejects_non_numbers(text):
    assert parse_amount(text) is None


def test_parse_amount_reads_cr_dr_suffix():
    credit = parse_amount("25.00 CR")
    debit = parse_amount("25.00DR")
    assert credit is not None and credit.suffix == "CR" and credit.value == Decimal("25.00")
    assert debit is not None and debit.suffix == "DR"


@pytest.mark.parametrize(
    ("text", "order", "expected"),
    [
        ("2026-03-14", MDY, date(2026, 3, 14)),
        ("2026/03/14", DMY, date(2026, 3, 14)),
        ("03/14/2026", MDY, date(2026, 3, 14)),
        ("14/03/2026", DMY, date(2026, 3, 14)),
        ("14.03.26", DMY, date(2026, 3, 14)),
        ("14 Mar 2026", MDY, date(2026, 3, 14)),
        ("Mar 14, 2026", MDY, date(2026, 3, 14)),
        ("14-Mar-26", MDY, date(2026, 3, 14)),
        ("March 14th 2026", MDY, date(2026, 3, 14)),
        ("2026-03-14T10:11:12", MDY, date(2026, 3, 14)),
    ],
)
def test_parse_date_formats(text, order, expected):
    assert parse_date(text, order) == expected


def test_parse_date_rejects_impossible_and_implausible_dates():
    assert parse_date("31/02/2026", DMY) is None
    assert parse_date("13/13/2026", MDY) is None
    assert parse_date("01/01/1850", MDY) is None
    assert parse_date("hello", MDY) is None
    assert parse_date(None) is None


def test_parse_date_without_year_uses_default_year():
    assert parse_date("Mar 14", MDY, default_year=2026) == date(2026, 3, 14)
    assert parse_date("03/14", MDY, default_year=2026) == date(2026, 3, 14)
    assert parse_date("Mar 14", MDY) is None


def test_infer_date_order_uses_whole_column():
    assert infer_date_order(["01/02/2026", "25/02/2026"]).order == DMY
    assert infer_date_order(["01/02/2026", "02/25/2026"]).order == MDY
    ambiguous = infer_date_order(["01/02/2026", "03/04/2026"])
    assert ambiguous.ambiguous and ambiguous.order == MDY


# -- month names in other languages --------------------------------------------------------------

MONTH_SAMPLES = {
    "english": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "french": [
        "janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
        "nov.", "déc.",
    ],
    "french_plain": [
        "janv", "fevr", "mars", "avr", "mai", "juin", "juil", "aout", "sept", "oct", "nov", "dec",
    ],
    "french_full": [
        "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre",
    ],
    "dutch": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "dutch_full": [
        "januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
        "oktober", "november", "december",
    ],
    "spanish": [
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic",
    ],
    "spanish_full": [
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
        "octubre", "noviembre", "diciembre",
    ],
    "german": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    "german_full": [
        "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
        "Oktober", "November", "Dezember",
    ],
}  # fmt: skip


@pytest.mark.parametrize("language", sorted(MONTH_SAMPLES))
def test_month_names_in_each_language(language):
    for number, name in enumerate(MONTH_SAMPLES[language], start=1):
        assert parse_date(f"14 {name} 2026", DMY) == date(2026, number, 14), name
        assert parse_date(f"5 {name.upper()}", DMY, 2026) == date(2026, number, 5), name


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("02 janv. 25", date(2025, 1, 2)),
        ("1er mars 2026", date(2026, 3, 1)),
        ("1 mei", date(2026, 5, 1)),
        ("15. Mai 2026", date(2026, 5, 15)),
        ("14/03", date(2026, 3, 14)),
        ("15.05.", date(2026, 5, 15)),
        ("14-03-26", date(2026, 3, 14)),
        ("05JAN", date(2026, 1, 5)),
        ("05JAN26", date(2026, 1, 5)),
        ("Sept. 14, 2026", date(2026, 9, 14)),
        ("2026-03-14", date(2026, 3, 14)),
    ],
)
def test_date_layouts(text, expected):
    assert parse_date(text, DMY, 2026) == expected


def test_unknown_month_names_are_not_dates():
    assert parse_date("14 xyz 2026", DMY) is None
    assert parse_date("14 total 2026", DMY) is None


def test_order_is_inferred_from_dates_without_a_year():
    assert infer_date_order(["09/13", "09/01"]).order == MDY
    assert infer_date_order(["27/08", "01/09"]).order == DMY
    assert infer_date_order(["01/02", "03/04"]).ambiguous


def test_date_prefix_is_split_off_a_description():
    assert split_date_prefix("02 janv. 25 SKIP PLATS") == ("02 janv. 25", "SKIP PLATS")
    assert split_date_prefix("Mar 01  ADOBE") == ("Mar 01", "ADOBE")
    assert split_date_prefix("2026-03-01 X") == ("2026-03-01", "X")
    assert split_date_prefix("12 AVENUE FOCH") is None
    assert split_date_prefix("SKIP PLATS") is None


def test_has_year():
    assert has_year("02 janv. 25") and has_year("03/04/2026") and has_year("2026-01-02")
    assert not has_year("1 mei") and not has_year("Mar 01") and not has_year("03/04")


def test_year_is_guessed_from_complete_dates_not_stray_numbers():
    text = "Order 4821 2023 ref\nStatement 30/09/2025\nFee since 1 Sep 2024\nClosing 30/09/2025"
    assert guess_year(text) == 2025
    assert guess_year("Statement closing January 15, 2026") == 2026
    assert guess_year("Reference 2021 only") == 2021
    assert guess_year("nothing here") is None


def _roll(months, reference=2026):
    dates = [date(reference, m, 15) for m in months]
    fixed = fix_year_rollover(dates, [True] * len(dates), reference)
    return [d.year for d in fixed]


def test_year_rollover_moves_the_months_before_the_new_year_back():
    assert _roll([12, 1]) == [2025, 2026]
    assert _roll([11, 12, 1, 2]) == [2025, 2025, 2026, 2026]
    assert _roll([10, 11, 12, 1, 2]) == [2025, 2025, 2025, 2026, 2026]


def test_year_rollover_leaves_ordinary_statements_alone():
    assert _roll([3, 4]) == [2026, 2026]
    assert _roll([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) == [2026] * 12
    assert _roll([5]) == [2026]


def test_dates_with_their_own_year_are_not_rolled_back():
    dates = [date(2026, 12, 20), date(2026, 1, 3)]
    assert fix_year_rollover(dates, [False, True], 2026) == dates


# -- currency and amounts ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Gross Amount (£)", "GBP"),
        ("114,83 €", "EUR"),
        ("$ Amount", "USD"),
        ("Rs. 500", "INR"),
        ("₹1,200.00", "INR"),
        ("USD 99.5", "USD"),
        ("Amount (SGD)", "SGD"),
        ("Amount", None),
        ("", None),
    ],
)
def test_detect_currency(text, code):
    assert detect_currency(text) == code


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("114,83 €", "114.83"),
        ("€ 12,50", "12.50"),
        ("1 234,56", "1234.56"),
        ("1 234,56", "1234.56"),
        ("10 598,70 $", "10598.70"),
        ("-1.450,77 €", "-1450.77"),
        ("1,20,000.00", "120000.00"),
        (".90", "0.90"),
        ("Rs. 1,200.50", "1200.50"),
    ],
)
def test_amounts_in_either_separator_style_with_symbols(text, expected):
    result = parse_amount(text)
    assert result is not None and result.value == Decimal(expected)


def test_amount_reports_its_currency_and_a_leading_cr_dr():
    assert parse_amount("£1,400.70").currency == "GBP"
    assert parse_amount("12.50").currency is None
    leading = parse_amount("CR 5.00")
    assert leading is not None and leading.suffix == "CR" and leading.value == Decimal("5.00")
    assert parse_amount("100.00 Cr").suffix == "CR"
