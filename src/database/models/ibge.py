from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.conexao import Base


class IbgeIndicador(Base):
    __tablename__ = "ibge_indicadores"

    __table_args__ = (
        UniqueConstraint(
            "ano",
            "indicador",
            name="uq_ano_indicador_ibge",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    ano: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        index=True,
    )

    indicador: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    descricao: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    valor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unidade: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
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
