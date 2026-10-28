import pytest

from app.core.errors import ParseError
from app.ingest import parse_statement
from app.ingest.csv_reader import parse_csv, sniff_delimiter
from tests.factories import bank_csv


def codes(result: object) -> list[str]:
    return [w.code for w in result.warnings]  # type: ignore[attr-defined]


def test_basic_parse_and_row_indexes() -> None:
    res = parse_csv(bank_csv(), max_rows=100)
    assert [r.row_index for r in res.rows] == [1, 2, 3, 4]
    assert res.rows[1].description_raw.startswith("POS DEBIT HOME DEPOT")
    assert res.date_format == "%m/%d/%Y"


def test_P03_semicolon_decimal_comma() -> None:
    text = "Date;Description;Amount\n15/01/2026;RENT;1.800,00\n16/01/2026;SHELL;-45,10\n"
    res = parse_csv(text, max_rows=100)
    assert res.decimal_comma
    assert "DECIMAL_COMMA" in codes(res)
    assert res.date_format == "%d/%m/%Y"


def test_P04_preamble_skipped() -> None:
    text = (
        "Account: 1234\nStatement period: Jan 2026\n\nDate,Description,Amount\n01/15/2026,X,-1.00\n"
    )
    res = parse_csv(text, max_rows=100)
    assert "PREAMBLE_SKIPPED" in codes(res)
    assert len(res.rows) == 1


def test_P05_footer_rows_skipped() -> None:
    text = bank_csv() + "Ending Balance,,5000.00\n,TOTAL,123.00\n"
    res = parse_csv(text, max_rows=100)
    assert len(res.rows) == 4
    assert codes(res).count("SUMMARY_ROW_SKIPPED") == 2


def test_P06_blank_lines_ignored() -> None:
    text = "Date,Description,Amount\n\n01/15/2026,X,-1.00\n\n\n01/16/2026,Y,-2.00\n"
    res = parse_csv(text, max_rows=100)
    assert [r.row_index for r in res.rows] == [2, 5]


def test_P07_quoted_description_with_comma() -> None:
    text = 'Date,Description,Amount\n01/15/2026,"SMITH, JOHN PLUMBING",-80.00\n'
    assert parse_csv(text, max_rows=100).rows[0].description_raw == "SMITH, JOHN PLUMBING"


def test_P08_debit_credit_columns() -> None:
    text = "Posted Date,Payee,Debit,Credit\n01/15/2026,SHELL,45.00,\n01/16/2026,RENT,,1800.00\n"
    res = parse_csv(text, max_rows=100)
    assert res.rows[0].debit_raw == "45.00"
    assert res.rows[1].credit_raw == "1800.00"
    assert res.rows[0].amount_raw is None


def test_both_debit_and_credit_is_row_error() -> None:
    rows = "".join(f"01/{d:02d}/2026,X,1.00,\n" for d in range(1, 29))
    text = "Date,Description,Debit,Credit\n" + rows + "01/29/2026,BAD,5.00,5.00\n"
    res = parse_csv(text, max_rows=100)
    assert len(res.rows) == 28
    assert "BOTH_DEBIT_CREDIT" in codes(res)


def test_posted_date_preferred_over_transaction_date() -> None:
    text = "Transaction Date,Posted Date,Description,Amount\n01/01/2026,01/03/2026,X,-1.00\n"
    assert parse_csv(text, max_rows=100).rows[0].date_raw == "01/03/2026"


def test_P14_missing_amount_column_lists_missing() -> None:
    with pytest.raises(ParseError) as exc:
        parse_csv("Date,Description\n01/15/2026,X\n", max_rows=100)
    assert exc.value.code == "MISSING_COLUMNS"
    assert "amount" in str(exc.value.detail)


def test_no_header_is_422() -> None:
    with pytest.raises(ParseError) as exc:
        parse_csv("foo,bar\n1,2\n", max_rows=100)
    assert exc.value.code == "NO_HEADER"


