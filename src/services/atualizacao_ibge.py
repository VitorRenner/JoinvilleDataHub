import logging
from time import perf_counter

from src.collectors.ibge import IBGECollector
from src.core.logging import configurar_logging
from src.database.conexao import SessionLocal
from src.database.repositorio_ibge import upsert_ibge
from src.schemas.ibge import IbgeCreate
from src.transformers.ibge import transformar_ibge, validar_ibge

logger = logging.getLogger(__name__)

LOG_SEPARATOR = "=" * 50


def atualizar_ibge() -> int:
    inicio_execucao = perf_counter()

    db = SessionLocal()

    try:
        logger.info(LOG_SEPARATOR)
        logger.info("Iniciando atualização do IBGE.")
        logger.info(LOG_SEPARATOR)

        linhas = IBGECollector().coletar()

        registros = transformar_ibge(linhas)

        logger.info("Dados transformados: %d registros.", len(registros))

        validos, invalidos = validar_ibge(registros)

        logger.info("Registros válidos: %d.", len(validos))

        if invalidos:
            logger.warning(
                "Registros inválidos encontrados: %d. Exemplo: %s",
                len(invalidos),
                invalidos[0],
            )

        processados = upsert_ibge(
            db,
            [IbgeCreate(**registro) for registro in validos],
        )

        logger.info(
            "Persistência concluída. Registros processados: %d.",
            processados,
        )

        return processados

    except Exception:
        db.rollback()
        logger.exception("Erro durante atualização do IBGE.")
        raise

    finally:
        db.close()

        logger.info(
            "Tempo de execução: %.2f segundos.",
            perf_counter() - inicio_execucao,
        )
        logger.info(LOG_SEPARATOR)


if __name__ == "__main__":
    configurar_logging()
    atualizar_ibge()
