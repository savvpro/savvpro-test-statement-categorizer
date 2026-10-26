from app.brain.models import AccountType, TxnStatus
from tests.brain.helpers import decide, one, row

CARD = AccountType.credit_card
CHECKING = AccountType.checking


def test_refund_linked_to_original_purchase() -> None:
    purchase, refund = decide(
        row("BEST BUY 00123", "-129.99", 21, 1),
        row("BEST BUY 00123 RETURN", "129.99", 1, 2),
        account=CARD,
    )

    assert (purchase.category_id, refund.category_id) == ("equipment", "refund")
    assert refund.status is TxnStatus.auto
    assert refund.linked_row_index == 0
    assert "reverses row 0 (equipment); nets against that expense" in refund.reasons


def test_partial_refund_links() -> None:
    d = decide(row("FIGMA MONTHLY", "-45.00", 4, 1), row("FIGMA REFUND", "15.00", 10, 1))[1]

    assert d.linked_row_index == 0


def test_unlinked_refund_is_still_refund_not_income() -> None:
    d = one("FAKE GADGETS REFUND", "50.00", account=CARD)

    assert (d.status, d.category_id) == (TxnStatus.auto, "refund")
    assert d.linked_row_index is None
    assert any("still a refund, not income" in r for r in d.reasons)


def test_refund_outside_window_or_too_large_not_linked() -> None:
    late = decide(row("BEST BUY", "-50.00", 1, 1), row("BEST BUY RETURN", "50.00", 15, 4))
    big = decide(row("BEST BUY", "-50.00", 1, 1), row("BEST BUY RETURN", "80.00", 5, 1))
    other = decide(row("BEST BUY", "-50.00", 1, 1), row("STAPLES RETURN", "50.00", 5, 1))

    assert late[1].linked_row_index is None  # 104 days later
    assert big[1].linked_row_index is None  # more than was spent
    assert other[1].linked_row_index is None  # different merchant


def test_each_purchase_links_to_one_refund() -> None:
    decisions = decide(
        row("FAKE SHOP", "-20.00", 1),
        row("FAKE SHOP REFUND", "20.00", 2),
        row("FAKE SHOP REFUND", "20.00", 3),
    )

    assert [d.linked_row_index for d in decisions] == [None, 0, None]


def test_chargeback_always_review_and_linked() -> None:
    decisions = decide(
        row("KLARO PRINT SHOP", "-60.00", 14, 2),
        row("DISPUTE CREDIT KLARO PRINT SHOP", "60.00", 1, 3),
        account=CARD,
        user_rules={"DISPUTE CREDIT KLARO PRINT SHOP": "refund"},
    )
    chargeback = decisions[1]

    assert chargeback.status is TxnStatus.needs_review
    assert "chargeback" in chargeback.flags
    assert chargeback.suggested_category_id == "refund"
    assert chargeback.linked_row_index == 0


def test_duplicate_row_flagged_not_dropped() -> None:
    decisions = decide(
        row("UBER *TRIP", "-31.05", 9),
        row("UBER *TRIP", "-31.05", 9),
        row("UBER *TRIP", "-31.05", 10),  # different day: not a duplicate
        account=CARD,
    )

    assert len(decisions) == 3
    first, second, third = decisions
    assert (first.status, first.category_id) == (TxnStatus.auto, "travel")
    assert second.status is TxnStatus.needs_review
    assert second.flags == ["possible_duplicate"]
    assert second.suggested_category_id == "travel"
    assert second.reasons[0].startswith("possible duplicate of row 0")
    assert third.status is TxnStatus.auto


def test_pending_flag() -> None:
    d = decide(row("UBER *TRIP", "-24.60", pending=True), account=CARD)[0]

    assert "pending" in d.flags
    assert d.category_id == "travel"


def test_card_payment_on_both_sides_is_non_operating() -> None:
    checking = one("CARD SERVICES AUTOPAY PAYMENT", "-1520.44", account=CHECKING)
    card = one("PAYMENT THANK YOU", "1520.44", account=CARD)
    card_plain = one("ONLINE PAYMENT", "300.00", account=CARD)

    assert checking.category_id == card.category_id == card_plain.category_id == "card_payment"
    # A bill paid from checking is not a card payment.
    assert one("VERIZON WIRELESS PAYMENT", "-65.00").category_id == "phone_internet"
    assert one("ONLINE PAYMENT", "-300.00", account=CHECKING).category_id != "card_payment"


def test_own_account_transfers() -> None:
    assert one("ONLINE TRANSFER TO SAVINGS XXXX5521", "-1000.00").category_id == "transfer"
    assert one("TRANSFER FROM CHECKING", "500.00").category_id == "transfer"
    # A payout that happens to say TRANSFER is not an own-account transfer.
    assert one("STRIPE TRANSFER ST-8F3K", "1845.30").category_id == "client_income"


def test_platform_fees_vs_payouts() -> None:
    assert one("UPWORK *SERVICE FEE", "-48.00", account=CARD).category_id == "platform_fees"
    assert one("PAYPAL *FIVERR SERVICE FEE", "-5.50", account=CARD).category_id == "platform_fees"
    assert one("UPWORK WITHDRAWAL 7731042", "960.00").category_id == "client_income"
    assert one("FIVERR PAYOUT", "300.00").category_id == "client_income"


def test_estimated_tax_is_tax_payment() -> None:
    d = one("IRS USATAXPYMT EST TAX 2025 Q4", "-1800.00")

    assert (d.status, d.category_id) == (TxnStatus.auto, "tax_payment")


def test_interest_earned_vs_charged() -> None:
    assert one("INTEREST PAID", "1.84").category_id == "interest_income"
    assert one("INTEREST CHARGE ON PURCHASES", "-12.30", account=CARD).category_id == "bank_fees"


def test_foreign_fee_and_foreign_merchant() -> None:
    fee, merchant = decide(
        row("FOREIGN TRANSACTION FEE", "-2.62"),
        row("HOTEL LISBOA CENTRO PT", "-180.00"),
        account=CARD,
    )

    assert fee.category_id == "bank_fees"
    assert merchant.category_id == "travel"  # foreign merchant still categorized


def test_uber_trip_vs_eats() -> None:
    trip, eats = decide(row("UBER *TRIP HELP.UBER.COM", "-18.72"), row("UBER *EATS", "-26.40"))

    assert trip.category_id == "travel"
    assert eats.category_id == "meals"


def test_client_invoice_deposit_vs_unknown_deposit() -> None:
    invoice = one("ACH DEPOSIT HARBOR & PINE CO INV-2026-001", "3200.00")
    unknown = one("ACH DEPOSIT ORCHID LANE", "1200.00")

    assert (invoice.status, invoice.category_id) == (TxnStatus.auto, "client_income")
    assert unknown.status is TxnStatus.needs_review
    assert unknown.suggested_category_id == "client_income"
