
import io

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_csv_is_categorized():
    content = (
        "date,description,amount\n"
        "2026-09-01,CLOUDHOST MONTHLY,-24.99\n"
        "2026-09-02,SUPPLIER REFUND,22.00\n"
        "2026-09-03,UNKNOWN MERCHANT,-10.00\n"
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "sample.csv",
                io.BytesIO(content.encode("utf-8")),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["transaction_count"] == 3
    assert data["transactions"][0]["category"] == "Software"
    assert data["transactions"][1]["category"] == "Refund"
    assert data["transactions"][2]["category"] == "Needs Review"


def test_rejects_non_csv_file():
    response = client.post(
        "/categorize",
        files={
            "file": (
                "statement.txt",
                b"not a csv file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_rejects_missing_required_columns():
    content = "date,description\n2026-09-01,CLOUDHOST MONTHLY\n"

    response = client.post(
        "/categorize",
        files={
            "file": (
                "missing_columns.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400


def test_rejects_empty_csv():
    response = client.post(
        "/categorize",
        files={
            "file": ("empty.csv", b"", "text/csv")
        },
    )

    assert response.status_code == 400


def test_rejects_invalid_amount():
    content = "date,description,amount\n2026-09-01,CLOUDHOST,abc\n"

    response = client.post(
        "/categorize",
        files={
            "file": (
                "invalid_amount.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400


def test_rejects_missing_date():
    content = "date,description,amount\n,CLOUDHOST,-10.00\n"

    response = client.post(
        "/categorize",
        files={
            "file": (
                "missing_date.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400


def test_rejects_non_finite_amount():
    content = "date,description,amount\n2026-09-01,CLOUDHOST,nan\n"

    response = client.post(
        "/categorize",
        files={
            "file": (
                "non_finite.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400


def test_rejects_oversized_file():
    content = (
        b"date,description,amount\n"
        + b"2026-09-01,TEST,-1.00\n" * 100_000
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "large.csv",
                content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 413


def test_ignores_blank_rows():
    content = (
        "date,description,amount\n"
        "2026-09-01,CLOUDHOST,-24.99\n"
        "\n"
        "2026-09-02,SHIPPING LABEL,-12.00\n"
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "blank_rows.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["transaction_count"] == 2


def test_rejects_csv_with_headers_but_no_transactions():
    content = "date,description,amount\n"

    response = client.post(
        "/categorize",
        files={
            "file": (
                "headers_only.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "No transactions were found in the CSV file."
    )

def test_rejects_duplicate_headers():
    content = (
        "date,description,amount,amount\n"
        "2026-09-01,CLOUDHOST,-24.99,-30.00\n"
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "duplicate_headers.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "CSV contains duplicate column headers."
    )

def test_rejects_invalid_date():
    content = (
        "date,description,amount\n"
        "not-a-date,CLOUDHOST,-24.99\n"
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "invalid_date.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid date on CSV row 2. Use YYYY-MM-DD format."
    )


def test_rejects_impossible_date():
    content = (
        "date,description,amount\n"
        "2026-02-30,CLOUDHOST,-24.99\n"
    )

    response = client.post(
        "/categorize",
        files={
            "file": (
                "impossible_date.csv",
                content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid date on CSV row 2. Use YYYY-MM-DD format."
    )
