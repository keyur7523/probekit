"""Add condition and model_id to conversation_turns

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("condition", sa.String(50), nullable=True))
    op.add_column("conversation_turns", sa.Column("model_id", sa.String(100), nullable=True))

    op.execute(
        "UPDATE conversation_turns AS ct "
        "SET condition = cr.condition, model_id = cr.model "
        "FROM conversation_runs AS cr "
        "WHERE ct.run_id = cr.id"
    )

    op.alter_column("conversation_turns", "condition", nullable=False)
    op.alter_column("conversation_turns", "model_id", nullable=False)


def downgrade() -> None:
    op.drop_column("conversation_turns", "model_id")
    op.drop_column("conversation_turns", "condition")
