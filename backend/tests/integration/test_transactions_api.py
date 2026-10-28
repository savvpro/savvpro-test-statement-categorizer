import csv
import io

from fastapi.testclient import TestClient

from tests.conftest import upload
from tests.factories import bank_csv


def _statement(client: TestClient, extra: list[tuple[str, str, str]] | None = None) -> str:
    r = upload(client, bank_csv(extra or []))
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _items(client: TestClient, sid: str, query: str = "") -> list[dict[str, object]]:
    r = client.get(f"/api/v1/statements/{sid}/transactions{query}")
    assert r.status_code == 200, r.text
    return list(r.json()["items"])


def test_list_shape_and_defaults(client: TestClient) -> None:
    sid = _statement(client)
    body = client.get(f"/api/v1/statements/{sid}/transactions").json()
    assert body["total"] == 4
    item = body["items"][0]
    assert set(item) == {
        "id", "row_index", "posted_date", "amount_cents", "direction", "description", "memo",
        "merchant_key", "category", "brain_category", "status", "confidence", "reasons",
        "flags", "is_refund", "duplicate_of_id", "similar_count",
    }  # fmt: skip
    assert [i["row_index"] for i in body["items"]] == [1, 2, 3, 4]


def test_filters_sort_pagination(client: TestClient) -> None:
    sid = _statement(client)
    assert {i["status"] for i in _items(client, sid, "?status=needs_review")} == {"needs_review"}
    assert len(_items(client, sid, "?category=REPAIRS")) == 2
    assert len(_items(client, sid, "?q=home%20depot")) == 2
    assert _items(client, sid, "?q=%25") == []  # LIKE wildcard is escaped
    amounts = [i["amount_cents"] for i in _items(client, sid, "?sort=amount&order=desc")]
    assert amounts == sorted(amounts, reverse=True)
    page = client.get(f"/api/v1/statements/{sid}/transactions?limit=2&offset=3").json()
    assert page["total"] == 4
    assert len(page["items"]) == 1
    assert client.get(f"/api/v1/statements/{sid}/transactions?limit=501").status_code == 422
    assert client.get(f"/api/v1/statements/{sid}/transactions?sort=evil").status_code == 422


def test_similar_count(client: TestClient) -> None:
    sid = _statement(client)
    hd = [i for i in _items(client, sid) if i["merchant_key"] == "HOME DEPOT"]
    assert [i["similar_count"] for i in hd] == [1, 1]


def test_patch_confirms_and_changes_category(client: TestClient) -> None:
    sid = _statement(client)
    cafe = next(i for i in _items(client, sid) if i["merchant_key"] == "JOES CAFE")
    r = client.patch(f"/api/v1/transactions/{cafe['id']}", json={"category": "OTHER_EXPENSE"})
    assert r.status_code == 200
    body = r.json()
    assert body["rule_created"] is False
    assert body["updated"][0]["status"] == "user_confirmed"
    assert body["updated"][0]["category"] == "OTHER_EXPENSE"


def test_patch_422_for_direction_conflict_and_unknown_category(client: TestClient) -> None:
    sid = _statement(client)
    cafe = next(i for i in _items(client, sid) if i["merchant_key"] == "JOES CAFE")
    r = client.patch(f"/api/v1/transactions/{cafe['id']}", json={"category": "RENT"})
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_CORRECTION"
    assert (
        client.patch(f"/api/v1/transactions/{cafe['id']}", json={"category": "NOPE"}).status_code
        == 422
    )
    assert (
        client.patch("/api/v1/transactions/missing", json={"category": "REPAIRS"}).status_code
        == 404
    )
    extra = client.patch(f"/api/v1/transactions/{cafe['id']}", json={"category": "REPAIRS", "x": 1})
    assert extra.status_code == 422


def test_D12_refund_row_accepts_expense_category_on_inflow(client: TestClient) -> None:
    sid = _statement(client)
    refund = next(i for i in _items(client, sid) if i["amount_cents"] == 4500)
    assert refund["is_refund"] is True
    r = client.patch(f"/api/v1/transactions/{refund['id']}", json={"category": "SUPPLIES"})
    assert r.status_code == 200


def test_remember_creates_rule_then_updates_it(client: TestClient) -> None:
    sid = _statement(client)
    cafe = next(i for i in _items(client, sid) if i["merchant_key"] == "JOES CAFE")
    url = f"/api/v1/transactions/{cafe['id']}"
    assert client.patch(url, json={"category": "OTHER_EXPENSE", "remember": True}).json()[
        "rule_created"
    ]
    assert not client.patch(url, json={"category": "SUPPLIES", "remember": True}).json()[
        "rule_created"
    ]


