import pytest

from app.core.errors import ParseError
from app.domain.enums import AccountType, SourceFormat
from app.ingest import parse_statement
from app.ingest.ofx_reader import parse_ofx
from tests.factories import OFX_V1, OFX_V2


def test_P17_sgml_without_closing_tags() -> None:
    fmt, res = parse_statement(OFX_V1.encode(), "a.ofx")
    assert fmt is SourceFormat.OFX
    assert len(res.rows) == 4
    assert res.rows[0].amount_raw == "1800.00"
    assert res.rows[0].fitid == "A1"
    assert res.account_type_hint is AccountType.CHECKING
    assert res.date_format == "ofx"


def test_sgml_entities_unescaped() -> None:
    res = parse_ofx(OFX_V1, max_rows=100)
    assert res.rows[1].memo_raw == "repairs & parts"


def test_P18_xml_v2_credit_card() -> None:
    _, res = parse_statement(OFX_V2.encode(), "a.qfx")
    assert len(res.rows) == 2
    assert res.account_type_hint is AccountType.CREDIT_CARD
    assert res.rows[0].description_raw == "LOWES #1234"


def test_P20_memo_used_when_name_missing() -> None:
    res = parse_ofx(OFX_V1, max_rows=100)
    assert res.rows[2].description_raw == "MEMO ONLY ITEM"
    assert res.rows[2].memo_raw is None


def test_no_name_no_memo_uses_trntype_with_warning() -> None:
    text = "<OFX><STMTTRN><TRNTYPE>FEE<DTPOSTED>20260105<TRNAMT>-3.00<FITID>1</STMTTRN></OFX>"
    res = parse_ofx(text, max_rows=10)
    assert res.rows[0].description_raw == "FEE"
    assert [w.code for w in res.warnings] == ["NO_DESCRIPTION"]


def test_checknum_description() -> None:
    text = (
        "<OFX><STMTTRN><TRNTYPE>CHECK<DTPOSTED>20260105<TRNAMT>-3.00<CHECKNUM>1042</STMTTRN></OFX>"
    )
    assert parse_ofx(text, max_rows=10).rows[0].description_raw == "CHECK #1042"


def test_S04_doctype_entity_is_unsafe_xml() -> None:
    xxe = (
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        "<OFX><STMTTRN><DTPOSTED>20260101</DTPOSTED><TRNAMT>-1</TRNAMT>"
        "<NAME>&xxe;</NAME></STMTTRN></OFX>"
    )
    with pytest.raises(ParseError) as exc:
        parse_statement(xxe.encode(), "a.ofx")
    assert exc.value.code == "UNSAFE_XML"


def test_S05_billion_laughs_is_unsafe_xml() -> None:
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
        '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]>'
        "<OFX><STMTTRN><NAME>&lol3;</NAME></STMTTRN></OFX>"
    )
    with pytest.raises(ParseError) as exc:
        parse_statement(bomb.encode(), "a.ofx")
    assert exc.value.code == "UNSAFE_XML"


def test_xml_without_doctype_defusedxml_path_rejects_malformed() -> None:
    with pytest.raises(ParseError) as exc:
        parse_ofx('<?xml version="1.0"?><OFX><STMTTRN></OFX>', max_rows=10)
    assert exc.value.code == "INVALID_OFX"


def test_S10_deeply_nested_sgml_and_xml() -> None:
    sgml = "<OFX>" + "<A>" * 60 + "</A>" * 60 + "</OFX>"
    with pytest.raises(ParseError) as exc:
        parse_ofx(sgml, max_rows=10)
    assert exc.value.code == "OFX_TOO_DEEP"
    xml = '<?xml version="1.0"?><OFX>' + "<A>" * 60 + "</A>" * 60 + "</OFX>"
    with pytest.raises(ParseError) as exc2:
        parse_ofx(xml, max_rows=10)
    assert exc2.value.code == "OFX_TOO_DEEP"


def test_no_ofx_element() -> None:
    with pytest.raises(ParseError):
        parse_ofx("OFXHEADER:100\n\nnothing here", max_rows=10)


def test_ofx_row_limit() -> None:
    with pytest.raises(ParseError) as exc:
        parse_ofx(OFX_V1, max_rows=2)
    assert exc.value.code == "ROW_LIMIT"


def test_ofx_bad_rows_over_5_percent_refused() -> None:
    text = "<OFX><STMTTRN><DTPOSTED>bad<TRNAMT>-1<NAME>x</STMTTRN></OFX>"
    with pytest.raises(ParseError):
        parse_ofx(text, max_rows=10)
