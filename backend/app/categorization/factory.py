"""Composition root for the engine: the single place where the chain is wired."""
from ..config import Settings
from ..learning.repository import MerchantRuleRepository
from .classifiers import (
    CreditClassifier,
    DuplicateClassifier,
    FallbackClassifier,
    KeywordClassifier,
    LearnedRuleClassifier,
    MixedUseClassifier,
    RefundClassifier,
    TransferClassifier,
)
from .engine import CategorizationEngine, ConfidencePolicy
from .post_processors import LargeAmountFlagger, RecurringDetector
from .rulebook import RuleBook


def build_engine(settings: Settings, rules: RuleBook, learned: MerchantRuleRepository) -> CategorizationEngine:
    return CategorizationEngine(
        classifiers=[
            DuplicateClassifier(),
            LearnedRuleClassifier(learned),
            TransferClassifier(rules),
            RefundClassifier(rules),
            CreditClassifier(rules),
            MixedUseClassifier(rules),
            KeywordClassifier(rules, settings.ambiguity_margin),
            FallbackClassifier(),
        ],
        policy=ConfidencePolicy(settings.confidence_threshold),
        post_processors=[LargeAmountFlagger(settings.large_amount), RecurringDetector()],
    )
