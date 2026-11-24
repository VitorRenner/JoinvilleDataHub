"""caged competencia no formato AAAA-MM

Revision ID: b8e3f5a1d2c7
Revises: a4d7e2c9f1b6
Create Date: 2026-11-24 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e3f5a1d2c7'
down_revision: Union[str, Sequence[str], None] = 'a4d7e2c9f1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'caged_movimentacao',
        'competencia',
        existing_type=sa.String(length=6),
        type_=sa.String(length=7),
        existing_nullable=False,
    )
    op.execute(
        "UPDATE caged_movimentacao "
        "SET competencia = SUBSTRING(competencia, 1, 4) || '-' "
        "|| SUBSTRING(competencia, 5, 2) "
        "WHERE competencia ~ '^[0-9]{6}$'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE caged_movimentacao "
        "SET competencia = REPLACE(competencia, '-', '') "
        "WHERE competencia ~ '^[0-9]{4}-[0-9]{2}$'"
    )
    op.alter_column(
        'caged_movimentacao',
        'competencia',
        existing_type=sa.String(length=7),
        type_=sa.String(length=6),
        existing_nullable=False,
    )
