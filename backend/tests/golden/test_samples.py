"""Golden gate: every samples/*.expected.json label is checked against the real pipeline."""

import json
from pathlib import Path

import pytest

from app.brain.context import BrainContext
from app.brain.engine import categorize
from app.brain.rules import DEFAULT_RULES_DIR, load_ruleset
from app.domain.enums import AccountType, Status
from app.domain.models import Transaction
from app.ingest import parse_statement
from app.normalize.normalizer import normalize

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
# Files evaluated as a second upload after another file (cross-upload duplicate detection).
PRIOR_UPLOADS = {"checking_overlap_feb_apr.csv": "checking_q1_2026.csv"}
EXPECTED = sorted(SAMPLES.glob("*.expected.json"))


def _normalized(path: Path) -> list[Transaction]:
    _, parsed = parse_statement(path.read_bytes(), path.name)
    account = AccountType.CREDIT_CARD if path.name.startswith("card") else AccountType.CHECKING
    return normalize(parsed, account)[0]


def _evaluate(
    sample: Path, labels: list[dict[str, object]]
) -> tuple[int, int, int, int, list[str]]:
    txns = _normalized(sample)
    prior = PRIOR_UPLOADS.get(sample.name)
    fps = (
        {t.fingerprint: f"{prior}#{t.row_index}" for t in _normalized(SAMPLES / prior)}
        if prior
        else {}
    )
    ctx = BrainContext(rules=load_ruleset(DEFAULT_RULES_DIR), prior_fingerprints=fps)
    decisions = {t.row_index: d for t, d in zip(txns, categorize(txns, ctx), strict=True)}
    auto = auto_ok = review = review_ok = 0
    misses: list[str] = []
    for label in labels:
        row = int(str(label["row_index"]))
        dec = decisions.get(row)
        if dec is None:
            continue
        want = Status(str(label["status"]))
        cat = label.get("category")
        where = f"{sample.name}#{row}"
        if dec.status is Status.AUTO:
            auto += 1
            if want is Status.AUTO and dec.category == cat:
                auto_ok += 1
            else:
                misses.append(f"WRONG AUTO {where}: got {dec.category}, expected {want}/{cat}")
        if want is Status.NEEDS_REVIEW:
            review += 1
            if dec.status is Status.NEEDS_REVIEW:
                review_ok += 1
            else:
                misses.append(f"MISSED REVIEW {where}: got {dec.status}/{dec.category}")
    return auto, auto_ok, review, review_ok, misses


def test_samples_exist() -> None:
    assert len(EXPECTED) >= 5


@pytest.mark.parametrize("expected", EXPECTED, ids=lambda p: p.name)
def test_sample_has_perfect_auto_precision_and_review_recall(expected: Path) -> None:
    sample = expected.with_name(expected.name.removesuffix(".expected.json"))
    labels = json.loads(expected.read_text(encoding="utf-8"))
    auto, auto_ok, review, review_ok, misses = _evaluate(sample, labels)
    assert auto_ok == auto, "\n".join(misses)
    assert review_ok == review, "\n".join(misses)
    assert auto > 0 or review > 0
