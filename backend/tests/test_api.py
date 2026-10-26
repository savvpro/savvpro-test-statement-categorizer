from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "freelancer_statement.csv"


def upload(client, name="s.csv", content=None):
    data = content if content is not None else SAMPLE.read_bytes()
    return client.post("/api/categorize", files={"file": (name, data, "text/csv")})


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_categorize_sample_end_to_end(client):
    response = upload(client)
    assert response.status_code == 200
    body = response.json()
    assert len(body["transactions"]) == 29
    assert body["issues"] == [{"row": 28, "message": "Unreadable amount 'abc'"}]
    assert body["needs_review"] == sum(t["category"] == "Needs Review" for t in body["transactions"])
    assert any("recurring" in t["flags"] for t in body["transactions"])


def test_rejects_unsupported_file_type(client):
    assert upload(client, "s.pdf", b"%PDF").status_code == 415


def test_rejects_unreadable_csv(client):
    assert upload(client, content=b"a,b\n1,2\n").status_code == 422


def test_learning_loop(client):
    def joes_cafe_category():
        rows = upload(client).json()["transactions"]
        return next(t["category"] for t in rows if t["merchant"] == "JOES CAFE")

    assert joes_cafe_category() == "Needs Review"
    saved = client.put("/api/rules", json={"merchant": "JOES CAFE 9921", "category": "Travel"})
    assert saved.json() == {"merchant": "JOES CAFE", "category": "Travel"}
    assert joes_cafe_category() == "Travel"
    assert client.delete("/api/rules/JOES CAFE").status_code == 204
    assert client.get("/api/rules").json() == []


def test_cannot_save_review_rule(client):
    assert client.put("/api/rules", json={"merchant": "X", "category": "Needs Review"}).status_code == 422


def test_tax_estimate_endpoint(client):
    body = {"transactions": [{"category": "Business Income", "amount": "30000"},
                             {"category": "Travel", "amount": "-2000"}]}
    result = client.post("/api/tax-estimate", json=body).json()
    assert result["profit"] == "28000.00"
