from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CagedBase(BaseModel):
    """
    Campos compartilhados dos registros CAGED.
    """

    competencia: str
    setor: str
    admissoes: int
    demissoes: int
    saldo: int


class CagedCreate(CagedBase):
    """
    Schema utilizado para criação de registros CAGED.
    """

    pass


class CagedBulkCreate(BaseModel):
    """
    Schema utilizado para criação de múltiplos registros CAGED.
    """

    registros: list[CagedCreate]


class CagedResponse(CagedBase):
    """
    Schema utilizado nas respostas da API.
    """

    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
