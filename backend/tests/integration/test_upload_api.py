from fastapi.testclient import TestClient

from tests.conftest import upload
from tests.factories import OFX_V1, bank_csv


def test_upload_returns_201_statement_out(client: TestClient) -> None:
    r = upload(client, bank_csv())
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "jan.csv"
    assert body["source_format"] == "csv"
    assert body["account_type"] == "checking"
    assert body["row_count"] == 4
    assert body["period_start"] == "2026-01-02"
    assert body["period_end"] == "2026-01-20"
    assert sum(body["counts"].values()) == 4
    assert set(body["counts"]) == {"auto", "needs_review", "user_confirmed", "duplicate"}
    assert r.headers["X-Request-ID"]


def test_D40_same_file_twice_is_409_with_existing_id(client: TestClient) -> None:
    first = upload(client, bank_csv()).json()
    r = upload(client, bank_csv())
    assert r.status_code == 409
    body = r.json()
    assert r.headers["content-type"].startswith("application/problem+json")
    assert body["existing_id"] == first["id"]
    assert first["id"] in body["detail"]


def test_D41_overlapping_second_statement_marks_duplicates(client: TestClient) -> None:
    upload(client, bank_csv())
    second = upload(client, bank_csv([("02/10/2026", "SOMETHING NEW", "-9.99")]), name="feb.csv")
    assert second.status_code == 201
    body = second.json()
    assert body["counts"]["duplicate"] == 4
    items = client.get(f"/api/v1/statements/{body['id']}/transactions?status=duplicate").json()
    assert items["total"] == 4
    assert all(i["duplicate_of_id"] for i in items["items"])


def test_P19_duplicate_fitid_in_ofx_second_is_duplicate(client: TestClient) -> None:
    r = upload(client, OFX_V1, name="a.ofx")
    assert r.status_code == 201
    body = r.json()
    assert body["source_format"] == "ofx"
    assert body["counts"]["duplicate"] == 1
    dup = client.get(f"/api/v1/statements/{body['id']}/transactions?status=duplicate").json()
    assert dup["items"][0]["row_index"] == 4
    assert dup["items"][0]["duplicate_of_id"]


def test_P21_ofx_in_csv_file_warns(client: TestClient) -> None:
    body = upload(client, OFX_V1, name="oops.csv").json()
    assert body["source_format"] == "ofx"
    assert "EXTENSION_MISMATCH" in [w["code"] for w in body["warnings"]]


def test_422_problem_shape_for_bad_csv(client: TestClient) -> None:
    r = upload(client, "foo,bar\n1,2\n")
    assert r.status_code == 422
    body = r.json()
    assert {"type", "title", "status", "detail", "instance"} <= body.keys()
    assert body["code"] == "NO_HEADER"
    assert r.headers["content-type"].startswith("application/problem+json")


def test_P16_row_level_errors_listed(client: TestClient) -> None:
    rows = [
        (f"01/{(i % 28) + 1:02d}/2026", f"R{i}", "bad" if i < 30 else "-1.00") for i in range(100)
    ]
    r = upload(client, "Date,Description,Amount\n" + "\n".join(",".join(x) for x in rows))
    assert r.status_code == 422
    assert len(r.json()["errors"]) == 20


def test_415_for_wrong_extension(client: TestClient) -> None:
    assert upload(client, "x", name="a.exe").status_code == 415


def test_missing_account_type_is_422_problem(client: TestClient) -> None:
    r = client.post("/api/v1/statements", files={"file": ("a.csv", b"x", "text/csv")})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_invalid_account_type_rejected(client: TestClient) -> None:
    assert upload(client, bank_csv(), account_type="savings").status_code == 422


def test_list_get_delete_statement(client: TestClient) -> None:
    a = upload(client, bank_csv()).json()
    b = upload(client, bank_csv([("02/01/2026", "NEW", "-1.00")]), name="b.csv").json()
    listing = client.get("/api/v1/statements").json()
    assert [s["id"] for s in listing] == [b["id"], a["id"]] or {s["id"] for s in listing} == {
        a["id"],
        b["id"],
    }
    assert client.get(f"/api/v1/statements/{a['id']}").json()["id"] == a["id"]
    assert client.delete(f"/api/v1/statements/{a['id']}").status_code == 204
    assert client.get(f"/api/v1/statements/{a['id']}").status_code == 404
    assert client.delete(f"/api/v1/statements/{a['id']}").status_code == 404
    # purge also removed its transactions
    assert client.get(f"/api/v1/statements/{a['id']}/transactions").status_code == 404
    # and a re-upload of the purged file is allowed again
    assert upload(client, bank_csv()).status_code == 201


def test_deleting_earlier_statement_keeps_later_duplicates_intact(client: TestClient) -> None:
    a = upload(client, bank_csv()).json()
    b = upload(client, bank_csv([("02/10/2026", "NEW", "-1.00")]), name="b.csv").json()
    assert client.delete(f"/api/v1/statements/{a['id']}").status_code == 204
    items = client.get(f"/api/v1/statements/{b['id']}/transactions").json()
    assert items["total"] == 5
    assert all(i["duplicate_of_id"] is None for i in items["items"])


def test_unknown_statement_404_problem(client: TestClient) -> None:
    r = client.get("/api/v1/statements/nope")
    assert r.status_code == 404
    assert r.json()["status"] == 404


def test_categories_endpoint(client: TestClient) -> None:
    cats = client.get("/api/v1/categories").json()
    rent = next(c for c in cats if c["code"] == "RENT")
    assert rent == {
        "code": "RENT",
        "label": "Rents received",
        "kind": "income",
        "schedule_e_line": "3",
        "allowed_directions": ["inflow"],
    }
    assert len(cats) == 25


def test_health(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
