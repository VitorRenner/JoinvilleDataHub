from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from src.core.security import exigir_token_uso_unico
from src.database import repositorio
from src.database.conexao import get_db
from src.schemas.caged import (
    CagedBulkCreate,
    CagedCreate,
    CagedResponse,
    CagedSerieItem,
    ResumoFonte,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[CagedResponse],
)
def listar_caged(
    competencia: str | None = Query(
        None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Competência no formato AAAA-MM",
        examples=["2026-09"],
    ),
    setor: str | None = Query(
        None,
        description="Nome do setor",
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Quantidade de registros para pular",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Quantidade máxima de registros",
    ),
    db: Session = Depends(get_db),
):
    """
    Lista registros do CAGED.
    """

    return repositorio.buscar_caged(
        db,
        competencia,
        setor,
        skip,
        limit,
    )


@router.get(
    "/serie",
    response_model=list[CagedSerieItem],
    summary="Totais de Joinville por competência",
)
def serie_caged(
    competencia_inicial: str | None = Query(
        None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        examples=["2024-01"],
    ),
    competencia_final: str | None = Query(
        None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        examples=["2026-09"],
    ),
    db: Session = Depends(get_db),
):
    return repositorio.buscar_serie_caged(
        db,
        competencia_inicial,
        competencia_final,
    )


@router.get(
    "/stats/resumo",
    response_model=ResumoFonte,
)
def estatisticas(
    db: Session = Depends(get_db),
):
    """
    Retorna estatísticas básicas do CAGED.
    """

    periodos = repositorio.listar_competencias_caged(db)
    return ResumoFonte(
        total_registros=repositorio.contar_registros(db),
        periodos=periodos,
        ultimo_periodo=periodos[-1] if periodos else None,
    )


@router.get(
    "/{registro_id}",
    response_model=CagedResponse,
)
def buscar_caged_por_id(
    registro_id: int,
    db: Session = Depends(get_db),
):
    """
    Busca um registro específico pelo ID.
    """

    registro = repositorio.buscar_por_id(
        db,
        registro_id,
    )

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        )

    return registro


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_token_uso_unico)],
)
def criar_caged(
    dados: CagedCreate,
    db: Session = Depends(get_db),
):
    """
    Cria ou atualiza um registro do CAGED.
    """

    # upsert_caged recebe os schemas (ele mesmo faz o model_dump)
    quantidade = repositorio.upsert_caged(
        db,
        [dados],
    )

    return {
        "message": "Registro criado/atualizado com sucesso.",
        "count": quantidade,
    }


@router.post(
    "/bulk",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_token_uso_unico)],
)
def criar_bulk_caged(
    dados: CagedBulkCreate,
    db: Session = Depends(get_db),
):
    """
    Cria ou atualiza múltiplos registros.
    """

    quantidade = repositorio.upsert_caged(
        db,
        dados.registros,
    )

    return {
        "message": f"{quantidade} registros processados.",
        "count": quantidade,
    }


@router.delete(
    "/{registro_id}",
    dependencies=[Depends(exigir_token_uso_unico)],
)
def deletar_caged(
    registro_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove um registro pelo ID.
    """

    sucesso = repositorio.deletar_caged(
        db,
        registro_id,
    )

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        )

    return {
        "message": "Registro deletado com sucesso.",
    }
