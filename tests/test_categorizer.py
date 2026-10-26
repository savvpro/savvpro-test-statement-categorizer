import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from main import categorize, parse_statement, summarize

def test_known_software_is_categorized():
    assert categorize("ADOBE CREATIVE CLOUD", -59.99)[0] == "Software"

def test_unknown_merchant_needs_review():
    assert categorize("JOES CAFE 9921", -18.75)[0] == "Meals"  # Dining is a known merchant class.

def test_unknown_business_is_review():
    assert categorize("MYSTERY VENDOR 999", -21.00)[0] == "Needs Review"

def test_transfer_is_not_expense():
    rows = [{"amount": -300, "category": "Transfer"}]
    assert summarize(rows)["expenses"] == 0

def test_refund_not_income():
    rows = [{"amount": 32.49, "category": "Refund"}]
    result = summarize(rows)
    assert result["income"] == 0
    assert result["refunds"] == 32.49

def test_csv_parsing_and_review_fallback():
    data = b"Date,Description,Amount\n2026-10-01,ADOBE CREATIVE CLOUD,-59.99\n2026-10-02,MYSTERY VENDOR,-10.00\n"
    tx = parse_statement(data, "sample.csv")
    assert len(tx) == 2
    assert tx[1]["category"] == "Needs Review"
