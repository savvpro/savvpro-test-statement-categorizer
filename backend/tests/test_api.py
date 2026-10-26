import csv
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import upload
from fastapi.testclient import TestClient
from statement_categorizer.domain import ImportOptions
from statement_categorizer.main import create_app
from statement_categorizer.parser import MAX_FILE_BYTES, parse_statement
from statement_categorizer.store import Store


def import_and_get(client, data):
    result = upload(client, data)
    assert result.status_code in (200, 201), result.text
    return client.get(f"/api/statements/{result.json()['id']}").json()


def review(client, row, **overrides):
    payload = {
        "category": row["category"],
        "kind": row["kind"],
        "expected_version": row["version"],
        "excluded": False,
        "note": "",
        **overrides,
    }
    return client.patch(f"/api/transactions/{row['id']}", json=payload)


def test_sample_import_exact_summary_and_reconciliation(client, sample_bytes):
    statement = import_and_get(client, sample_bytes)
    s = statement["summary"]
    assert (s["transaction_count"], s["review_count"], s["auto_count"]) == (20, 9, 11)
    assert (s["spent_minor"], s["refund_minor"], s["net_expenses_minor"]) == (20248, 2000, 18248)
    assert s["income_minor"] == 0  # Unknown client credit is withheld.
    assert (s["transfer_in_minor"], s["transfer_out_minor"]) == (20000, 80000)
    assert s["raw_net_minor"] == s["accepted_net_minor"] + s["unresolved_net_minor"] + s["excluded_net_minor"]
    duplicate = next(row for row in statement["transactions"] if "possible_duplicate" in row["review_flags"])
    assert duplicate["duplicate_of"] and duplicate["status"] == "needs_review"
    assert client.get(f"/api/statements/{statement['id']}/export?final=true").status_code == 409


def test_exact_reupload_is_idempotent_and_different_settings_conflict(client, sample_bytes):
    first = upload(client, sample_bytes)
    second = upload(client, sample_bytes)
    assert first.status_code == 201 and second.status_code == 200
    assert second.json() == {"id": first.json()["id"], "reused": True}
    assert len(client.get("/api/statements").json()) == 1
    assert upload(client, sample_bytes, amount_mode="card_signed").status_code == 409


def test_review_persists_audit_and_detects_stale_edit(client, sample_bytes):
    statement = import_and_get(client, sample_bytes)
    row = next(row for row in statement["transactions"] if row["description"] == "JOES CAFE 9921")
    result = review(client, row, category="Meals", kind="expense", note="Meeting with a client; demo receipt checked.")
    assert result.status_code == 200
    assert result.json()["version"] == 2 and result.json()["status"] == "reviewed"
    assert result.json()["original_decision"] == row["original_decision"]
    assert review(client, row, category="Meals", kind="expense").status_code == 409
    events = client.get(f"/api/statements/{statement['id']}/audit").json()
    assert len(events) == 1 and events[0]["previous_value"]["category"] == "Needs Review"
    assert events[0]["new_value"]["category"] == "Meals"
    assert client.get(f"/api/statements/{statement['id']}").json()["summary"]["net_expenses_minor"] == 20088


def test_final_export_after_resolving_all_rows(client, sample_bytes):
    statement = import_and_get(client, sample_bytes)
    for row in statement["transactions"]:
        if row["status"] == "needs_review":
            result = review(client, row, excluded=True, note="Excluded by demo reviewer for this test.")
            assert result.status_code == 200, result.text
    final = client.get(f"/api/statements/{statement['id']}/export?final=true")
    assert final.status_code == 200
    rows = list(csv.DictReader(io.StringIO(final.text.lstrip("\ufeff"))))
    assert len(rows) == 20  # Excluded rows remain auditable in exports.
    assert "final-transactions.csv" in final.headers["content-disposition"]
    totals = client.get(f"/api/statements/{statement['id']}/export?final=true&summary=true")
    assert "Software" in totals.text and "20.00" in totals.text


def test_cross_statement_duplicate_is_flagged_not_deleted(client):
    import_and_get(client, b"Date,Description,Amount\n2026-04-02,FIGMA,-15\n")
    other = import_and_get(client, b"Date,Description,Amount\n2026-04-02,figma,-15.00\n")
    row = other["transactions"][0]
    assert row["status"] == "needs_review" and row["review_flags"] == ["possible_duplicate"]
    assert review(client, row, note="Two separate invoices checked.").status_code == 200
    assert client.get(f"/api/statements/{other['id']}").json()["summary"]["net_expenses_minor"] == 1500


