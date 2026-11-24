from dataclasses import asdict
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.agent.agente import Agente, AgenteIndisponivel
from src.agent.limites import LimiteDeUso
from src.core.settings import settings
from src.database.conexao import get_db
from src.schemas.agente import PerguntaRequest, PerguntaResponse

router = APIRouter()

limite = LimiteDeUso(
    por_minuto_por_ip=settings.AGENTE_LIMITE_POR_MINUTO,
    por_dia_total=settings.AGENTE_LIMITE_DIARIO,
)


@lru_cache(maxsize=1)
def _agente_padrao() -> Agente:
    # Import tardio: a API sobe e os testes rodam sem criar cliente real
    from google import genai
    from google.genai import types

    cliente = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=settings.AGENTE_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(
                attempts=settings.AGENTE_TENTATIVAS,
                initial_delay=0.2,
                max_delay=1.0,
            ),
        ),
    )
    return Agente(
        cliente=cliente,
        modelo=settings.GEMINI_MODEL,
        max_passos=settings.AGENTE_MAX_PASSOS,
        thinking_level=settings.AGENTE_THINKING_LEVEL or None,
    )


def get_agente() -> Agente:
    """
    Dependência do agente; sem GEMINI_API_KEY o recurso fica desligado.
    Os testes sobrescrevem com um agente que usa um modelo falso.
    """

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agente desabilitado: GEMINI_API_KEY não configurada.",
        )
    return _agente_padrao()


@router.post(
    "",
    response_model=PerguntaResponse,
    summary="Pergunta em linguagem natural sobre a economia de Joinville",
)
def perguntar(
    dados: PerguntaRequest,
    request: Request,
    db: Session = Depends(get_db),
    agente: Agente = Depends(get_agente),
):
    """
    Responde com dados oficiais da API. O modelo só usa ferramentas de
    leitura; a resposta lista as consultas feitas, tokens e latência.
    """

    ip = request.client.host if request.client else "desconhecido"
    permitido, motivo = limite.permitir(ip)
    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=motivo,
        )

    try:
        resultado = agente.perguntar(db, dados.pergunta)
    except AgenteIndisponivel as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O modelo de IA não respondeu. Tente de novo em instantes.",
        ) from exc

    return PerguntaResponse(
        resposta=resultado.resposta,
        resposta_linhas=[
            linha.strip() for linha in resultado.resposta.splitlines() if linha.strip()
        ],
        consultas=[asdict(consulta) for consulta in resultado.consultas],
        modelo=resultado.modelo,
        tokens_entrada=resultado.tokens_entrada,
        tokens_saida=resultado.tokens_saida,
        latencia_ms=resultado.latencia_ms,
    )
