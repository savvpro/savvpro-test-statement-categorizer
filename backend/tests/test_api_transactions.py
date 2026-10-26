import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserRuleRow
from tests.conftest import upload

HEADER = "Date,Description,Amount,Currency\n"


def find(detail: dict, text: str) -> dict:
    matches = [t for t in detail["transactions"] if text in t["raw_description"]]
    assert len(matches) == 1, f"expected one row containing {text!r}, got {len(matches)}"
    return matches[0]


def patch(client: TestClient, transaction_id: int, **body):
    return client.patch(f"/api/transactions/{transaction_id}", json=body)


def test_fixing_a_review_row(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    row = find(statement, "XYZ TRADERS")
    assert row["needs_review"] is True and row["category"] == "Needs Review"

    response = patch(client, row["id"], category="Office Supplies")
    assert response.status_code == 200
    body = response.json()
    fixed = body["transaction"]
    assert fixed["category"] == "Office Supplies" and fixed["kind"] == "expense"
    assert fixed["needs_review"] is False and fixed["edited_by_user"] is True
    assert (fixed["rule_id"], fixed["reason"], fixed["confidence"]) == ("manual", "set by you", 1.0)
    assert fixed["suggested_category"] is None and body["reclassified_count"] == 0

    reread = client.get(f"/api/statements/{statement['id']}").json()
    assert find(reread, "XYZ TRADERS")["category"] == "Office Supplies"
    assert reread["needs_review_count"] == 3


def test_unchanged_rows_stay_untouched(client: TestClient) -> None:
    statement = upload(client, "bank_a_card.csv").json()
    patch(client, find(statement, "XYZ TRADERS")["id"], category="Office Supplies")
    after = client.get(f"/api/statements/{statement['id']}").json()
    before_rows = {t["id"]: t for t in statement["transactions"]}
    for t in after["transactions"]:
        if "XYZ TRADERS" not in t["raw_description"]:
            assert t == before_rows[t["id"]]


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"category": "Groceries"}, 422),
        ({"category": "Needs Review"}, 422),
        ({"category": "Meals", "kind": "spending"}, 422),
        ({}, 422),
        ({"category": "Meals", "remember": "maybe"}, 422),
    ],
)
def test_invalid_corrections_are_422(client: TestClient, body: dict, status: int) -> None:
    row = find(upload(client, "bank_a_card.csv").json(), "XYZ TRADERS")
    assert patch(client, row["id"], **body).status_code == status
    after = client.get("/api/statements/1").json()
    assert find(after, "XYZ TRADERS")["needs_review"] is True  # nothing changed


def test_unknown_transaction_is_a_404(client: TestClient) -> None:
    response = patch(client, 999, category="Meals")
    assert response.status_code == 404 and "999" in response.json()["detail"]


@pytest.mark.parametrize(
    ("text", "category", "given_kind", "kind"),
    [
        ("XYZ TRADERS", "Transfer", None, "transfer"),
        ("XYZ TRADERS", "Income", None, "income"),
        ("XYZ TRADERS", "Refund", None, "refund"),
        ("XYZ TRADERS", "Bank Fees", None, "fee"),
        ("XYZ TRADERS", "Tax Withheld", None, "tax"),
        ("XYZ TRADERS", "Meals", None, "expense"),  # no implied kind: money out = expense
        ("XYZ TRADERS", "Meals", "fee", "fee"),  # an explicit kind wins
        ("XYZ TRADERS", "Transfer", "expense", "expense"),
    ],
)
def test_kind_follows_the_category_unless_given(
    client: TestClient, text: str, category: str, given_kind: str | None, kind: str
) -> None:
    row = find(upload(client, "bank_a_card.csv").json(), text)
    body = {"category": category} | ({"kind": given_kind} if given_kind else {})
    assert patch(client, row["id"], **body).json()["transaction"]["kind"] == kind


def test_a_cash_row_with_kind_transfer_follows_the_sign_when_recategorised(
    client: TestClient,
) -> None:
    row = find(upload(client, "bank_b_checking.csv").json(), "ATM CASH")
    assert row["kind"] == "transfer"
    assert patch(client, row["id"], category="Personal").json()["transaction"]["kind"] == "expense"


