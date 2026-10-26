"""End-to-end API tests: upload -> categorized JSON."""

import io


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["rules_version"]


def test_categories_endpoint(client):
    r = client.get("/api/categories")
    assert r.status_code == 200
    body = r.json()
    assert "Software & Subscriptions" in body["spending"]
    assert "Transfers & Payments" in body["special"]


def _upload(client, path):
    with open(path, "rb") as f:
        return client.post(
            "/api/categorize",
            files={"file": (path.name, io.BytesIO(f.read()), "text/csv")},
        )


def test_categorize_designer_sample(client, designer_csv):
    r = _upload(client, designer_csv)
    assert r.status_code == 200
    body = r.json()

    assert body["summary"]["count"] == 39
    by_desc = {t["description"]: t for t in body["transactions"]}

    # the big rule: sure rows are auto-categorized...
    assert by_desc["ADOBE CREATIVE CLOUD"]["category"] == "Software & Subscriptions"
    assert by_desc["ADOBE CREATIVE CLOUD"]["needs_review"] is False
    # ...and unsure rows are asked about, never guessed
    assert by_desc["JOES CAFE 9921"]["category"] is None
    assert by_desc["JOES CAFE 9921"]["needs_review"] is True

    # special flows
    assert by_desc["TRANSFER TO SAVINGS *OPEN"]["category"] == "Transfers & Payments"
    assert by_desc["STRIPE PAYOUT INV-1042"]["category"] == "Income"
    assert by_desc["REFUND - STARBUCKS STORE 8842"]["linked_category"] == "Meals & Coffee"

    # the unknown credit must NOT be silently called income
    assert by_desc["CHECK DEPOSIT 5500"]["needs_review"] is True

    assert body["summary"]["review_count"] >= 3
    assert body["summary"]["spending_total"] > 0


def test_categorize_messy_sample(client, messy_csv):
    r = _upload(client, messy_csv)
    assert r.status_code == 200
    body = r.json()

    by_desc = {t["description"]: t for t in body["transactions"]}
    # duplicate detection
    uber = [t for t in body["transactions"] if t["description"].startswith("UBER *TRIP")]
    assert len(uber) == 2
    assert "possible_duplicate" in uber[1]["flags"]

    # total row skipped
    assert "Total" not in by_desc
    # unreadable date row survives and lands in review
    weird = by_desc["05/99/2026 WEIRD DATE ROW"]
    assert weird["needs_review"] is True
    # a row whose DATE COLUMN is garbage is caught by the date issue path
    bad = by_desc["TYPED WRONG DATE ROW"]
    assert bad["date"] is None
    assert bad["needs_review"] is True
    assert "date" in bad["reasons"][0]
    assert any("unreadable date" in w for w in body["warnings"])
    # the exact-amount refund of the amazon charge links back to the category
    assert by_desc["REFUND AMAZON MKTPLACE PMTS"]["linked_category"] == "Office & Equipment"
    # summary furniture + parse warnings surfaced to the user
    assert any("Skipped" in w for w in body["warnings"])


def test_rejects_non_csv(client):
    r = client.post("/api/categorize",
                    files={"file": ("statement.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert r.status_code == 400
    assert "csv" in r.json()["detail"].lower()


def test_rejects_empty_file(client):
    r = client.post("/api/categorize",
                    files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_rejects_unparseable_csv(client):
    r = client.post("/api/categorize",
                    files={"file": ("bad.csv", b"not,a,real,statement\n1,2,3\n",
                                    "text/csv")})
    assert r.status_code == 400


def test_every_transaction_is_audit_ready(client, designer_csv):
    """Each row must carry its reasoning - no black boxes."""
    body = _upload(client, designer_csv).json()
    for t in body["transactions"]:
        assert t["normalized"], "normalized description must be shown"
        assert isinstance(t["reasons"], list) and t["reasons"]
        assert t["band"] in {"high", "medium", "low"}
        assert 0.0 <= t["confidence"] <= 1.0
