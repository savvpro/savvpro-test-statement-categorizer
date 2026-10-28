from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import upload
from tests.factories import bank_csv, fake_categorize


def test_S01_oversize_file_413_via_content_length(client: TestClient) -> None:
    r = upload(client, b"a" * (6 * 1024 * 1024), name="big.csv")
    assert r.status_code == 413
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 413


def test_S01_oversize_when_content_length_lies(settings: Settings) -> None:
    small = settings.model_copy(update={"max_upload_bytes": 1000})
    with TestClient(create_app(small, categorize=fake_categorize)) as c:
        # chunked body: no Content-Length header, size is counted while streaming
        def body():  # type: ignore[no-untyped-def]
            yield b'--b\r\nContent-Disposition: form-data; name="account_type"\r\n\r\nchecking\r\n'
            yield b'--b\r\nContent-Disposition: form-data; name="file"; filename="a.csv"\r\n\r\n'
            for _ in range(200):
                yield b"x" * 1024
            yield b"\r\n--b--\r\n"

        r = c.post(
            "/api/v1/statements",
            content=body(),
            headers={"Content-Type": "multipart/form-data; boundary=b"},
        )
        assert r.status_code == 413


def test_S02_exe_renamed_csv_415(client: TestClient) -> None:
    assert upload(client, b"MZ\x90\x00\x03" + b"\x00" * 100, name="a.csv").status_code == 415


def test_S03_pdf_415(client: TestClient) -> None:
    assert upload(client, b"%PDF-1.4\n1 0 obj", name="a.pdf").status_code == 415
    assert upload(client, b"%PDF-1.4\n1 0 obj", name="a.csv").status_code == 415


def test_S04_xxe_422_unsafe_xml(client: TestClient) -> None:
    xxe = (
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
        b"<OFX><STMTTRN><DTPOSTED>20260101</DTPOSTED><TRNAMT>-1</TRNAMT><NAME>&e;</NAME></STMTTRN></OFX>"
    )
    r = upload(client, xxe, name="x.ofx")
    assert r.status_code == 422
    assert r.json()["code"] == "UNSAFE_XML"


def test_S06_too_many_rows_422(settings: Settings) -> None:
    capped = settings.model_copy(update={"max_rows": 50})
    with TestClient(create_app(capped, categorize=fake_categorize)) as c:
        rows = [(f"01/{(i % 28) + 1:02d}/2026", f"R{i}", "-1.00") for i in range(60)]
        text = "Date,Description,Amount\n" + "\n".join(",".join(r) for r in rows)
        r = upload(c, text)
        assert r.status_code == 422
        assert r.json()["code"] == "ROW_LIMIT"


def test_S07_path_traversal_filename_stored_as_basename(client: TestClient) -> None:
    r = upload(client, bank_csv(), name="../../etc/passwd.csv")
    assert r.status_code == 201
    assert r.json()["filename"] == "passwd.csv"


def test_S09_very_long_description_truncated_with_warning(client: TestClient) -> None:
    text = "Date,Description,Amount\n01/05/2026," + "A" * 10_000 + ",-5.00\n"
    r = upload(client, text)
    assert r.status_code == 201
    assert "DESCRIPTION_TRUNCATED" in [w["code"] for w in r.json()["warnings"]]
    item = client.get(f"/api/v1/statements/{r.json()['id']}/transactions").json()["items"][0]
    assert len(item["description"]) == 512


def test_S08_formula_payloads_escaped_on_export(client: TestClient) -> None:
    rows = [
        ("01/05/2026", "\"=cmd|' /C calc'!A0\"", "-5.00"),
        ("01/06/2026", '"+SUM(1,1)"', "-6.00"),
        ("01/07/2026", '"@evil"', "-7.00"),
        ("01/08/2026", '"-2+3"', "-8.00"),
    ]
    sid = upload(client, "Date,Description,Amount\n" + "\n".join(",".join(r) for r in rows)).json()[
        "id"
    ]
    text = client.get(f"/api/v1/statements/{sid}/export.csv").text
    for line in text.splitlines()[1:]:
        assert line.split(",")[1].lstrip('"')[0] == "'"


def test_security_headers_present_on_every_response(client: TestClient) -> None:
    for r in (client.get("/healthz"), client.get("/api/v1/statements/nope")):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
        assert r.headers["cross-origin-opener-policy"] == "same-origin"
        assert "camera=()" in r.headers["permissions-policy"]


def test_request_id_accepted_only_when_well_formed(client: TestClient) -> None:
    ok = client.get("/healthz", headers={"X-Request-ID": "abcd-1234-efgh"})
    assert ok.headers["x-request-id"] == "abcd-1234-efgh"
    bad = client.get("/healthz", headers={"X-Request-ID": "bad id\twith junk!"})
    assert bad.headers["x-request-id"] != "bad id\twith junk!"
    assert len(bad.headers["x-request-id"]) == 36


def test_cors_allowlist(client: TestClient) -> None:
    allowed = client.get("/healthz", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-credentials" not in allowed.headers
    denied = client.get("/healthz", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in denied.headers


def test_rate_limit_on_uploads(settings: Settings) -> None:
    limited = settings.model_copy(update={"rate_limit": "3/minute"})
    with TestClient(create_app(limited, categorize=fake_categorize)) as c:
        codes = [upload(c, b"x", name="a.exe").status_code for _ in range(5)]
        assert codes[:3] == [415, 415, 415]
        assert codes[3:] == [429, 429]
        r = upload(c, b"x", name="a.exe")
        assert r.headers["content-type"].startswith("application/problem+json")


def test_docs_disabled_in_production(tmp_path: Path, settings: Settings) -> None:
    prod = settings.model_copy(update={"env": "production"})
    with TestClient(create_app(prod, categorize=fake_categorize)) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404
    with TestClient(create_app(settings, categorize=fake_categorize)) as c:
        assert c.get("/docs").status_code == 200


def test_unhandled_error_is_500_problem_without_stack(settings: Settings) -> None:
    def boom(txns, ctx):  # type: ignore[no-untyped-def]
        raise RuntimeError("secret internals")

    with TestClient(create_app(settings, categorize=boom), raise_server_exceptions=False) as c:
        r = upload(c, bank_csv())
        assert r.status_code == 500
        assert "secret internals" not in r.text
        assert r.json()["title"] == "Internal error"
        assert r.headers["x-request-id"]
        # a failed upload leaves nothing behind (transaction rolled back)
        assert c.get("/api/v1/statements").json() == []
