from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Teto de registros por chamada do /bulk, para um único request não
# derrubar a API nem o banco
CAGED_BULK_MAX_REGISTROS = 1000


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

    As validações ficam só na entrada: a resposta (CagedResponse) não
    pode quebrar por causa de um registro antigo já gravado no banco.
    """

    # Limites iguais aos da tabela (String(7) e String(100))
    competencia: str = Field(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Formato AAAA-MM",
        examples=["2026-09"],
    )
    setor: str = Field(min_length=1, max_length=100)
    admissoes: int = Field(ge=0)
    demissoes: int = Field(ge=0)
    # Saldo pode ser negativo (mais demissões que admissões)
    saldo: int


class CagedBulkCreate(BaseModel):
    """
    Schema utilizado para criação de múltiplos registros CAGED.
    """

    registros: list[CagedCreate] = Field(
        min_length=1,
        max_length=CAGED_BULK_MAX_REGISTROS,
    )


class CagedSerieItem(BaseModel):
    competencia: str
    admissoes: int
    demissoes: int
    saldo: int


class ResumoFonte(BaseModel):
    total_registros: int
    periodos: list[str]
    ultimo_periodo: str | None


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
