from decimal import Decimal

import pytest

from app.ingest.amounts import AmountError, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.99", "12.99"),
        ("-12.99", "-12.99"),
        ("+12.99", "12.99"),
        ("  -59.99  ", "-59.99"),
        ("0", "0"),
        ("0.00", "0.00"),
        (".5", "0.5"),
        ("500", "500"),
        # thousands separators
        ("1,250.00", "1250.00"),
        ("185,000.00", "185000.00"),
        ("-1,234,567.89", "-1234567.89"),
        # parentheses mean negative
        ("(45.00)", "-45.00"),
        ("( 45.00 )", "-45.00"),
        ("(1,250.00)", "-1250.00"),
        # currency symbols and codes
        ("Rs 500", "500"),
        ("Rs. 500", "500"),
        ("Rs500", "500"),
        ("rs 500", "500"),
        ("PKR 1,250.00", "1250.00"),
        ("1,250.00 PKR", "1250.00"),
        ("USD 12.99", "12.99"),
        ("$12.99", "12.99"),
        ("-$12.99", "-12.99"),
        ("$-12.99", "-12.99"),
        ("($12.99)", "-12.99"),
        ("-Rs 500", "-500"),
        (" -12.99", "-12.99"),
    ],
)
def test_parse_amount_valid(text: str, expected: str) -> None:
    result = parse_amount(text)
    assert isinstance(result, Decimal)
    assert result == Decimal(expected)
    assert result.as_tuple() == Decimal(expected).as_tuple()  # exact digits, no float noise


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "$",
        "Rs",
        "abc",
        "12.99abc",
        "NaN",
        "Infinity",
        "1e5",
        "--5",
        "(-45.00)",
        "-(45.00)",
        "()",
        "(45.00",
        "45.00)",
        "1,23.00",
        "1,2345.00",
        ",500",
        "500,",
        "1.234,56",
        "1 234.56",
        "1 234.56x",
        "1rs2",
        "5 USD 5",
        "Rs 5 0",
        "Rs 5 Rs",
        "Rs$5",
        "+(5)",
        "(5)-",
        "((5))",
        "12.99.1",
        "-",
        "+",
    ],
)
def test_parse_amount_invalid(text: str) -> None:
    with pytest.raises(AmountError):
        parse_amount(text)
