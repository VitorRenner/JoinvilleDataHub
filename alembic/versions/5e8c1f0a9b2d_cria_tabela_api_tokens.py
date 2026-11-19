"""cria tabela api_tokens

Revision ID: 5e8c1f0a9b2d
Revises: 3101cdc26c6d
Create Date: 2026-11-19 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e8c1f0a9b2d'
down_revision: Union[str, Sequence[str], None] = '3101cdc26c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('api_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('descricao', sa.String(length=100), nullable=False),
    sa.Column('criado_em', sa.BigInteger(), nullable=False),
    sa.Column('expira_em', sa.BigInteger(), nullable=False),
    sa.Column('usado_em', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_tokens_token_hash'), 'api_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_api_tokens_token_hash'), table_name='api_tokens')
    op.drop_table('api_tokens')
