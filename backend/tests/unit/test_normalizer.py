from datetime import date

from app.domain.enums import AccountType, Direction
from app.domain.models import ParseResult
from app.ingest import parse_statement
from app.normalize.normalizer import make_fingerprint, normalize
from tests.factories import make_raw

FMT = "%m/%d/%Y"


def result(*rows: object, **kw: object) -> ParseResult:
    return ParseResult(rows=tuple(rows), warnings=(), date_format=FMT, **kw)  # type: ignore[arg-type]


def test_checking_signs_and_directions() -> None:
    txns, _ = normalize(
        result(
            make_raw(row_index=1, amount_raw="1800.00", description_raw="RENT"),
            make_raw(row_index=2, amount_raw="-45.10", description_raw="SHELL"),
        ),
        AccountType.CHECKING,
    )
    assert [t.amount_cents for t in txns] == [180000, -4510]
    assert [t.direction for t in txns] == [Direction.INFLOW, Direction.OUTFLOW]
    assert txns[0].posted_date == date(2026, 1, 5)


def test_debit_credit_columns_signed() -> None:
    txns, _ = normalize(
        result(
            make_raw(amount_raw=None, debit_raw="45.00", credit_raw=None, row_index=1),
            make_raw(amount_raw=None, debit_raw=None, credit_raw="10.00", row_index=2),
        ),
        AccountType.CHECKING,
    )
    assert [t.amount_cents for t in txns] == [-4500, 1000]


def test_type_column_forces_negative_for_unsigned_debit() -> None:
    txns, _ = normalize(result(make_raw(amount_raw="5.00", type_raw="DR")), AccountType.CHECKING)
    assert txns[0].amount_cents == -500


def _card_rows(charge: str, payment: str) -> list[object]:
    rows = [
        make_raw(row_index=i, amount_raw=charge, description_raw=f"STORE {i}") for i in range(1, 6)
    ]
    rows.append(
        make_raw(row_index=6, amount_raw=payment, description_raw="ONLINE PAYMENT THANK YOU")
    )
    return rows


def test_P12_card_charges_positive_are_inverted() -> None:
    txns, warns = normalize(result(*_card_rows("20.00", "-100.00")), AccountType.CREDIT_CARD)
    assert txns[0].amount_cents == -2000
    assert txns[5].amount_cents == 10000
    assert not any(w.code == "CARD_SIGN_ASSUMED" for w in warns)


def test_P13_card_charges_negative_not_inverted() -> None:
    txns, warns = normalize(result(*_card_rows("-20.00", "100.00")), AccountType.CREDIT_CARD)
    assert txns[0].amount_cents == -2000
    assert txns[5].amount_cents == 10000
    assert not any(w.code == "CARD_SIGN_ASSUMED" for w in warns)


def test_card_sign_ambiguous_assumes_charges_positive_with_warning() -> None:
    rows = [make_raw(row_index=i, amount_raw="20.00", description_raw=f"S{i}") for i in (1, 2)]
    txns, warns = normalize(result(*rows), AccountType.CREDIT_CARD)
    assert txns[0].amount_cents == -2000
    assert any(w.code == "CARD_SIGN_ASSUMED" for w in warns)


def test_card_with_split_columns_is_not_inverted() -> None:
    rows = [make_raw(amount_raw=None, debit_raw="20.00", credit_raw=None)]
    txns, warns = normalize(result(*rows), AccountType.CREDIT_CARD)
    assert txns[0].amount_cents == -2000
    assert warns == []


def test_ofx_account_type_mismatch_warns_but_user_wins() -> None:
    _, parsed = parse_statement(
        b"<OFX><CCSTMTRS><STMTTRN><DTPOSTED>20260105<TRNAMT>-1.00<NAME>X</STMTTRN></CCSTMTRS></OFX>",
        "a.ofx",
    )
    txns, warns = normalize(parsed, AccountType.CHECKING)
    assert txns[0].account_type is AccountType.CHECKING
    assert any(w.code == "ACCOUNT_TYPE_MISMATCH" for w in warns)
    assert txns[0].amount_cents == -100  # OFX signs are never inverted


def test_pending_from_status_or_description() -> None:
    txns, _ = normalize(
        result(
            make_raw(row_index=1, status_raw="Pending"),
            make_raw(row_index=2, description_raw="SHELL PENDING"),
            make_raw(row_index=3, status_raw="Posted"),
        ),
        AccountType.CHECKING,
    )
    assert [t.is_pending for t in txns] == [True, True, False]


def test_fingerprint_occurrence_counter_separates_identical_rows() -> None:
    txns, _ = normalize(
        result(
            *[
                make_raw(row_index=i, description_raw="COFFEE", amount_raw="-4.00")
                for i in (1, 2, 3)
            ]
        ),
        AccountType.CHECKING,
    )
    assert len({t.fingerprint for t in txns}) == 3
    again, _ = normalize(
        result(
            *[
                make_raw(row_index=i, description_raw="COFFEE", amount_raw="-4.00")
                for i in (1, 2, 3)
            ]
        ),
        AccountType.CHECKING,
    )
    assert [t.fingerprint for t in again] == [t.fingerprint for t in txns]
    assert txns[0].fingerprint == make_fingerprint(
        AccountType.CHECKING, date(2026, 1, 5), -400, "COFFEE", 0
    )


def test_S09_long_description_truncated_to_512_with_warning() -> None:
    txns, warns = normalize(result(make_raw(description_raw="A" * 10_000)), AccountType.CHECKING)
    assert len(txns[0].description) == 512
    assert any(w.code == "DESCRIPTION_TRUNCATED" for w in warns)


def test_whitespace_collapsed_and_memo_kept() -> None:
    txns, _ = normalize(
        result(make_raw(description_raw="  A \t  B\n C ", memo_raw=" note   here ")),
        AccountType.CHECKING,
    )
    assert txns[0].description == "A B C"
    assert txns[0].memo == "note here"


def test_money_is_conserved() -> None:
    raws = [
        make_raw(row_index=i, amount_raw=a)
        for i, a in enumerate(["0.10", "0.20", "-1,234.56", "(3.33)"], 1)
    ]
    txns, _ = normalize(result(*raws), AccountType.CHECKING)
    assert sum(t.amount_cents for t in txns) == 10 + 20 - 123456 - 333


def test_unparseable_row_is_skipped_not_raised() -> None:
    txns, warns = normalize(
        result(make_raw(row_index=1, amount_raw="oops"), make_raw(row_index=2)),
        AccountType.CHECKING,
    )
    assert len(txns) == 1
    assert warns[0].code == "ROW_SKIPPED"
