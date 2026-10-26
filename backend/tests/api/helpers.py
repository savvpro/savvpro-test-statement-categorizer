from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
ACCOUNTS = {
    "checking_simple.csv": "checking",
    "credit_card.csv": "credit_card",
    "bank_messy.csv": "checking",
    "credit_card.xlsx": "credit_card",
}


def upload_bytes(
    client: TestClient, name: str, content: bytes, account_type: str = "checking", **data: str
) -> Any:
    return client.post(
        "/api/statements",
        files={"file": (name, content)},
        data={"account_type": account_type, **data},
    )


def upload_sample(client: TestClient, name: str) -> dict[str, Any]:
    response = upload_bytes(client, name, (SAMPLES / name).read_bytes(), ACCOUNTS[name])
    assert response.status_code == 201, response.text
    return response.json()


def by_description(statement: dict[str, Any], text: str) -> list[dict[str, Any]]:
    return [t for t in statement["transactions"] if t["description_raw"].startswith(text)]
