#!/usr/bin/env python3
"""Informational: list catalog IDs (docs/plan/04) that no labelled sample row covers.

Reads every samples/**/*.expected.json. S-cases are not in the P/D table and are
ignored; D40, D42 and D43 are API-level and exempt. Always exits 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "plan" / "04-edge-cases-and-fixtures.md"
SAMPLES = ROOT / "samples"
EXEMPT = {"D40", "D42", "D43"}


def catalog_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"^\|\s*([PD]\d{2})\s*\|", text, flags=re.MULTILINE)))


def covered_ids() -> set[str]:
    found: set[str] = set()
    for path in SAMPLES.rglob("*.expected.json"):
        for row in json.loads(path.read_text(encoding="utf-8")):
            if row.get("case_id"):
                found.add(row["case_id"])
    return found


def main() -> int:
    ids = catalog_ids(CATALOG.read_text(encoding="utf-8"))
    covered = covered_ids()
    in_scope = [i for i in ids if i not in EXEMPT]
    missing = [i for i in in_scope if i not in covered]
    print(f"Catalog IDs: {len(ids)} (exempt: {', '.join(sorted(EXEMPT))})")
    print(f"Covered: {len(in_scope) - len(missing)}/{len(in_scope)}")
    print("Missing: " + (", ".join(missing) if missing else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
