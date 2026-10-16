"""Add is_demo flag to evaluation_runs and backfill seeded runs

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Runs written by scripts/seed_demo_runs.py before this flag existed are
# recognisable by their scripted evaluator results.
SEEDED_RUN_IDS = (
    "SELECT DISTINCT o.run_id FROM evaluation_outputs AS o "
    "JOIN evaluator_results AS r ON r.output_id = o.id "
    "WHERE r.reasoning = 'Seeded result'"
)


def _demo_model_id(model_id: str) -> str:
    return model_id if model_id.startswith("demo-") else f"demo-{model_id}"


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    bind = op.get_bind()
    bind.execute(sa.text(f"UPDATE evaluation_runs SET is_demo = true WHERE id IN ({SEEDED_RUN_IDS})"))

    # Real model names must never appear on scripted data
    bind.execute(sa.text(
        "UPDATE evaluation_outputs SET model = 'demo-' || model "
        "WHERE model NOT LIKE 'demo-%' "
        "AND run_id IN (SELECT id FROM evaluation_runs WHERE is_demo)"
    ))
    rows = bind.execute(sa.text("SELECT id, models FROM evaluation_runs WHERE is_demo")).all()
    for run_id, models in rows:
        if isinstance(models, str):
            models = json.loads(models)
        renamed = [{**m, "model_id": _demo_model_id(m.get("model_id", ""))} for m in models or []]
        bind.execute(
            sa.text("UPDATE evaluation_runs SET models = :models WHERE id = :id")
            .bindparams(sa.bindparam("models", type_=sa.JSON)),
            {"models": renamed, "id": run_id},
        )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "is_demo")
