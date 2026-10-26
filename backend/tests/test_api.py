from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import SAMPLE_DIR, upload
from tests.factories import (
    CARD_ROWS,
    OFX_SAMPLE,
    csv_bytes,
    pdf_blank_bytes,
    pdf_encrypted_bytes,
    pdf_text_bytes,
    xlsx_bytes,
)

CARD_LINES = [
    "03/01/2026 ADOBE CREATIVE CLOUD                   54.99",
    "03/02/2026 UBER *TRIP                             23.40",
    "03/03/2026 ONLINE PAYMENT THANK YOU             -500.00",
]


def codes(response):
    return response.json()["detail"]["code"]


# -- read-only endpoints -----------------------------------------------------------------------


def test_health_config_and_categories(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    cfg = client.get("/api/config").json()
    assert cfg["max_upload_mb"] == 5 and ".pdf" in cfg["accepted_extensions"]
    cats = client.get("/api/categories").json()
    kinds = {c["kind"] for c in cats}
    assert kinds == {"expense", "non_spending", "income", "review"}
    assert next(c for c in cats if c["id"] == "meals")["deductible"] == "partial"


def test_unknown_routes_use_the_error_shape(client):
    response = client.get("/api/nope")
    assert response.status_code == 404 and codes(response) == "not_found"
    assert client.delete("/api/health").status_code == 405


def test_security_headers_are_set(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store"


def test_cors_allows_the_dev_frontend_only(client):
    ok = client.options(
        "/api/statements",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    bad = client.options(
        "/api/statements",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


# -- uploads in every format -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "data", "fmt"),
    [
        ("card.csv", csv_bytes(CARD_ROWS), "csv"),
        ("card.xlsx", xlsx_bytes({"S": CARD_ROWS}), "xlsx"),
        ("card.pdf", pdf_text_bytes(CARD_LINES), "pdf"),
        ("card.ofx", OFX_SAMPLE, "ofx"),
    ],
)
def test_every_format_ends_in_the_same_result_shape(client, name, data, fmt):
    response = upload(client, name, data)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_format"] == fmt
    assert body["summary"]["transaction_count"] >= 2
    first = body["transactions"][0]
    assert {
        "id",
        "category_id",
        "status",
        "confidence",
        "reasons",
        "flags",
        "suggestions",
    } <= first.keys()


def test_misnamed_file_is_read_by_content_with_a_warning(client):
    body = upload(client, "statement.csv", pdf_text_bytes(CARD_LINES)).json()
    assert body["source_format"] == "pdf"
    assert any("looks like PDF" in w for w in body["warnings"])


def test_the_bundled_designer_sample_end_to_end(client):
    data = (SAMPLE_DIR / "designer_card_march_2026.csv").read_bytes()
    body = upload(client, "designer_card_march_2026.csv", data).json()
    by_desc = {t["description"]: t for t in body["transactions"]}
    assert by_desc["ADOBE *CREATIVE CLOUD 800-833-6687 CA"]["category_id"] == "software"
    assert by_desc["SQ *JOES CAFE 9921 SAN JOSE CA"]["status"] == "needs_review"
    assert by_desc["TRANSFER TO SAVINGS ****4421"]["status"] == "excluded"
    refund = by_desc["ADOBE REFUND CREATIVE CLOUD"]
    assert refund["category_id"] == "software" and refund["refund_of"] == "t-0001"
    assert body["summary"]["total_refunds"] > 0
    assert {r["line"] for r in body["rejected_rows"]} == {28, 29}


def test_filename_is_sanitised(client):
    body = upload(client, "../../etc/pass wd<script>.csv", csv_bytes(CARD_ROWS)).json()
    assert "/" not in body["filename"] and "<" not in body["filename"]
    assert body["filename"].endswith(".csv")


def test_manual_amount_convention(client):
    data = csv_bytes([["Date", "Description", "Amount"], ["2026-03-01", "STAPLES", "50.00"]])
    body = upload(client, "a.csv", data, amount_convention="negative_is_spending").json()
    assert body["convention"] == "negative_is_spending"
    assert body["transactions"][0]["spend_amount"] == -50.0


def test_bad_amount_convention_is_rejected(client):
    response = upload(client, "a.csv", csv_bytes(CARD_ROWS), amount_convention="sideways")
    assert response.status_code == 422 and codes(response) == "invalid_request"


def test_missing_file_field(client):
    response = client.post("/api/statements", data={})
    assert response.status_code == 422 and codes(response) == "invalid_request"


# -- files that cannot be used: clear errors, never a crash ------------------------------------


@pytest.mark.parametrize(
    ("name", "data", "status", "code"),
    [
        ("a.csv", b"", 422, "empty_file"),
        ("a.csv", b"  \n ", 422, "empty_file"),
        ("a.exe", b"MZ....", 415, "unsupported_format"),
        ("a", b"Date,Description,Amount\n", 415, "unsupported_format"),
        ("a.csv", b"Name,Age\nAda,36\n", 422, "missing_columns"),
        ("a.csv", b"Date,Description,Amount\n", 422, "no_transactions_found"),
        ("a.csv", b"Date,Description,Amount\nbad,row,here\n", 422, "no_transactions_found"),
        ("a.pdf", b"%PDF-1.4 definitely not a pdf", 422, "file_corrupt"),
        ("a.pdf", pdf_blank_bytes(), 422, "pdf_no_text"),
        ("a.pdf", pdf_encrypted_bytes(), 422, "pdf_encrypted"),
        ("a.xlsx", b"PK\x03\x04junk", 415, "unsupported_format"),
        ("a.csv", b"\x89PNG\r\n\x1a\n\x00\x00\x00", 415, "unsupported_format"),
        ("a.ofx", b"<OFX></OFX>", 422, "no_transactions_found"),
    ],
)
def test_unusable_files_get_a_clear_error(client, name, data, status, code):
    response = upload(client, name, data)
    assert response.status_code == status, response.text
    assert codes(response) == code
    assert response.json()["detail"]["message"]


def test_too_many_rows(settings):
    small = Settings(**{**settings.__dict__, "max_rows": 5})
    with TestClient(create_app(small)) as client:
        rows = [["Date", "Description", "Amount"]] + [
            ["2026-03-01", f"SHOP {i}", "1"] for i in range(9)
        ]
        response = upload(client, "a.csv", csv_bytes(rows))
    assert response.status_code == 413 and codes(response) == "too_many_rows"


def test_oversized_upload_is_refused_early(settings):
    small = Settings(**{**settings.__dict__, "max_upload_mb": 1})
    with TestClient(create_app(small)) as client:
        response = upload(client, "a.csv", b"Date,Description,Amount\n" + b"x" * (2 * 1024 * 1024))
    assert response.status_code == 413 and codes(response) == "file_too_large"


def test_upload_right_under_the_cap_is_accepted(settings):
    small = Settings(**{**settings.__dict__, "max_upload_mb": 1, "max_rows": 100_000})
    rows = "Date,Description,Amount\n" + "2026-03-01,STAPLES,1.00\n" * 100
    with TestClient(create_app(small)) as client:
        assert upload(client, "a.csv", rows.encode()).status_code == 201


def test_pdf_page_cap(settings):
    small = Settings(**{**settings.__dict__, "max_pdf_pages": 2})
    with TestClient(create_app(small)) as client:
        response = upload(client, "a.pdf", pdf_text_bytes(CARD_LINES, pages=4))
    assert response.status_code == 413 and codes(response) == "pdf_too_many_pages"


# -- rate limiting -----------------------------------------------------------------------------


def test_uploads_are_rate_limited_with_retry_after(settings):
    limited = Settings(**{**settings.__dict__, "rate_limit_uploads_per_minute": 2})
    with TestClient(create_app(limited)) as client:
        statuses = [upload(client, "a.csv", csv_bytes(CARD_ROWS)).status_code for _ in range(3)]
        blocked = upload(client, "a.csv", csv_bytes(CARD_ROWS))
        assert statuses == [201, 201, 429]
        assert codes(blocked) == "rate_limited"
        assert int(blocked.headers["retry-after"]) >= 1
        # Reads and health checks are not held back by the upload limit.
        assert client.get("/api/categories").status_code == 200
        assert client.get("/api/health").status_code == 200


def test_general_requests_are_rate_limited_but_health_is_exempt(settings):
    limited = Settings(**{**settings.__dict__, "rate_limit_requests_per_minute": 3})
    with TestClient(create_app(limited)) as client:
        results = [client.get("/api/categories").status_code for _ in range(5)]
        assert results == [200, 200, 200, 429, 429]
        assert all(client.get("/api/health").status_code == 200 for _ in range(10))


def test_rate_limit_responses_still_carry_cors_headers(settings):
    limited = Settings(**{**settings.__dict__, "rate_limit_requests_per_minute": 1})
    with TestClient(create_app(limited)) as client:
        client.get("/api/categories")
        blocked = client.get("/api/categories", headers={"Origin": "http://localhost:5173"})
    assert blocked.status_code == 429
    assert blocked.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "retry-after" in blocked.headers["access-control-expose-headers"].lower()


# -- reading and correcting --------------------------------------------------------------------

STARBUCKS = csv_bytes(
    [
        ["Date", "Description", "Amount"],
        ["2026-03-01", "SQ *JOES CAFE 9921", "12.50"],
        ["2026-03-02", "SQ *JOES CAFE 1234", "9.00"],
        ["2026-03-03", "STAPLES 0042", "20.00"],
        ["2026-03-04", "STAPLES 0042 RETURN", "-20.00"],
    ]
)


def test_get_statement_round_trips(client):
    created = upload(client, "a.csv", STARBUCKS).json()
    assert client.get(f"/api/statements/{created['id']}").json() == created


def test_unknown_statement_and_transaction(client):
    assert codes(client.get("/api/statements/nope")) == "statement_not_found"
    sid = upload(client, "a.csv", STARBUCKS).json()["id"]
    response = client.patch(
        f"/api/statements/{sid}/transactions/t-9999", json={"category_id": "meals"}
    )
    assert response.status_code == 404 and codes(response) == "transaction_not_found"


def test_correcting_one_row(client):
    sid = upload(client, "a.csv", STARBUCKS).json()["id"]
    response = client.patch(
        f"/api/statements/{sid}/transactions/t-0001", json={"category_id": "meals"}
    )
    body = response.json()
    assert response.status_code == 200 and body["updated_count"] == 1
    rows = {t["id"]: t for t in body["statement"]["transactions"]}
    assert rows["t-0001"]["status"] == "user_corrected" and rows["t-0001"]["confidence"] == 1.0
    assert rows["t-0002"]["status"] == "needs_review"  # not applied to similar
    assert body["statement"]["summary"]["needs_review_count"] == 1


def test_apply_to_similar_updates_matching_rows_and_remembers_the_rule(settings):
    with TestClient(create_app(settings)) as client:
        sid = upload(client, "a.csv", STARBUCKS).json()["id"]
        body = client.patch(
            f"/api/statements/{sid}/transactions/t-0001",
            json={"category_id": "meals", "apply_to_similar": True},
        ).json()
        assert body["updated_count"] == 2
        rows = {t["id"]: t for t in body["statement"]["transactions"]}
        assert (
            rows["t-0002"]["category_id"] == "meals"
            and rows["t-0002"]["status"] == "user_corrected"
        )
        assert rows["t-0003"]["status"] == "categorized"  # unrelated row untouched

    # A brand-new app (new process) with the same data directory still knows the rule.
    with TestClient(create_app(settings)) as fresh:
        again = upload(fresh, "b.csv", STARBUCKS).json()
        first = again["transactions"][0]
        assert first["category_id"] == "meals" and first["status"] == "categorized"
        assert "saved" in first["reasons"][0]


def test_a_refund_follows_a_corrected_purchase(client):
    sid = upload(client, "a.csv", STARBUCKS).json()["id"]
    body = client.patch(
        f"/api/statements/{sid}/transactions/t-0003", json={"category_id": "personal"}
    ).json()
    rows = {t["id"]: t for t in body["statement"]["transactions"]}
    assert body["updated_count"] == 2
    assert rows["t-0004"]["category_id"] == "personal"
    assert rows["t-0004"]["refund_of"] == "t-0003"


@pytest.mark.parametrize("category", ["needs_review", "bogus", ""])
def test_invalid_categories_are_refused(client, category):
    sid = upload(client, "a.csv", STARBUCKS).json()["id"]
    response = client.patch(
        f"/api/statements/{sid}/transactions/t-0001", json={"category_id": category}
    )
    assert response.status_code == 422
    assert codes(response) in {"invalid_category", "invalid_request"}


def test_correction_to_a_non_spending_category_leaves_spending(client):
    sid = upload(client, "a.csv", STARBUCKS).json()["id"]
    body = client.patch(
        f"/api/statements/{sid}/transactions/t-0001", json={"category_id": "transfer"}
    ).json()
    row = body["statement"]["transactions"][0]
    assert row["kind"] == "non_spending"
    assert body["statement"]["summary"]["excluded_total"] == 12.5


# -- export ------------------------------------------------------------------------------------


def test_export_csv(client):
    data = csv_bytes(
        [
            ["Date", "Description", "Amount"],
            ["2026-03-01", '=HYPERLINK("http://evil")', "10.00"],
            ["2026-03-02", "STAPLES 0042", "20.00"],
        ]
    )
    sid = upload(client, "my statement.csv", data).json()["id"]
    response = client.get(f"/api/statements/{sid}/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="my statement-categorized.csv"' in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("date,description,merchant,amount")
    assert "'=HYPERLINK" in lines[1]  # formula neutralised
    assert "Office Supplies & Equipment" in lines[2]


def test_export_of_unknown_statement(client):
    assert client.get("/api/statements/nope/export.csv").status_code == 404


def test_user_rule_file_is_created_under_the_data_dir(settings, tmp_path: Path):
    with TestClient(create_app(settings)) as client:
        sid = upload(client, "a.csv", STARBUCKS).json()["id"]
        client.patch(
            f"/api/statements/{sid}/transactions/t-0001",
            json={"category_id": "meals", "apply_to_similar": True},
        )
    assert (tmp_path / "user_rules.json").exists()