def test_remember_reclassifies_other_rows_but_not_hand_edited_ones(
    client: TestClient, db: Session
) -> None:
    a = upload(client, "bank_a_card.csv").json()
    messy = upload(client, "messy_statement.csv").json()
    a2 = upload(client, "bank_a_card.csv").json()
    # "XYZ TRADERS 4471 RAWALPINDI" has the same merchant key in all three statements
    row_a, row_m, row_a2 = (find(s, "XYZ TRADERS") for s in (a, messy, a2))
    assert row_a["merchant_key"] == row_m["merchant_key"] == "XYZ TRADERS RAWALPINDI"
    assert row_m["needs_review"] and row_a2["needs_review"]

    # the user fixes one copy by hand, with no "remember"
    assert patch(client, row_a2["id"], category="Meals").status_code == 200

    response = patch(client, row_a["id"], category="Travel", remember=True)
    assert response.status_code == 200
    assert response.json()["reclassified_count"] == 1

    rule = db.scalars(select(UserRuleRow)).one()
    assert (rule.merchant_key, rule.category, rule.kind) == (
        "XYZ TRADERS RAWALPINDI",
        "Travel",
        None,
    )

    after_m = find(client.get(f"/api/statements/{messy['id']}").json(), "XYZ TRADERS")
    assert (after_m["category"], after_m["needs_review"]) == ("Travel", False)
    assert after_m["rule_id"] == "user:XYZ TRADERS RAWALPINDI"
    assert after_m["edited_by_user"] is False and after_m["confidence"] == 1.0
    after_a2 = find(client.get(f"/api/statements/{a2['id']}").json(), "XYZ TRADERS")
    assert (after_a2["category"], after_a2["edited_by_user"]) == ("Meals", True)  # not overwritten
    assert after_a2["rule_id"] == "manual"


def test_remember_updates_the_rule_instead_of_adding_another(
    client: TestClient, db: Session
) -> None:
    row = find(upload(client, "bank_a_card.csv").json(), "XYZ TRADERS")
    patch(client, row["id"], category="Travel", remember=True)
    patch(client, row["id"], category="Meals", remember=True)
    rule = db.scalars(select(UserRuleRow)).one()
    assert rule.category == "Meals"


def test_remember_keeps_the_kind_a_category_implies(client: TestClient, db: Session) -> None:
    row = find(upload(client, "bank_a_card.csv").json(), "XYZ TRADERS")
    patch(client, row["id"], category="Transfer", remember=True)
    assert db.scalars(select(UserRuleRow)).one().kind == "transfer"
    again = upload(client, "bank_a_card.csv").json()
    new = find(again, "XYZ TRADERS")
    assert (new["category"], new["kind"], new["needs_review"]) == ("Transfer", "transfer", False)


def test_remembered_rule_applies_to_later_uploads(client: TestClient) -> None:
    row = find(upload(client, "bank_a_card.csv").json(), "XYZ TRADERS")
    patch(client, row["id"], category="Travel", remember=True)
    later = find(upload(client, "messy_statement.csv").json(), "XYZ TRADERS")
    assert (later["category"], later["rule_id"]) == ("Travel", "user:XYZ TRADERS RAWALPINDI")


def test_remember_is_rejected_without_a_merchant_key(client: TestClient) -> None:
    csv = (HEADER + "2026-09-01,12345,-5.00,PKR\n").encode()
    row = upload(client, "x.csv", csv).json()["transactions"][0]
    assert row["merchant_key"] == ""
    response = patch(client, row["id"], category="Meals", remember=True)
    assert response.status_code == 422 and "merchant" in response.json()["detail"].lower()
    # the row was not changed by the rejected request
    assert client.get("/api/statements/1").json()["transactions"][0]["needs_review"] is True
    # without "remember" the same row can be fixed
    assert patch(client, row["id"], category="Meals").status_code == 200


def test_duplicate_flag_survives_a_remember_re_run(client: TestClient) -> None:
    csv = (HEADER + "2026-09-01,MYSTERY SHOP 77,-10.00,PKR\n" * 2).encode()
    first, second = upload(client, "x.csv", csv).json()["transactions"]
    assert "possible duplicate of row 1" in second["reason"] and second["needs_review"]

    patch(client, first["id"], category="Meals", remember=True)
    after = client.get("/api/statements/1").json()["transactions"]
    assert (after[0]["category"], after[0]["needs_review"]) == ("Meals", False)
    assert after[1]["category"] == "Meals"  # from the saved rule
    assert after[1]["needs_review"] is True and after[1]["reason"] == "possible duplicate of row 1"
