from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.models import IbgeIndicador
from src.schemas.ibge import IbgeCreate


def buscar_ibge(
    db: Session,
    indicador: str | None = None,
    ano: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[IbgeIndicador]:
    query = db.query(IbgeIndicador)

    if indicador:
        query = query.filter(IbgeIndicador.indicador == indicador)

    if ano:
        query = query.filter(IbgeIndicador.ano == ano)

    return (
        query.order_by(IbgeIndicador.indicador, IbgeIndicador.ano)
        .offset(skip)
        .limit(limit)
        .all()
    )


def buscar_por_id_ibge(
    db: Session,
    registro_id: int,
) -> IbgeIndicador | None:
    return db.query(IbgeIndicador).filter(IbgeIndicador.id == registro_id).first()


def buscar_mais_recentes_ibge(
    db: Session,
) -> list[IbgeIndicador]:
    ultimo_ano = (
        db.query(
            IbgeIndicador.indicador,
            func.max(IbgeIndicador.ano).label("ano"),
        )
        .group_by(IbgeIndicador.indicador)
        .subquery()
    )

    return (
        db.query(IbgeIndicador)
        .join(
            ultimo_ano,
            (IbgeIndicador.indicador == ultimo_ano.c.indicador)
            & (IbgeIndicador.ano == ultimo_ano.c.ano),
        )
        .order_by(IbgeIndicador.indicador)
        .all()
    )


def contar_registros_ibge(
    db: Session,
) -> int:
    return db.query(IbgeIndicador).count()


def listar_indicadores_ibge(
    db: Session,
) -> list[str]:
    linhas = (
        db.query(IbgeIndicador.indicador)
        .distinct()
        .order_by(IbgeIndicador.indicador)
        .all()
    )
    return [linha[0] for linha in linhas]


def listar_anos_ibge(
    db: Session,
) -> list[str]:
    linhas = db.query(IbgeIndicador.ano).distinct().order_by(IbgeIndicador.ano).all()
    return [linha[0] for linha in linhas]


def upsert_ibge(
    db: Session,
    registros: list[IbgeCreate],
) -> int:
    if not registros:
        return 0

    stmt = insert(IbgeIndicador).values([r.model_dump() for r in registros])
    stmt = stmt.on_conflict_do_update(
        index_elements=["ano", "indicador"],
        set_={
            "descricao": stmt.excluded.descricao,
            "valor": stmt.excluded.valor,
            "unidade": stmt.excluded.unidade,
            "atualizado_em": func.now(),
        },
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount
