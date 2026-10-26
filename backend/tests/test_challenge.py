import json
from pathlib import Path

import pytest

from app.engine import classify

CASES = json.loads((Path(__file__).parent / "fixtures" / "challenge.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["description"] for case in CASES])
def test_independent_challenge(case):
    result = classify(case["description"], case["amount"])
    assert (result.kind, result.category, result.status) == (
        case["kind"],
        case["category"],
        case["status"],
    )


@pytest.mark.parametrize("amount", [-1, -937, -999999])
def test_merchant_evidence_survives_amount_and_spacing_changes(amount):
    a = classify("  ADOBE   CREATIVE CLOUD  ", amount)
    b = classify("adobe creative cloud", amount)
    assert a == b
