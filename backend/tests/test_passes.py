from copy import deepcopy

from app.engine import categorize_all
from app.schemas import NEEDS_REVIEW


def test_own_account_transfer_not_spending(rows):
    transfers = [t for t in rows if "transfer" in t.flags]
    assert [t.id for t in transfers] == [11, 49]
    assert all(t.category == "Transfer" and not t.needs_review for t in transfers)


def test_refunds_are_not_income(rows):
    refunds = [t for t in rows if t.category == "Refund"]
    assert {t.description for t in refunds} == {
        "DARAZ.PK REFUND ORD 7782316",
        "CAREEM *TRIP REFUND",
    }
    assert all(t.amount > 0 and not t.needs_review for t in refunds)


def test_refund_links_to_original_purchase(by_desc):
    assert "full refund of row 18" in by_desc["CAREEM *TRIP REFUND"].reason
    assert "partial refund against row 14" in by_desc["DARAZ.PK REFUND ORD 7782316"].reason


def test_failed_atm_and_reversal_pair_net_zero(by_desc):
    failed, reversal = by_desc["ATM CASH WDL FAILED TXN"], by_desc["REVERSAL - FAILED ATM TXN"]
    for tx in (failed, reversal):
        assert tx.category == "Transfer" and "reversal" in tx.flags
        assert "net 0" in tx.reason
    assert failed.amount + reversal.amount == 0


def test_unpaired_failed_row_stays_in_review(rows):
    subset = deepcopy([t for t in rows if t.id != 59])
    categorize_all(subset)
    failed = next(t for t in subset if "FAILED" in t.normalized)
    assert failed.category == NEEDS_REVIEW and "reversal" not in failed.flags


def test_duplicate_flags_later_row_only(rows):
    first, second = rows[19], rows[20]
    assert first.normalized == second.normalized and first.amount == second.amount
    assert "duplicate" not in first.flags and not first.needs_review
    assert "duplicate" in second.flags and second.needs_review
    assert "row 20" in second.reason
    assert second.category == "Food"


def test_only_one_duplicate_in_sample(rows):
    assert [t.id for t in rows if "duplicate" in t.flags] == [21]


def test_recurring_monthly_charges_are_not_duplicates(by_desc, rows):
    careem = [t for t in rows if t.description == "CAREEM *TRIP LHR"]
    assert len(careem) == 4 and not any("duplicate" in t.flags for t in careem)
