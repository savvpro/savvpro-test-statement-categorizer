from fastapi.testclient import TestClient

from app.categories import Category as C
from app.config import Settings
from app.main import create_app

from .conftest import by_row, upload

# What the brain should decide for every row of sample_data/driver_statement.csv.
# Keys are line numbers in the file. Line 23 has an impossible date and is skipped.
EXPECTED_SAMPLE = {
    2: C.INCOME,  # UBER BV PAYOUT
    3: C.FUEL,  # SHELL ... LAHORE
    4: C.FUEL,  # PSO FUEL
    5: C.TOLLS_PARKING,  # M2 MOTORWAY TOLL
    6: C.PHONE_INTERNET,  # JAZZ MOBILE BILL
    7: C.PERSONAL,  # FOODPANDA*ORDER (a purchase, not a payout)
    8: C.TRANSFER,  # TRANSFER TO SAVINGS
    9: C.CAR_MAINTENANCE,  # AUTO WORKSHOP
    10: C.REFUND,  # SHELL PETROL REFUND (not income)
    11: C.INCOME,  # CAREEM PAYOUT
    12: C.NEEDS_REVIEW,  # ALI TRADERS (unknown)
    13: C.NEEDS_REVIEW,  # ATM CASH WITHDRAWAL
    14: C.PLATFORM_FEES,  # UBER SERVICE FEE
    15: C.NEEDS_REVIEW,  # TRANSFER TO ALI KHAN (own account or a payment?)
    16: C.NEEDS_REVIEW,  # ALI TRADERS again
    17: C.FUEL,  # lower-case shell petrol
    18: C.TOLLS_PARKING,  # CITY PARKING FEE
    19: C.CARD_PAYMENT,  # PAYMENT THANK YOU
    20: C.PERSONAL,  # NETFLIX
    21: C.INCOME,  # FOODPANDA PAYOUT
    22: C.NEEDS_REVIEW,  # RANDOM DEPOSIT
    24: C.PHONE_INTERNET,  # ZONG
    25: C.NEEDS_REVIEW,  # EASYPAISA
}


def uploaded_sample(client, sample_bytes):
    response = upload(client, sample_bytes, "driver_statement.csv")
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------- upload


