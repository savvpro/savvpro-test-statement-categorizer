"""Unit tests for description normalization."""

from app.brain.normalizer import normalize, strip_noise


def test_lowercases_and_drops_punctuation():
    assert normalize("UBER *TRIP HELP.UBER.COM") == "uber trip help.uber.com"


def test_drops_long_digit_runs():
    assert normalize("JOES CAFE 9921") == "joes cafe"
    assert normalize("WHOLE FOODS MKT 102") == "whole foods mkt"


def test_keeps_short_numbers():
    assert normalize("WALGREENS #4471 X2") == "walgreens x2"


def test_collapses_whitespace():
    assert normalize("ADOBE  CREATIVE   CLOUD") == "adobe creative cloud"


def test_empty_and_none_safe():
    assert normalize("") == ""
    assert normalize(None) == ""


def test_strip_noise_removes_card_terms():
    assert strip_noise("pos purchase github.com") == "github.com"


def test_strip_noise_word_boundaries():
    # "pmt" must not mangle "pmts" or "payment"
    assert "pmts" in strip_noise("amazon mktplace pmts")
    assert "payment" in strip_noise("payment to bob")


def test_strip_noise_keeps_transfer_words():
    # special-flow words must survive normalization for auditability
    assert "transfer" in normalize("TRANSFER TO SAVINGS")
