from fastapi.testclient import TestClient

from tests.api.helpers import by_description, upload_bytes, upload_sample


def patch(client: TestClient, txn_id: int, category_id: str, remember: bool = False):  # type: ignore[no-untyped-def]
    return client.patch(
        f"/api/transactions/{txn_id}", json={"category_id": category_id, "remember": remember}
    )


def test_patch_without_remember_changes_only_that_row(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    first, second, _dupe = by_description(body, "SQ *JOES CAFE")
    response = patch(client, first["id"], "meals")
    assert response.status_code == 200
    out = response.json()
    assert out["updated_count"] == 0
    assert out["transaction"]["category_id"] == "meals"
    assert out["transaction"]["status"] == "user_confirmed"
    assert out["transaction"]["reasons"] == ["set by user"]

    rows = client.get(f"/api/statements/{body['id']}/transactions").json()
    still = next(t for t in rows if t["id"] == second["id"])
    assert still["status"] == "needs_review"
    assert client.get("/api/rules").json() == []


def test_patch_with_remember_flips_other_rows_and_applies_to_new_uploads(
    client: TestClient,
) -> None:
    card = upload_sample(client, "credit_card.csv")
    first, second, dupe = by_description(card, "SQ *JOES CAFE")

    out = patch(client, first["id"], "meals", remember=True).json()
    assert out["updated_count"] == 1

    rows = {t["id"]: t for t in client.get(f"/api/statements/{card['id']}/transactions").json()}
    assert rows[second["id"]]["status"] == "auto"
    assert rows[second["id"]]["category_id"] == "meals"
    assert rows[second["id"]]["rule_id"] == "user:JOES CAFE"
    # The same-day repeat is still a possible duplicate: a rule never hides that.
    assert rows[dupe["id"]]["status"] == "needs_review"
    assert "possible_duplicate" in rows[dupe["id"]]["flags"]

    rules = client.get("/api/rules").json()
    assert [(r["merchant_key"], r["category_id"]) for r in rules] == [("JOES CAFE", "meals")]

    later = upload_bytes(
        client,
        "april.csv",
        b"Date,Description,Amount\n04/02/2026,SQ *JOES CAFE 7781,12.30\n",
        "credit_card",
    ).json()
    (txn,) = later["transactions"]
    assert (txn["status"], txn["category_id"], txn["rule_id"]) == (
        "auto",
        "meals",
        "user:JOES CAFE",
    )
    assert client.get("/api/rules").json()[0]["hits"] == 2


def test_remember_reaches_other_statements_but_not_confirmed_rows(client: TestClient) -> None:
    csv_ = upload_sample(client, "credit_card.csv")
    xlsx = upload_sample(client, "credit_card.xlsx")
    (_, other_csv, _) = by_description(csv_, "SQ *JOES CAFE")
    xlsx_rows = by_description(xlsx, "SQ *JOES CAFE")
    assert xlsx_rows
    patch(client, other_csv["id"], "personal")  # confirmed by hand first

    first = by_description(csv_, "SQ *JOES CAFE")[0]
    out = patch(client, first["id"], "meals", remember=True).json()
    assert out["updated_count"] >= len([t for t in xlsx_rows if t["status"] == "needs_review"]) - 1

    rows = client.get(f"/api/statements/{csv_['id']}/transactions").json()
    assert next(t for t in rows if t["id"] == other_csv["id"])["category_id"] == "personal"
    xlsx_after = client.get(f"/api/statements/{xlsx['id']}/transactions").json()
    assert any(t["rule_id"] == "user:JOES CAFE" for t in xlsx_after)


def test_invalid_category_is_422(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    txn_id = body["transactions"][0]["id"]
    for bad in ("not_a_category", "needs_review"):
        response = patch(client, txn_id, bad)
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_category"
    assert client.patch(f"/api/transactions/{txn_id}", json={}).status_code == 422
    assert patch(client, 999_999, "meals").status_code == 404


def test_rules_list_and_delete(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    cafe = by_description(body, "SQ *JOES CAFE")[0]
    patch(client, cafe["id"], "meals", remember=True)
    (rule,) = client.get("/api/rules").json()

    assert client.delete(f"/api/rules/{rule['id']}").status_code == 204
    assert client.get("/api/rules").json() == []
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 404

    # Forgotten: a new upload of the merchant goes back to review.
    later = upload_bytes(
        client,
        "may.csv",
        b"Date,Description,Amount\n05/02/2026,SQ *JOES CAFE,9.00\n",
        "credit_card",
    ).json()
    assert later["transactions"][0]["status"] == "needs_review"
