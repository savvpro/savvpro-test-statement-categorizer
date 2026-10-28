from datetime import date, timedelta

import pytest

from app.ingest.dates import (
    DateError,
    infer_format,
    is_future,
    parse_date,
    parse_ofx_date,
)


def test_P10_all_days_up_to_12_is_ambiguous_mdy() -> None:
    inf = infer_format(["01/02/2026", "03/04/2026", "05/06/2026"])
    assert inf.fmt == "%m/%d/%Y"
    assert inf.ambiguous


def test_P11_dmy_with_a_25th_is_chosen_without_warning() -> None:
    inf = infer_format(["25/01/2026", "03/02/2026"])
    assert inf.fmt == "%d/%m/%Y"
    assert not inf.ambiguous


def test_mdy_with_a_25th_is_unambiguous() -> None:
    inf = infer_format(["01/25/2026", "02/03/2026"])
    assert inf.fmt == "%m/%d/%Y"
    assert not inf.ambiguous


@pytest.mark.parametrize(
    ("value", "fmt"),
    [
        ("2026-01-15", "%Y-%m-%d"),
        ("15-Jan-2026", "%d-%b-%Y"),
        ("Jan 15, 2026", "%b %d, %Y"),
        ("20260115", "%Y%m%d"),
        ("1/15/26", "%m/%d/%y"),
    ],
)
def test_other_formats(value: str, fmt: str) -> None:
    inf = infer_format([value])
    assert inf.fmt == fmt
    assert parse_date(value, fmt) == date(2026, 1, 15)


def test_time_suffix_is_ignored() -> None:
    assert parse_date("2026-01-15 10:30:00", "%Y-%m-%d") == date(2026, 1, 15)


def test_majority_format_wins_when_none_fit_all() -> None:
    inf = infer_format(["01/15/2026", "01/16/2026", "garbage"])
    assert inf.fmt == "%m/%d/%Y"
    with pytest.raises(DateError):
        parse_date("garbage", inf.fmt)


def test_nothing_parses() -> None:
    assert infer_format(["foo", "bar"]).fmt is None


def test_year_before_2000_is_row_error() -> None:
    with pytest.raises(DateError):
        parse_date("01/15/1999", "%m/%d/%Y")


@pytest.mark.parametrize(
    "raw",
    [
        "20260115",
        "20260115120000",
        "20260115120000.000",
        "20260115120000.000[-5:EST]",
        "20260115[0:GMT]",
    ],
)
def test_ofx_dates(raw: str) -> None:
    assert parse_ofx_date(raw) == date(2026, 1, 15)


def test_ofx_date_garbage() -> None:
    with pytest.raises(DateError):
        parse_ofx_date("2026-01-15")
    with pytest.raises(DateError):
        parse_ofx_date("20261340")


def test_P25_future_date() -> None:
    today = date(2026, 1, 1)
    assert is_future(today + timedelta(days=8), today)
    assert not is_future(today + timedelta(days=7), today)
