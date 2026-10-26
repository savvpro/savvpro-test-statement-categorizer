import pytest
from pydantic import ValidationError

from app.domain import ImportOptions
from app.importer import ImportFailure, parse_amount, parse_statement, preview


def options(**changes):
    return ImportOptions(
        **dict(
            dict(
                date_column="Date",
                description_column="Description",
                amount_column="Amount",
                mode="signed",
                date_format="iso",
                sign_convention="negative_outgoing",
                currency="USD",
            ),
            **changes,
        )
    )


@pytest.mark.parametrize(
    "raw,expected",
    [("-12.34", -1234), ("0", 0), ("(1,250.00)", -125000), ("+10.20", 1020), ("1,000", 100000)],
)
def test_amounts(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "NaN", "Infinity", "1e3", "1.001", "1,23", "$15", "--5", "(+10)", "10000000001"]
)
def test_invalid_amounts(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


def test_bom_quoted_commas_and_source_rows():
    content = '\ufeffDate,Description,Amount\n\n2026-10-01,"Acme, Inc.","-1,234.56"\n'.encode()
    rows, blanks = parse_statement(content, options())
    assert rows[0].description == "Acme, Inc."
    assert rows[0].source_row == 3
    assert rows[0].amount_minor == -123456
    assert blanks == 1


def test_multiline_description_has_physical_line_number():
    rows, _ = parse_statement(
        b'Date,Description,Amount\n2026-10-01,"Acme\nInc",-1\n2026-10-02,Figma,-2\n', options()
    )
    assert [r.source_row for r in rows] == [2, 4]


def test_split_columns():
    config = options(mode="split", debit_column="Debit", credit_column="Credit")
    rows, _ = parse_statement(
        b"Date,Description,Debit,Credit\n2026-10-01,A,10,\n2026-10-02,B,,5", config
    )
    assert [r.amount_minor for r in rows] == [-1000, 500]


def test_date_and_sign_interpretation():
    rows, _ = parse_statement(
        b"Date,Description,Amount\n03/04/2026,Figma,12",
        options(date_format="dmy", sign_convention="positive_outgoing"),
    )
    assert rows[0].date == "2026-04-03" and rows[0].amount_minor == -1200


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"Date,Description,Amount\n",
        b"Date,Date,Amount\n2026-01-01,A,1",
        b"Date,Description,Amount\n2026-02-30,A,-1",
        b"Date,Description,Amount\n2026-02-01,,-1",
        b"Date,Description,Amount\n2026-02-01,A,1.001",
        b"Date,Description,Amount\n2026-02-01,A,-1,extra",
        b'Date,Description,Amount\n2026-02-01,"unterminated,-1',
        b"Date,Description,Amount\n2026-02-01,\xff,-1",
    ],
)
def test_invalid_files(content):
    with pytest.raises(ImportFailure):
        parse_statement(content, options())


def test_atomic_validation_reports_invalid_source_row():
    with pytest.raises(ImportFailure) as exc:
        parse_statement(b"Date,Description,Amount\n2026-02-01,Figma,-1\nwrong,X,2", options())
    assert exc.value.errors[0]["row"] == 3


def test_missing_mapping():
    with pytest.raises(ImportFailure):
        parse_statement(b"Date,Description,Other\n2026-02-01,A,2", options())
    with pytest.raises(ValidationError):
        options(description_column="Date")


def test_preview_suggests_only_columns():
    result = preview(b"Date,Description,Amount\n2026-01-01,A,-1")
    assert result["suggestions"]["amount_column"] == "Amount"
    assert result["row_count"] == 1


def test_raw_description_preserved():
    rows, _ = parse_statement(b"Date,Description,Amount\n2026-01-01,  FiGMA  ,1", options())
    assert rows[0].description == "  FiGMA  "


def test_oversized_number_is_validation_error():
    with pytest.raises(ValueError):
        parse_amount("9" * 10000)


def test_row_limit():
    content = b"Date,Description,Amount\n" + b"2026-01-01,Figma,-1\n" * 5001
    with pytest.raises(ImportFailure):
        parse_statement(content, options())


@pytest.mark.parametrize("debit,credit", [("1", "1"), ("-1", ""), ("", ""), ("", "-5")])
def test_invalid_split_layout(debit, credit):
    config = options(mode="split", debit_column="Debit", credit_column="Credit")
    with pytest.raises(ImportFailure):
        parse_statement(
            f"Date,Description,Debit,Credit\n2026-01-01,A,{debit},{credit}".encode(), config
        )


def test_explicit_currency_column_must_match_statement():
    content = b"Date,Description,Amount,Currency\n2026-01-01,Figma,-1,EUR"
    with pytest.raises(ImportFailure) as exc:
        parse_statement(content, options(currency="USD"))
    assert exc.value.errors[0]["field"] == "currency"
    assert parse_statement(content, options(currency="EUR"))[0][0].amount_minor == -100
