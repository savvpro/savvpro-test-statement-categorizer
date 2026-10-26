"""Phase 5 web and API tests for Dashboard and Transaction Management.

Validates dashboard metrics rendering, date filtering, transaction table,
search and filter combinations, sorting, pagination, transaction detail view,
and security protections.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction


@pytest.fixture(scope="module")
def app():
    """Create the FastAPI app for testing with patched database connection."""
    with patch("app.database.session.get_engine") as mock_eng, \
         patch("app.database.session.get_session_factory") as mock_factory:
        mock_factory.return_value = MagicMock()
        mock_eng.return_value = MagicMock()

        from app.main import app as fastapi_app
        yield fastapi_app


@pytest.fixture(scope="module")
def client(app):
    """Return TestClient for HTTP verification."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _mock_session_with_data():
    """Create a mock session pre-populated with realistic models."""
    session = MagicMock()

    # Create dummy category
    cat_software = Category(
        id=1,
        name="Software",
        description="IDE licenses and tools",
        is_system_category=True,
    )

    # Create dummy statement
    stmt = Statement(
        id=1,
        original_filename="august_2026.csv",
        status="COMPLETED",
        transaction_count=2,
    )

    # Create dummy transactions
    tx1 = Transaction(
        id=101,
        statement_id=1,
        transaction_date=date(2026, 8, 1),
        original_description="JETBRAINS *SUBSCRIPTION",
        normalized_description="JETBRAINS SUBSCRIPTION",
        amount=Decimal("-15.00"),
        currency="USD",
        category_id=1,
        confidence_score=0.95,
        classification_reason="Matched known developer IDE pattern",
        review_status=ReviewStatus.NOT_REQUIRED,
        was_manually_categorized=False,
    )
    tx1.category = cat_software
    tx1.statement = stmt
    tx1.classification_events = []

    tx2 = Transaction(
        id=102,
        statement_id=1,
        transaction_date=date(2026, 8, 5),
        original_description="ACME CLIENT RETAINER",
        normalized_description="ACME CLIENT RETAINER",
        amount=Decimal("2500.00"),
        currency="USD",
        category_id=None,
        confidence_score=0.40,
        classification_reason="Ambiguous client deposit",
        review_status=ReviewStatus.PENDING,
        was_manually_categorized=False,
    )
    tx2.category = None
    tx2.statement = stmt
    tx2.classification_events = []

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [tx1, tx2]
    execute_result.scalars.return_value.first.return_value = tx1
    execute_result.scalar.return_value = 2
    execute_result.scalar_one.return_value = 2
    execute_result.all.return_value = []
    session.execute.return_value = execute_result

    return session, tx1, tx2, cat_software, stmt


# ---------------------------------------------------------------------------
# Dashboard Tests
# ---------------------------------------------------------------------------

