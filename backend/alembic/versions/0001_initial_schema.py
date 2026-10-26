"""Initial database schema for LedgerLens.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-27 00:00:00

Creates the core 5 tables:
- categories
- statements
- transactions
- merchant_rules
- classification_events
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_system_category", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )
    op.create_index("ix_categories_name", "categories", ["name"])

    # 2. Statements table
    op.create_table(
        "statements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("transaction_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_statements_status", "statements", ["status"])

    # 3. Transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("statement_id", sa.Integer(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("original_description", sa.String(length=500), nullable=False),
        sa.Column("normalized_description", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("classification_reason", sa.String(length=500), nullable=False),
        sa.Column("review_status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("was_manually_categorized", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["statement_id"], ["statements.id"], name="fk_transactions_statement_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name="fk_transactions_category_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_statement_id", "transactions", ["statement_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_review_status", "transactions", ["review_status"])

    # 4. Merchant rules table
    op.create_table(
        "merchant_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("merchant_pattern", sa.String(length=255), nullable=False),
        sa.Column("match_type", sa.String(length=32), server_default=sa.text("'CONTAINS'"), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name="fk_merchant_rules_category_id", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_rules_category_id", "merchant_rules", ["category_id"])

    # 5. Classification events table
    op.create_table(
        "classification_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("previous_category_id", sa.Integer(), nullable=True),
        sa.Column("new_category_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), server_default=sa.text("'AUTO_CLASSIFIED'"), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], name="fk_events_transaction_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["previous_category_id"], ["categories.id"], name="fk_events_previous_category_id", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["new_category_id"], ["categories.id"], name="fk_events_new_category_id", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classification_events_tx_id", "classification_events", ["transaction_id"])
    op.create_index("ix_classification_events_type", "classification_events", ["event_type"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("classification_events")
    op.drop_table("merchant_rules")
    op.drop_table("transactions")
    op.drop_table("statements")
    op.drop_table("categories")
