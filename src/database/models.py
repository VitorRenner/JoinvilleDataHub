from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.conexao import Base


class CagedMovimentacao(Base):
    """
    Modelo da tabela que armazena as movimentações do CAGED.
    """

    __tablename__ = "caged_movimentacao"

    __table_args__ = (
        UniqueConstraint(
            "competencia",
            "setor",
            name="uq_competencia_setor",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    competencia: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        index=True,
    )

    setor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    admissoes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    demissoes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    saldo: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict[str, str | int | None]:
        """
        Converte o modelo para um dicionário.
        """

        return {
            "id": self.id,
            "competencia": self.competencia,
            "setor": self.setor,
            "admissoes": self.admissoes,
            "demissoes": self.demissoes,
            "saldo": self.saldo,
            "criado_em": (self.criado_em.isoformat() if self.criado_em else None),
            "atualizado_em": (
                self.atualizado_em.isoformat() if self.atualizado_em else None
            ),
        }

    def __repr__(self) -> str:
        return (
            "CagedMovimentacao("
            f"id={self.id}, "
            f"competencia='{self.competencia}', "
            f"setor='{self.setor}'"
            ")"
        )
