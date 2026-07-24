import logging

from src.database import models  # noqa: F401
from src.database.conexao import Base, engine

logger = logging.getLogger(__name__)


def criar_tabelas() -> None:
    """
    Cria as tabelas definidas nos modelos SQLAlchemy.
    """

    try:
        Base.metadata.create_all(
            bind=engine,
        )

        logger.info(
            "Tabelas criadas com sucesso.",
        )

    except Exception:
        logger.exception(
            "Erro ao criar tabelas.",
        )
        raise


if __name__ == "__main__":
    criar_tabelas()
