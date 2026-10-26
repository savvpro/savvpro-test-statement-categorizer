"""Web/API smoke tests for Phase 4 FastAPI application.

These tests use FastAPI's test client and work WITHOUT a real MySQL database
by patching the database session dependency with an in-memory MagicMock.
They verify routing, template rendering, and basic HTTP behaviour.
"""

import io
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Create the FastAPI app for testing.

    Patches database dependency so no real MySQL connection is required.
    """
    # Patch database engine creation to avoid any DB connection at import time
    with patch("app.database.session.get_engine") as mock_eng, \
         patch("app.database.session.get_session_factory") as mock_factory:
        mock_factory.return_value = MagicMock()
        mock_eng.return_value = MagicMock()

        # Import after patching so engine init doesn't run
        from app.main import app as fastapi_app
        yield fastapi_app


@pytest.fixture(scope="module")
def client(app):
    """Return a TestClient wrapping the FastAPI app."""
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _mock_session():
    """Build a minimal mock SQLAlchemy session."""
    session = MagicMock()
    # Mock execute to return empty scalars and aggregates
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    execute_result.scalar_one.return_value = 0
    execute_result.scalar.return_value = 0
    execute_result.all.return_value = []
    session.execute.return_value = execute_result
    return session


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        with patch("app.api.routes.health.check_database_connection", return_value=True):
            resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_json_structure(self, client):
        with patch("app.api.routes.health.check_database_connection", return_value=True):
            resp = client.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert "database" in data

    def test_health_ok_when_db_connected(self, client):
        with patch("app.api.routes.health.check_database_connection", return_value=True):
            resp = client.get("/api/health")
        assert resp.json()["status"] == "ok"
        assert resp.json()["database"] == "connected"

    def test_health_degraded_when_db_unreachable(self, client):
        with patch("app.api.routes.health.check_database_connection", return_value=False):
            resp = client.get("/api/health")
        assert resp.json()["status"] == "degraded"


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

class TestDashboard:

    def _db_override(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        # Patch statement repository list to return empty
        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_dashboard_returns_200(self, client, app):
        session = self._db_override(app)
        resp = client.get("/")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_dashboard_contains_ledgerlens(self, client, app):
        session = self._db_override(app)
        resp = client.get("/")
        assert b"LedgerLens" in resp.content
        app.dependency_overrides = {}

    def test_dashboard_contains_dashboard_heading(self, client, app):
        session = self._db_override(app)
        resp = client.get("/")
        assert b"Dashboard" in resp.content
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Upload page
# ---------------------------------------------------------------------------

class TestUploadPage:

    def test_upload_get_returns_200(self, client):
        resp = client.get("/statements/upload")
        assert resp.status_code == 200

    def test_upload_page_has_form(self, client):
        resp = client.get("/statements/upload")
        assert b"<form" in resp.content

    def test_upload_page_has_file_input(self, client):
        resp = client.get("/statements/upload")
        assert b'type="file"' in resp.content

    def test_upload_rejects_non_csv(self, client, app):
        """Uploading a .txt file must return 422."""
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        resp = client.post(
            "/statements/upload",
            files={"file": ("test.txt", b"date,description,amount\n", "text/plain")},
        )
        assert resp.status_code == 422
        assert b"CSV" in resp.content
        app.dependency_overrides = {}

    def test_upload_rejects_empty_file(self, client, app):
        """An empty file must return 422 with a helpful message."""
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        resp = client.post(
            "/statements/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert resp.status_code == 422
        assert b"empty" in resp.content.lower()
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Statements list page
# ---------------------------------------------------------------------------

class TestStatementsPage:

    def _setup(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_statements_page_returns_200(self, client, app):
        self._setup(app)
        resp = client.get("/statements")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_statements_page_has_table(self, client, app):
        from app.api.dependencies import get_db_session
        session = MagicMock()
        mock_stmt = MagicMock()
        mock_stmt.id = 1
        mock_stmt.original_filename = "test.csv"
        mock_stmt.status = "COMPLETED"
        mock_stmt.transaction_count = 5
        mock_stmt.currency = "USD"
        mock_stmt.created_at = None
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = [mock_stmt]
        session.execute.return_value = execute_result

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        resp = client.get("/statements")
        assert b"<table" in resp.content
        assert b"test.csv" in resp.content
        app.dependency_overrides = {}

    def test_statements_page_shows_empty_state(self, client, app):
        self._setup(app)
        resp = client.get("/statements")
        # Should show empty state message
        assert b"No statements" in resp.content or b"Upload" in resp.content
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Transactions page
# ---------------------------------------------------------------------------

class TestTransactionsPage:

    def _setup(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_transactions_page_returns_200(self, client, app):
        self._setup(app)
        resp = client.get("/transactions")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_transactions_filter_pending(self, client, app):
        self._setup(app)
        resp = client.get("/transactions?review=pending")
        assert resp.status_code == 200
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Review queue page
# ---------------------------------------------------------------------------

class TestReviewPage:

    def _setup(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_review_page_returns_200(self, client, app):
        self._setup(app)
        resp = client.get("/review")
        assert resp.status_code == 200
        app.dependency_overrides = {}

    def test_review_shows_all_clear_when_empty(self, client, app):
        self._setup(app)
        resp = client.get("/review")
        assert b"clear" in resp.content.lower() or b"nothing" in resp.content.lower() or b"All clear" in resp.content
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Categories page
# ---------------------------------------------------------------------------

class TestCategoriesPage:

    def _setup(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_categories_page_returns_200(self, client, app):
        self._setup(app)
        resp = client.get("/categories")
        assert resp.status_code == 200
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# 404 handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_route_returns_404(self, client):
        resp = client.get("/this-does-not-exist")
        assert resp.status_code == 404

    def test_unknown_statement_returns_404(self, client, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()
        session.get.return_value = None  # Statement not found

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        resp = client.get("/statements/99999")
        assert resp.status_code == 404
        app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------

class TestJsonApi:

    def _setup(self, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        return session

    def test_api_categories_returns_json(self, client, app):
        self._setup(app)
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        app.dependency_overrides = {}

    def test_api_statements_returns_json(self, client, app):
        self._setup(app)
        resp = client.get("/api/statements")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        app.dependency_overrides = {}

    def test_api_statement_not_found_returns_404(self, client, app):
        from app.api.dependencies import get_db_session
        session = _mock_session()
        session.get.return_value = None

        def override():
            yield session

        app.dependency_overrides[get_db_session] = override
        resp = client.get("/api/statements/99999/transactions")
        assert resp.status_code == 404
        app.dependency_overrides = {}

    def test_api_docs_accessible(self, client):
        resp = client.get("/api/docs")
        assert resp.status_code == 200
