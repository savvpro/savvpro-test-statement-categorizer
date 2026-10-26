"""Pytest configuration and synthetic fixtures for LedgerLens tests.

All test data is purely synthetic with no real personal or banking information.
"""

from decimal import Decimal
import pytest

from app.schemas.transaction import TransactionInput
from app.services.categorizer import CategorizationEngine


@pytest.fixture
def engine() -> CategorizationEngine:
    """Provide a freshly initialized categorization engine."""
    return CategorizationEngine()


@pytest.fixture
def synthetic_software_tx() -> TransactionInput:
    """Synthetic developer software transaction."""
    return TransactionInput(
        original_description="GITHUB *COPILOT SUB",
        amount=Decimal("-10.00"),
    )


@pytest.fixture
def synthetic_cloud_tx() -> TransactionInput:
    """Synthetic cloud hosting transaction."""
    return TransactionInput(
        original_description="DIGITALOCEAN.COM VPS CLOUD",
        amount=Decimal("-24.00"),
    )


@pytest.fixture
def synthetic_income_tx() -> TransactionInput:
    """Synthetic freelance client income transaction."""
    return TransactionInput(
        original_description="CLIENT PAYMENT - ACME CORP CONSULTING",
        amount=Decimal("1500.00"),
    )
