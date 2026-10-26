import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from backend.app.parsers import ImportProblem, extract, money, parse_rows

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"
OPTIONS = {
    "account": "Test card",
    "account_type": "credit_card",
    "currency": "PKR",
    "date_order": "day_first",
    "amount_direction": "out_positive",
    "mapping": {"date": "Date", "description": "Description", "amount": "Amount", "currency": "Currency"},
}


def post_file(client, endpoint, content, options=OPTIONS, name="statement.csv"):
    return client.post(endpoint, files={"file": (name, content)}, data={"options": json.dumps(options)})


@pytest.mark.parametrize(
    "value,expected", [("1,234.56", 123456), ("(500.00)", -50000), ("PKR 9.99", 999), ("-20", -2000)]
)
def test_exact_money(value, expected):
    assert money(value) == expected


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1.001", "20 CR", "not money"])
def test_invalid_money(value):
    with pytest.raises(ImportProblem):
        money(value)


def test_invalid_rows_block_whole_import(client):
    content = (SAMPLES / "invalid-rows.csv").read_bytes()
    preview = post_file(client, "/api/imports/preview", content).json()
    assert preview["source_count"] == 5
    assert preview["valid_count"] == 1
    assert [error["row"] for error in preview["errors"]] == [3, 4, 5, 6]
    assert post_file(client, "/api/imports", content).status_code == 422
    assert client.get("/api/workspace").json()["transactions"] == []


def test_signed_amount_direction_and_day_first():
    extracted = extract("test.csv", b"Date,Description,Amount,Currency\n03/09/2026,NETFLIX,-1100,PKR\n")
    rows, errors = parse_rows(extracted, OPTIONS | {"amount_direction": "in_positive"})
    assert not errors
    assert rows[0]["amount_minor"] == 110000
    assert rows[0]["date"] == "2026-09-03"


def test_duplicate_upload_and_overlap_are_distinct(client):
    content = b"Date,Description,Amount,Currency\n2026-09-01,NETFLIX,1100,PKR\n"
    assert post_file(client, "/api/imports", content).status_code == 201
    assert post_file(client, "/api/imports", content).status_code == 409
    overlap = content + b"2026-09-02,SPOTIFY,349,PKR\n"
    assert post_file(client, "/api/imports", overlap).status_code == 201
    rows = client.get("/api/workspace").json()["transactions"]
    assert len(rows) == 3
    assert sum(row["possible_duplicate"] for row in rows) == 1


def test_debit_credit_ambiguity_and_ragged_rows():
    data = extract("x.csv", b"Date,Description,Debit,Credit\n2026-09-01,ABC,5,6\n2026-09-02,XYZ,2\n")
    options = OPTIONS | {
        "mapping": {"date": "Date", "description": "Description", "debit": "Debit", "credit": "Credit"}
    }
    rows, errors = parse_rows(data, options)
    assert not rows
    assert len(errors) == 2


def test_xlsx_and_pdf_samples():
    for filename in ["developer-statement.xlsx", "developer-statement.pdf"]:
        extracted = extract(filename, (SAMPLES / filename).read_bytes())
        assert extracted["row_count"] == 12
        rows, errors = parse_rows(extracted, OPTIONS | {"mapping": extracted["mapping"]})
        assert not errors
        assert len(rows) == 12


def test_multisheet_rejected():
    book = Workbook()
    book.create_sheet("Other")
    stream = io.BytesIO()
    book.save(stream)
    with pytest.raises(ImportProblem, match="one statement sheet"):
        extract("x.xlsx", stream.getvalue())


def test_empty_bad_extension_and_duplicate_headers():
    for filename, data in [("x.csv", b""), ("x.exe", b"example"), ("x.csv", b"Date,Date\na,b\n")]:
        with pytest.raises(ImportProblem):
            extract(filename, data)
