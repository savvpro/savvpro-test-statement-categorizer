import pytest
from statement_categorizer.domain import AmountMode, DateFormat, ImportOptions
from statement_categorizer.parser import MAX_FILE_BYTES, StatementError, parse_money, parse_statement


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-12.34", -1234),
        ("(12.34)", -1234),
        ("$1,234.56", 123456),
        ("USD 12.1", 1210),
        ("0.01", 1),
        ("-0.00", 0),
        ("+12", 1200),
        ("($12.34)", -1234),
    ],
)
def test_exact_money(raw, expected):
    assert parse_money(raw, "USD") == expected


@pytest.mark.parametrize(
    "raw",
    [
        "12.345",
        "NaN",
        "Infinity",
        "1e3",
        "1,23",
        "12,34.56",
        "--10",
        "(-10)",
        "(+10)",
        "1 000.00",
        "£10",
        "",
        "100000001",
    ],
)
def test_invalid_amounts_are_not_rounded_or_guessed(raw):
    with pytest.raises(ValueError):
        parse_money(raw, "USD")


def test_utf8_bom_aliases_thousands_and_multiline_description():
    raw = '\ufeffTransaction Date,Details,Amount\r\n2026-04-02,"ADOBE\nCLOUD","-1,234.56"\r\n\r\n2026-04-03,FIGMA,-15\r\n'.encode()
    rows = parse_statement(raw, ImportOptions())
    assert len(rows) == 2 and rows[0].amount_minor == -123456
    assert rows[0].source_row == 2 and rows[1].source_row == 5


def test_card_and_split_adapters_normalize_direction():
    card = b"Date,Description,Amount\n04/02/2026,FIGMA,15\n04/03/2026,FIGMA REFUND,-5\n"
    rows = parse_statement(card, ImportOptions(amount_mode=AmountMode.CARD, date_format=DateFormat.MDY))
    assert [row.amount_minor for row in rows] == [-1500, 500]
    split = b"Date;Description;Debit;Credit\n02/04/2026;FIGMA;15;\n03/04/2026;REFUND FIGMA;;5\n"
    rows = parse_statement(split, ImportOptions(amount_mode=AmountMode.SPLIT, date_format=DateFormat.DMY))
    assert [row.amount_minor for row in rows] == [-1500, 500]
    assert rows[0].date == "2026-04-02"


@pytest.mark.parametrize(
    "csv",
    [
        "Date,Description,Amount\n2026-04-02,,10",
        "Date,Description,Amount\n2026-02-30,FIGMA,10",
        "Date,Description,Amount\n03/04/2026,FIGMA,10",
        "Date,Description,Amount\n2026-04-02,FIGMA,1,000.00",
        "Date,Description,Amount,Currency\n2026-04-02,FIGMA,10,EUR",
        "Date,Description,Amount,Status\n2026-04-02,FIGMA,10,voided",
        "Date,Description,Amount\n2026-04-02,FIGMA,NaN",
        "Date,Description,Amount\n2026-04-02,FIGMA\x1b,10",
    ],
)
def test_invalid_rows_report_source_line(csv):
    with pytest.raises(StatementError) as error:
        parse_statement(csv.encode(), ImportOptions())
    assert error.value.errors[0]["row"] == 2


@pytest.mark.parametrize(
    "csv",
    [
        "Date,Description,Amount,Amount\n2026-04-02,FIGMA,10,10",
        "Date,Description,Amount,Debit,Credit\n2026-04-02,FIGMA,10,10,0",
        "Date,Merchant,Description,Amount\n2026-04-02,FIGMA,FIGMA,10",
        "Date,Description\n2026-04-02,FIGMA",
        "Date,Description,Amount\n",
        'Date,Description,Amount\n2026-04-02,"unterminated,10',
    ],
)
def test_invalid_schemas_and_empty_csv_fail(csv):
    with pytest.raises(StatementError):
        parse_statement(csv.encode(), ImportOptions())


@pytest.mark.parametrize("values", ["10,20", "-10,0", ","])
def test_split_amounts_cannot_conflict(values):
    raw = f"Date,Description,Debit,Credit\n2026-04-02,FIGMA,{values}".encode()
    with pytest.raises(StatementError):
        parse_statement(raw, ImportOptions(amount_mode=AmountMode.SPLIT))


def test_pending_zero_and_tabs_are_preserved():
    rows = parse_statement(b"Date\tDescription\tAmount\tStatus\n2026-04-02\tFIGMA\t0\tpending", ImportOptions())
    assert rows[0].pending and rows[0].amount_minor == 0


def test_limits_and_encoding(monkeypatch):
    with pytest.raises(ValueError, match="too long"):
        parse_money("9" * 10000, "USD")
    for content in [b"", b"\xff", b"a\x00b", b"a" * (MAX_FILE_BYTES + 1)]:
        with pytest.raises(StatementError):
            parse_statement(content, ImportOptions())
    with pytest.raises(StatementError):
        parse_statement(b"Date,Description,Amount\n2026-04-02,FIGMA,10", ImportOptions(currency="JPY"))
    from statement_categorizer import parser

    monkeypatch.setattr(parser, "MAX_ROWS", 1)
    with pytest.raises(StatementError, match="at most"):
        parse_statement(b"Date,Description,Amount\n2026-04-02,FIGMA,10\n2026-04-03,FIGMA,10", ImportOptions())