@pytest.mark.parametrize(
    ("amount", "category", "kind"),
    [
        (10, "Software", "expense"),
        (-10, "Software", "refund"),
        (-10, "Income", "income"),
        (-10, "Software", "transfer"),
        (-10, "Personal", "expense"),
        (-10, "Needs Review", "unknown"),
        (0, "Transfers", "transfer"),
        (-10, "Meals", "personal"),
        (10, "Software", "income"),
    ],
)
def test_invalid_accounting_override_is_rejected(client, amount, category, kind):
    row = import_and_get(client, f"Date,Description,Amount\n2026-04-02,UNKNOWN,{amount}\n".encode())["transactions"][0]
    assert review(client, row, category=category, kind=kind).status_code == 422


def test_pending_cannot_count_and_exclusion_requires_note(client):
    statement = import_and_get(client, b"Date,Description,Amount,Status\n2026-04-02,FIGMA,-15,pending\n")
    row = statement["transactions"][0]
    assert review(client, row).status_code == 422
    assert review(client, row, excluded=True).status_code == 422
    assert review(client, row, excluded=True, note="Awaiting posted version.").status_code == 200
    posted = import_and_get(client, b"Date,Description,Amount,Status\n2026-04-02,FIGMA,-15,posted\n")
    assert posted["summary"]["review_count"] == 0


def test_invalid_import_is_atomic(client):
    result = upload(client, b"Date,Description,Amount\n2026-04-02,FIGMA,-15\n2026-04-03,ADOBE,abc\n")
    assert result.status_code == 422 and result.json()["errors"][0]["row"] == 3
    assert client.get("/api/statements").json() == []


def test_spreadsheet_formulas_escaped_and_original_preserved(client):
    statement = import_and_get(client, b'Date,Description,Amount\n2026-04-02,"=2+2",-15\n')
    row = statement["transactions"][0]
    assert row["description"] == "=2+2"
    assert review(client, row, excluded=True, note="@SUM(1,2)").status_code == 200
    result = client.get(f"/api/statements/{statement['id']}/export")
    exported = list(csv.DictReader(io.StringIO(result.text.lstrip("\ufeff"))))[0]
    assert exported["description"] == "'=2+2" and exported["review_note"] == "'@SUM(1,2)"
    assert exported["amount"] == "-15.00"


def test_boundaries_security_and_missing_resources(client):
    assert client.post("/api/statements", files={"file": ("sample.pdf", b"PDF")}).status_code == 415
    assert upload(client, b"a" * (MAX_FILE_BYTES + 1)).status_code == 413
    assert (
        client.post(
            "/api/statements", content=b"small", headers={"Content-Length": str(MAX_FILE_BYTES * 2)}
        ).status_code
        == 413
    )
    assert (
        client.post("/api/statements", content=b"small", headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 400
    for path in [
        "/api/statements/absent",
        "/api/statements/absent/audit",
        "/api/statements/absent/export",
        "/api/missing",
    ]:
        assert client.get(path).status_code == 404
    assert client.delete("/api/statements/absent").status_code == 404
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/options").json()["currencies"] == ["USD", "EUR", "GBP", "PKR", "CAD", "AUD"]
    assert client.get("/api/sample").status_code == 200


def test_delete_and_restart_persistence(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(path), base_url="http://localhost") as first:
        statement = import_and_get(first, b"Date,Description,Amount\n2026-04-02,FIGMA,-15\n")
        row = statement["transactions"][0]
        assert review(first, row, note="Verified receipt").status_code == 200
    with TestClient(create_app(path), base_url="http://localhost") as second:
        saved = second.get(f"/api/statements/{statement['id']}").json()
        assert saved["transactions"][0]["note"] == "Verified receipt"
        assert second.delete(f"/api/statements/{statement['id']}").status_code == 204
        assert second.get("/api/statements").json() == []


def test_concurrent_identical_imports_create_one_statement(tmp_path):
    store = Store(tmp_path / "concurrent.sqlite3")
    store.initialize()
    content = b"Date,Description,Amount\n2026-04-02,FIGMA,-15\n"
    parsed = parse_statement(content, ImportOptions())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: store.import_statement("fake.csv", content, ImportOptions(), parsed), range(4))
        )
    assert len({result[0] for result in results}) == 1
    assert sum(not reused for _, reused in results) == 1
