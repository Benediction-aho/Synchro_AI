"""add_id_to_equity_snapshots_remove_composite_pk

Revision ID: 97c718699a50
Revises: bd37c658741a
Create Date: 2026-08-28 00:33:33.609490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '97c718699a50'
down_revision: Union[str, Sequence[str], None] = 'bd37c658741a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add id column, drop composite PK, add new PK and index."""
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    # 1. Add new id column (autoincrement for PostgreSQL, regular Integer for SQLite)
    if is_postgresql:
        op.add_column('equity_snapshots', sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False))
    else:
        op.add_column('equity_snapshots', sa.Column('id', sa.Integer(), nullable=False, autoincrement=True))
    
    # 2. Populate id values for existing rows
    if is_postgresql:
        op.execute("UPDATE equity_snapshots SET id = nextval(pg_get_serial_sequence('equity_snapshots', 'id'))")
    else:
        # SQLite auto-assigns on insert, but for existing rows we need to update
        op.execute("UPDATE equity_snapshots SET id = rowid")
    
    # 3. Drop the old composite primary key
    op.drop_constraint('equity_snapshots_pkey', 'equity_snapshots', type_='primary')
    
    # 4. Add new primary key on id
    op.create_primary_key('equity_snapshots_pkey', 'equity_snapshots', ['id'])
    
    # 5. Create index on (account_id, timestamp) for time-series queries
    op.create_index('ix_equity_snapshots_account_id_timestamp', 'equity_snapshots', ['account_id', 'timestamp'])


def downgrade() -> None:
    """Downgrade schema: restore composite primary key."""
    # 1. Drop the index
    op.drop_index('ix_equity_snapshots_account_id_timestamp', table_name='equity_snapshots')
    
    # 2. Drop the primary key on id
    op.drop_constraint('equity_snapshots_pkey', 'equity_snapshots', type_='primary')
    
    # 5. Drop the id column
    op.drop_column('equity_snapshots', 'id')
    
    # 6. Recreate composite primary key on (account_id, timestamp)
    op.create_primary_key('equity_snapshots_pkey', 'equity_snapshots', ['account_id', 'timestamp'])