def test_D42_memory_applies_on_next_upload(client: TestClient) -> None:
    sid = _statement(client)
    cafe = next(i for i in _items(client, sid) if i["merchant_key"] == "JOES CAFE")
    client.patch(
        f"/api/v1/transactions/{cafe['id']}", json={"category": "OTHER_EXPENSE", "remember": True}
    )
    r = upload(
        client,
        "Date,Description,Amount\n03/01/2026,SQ *JOES CAFE 1111 SEATTLE WA,-12.00\n",
        name="m.csv",
    )
    sid2 = r.json()["id"]
    row = _items(client, sid2)[0]
    assert (row["category"], row["status"]) == ("OTHER_EXPENSE", "auto")


def test_apply_to_similar_skips_confirmed_and_incompatible(client: TestClient) -> None:
    extra = [("01/25/2026", "POS DEBIT HOME DEPOT #4410 TACOMA WA", "-10.00")]
    sid = _statement(client, extra)
    rows = [i for i in _items(client, sid) if i["merchant_key"] == "HOME DEPOT"]
    assert len(rows) == 3
    outflows = [r for r in rows if r["amount_cents"] < 0]  # type: ignore[operator]
    client.patch(f"/api/v1/transactions/{outflows[1]['id']}", json={"category": "SUPPLIES"})
    r = client.patch(
        f"/api/v1/transactions/{outflows[0]['id']}",
        json={"category": "CLEANING_MAINTENANCE", "apply_to_similar": True},
    ).json()
    updated = {u["id"]: u for u in r["updated"]}
    assert outflows[0]["id"] in updated
    assert outflows[1]["id"] not in updated  # already user_confirmed
    refund = next(x for x in rows if x["amount_cents"] > 0)  # type: ignore[operator]
    assert refund["id"] in updated  # refunds may take an expense category
    after = {i["id"]: i for i in _items(client, sid)}
    assert after[outflows[1]["id"]]["category"] == "SUPPLIES"


def test_apply_to_similar_leaves_other_statements_alone(client: TestClient) -> None:
    sid1 = _statement(client)
    sid2 = upload(
        client,
        "Date,Description,Amount\n03/01/2026,POS DEBIT HOME DEPOT #9 TACOMA WA,-5.00\n",
        name="o.csv",
    ).json()["id"]
    target = next(i for i in _items(client, sid1) if i["amount_cents"] == -12345)
    client.patch(
        f"/api/v1/transactions/{target['id']}",
        json={"category": "SUPPLIES", "apply_to_similar": True},
    )
    assert _items(client, sid2)[0]["category"] == "REPAIRS"


def test_restore_duplicate_makes_row_real(client: TestClient) -> None:
    upload(client, bank_csv())
    sid2 = upload(client, bank_csv([("02/10/2026", "NEW THING", "-9.99")]), name="b.csv").json()[
        "id"
    ]
    dup = _items(client, sid2, "?status=duplicate")[0]
    r = client.post(f"/api/v1/transactions/{dup['id']}/restore-duplicate")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"auto", "needs_review"}
    assert body["duplicate_of_id"] is None
    assert "DUPLICATE_PRIOR_UPLOAD" not in body["flags"]
    # restoring a row that is not a duplicate is refused
    assert client.post(f"/api/v1/transactions/{dup['id']}/restore-duplicate").status_code == 422
    assert client.post("/api/v1/transactions/zzz/restore-duplicate").status_code == 404


def test_summary_counts_and_refund_netting(client: TestClient) -> None:
    sid = _statement(client)
    s = client.get(f"/api/v1/statements/{sid}/summary").json()
    assert s["income"] == {"RENT": 180000}
    assert s["expenses"] == {"REPAIRS": -12345 + 4500}
    assert s["total_income_cents"] == 180000
    assert s["total_expense_cents"] == -7845
    assert s["net_cents"] == 180000 - 7845
    assert s["unresolved"] == {"count": 1, "total_abs_cents": 1850}
    assert s["duplicates"] == {"count": 0}
    assert s["schedule_e"][0] == {
        "line": "3", "label": "Rents received", "category": "RENT", "total_cents": 180000,
    }  # fmt: skip


def test_summary_updates_after_correction(client: TestClient) -> None:
    sid = _statement(client)
    cafe = next(i for i in _items(client, sid) if i["merchant_key"] == "JOES CAFE")
    client.patch(f"/api/v1/transactions/{cafe['id']}", json={"category": "OTHER_EXPENSE"})
    s = client.get(f"/api/v1/statements/{sid}/summary").json()
    assert s["expenses"]["OTHER_EXPENSE"] == -1850
    assert s["unresolved"]["count"] == 0


def test_export_csv(client: TestClient) -> None:
    sid = _statement(client)
    r = client.get(f"/api/v1/statements/{sid}/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="jan-categorized.csv"'
    rows = list(csv.reader(io.StringIO(r.text, newline="")))
    assert rows[0][:4] == ["date", "description", "amount", "category"]
    assert len(rows) == 5
    assert rows[1][2] == "1800.00"
    assert rows[2][2] == "-123.45"
    assert client.get("/api/v1/statements/nope/export.csv").status_code == 404
