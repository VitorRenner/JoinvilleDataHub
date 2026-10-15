import argparse
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

def _ler_anos_da_linha_de_comando() -> list[int | None]:
    """
    Lê os anos passados na linha de comando.

    Sem argumentos -> [None] (ano mais recente).
    Ex.: python -m src.services.atualizacao_cempre 2022 2023
    """

    parser = argparse.ArgumentParser(
        description="Atualiza os dados do CEMPRE (IBGE) no banco.",
    )

    parser.add_argument(
        "anos",
        nargs="*",
        type=int,
        help="Anos a carregar (ex.: 2022 2023). Vazio = mais recente.",
    )

    argumentos = parser.parse_args()

    return argumentos.anos or [None]

if __name__ == "__main__":
    # Só configura o log "simples" quando o service roda na mão. Quando é
    # importado pelo scheduler, quem manda no log é o configurar_logging().
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Cada ano roda separado: se um falhar, os outros continuam.
    for ano in _ler_anos_da_linha_de_comando():
        try:
            atualizar_cempre(ano=ano)

        except Exception:
            logger.exception(
                "Ano %s não foi carregado. Seguindo para o próximo.",
                ano,
            )