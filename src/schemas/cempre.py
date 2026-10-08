from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CempreBase(BaseModel):
    """
    Campos compartilhados dos registros CEMPRE.
    """

    ano: str
    setor: str
    unidades_locais: int
    pessoal_ocupado: int
    salario_medio: float


class CempreCreate(CempreBase):
    """
    Schema utilizado para criação de registros CEMPRE.
    """

    pass


class CempreBulkCreate(BaseModel):
    """
    Schema utilizado para criação de múltiplos registros CEMPRE.
    """

    registros: list[CempreCreate]


class CempreResponse(CempreBase):
    """
    Schema utilizado nas respostas da API.
    """

    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )