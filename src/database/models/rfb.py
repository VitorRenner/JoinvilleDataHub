from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.conexao import Base


class RfbEmpresa(Base):
    """
    Modelo da tabela que armazena os dados mensais agregados da RFB
    (cadastro de CNPJ da Receita Federal), por competência e setor.
    """

    __tablename__ = "rfb_empresas"

    __table_args__ = (
        UniqueConstraint(
            "competencia",
            "setor",
            name="uq_competencia_setor_rfb",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Formato AAAA-MM (com traço), por isso 7 caracteres.
    competencia: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )

    setor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Contagens calculadas pelo próprio projeto a partir do cadastro:
    # ausência de empresas é zero de verdade, por isso NOT NULL com default 0.
    ativas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    aberturas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    encerramentos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    ativas_mei: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    ativas_simples: Mapped[int] = mapped_column(
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
            "ativas": self.ativas,
            "aberturas": self.aberturas,
            "encerramentos": self.encerramentos,
            "ativas_mei": self.ativas_mei,
            "ativas_simples": self.ativas_simples,
            "criado_em": (self.criado_em.isoformat() if self.criado_em else None),
            "atualizado_em": (
                self.atualizado_em.isoformat() if self.atualizado_em else None
            ),
        }

    def __repr__(self) -> str:
        return (
            "RfbEmpresa("
            f"id={self.id}, "
            f"competencia='{self.competencia}', "
            f"setor='{self.setor}'"
            ")"
        )
