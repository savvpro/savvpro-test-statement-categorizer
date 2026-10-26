
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_valid_csv():
    csv_content = (
        "description,amount\n"
        "GitHub subscription,-10.00\n"
        "Unknown merchant 123,-42.00\n"
    )

    response = client.post(
        "/api/transactions/upload",
        files={
            "file": (
                "sample.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["transaction_count"] == 2
    assert data["transactions"][0]["category"] == "Software & Subscriptions"
    assert data["transactions"][1]["category"] == "Needs Review"


def test_upload_rejects_non_csv_file():
    response = client.post(
        "/api/transactions/upload",
        files={
            "file": (
                "notes.txt",
                b"some text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_upload_rejects_missing_columns():
    response = client.post(
        "/api/transactions/upload",
        files={
            "file": (
                "invalid.csv",
                b"merchant,total\nGitHub,10\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
