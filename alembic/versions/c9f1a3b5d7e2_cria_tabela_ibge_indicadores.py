"""cria tabela ibge_indicadores

Revision ID: c9f1a3b5d7e2
Revises: b8e3f5a1d2c7
Create Date: 2026-11-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9f1a3b5d7e2'
down_revision: Union[str, Sequence[str], None] = 'b8e3f5a1d2c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ibge_indicadores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ano', sa.String(length=4), nullable=False),
        sa.Column('indicador', sa.String(length=50), nullable=False),
        sa.Column('descricao', sa.String(length=200), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False),
        sa.Column('unidade', sa.String(length=30), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'atualizado_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ano', 'indicador', name='uq_ano_indicador_ibge'),
    )
    op.create_index(op.f('ix_ibge_indicadores_id'), 'ibge_indicadores', ['id'], unique=False)
    op.create_index(op.f('ix_ibge_indicadores_ano'), 'ibge_indicadores', ['ano'], unique=False)
    op.create_index(
        op.f('ix_ibge_indicadores_indicador'),
        'ibge_indicadores',
        ['indicador'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ibge_indicadores_indicador'), table_name='ibge_indicadores')
    op.drop_index(op.f('ix_ibge_indicadores_ano'), table_name='ibge_indicadores')
    op.drop_index(op.f('ix_ibge_indicadores_id'), table_name='ibge_indicadores')
    op.drop_table('ibge_indicadores')