class TestDashboardPhase5:

    def test_dashboard_renders_metrics_and_components(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.content
        assert b"Total Transactions" in resp.content
        assert b"Business Income" in resp.content
        assert b"Total Expenses" in resp.content
        assert b"Net Cash Flow" in resp.content
        app.dependency_overrides = {}

    def test_dashboard_date_filtering(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/?start_date=2026-08-01&end_date=2026-08-31")
        assert resp.status_code == 200
        assert b"2026-08-01" in resp.content
        assert b"2026-08-31" in resp.content
        app.dependency_overrides = {}

    def test_dashboard_date_validation_error(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        # Start date after end date
        resp = client.get("/?start_date=2026-09-01&end_date=2026-08-01")
        assert resp.status_code == 200
        assert b"cannot be later than end date" in resp.content
        app.dependency_overrides = {}

    def test_dashboard_api_stats_endpoint(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "category_breakdown" in data
        assert "total_transactions" in data["stats"]
        assert "total_income" in data["stats"]
        assert "total_expenses" in data["stats"]
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Transaction List & Management Tests
# ---------------------------------------------------------------------------

class TestTransactionManagementPhase5:

    def test_transaction_list_page_renders_table(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert b"Transactions" in resp.content
        assert b"JETBRAINS" in resp.content
        app.dependency_overrides = {}

    def test_search_by_description(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?q=jetbrains")
        assert resp.status_code == 200
        assert b"jetbrains" in resp.content.lower()
        app.dependency_overrides = {}

    def test_filter_by_status(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?status=PENDING")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_filter_by_type_expense(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?tx_type=expense")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_filter_by_category(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?category_id=1")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_sorting_parameters(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?sort_by=amount&sort_dir=asc")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_pagination_parameters(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions?page=2&page_size=10")
        assert resp.status_code == 200
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Transaction Details Tests
# ---------------------------------------------------------------------------

class TestTransactionDetailPhase5:

    def test_transaction_detail_found(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions/101")
        assert resp.status_code == 200
        assert b"Transaction #101" in resp.content
        assert b"JETBRAINS *SUBSCRIPTION" in resp.content
        assert b"Matched known developer IDE pattern" in resp.content
        app.dependency_overrides = {}

    def test_transaction_detail_invalid_id_returns_404(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions/0")
        assert resp.status_code == 404
        app.dependency_overrides = {}

    def test_transaction_detail_missing_returns_404(self, client, app):
        from app.api.dependencies import get_db_session
        session = MagicMock()
        exec_mock = MagicMock()
        exec_mock.scalars.return_value.first.return_value = None
        session.execute.return_value = exec_mock
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/transactions/999999")
        assert resp.status_code == 404
        app.dependency_overrides = {}

    def test_api_transaction_json_detail(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/api/transactions/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 101
        assert data["original_description"] == "JETBRAINS *SUBSCRIPTION"
        assert data["category_name"] == "Software"
        assert data["confidence_score"] == 0.95
        app.dependency_overrides = {}

    def test_api_transaction_list_json(self, client, app):
        from app.api.dependencies import get_db_session
        session, tx1, tx2, cat, stmt = _mock_session_with_data()
        app.dependency_overrides[get_db_session] = lambda: session

        resp = client.get("/api/transactions?page=1&page_size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert len(data["items"]) == 2
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Reliability & Security Tests
# ---------------------------------------------------------------------------

class TestReliabilityAndSecurity:

    def test_html_escaping_of_raw_descriptions(self, client, app):
        """Verify that XSS payloads in descriptions are safely escaped in HTML."""
        from app.api.dependencies import get_db_session
        session = MagicMock()

        xss_tx = Transaction(
            id=999,
            statement_id=1,
            transaction_date=date(2026, 8, 1),
            original_description="<script>alert('xss')</script>",
            normalized_description="ALERT XSS",
            amount=Decimal("-50.00"),
            currency="USD",
            category_id=None,
            confidence_score=0.1,
            classification_reason="Testing XSS safety",
            review_status=ReviewStatus.PENDING,
            was_manually_categorized=False,
        )
        xss_tx.category = None
        xss_tx.statement = None
        xss_tx.classification_events = []

        exec_mock = MagicMock()
        exec_mock.scalars.return_value.all.return_value = [xss_tx]
        exec_mock.scalars.return_value.first.return_value = xss_tx
        exec_mock.scalar.return_value = 1
        exec_mock.all.return_value = []
        session.execute.return_value = exec_mock

        app.dependency_overrides[get_db_session] = lambda: session

        # Check in transaction listing
        resp = client.get("/transactions")
        assert resp.status_code == 200
        # Should be escaped, not rendered as raw executable tag
        assert b"<script>alert('xss')</script>" not in resp.content
        assert b"&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in resp.content or b"&lt;script&gt;alert('xss')&lt;/script&gt;" in resp.content

        # Check in transaction detail
        resp_detail = client.get("/transactions/999")
        assert resp_detail.status_code == 200
        assert b"<script>alert('xss')</script>" not in resp_detail.content

        app.dependency_overrides = {}
