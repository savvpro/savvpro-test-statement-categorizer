"""Run the whole brain (parse -> classify -> postcheck) on the sample files and compare
with sample_data/expected_labels.csv."""

import csv
from pathlib import Path

import pytest

from app.brain.classifier import classify
from app.brain.models import Decision
from app.brain.postcheck import postcheck
from app.core.domain import CATEGORIES, KINDS
from app.ingest.models import ParsedRow
from app.ingest.parser import parse

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
FILES = ["bank_a_card.csv", "bank_b_checking.csv", "messy_statement.csv"]
NOT_CATEGORIES = {"PARSE_ERROR", "SKIPPED"}


def load_labels() -> list[dict[str, str]]:
    with (SAMPLE_DIR / "expected_labels.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_pipeline(name: str) -> dict[int, tuple[ParsedRow, Decision]]:
    result = parse((SAMPLE_DIR / name).read_bytes())
    decisions = postcheck(result.rows, [classify(row) for row in result.rows])
    return {row.row_number: (row, d) for row, d in zip(result.rows, decisions, strict=True)}


def find_mismatches() -> list[dict[str, str]]:
    pipelines = {name: run_pipeline(name) for name in FILES}
    mismatches = []
    for label in load_labels():
        if label["expected_category"] in NOT_CATEGORIES:
            continue
        row, d = pipelines[label["file"]][int(label["row_number"])]
        expected = (
            label["expected_category"],
            label["expected_kind"],
            label["expected_needs_review"],
        )
        got = (d.category, d.kind, str(d.needs_review).lower())
        if expected != got:
            mismatches.append(
                {
                    "where": f"{label['file'].removesuffix('.csv')}:{label['row_number']}",
                    "description": row.raw_description.strip(),
                    "expected": " | ".join(expected),
                    "got": " | ".join(got),
                    "rule": d.rule_id or "-",
                    "reason": d.reason,
                }
            )
    return mismatches


def format_table(mismatches: list[dict[str, str]]) -> str:
    if not mismatches:
        return "no mismatches"
    columns = ["where", "description", "expected", "got", "rule", "reason"]
    widths = {c: min(max(len(c), *(len(m[c]) for m in mismatches)), 44) for c in columns}

    def line(values: dict[str, str]) -> str:
        return "  ".join(values[c][: widths[c]].ljust(widths[c]) for c in columns).rstrip()

    header = line({c: c for c in columns})
    return "\n".join([header, "-" * len(header), *(line(m) for m in mismatches)])


@pytest.mark.parametrize("name", FILES)
def test_pipeline_runs_and_returns_valid_decisions(name: str) -> None:
    for _, d in run_pipeline(name).values():
        assert d.category in CATEGORIES and d.kind in KINDS
        assert d.reason
        assert 0 <= d.confidence <= 1
        if d.category == "Needs Review":
            assert d.needs_review is True


def test_every_parsed_row_has_a_label() -> None:
    labelled = {(lab["file"], int(lab["row_number"])) for lab in load_labels()}
    for name in FILES:
        for number in run_pipeline(name):
            assert (name, number) in labelled


def test_table_formatting() -> None:
    assert format_table([]) == "no mismatches"
    table = format_table(
        [{"where": "a:1", "description": "X", "expected": "A", "got": "B", "rule": "r",
          "reason": "z"}]
    )
    assert table.splitlines()[0].startswith("where")


def test_labels_match() -> None:
    mismatches = find_mismatches()
    table = format_table(mismatches)
    print(f"\n{len(mismatches)} mismatches\n{table}")
    assert not mismatches, f"{len(mismatches)} rows differ from expected_labels.csv\n{table}"
