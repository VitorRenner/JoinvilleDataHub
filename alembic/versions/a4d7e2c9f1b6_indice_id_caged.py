"""indice ix_caged_movimentacao_id

Revision ID: a4d7e2c9f1b6
Revises: 5e8c1f0a9b2d
Create Date: 2026-11-24 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a4d7e2c9f1b6'
down_revision: Union[str, Sequence[str], None] = '5e8c1f0a9b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        op.f('ix_caged_movimentacao_id'),
        'caged_movimentacao',
        ['id'],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_caged_movimentacao_id'),
        table_name='caged_movimentacao',
        if_exists=True,
    )
