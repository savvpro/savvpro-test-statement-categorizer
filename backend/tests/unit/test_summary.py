from dataclasses import dataclass

from app.services.summary import compute_summary


@dataclass
class Row:
    category: str | None
    status: str
    amount_cents: int


def test_totals_use_auto_and_confirmed_only() -> None:
    s = compute_summary(
        [
            Row("RENT", "auto", 180_000),
            Row("REPAIRS", "user_confirmed", -12_345),
            Row("REPAIRS", "needs_review", -99_999),
            Row("REPAIRS", "duplicate", -50_000),
        ]
    )
    assert s.income == {"RENT": 180_000}
    assert s.expenses == {"REPAIRS": -12_345}
    assert (s.total_income_cents, s.total_expense_cents, s.net_cents) == (180_000, -12_345, 167_655)
    assert (s.unresolved_count, s.unresolved_total_abs_cents) == (1, 99_999)
    assert s.duplicate_count == 1


def test_D12_refund_nets_against_its_category() -> None:
    s = compute_summary([Row("REPAIRS", "auto", -12_345), Row("REPAIRS", "auto", 4_500)])
    assert s.expenses["REPAIRS"] == -7_845


def test_non_pnl_categories_are_excluded_from_schedule_e() -> None:
    s = compute_summary(
        [
            Row("TRANSFER", "auto", -100_000),
            Row("SECURITY_DEPOSIT_RECEIVED", "auto", 150_000),
            Row("RENT", "auto", 100_000),
        ]
    )
    assert s.excluded == {"TRANSFER": -100_000, "SECURITY_DEPOSIT_RECEIVED": 150_000}
    assert [line["category"] for line in s.schedule_e] == ["RENT"]
    assert s.net_cents == 100_000


def test_schedule_e_lines_ordered_numerically() -> None:
    s = compute_summary(
        [
            Row("OTHER_EXPENSE", "auto", -1),
            Row("REPAIRS", "auto", -1),
            Row("ADVERTISING", "auto", -1),
            Row("RENT", "auto", 1),
        ]
    )
    assert [line["line"] for line in s.schedule_e] == ["3", "5", "14", "19"]


def test_uncategorised_auto_rows_are_ignored() -> None:
    s = compute_summary([Row(None, "auto", -100)])
    assert s.net_cents == 0
    assert s.schedule_e == []


def test_empty() -> None:
    s = compute_summary([])
    assert s.net_cents == 0
    assert s.unresolved_count == 0
