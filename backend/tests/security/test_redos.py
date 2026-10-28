import contextlib
import time

import pytest

from app.ingest.amounts import AmountError, parse_amount
from app.ingest.csv_reader import parse_csv
from app.ingest.ofx_reader import parse_ofx
from app.normalize.merchant import clean_description

BUDGET_SECONDS = 2.0


@pytest.mark.parametrize(
    "raw",
    [
        "ZELLE FROM " + "A " * 20_000 + "CONF",
        "ZELLE FROM " + "A" * 100_000,
        "ID " * 30_000,
        "X" * 200_000,
        "(" * 5000 + "1" + ")" * 5000,
        "1 " * 50_000 + "-",
        "#" * 100_000,
        "9" * 100_000 + " " + "1" * 100_000,
    ],
    ids=[
        "zelle-words",
        "zelle-long",
        "id-repeat",
        "x-long",
        "parens",
        "digit-dash",
        "hashes",
        "digits",
    ],
)
def test_merchant_cleaner_is_linear_on_pathological_input(raw: str) -> None:
    start = time.perf_counter()
    key, _, _ = clean_description(raw)
    assert time.perf_counter() - start < BUDGET_SECONDS
    assert 0 < len(key) <= 128


def test_amount_parser_rejects_long_junk_quickly() -> None:
    start = time.perf_counter()
    for raw in ("1," * 50_000 + "x", "(" * 50_000, "." * 50_000):
        with contextlib.suppress(AmountError):
            parse_amount(raw)
    assert time.perf_counter() - start < BUDGET_SECONDS


def test_ofx_tokenizer_handles_unterminated_tags_quickly() -> None:
    start = time.perf_counter()
    text = "<OFX>" + "<A" * 100_000 + "<B>" * 10
    try:
        parse_ofx(text, max_rows=10)
    except Exception:  # noqa: S110
        pass
    assert time.perf_counter() - start < BUDGET_SECONDS


def test_csv_header_scan_on_wide_garbage_is_bounded() -> None:
    start = time.perf_counter()
    text = ",".join("x" for _ in range(50_000)) + "\n" + "a,b\n" * 1000
    try:
        parse_csv(text, max_rows=100)
    except Exception:  # noqa: S110
        pass
    assert time.perf_counter() - start < BUDGET_SECONDS
