import csv
import io

from fastapi.testclient import TestClient

from tests.conftest import upload

HEADER = "Date,Description,Amount,Currency\n"
TWO_CURRENCIES = (
    HEADER
    + "2026-09-01,ADOBE CREATIVE CLOUD,-59.99,USD\n"
    + "2026-09-02,GITHUB INC,-4.00,USD\n"
    + "2026-09-03,SQ *JOES CAFE 9921,-1850.00,PKR\n"
    + "2026-09-04,ANNUAL FEE,-5000.00,PKR\n"
    + "2026-09-05,PAYMENT THANK YOU,185000.00,PKR\n"
    + "2026-09-06,ADOBE CREATIVE CLOUD,59.99,USD\n"
).encode()


def summary(client: TestClient, statement_id: int) -> dict:
    response = client.get(f"/api/statements/{statement_id}/summary")
    assert response.status_code == 200
    return response.json()


def test_currencies_are_summed_separately(client: TestClient) -> None:
    statement_id = upload(client, "two.csv", TWO_CURRENCIES).json()["id"]
    body = summary(client, statement_id)
    assert set(body["currencies"]) == {"PKR", "USD"}
    usd, pkr = body["currencies"]["USD"], body["currencies"]["PKR"]

    assert usd["expenses"] == {"count": 2, "total": "63.99"}
    assert usd["expenses_by_category"] == [
        {"category": "Software & Subscriptions", "count": 2, "total": "63.99"}
    ]
    assert usd["refunds"] == {"count": 1, "total": "59.99"}
    assert usd["fees"]["total"] == "0.00" and usd["income"]["total"] == "0.00"

    assert pkr["expenses"] == {"count": 1, "total": "1850.00"}
    assert pkr["expenses_by_category"] == [{"category": "Meals", "count": 1, "total": "1850.00"}]
    assert pkr["fees"] == {"count": 1, "total": "5000.00"}
    assert pkr["transfers"] == {"count": 1, "total_out": "0.00", "total_in": "185000.00"}
    assert pkr["refunds"]["count"] == 0
    assert body["needs_review_count"] == 0 and body["parse_error_count"] == 0


def test_bank_summary_keeps_transfers_and_tax_out_of_expenses(client: TestClient) -> None:
    body = summary(client, upload(client, "bank_b_checking.csv").json()["id"])
    assert set(body["currencies"]) == {"PKR"}
    pkr = body["currencies"]["PKR"]
    categories = {c["category"] for c in pkr["expenses_by_category"]}
    assert categories == {"Internet & Phone", "Professional Services"}  # no Transfer, no Tax
    assert pkr["expenses"] == {"count": 5, "total": "39649.00"}
    assert pkr["tax_already_paid"] == {"count": 1, "total": "120.00"}
    assert pkr["transfers"] == {"count": 3, "total_out": "285000.00", "total_in": "50000.00"}
    assert pkr["fees"] == {"count": 5, "total": "1022.00"}
    assert pkr["income"] == {"count": 5, "total": "1186550.00"}
    assert pkr["refunds"] == {"count": 1, "total": "4299.00"}
    assert pkr["personal"] == {"count": 0, "total": "0.00"}


