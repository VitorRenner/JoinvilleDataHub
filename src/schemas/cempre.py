from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CempreBase(BaseModel):
    """
    Campos compartilhados dos registros CEMPRE.
    """

    ano: str
    setor: str
    # None = valor não divulgado pelo IBGE (sigiloso ou não disponível).
    unidades_locais: int | None = None
    pessoal_ocupado: int | None = None
    salario_medio: float | None = None


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