def test_sample_statement_is_categorised_exactly_as_designed(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    rows = by_row(data)
    assert {r: C(t["category"]) for r, t in rows.items()} == EXPECTED_SAMPLE
    assert all(t["reason"] for t in rows.values())


def test_sample_upload_reports_skipped_rows_and_review_count(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    assert data["summary"]["total_transactions"] == 23
    assert data["summary"]["needs_review"] == 6
    assert [s["row"] for s in data["skipped"]] == [23]
    assert "valid date" in data["skipped"][0]["message"]
    assert data["currency"] == "PKR"
    kinds = {c["name"]: c["kind"] for c in data["categories"]}
    assert kinds["Fuel"] == "deductible"
    assert kinds["Needs Review"] == "review"
    assert len(kinds) == 11


def test_sample_tax_summary(client, sample_bytes):
    tax = uploaded_sample(client, sample_bytes)["summary"]["tax"]
    assert tax["income"] == 76800  # 45000 + 22000 + 9800
    assert tax["deductible_expenses"] == 21600  # 28100 spent - 6500 fuel refund
    assert tax["refunds_netted"] == 6500
    assert tax["personal_spending"] == 2550
    assert tax["estimated_profit"] == 55200
    assert tax["complete"] is False


def test_uploaded_statement_can_be_fetched_again(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    again = client.get(f"/api/statements/{data['id']}")
    assert again.status_code == 200
    assert again.json()["summary"] == data["summary"]


def test_credit_card_statements_with_positive_purchases(client):
    csv = (
        b"Date,Description,Amount\n"
        b"01/10/2026,SHELL PETROL,6500.00\n"
        b"02/10/2026,PAYMENT THANK YOU,-6500.00\n"
    )
    data = upload(client, csv, purchases_positive="true").json()
    rows = by_row(data)
    assert rows[2]["amount"] == -6500
    assert rows[2]["category"] == "Fuel"
    assert rows[3]["category"] == "Card Payment"


def test_amounts_are_json_numbers(client, sample_bytes):
    rows = by_row(uploaded_sample(client, sample_bytes))
    assert isinstance(rows[2]["amount"], float)
    assert rows[3]["amount"] == -6500


# ---------------------------------------------------------------- upload errors


def test_non_csv_file_is_rejected(client):
    r = upload(client, b"hello", "notes.txt")
    assert r.status_code == 400
    assert ".csv" in r.json()["detail"]


def test_empty_file_is_rejected(client):
    r = upload(client, b"")
    assert r.status_code == 400
    assert "empty" in r.json()["detail"]


def test_file_without_the_right_columns_gets_a_helpful_message(client):
    r = upload(client, b"Name,Colour\nAli,Red\n")
    assert r.status_code == 400
    assert "Could not find the columns" in r.json()["detail"]


def test_oversized_file_is_rejected():
    client = TestClient(create_app(Settings(_env_file=None, max_upload_bytes=200)))
    r = upload(client, b"Date,Description,Amount\n" + b"01/10/2026,SHELL,-5\n" * 50)
    assert r.status_code == 413


def test_missing_file_field_is_a_validation_error(client):
    assert client.post("/api/statements").status_code == 422


def test_a_path_in_the_filename_is_stripped(client, sample_bytes):
    data = upload(client, sample_bytes, "../../etc/passwd.csv").json()
    assert data["filename"] == "passwd.csv"


# ---------------------------------------------------------------- fixing rows


def fix(client, statement_id, txn_id, category):
    return client.patch(
        f"/api/statements/{statement_id}/transactions/{txn_id}", json={"category": category}
    )


def test_fixing_a_row_updates_totals_and_review_count(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    atm = by_row(data)[13]  # ATM CASH WITHDRAWAL, 5000

    response = fix(client, data["id"], atm["id"], "Personal")
    assert response.status_code == 200
    body = response.json()
    after = by_row(body["statement"])[13]
    assert after["category"] == "Personal"
    assert after["user_fixed"] is True
    assert after["confidence"] == 1.0
    assert body["statement"]["summary"]["needs_review"] == 5
    assert body["statement"]["summary"]["tax"]["personal_spending"] == 2550 + 5000


def test_one_fix_settles_every_look_alike_row(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    rows = by_row(data)
    # ALI TRADERS 5521 and ALI TRADERS 7733 are the same merchant
    body = fix(client, data["id"], rows[12]["id"], "Personal").json()
    after = by_row(body["statement"])
    assert after[12]["category"] == after[16]["category"] == "Personal"
    assert body["updated_ids"] == [rows[16]["id"]]
    assert after[16]["user_fixed"] is False  # the brain did it, the user did not
    assert body["statement"]["summary"]["needs_review"] == 4


def test_cash_rows_are_never_learned_from_each_other(client):
    csv = (
        b"Date,Description,Amount\n"
        b"01/10/2026,ATM CASH WITHDRAWAL,-5000\n"
        b"02/10/2026,ATM CASH WITHDRAWAL,-2000\n"
    )
    data = upload(client, csv).json()
    rows = by_row(data)
    body = fix(client, data["id"], rows[2]["id"], "Fuel").json()
    after = by_row(body["statement"])
    assert after[2]["category"] == "Fuel"
    assert after[3]["category"] == "Needs Review"  # each cash withdrawal has its own purpose
    assert body["updated_ids"] == []


def test_the_user_can_overrule_a_confident_decision(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    rows = by_row(data)
    body = fix(client, data["id"], rows[3]["id"], "Personal").json()  # SHELL ... was Fuel
    after = by_row(body["statement"])
    assert after[3]["category"] == "Personal"
    assert after[17]["category"] == "Personal"  # the look-alike shell row followed
    assert after[4]["category"] == "Fuel"  # PSO is a different merchant


def test_rows_the_user_fixed_are_never_overwritten_by_later_learning(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    rows = by_row(data)
    fix(client, data["id"], rows[17]["id"], "Fuel")  # explicit choice on the lower-case row
    body = fix(client, data["id"], rows[3]["id"], "Personal").json()
    after = by_row(body["statement"])
    assert after[17]["category"] == "Fuel"
    assert after[17]["user_fixed"] is True


def test_fixing_a_refund_row_remembers_what_it_refunds(client):
    csv = (
        b"Date,Description,Amount\n"
        b"01/10/2026,SHELL PETROL RETURN,6500\n"
        b"02/10/2026,SHELL PETROL,-6500\n"
    )
    data = upload(client, csv).json()
    rows = by_row(data)
    body = fix(client, data["id"], rows[2]["id"], "Refund").json()
    tax = body["statement"]["summary"]["tax"]
    assert tax["refunds_netted"] == 6500
    assert tax["deductible_expenses"] == 0
    assert tax["income"] == 0  # a refund must never leak into income


def test_fixing_does_not_leak_between_statements(client, sample_bytes):
    first = uploaded_sample(client, sample_bytes)
    second = uploaded_sample(client, sample_bytes)
    fix(client, first["id"], by_row(first)[12]["id"], "Personal")
    again = client.get(f"/api/statements/{second['id']}").json()
    assert by_row(again)[12]["category"] == "Needs Review"


def test_invalid_fixes_are_rejected(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    txn_id = by_row(data)[12]["id"]
    assert fix(client, data["id"], txn_id, "Not A Category").status_code == 422
    assert fix(client, data["id"], txn_id, "Needs Review").status_code == 422
    assert (
        client.patch(f"/api/statements/{data['id']}/transactions/{txn_id}", json={}).status_code
        == 422
    )


def test_unknown_ids_are_404(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    assert fix(client, data["id"], "nope", "Fuel").status_code == 404
    assert fix(client, "nope", "nope", "Fuel").status_code == 404
    assert client.get("/api/statements/nope").status_code == 404
    assert client.get("/api/statements/nope/export.csv").status_code == 404


# ---------------------------------------------------------------- export


def test_export_is_a_csv_download_that_excel_opens_as_utf8(client, sample_bytes):
    data = uploaded_sample(client, sample_bytes)
    r = client.get(f"/api/statements/{data['id']}/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf")
    lines = r.content.decode("utf-8-sig").splitlines()
    assert lines[0] == "Date,Description,Amount,Category,Confidence %,Why,Fixed by you"
    assert len(lines) == 1 + 23


def test_export_neutralises_spreadsheet_formulas(client):
    csv = (
        b"Date,Description,Amount\n"
        b'01/10/2026,"=HYPERLINK(""http://evil.test"",""click"")",-5\n'
        b"02/10/2026,@SUM(A1:A9),-6\n"
        b"03/10/2026,+1+1,-7\n"
    )
    data = upload(client, csv).json()
    text = client.get(f"/api/statements/{data['id']}/export.csv").content.decode("utf-8-sig")
    assert "'=HYPERLINK" in text
    assert "'@SUM" in text
    assert "'+1+1" in text
    for line in text.splitlines()[1:]:
        assert not line.split(",")[1].startswith(("=", "@", "+"))


# ---------------------------------------------------------------- misc endpoints


def test_health_and_categories(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    names = [c["name"] for c in client.get("/api/categories").json()]
    assert "Needs Review" not in names  # not something a user can pick
    assert {"Income", "Fuel", "Refund", "Transfer", "Card Payment"} <= set(names)


def test_sample_statement_download(client, sample_bytes):
    r = client.get("/api/sample-statement")
    assert r.status_code == 200
    assert r.content == sample_bytes


def test_cors_allows_the_frontend_origin_only(client):
    ok = client.options(
        "/api/statements",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/api/statements",
        headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers
