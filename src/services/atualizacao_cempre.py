import logging
from time import perf_counter

from src.collectors.cempre import CempreCollector
from src.database.conexao import SessionLocal
from src.database.repositorio_cempre import upsert_cempre
from src.schemas.cempre import CempreCreate
from src.transformers.cempre import (
    transformar_cempre,
    validar_dados,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


logger = logging.getLogger(__name__)

LOG_SEPARATOR = "=" * 50


def atualizar_cempre(
        ano: int | None = None,
) -> int:
    """
    Executa o fluxo completo de atualização dos dados do CEMPRE.

    Etapas:
    - coleta dos dados;
    - transformação;
    - validação;
    - persistência no banco.

    Quando `ano` não é informado, atualiza o período mais recente
    publicado pelo IBGE.

    Retorna:
        Quantidade de registros processados.
    """

    inicio_execucao = perf_counter()

    db = SessionLocal()

    try:
        collector = CempreCollector()

        logger.info(LOG_SEPARATOR)
        logger.info("Iniciando atualização do CEMPRE.")
        logger.info(
            "Ano: %s",
            ano if ano is not None else "mais recente",
        )
        logger.info(LOG_SEPARATOR)

        dados_brutos = collector.coletar(
            ano=ano,
        )

        logger.info(
            "Dados coletados: %d registros.",
            len(dados_brutos),
        )

        registros = transformar_cempre(
            dados_brutos,
        )

        logger.info(
            "Dados transformados: %d registros.",
            len(registros),
        )

        registros_validos, registros_invalidos = validar_dados(
            registros,
        )

        logger.info(
            "Registros válidos: %d.",
            len(registros_validos),
        )

        if registros_invalidos:
            logger.warning(
                "Registros inválidos encontrados: %d.",
                len(registros_invalidos),
            )

        registros_schema = [
            CempreCreate(**registro) for registro in registros_validos
        ]

        processados = upsert_cempre(
            db,
            registros_schema,
        )

        logger.info(
            "Persistência concluída. Registros processados: %d.",
            processados,
        )

        return processados

    except Exception:
        db.rollback()

        logger.exception(
            "Erro durante atualização do CEMPRE.",
        )

        raise

    finally:
        db.close()

        duracao = perf_counter() - inicio_execucao

        logger.info(
            "Tempo de execução: %.2f segundos.",
            duracao,
        )

        logger.info(LOG_SEPARATOR)


if __name__ == "__main__":
    atualizar_cempre()