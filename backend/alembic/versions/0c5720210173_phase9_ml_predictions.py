"""phase9_ml_predictions

Revision ID: 0c5720210173
Revises: aa956c6cf516
Create Date: 2026-08-22 04:56:06.637766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c5720210173'
down_revision: Union[str, None] = 'aa956c6cf516'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ml_prediction table already exists -- migration was applied outside of alembic
    # Verify and skip if exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if 'ml_prediction' not in tables:
        op.create_table('ml_prediction',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_name', sa.String(length=255), autoincrement=False, nullable=False),
        sa.Column('model_version', sa.String(length=255), autoincrement=False, nullable=False),
        sa.Column('input_features', sa.JSON(), autoincrement=False, nullable=False),
        sa.Column('prediction_output', sa.JSON(), autoincrement=False, nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), autoincrement=False, nullable=True),
        sa.Column('entity_type', sa.String(length=255), autoincrement=False, nullable=True),
        sa.Column('entity_id', sa.String(length=255), autoincrement=False, nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    # Only drop ml_prediction if this migration created it
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if 'ml_prediction' in tables:
        op.drop_table('ml_prediction')
