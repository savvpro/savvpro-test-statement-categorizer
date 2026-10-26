"""Unit tests for DashboardService and date range parsing.

Validates statistical aggregations, income and expense calculations,
category breakdown distributions, and date-range filtering.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest

from app.models.category import Category
from app.models.transaction import ReviewStatus, Transaction
from app.services.dashboard_service import (
    CategoryBreakdownItem,
    DashboardService,
    DashboardStats,
    _to_decimal,
    _to_int,
    parse_date_range,
)


class TestParseDateRange:
    """Test date parsing and validation."""

    def test_both_none(self):
        s, e, err = parse_date_range(None, None)
        assert s is None
        assert e is None
        assert err is None

    def test_empty_strings(self):
        s, e, err = parse_date_range("  ", "")
        assert s is None
        assert e is None
        assert err is None

    def test_valid_range(self):
        s, e, err = parse_date_range("2026-08-01", "2026-08-31")
        assert s == date(2026, 8, 1)
        assert e == date(2026, 8, 31)
        assert err is None

    def test_single_start_date(self):
        s, e, err = parse_date_range("2026-08-01", None)
        assert s == date(2026, 8, 1)
        assert e is None
        assert err is None

    def test_single_end_date(self):
        s, e, err = parse_date_range(None, "2026-08-31")
        assert s is None
        assert e == date(2026, 8, 31)
        assert err is None

    def test_invalid_start_format(self):
        s, e, err = parse_date_range("01-08-2026", "2026-08-31")
        assert s is None
        assert "Invalid start date format" in err

    def test_invalid_end_format(self):
        s, e, err = parse_date_range("2026-08-01", "August 31, 2026")
        assert e is None
        assert "Invalid end date format" in err

    def test_start_greater_than_end(self):
        s, e, err = parse_date_range("2026-09-01", "2026-08-01")
        assert s is None
        assert e is None
        assert "cannot be later than end date" in err

    def test_equal_start_and_end(self):
        s, e, err = parse_date_range("2026-08-15", "2026-08-15")
        assert s == date(2026, 8, 15)
        assert e == date(2026, 8, 15)
        assert err is None


class TestHelperConversions:
    """Test _to_decimal and _to_int conversion safety."""

    def test_to_decimal_with_decimal(self):
        assert _to_decimal(Decimal("42.50")) == Decimal("42.50")

    def test_to_decimal_with_float_int(self):
        assert _to_decimal(100) == Decimal("100")
        assert _to_decimal(10.5) == Decimal("10.5")

    def test_to_decimal_with_string(self):
        assert _to_decimal("99.99") == Decimal("99.99")
        assert _to_decimal("invalid") == Decimal("0.00")

    def test_to_decimal_with_none_or_mock(self):
        assert _to_decimal(None) == Decimal("0.00")
        assert _to_decimal(MagicMock()) == Decimal("0.00")

    def test_to_int_with_valid_values(self):
        assert _to_int(42) == 42
        assert _to_int("100") == 100

    def test_to_int_with_invalid_or_mock(self):
        assert _to_int(None) == 0
        assert _to_int("invalid") == 0
        assert _to_int(MagicMock()) == 0


class TestDashboardServiceCalculations:
    """Test aggregate calculations in DashboardService."""

    def test_get_stats_empty_database(self):
        session = MagicMock()
        exec_mock = MagicMock()
        exec_mock.scalar.return_value = 0
        session.execute.return_value = exec_mock

        svc = DashboardService(session)
        stats = svc.get_stats()

        assert stats.total_transactions == 0
        assert stats.categorized_count == 0
        assert stats.review_count == 0
        assert stats.unknown_count == 0
        assert stats.total_income == Decimal("0.00")
        assert stats.total_expenses == Decimal("0.00")
        assert stats.net_cash_flow == Decimal("0.00")
        assert stats.total_statements == 0

    def test_get_stats_with_computed_aggregates(self):
        session = MagicMock()

        # Sequence of scalar returns for:
        # 1: total_transactions
        # 2: categorized_count
        # 3: review_count
        # 4: unknown_count
        # 5: total_income
        # 6: total_expenses
        # 7: total_statements
        scalar_values = [
            25,                    # total txs
            20,                    # categorized
            5,                     # review count
            3,                     # unknown count
            Decimal("3500.00"),    # total income
            Decimal("1200.00"),    # total expenses
            2,                     # statements
        ]

        exec_results = []
        for val in scalar_values:
            m = MagicMock()
            m.scalar.return_value = val
            exec_results.append(m)

        session.execute.side_effect = exec_results

        svc = DashboardService(session)
        stats = svc.get_stats(start_date=date(2026, 8, 1), end_date=date(2026, 8, 31))

        assert stats.total_transactions == 25
        assert stats.categorized_count == 20
        assert stats.review_count == 5
        assert stats.unknown_count == 3
        assert stats.total_income == Decimal("3500.00")
        assert stats.total_expenses == Decimal("1200.00")
        assert stats.net_cash_flow == Decimal("2300.00")
        assert stats.total_statements == 2
        assert stats.start_date == date(2026, 8, 1)
        assert stats.end_date == date(2026, 8, 31)

    def test_category_breakdown_aggregations(self):
        session = MagicMock()
        exec_mock = MagicMock()

        Row = MagicMock
        row1 = Row(
            category_id=1,
            category_name="Software",
            tx_count=10,
            spending=Decimal("400.00"),
            income=Decimal("0.00"),
        )
        row2 = Row(
            category_id=2,
            category_name="Cloud Hosting",
            tx_count=5,
            spending=Decimal("600.00"),
            income=Decimal("0.00"),
        )
        row3 = Row(
            category_id=14,
            category_name="Internal Transfer",
            tx_count=2,
            spending=Decimal("1000.00"),
            income=Decimal("0.00"),
        )

        exec_mock.all.return_value = [row1, row2, row3]
        session.execute.return_value = exec_mock

        svc = DashboardService(session)
        breakdown = svc.get_category_breakdown()

        assert len(breakdown) == 3
        # Total spending across non-transfers = 400 + 600 = 1000.00
        # Software: 400 / 1000 = 40.0%
        item_software = next(b for b in breakdown if b.category_name == "Software")
        assert item_software.transaction_count == 10
        assert item_software.total_spending == Decimal("400.00")
        assert item_software.percentage_of_spending == 40.0

        # Cloud Hosting: 600 / 1000 = 60.0%
        item_cloud = next(b for b in breakdown if b.category_name == "Cloud Hosting")
        assert item_cloud.percentage_of_spending == 60.0

        # Internal transfer excluded from spending percentage calculation
        item_xfer = next(b for b in breakdown if b.category_name == "Internal Transfer")
        assert item_xfer.percentage_of_spending == 0.0
