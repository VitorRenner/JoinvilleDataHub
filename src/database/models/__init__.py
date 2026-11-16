"""
Modelos do banco de dados, um arquivo por fonte de dados.

Este pacote reexporta todas as classes para manter compatíveis os imports
`from src.database.models import ...` e para registrar todas as tabelas
no Base.metadata (necessário para o Alembic e para o create_all).
"""

from src.database.models.caged import CagedMovimentacao
from src.database.models.cempre import CempreEmprego
from src.database.models.rfb import RfbEmpresa

__all__ = [
    "CagedMovimentacao",
    "CempreEmprego",
    "RfbEmpresa",
]
