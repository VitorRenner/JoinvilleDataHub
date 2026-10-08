from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.models import CempreEmprego
from src.schemas.cempre import CempreCreate


def buscar_cempre(
        db: Session,
        ano: str | None = None,
        setor: str | None = None,
        skip: int = 0,
        limit: int = 100,
) -> list[CempreEmprego]:
    """
    Busca registros do CEMPRE com filtros opcionais.
    """

    query = db.query(CempreEmprego)

    if ano:
        query = query.filter(
            CempreEmprego.ano == ano,
            )

    if setor:
        query = query.filter(
            CempreEmprego.setor.ilike(f"%{setor}%"),
        )

    return query.offset(skip).limit(limit).all()


def buscar_por_id_cempre(
        db: Session,
        registro_id: int,
) -> CempreEmprego | None:
    """
    Busca um registro do CEMPRE pelo identificador.
    """

    return (
        db.query(CempreEmprego)
        .filter(
            CempreEmprego.id == registro_id,
            )
        .first()
    )


def contar_registros_cempre(
        db: Session,
) -> int:
    """
    Retorna a quantidade total de registros do CEMPRE.
    """

    return db.query(CempreEmprego).count()


def upsert_cempre(
        db: Session,
        registros: list[CempreCreate],
) -> int:
    """
    Cria novos registros ou atualiza existentes usando INSERT ... ON CONFLICT.
    A chave de conflito é (ano, setor).
    """

    if not registros:
        return 0

    stmt = insert(CempreEmprego).values(
        [r.model_dump() for r in registros]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["ano", "setor"],
        set_={
            "unidades_locais": stmt.excluded.unidades_locais,
            "pessoal_ocupado": stmt.excluded.pessoal_ocupado,
            "salario_medio": stmt.excluded.salario_medio,
            "atualizado_em": func.now(),
        },
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def deletar_cempre(
        db: Session,
        registro_id: int,
) -> bool:
    """
    Remove um registro do CEMPRE pelo identificador.
    """

    registro = buscar_por_id_cempre(
        db,
        registro_id,
    )

    if registro is None:
        return False

    db.delete(registro)
    db.commit()

    return True