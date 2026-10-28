"""Brain behaviour, one test per landlord edge case (IDs from docs/plan/04)."""

from datetime import date

from app.domain.enums import AccountType, Category, Flag, Status
from tests.unit.brain.conftest import Run, txn

CARD = AccountType.CREDIT_CARD


def zelle_in(
    name: str, cents: int, *, row: int = 1, day: date = date(2026, 1, 3), memo: str | None = None
):
    return txn(
        f"ZELLE FROM {name}",
        cents,
        row=row,
        day=day,
        memo=memo,
        merchant_key=f"ZELLE {name}",
        channel="ZELLE",
        counterparty=name,
    )


def zelle_out(name: str, cents: int, *, row: int = 1, memo: str | None = None):
    return txn(
        f"ZELLE TO {name}",
        cents,
        row=row,
        memo=memo,
        merchant_key=f"ZELLE {name}",
        channel="ZELLE",
        counterparty=name,
    )


def test_D01_rent_with_memo_is_auto(run: Run) -> None:
    [d] = run(zelle_in("MARIA K LOPEZ", 185000, memo="rent march"))
    assert (d.status, d.category) == (Status.AUTO, Category.RENT)


def test_D02_monthly_tenant_without_memo_becomes_auto(run: Run) -> None:
    rows = [zelle_in("MARIA K LOPEZ", 185000, row=i, day=date(2026, i, 2)) for i in (1, 2, 3)]
    decisions = run(*rows)
    assert all(d.status is Status.AUTO and d.category is Category.RENT for d in decisions)
    assert all(Flag.RECURRING in d.flags for d in decisions)


def test_D03_single_unexplained_payment_needs_review(run: Run) -> None:
    [d] = run(zelle_in("ANDRE PHILLIPS", 140000))
    assert d.status is Status.NEEDS_REVIEW
    assert d.category is None
    assert d.suggestion is Category.RENT


def test_D04_security_deposit_is_not_income(run: Run) -> None:
    [d] = run(zelle_in("ANDRE PHILLIPS", 140000, memo="security deposit"))
    assert (d.status, d.category) == (Status.AUTO, Category.SECURITY_DEPOSIT_RECEIVED)


def test_D05_double_rent_payment_is_outlier(run: Run) -> None:
    rows = [zelle_in("MARIA K LOPEZ", 185000, row=i, day=date(2026, i, 2)) for i in (1, 2, 3)]
    big = zelle_in("MARIA K LOPEZ", 370000, row=4, day=date(2026, 3, 20))
    decisions = run(*rows, big)
    assert decisions[-1].status is Status.NEEDS_REVIEW
    assert Flag.AMOUNT_OUTLIER in decisions[-1].flags


def test_D07_deposit_returned(run: Run) -> None:
    [d] = run(zelle_out("TOM BAKER", -90000, memo="deposit return"))
    assert (d.status, d.category) == (Status.AUTO, Category.SECURITY_DEPOSIT_RETURNED)


def test_D08_returned_tenant_payment_reverses_rent(run: Run) -> None:
    [d] = run(txn("RETURNED ITEM ZELLE MARIA K LOPEZ", -185000, channel=None))
    assert (d.status, d.category) == (Status.AUTO, Category.RENT)
    assert d.is_refund
    assert Flag.RENT_REVERSAL in d.flags


def test_D09_nsf_fee_is_bank_fee(run: Run) -> None:
    [d] = run(txn("RETURNED ITEM FEE", -3500, channel=None))
    assert (d.status, d.category) == (Status.AUTO, Category.OTHER_EXPENSE)


def test_D10_small_hardware_purchase_is_repair(run: Run) -> None:
    [d] = run(txn("HOME DEPOT #4410", -8412, merchant_key="HOME DEPOT", account=CARD))
    assert (d.status, d.category) == (Status.AUTO, Category.REPAIRS)


def test_D11_large_hardware_purchase_may_be_improvement(run: Run) -> None:
    [d] = run(txn("HOME DEPOT #4410", -341200, merchant_key="HOME DEPOT", account=CARD))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.POSSIBLE_CAPITAL_IMPROVEMENT in d.flags
    assert d.suggestion is Category.REPAIRS


def test_D12_refund_reduces_repairs_not_income(run: Run) -> None:
    [d] = run(txn("HOME DEPOT RETURN", 4210, merchant_key="HOME DEPOT", account=CARD))
    assert (d.status, d.category) == (Status.AUTO, Category.REPAIRS)
    assert d.is_refund


def test_D13_amazon_is_mixed_use(run: Run) -> None:
    [d] = run(txn("AMZN MKTP US*2K4T81", -5620, merchant_key="AMAZON", account=CARD))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.MIXED_USE_MERCHANT in d.flags


def test_D15_mortgage_needs_split(run: Run) -> None:
    [d] = run(
        txn(
            "GRANITE HOME LENDING MTG PMT",
            -191244,
            merchant_key="GRANITE HOME LENDING",
            channel="ACH",
        )
    )
    assert d.status is Status.NEEDS_REVIEW
    assert d.suggestion is Category.MORTGAGE_INTEREST
    assert Flag.MORTGAGE_SPLIT_REQUIRED in d.flags


def test_D16_property_tax(run: Run) -> None:
    [d] = run(txn("CEDAR COUNTY TREASURER", -221000, channel="ACH"))
    assert (d.status, d.category) == (Status.AUTO, Category.TAXES)


def test_D24_payment_to_individual_needs_review(run: Run) -> None:
    [d] = run(zelle_out("JAMES CARTER", -45000))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.PAYMENT_TO_INDIVIDUAL in d.flags


def test_D25_contractor_over_600_flags_1099(run: Run) -> None:
    decisions = run(
        zelle_out("JAMES CARTER", -45000, row=1), zelle_out("JAMES CARTER", -30000, row=2)
    )
    assert all(Flag.POSSIBLE_1099 in d.flags for d in decisions)


def test_D26_check_without_payee(run: Run) -> None:
    [d] = run(txn("CHECK #1042", -40000, merchant_key="CHECK", channel="CHECK"))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.CHECK_NO_PAYEE in d.flags


def test_D27_transfer_is_not_counted(run: Run) -> None:
    [d] = run(txn("ONLINE TRANSFER TO SAVINGS XXXX4421", -500000, channel=None))
    assert (d.status, d.category) == (Status.AUTO, Category.TRANSFER)


def test_D30_card_payment_thank_you(run: Run) -> None:
    [d] = run(txn("PAYMENT THANK YOU", 120000, account=CARD, channel=None))
    assert (d.status, d.category) == (Status.AUTO, Category.CARD_PAYMENT)


def test_D33_gas_station_needs_review(run: Run) -> None:
    [d] = run(txn("SHELL OIL 5741", -4520, merchant_key="SHELL OIL", account=CARD))
    assert d.status is Status.NEEDS_REVIEW
    assert d.suggestion is Category.AUTO_TRAVEL


def test_D34_unknown_merchant(run: Run) -> None:
    [d] = run(txn("SQ *JOES CAFE 9921", -1250, merchant_key="JOES CAFE", account=CARD))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.UNKNOWN_MERCHANT in d.flags


def test_D35_typo_merchant_found_by_fuzzy_but_asks(run: Run) -> None:
    [d] = run(txn("HOEM DEPOT", -2300, merchant_key="HOEM DEPOT", account=CARD))
    assert d.suggestion is Category.REPAIRS
    assert d.status is Status.NEEDS_REVIEW


def test_D36_inflow_from_utility_without_refund_word(run: Run) -> None:
    [d] = run(txn("CITY WATER AND SEWER", 4100, channel="ACH"))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.DIRECTION_CONFLICT in d.flags


def test_D39_identical_purchases_are_not_duplicates(run: Run) -> None:
    a = txn("HOME DEPOT", -1999, row=1, fingerprint="a", account=CARD)
    b = txn("HOME DEPOT", -1999, row=2, fingerprint="b", account=CARD)
    assert all(d.status is Status.AUTO for d in run(a, b))


def test_D42_memory_overrides_unknown(run: Run) -> None:
    [d] = run(
        txn("SQ *JOES CAFE", -1250, merchant_key="JOES CAFE"),
        memory={"JOES CAFE": Category.PERSONAL},
    )
    assert (d.status, d.category) == (Status.AUTO, Category.PERSONAL)


def test_P19_duplicate_fitid(run: Run) -> None:
    decisions = run(
        txn("HOME DEPOT", -1999, row=1, fitid="X1"), txn("HOME DEPOT", -1999, row=2, fitid="X1")
    )
    assert decisions[1].status is Status.DUPLICATE
    assert decisions[1].duplicate_of_row == 1


def test_P23_pending_copy_is_duplicate(run: Run) -> None:
    posted = txn("HOME DEPOT", -1999, row=1, day=date(2026, 3, 5))
    pending = txn("HOME DEPOT", -1999, row=2, day=date(2026, 3, 4), pending=True)
    assert run(posted, pending)[1].status is Status.DUPLICATE


def test_D41_prior_upload_is_duplicate(run: Run) -> None:
    [d] = run(txn("HOME DEPOT", -1999, fingerprint="seen"), prior_fingerprints={"seen": "tx-1"})
    assert d.status is Status.DUPLICATE
    assert Flag.DUPLICATE_PRIOR_UPLOAD in d.flags


def test_P24_zero_amount_needs_review(run: Run) -> None:
    [d] = run(txn("HOME DEPOT", 0))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.ZERO_AMOUNT in d.flags


def test_auto_decisions_always_have_category_and_no_blocking_flag(run: Run) -> None:
    from app.domain.enums import NON_BLOCKING_FLAGS

    samples = [
        txn("HOME DEPOT", -8412),
        txn("AMAZON", -100),
        txn("CEDAR COUNTY TREASURER", -100),
        zelle_in("MARIA K LOPEZ", 1000, memo="rent"),
        txn("XYZ", -5),
    ]
    for d in run(*samples):
        if d.status is Status.AUTO:
            assert d.category is not None
            assert not (d.flags - NON_BLOCKING_FLAGS)
        else:
            assert d.category is None


def test_determinism(run: Run) -> None:
    rows = [zelle_in("MARIA K LOPEZ", 185000, row=i, day=date(2026, i, 2)) for i in (1, 2, 3)]
    assert run(*rows) == run(*rows)


def test_EC1_water_heater_is_not_a_utility_bill(run: Run) -> None:
    for text in (
        "NEW WATER HEATER INSTALL",
        "WATER DAMAGE RESTORATION SERVPRO",
        "WATER BOTTLE SUPPLY",
    ):
        [d] = run(txn(text, -150000, channel="CARD"))
        assert d.status is Status.NEEDS_REVIEW, text


def test_EC1_real_water_bill_still_auto(run: Run) -> None:
    [d] = run(txn("CITY WATER AND SEWER DEPT", -9240, channel="ACH"))
    assert (d.status, d.category) == (Status.AUTO, Category.UTILITIES)


def test_EC2_parents_rent_help_is_not_tenant_rent(run: Run) -> None:
    [d] = run(txn("DEPOSIT PARENT'S RENT HELP", 100000, channel="ACH"))
    assert d.status is Status.NEEDS_REVIEW


def test_EC3_refund_larger_than_purchase_needs_review(run: Run) -> None:
    buy = txn("HOME DEPOT", -5000, row=1, merchant_key="HOME DEPOT", day=date(2026, 1, 2))
    back = txn("HOME DEPOT RETURN", 9000, row=2, merchant_key="HOME DEPOT", day=date(2026, 3, 2))
    decisions = run(buy, back)
    assert decisions[1].status is Status.NEEDS_REVIEW
    assert Flag.REFUND_EXCEEDS_PURCHASE in decisions[1].flags


def test_EC5_returned_rent_variants_reverse_rent(run: Run) -> None:
    for text in ("NSF RETURN RENT", "RENT REVERSAL"):
        [d] = run(txn(text, -95000, channel=None))
        assert (d.status, d.category) == (Status.AUTO, Category.RENT), text
        assert Flag.RENT_REVERSAL in d.flags


def test_EC5_returned_check_fee_is_a_bank_fee(run: Run) -> None:
    [d] = run(txn("RETURNED CHECK FEE", -3000, channel=None))
    assert (d.status, d.category) == (Status.AUTO, Category.OTHER_EXPENSE)


def test_EC6_card_payment_variants_from_checking(run: Run) -> None:
    for text in ("PAYMENT TO CHASE CARD", "CHASE CREDIT CRD AUTOPAY"):
        [d] = run(txn(text, -50000, channel=None))
        assert (d.status, d.category) == (Status.AUTO, Category.CARD_PAYMENT), text


def test_EC7_amzn_marketplace_is_mixed_use(run: Run) -> None:
    [d] = run(txn("AMZN MKTP US", -2000, merchant_key="AMZN MKTP US", account=CARD))
    assert d.status is Status.NEEDS_REVIEW
    assert Flag.MIXED_USE_MERCHANT in d.flags
