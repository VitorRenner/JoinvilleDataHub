from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from src.database import repositorio
from src.database.conexao import get_db
from src.schemas.caged import (
    CagedBulkCreate,
    CagedCreate,
    CagedResponse,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[CagedResponse],
)
def listar_caged(
    competencia: str | None = Query(
        None,
        description="Competência no formato YYYYMM",
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
    "/stats/resumo",
)
def estatisticas(
    db: Session = Depends(get_db),
):
    """
    Retorna estatísticas básicas do CAGED.
    """

    return {
        "total_registros": repositorio.contar_registros(db),
    }


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
)
def criar_caged(
    dados: CagedCreate,
    db: Session = Depends(get_db),
):
    """
    Cria ou atualiza um registro do CAGED.
    """

    quantidade = repositorio.upsert_caged(
        db,
        [dados.model_dump()],
    )

    return {
        "message": "Registro criado/atualizado com sucesso.",
        "count": quantidade,
    }


@router.post(
    "/bulk",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def criar_bulk_caged(
    dados: CagedBulkCreate,
    db: Session = Depends(get_db),
):
    """
    Cria ou atualiza múltiplos registros.
    """

    registros = [registro.model_dump() for registro in dados.registros]

    quantidade = repositorio.upsert_caged(
        db,
        registros,
    )

    return {
        "message": f"{quantidade} registros processados.",
        "count": quantidade,
    }


@router.delete(
    "/{registro_id}",
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
