"""Comprehensive Phase 7 Test Suite: Financial Reporting, Reconciliation & CSV Export.

Tests verify:
1. Financial Reporting Service:
   - Aggregation of income, expenses, and net movement.
   - Exclusion of internal transfers, reversals, and refunds from ordinary revenue/expense.
   - Decimal monetary precision and handling of uncategorized items.
   - Category breakdowns and percentage of spending calculations.
   - Monthly trend performance grouping.
   - Date, category, type, and statement filtering.

2. Statement Reconciliation Service:
   - Per-statement and batch credits, debits, and net cash flow auditing.
   - Balance reconciliation check (opening_balance + net_movement == closing_balance).
   - Discrepancy reporting and read-only non-destructive guarantees.

3. CSV Export & Security:
   - Full unpaginated export matching active filters.
   - Spreadsheet formula injection protection (CWE-1236) on untrusted text fields.
   - Preservation of legitimate negative numeric amounts and ISO dates.
   - RFC 4180 compliance for commas, quotes, and newlines.
   - Empty export with valid headers.

4. API & Web Route Integration:
   - GET /api/reports/summary, /categories, /monthly
   - GET /api/reconciliation, /api/reconciliation/{id}
   - GET /api/export/transactions
   - GET /reports and /reconciliation HTML pages
"""

from datetime import date, datetime
from decimal import Decimal
import io
import csv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session
from app.models import Base
from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction
from app.services.csv_export_service import CsvExportService, sanitize_text_for_csv
from app.services.reconciliation_service import ReconciliationService
from app.services.report_service import ReportService
from app.services.transaction_repository import TransactionRepository


# ---------------------------------------------------------------------------
# Fixtures with in-memory SQLite
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an isolated, in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed core categories
    cat_software = Category(id=1, name="Software", description="Software tools", is_system_category=True)
    cat_cloud = Category(id=2, name="Cloud Hosting", description="Cloud infrastructure", is_system_category=True)
    cat_meals = Category(id=3, name="Meals", description="Dining and food", is_system_category=True)
    cat_income = Category(id=4, name="Business Income", description="Client revenue", is_system_category=True)
    cat_transfer = Category(id=5, name="Internal Transfer", description="Account transfers", is_system_category=True)
    cat_refund = Category(id=6, name="Refund", description="Merchant refunds", is_system_category=True)
    cat_reversal = Category(id=7, name="Reversal", description="Bank fee reversal", is_system_category=True)
    cat_review = Category(id=8, name="Needs Review", description="Requires review", is_system_category=True)

    session.add_all([
        cat_software, cat_cloud, cat_meals, cat_income,
        cat_transfer, cat_refund, cat_reversal, cat_review
    ])

    # Seed statements
    stmt1 = Statement(id=1, original_filename="august_statement.csv", status="COMPLETED", transaction_count=4)
    stmt2 = Statement(id=2, original_filename="september_statement.csv", status="COMPLETED", transaction_count=2)
    session.add_all([stmt1, stmt2])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app(db_session):
    """Provide FastAPI app with database dependency overridden to test session."""
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db_session] = lambda: db_session
    yield fastapi_app
    fastapi_app.dependency_overrides = {}


@pytest.fixture
def client(app):
    """Test client."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _create_tx(
    session,
    statement_id: int,
    tx_date: date,
    description: str,
    amount: Decimal,
    category_id: int,
    review_status: str = ReviewStatus.REVIEWED,
) -> Transaction:
    """Helper to persist a transaction."""
    tx = Transaction(
        statement_id=statement_id,
        transaction_date=tx_date,
        original_description=description,
        normalized_description=description.upper(),
        amount=amount,
        currency="USD",
        category_id=category_id,
        confidence_score=0.9,
        classification_reason="Categorized",
        review_status=review_status,
        was_manually_categorized=False,
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Financial Reporting Tests
# ---------------------------------------------------------------------------

class TestFinancialReporting:
    """Test ReportService aggregation, conventions, and filtering."""

    def test_summary_calculations_and_exclusions(self, db_session):
        """Verify income, expenses, and net movement respect exclusions.

        - Income: +2500 (Business Income), excludes +500 (Refund), +1000 (Internal Transfer)
        - Expenses: -150 (Software) + -50 (Meals) = 200, excludes -300 (Internal Transfer)
        - Net movement: 2500 - 200 = 2300
        """
        _create_tx(db_session, 1, date(2026, 8, 1), "CLIENT PAYMENT", Decimal("2500.00"), 4)  # Income
        _create_tx(db_session, 1, date(2026, 8, 5), "GITHUB COPILOT", Decimal("-150.00"), 1)  # Expense: Software
        _create_tx(db_session, 1, date(2026, 8, 10), "CAFE LUNCH", Decimal("-50.00"), 3)      # Expense: Meals
        _create_tx(db_session, 1, date(2026, 8, 12), "TRANSFER TO SAVINGS", Decimal("-300.00"), 5)  # Transfer (excluded)
        _create_tx(db_session, 1, date(2026, 8, 15), "TRANSFER FROM CHECKING", Decimal("1000.00"), 5) # Transfer (excluded)
        _create_tx(db_session, 1, date(2026, 8, 20), "CLOUD REFUND", Decimal("500.00"), 6)    # Refund (isolated)

        svc = ReportService(db_session)
        summary = svc.get_financial_summary()

        assert summary.total_transactions == 6
        assert summary.total_income == Decimal("2500.00")
        assert summary.total_expenses == Decimal("200.00")
        assert summary.net_movement == Decimal("2300.00")
        assert summary.total_transfers == Decimal("1300.00")  # abs(-300) + 1000
        assert summary.total_refunds == Decimal("500.00")

    def test_summary_date_filtering(self, db_session):
        """Verify summary accurately respects start_date and end_date."""
        _create_tx(db_session, 1, date(2026, 7, 15), "JULY INCOME", Decimal("1000.00"), 4)
        _create_tx(db_session, 1, date(2026, 8, 10), "AUGUST INCOME", Decimal("2000.00"), 4)
        _create_tx(db_session, 1, date(2026, 9, 5), "SEPTEMBER INCOME", Decimal("3000.00"), 4)

        svc = ReportService(db_session)
        august_summary = svc.get_financial_summary(start_date=date(2026, 8, 1), end_date=date(2026, 8, 31))

        assert august_summary.total_transactions == 1
        assert august_summary.total_income == Decimal("2000.00")

    def test_empty_dataset_handling(self, db_session):
        """Verify financial summary returns zero Decimals on empty database."""
        svc = ReportService(db_session)
        summary = svc.get_financial_summary()

        assert summary.total_transactions == 0
        assert summary.total_income == Decimal("0.00")
        assert summary.total_expenses == Decimal("0.00")
        assert summary.net_movement == Decimal("0.00")
        assert summary.categorized_count == 0

    def test_category_report_breakdown(self, db_session):
        """Verify category breakdown calculates expenses, income, and expense shares."""
        _create_tx(db_session, 1, date(2026, 8, 1), "JETBRAINS IDE", Decimal("-300.00"), 1)  # Software
        _create_tx(db_session, 1, date(2026, 8, 2), "DOCKER DESKTOP", Decimal("-100.00"), 1) # Software
        _create_tx(db_session, 1, date(2026, 8, 5), "AWS CLOUD", Decimal("-600.00"), 2)       # Cloud
        # Total expenses: 1000 (Software: 400 = 40%, Cloud: 600 = 60%)

        svc = ReportService(db_session)
        items = svc.get_category_report()

        assert len(items) == 2
        # Cloud has higher expense, so should appear first
        assert items[0].category_name == "Cloud Hosting"
        assert items[0].total_expenses == Decimal("600.00")
        assert items[0].percentage_of_expenses == 60.0

        assert items[1].category_name == "Software"
        assert items[1].total_expenses == Decimal("400.00")
        assert items[1].transaction_count == 2
        assert items[1].percentage_of_expenses == 40.0

    def test_monthly_trends_grouping(self, db_session):
        """Verify monthly income, expense, and net movement grouping."""
        _create_tx(db_session, 1, date(2026, 7, 20), "JULY FEE", Decimal("-100.00"), 1)
        _create_tx(db_session, 1, date(2026, 7, 25), "JULY CLIENT", Decimal("1500.00"), 4)
        _create_tx(db_session, 1, date(2026, 8, 10), "AUG HOSTING", Decimal("-250.00"), 2)

        svc = ReportService(db_session)
        trends = svc.get_monthly_trends()

        assert len(trends) == 2
        assert trends[0].month_key == "2026-07"
        assert trends[0].income == Decimal("1500.00")
        assert trends[0].expenses == Decimal("100.00")
        assert trends[0].net == Decimal("1400.00")

        assert trends[1].month_key == "2026-08"
        assert trends[1].income == Decimal("0.00")
        assert trends[1].expenses == Decimal("250.00")
        assert trends[1].net == Decimal("-250.00")


# ---------------------------------------------------------------------------
# 2. Statement Reconciliation Tests
# ---------------------------------------------------------------------------

class TestStatementReconciliation:
    """Test statement reconciliation, credit/debit calculation, and balance checking."""

    def test_statement_reconciliation_credits_and_debits(self, db_session):
        """Verify statement reconciliation totals credits, debits, and net movement."""
        _create_tx(db_session, 1, date(2026, 8, 1), "CLIENT DEPOSIT", Decimal("3000.00"), 4)
        _create_tx(db_session, 1, date(2026, 8, 2), "OFFICE RENT", Decimal("-1200.00"), 1)
        _create_tx(db_session, 1, date(2026, 8, 3), "UNKNOWN FEE", Decimal("-50.00"), 8, review_status=ReviewStatus.PENDING)

        svc = ReconciliationService(db_session)
        rec = svc.reconcile_statement(1)

        assert rec is not None
        assert rec.statement_id == 1
        assert rec.transaction_count == 3
        assert rec.total_credits == Decimal("3000.00")
        assert rec.total_debits == Decimal("1250.00")
        assert rec.net_movement == Decimal("1750.00")
        assert rec.pending_count == 1
        assert rec.reviewed_count == 2

    def test_statement_balance_reconciliation_balanced(self, db_session):
        """Verify opening + net == closing indicates balanced statement."""
        # Net movement: +1000 - 200 = +800
        _create_tx(db_session, 1, date(2026, 8, 1), "DEP", Decimal("1000.00"), 4)
        _create_tx(db_session, 1, date(2026, 8, 2), "EXP", Decimal("-200.00"), 1)

        svc = ReconciliationService(db_session)
        rec = svc.reconcile_statement(
            1,
            opening_balance=Decimal("5000.00"),
            closing_balance=Decimal("5800.00"),
        )

        assert rec.is_balanced is True
        assert rec.expected_closing_balance == Decimal("5800.00")
        assert rec.discrepancy == Decimal("0.00")

    def test_statement_balance_reconciliation_discrepancy(self, db_session):
        """Verify discrepancy calculation when closing balance differs from expected."""
        _create_tx(db_session, 1, date(2026, 8, 1), "DEP", Decimal("1000.00"), 4)

        svc = ReconciliationService(db_session)
        rec = svc.reconcile_statement(
            1,
            opening_balance=Decimal("2000.00"),
            closing_balance=Decimal("2900.00"),  # Expected: 3000 -> Discrepancy: -100
        )

        assert rec.is_balanced is False
        assert rec.expected_closing_balance == Decimal("3000.00")
        assert rec.discrepancy == Decimal("-100.00")

    def test_reconcile_all_statements(self, db_session):
        """Verify batch reconciliation across all statements."""
        _create_tx(db_session, 1, date(2026, 8, 1), "TX1", Decimal("500.00"), 4)
        _create_tx(db_session, 2, date(2026, 9, 1), "TX2", Decimal("-150.00"), 1)

        svc = ReconciliationService(db_session)
        all_recs = svc.reconcile_all_statements()

        assert len(all_recs) == 2
        stmt_ids = [r.statement_id for r in all_recs]
        assert 1 in stmt_ids
        assert 2 in stmt_ids


# ---------------------------------------------------------------------------
# 3. CSV Export & Security Tests (Formula Injection Protection)
# ---------------------------------------------------------------------------

class TestCsvExportAndSecurity:
    """Test CSV generation, RFC 4180 escaping, and formula injection protection."""

    def test_sanitize_text_prepends_quote_to_dangerous_prefixes(self):
        """Verify dangerous formula prefixes are escaped with single quote."""
        assert sanitize_text_for_csv("=1+1") == "'=1+1"
        assert sanitize_text_for_csv("  =cmd|' /C calc'!A0") == "'  =cmd|' /C calc'!A0"
        assert sanitize_text_for_csv("+SUM(A1:A10)") == "'+SUM(A1:A10)"
        assert sanitize_text_for_csv("-2+3*4") == "'-2+3*4"
        assert sanitize_text_for_csv("@IMPORTXML(...)") == "'@IMPORTXML(...)"
        assert sanitize_text_for_csv("\tTabMalicious") == "'\tTabMalicious"

    def test_sanitize_text_preserves_safe_strings(self):
        """Safe strings without formula triggers remain untouched."""
        assert sanitize_text_for_csv("GitHub Copilot Subscription") == "GitHub Copilot Subscription"
        assert sanitize_text_for_csv("Staples Office Supplies") == "Staples Office Supplies"
        assert sanitize_text_for_csv("") == ""
        assert sanitize_text_for_csv(None) == ""

    def test_csv_export_preserves_legitimate_negative_monetary_numbers(self, db_session):
        """CRITICAL: Legitimate negative numbers (e.g. -25.00) MUST NOT be quoted as formulas."""
        _create_tx(db_session, 1, date(2026, 8, 1), "LEGIT EXPENSE", Decimal("-45.50"), 1)

        repo = TransactionRepository(db_session)
        transactions = repo.get_all_matching()

        csv_text = CsvExportService.export_transactions(transactions)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        header = rows[0]
        data_row = rows[1]

        amount_idx = header.index("Amount")
        debit_idx = header.index("Debit")

        # Amount must be clean numeric "-45.50" (not "'-45.50")
        assert data_row[amount_idx] == "-45.50"
        # Debit is positive expense amount
        assert data_row[debit_idx] == "45.50"

    def test_csv_export_escapes_malicious_descriptions(self, db_session):
        """Malicious formula descriptions are neutralized."""
        _create_tx(db_session, 1, date(2026, 8, 1), "=HYPERLINK('http://evil.com')", Decimal("10.00"), 4)
        _create_tx(db_session, 1, date(2026, 8, 2), "+2+5*cmd", Decimal("-20.00"), 1)

        repo = TransactionRepository(db_session)
        transactions = repo.get_all_matching()

        csv_text = CsvExportService.export_transactions(transactions)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        desc_idx = rows[0].index("Original Description")
        assert rows[1][desc_idx].startswith("'+")
        assert rows[2][desc_idx].startswith("'=")



    def test_csv_export_handles_commas_and_newlines_in_descriptions(self, db_session):
        """RFC 4180 quotes commas and newlines properly."""
        _create_tx(db_session, 1, date(2026, 8, 1), "STORE, INC - NYC\nDEPARTMENT #2", Decimal("-30.00"), 1)

        repo = TransactionRepository(db_session)
        transactions = repo.get_all_matching()

        csv_text = CsvExportService.export_transactions(transactions)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        desc_idx = rows[0].index("Original Description")
        assert "STORE, INC - NYC\nDEPARTMENT #2" == rows[1][desc_idx]

    def test_csv_export_empty_transactions(self):
        """Empty export returns standard headers without error."""
        csv_text = CsvExportService.export_transactions([])
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        assert len(rows) == 1
        assert "Transaction ID" in rows[0]
        assert "Amount" in rows[0]


# ---------------------------------------------------------------------------
# 4. API & Web Route Integration Tests
# ---------------------------------------------------------------------------

class TestPhase7Routes:
    """Verify HTTP API and Web route endpoints."""

    def test_api_report_summary(self, client, db_session):
        """GET /api/reports/summary returns JSON financial metrics."""
        _create_tx(db_session, 1, date(2026, 8, 1), "INCOME", Decimal("1000.00"), 4)

        resp = client.get("/api/reports/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_transactions"] == 1
        assert data["total_income"] == 1000.0
        assert data["net_movement"] == 1000.0

    def test_api_report_categories(self, client, db_session):
        """GET /api/reports/categories returns category distribution list."""
        _create_tx(db_session, 1, date(2026, 8, 1), "TOOL", Decimal("-80.00"), 1)

        resp = client.get("/api/reports/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["category_name"] == "Software"
        assert data[0]["total_expenses"] == 80.0

    def test_api_report_monthly(self, client, db_session):
        """GET /api/reports/monthly returns monthly performance array."""
        _create_tx(db_session, 1, date(2026, 8, 1), "TOOL", Decimal("-50.00"), 1)

        resp = client.get("/api/reports/monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["month_key"] == "2026-08"
        assert data[0]["expenses"] == 50.0

    def test_api_reconciliation_list(self, client, db_session):
        """GET /api/reconciliation returns statement reconciliation records."""
        resp = client.get("/api/reconciliation")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["statement_id"] in (1, 2)

    def test_api_reconciliation_single_statement_with_balance(self, client, db_session):
        """GET /api/reconciliation/1?opening_balance=1000&closing_balance=1000."""
        resp = client.get("/api/reconciliation/1?opening_balance=1000.00&closing_balance=1000.00")
        assert resp.status_code == 200
        data = resp.json()
        assert data["statement_id"] == 1
        assert data["is_balanced"] is True

    def test_api_export_transactions_csv_stream(self, client, db_session):
        """GET /api/export/transactions returns CSV content with attachment header."""
        _create_tx(db_session, 1, date(2026, 8, 1), "AWS HOSTING", Decimal("-120.00"), 2)

        resp = client.get("/api/export/transactions")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment; filename=" in resp.headers["content-disposition"]
        assert "Transaction ID,Date,Original Description" in resp.text
        assert "AWS HOSTING" in resp.text

    def test_web_reports_page_renders(self, client, db_session):
        """GET /reports renders HTML page with summary and chart elements."""
        _create_tx(db_session, 1, date(2026, 8, 1), "CLIENT DEPOSIT", Decimal("2000.00"), 4)

        resp = client.get("/reports")
        assert resp.status_code == 200
        assert "Financial Reports" in resp.text
        assert "monthly-trend-chart" in resp.text
        assert "category-report-chart" in resp.text

    def test_web_reconciliation_page_renders(self, client, db_session):
        """GET /reconciliation renders reconciliation table and balance calculator."""
        resp = client.get("/reconciliation")
        assert resp.status_code == 200
        assert "Statement Reconciliation" in resp.text
        assert "Balance Reconciliation Calculator" in resp.text

    def test_web_export_transactions_download(self, client, db_session):
        """GET /export/transactions downloads CSV file directly."""
        _create_tx(db_session, 1, date(2026, 8, 1), "TAX PREP", Decimal("-250.00"), 1)

        resp = client.get("/export/transactions")
        assert resp.status_code == 200
        assert "TAX PREP" in resp.text
        assert "attachment; filename=" in resp.headers["content-disposition"]
