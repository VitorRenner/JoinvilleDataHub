"""cempre: colunas numericas aceitam null

Revision ID: 7b2e4d9a1c3f
Revises: c54a3a3e7feb
Create Date: 2026-10-15 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b2e4d9a1c3f'
down_revision: Union[str, Sequence[str], None] = 'c54a3a3e7feb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUNAS = (
    ("unidades_locais", sa.Integer()),
    ("pessoal_ocupado", sa.Integer()),
    ("salario_medio", sa.Float()),
)


def upgrade() -> None:
    """Upgrade schema."""
    # Libera NULL nas colunas numéricas: NULL passa a significar
    # "valor não divulgado pelo IBGE" (X = sigiloso, ... = não disponível).
    for coluna, tipo in COLUNAS:
        op.alter_column(
            'cempre_emprego',
            coluna,
            existing_type=tipo,
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Antes de voltar para NOT NULL, os NULLs precisam virar 0. Sem isso
    # o ALTER falha se já houver algum valor ausente gravado.
    for coluna, tipo in COLUNAS:
        op.execute(
            f"UPDATE cempre_emprego SET {coluna} = 0 WHERE {coluna} IS NULL"
        )

        op.alter_column(
            'cempre_emprego',
            coluna,
            existing_type=tipo,
            nullable=False,
        )