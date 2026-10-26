"""
Tests for CSV parser.
"""

import pytest

from app.parsers import parse_csv


SAMPLE_CSV = """Date,Description,Amount
2025-01-02,ADOBE CREATIVE CLOUD,-54.99
2025-01-03,UBER *TRIP,-18.50
2025-01-04,STRIPE PAYOUT,1250.00
2025-01-05,JOES CAFE 9921,-12.40
"""


def test_parse_basic_csv():
    txs = parse_csv(SAMPLE_CSV)
    assert len(txs) == 4
    assert txs[0]["description"] == "ADOBE CREATIVE CLOUD"
    assert txs[0]["amount"] == -54.99
    assert txs[2]["amount"] == 1250.00


def test_parse_with_different_headers():
    csv_content = """Transaction Date,Memo,Value
01/02/2025,GITHUB.COM,-4.00
"""
    txs = parse_csv(csv_content)
    assert len(txs) == 1
    assert txs[0]["description"] == "GITHUB.COM"
    assert txs[0]["amount"] == -4.00


def test_missing_columns_raises():
    bad = """Foo,Bar
1,2
"""
    with pytest.raises(ValueError, match="Could not detect required columns"):
        parse_csv(bad)
