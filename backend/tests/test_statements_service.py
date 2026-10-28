from datetime import date
from decimal import Decimal

from app.ingest.parsing import RawTransaction, parse_csv
from app.services.statements import categorize_statement, summarize


def raw(row, desc, amount, pending=False):
    return RawTransaction(row, date(2026, 9, 10), desc, Decimal(amount), pending)


def test_duplicate_charge_goes_to_review():
    items = categorize_statement([raw(1, "T-MOBILE AUTOPAY", "-85"), raw(2, "T-MOBILE AUTOPAY", "-85")], {})
    assert items[0]["category"] == "Phone & Data"
    assert items[1]["category"] == "Needs Review"
    assert "duplicate" in items[1]["reason"]
    assert items[1]["suggestion"] == "Phone & Data"


def test_pending_charge_goes_to_review():
    item = categorize_statement([raw(1, "CHEVRON 0091142", "-44", pending=True)], {})[0]
    assert item["category"] == "Needs Review"
    assert "Pending" in item["reason"]


def test_refund_nets_against_the_purchase_category():
    items = categorize_statement([raw(1, "AUTOZONE #4410", "-62.15"), raw(2, "AUTOZONE #4410 REFUND", "24.99")], {})
    assert items[1]["refund_of"] == "Vehicle Maintenance"
    totals = {c["category"]: c["total"] for c in summarize(items)["by_category"]}
    assert totals["Vehicle Maintenance"] == "37.16"


def test_summary_on_the_bank_sample(sample):
    items = categorize_statement(parse_csv(sample("checking_bank_style.csv")).transactions, {})
    s = summarize(items)
    assert s["income"] == "2047.25"  # payouts + bonus, not the unknown deposit or the refund
    assert s["not_spending"] == "500.00"
    assert s["needs_review"] == 5
