"""phase8_aml_compliance_reporting

Revision ID: aa956c6cf516
Revises: ee5100495913
Create Date: 2026-08-22 04:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa956c6cf516'
down_revision: Union[str, None] = 'ee5100495913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables were already created -- this migration was retroactively added to
    # match the database state. Actual table creation happened outside of alembic.
    pass


def downgrade() -> None:
    # Cannot safely downgrade -- tables may contain data
    pass