def test_personal_spending_is_reported_apart_from_expenses(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    netflix = next(t for t in statement["transactions"] if "NETFLIX" in t["raw_description"])
    assert netflix["category"] == "Personal" and netflix["kind"] == "expense"

    body = summary(client, statement["id"])
    pkr = body["currencies"]["PKR"]
    assert pkr["personal"] == {"count": 1, "total": "1100.00"}
    assert "Personal" not in {c["category"] for c in pkr["expenses_by_category"]}
    # ten business rows: Joe's Cafe, hosting, cafe, Uber Eats, Careem, stationers, Uber,
    # PIA, Airblue, computers. Netflix is not one of them.
    assert pkr["expenses"] == {"count": 10, "total": "85395.00"}
    assert sum(c["count"] for c in pkr["expenses_by_category"]) == 10
    usd = body["currencies"]["USD"]
    assert usd["personal"] == {"count": 0, "total": "0.00"}
    assert usd["expenses"] == {"count": 10, "total": "220.26"}


def test_a_row_fixed_to_personal_leaves_expenses(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    xyz = next(t for t in statement["transactions"] if "XYZ TRADERS" in t["raw_description"])
    before = summary(client, statement["id"])["currencies"]["PKR"]
    assert before["personal"]["total"] == "1100.00"

    client.patch(f"/api/transactions/{xyz['id']}", json={"category": "Personal"})
    after = summary(client, statement["id"])["currencies"]["PKR"]
    assert after["personal"] == {"count": 2, "total": "4300.00"}  # 1100.00 + 3200.00
    assert after["expenses"] == before["expenses"]  # not deductible, so expenses do not change
    assert after["needs_review"]["count"] == before["needs_review"]["count"] - 1


def test_review_rows_are_kept_out_of_every_total_and_reported_on_their_own(
    client: TestClient,
) -> None:
    body = summary(client, upload(client, "bank_b_checking.csv").json()["id"])
    pkr = body["currencies"]["PKR"]
    assert body["needs_review_count"] == 5
    assert pkr["needs_review"] == {"count": 5, "total_out": "108740.00", "total_in": "15000.00"}


def test_fixing_a_row_moves_it_into_the_totals(client: TestClient) -> None:
    statement = upload(client, "bank_b_checking.csv").json()
    person = next(t for t in statement["transactions"] if "ALI RAZA" in t["raw_description"])
    client.patch(f"/api/transactions/{person['id']}", json={"category": "Professional Services"})
    pkr = summary(client, statement["id"])["currencies"]["PKR"]
    assert pkr["expenses"]["total"] == "74649.00"  # 39649.00 + 35000.00
    assert pkr["needs_review"]["count"] == 4


def test_summary_counts_parse_errors(client: TestClient) -> None:
    body = summary(client, upload(client, "messy_statement.csv").json()["id"])
    assert body["parse_error_count"] == 4 and body["needs_review_count"] == 2
    assert body["currencies"]["PKR"]["needs_review"]["count"] == 1  # XYZ TRADERS
    assert body["currencies"]["USD"]["needs_review"]["count"] == 1  # the duplicate Adobe row


def test_empty_statement_has_an_empty_summary(client: TestClient) -> None:
    statement_id = upload(client, "e.csv", HEADER.encode()).json()["id"]
    assert summary(client, statement_id)["currencies"] == {}


def test_export_has_the_original_columns_plus_the_decision(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    response = client.get(f"/api/statements/{statement['id']}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="bank_a_card-categorized.csv"' in response.headers[
        "content-disposition"
    ]
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "Date", "Description", "Amount", "Currency",
        "Category", "Kind", "Confidence", "Needs Review", "Reason",
    ]  # fmt: skip
    assert len(rows) == 32
    assert rows[1] == [
        "2026-09-01", "ADOBE CREATIVE CLOUD SAN JOSE CA", "-59.99", "USD",
        "Software & Subscriptions", "expense", "0.95", "no", "Adobe subscription",
    ]  # fmt: skip
    by_description = {r[1]: r for r in rows[1:]}
    xyz = by_description["XYZ TRADERS 4471 RAWALPINDI"]
    assert (xyz[4], xyz[7]) == ("Needs Review", "yes")
    assert by_description["PAYMENT THANK YOU"][2:6] == ["185000.00", "PKR", "Transfer", "transfer"]


def test_export_includes_the_users_fixes(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    row = next(t for t in statement["transactions"] if "XYZ" in t["raw_description"])
    client.patch(f"/api/transactions/{row['id']}", json={"category": "Travel"})
    exported = client.get(f"/api/statements/{statement['id']}/export").text
    rows = list(csv.reader(io.StringIO(exported)))
    xyz = next(r for r in rows if "XYZ" in r[1])
    assert (xyz[4], xyz[7], xyz[8]) == ("Travel", "no", "set by you")


def test_export_does_not_let_a_description_become_a_spreadsheet_formula(
    client: TestClient,
) -> None:
    statement_id = upload(
        client, "evil.csv", (HEADER + '2026-09-01,"=HYPERLINK(""http://x.test"")",-1.00,PKR\n').encode()
    ).json()["id"]
    rows = list(csv.reader(io.StringIO(client.get(f"/api/statements/{statement_id}/export").text)))
    assert rows[1][1].startswith("'=HYPERLINK")
    assert rows[1][2] == "-1.00"  # amounts are not touched


def test_export_file_name_is_made_safe(client: TestClient) -> None:
    statement_id = upload(
        client, "my stmt;(1)&.csv", (HEADER + "2026-09-01,X,-1,PKR\n").encode()
    ).json()["id"]
    response = client.get(f"/api/statements/{statement_id}/export")
    disposition = response.headers["content-disposition"]
    assert disposition == 'attachment; filename="my_stmt__1__-categorized.csv"'
