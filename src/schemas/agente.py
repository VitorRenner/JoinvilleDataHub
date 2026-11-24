from typing import Any

from pydantic import BaseModel, Field


class PerguntaRequest(BaseModel):
    """
    Pergunta em linguagem natural sobre a economia de Joinville.
    """

    # Teto de tamanho: limita custo e superfície para prompt injection
    pergunta: str = Field(
        min_length=3,
        max_length=300,
        examples=["Quantas empresas ativas existem em Joinville?"],
    )


class ConsultaResponse(BaseModel):
    ferramenta: str
    argumentos: dict[str, Any]
    erro: str | None = None


class PerguntaResponse(BaseModel):
    resposta: str
    resposta_linhas: list[str]
    consultas: list[ConsultaResponse]
    modelo: str
    tokens_entrada: int
    tokens_saida: int
    latencia_ms: int
