"""unique statements.file_sha256

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 23:59:00
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("statements", schema=None) as batch_op:
        batch_op.drop_index("ix_statements_file_sha256")
        batch_op.create_unique_constraint("uq_statements_file_sha256", ["file_sha256"])


def downgrade() -> None:
    with op.batch_alter_table("statements", schema=None) as batch_op:
        batch_op.drop_constraint("uq_statements_file_sha256", type_="unique")
        batch_op.create_index("ix_statements_file_sha256", ["file_sha256"], unique=False)
