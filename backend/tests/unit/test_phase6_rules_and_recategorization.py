"""Comprehensive Phase 6 Test Suite: Rules Engine, Manual Categorization & Bulk Recategorization.

Tests verify:
1. Manual categorization: category updates, audit trail logging, and flags.
2. Reusable merchant rules: CRUD, validation, regex safety, and priority ordering.
3. Deterministic pattern matching: CONTAINS, EXACT, and REGEX matching engines.
4. Safe bulk recategorization & dry-run preview: protects manual corrections by default,
   allows explicit manual overrides, and audits all changes.
5. Web interface integration: rules management page, pre-fill parameters, and review queue.
"""

from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session
from app.models import Base
from app.models.category import Category
from app.models.classification_event import ClassificationEvent, ClassificationEventType
from app.models.merchant_rule import MerchantRule, RuleMatchType
from app.models.statement import Statement
from app.models.transaction import ReviewStatus, Transaction
from app.services.category_repository import CategoryRepository
from app.services.rule_service import RuleService


# ---------------------------------------------------------------------------
# Test Fixtures with in-memory SQLite for realistic DB transactions
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

    # Seed required categories
    cat_software = Category(id=1, name="Software", description="Software tools", is_system_category=True)
    cat_cloud = Category(id=2, name="Cloud Hosting", description="Cloud infrastructure", is_system_category=True)
    cat_meals = Category(id=3, name="Meals", description="Dining and food", is_system_category=True)
    cat_travel = Category(id=4, name="Travel", description="Business travel", is_system_category=True)
    cat_review = Category(id=5, name="Needs Review", description="Requires review", is_system_category=True)
    cat_custom = Category(id=10, name="Freelance Misc", description="Custom category", is_system_category=False)

    session.add_all([cat_software, cat_cloud, cat_meals, cat_travel, cat_review, cat_custom])

    # Seed a statement
    statement = Statement(
        id=1,
        original_filename="test_statement.csv",
        status="COMPLETED",
        transaction_count=5,
    )
    session.add(statement)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app(db_session):
    """Provide FastAPI app with database dependency overridden to the test session."""
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db_session] = lambda: db_session
    yield fastapi_app
    fastapi_app.dependency_overrides = {}


