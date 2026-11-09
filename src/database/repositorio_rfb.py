from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.models import RfbEmpresa
from src.schemas.rfb import RfbCreate

#Nome da linha que csoma todos os setores , gerada pelo transformer da Receita Federal Brasileira.
SETOR_TOTAL = "Total"

def buscar_rfb(
    db: Session,
    competencia: str | None = None,
    setor: str | None = None,
    skip: int = 0,
    limit: int = 100,
    incluir_total:  bool = True,
)-> list[RfbEmpresa]:

    """
Busca registros agregados da Receita Federal Brasileira com filtros opcionais.
incluir_total=False exclui a linha "Total" ( que é a soma de todos os setores)
Use False ao somar ou comparar setores, para não contar em dobro os setores selecionados.
    """
    query = db.query(RfbEmpresa)

    if not incluir_total:
        query = query.filter(
            RfbEmpresa.setor !=SETOR_TOTAL,
        )

    if competencia:
        query = query.filter(
        RfbEmpresa.competencia ==competencia,
        )

    if setor:
        query = query.filter(
        RfbEmpresa.setor.ilike(f"%{setor}%")
        )

    return (
    query.order_by(RfbEmpresa.competencia, RfbEmpresa.setor)
    .offset(skip)
    .limit(limit)
    .all()
    )

def buscar_por_id_rfb(
             db: Session,
             registro_id: int,
      )-> RfbEmpresa | None:

    """
Busca um registro dentro dos dados da Receita Federal Brasileira (RFB) via identificador.
    """

    return (
      db.query(RfbEmpresa)
      .filter(
            RfbEmpresa.id == registro_id
        )
      .first()
      )


def contar_registros_rfb(
            db: Session,
      )-> int:

    """
Dá um retorno pela quantidade total de registros da Receita Federal Brasileira.
    """

    return db.query(RfbEmpresa).count()

def competencia_ja_processada(
              db: Session,
              competencia: str,
      )-> bool:

    """
Indica caso já exista algum registro gravado para a competencia (AAAA-MM).
Usado também pelo arquivo service para não baixar arquivos já processados de meses passados.
    """

    return (
     db.query(RfbEmpresa.id)
     .filter(
              RfbEmpresa.competencia == competencia
          )
          .first()
          is not None
     )


def listar_competencias_rfb(
            db: Session,
     ) ->  list[str]:

    """
Retorna as competencias já disponíveis no banco, das mais antigas até as mais recentes.competencia
    """


    linhas = (
        db.query(RfbEmpresa.competencia)
        .distinct()
        .order_by(RfbEmpresa.competencia)
        .all()
    )

    return [linha.competencia  for linha in linhas]

def upsert_rfb(
    db: Session,
    registros: list[RfbCreate],
) -> int:
    """
Efetua a criação de registros ou caso necessário, atualiza os existentes usando INSERT ... ON CONFLICT.
A chave de conflito é ( competencia, setor).
    """

    if not registros:
        return 0

    stmt = insert(RfbEmpresa).values(
    [r.model_dump() for r in registros]
    )
    stmt = stmt.on_conflict_do_update(
    index_elements=["competencia", "setor"],
    set_={
    "ativas": stmt.excluded.ativas,
    "aberturas": stmt.excluded.aberturas,
    "encerramentos": stmt.excluded.encerramentos,
    "ativas_mei": stmt.excluded.ativas_mei,
    "ativas_simples": stmt.excluded.ativas_simples,
    "atualizado_em": func.now(),
        },
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount