"""
Unit tests for text normalization, noise stripping, and indicator flags.
"""

from app.brain.normalizer import normalize_description


def test_strip_prefix():
    norm = normalize_description("POS DEBIT ADOBE SYSTEMS 800-833-6687 CA")
    assert "POS DEBIT" not in norm.cleaned
    assert "ADOBE" in norm.tokens
    assert "800-833-6687" not in norm.cleaned


def test_strip_square_and_paypal_prefixes():
    norm1 = normalize_description("SQ *BLUE BOTTLE COFFEE SAN FRANCISCO CA")
    assert "SQ *" not in norm1.cleaned
    assert "BLUE" in norm1.tokens

    norm2 = normalize_description("PAYPAL *GITHUB INC 877-448-4820 CA")
    assert "PAYPAL *" not in norm2.cleaned
    assert "GITHUB" in norm2.tokens


def test_strip_card_masks():
    norm = normalize_description("UBER TRIP CARD 9921 SAN FRANCISCO CA")
    assert "CARD 9921" not in norm.cleaned
    assert "UBER" in norm.tokens


def test_refund_indicator_detection():
    norm = normalize_description("AMZN MKTPLACE REFUND ORDER 112-94819")
    assert norm.is_refund_flag is True


def test_transfer_indicator_detection():
    norm1 = normalize_description("AUTOPAY PAYMENT - THANK YOU")
    assert norm1.is_transfer_flag is True

    norm2 = normalize_description("TRANSFER TO SAVINGS ACCOUNT 1029")
    assert norm2.is_transfer_flag is True

    norm3 = normalize_description("ZELLE TRANSFER TO OWNER PERSONAL DRAW")
    assert norm3.is_transfer_flag is True


def test_income_indicator_detection():
    norm = normalize_description("CLIENT ACH DEPOSIT - ACME CORP INV-2024-08")
    assert norm.is_income_flag is True
