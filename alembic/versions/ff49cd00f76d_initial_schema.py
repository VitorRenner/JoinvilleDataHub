"""initial schema

Revision ID: ff49cd00f76d
Revises: 
Create Date: 2026-07-27 14:16:20.043276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ff49cd00f76d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create caged_movimentacao table."""
    op.create_table(
        'caged_movimentacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competencia', sa.String(length=6), nullable=False),
        sa.Column('setor', sa.String(length=100), nullable=False),
        sa.Column('admissoes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('demissoes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('saldo', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competencia', 'setor', name='uq_competencia_setor')
    )
    op.create_index(op.f('ix_caged_movimentacao_competencia'), 'caged_movimentacao', ['competencia'], unique=False)
    op.create_index(op.f('ix_caged_movimentacao_setor'), 'caged_movimentacao', ['setor'], unique=False)


def downgrade() -> None:
    """Drop caged_movimentacao table."""
    op.drop_index(op.f('ix_caged_movimentacao_setor'), table_name='caged_movimentacao')
    op.drop_index(op.f('ix_caged_movimentacao_competencia'), table_name='caged_movimentacao')
    op.drop_table('caged_movimentacao')