@pytest.fixture
def client(app):
    """Test client."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _create_transaction(
    db_session,
    description: str,
    amount: Decimal = Decimal("-25.00"),
    category_id: int = 5,  # Needs Review
    was_manual: bool = False,
    review_status: str = ReviewStatus.PENDING,
) -> Transaction:
    """Helper to persist a test transaction."""
    tx = Transaction(
        statement_id=1,
        transaction_date=date(2026, 8, 15),
        original_description=description,
        normalized_description=description.upper(),
        amount=amount,
        currency="USD",
        category_id=category_id,
        confidence_score=0.4 if not was_manual else 1.0,
        classification_reason="Initial rule" if not was_manual else "Manual override",
        review_status=review_status,
        was_manually_categorized=was_manual,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Manual Categorization & Audit Trail
# ---------------------------------------------------------------------------

class TestManualCategorization:
    """Verify manual corrections, flags, and audit event tracking."""

    def test_manual_category_patch_updates_fields(self, client, db_session):
        """PATCH /api/transactions/{id} sets category, manual flag, and reviewed status."""
        tx = _create_transaction(db_session, "MYSTERY MERCHANT CA", category_id=5)

        resp = client.patch(f"/api/transactions/{tx.id}", json={"category_id": 1})
        assert resp.status_code == 200
        data = resp.json()

        assert data["category_id"] == 1
        assert data["category_name"] == "Software"
        assert data["was_manually_categorized"] is True
        assert data["review_status"] == ReviewStatus.REVIEWED

        # Verify DB persistence
        db_session.refresh(tx)
        assert tx.category_id == 1
        assert tx.was_manually_categorized is True
        assert tx.review_status == ReviewStatus.REVIEWED

    def test_manual_categorization_generates_audit_event(self, client, db_session):
        """Verify ClassificationEvent record is created on manual change."""
        tx = _create_transaction(db_session, "COFFEE SHOP", category_id=5)

        resp = client.patch(f"/api/transactions/{tx.id}", json={"category_id": 3})
        assert resp.status_code == 200

        events = db_session.query(ClassificationEvent).filter_by(transaction_id=tx.id).all()
        assert len(events) >= 1
        latest_event = events[-1]
        assert latest_event.event_type == ClassificationEventType.MANUAL_OVERRIDE
        assert latest_event.previous_category_id == 5
        assert latest_event.new_category_id == 3


    def test_manual_categorization_invalid_category_returns_404(self, client, db_session):
        """PATCH with non-existent category ID returns 404."""
        tx = _create_transaction(db_session, "SOME SERVICE", category_id=5)

        resp = client.patch(f"/api/transactions/{tx.id}", json={"category_id": 9999})
        assert resp.status_code == 404

    def test_manual_categorization_nonexistent_transaction_returns_404(self, client):
        """PATCH with non-existent transaction ID returns 404."""
        resp = client.patch("/api/transactions/999999", json={"category_id": 1})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. Reusable Categorization Rules: CRUD & Validation
# ---------------------------------------------------------------------------

class TestRuleManagement:
    """Verify rule creation, validation, priority ordering, updates, and deletion."""

    def test_create_rule_validation_success(self, db_session):
        """Verify RuleService creates rules with valid parameters."""
        service = RuleService(db_session)
        rule = service.create_rule(
            merchant_pattern="GITHUB",
            category_id=1,
            match_type=RuleMatchType.CONTAINS,
            priority=150,
        )
        assert rule.id is not None
        assert rule.merchant_pattern == "GITHUB"
        assert rule.match_type == "CONTAINS"
        assert rule.priority == 150
        assert rule.is_active is True

    def test_create_rule_rejects_empty_pattern(self, db_session):
        """RuleService rejects whitespace-only or empty pattern."""
        service = RuleService(db_session)
        with pytest.raises(ValueError, match="cannot be empty"):
            service.create_rule(merchant_pattern="   ", category_id=1)

    def test_create_rule_rejects_invalid_match_type(self, db_session):
        """RuleService rejects unsupported match type."""
        service = RuleService(db_session)
        with pytest.raises(ValueError, match="Invalid match type"):
            service.create_rule(merchant_pattern="TEST", category_id=1, match_type="FUZZY")

    def test_create_rule_rejects_invalid_regex(self, db_session):
        """RuleService catches bad regex patterns before saving."""
        service = RuleService(db_session)
        with pytest.raises(ValueError, match="Invalid regular expression"):
            service.create_rule(merchant_pattern="[unclosed(regex", category_id=1, match_type=RuleMatchType.REGEX)

    def test_create_rule_rejects_nonexistent_category(self, db_session):
        """RuleService rejects category IDs that do not exist."""
        service = RuleService(db_session)
        with pytest.raises(ValueError, match="does not exist"):
            service.create_rule(merchant_pattern="TEST", category_id=8888)

    def test_list_rules_ordered_by_priority(self, db_session):
        """Rules are returned ordered by priority DESC."""
        service = RuleService(db_session)
        r1 = service.create_rule(merchant_pattern="LOW", category_id=1, priority=50)
        r2 = service.create_rule(merchant_pattern="HIGH", category_id=1, priority=500)
        r3 = service.create_rule(merchant_pattern="MID", category_id=1, priority=200)

        rules = service.list_rules()
        assert [r.id for r in rules] == [r2.id, r3.id, r1.id]

    def test_update_and_toggle_rule(self, db_session):
        """Verify updating pattern, priority, and active toggle."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="SLACK", category_id=1, priority=100)

        # Update
        updated = service.update_rule(rule.id, merchant_pattern="SLACK TECH", priority=250)
        assert updated.merchant_pattern == "SLACK TECH"
        assert updated.priority == 250

        # Toggle inactive
        toggled = service.toggle_rule(rule.id)
        assert toggled.is_active is False

        # Toggle active again
        toggled_again = service.toggle_rule(rule.id)
        assert toggled_again.is_active is True

    def test_delete_rule_safely_preserves_transactions(self, db_session):
        """Deleting a rule removes the rule but leaves transactions intact."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="DIGITALOCEAN", category_id=2)
        tx = _create_transaction(db_session, "DIGITALOCEAN VPS", category_id=2)

        success = service.delete_rule(rule.id)
        assert success is True
        assert service.get_rule(rule.id) is None

        # Verify transaction still exists untouched
        db_session.refresh(tx)
        assert tx.id is not None
        assert tx.category_id == 2


# ---------------------------------------------------------------------------
# 3. Deterministic Rule Matching Logic
# ---------------------------------------------------------------------------

class TestRuleMatchingLogic:
    """Verify CONTAINS, EXACT, and REGEX matching engines."""

    def test_contains_matching(self, db_session):
        """CONTAINS matches substring case-insensitively."""
        rule = MerchantRule(merchant_pattern="GITHUB", match_type=RuleMatchType.CONTAINS, category_id=1)
        tx1 = Transaction(original_description="GITHUB *COPILOT SUB", normalized_description="GITHUB COPILOT SUB")
        tx2 = Transaction(original_description="PAYMENT TO GITHUB INC", normalized_description="PAYMENT TO GITHUB INC")
        tx3 = Transaction(original_description="GITLAB SUBSCRIPTION", normalized_description="GITLAB SUBSCRIPTION")

        assert RuleService.matches_transaction(rule, tx1) is True
        assert RuleService.matches_transaction(rule, tx2) is True
        assert RuleService.matches_transaction(rule, tx3) is False

    def test_exact_matching(self, db_session):
        """EXACT matches full normalized or raw description."""
        rule = MerchantRule(merchant_pattern="STARBUCKS", match_type=RuleMatchType.EXACT, category_id=3)
        tx1 = Transaction(original_description="Starbucks", normalized_description="STARBUCKS")
        tx2 = Transaction(original_description="STARBUCKS STORE #1234", normalized_description="STARBUCKS STORE 1234")

        assert RuleService.matches_transaction(rule, tx1) is True
        assert RuleService.matches_transaction(rule, tx2) is False

    def test_regex_matching(self, db_session):
        """REGEX matches complex patterns."""
        rule = MerchantRule(merchant_pattern=r"AWS\s*EMEA|AMAZON\s*WEB\s*SERVICES", match_type=RuleMatchType.REGEX, category_id=2)
        tx1 = Transaction(original_description="AWS EMEA Cloud Server", normalized_description="AWS EMEA CLOUD SERVER")
        tx2 = Transaction(original_description="AMAZON WEB SERVICES BILL", normalized_description="AMAZON WEB SERVICES BILL")
        tx3 = Transaction(original_description="AMAZON RETAIL PURCHASE", normalized_description="AMAZON RETAIL PURCHASE")

        assert RuleService.matches_transaction(rule, tx1) is True
        assert RuleService.matches_transaction(rule, tx2) is True
        assert RuleService.matches_transaction(rule, tx3) is False


# ---------------------------------------------------------------------------
# 4. Dry-Run Preview & Recategorization Safety
# ---------------------------------------------------------------------------

class TestRuleRecategorizationSafety:
    """Verify dry-run preview and manual protection during bulk recategorization."""

    def test_preview_partitions_transactions_correctly(self, db_session):
        """Preview correctly categorizes eligible, protected manual, and already matching transactions."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="HEROKU", category_id=2)  # Cloud Hosting

        # 1. Eligible transaction (needs review)
        tx_eligible = _create_transaction(db_session, "HEROKU APP SERVER", category_id=5, was_manual=False)
        # 2. Protected manual transaction
        tx_manual = _create_transaction(db_session, "HEROKU POSTGRES DB", category_id=1, was_manual=True)
        # 3. Already matching transaction
        tx_already = _create_transaction(db_session, "HEROKU DYNO INVOICE", category_id=2, was_manual=False)
        # 4. Unrelated transaction
        tx_unrelated = _create_transaction(db_session, "WHOLE FOODS MARKET", category_id=3, was_manual=False)

        preview = service.preview_recategorization(rule.id, override_manual=False)

        assert preview["total_matches"] == 3
        assert preview["eligible_count"] == 1
        assert preview["protected_count"] == 1
        assert preview["already_matching_count"] == 1

        # When override_manual is True, the protected one becomes eligible
        preview_override = service.preview_recategorization(rule.id, override_manual=True)
        assert preview_override["eligible_count"] == 2
        assert preview_override["protected_count"] == 0

    def test_apply_protects_manual_corrections_by_default(self, db_session):
        """CRITICAL: bulk recategorization must NEVER overwrite manual categorizations by default."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="UBER", category_id=4)  # Travel

        # User previously manually set this specific Uber ride to Meals (client meeting)
        tx_manual = _create_transaction(db_session, "UBER TRIP NYC", category_id=3, was_manual=True)
        # Auto-classified Uber ride still Needs Review
        tx_auto = _create_transaction(db_session, "UBER TRIP SFO", category_id=5, was_manual=False)

        result = service.apply_recategorization(rule.id, override_manual=False)

        assert result["updated_count"] == 1
        assert result["protected_count"] == 1

        db_session.refresh(tx_manual)
        db_session.refresh(tx_auto)

        # Manual transaction MUST remain Meals (category 3)
        assert tx_manual.category_id == 3
        assert tx_manual.was_manually_categorized is True

        # Automatic transaction updated to Travel (category 4)
        assert tx_auto.category_id == 4
        assert tx_auto.review_status == ReviewStatus.REVIEWED

    def test_apply_with_explicit_override_updates_manual_transactions(self, db_session):
        """When override_manual=True is explicitly given, manual transactions are updated."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="UBER", category_id=4)  # Travel

        tx_manual = _create_transaction(db_session, "UBER TRIP NYC", category_id=3, was_manual=True)

        result = service.apply_recategorization(rule.id, override_manual=True)

        assert result["updated_count"] == 1
        assert result["protected_count"] == 0

        db_session.refresh(tx_manual)
        assert tx_manual.category_id == 4

    def test_apply_generates_audit_events_for_reclassified_transactions(self, db_session):
        """Bulk recategorization generates ClassificationEvent records for each modified transaction."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="VERCEL", category_id=2)
        tx = _create_transaction(db_session, "VERCEL INC HOSTING", category_id=5, was_manual=False)

        result = service.apply_recategorization(rule.id, override_manual=False)
        assert result["updated_count"] == 1

        events = db_session.query(ClassificationEvent).filter_by(transaction_id=tx.id).all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == ClassificationEventType.RULE_RECLASSIFICATION
        assert event.previous_category_id == 5
        assert event.new_category_id == 2
        assert f"rule #{rule.id}" in event.reason.lower()


# ---------------------------------------------------------------------------
# 5. HTTP API Endpoints for Rules
# ---------------------------------------------------------------------------

class TestRulesApiEndpoints:
    """Verify FastAPI routes: /api/rules, /preview, /apply."""

    def test_api_create_rule(self, client):
        """POST /api/rules creates a rule and returns JSON."""
        resp = client.post(
            "/api/rules",
            json={
                "merchant_pattern": "FIGMA",
                "category_id": 1,
                "match_type": "CONTAINS",
                "priority": 120,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["merchant_pattern"] == "FIGMA"
        assert data["category_name"] == "Software"
        assert data["priority"] == 120

    def test_api_preview_endpoint(self, client, db_session):
        """POST /api/rules/{id}/preview returns dry run summary."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="AIRBNB", category_id=4)
        _create_transaction(db_session, "AIRBNB BOOKING", category_id=5)

        resp = client.post(f"/api/rules/{rule.id}/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rule_id"] == rule.id
        assert data["eligible_count"] == 1
        assert len(data["items"]) == 1


    def test_api_apply_endpoint_enforces_protection(self, client, db_session):
        """POST /api/rules/{id}/apply updates transactions with protection."""
        service = RuleService(db_session)
        rule = service.create_rule(merchant_pattern="AIRBNB", category_id=4)
        _create_transaction(db_session, "AIRBNB BOOKING", category_id=5, was_manual=False)
        _create_transaction(db_session, "AIRBNB WORK EVENT", category_id=3, was_manual=True)

        resp = client.post(f"/api/rules/{rule.id}/apply", json={"override_manual": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert data["protected_count"] == 1


# ---------------------------------------------------------------------------
# 6. Web Page Integration Tests
# ---------------------------------------------------------------------------

class TestPhase6WebPages:
    """Verify server-rendered pages for Rules and Review Queue."""

    def test_rules_page_renders_with_rules(self, client, db_session):
        """GET /rules displays the rules management table and buttons."""
        service = RuleService(db_session)
        service.create_rule(merchant_pattern="JETBRAINS", category_id=1, priority=180)

        resp = client.get("/rules")
        assert resp.status_code == 200
        assert "Rules" in resp.text
        assert "JETBRAINS" in resp.text
        assert "Software" in resp.text

    def test_rules_page_with_prefill_parameters(self, client, db_session):
        """GET /rules?prefill_pattern=Slack&prefill_category_id=1 pre-populates form."""
        resp = client.get("/rules?prefill_pattern=Slack&prefill_category_id=1")
        assert resp.status_code == 200
        assert "Slack" in resp.text

    def test_review_queue_page_renders(self, client, db_session):
        """GET /review displays transactions needing review."""
        _create_transaction(db_session, "UNKNOWN MERCHANT", category_id=5, review_status=ReviewStatus.PENDING)

        resp = client.get("/review")
        assert resp.status_code == 200
        assert "Review" in resp.text
        assert "UNKNOWN MERCHANT" in resp.text
