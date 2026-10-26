import datetime as dt

import pytest

from app.parsing.dates import DateOrder, detect_date_order, parse_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-01-05", dt.date(2026, 1, 5)),
        ("2026/01/05", dt.date(2026, 1, 5)),
        ("2026-01-05T00:00:00", dt.date(2026, 1, 5)),
        ("01/05/2026", dt.date(2026, 1, 5)),
        ("1/5/2026", dt.date(2026, 1, 5)),
        ("01/05/26", dt.date(2026, 1, 5)),
        ("01-05-2026", dt.date(2026, 1, 5)),
        ("05 Jan 2026", dt.date(2026, 1, 5)),
        ("5-Jan-2026", dt.date(2026, 1, 5)),
        ("05 January 2026", dt.date(2026, 1, 5)),
        ("05 Sept 2026", dt.date(2026, 9, 5)),
        ("Jan 5, 2026", dt.date(2026, 1, 5)),
        ("January 5 2026", dt.date(2026, 1, 5)),
        ("jan 5th, 2026", dt.date(2026, 1, 5)),
    ],
)
def test_parse_month_first(text: str, expected: dt.date) -> None:
    assert parse_date(text, DateOrder.month_first) == expected


def test_day_first_order() -> None:
    assert parse_date("05/01/2026", DateOrder.day_first) == dt.date(2026, 1, 5)
    assert parse_date("25/12/2025", DateOrder.day_first) == dt.date(2025, 12, 25)


def test_order_detected_per_column() -> None:
    # Only one value proves day-first, and it decides for the whole column.
    assert detect_date_order(["01/02/2026", "03/04/2026", "25/04/2026"]) is DateOrder.day_first
    assert detect_date_order(["01/02/2026", "12/04/2026"]) is DateOrder.month_first
    assert detect_date_order(["2026-01-02", "05 Jan 2026"]) is DateOrder.unambiguous


@pytest.mark.parametrize(
    "text",
    ["", "yesterday", "31 Feb 2026", "13/13/2026", "1999-12-31", "2099-01-01", "05 Foo 2026"],
)
def test_invalid_dates_raise(text: str) -> None:
    with pytest.raises(ValueError):
        parse_date(text)


def test_year_upper_bound_is_next_year() -> None:
    next_year = dt.date.today().year + 1
    assert parse_date(f"{next_year}-01-01").year == next_year
    with pytest.raises(ValueError, match="outside"):
        parse_date(f"{next_year + 1}-01-01")
