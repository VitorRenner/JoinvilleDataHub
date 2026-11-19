from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.conexao import Base


class ApiToken(Base):
    """
    Token de uso único para as rotas de escrita.

    Só o hash SHA-256 fica no banco: quem lê a tabela não consegue usar o
    token. Os instantes são epoch em segundos (UTC) para a comparação de
    validade ser igual no PostgreSQL e no SQLite dos testes.
    """

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # Para que o token foi emitido (auditoria)
    descricao: Mapped[str] = mapped_column(String(100), nullable=False)

    criado_em: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expira_em: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # NULL = ainda não usado; preenchido no consumo, nunca volta a NULL
    usado_em: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:
        return (
            f"ApiToken(id={self.id}, descricao='{self.descricao}', "
            f"usado={self.usado_em is not None})"
        )
