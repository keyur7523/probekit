"""Initial schema with all tables and new spec fields

Revision ID: 0001
Revises:
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create test_cases table
    op.create_table(
        'test_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('expected_structure', sa.JSON(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        # New spec fields (PRD 1.1-1.5)
        sa.Column('instruction_spec', sa.JSON(), nullable=True),
        sa.Column('format_spec', sa.JSON(), nullable=True),
        sa.Column('stability_params', sa.JSON(), nullable=True),
        sa.Column('should_refuse', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prompt_version', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('models', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('total_duration_ms', sa.Integer(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )

    # Create evaluation_outputs table
    op.create_table(
        'evaluation_outputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_runs.id'), nullable=False),
        sa.Column('test_case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_cases.id'), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('model_response', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
    )

    # Create evaluator_results table
    op.create_table(
        'evaluator_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('output_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_outputs.id'), nullable=False),
        sa.Column('evaluator_name', sa.String(100), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
    )

    # Create human_annotations table
    op.create_table(
        'human_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('output_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_outputs.id'), nullable=False),
        sa.Column('annotation_type', sa.String(50), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('human_annotations')
    op.drop_table('evaluator_results')
    op.drop_table('evaluation_outputs')
    op.drop_table('evaluation_runs')
    op.drop_table('test_cases')
