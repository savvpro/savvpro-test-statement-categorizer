from decimal import Decimal
from pathlib import Path

import pytest
from app.csv_parser import MAX_FILE_BYTES, CSVValidationError, parse_csv


def test_signed_format_bom_headers_and_whitespace():
    rows = parse_csv(
        "\ufeff Transaction Date , Transaction Description , Transaction Amount \n2026-09-01, GITHUB COPILOT , -19.00 \n02/09/2026,CLIENT PAYMENT NORTHSTAR,2000\n03.09.2026,Verification,0\n".encode()
    )
    assert [(row.date, row.description, row.amount) for row in rows] == [
        ("2026-09-01", "GITHUB COPILOT", Decimal("-19.00")),
        ("2026-09-02", "CLIENT PAYMENT NORTHSTAR", Decimal("2000.00")),
        ("2026-09-03", "Verification", Decimal("0.00")),
    ]


def test_debit_credit_direction_and_zero():
    rows = parse_csv(
        b"Date,Description,Debit,Credit\n2026-09-01,AWS BILLING,20,\n2026-09-02,CLIENT PAYMENT,,500\n2026-09-03,Verification,0,0\n"
    )
    assert [row.amount for row in rows] == [
        Decimal("-20"),
        Decimal("500"),
        Decimal("0"),
    ]


@pytest.mark.parametrize(
    "content, message",
    [
        (b"", "empty"),
        (b"Date,Description,Amount\n", "at least one"),
        (b"Date;Description;Amount\n2026-09-01;AWS;20", "comma-separated"),
        (b"Date,Amount\n2026-09-01,-20", "Description"),
        (b"Date,Description,Debit\n2026-09-01,AWS,20", "both Debit and Credit"),
        (b"Date,Description,Amount,Credit\n2026-09-01,AWS,-20,20", "not both"),
        (b"Date,Description,Amount,amount\n2026-09-01,AWS,-20,-20", "unique"),
        (
            b"Date,Booking Date,Description,Amount\n2026-09-01,2026-09-01,AWS,-20",
            "More than one",
        ),
        (b"Date,Description,Amount\n2026-02-30,AWS,-20", "Row 2: date"),
        (b"Date,Description,Amount\n09/30/2026,AWS,-20", "date must"),
        (b"Date,Description,Amount\n2026-09-01,,20", "description must"),
        (b"Date,Description,Amount\n2026-09-01,AWS,20,extra", "column count"),
        (b"Date,Description,Amount\n\n", "column count"),
        (b'Date,Description,Amount\n2026-09-01,"AWS,20', "Malformed CSV"),
        (
            b"Date,Description,Amount,Currency\n2026-09-01,AWS,-20,USD",
            "currency must be PKR",
        ),
        (b"\xff", "UTF-8"),
        (b"Date,Description,Amount\n2026-09-01,AWS\x00,-20", "null characters"),
    ],
)
def test_invalid_formats_are_explained(content, message):
    with pytest.raises(CSVValidationError, match=message):
        parse_csv(content)


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "1e3", "19.999", "PKR 20", "1,200.00", "", "10000000000"],
)
def test_invalid_monetary_values(value):
    content = f'Date,Description,Amount\n2026-09-01,AWS BILLING,"{value}"\n'
    with pytest.raises(CSVValidationError, match="Row 2: amounts must"):
        parse_csv(content.encode())


@pytest.mark.parametrize(
    "debit, credit", [("-20", ""), ("", "-20"), ("20", "30"), ("", "")]
)
def test_ambiguous_debit_credit_is_rejected(debit, credit):
    with pytest.raises(CSVValidationError):
        parse_csv(
            f"Date,Description,Debit,Credit\n2026-09-01,AWS,{debit},{credit}\n".encode()
        )


def test_duplicates_are_flagged_and_retained():
    rows = parse_csv(
        b"Date,Description,Amount\n2026-09-01,VERCEL,-20\n2026-09-01,vercel,-20\n2026-09-02,VERCEL,-20\n"
    )
    assert len(rows) == 3
    assert [row.possible_duplicate for row in rows] == [True, True, False]


def test_size_and_row_limits():
    with pytest.raises(CSVValidationError, match="1 MiB"):
        parse_csv(b"x" * (MAX_FILE_BYTES + 1))
    content = b"Date,Description,Amount\n" + b"2026-09-01,VERCEL,-20\n" * 5000
    assert len(parse_csv(content)) == 5000
    with pytest.raises(CSVValidationError, match="5,000"):
        parse_csv(content + b"2026-09-01,VERCEL,-20\n")


def test_both_fictional_samples_parse():
    samples = Path(__file__).resolve().parents[2] / "samples"
    assert len(parse_csv((samples / "developer-signed.csv").read_bytes())) == 18
    assert len(parse_csv((samples / "developer-debit-credit.csv").read_bytes())) == 12


@pytest.mark.parametrize("currency", ["PKR", "pkr", " PKR "])
def test_explicit_pkr_is_accepted(currency):
    rows = parse_csv(
        f"Date,Description,Amount,Currency\n2026-09-01,VERCEL,-5600,{currency}\n".encode()
    )
    assert rows[0].amount == Decimal("-5600.00")


@pytest.mark.parametrize("currency", ["EUR", "USD", "", "Rs"])
def test_other_or_ambiguous_currency_is_rejected(currency):
    with pytest.raises(CSVValidationError, match="currency must be PKR"):
        parse_csv(
            f"Date,Description,Amount,Currency\n2026-09-01,VERCEL,-5600,{currency}\n".encode()
        )
