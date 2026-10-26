"""End to end through the HTTP API, using the fake sample statements."""

import csv
import io

PKR_CSV = "pkr_business_account_march.csv"
USD_CSV = "usd_freelance_account_april.csv"


def rows(client, **params):
    return client.get("/api/transactions", params=params).json()


def by_description(client, text):
    return next(t for t in rows(client) if t["description"] == text)


def test_upload_categorises_every_row_or_marks_it_for_review(client, upload):
    response = upload(PKR_CSV)
    assert response.status_code == 201
    report = response.json()["report"]
    assert report["rows_imported"] == 20
    assert report["auto"] + report["needs_review"] == 20
    for t in rows(client):
        assert t["status"] in ("auto", "needs_review")
        assert t["reason"]
        assert (t["category"] is None) == (t["status"] == "needs_review")


def test_same_file_twice_is_refused(upload):
    assert upload(PKR_CSV).status_code == 201
    second = upload(PKR_CSV)
    assert second.status_code == 409
    assert "already imported" in second.json()["detail"]


def test_overlapping_statements_flag_duplicates(client, upload):
    first = "Date,Description,Amount\n2026-03-01,JETBRAINS SRO,-3980.00\n"
    second = first + "2026-03-02,GITHUB.COM,-1120.00\n"
    upload(first, name="a.csv", currency="PKR")
    upload(second, name="b.csv", currency="PKR")
    jetbrains = [t for t in rows(client) if t["description"] == "JETBRAINS SRO"]
    assert [t["status"] for t in jetbrains] == ["auto", "needs_review"]
    assert "imported earlier" in jetbrains[1]["reason"]


def test_unsupported_and_ambiguous_files_get_clear_messages(upload):
    assert upload(b"hello", name="notes.txt").status_code == 422
    missing_currency = upload("Date,Description,Amount\n2026-03-01,A,-1\n")
    assert missing_currency.status_code == 422
    assert "PKR or USD" in missing_currency.json()["detail"]


def test_correction_is_saved_and_offers_a_rule(client, upload):
    upload(PKR_CSV)
    cafe = by_description(client, "JOES CAFE 9921")
    response = client.patch(f"/api/transactions/{cafe['id']}", json={"category": "Meals"})
    body = response.json()
    assert (body["status"], body["category"]) == ("user_corrected", "Meals")
    assert body["rule_offer"] == {"pattern": "JOES CAFE", "match_type": "contains", "category": "Meals"}
    assert by_description(client, "JOES CAFE 9921")["status"] == "user_corrected"  # persisted


def test_correction_can_be_undone(client, upload):
    upload(PKR_CSV)
    cafe = by_description(client, "JOES CAFE 9921")
    client.patch(f"/api/transactions/{cafe['id']}", json={"category": "Meals"})
    undone = client.patch(f"/api/transactions/{cafe['id']}", json={"category": None}).json()
    assert undone["status"] == "needs_review" and undone["category"] is None


def test_income_category_on_money_out_is_rejected(client, upload):
    upload(PKR_CSV)
    cafe = by_description(client, "JOES CAFE 9921")
    response = client.patch(f"/api/transactions/{cafe['id']}", json={"category": "Business Income"})
    assert response.status_code == 422


def test_money_in_corrected_to_a_spending_category_counts_as_a_refund(client, upload):
    upload("Date,Description,Amount\n2026-03-01,MYSTERY CREDIT,500.00\n", currency="PKR")
    row = rows(client)[0]
    body = client.patch(f"/api/transactions/{row['id']}", json={"category": "Office & Equipment"}).json()
    assert body["type"] == "refund"


def test_rule_preview_then_create_only_changes_review_rows(client, upload):
    upload(PKR_CSV)
    foodpanda = [t for t in rows(client) if t["description"] == "FOODPANDA ORDER 5512"]
    client.patch(f"/api/transactions/{foodpanda[0]['id']}", json={"category": "Personal"})

    rule = {"pattern": "foodpanda", "match_type": "contains", "category": "Meals"}
    preview = client.post("/api/rules/preview", json=rule).json()
    assert preview["pattern"] == "FOODPANDA"
    assert preview["already_decided"] == 1  # the corrected row is left alone
    assert len(preview["affected"]) == 1
    assert preview["affected"][0]["after"]["status"] == "needs_review"  # still a possible duplicate
    assert any(o["id"] == "FOOD-FOODPANDA" for o in preview["overlaps"])

    created = client.post("/api/rules", json=rule)
    assert created.status_code == 201
    after = [t for t in rows(client) if t["description"] == "FOODPANDA ORDER 5512"]
    assert after[0]["category"] == "Personal"  # user's correction kept
    assert after[1]["status"] == "needs_review"
    assert after[1]["suggested_category"] == "Meals"


