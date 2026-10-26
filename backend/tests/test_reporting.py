import pytest
from statement_categorizer.reporting import money_text, safe_text, summarize


def row(amount, kind="expense", category="Software", status="auto", excluded=False):
    return {"amount_minor": amount, "kind": kind, "category": category, "status": status, "excluded": excluded}


def test_partial_refund_and_credit_larger_than_spending():
    s = summarize(
        [
            row(-10000),
            row(15000, kind="refund"),
            row(70000, "income", "Income", "reviewed"),
            row(-2000, "personal", "Personal", "reviewed"),
            row(-1000, excluded=True),
            row(500, "unknown", "Needs Review", "needs_review"),
        ]
    )
    assert s["net_expenses_minor"] == -5000  # Net credits are allowed; do not clamp to zero.
    assert s["refund_minor"] == 15000 and s["income_minor"] == 70000
    assert s["raw_net_minor"] == s["accepted_net_minor"] + s["unresolved_net_minor"] + s["excluded_net_minor"]
    assert s["review_count"] == 1 and s["excluded_count"] == 1


@pytest.mark.parametrize("text", ["=SUM(A1)", "  =1+1", "+cmd", "-cmd", "@formula", "\tcmd", "\rtest", "\ntest"])
def test_formula_guards(text):
    assert safe_text(text) == "'" + text


def test_money_export_preserves_cents():
    assert money_text(-1) == "-0.01" and money_text(999999) == "9999.99"
    assert safe_text("ordinary merchant") == "ordinary merchant"
