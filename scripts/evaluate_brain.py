"""Evaluate the brain against the labelled fake statements in samples/.

Runs the real pipeline (parse → normalize → categorize) without a database and reports:
  auto_precision  correct AUTO decisions / all AUTO decisions        (gate: 1.00)
  review_recall   rows labelled needs_review that the brain sent to review (gate: 1.00)
  coverage        AUTO rows / non-duplicate rows                       (reported)

Usage: cd backend && uv run python ../scripts/evaluate_brain.py [--gate] [--json] [--verbose]
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.brain.context import BrainContext  # noqa: E402
from app.brain.engine import categorize  # noqa: E402
from app.brain.rules import DEFAULT_RULES_DIR, load_ruleset  # noqa: E402
from app.domain.enums import AccountType, Status  # noqa: E402
from app.ingest import parse_statement  # noqa: E402
from app.normalize.normalizer import normalize  # noqa: E402

SAMPLES = ROOT / "samples"
# Files evaluated as a second upload after another file (cross-upload duplicate detection).
PRIOR_UPLOADS = {"checking_overlap_feb_apr.csv": "checking_q1_2026.csv"}


def fingerprints_of(path: Path) -> dict[str, str]:
    _, parsed = parse_statement(path.read_bytes(), path.name)
    txns, _ = normalize(parsed, account_type_for(path))
    return {t.fingerprint: f"{path.name}#{t.row_index}" for t in txns}


@dataclass
class Score:
    auto_total: int = 0
    auto_correct: int = 0
    review_expected: int = 0
    review_caught: int = 0
    non_duplicate: int = 0
    misses: list[str] = field(default_factory=list)


def account_type_for(path: Path) -> AccountType:
    return AccountType.CREDIT_CARD if path.name.startswith("card") else AccountType.CHECKING


def evaluate_file(path: Path, labels: list[dict[str, object]], score: Score) -> None:
    rules = load_ruleset(DEFAULT_RULES_DIR)
    _, parsed = parse_statement(path.read_bytes(), path.name)
    txns, _ = normalize(parsed, account_type_for(path))
    prior = PRIOR_UPLOADS.get(path.name)
    ctx = BrainContext(rules=rules, prior_fingerprints=fingerprints_of(SAMPLES / prior) if prior else {})
    decisions = {t.row_index: d for t, d in zip(txns, categorize(txns, ctx), strict=True)}
    by_row = {t.row_index: t for t in txns}

    for label in labels:
        row = int(str(label["row_index"]))
        decision = decisions.get(row)
        if decision is None:
            continue  # row intentionally skipped by the parser (malformed / summary)
        expected_status = Status(str(label["status"]))
        expected_cat = label.get("category")
        where = f"{path.name}#{row} {by_row[row].description[:40]!r}"

        if decision.status is not Status.DUPLICATE:
            score.non_duplicate += 1
        if decision.status is Status.AUTO:
            score.auto_total += 1
            if expected_status is Status.AUTO and decision.category == expected_cat:
                score.auto_correct += 1
            else:
                score.misses.append(
                    f"WRONG AUTO {where}: got {decision.category}, expected "
                    f"{expected_status.value}/{expected_cat}"
                )
        if expected_status is Status.NEEDS_REVIEW:
            score.review_expected += 1
            if decision.status is Status.NEEDS_REVIEW:
                score.review_caught += 1
            else:
                score.misses.append(f"MISSED REVIEW {where}: got {decision.status.value}/{decision.category}")
        elif expected_status is Status.AUTO and decision.status is Status.NEEDS_REVIEW:
            score.misses.append(
                f"OVER-CAUTIOUS {where}: expected {expected_cat}, flags={sorted(decision.flags)}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", action="store_true", help="exit 1 if a gate fails")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="list over-cautious rows too")
    args = parser.parse_args()

    score = Score()
    for expected in sorted(SAMPLES.glob("*.expected.json")):
        sample = expected.with_name(expected.name.removesuffix(".expected.json"))
        evaluate_file(sample, json.loads(expected.read_text(encoding="utf-8")), score)

    precision = score.auto_correct / score.auto_total if score.auto_total else 1.0
    recall = score.review_caught / score.review_expected if score.review_expected else 1.0
    coverage = score.auto_total / score.non_duplicate if score.non_duplicate else 0.0
    metrics = {
        "auto_precision": round(precision, 4),
        "review_recall": round(recall, 4),
        "coverage": round(coverage, 4),
        "auto_rows": score.auto_total,
        "rows": score.non_duplicate,
    }
    hard = [m for m in score.misses if not m.startswith("OVER-CAUTIOUS")]
    soft = [m for m in score.misses if m.startswith("OVER-CAUTIOUS")]

    if args.json:
        print(json.dumps({**metrics, "failures": hard}, indent=2))
    else:
        print("| Metric | Value | Gate |\n|---|---|---|")
        print(f"| Auto precision | {precision:.1%} | 100% |")
        print(f"| Review recall | {recall:.1%} | 100% |")
        print(f"| Coverage (auto-sorted) | {coverage:.1%} | report |")
        print(f"| Rows evaluated | {score.non_duplicate} | |")
        for line in hard + (soft if args.verbose else []):
            print(f"- {line}")
        if soft and not args.verbose:
            print(f"- {len(soft)} over-cautious rows (asked when the label says auto); use --verbose")

    passed = precision == 1.0 and recall == 1.0
    return 0 if passed or not args.gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
