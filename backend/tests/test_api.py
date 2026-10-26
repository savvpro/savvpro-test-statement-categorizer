import io
from fastapi import HTTPException
import pytest

from app.main import (
    app,
    get_sample_data,
    get_categories,
    recalculate,
    process_statement_bytes,
    RecalculateRequest,
    TransactionRow,
)


def test_get_categories():
    res = get_categories()
    assert "categories" in res
    assert "Software & Subscriptions" in res["categories"]
    assert "Needs Review" in res["categories"]


def test_get_sample_data():
    res = get_sample_data()
    assert res["filename"] == "sample_statement.csv"
    assert res["total_transactions"] > 0
    assert "gross_expenses" in res
    assert len(res["transactions"]) == res["total_transactions"]


def test_recalculate_metrics():
    rows = [
        TransactionRow(
            id=1,
            date="2026-10-01",
            description="ADOBE",
            amount="-29.99",
            category="Software & Subscriptions",
            confidence="high",
            reason="Verified rule",
            transaction_type="expense",
            include_in_expenses=True,
            is_tax_deductible=True,
        ),
        TransactionRow(
            id=2,
            date="2026-10-02",
            description="JOES CAFE",
            amount="-15.00",
            category="Meals (50% Deductible)",
            confidence="high",
            reason="User confirmed client meal",
            transaction_type="expense",
            include_in_expenses=True,
            is_tax_deductible=True,
        ),
    ]
    req = RecalculateRequest(transactions=rows)
    result = recalculate(req)
    assert result["total_transactions"] == 2
    assert result["needs_review_count"] == 0
    assert result["gross_expenses"] == "44.99"


def test_process_statement_bytes():
    csv_content = (
        "date,description,amount\n"
        "2026-10-01,ADOBE CREATIVE CLOUD,-29.99\n"
        "2026-10-02,TRANSFER TO SAVINGS,-100.00\n"
        "2026-10-03,UNKNOWN SHOP,-12.50\n"
    ).encode("utf-8")

    result = process_statement_bytes(csv_content, "test.csv")
    assert result["total_transactions"] == 3
    assert result["needs_review_count"] == 1
    assert result["transactions"][0]["category"] == "Software & Subscriptions"
    assert result["transactions"][1]["category"] == "Transfer"
    assert result["transactions"][2]["category"] == "Needs Review"


def test_process_statement_bytes_with_debit_credit():
    csv_content = (
        "Transaction Date,Merchant,Debit,Credit\n"
        "2026-10-01,FIGMA PRO,15.00,\n"
        "2026-10-02,CLIENT PAYMENT,,1200.00\n"
    ).encode("utf-8")

    result = process_statement_bytes(csv_content, "bank_export.csv")
    assert result["total_transactions"] == 2
    assert result["transactions"][0]["category"] == "Software & Subscriptions"
    assert result["transactions"][0]["amount"] == "-15.00"
    assert result["transactions"][1]["category"] == "Client Revenue"
    assert result["transactions"][1]["amount"] == "1200.00"


def test_process_statement_bytes_empty_raises():
    with pytest.raises(HTTPException) as exc:
        process_statement_bytes(b"", "empty.csv")
    assert exc.value.status_code == 400


def test_process_statement_bytes_no_valid_headers():
    csv_content = b"foo,bar,baz\n1,2,3"
    with pytest.raises(HTTPException) as exc:
        process_statement_bytes(csv_content, "invalid.csv")
    assert exc.value.status_code == 400
