from datetime import date

from app.engine.brain import CategorizationBrain
from app.models.transaction import RawTransaction, TransactionType


def make_raw_tx(desc: str, amount: float = 50.0, tx_type: TransactionType = TransactionType.DEBIT, tx_id: str = "tx_1"):
    return RawTransaction(
        id=tx_id,
        line_number=1,
        date=date(2024, 3, 1),
        description=desc,
        amount=amount,
        transaction_type=tx_type,
    )


def test_exact_merchant_match():
    brain = CategorizationBrain()
    tx = make_raw_tx("GITHUB")
    results = brain.categorize_batch([tx])
    assert len(results) == 1
    assert results[0].category == "Software & Subscriptions"
    assert results[0].confidence >= 0.95
    assert not results[0].needs_review


def test_pattern_rule_match():
    brain = CategorizationBrain()
    tx = make_raw_tx("CLOUDFLARE SAN FRANCISCO CA")
    results = brain.categorize_batch([tx])
    assert len(results) == 1
    assert results[0].category == "Cloud & Infrastructure"
    assert results[0].confidence >= 0.90
    assert not results[0].needs_review


def test_fuzzy_match_rapidfuzz():
    brain = CategorizationBrain()
    # Misspelled canonical merchant that does not trigger strict regex
    tx = make_raw_tx("JETBRAINSS CLOUD DEV")
    results = brain.categorize_batch([tx])
    assert len(results) == 1
    assert results[0].category == "Software & Subscriptions"
    assert "Fuzzy match" in results[0].reason
    assert results[0].confidence >= 0.75
    assert not results[0].needs_review


def test_unknown_merchant_needs_review():
    brain = CategorizationBrain()
    # Unfamiliar local vendor
    tx = make_raw_tx("RANDOM ACME SUPPLIER 9912")
    results = brain.categorize_batch([tx])
    assert len(results) == 1
    assert results[0].category == "Needs Review"
    assert results[0].needs_review is True
    assert results[0].confidence < 0.75
    assert "manual tax classification" in results[0].reason.lower()
