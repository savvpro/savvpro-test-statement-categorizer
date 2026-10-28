"""Inputs the brain needs besides the transactions themselves. Built by the service layer."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.brain.rules import RuleSet
from app.domain.enums import Category


@dataclass(frozen=True, slots=True)
class BrainSettings:
    auto_threshold: float = 0.85
    margin_threshold: float = 0.20
    de_minimis_cents: int = 250_000
    contractor_1099_cents: int = 60_000
    fuzzy_min_ratio: int = 88


@dataclass(frozen=True, slots=True)
class BrainContext:
    rules: RuleSet
    settings: BrainSettings = field(default_factory=BrainSettings)
    # merchant_key -> category the user chose with "remember"
    memory: Mapping[str, Category] = field(default_factory=dict)
    # fingerprint -> id of an existing transaction from an earlier upload
    prior_fingerprints: Mapping[str, str] = field(default_factory=dict)
    # counterparty -> cents already paid in earlier statements (for the 1099 flag)
    ytd_by_counterparty: Mapping[str, int] = field(default_factory=dict)
