from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from src.database import repositorio_cempre
from src.database.conexao import get_db
from src.schemas.cempre import CempreResponse

# O CEMPRE é dado oficial do IBGE: quem grava no banco é só o service
# (atualizacao_cempre). Por isso este router expõe apenas leitura.
router = APIRouter()


@router.get(
    "/",
    response_model=list[CempreResponse],
)
def listar_cempre(
        ano: str | None = Query(
            None,
            description="Ano de referência no formato YYYY",
        ),
        setor: str | None = Query(
            None,
            description="Nome (ou parte do nome) da seção da CNAE",
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
        incluir_total: bool = Query(
            True,
            description=(
                    "Inclui a linha 'Total' (soma de todas as seções). "
                    "Use false para somar ou comparar setores sem contar em dobro."
            ),
        ),
        db: Session = Depends(get_db),
):
    """
    Lista registros do CEMPRE.
    """

    return repositorio_cempre.buscar_cempre(
        db,
        ano,
        setor,
        skip,
        limit,
        incluir_total,
    )

# Precisa vir ANTES de "/{registro_id}". Senão o FastAPI tenta ler
# "stats" como um id numérico e devolve 422.
@router.get(
    "/stats/resumo",
)
def estatisticas_cempre(
        db: Session = Depends(get_db),
):
    """
    Retorna estatísticas básicas do CEMPRE.
    """

    return {
        "total_registros": repositorio_cempre.contar_registros_cempre(db),
    }


@router.get(
    "/{registro_id}",
    response_model=CempreResponse,
)
def buscar_cempre_por_id(
        registro_id: int,
        db: Session = Depends(get_db),
):
    """
    Busca um registro específico do CEMPRE pelo ID.
    """

    registro = repositorio_cempre.buscar_por_id_cempre(
        db,
        registro_id,
    )

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        )

    return registro