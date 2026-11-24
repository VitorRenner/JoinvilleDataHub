import logging
from time import perf_counter

from src.collectors.caged import CagedCollector
from src.core.logging import configurar_logging
from src.database.conexao import SessionLocal
from src.database.repositorio import substituir_serie_caged
from src.schemas.caged import CagedCreate
from src.transformers.caged import (
    transformar_caged,
    validar_dados,
)

logger = logging.getLogger(__name__)

LOG_SEPARATOR = "=" * 50


def atualizar_caged() -> int:
    """
    Executa o fluxo completo de atualização da série do CAGED.

    Etapas:
    - lista todas as competências do Novo CAGED no FTP oficial;
    - baixa só as que ainda não estão no cache local de Joinville;
    - recalcula a série inteira (MOV + FOR - EXC);
    - transforma, valida e substitui a série no banco numa única transação.

    Retorna:
        Quantidade de registros gravados.
    """

    inicio_execucao = perf_counter()

    db = SessionLocal()

    try:
        collector = CagedCollector()

        logger.info(LOG_SEPARATOR)
        logger.info("Iniciando atualização do CAGED.")
        logger.info(LOG_SEPARATOR)

        agregados = collector.coletar()

        competencias = sorted(agregados["competencia"].unique())

        registros = transformar_caged(
            agregados,
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
                "Registros inválidos encontrados: %d. Exemplo: %s",
                len(registros_invalidos),
                registros_invalidos[0],
            )

        registros_schema = [CagedCreate(**registro) for registro in registros_validos]

        gravados = substituir_serie_caged(
            db,
            registros_schema,
        )

        logger.info(
            "Série do CAGED substituída. Registros gravados: %d (%s a %s).",
            gravados,
            competencias[0],
            competencias[-1],
        )

        return gravados

    except Exception:
        db.rollback()

        logger.exception(
            "Erro durante atualização do CAGED.",
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
    configurar_logging()
    atualizar_caged()
