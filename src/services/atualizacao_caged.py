import logging
from time import perf_counter

from src.collectors.caged import CagedCollector
from src.database.conexao import SessionLocal
from src.database.repositorio import upsert_caged
from src.schemas.caged import CagedCreate
from src.transformers.caged import (
    transformar_caged,
    validar_dados,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


logger = logging.getLogger(__name__)

LOG_SEPARATOR = "=" * 50


def atualizar_caged(
    ano: int | None = None,
    mes: int | None = None,
) -> int:
    """
    Executa o fluxo completo de atualização dos dados do CAGED.

    Etapas:
    - coleta dos dados;
    - transformação;
    - validação;
    - persistência no banco.

    Quando `ano`/`mes` não são informados, atualiza a competência mais
    recente disponível na fonte oficial.

    Retorna:
        Quantidade de registros processados.
    """

    inicio_execucao = perf_counter()

    db = SessionLocal()

    try:
        collector = CagedCollector()

        if ano is None or mes is None:
            ano, mes = collector.competencia_mais_recente()

        logger.info(LOG_SEPARATOR)
        logger.info("Iniciando atualização do CAGED.")
        logger.info(
            "Competência: %d/%02d",
            ano,
            mes,
        )
        logger.info(LOG_SEPARATOR)

        logger.info("Coletando dados do CAGED.")

        dados_brutos = collector.coletar(
            ano=ano,
            mes=mes,
        )

        logger.info(
            "Dados coletados: %d registros.",
            len(dados_brutos),
        )

        registros = transformar_caged(
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

        registros_schema = [CagedCreate(**registro) for registro in registros_validos]

        processados = upsert_caged(
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
    atualizar_caged()
