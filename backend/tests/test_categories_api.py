from fastapi.testclient import TestClient

from app.brain.taxonomy import all_categories


def test_list_categories(client: TestClient) -> None:
    response = client.get("/api/categories")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body] == [c.id for c in all_categories()]

    meals = next(c for c in body if c["id"] == "meals")
    assert meals == {
        "id": "meals",
        "label": "Business Meals",
        "kind": "expense",
        "schedule_c_line": "Line 24b - Deductible meals",
        "deductible_pct": 50,
        "description": "Meals with clients or while travelling for work (50% deductible).",
    }


def test_needs_review_is_listed(client: TestClient) -> None:
    ids = {c["id"] for c in client.get("/api/categories").json()}

    assert "needs_review" in ids