def test_new_rule_decides_matching_review_rows(client, upload):
    upload(PKR_CSV)
    created = client.post("/api/rules", json={"pattern": "JOES CAFE", "category": "Meals"}).json()
    assert created["rows_decided"] == 1
    cafe = by_description(client, "JOES CAFE 9921")
    assert (cafe["status"], cafe["category"], cafe["rule_id"]) == ("auto", "Meals", created["rule"]["rule_id"])


def test_rule_is_used_for_later_imports(client, upload):
    client.post("/api/rules", json={"pattern": "JOES CAFE", "category": "Meals"})
    upload("Date,Description,Amount\n2026-05-01,JOES CAFE 1234,-900\n", currency="PKR")
    assert rows(client)[0]["category"] == "Meals"


def test_duplicate_rule_and_tiny_pattern_are_refused(client):
    client.post("/api/rules", json={"pattern": "JOES CAFE", "category": "Meals"})
    assert client.post("/api/rules", json={"pattern": "joes  cafe", "category": "Meals"}).status_code == 409
    assert client.post("/api/rules", json={"pattern": "ab", "category": "Meals"}).status_code == 422
    assert client.post("/api/rules", json={"pattern": "abc", "category": "Nope"}).status_code == 422


def test_disabled_rule_is_not_used(client, upload):
    rule = client.post("/api/rules", json={"pattern": "JOES CAFE", "category": "Meals"}).json()["rule"]
    client.patch(f"/api/rules/{rule['id']}", json={"enabled": False})
    upload("Date,Description,Amount\n2026-05-01,JOES CAFE 1234,-900\n", currency="PKR")
    assert rows(client)[0]["status"] == "needs_review"


def test_totals_keep_currencies_apart_and_skip_unsure_rows(client, upload):
    upload(PKR_CSV)
    upload(USD_CSV)
    summary = client.get("/api/summary").json()
    pkr, usd = summary["currencies"]
    assert (pkr["currency"], usd["currency"]) == ("PKR", "USD")

    # PKR: Payoneer 280,000 is the only decided income; ACME is still in review.
    assert pkr["income"] == "280000.00"
    # GitHub 1120 - refund 1120 + Nayatel 4999 + AWS 8450 + JetBrains 3980 + SMS 200
    assert pkr["spending"] == "17629.00"
    assert pkr["tax_deducted"] == "732.00"
    assert pkr["transfers_out"] == "50000.00"
    assert pkr["personal_out"] == "1100.00"
    assert pkr["review_count"] == 9

    # USD: Upwork 1800 + Toptal 3200 + Wise 450
    assert usd["income"] == "5450.00"
    assert summary["unreadable_rows"] == 1  # the '31.2O' row in the USD file


def test_export_is_csv_and_neutralises_formulas(client, upload):
    upload("Date,Description,Amount\n2026-05-01,=HYPERLINK(\"x\"),-900\n", currency="PKR")
    upload(PKR_CSV)
    text = client.get("/api/export.csv").text
    table = list(csv.reader(io.StringIO(text)))
    assert table[0][:4] == ["date", "description", "amount", "currency"]
    formula_row = next(r for r in table if "HYPERLINK" in r[1])
    assert formula_row[1].startswith("'=")
    assert formula_row[2] == "-900.00"  # numbers stay numbers


def test_deleting_a_statement_removes_its_rows(client, upload):
    statement = upload(PKR_CSV).json()
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 204
    assert rows(client) == []
    assert client.delete(f"/api/statements/{statement['id']}").status_code == 404


def test_meta_lists_categories_and_ocr_status(client):
    meta = client.get("/api/meta").json()
    assert {"name": "Transfer", "kind": "transfer"} in meta["categories"]
    assert isinstance(meta["ocr_available"], bool)

