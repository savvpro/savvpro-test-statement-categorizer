"""Score the engine against the hand-labelled golden set in samples/labels/.

Metrics:
- auto-precision: share of auto-assigned rows whose category matches the label. A row labelled
  needs_review that the engine auto-assigns counts as wrong (a confident guess where a human
  said "ask").
- review rate: share of all rows sent to needs_review.
- coverage: share of rows with a real label (not needs_review) that were auto-assigned correctly.
- direction errors: wrong auto rows that swap income and expense. Must be zero.

Usage: python scripts/evaluate.py
"""

import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Run as a plain script from anywhere: make `app` importable without relying on the install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.brain.engine import categorize
from app.brain.models import AccountType, CategoryKind, TxnStatus
from app.brain.taxonomy import NEEDS_REVIEW, get_category
from app.parsing import parse_statement

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
ACCOUNTS = {
    "checking_simple.csv": AccountType.checking,
    "credit_card.csv": AccountType.credit_card,
    "bank_messy.csv": AccountType.checking,
    "credit_card.xlsx": AccountType.credit_card,
}


@dataclass
class FileScore:
    name: str
    rows: int = 0
    auto: int = 0
    auto_correct: int = 0
    review: int = 0
    labelled: int = 0  # rows whose label is a real category

    @property
    def precision(self) -> float:
        return self.auto_correct / self.auto if self.auto else 1.0


@dataclass
class Report:
    files: list[FileScore] = field(default_factory=list)
    wrong: list[tuple[str, int, str, str, str]] = field(default_factory=list)
    direction_errors: int = 0

    def total(self, attr: str) -> int:
        return sum(getattr(f, attr) for f in self.files)

    @property
    def precision(self) -> float:
        auto = self.total("auto")
        return self.total("auto_correct") / auto if auto else 1.0

    @property
    def review_rate(self) -> float:
        return self.total("review") / self.total("rows")

    @property
    def coverage(self) -> float:
        return self.total("auto_correct") / self.total("labelled")


def _kind(category_id: str) -> CategoryKind:
    return get_category(category_id).kind


def _flips_direction(expected: str, got: str) -> bool:
    kinds = {_kind(expected), _kind(got)}
    return kinds == {CategoryKind.income, CategoryKind.expense}


def load_labels(samples: Path) -> dict[str, dict[int, str]]:
    labels: dict[str, dict[int, str]] = {}
    for path in sorted((samples / "labels").glob("*.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                labels.setdefault(row["file"], {})[int(row["row_index"])] = row["expected_category"]
    return labels


def evaluate(samples: Path = SAMPLES) -> Report:
    report = Report()
    for name, expected_by_row in load_labels(samples).items():
        result = parse_statement((samples / name).read_bytes(), name, ACCOUNTS[name])
        decisions = categorize(result.rows, ACCOUNTS[name])
        if len(expected_by_row) != len(result.rows):
            raise ValueError(f"{name}: {len(expected_by_row)} labels for {len(result.rows)} rows")

        score = FileScore(name)
        for row, decision in zip(result.rows, decisions, strict=True):
            expected = expected_by_row[row.row_index]
            score.rows += 1
            score.labelled += expected != NEEDS_REVIEW
            if decision.status is TxnStatus.auto:
                score.auto += 1
                if decision.category_id == expected:
                    score.auto_correct += 1
                else:
                    report.wrong.append(
                        (name, row.row_index, row.description, expected, decision.category_id)
                    )
                    if expected != NEEDS_REVIEW and _flips_direction(
                        expected, decision.category_id
                    ):
                        report.direction_errors += 1
            else:
                score.review += 1
        report.files.append(score)
    return report


def main() -> int:
    report = evaluate()
    print(f"{'file':22} {'rows':>4} {'auto':>4} {'ok':>4} {'review':>6} {'precision':>9}")
    for f in report.files:
        print(
            f"{f.name:22} {f.rows:>4} {f.auto:>4} {f.auto_correct:>4} {f.review:>6} "
            f"{f.precision:>9.1%}"
        )
    print(
        f"\nauto-precision {report.precision:.1%} | review rate {report.review_rate:.1%} | "
        f"coverage {report.coverage:.1%} | direction errors {report.direction_errors}"
    )
    if report.wrong:
        print("\nwrong auto rows (expected -> got):")
        for (name, index, description, expected, got), n in Counter(report.wrong).items():
            print(f"  {name}#{index} {description!r}: {expected} -> {got}" + (f" x{n}" * (n > 1)))
    else:
        print("\nwrong auto rows: none")
    return 0 if report.precision >= 0.97 and report.direction_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
