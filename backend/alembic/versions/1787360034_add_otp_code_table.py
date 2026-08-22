"""add otp_code table

Revision ID: $(date +%s)
Revises: aa956c6cf516
Create Date: $(date -u +"%Y-%m-%d %H:%M:%S")

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '$(date +%s)'
down_revision: Union[str, None] = 'aa956c6cf516'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create otp_code table
    op.create_table(
        'otp_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index(
        'idx_otp_code_recipient_purpose',
        'otp_code',
        ['recipient', 'purpose', 'verified', 'expires_at']
    )


def downgrade() -> None:
    op.drop_index('idx_otp_code_recipient_purpose', table_name='otp_code')
    op.drop_table('otp_code')
