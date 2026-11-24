from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from src.database import repositorio_ibge
from src.database.conexao import get_db
from src.schemas.ibge import IbgeIndicadorAtual, IbgeResponse, IbgeResumo

router = APIRouter()


@router.get(
    "/",
    response_model=list[IbgeResponse],
    summary="Série anual dos indicadores do IBGE para Joinville",
)
def listar_ibge(
    indicador: str | None = Query(
        None,
        description="populacao_estimada, pib ou participacao_pib_sc",
        examples=["pib"],
    ),
    ano: str | None = Query(
        None,
        pattern=r"^\d{4}$",
        description="Ano no formato AAAA",
        examples=["2023"],
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return repositorio_ibge.buscar_ibge(db, indicador, ano, skip, limit)


@router.get(
    "/joinville",
    response_model=list[IbgeIndicadorAtual],
    summary="Valor mais recente de cada indicador do IBGE",
)
def indicadores_atuais(
    db: Session = Depends(get_db),
):
    return repositorio_ibge.buscar_mais_recentes_ibge(db)


@router.get(
    "/stats/resumo",
    response_model=IbgeResumo,
    summary="Resumo dos dados do IBGE",
)
def estatisticas_ibge(
    db: Session = Depends(get_db),
):
    periodos = repositorio_ibge.listar_anos_ibge(db)
    return IbgeResumo(
        total_registros=repositorio_ibge.contar_registros_ibge(db),
        indicadores=repositorio_ibge.listar_indicadores_ibge(db),
        periodos=periodos,
        ultimo_periodo=periodos[-1] if periodos else None,
    )


@router.get(
    "/{registro_id}",
    response_model=IbgeResponse,
    summary="Busca um indicador do IBGE pelo ID",
)
def buscar_ibge_por_id(
    registro_id: int,
    db: Session = Depends(get_db),
):
    registro = repositorio_ibge.buscar_por_id_ibge(db, registro_id)

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        )

    return registro
