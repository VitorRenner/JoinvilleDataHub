from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.models import CagedMovimentacao
from src.schemas.caged import CagedCreate


def buscar_caged(
    db: Session,
    competencia: str | None = None,
    setor: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CagedMovimentacao]:
    """
    Busca registros do CAGED com filtros opcionais.
    """

    query = db.query(CagedMovimentacao)

    if competencia:
        query = query.filter(
            CagedMovimentacao.competencia == competencia,
        )

    if setor:
        query = query.filter(
            CagedMovimentacao.setor.ilike(f"%{setor}%"),
        )

    return (
        query.order_by(
            CagedMovimentacao.competencia,
            CagedMovimentacao.setor,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def buscar_por_id(
    db: Session,
    registro_id: int,
) -> CagedMovimentacao | None:
    """
    Busca um registro do CAGED pelo identificador.
    """

    return (
        db.query(CagedMovimentacao)
        .filter(
            CagedMovimentacao.id == registro_id,
        )
        .first()
    )


def contar_registros(
    db: Session,
) -> int:
    """
    Retorna a quantidade total de registros cadastrados.
    """

    return db.query(CagedMovimentacao).count()


def listar_competencias_caged(
    db: Session,
) -> list[str]:
    linhas = (
        db.query(CagedMovimentacao.competencia)
        .distinct()
        .order_by(CagedMovimentacao.competencia)
        .all()
    )
    return [linha[0] for linha in linhas]


def buscar_serie_caged(
    db: Session,
    competencia_inicial: str | None = None,
    competencia_final: str | None = None,
) -> list[dict]:
    query = db.query(
        CagedMovimentacao.competencia,
        func.sum(CagedMovimentacao.admissoes).label("admissoes"),
        func.sum(CagedMovimentacao.demissoes).label("demissoes"),
        func.sum(CagedMovimentacao.saldo).label("saldo"),
    )

    if competencia_inicial:
        query = query.filter(CagedMovimentacao.competencia >= competencia_inicial)

    if competencia_final:
        query = query.filter(CagedMovimentacao.competencia <= competencia_final)

    linhas = (
        query.group_by(CagedMovimentacao.competencia)
        .order_by(CagedMovimentacao.competencia)
        .all()
    )

    return [
        {
            "competencia": linha.competencia,
            "admissoes": int(linha.admissoes),
            "demissoes": int(linha.demissoes),
            "saldo": int(linha.saldo),
        }
        for linha in linhas
    ]


def upsert_caged(
    db: Session,
    registros: list[CagedCreate],
) -> int:
    """
    Cria novos registros ou atualiza existentes usando INSERT ... ON CONFLICT.
    A chave de conflito é (competencia, setor).
    """

    if not registros:
        return 0

    stmt = insert(CagedMovimentacao).values([r.model_dump() for r in registros])
    stmt = stmt.on_conflict_do_update(
        index_elements=["competencia", "setor"],
        set_={
            "admissoes": stmt.excluded.admissoes,
            "demissoes": stmt.excluded.demissoes,
            "saldo": stmt.excluded.saldo,
            "atualizado_em": func.now(),
        },
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def substituir_serie_caged(
    db: Session,
    registros: list[CagedCreate],
) -> int:
    """
    Substitui a série inteira do CAGED numa única transação.

    A série é recalculada do zero a cada atualização (FOR e EXC de meses
    novos alteram meses antigos), então apagar e regravar mantém o banco
    igual ao cálculo, sem linha velha sobrando. Se algo falhar, o rollback
    devolve a série anterior intacta.
    """

    if not registros:
        raise ValueError("Série do CAGED vazia: nada foi alterado no banco.")

    try:
        db.query(CagedMovimentacao).delete()
        db.add_all(CagedMovimentacao(**r.model_dump()) for r in registros)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return len(registros)


def deletar_caged(
    db: Session,
    registro_id: int,
) -> bool:
    """
    Remove um registro do CAGED pelo identificador.
    """

    registro = buscar_por_id(
        db,
        registro_id,
    )

    if registro is None:
        return False

    db.delete(registro)
    db.commit()

    return True
