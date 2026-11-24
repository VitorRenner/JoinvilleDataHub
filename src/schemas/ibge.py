from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IbgeBase(BaseModel):
    ano: str
    indicador: str
    descricao: str
    valor: float
    unidade: str


class IbgeCreate(IbgeBase):
    ano: str = Field(pattern=r"^\d{4}$")
    indicador: str = Field(min_length=1, max_length=50)
    descricao: str = Field(min_length=1, max_length=200)
    valor: float = Field(ge=0)
    unidade: str = Field(min_length=1, max_length=30)


class IbgeResponse(IbgeBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class IbgeIndicadorAtual(BaseModel):
    indicador: str
    descricao: str
    ano: str
    valor: float
    unidade: str


class IbgeResumo(BaseModel):
    total_registros: int
    indicadores: list[str]
    periodos: list[str]
    ultimo_periodo: str | None
