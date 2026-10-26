from tests.conftest import SAMPLES, csv_bytes


def upload(client, data: bytes, name="statement.csv", **form):
    return client.post("/api/statements", files={"file": (name, data, "text/csv")}, data=form)


def test_health_and_categories(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    ids = [c["id"] for c in client.get("/api/categories").json()]
    assert "fuel" in ids and "platform_income" in ids


def test_upload_review_export_flow(client):
    res = upload(client, (SAMPLES / "gig_driver_checking.csv").read_bytes())
    assert res.status_code == 201
    statement = res.json()
    assert statement["transaction_count"] == 41
    assert statement["summary"]["needs_review_count"] > 0

    cafe = next(t for t in statement["transactions"] if "JOES CAFE" in t["description"])
    assert cafe["status"] == "needs_review" and cafe["suggestions"][0] == "personal"

    res = client.patch(
        f"/api/statements/{statement['id']}/transactions/{cafe['id']}",
        json={"category": "personal", "remember": True},
    )
    assert res.status_code == 200
    fixed = next(t for t in res.json()["transactions"] if t["id"] == cafe["id"])
    assert fixed["status"] == "reviewed"

    listing = client.get("/api/statements").json()
    assert listing[0]["id"] == statement["id"]
    assert listing[0]["needs_review_count"] == statement["summary"]["needs_review_count"] - 1

    export = client.get(f"/api/statements/{statement['id']}/export.csv")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")

    rules = client.get("/api/rules").json()
    assert rules[0]["category"] == "personal"
    assert client.delete(f"/api/rules/out/{rules[0]['merchant_key']}").status_code == 204


def test_sign_convention_form_field(client):
    data = csv_bytes("Date,Description,Amount", "01/03/2026,SHELL OIL,45.20", "01/04/2026,KROGER,5")
    res = upload(client, data, sign_convention="negative_is_spending")
    assert res.json()["transactions"][0]["amount_cents"] == 4520


def test_samples_endpoint(client):
    names = [s["name"] for s in client.get("/api/samples").json()]
    assert names == ["checking", "credit_card"]
    res = client.post("/api/samples/credit_card")
    assert res.status_code == 201 and len(res.json()["skipped"]) == 2
    assert client.post("/api/samples/../../etc/passwd").status_code == 404
    assert client.post("/api/samples/nope").status_code == 404


def test_rejects_bad_uploads(client):
    assert upload(client, b"x", name="statement.pdf").status_code == 415
    assert upload(client, b"a" * (64 * 1024 + 1)).status_code == 413
    res = upload(client, b"hello\nworld\n")
    assert res.status_code == 422 and "columns" in res.json()["detail"]
    assert client.get("/api/statements/999").status_code == 404


def test_invalid_category_update(client):
    statement = upload(client, csv_bytes("Date,Description,Amount", "01/03/2026,SHELL,-45")).json()
    tx = statement["transactions"][0]
    res = client.patch(
        f"/api/statements/{statement['id']}/transactions/{tx['id']}",
        json={"category": "bogus"},
    )
    assert res.status_code == 422


def test_delete_statement(client):
    statement = upload(client, csv_bytes("Date,Description,Amount", "01/03/2026,SHELL,-45")).json()
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 204
    assert client.get(f"/api/statements/{statement['id']}").status_code == 404