def _hundred_rows(bad: int) -> str:
    lines = ["Date,Description,Amount"]
    for i in range(100):
        amount = "oops" if i < bad else "-1.00"
        lines.append(f"01/{(i % 28) + 1:02d}/2026,ROW {i},{amount}")
    return "\n".join(lines) + "\n"


def test_P15_three_bad_rows_of_100_are_warnings() -> None:
    res = parse_csv(_hundred_rows(3), max_rows=1000)
    assert len(res.rows) == 97
    assert codes(res).count("BAD_AMOUNT") == 3


def test_P16_thirty_percent_bad_is_422_with_first_20_errors() -> None:
    with pytest.raises(ParseError) as exc:
        parse_csv(_hundred_rows(30), max_rows=1000)
    assert exc.value.code == "TOO_MANY_BAD_ROWS"
    assert exc.value.errors is not None
    assert len(exc.value.errors) == 20


def test_malformed_short_row_counts_as_failure() -> None:
    text = "Date,Description,Amount\n" + "01/15/2026,X,-1.00\n" * 40 + "01/16/2026\n"
    res = parse_csv(text, max_rows=100)
    assert len(res.rows) == 40
    assert "MALFORMED_ROW" in codes(res)


def test_row_limit() -> None:
    with pytest.raises(ParseError) as exc:
        parse_csv(bank_csv(), max_rows=3)
    assert exc.value.code == "ROW_LIMIT"


def test_P10_ambiguous_dates_warning_end_to_end() -> None:
    text = "Date,Description,Amount\n01/02/2026,X,-1.00\n03/04/2026,Y,-2.00\n"
    _, res = parse_statement(text.encode(), "a.csv")
    assert "AMBIGUOUS_DATE_ORDER" in codes(res)


def test_P25_future_date_warns_but_keeps_row() -> None:
    text = "Date,Description,Amount\n01/15/2099,X,-1.00\n"
    res = parse_csv(text, max_rows=10)
    assert len(res.rows) == 1
    assert "FUTURE_DATE" in codes(res)


def test_status_and_type_columns_carried() -> None:
    text = "Date,Description,Amount,Type,Status\n01/15/2026,X,5.00,DR,Pending\n"
    row = parse_csv(text, max_rows=10).rows[0]
    assert (row.type_raw, row.status_raw) == ("DR", "Pending")


@pytest.mark.parametrize(
    ("text", "delim"),
    [
        ("a,b,c\n1,2,3\n", ","),
        ("a;b;c\n1,5;2;3\n", ";"),
        ("a\tb\tc\n1\t2\t3\n", "\t"),
        ("a|b|c\n1|2|3\n", "|"),
        ("Account 1234\na,b,c\n1,2,3\n", ","),
    ],
)
def test_delimiter_sniffing(text: str, delim: str) -> None:
    assert sniff_delimiter(text) == delim


def test_P22_crlf_end_to_end() -> None:
    data = bank_csv().replace("\n", "\r\n").encode()
    _, res = parse_statement(data, "a.csv")
    assert len(res.rows) == 4


def test_P01_bom_end_to_end() -> None:
    _, res = parse_statement(b"\xef\xbb\xbf" + bank_csv().encode(), "a.csv")
    assert codes(res) == []


def test_no_transactions_is_422() -> None:
    with pytest.raises(ParseError):
        parse_statement(b"Date,Description,Amount\n", "a.csv")


def test_P15_small_file_tolerates_two_bad_rows() -> None:
    good = "01/15/2026,X,-1.00\n" * 12
    text = "Date,Description,Amount\n" + good + "01/16/2026,Y,oops\n01/17/2026,Z,bad\n"
    res = parse_csv(text, max_rows=100)
    assert len(res.rows) == 12
    assert codes(res).count("BAD_AMOUNT") == 2


def test_P16_three_bad_rows_of_14_refused() -> None:
    good = "01/15/2026,X,-1.00\n" * 11
    text = "Date,Description,Amount\n" + good + "01/16/2026,Y,oops\n" * 3
    with pytest.raises(ParseError):
        parse_csv(text, max_rows=100)
