import csv
import io

import pytest


def upload(client, content, filename="statement.csv"):
    if isinstance(content, str):
        content = content.encode()
    return client.post("/api/statements", files={"file": (filename, content, "text/csv")})


def upload_sample(client, sample_dir, name):
    return upload(client, (sample_dir / f"{name}.csv").read_bytes(), f"{name}.csv")


def by_desc(statement, description):
    return next(t for t in statement["transactions"] if t["description"] == description)


# ---------------------------------------------------------------- basics


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_categories(client):
    categories = client.get("/api/categories").json()
    assert categories[0] == "Software & Subscriptions"
    assert categories[-1] == "Needs Review"
    assert len(categories) == 13


# ---------------------------------------------------------------- upload


def test_upload_returns_categorized_rows(client, sample_dir):
    response = upload_sample(client, sample_dir, "bank_a")
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "bank_a.csv"
    assert body["row_count"] == 40 == len(body["transactions"])
    adobe = by_desc(body, "ADOBE CREATIVE CLOUD")
    assert adobe["category"] == "Software & Subscriptions"
    assert adobe["status"] == "auto"
    assert adobe["source"] == "rule"
    assert adobe["date"] == "2026-05-01"
    assert set(adobe) >= {
        "id",
        "normalized_merchant",
        "amount",
        "currency",
        "confidence",
        "reason",
        "needs_review",
        "is_duplicate",
        "notes",
    }


def test_upload_messy_reports_warnings_and_statuses(client, sample_dir):
    body = upload_sample(client, sample_dir, "messy").json()
    assert "Row 12 skipped: amount is missing" in body["warnings"]
    statuses = {t["row_number"]: t["status"] for t in body["transactions"]}
    assert statuses[10] == "duplicate"
    assert statuses[6] == "needs_review"  # SQ *JOES CAFE
    assert statuses[15] == "not_spending"  # transfer
    hotel = by_desc(body, "HOTEL LISBOA EUR 120.00")
    assert hotel["notes"] == ["Foreign currency: original charge 120.00 EUR"]


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("statement.pdf", b"%PDF-1.4", "Only .csv files are supported"),
        ("statement.csv", b"", "The file is empty"),
        ("statement.csv", b"Date,Description,Amount\n", "No transactions found in the file"),
        ("statement.csv", b"Foo,Bar\n1,2\n", "Could not find a date column"),
        ("statement.csv", b"\x00\x01\x02binary", "does not look like a text CSV"),
    ],
)
def test_bad_uploads_give_clear_400(client, filename, content, message):
    response = upload(client, content, filename)
    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_upload_too_large(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0.0001")  # ~100 bytes
    response = upload(client, "Date,Description,Amount\n" + "2026-05-01,ADOBE,-1\n" * 20)
    assert response.status_code == 400
    assert "larger than" in response.json()["detail"]


def test_upload_without_file_is_422(client):
    assert client.post("/api/statements").status_code == 422


def test_sample_endpoint(client):
    response = client.post("/api/statements/sample", params={"name": "bank_b"})
    assert response.status_code == 201
    assert response.json()["filename"] == "bank_b.csv"
    assert client.post("/api/statements/sample", params={"name": "../etc"}).status_code == 400


# ---------------------------------------------------------------- read


def test_get_and_list_statements(client, sample_dir):
    first = upload_sample(client, sample_dir, "bank_a").json()
    second = upload_sample(client, sample_dir, "bank_b").json()
    assert client.get(f"/api/statements/{first['id']}").json() == first
    listing = client.get("/api/statements").json()
    assert [s["id"] for s in listing] == [second["id"], first["id"]]
    assert listing[1]["needs_review_count"] == sum(t["needs_review"] for t in first["transactions"])


def test_unknown_statement_is_404(client):
    assert client.get("/api/statements/999").status_code == 404
    assert client.get("/api/statements/999/summary").status_code == 404
    assert client.get("/api/statements/999/export").status_code == 404


# ---------------------------------------------------------------- summary


def test_summary_totals(client):
    statement = upload(
        client,
        "Date,Description,Amount\n"
        "2026-05-01,ADOBE CREATIVE CLOUD,-50.00\n"
        "2026-05-02,FIGMA,-15.00\n"
        "2026-05-03,AMAZON REFUND,30.00\n"
        "2026-05-04,TRANSFER TO SAVINGS,-500.00\n"
        "2026-05-05,PAYMENT THANK YOU,800.00\n"
        "2026-05-06,UPWORK PAYOUT,1000.00\n"
        "2026-05-07,JOES CAFE 9921,-12.50\n"
        "2026-05-08,LATE FEE,-25.00\n",
    ).json()
    summary = client.get(f"/api/statements/{statement['id']}/summary").json()
    totals = summary["totals"]
    assert totals["transactions"] == 8
    assert totals["needs_review"] == 1
    assert totals["auto_categorized"] == 7
    assert totals["spending"] == 90.0  # 50 + 15 + 25; transfer and card payment excluded
    assert totals["refunds"] == 30.0
    assert totals["net_spending"] == 60.0  # refund reduces spending, is not income
    assert totals["income"] == 1000.0
    assert totals["not_spending"] == 1300.0
    cats = {c["category"]: c for c in summary["categories"]}
    assert cats["Software & Subscriptions"] == {
        "category": "Software & Subscriptions",
        "kind": "spending",
        "total": 65.0,
        "count": 2,
    }
    assert cats["Refund"]["kind"] == "refund"
    assert cats["Needs Review"]["kind"] == "review"
    assert summary["categories"][0]["category"] == "Software & Subscriptions"  # biggest spend first


# ---------------------------------------------------------------- fixing + learning


def test_patch_category_saves_and_learns(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    joes = by_desc(statement, "JOES CAFE 9921")
    assert joes["category"] == "Needs Review"

    response = client.patch(f"/api/transactions/{joes['id']}", json={"category": "Meals"})
    assert response.status_code == 200
    body = response.json()
    assert body["transaction"]["category"] == "Meals"
    assert body["transaction"]["source"] == "user"
    assert body["transaction"]["status"] == "user"
    assert body["transaction"]["needs_review"] is False
    assert body["learned_rule"]["merchant"] == "JOES CAFE"

    saved = by_desc(client.get(f"/api/statements/{statement['id']}").json(), "JOES CAFE 9921")
    assert saved["category"] == "Meals"

    # Next upload: a differently formatted JOES CAFE row is categorized automatically.
    second = upload_sample(client, sample_dir, "bank_b").json()
    joes_again = by_desc(second, "SQ *JOES CAFE")
    assert joes_again["category"] == "Meals"
    assert joes_again["source"] == "learned"
    assert joes_again["status"] == "learned"
    assert joes_again["confidence"] == 1.0

    rules = client.get("/api/rules/learned").json()
    assert rules[0]["merchant"] == "JOES CAFE"
    assert rules[0]["times_applied"] == 1


def test_patch_applies_to_same_merchant_rows_in_statement(client):
    statement = upload(
        client,
        "Date,Description,Amount\n"
        "2026-05-01,BLUE DOOR STUDIO,-140.00\n"
        "2026-05-09,SQ *BLUE DOOR STUDIO 2231,-60.00\n"
        "2026-05-10,ADOBE,-10.00\n",
    ).json()
    first, second, _ = statement["transactions"]
    body = client.patch(
        f"/api/transactions/{first['id']}", json={"category": "Office Supplies"}
    ).json()
    assert body["also_updated"] == [second["id"]]
    refreshed = client.get(f"/api/statements/{statement['id']}").json()["transactions"]
    assert refreshed[1]["category"] == "Office Supplies"
    assert refreshed[1]["source"] == "learned"


def test_patch_to_needs_review_does_not_learn(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    adobe = by_desc(statement, "ADOBE CREATIVE CLOUD")
    body = client.patch(f"/api/transactions/{adobe['id']}", json={"category": "Needs Review"})
    assert body.json()["learned_rule"] is None
    assert body.json()["transaction"]["needs_review"] is True
    assert client.get("/api/rules/learned").json() == []


def test_relearning_updates_existing_rule(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    joes = by_desc(statement, "JOES CAFE 9921")
    client.patch(f"/api/transactions/{joes['id']}", json={"category": "Meals"})
    client.patch(f"/api/transactions/{joes['id']}", json={"category": "Personal"})
    rules = client.get("/api/rules/learned").json()
    assert len(rules) == 1 and rules[0]["category"] == "Personal"


def test_patch_errors(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    txn_id = statement["transactions"][0]["id"]
    assert (
        client.patch(f"/api/transactions/{txn_id}", json={"category": "Snacks"}).status_code == 422
    )
    assert client.patch(f"/api/transactions/{txn_id}", json={}).status_code == 422
    assert client.patch("/api/transactions/99999", json={"category": "Meals"}).status_code == 404


def test_fixing_duplicate_clears_flag(client, sample_dir):
    statement = upload_sample(client, sample_dir, "messy").json()
    dup = next(t for t in statement["transactions"] if t["is_duplicate"])
    body = client.patch(
        f"/api/transactions/{dup['id']}", json={"category": "Office Supplies"}
    ).json()
    assert body["transaction"]["is_duplicate"] is False
    assert body["transaction"]["status"] == "user"


def test_delete_learned_rule(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    joes = by_desc(statement, "JOES CAFE 9921")
    rule = client.patch(f"/api/transactions/{joes['id']}", json={"category": "Meals"}).json()[
        "learned_rule"
    ]
    assert client.delete(f"/api/rules/learned/{rule['id']}").status_code == 204
    assert client.get("/api/rules/learned").json() == []
    assert client.delete(f"/api/rules/learned/{rule['id']}").status_code == 404
    again = upload_sample(client, sample_dir, "bank_a").json()
    assert by_desc(again, "JOES CAFE 9921")["category"] == "Needs Review"


# ---------------------------------------------------------------- export


def test_export_csv(client, sample_dir):
    statement = upload_sample(client, sample_dir, "bank_a").json()
    response = client.get(f"/api/statements/{statement['id']}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="categorized_bank_a.csv"' in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 40
    assert rows[0]["category"] == "Software & Subscriptions"
    assert rows[0]["amount"] == "-54.99"
    assert rows[0]["merchant"] == "ADOBE CREATIVE CLOUD"


def test_cors_allows_frontend(client):
    response = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
