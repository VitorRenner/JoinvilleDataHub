from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from src.database import repositorio_rfb
from src.database.conexao import get_db
from src.schemas.rfb import RfbResponse

# A RFB é dado oficial da Receita Federal: quem grava no banco é só o
# service (atualizacao_rfb). Por isso este router expõe apenas leitura.
router = APIRouter()


@router.get(
    "/",
    response_model=list[RfbResponse],
)
def listar_rfb(
        competencia: str | None = Query(
            None,
            pattern=r"^\d{4}-\d{2}$",
            description="Competência no formato AAAA-MM",
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
                    "Inclui a linha 'Total' (soma de todos os setores). "
                    "Use false para somar ou comparar setores sem contar em dobro."
            ),
        ),
        db: Session = Depends(get_db),
):
    """
    Lista registros agregados da RFB.
    """

    return repositorio_rfb.buscar_rfb(
        db,
        competencia,
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
def estatisticas_rfb(
        db: Session = Depends(get_db),
):
    """
    Retorna o total de registros e as competências disponíveis da RFB.
    """

    return {
        "total_registros": repositorio_rfb.contar_registros_rfb(db),
        "competencias": repositorio_rfb.listar_competencias_rfb(db),
    }


@router.get(
    "/{registro_id}",
    response_model=RfbResponse,
)
def buscar_rfb_por_id(
        registro_id: int,
        db: Session = Depends(get_db),
):
    """
    Busca um registro específico da RFB pelo ID.
    """

    registro = repositorio_rfb.buscar_por_id_rfb(
        db,
        registro_id,
    )

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        )

    return registro