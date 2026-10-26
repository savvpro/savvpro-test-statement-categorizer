import os
import tempfile
from datetime import date

from app.engine.brain import CategorizationBrain
from app.models.rule import RuleCreateRequest
from app.models.transaction import RawTransaction, TransactionType
from app.services.rule_store import RuleStore


def test_user_rule_persistence_and_precedence():
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "test_rules.json")
        store = RuleStore(storage_path=temp_file)

        # Initially empty
        assert len(store.get_all()) == 0

        # Add a custom rule for an unknown merchant
        rule = store.add_rule(
            RuleCreateRequest(
                pattern="BOB'S DEV WORKSHOP",
                category="Hardware & Office Equipment",
                notes="Custom workstation repair",
            )
        )
        assert rule.category == "Hardware & Office Equipment"
        assert len(store.get_all()) == 1

        # Brain uses this rule and categorizes it with 1.0 confidence
        brain = CategorizationBrain(custom_rules=store.get_all())
        tx = RawTransaction(
            id="tx_1",
            line_number=1,
            date=date(2024, 3, 1),
            description="BOB'S DEV WORKSHOP #409",
            amount=250.00,
            transaction_type=TransactionType.DEBIT,
        )
        results = brain.categorize_batch([tx])
        assert results[0].category == "Hardware & Office Equipment"
        assert results[0].confidence == 1.0
        assert results[0].user_overridden is True
        assert "User custom rule" in results[0].reason


def test_delete_rule():
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = os.path.join(tmpdir, "test_rules.json")
        store = RuleStore(storage_path=temp_file)
        rule = store.add_rule(
            RuleCreateRequest(pattern="TEST MERCHANT", category="Software & Subscriptions")
        )
        assert len(store.get_all()) == 1
        deleted = store.delete_rule(rule.id)
        assert deleted is True
        assert len(store.get_all()) == 0
