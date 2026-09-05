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

    return query.offset(skip).limit(limit).all()


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

    stmt = insert(CagedMovimentacao).values(
        [r.model_dump() for r in registros]
    )
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
