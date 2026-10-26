"""Unit and integration tests for Category CRUD API and web interface."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session
from app.models.category import Category


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


def _make_mock_session():
    """Build mock db session."""
    session = MagicMock()
    exec_res = MagicMock()
    exec_res.scalar_one.return_value = 0
    exec_res.scalars.return_value.all.return_value = []
    session.execute.return_value = exec_res
    return session


def test_api_list_categories(app, client):
    """Verify listing categories returns list with tx and rule counts."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session

    cat1 = Category(id=1, name="Software", description="Software tools", is_system_category=True)
    cat2 = Category(id=2, name="Freelance Misc", description="Custom", is_system_category=False)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.list_categories.return_value = [cat1, cat2]
            mock_repo_cls.return_value = mock_repo

            session.execute.return_value.scalar_one.side_effect = [5, 2, 0, 0]  # cat1: tx=5, rule=2; cat2: tx=0, rule=0

            resp = client.get("/api/categories")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["name"] == "Software"
            assert data[0]["is_system_category"] is True
            assert data[0]["transaction_count"] == 5
            assert data[0]["rule_count"] == 2
            assert data[1]["name"] == "Freelance Misc"
            assert data[1]["is_system_category"] is False
    finally:
        app.dependency_overrides = {}


def test_api_get_category(app, client):
    """Verify getting a single category by ID."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=1, name="Software", description="Software tools", is_system_category=True)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo
            session.execute.return_value.scalar_one.side_effect = [3, 1]

            resp = client.get("/api/categories/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 1
            assert data["name"] == "Software"
            assert data["transaction_count"] == 3
            assert data["rule_count"] == 1
    finally:
        app.dependency_overrides = {}


def test_api_get_category_not_found(app, client):
    """Verify 404 when category does not exist."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo

            resp = client.get("/api/categories/999")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Category not found"
    finally:
        app.dependency_overrides = {}


def test_api_create_category_success(app, client):
    """Verify creating a custom category."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_name.return_value = None
            mock_repo_cls.return_value = mock_repo

            resp = client.post(
                "/api/categories",
                json={"name": "Health Insurance", "description": "Medical policies"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["name"] == "Health Insurance"
            assert data["description"] == "Medical policies"
            assert data["is_system_category"] is False
            assert session.add.called
            assert session.commit.called
    finally:
        app.dependency_overrides = {}


def test_api_create_category_duplicate_conflict(app, client):
    """Verify 409 when creating a category that already exists."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    existing = Category(id=1, name="Software", description="Existing", is_system_category=True)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_name.return_value = existing
            mock_repo_cls.return_value = mock_repo

            resp = client.post(
                "/api/categories",
                json={"name": "Software", "description": "Duplicate name"},
            )
            assert resp.status_code == 409
            assert "already exists" in resp.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_api_create_category_empty_name(app, client):
    """Verify 400 when category name is empty string or whitespace."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            resp = client.post(
                "/api/categories",
                json={"name": "   ", "description": "test"},
            )
            assert resp.status_code == 400
    finally:
        app.dependency_overrides = {}


def test_api_update_system_category_description_allowed(app, client):
    """Verify description of system categories can be updated."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=1, name="Software", description="Old description", is_system_category=True)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo
            session.execute.return_value.scalar_one.side_effect = [0, 0]

            resp = client.put(
                "/api/categories/1",
                json={"description": "Updated SaaS tools description"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["description"] == "Updated SaaS tools description"
            assert cat.description == "Updated SaaS tools description"
    finally:
        app.dependency_overrides = {}


def test_api_update_system_category_name_forbidden(app, client):
    """Verify system category name cannot be modified."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=1, name="Software", description="Old description", is_system_category=True)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo

            resp = client.put(
                "/api/categories/1",
                json={"name": "New Software Name"},
            )
            assert resp.status_code == 403
            assert "System category names cannot be changed" in resp.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_api_update_custom_category_name_and_desc(app, client):
    """Verify custom category can have its name and description updated."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=10, name="Old Name", description="Old desc", is_system_category=False)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo.get_by_name.return_value = None
            mock_repo_cls.return_value = mock_repo
            session.execute.return_value.scalar_one.side_effect = [0, 0]

            resp = client.put(
                "/api/categories/10",
                json={"name": "New Name", "description": "New desc"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "New Name"
            assert data["description"] == "New desc"
            assert cat.name == "New Name"
    finally:
        app.dependency_overrides = {}


def test_api_delete_system_category_forbidden(app, client):
    """Verify deleting a system category is rejected with 403."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=1, name="Software", description="Desc", is_system_category=True)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo

            resp = client.delete("/api/categories/1")
            assert resp.status_code == 403
            assert "System categories cannot be deleted" in resp.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_api_delete_category_with_transactions_forbidden(app, client):
    """Verify deleting category with active transactions is rejected with 409."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=10, name="Custom Cat", description="Desc", is_system_category=False)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo
            # tx_count = 3
            session.execute.return_value.scalar_one.return_value = 3

            resp = client.delete("/api/categories/10")
            assert resp.status_code == 409
            assert "transaction(s) are still assigned" in resp.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_api_delete_category_with_rules_forbidden(app, client):
    """Verify deleting category with active merchant rules is rejected with 409."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=10, name="Custom Cat", description="Desc", is_system_category=False)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo
            # tx_count = 0, rule_count = 2
            session.execute.return_value.scalar_one.side_effect = [0, 2]

            resp = client.delete("/api/categories/10")
            assert resp.status_code == 409
            assert "rule(s) reference this category" in resp.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_api_delete_custom_category_success(app, client):
    """Verify unreferenced custom category is deleted successfully."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=10, name="Custom Cat", description="Desc", is_system_category=False)

    try:
        with patch("app.api.routes.categories.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = cat
            mock_repo_cls.return_value = mock_repo
            # tx_count = 0, rule_count = 0
            session.execute.return_value.scalar_one.side_effect = [0, 0]

            resp = client.delete("/api/categories/10")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
            assert resp.json()["deleted_category_id"] == 10
            assert session.delete.called
            assert session.commit.called
    finally:
        app.dependency_overrides = {}


def test_web_categories_page(app, client):
    """Verify the /categories HTML page renders with 200 OK and includes category management elements."""
    session = _make_mock_session()
    app.dependency_overrides[get_db_session] = lambda: session
    cat = Category(id=1, name="Software", description="Software tools", is_system_category=True)

    try:
        with patch("app.web.routes.CategoryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.list_categories.return_value = [cat]
            mock_repo_cls.return_value = mock_repo
            session.execute.return_value.scalar_one.return_value = 0

            resp = client.get("/categories")
            assert resp.status_code == 200
            assert "Category Management" in resp.text
            assert "Software" in resp.text
            assert "Create Custom Category" in resp.text
    finally:
        app.dependency_overrides = {}
