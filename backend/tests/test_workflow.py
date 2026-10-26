import csv
import io

from backend.app.reports import summarize
from backend.tests.test_imports import OPTIONS, post_file


def test_review_persists_rule_is_scoped_and_export_matches(client):
    content = b"Date,Description,Amount,Currency\n2026-09-01,NAYATEL INTERNET,4200,PKR\n"
    assert post_file(client, "/api/imports", content).status_code == 201
    workspace = client.get("/api/workspace").json()
    row = workspace["transactions"][0]
    assert workspace["summary"]["currencies"]["PKR"]["business"] == 0
    update = {
        "kind": "expense",
        "category": "Internet & mobile",
        "purpose": "mixed",
        "business_percent": 60,
        "note": "Home connection; 60% work allocation.",
        "remember": True,
    }
    assert client.patch(f"/api/transactions/{row['id']}", json=update).status_code == 200
    workspace = client.get("/api/workspace").json()
    assert workspace["summary"]["currencies"]["PKR"]["business"] == 252000
    assert workspace["summary"]["currencies"]["PKR"]["personal"] == 168000
    assert workspace["summary"]["needs_review"] == 0
    assert len(workspace["rules"]) == 1
    next_month = content.replace(b"2026-09-01", b"2026-10-01")
    assert post_file(client, "/api/imports", next_month).status_code == 201
    rows = client.get("/api/workspace").json()["transactions"]
    assert next(row for row in rows if row["date"] == "2026-10-01")["rule_id"] == "user.exact"
    assert (
        post_file(client, "/api/imports", next_month, OPTIONS | {"account": "Other account"}).status_code
        == 201
    )
    rows = client.get("/api/workspace").json()["transactions"]
    assert next(row for row in rows if row["account"] == "Other account")["needs_review"]
    exported = list(csv.DictReader(io.StringIO(client.get("/api/export/transactions").text.lstrip("\ufeff"))))
    assert len(exported) == 3
    assert any(row["business_percent"] == "60" and row["note"] == update["note"] for row in exported)


def test_payments_transfers_refunds_and_currencies_reconcile(client):
    content = b"Date,Description,Amount,Currency\n2026-09-01,NETFLIX,1100,PKR\n2026-09-02,NETFLIX REFUND,-100,PKR\n2026-09-03,CREDIT CARD PAYMENT,1100,PKR\n2026-09-04,TRANSFER TO OWN SAVINGS,5000,PKR\n2026-09-05,OPENAI,20,USD\n"
    assert post_file(client, "/api/imports", content).status_code == 201
    summary = client.get("/api/workspace").json()["summary"]
    pkr = summary["currencies"]["PKR"]
    assert pkr["gross_expenses"] == 110000
    assert pkr["refunds"] == 10000
    assert pkr["net_expenses"] == 100000
    assert pkr["excluded"] == 610000
    assert pkr["net_movement"] == pkr["money_out"] - pkr["money_in"] == 710000
    assert pkr["net_expenses"] == pkr["business"] + pkr["personal"] + pkr["unallocated"]
    assert summary["currencies"]["USD"]["net_expenses"] == 2000


def test_review_validation_prevents_false_confirmation(client):
    assert client.post("/api/demo").status_code == 201
    row = next(
        row
        for row in client.get("/api/workspace").json()["transactions"]
        if row["description"] == "OPENAI REFUND"
    )
    update = {
        "kind": "expense",
        "category": "AI & developer tools",
        "purpose": "business",
        "business_percent": 100,
    }
    assert client.patch(f"/api/transactions/{row['id']}", json=update).status_code == 422
    update |= {"kind": "refund", "purpose": "mixed", "business_percent": 100}
    assert client.patch(f"/api/transactions/{row['id']}", json=update).status_code == 422


def test_export_escapes_formula_injection(client):
    content = b'Date,Description,Amount,Currency\n2026-09-01,=HYPERLINK("example"),100,PKR\n'
    assert post_file(client, "/api/imports", content).status_code == 201
    exported = client.get("/api/export/transactions").text
    assert "'=HYPERLINK" in exported


def test_half_minor_unit_allocations_round_consistently():
    row = {
        "currency": "PKR",
        "amount_minor": 101,
        "kind": "expense",
        "category": "Internet & mobile",
        "purpose": "mixed",
        "business_percent": 50,
        "needs_review": False,
    }
    totals = summarize([row])["currencies"]["PKR"]
    assert totals["business"] == 51
    assert totals["personal"] == 50


def test_family_support_is_personal_spending_only_after_confirmation(client):
    content = b"Date,Description,Amount,Currency\n2026-09-01,IBFT TO RECIPIENT 001,25000,PKR\n"
    assert post_file(client, "/api/imports", content).status_code == 201
    row = client.get("/api/workspace").json()["transactions"][0]
    assert row["kind"] == "transfer" and row["needs_review"]
    update = {
        "kind": "expense",
        "category": "Family support",
        "purpose": "personal",
        "business_percent": 0,
        "remember": True,
    }
    assert client.patch(f"/api/transactions/{row['id']}", json=update).status_code == 200
    totals = client.get("/api/workspace").json()["summary"]["currencies"]["PKR"]
    assert totals["personal"] == 2500000
    assert totals["excluded"] == 0
    assert post_file(client, "/api/imports", content.replace(b"09-01", b"10-01")).status_code == 201
    latest = client.get("/api/workspace").json()["transactions"][0]
    assert latest["category"] == "Family support" and not latest["needs_review"]


def test_remove_statement_cascades_and_does_not_remove_rules(client):
    content = b"Date,Description,Amount,Currency\n2026-09-01,OPENAI,5680,PKR\n"
    statement = post_file(client, "/api/imports", content).json()
    row = client.get("/api/workspace").json()["transactions"][0]
    update = {
        "kind": "expense",
        "category": "AI & developer tools",
        "purpose": "business",
        "business_percent": 100,
        "remember": True,
    }
    assert client.patch(f"/api/transactions/{row['id']}", json=update).status_code == 200
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 204
    workspace = client.get("/api/workspace").json()
    assert workspace["transactions"] == [] and workspace["statements"] == []
    assert len(workspace["rules"]) == 1
    assert post_file(client, "/api/imports", content).status_code == 201


def test_foreign_origins_cannot_mutate_local_workspace(client):
    assert client.post("/api/demo", headers={"Origin": "https://untrusted.example"}).status_code == 403
