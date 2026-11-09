import argparse
import logging
import shutil
from time import perf_counter

from src.collectors.rfb import PASTA_TEMP, RfbCollector
from src.database.conexao import SessionLocal
from src.database.repositorio_rfb import (
    competencia_ja_processada,
    upsert_rfb,
)
from src.schemas.rfb import RfbCreate
from src.transformers.rfb import (
    transformar_rfb,
    validar_dados,
)

logger = logging.getLogger(__name__)

LOG_SEPARATOR = "=" * 50


def atualizar_rfb(
        competencia: str | None = None,
        forcar: bool = False,
) -> int:
    """
    Executa o fluxo completo de atualização dos dados da RFB.

    Etapas:
    - descoberta da competência (quando não informada);
    - checagem se a competência já foi processada;
    - coleta, transformação, validação e persistência;
    - limpeza da pasta temporária de downloads.

    forcar=True reprocessa a competência mesmo que já exista no banco.

    Retorna:
        Quantidade de registros processados.
    """

    inicio_execucao = perf_counter()

    db = SessionLocal()

    try:
        collector = RfbCollector()

        competencia = (
            competencia or collector.descobrir_competencia_mais_recente()
        )

        logger.info(LOG_SEPARATOR)
        logger.info("Iniciando atualização da RFB.")
        logger.info("Competência: %s", competencia)
        logger.info(LOG_SEPARATOR)

        if not forcar and competencia_ja_processada(db, competencia):
            logger.info(
                "Competência %s já processada. Nada a fazer "
                "(use --forcar para reprocessar).",
                competencia,
            )
            return 0

        competencia, estabelecimentos, empresas, simples = collector.coletar(
            competencia,
        )

        registros = transformar_rfb(
            competencia,
            estabelecimentos,
            empresas,
            simples,
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

        registros_schema = [
            RfbCreate(**registro) for registro in registros_validos
        ]

        processados = upsert_rfb(
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
            "Erro durante atualização da RFB.",
        )

        raise

    finally:
        shutil.rmtree(PASTA_TEMP, ignore_errors=True)

        db.close()

        duracao = perf_counter() - inicio_execucao

        logger.info(
            "Tempo de execução: %.2f segundos.",
            duracao,
        )

        logger.info(LOG_SEPARATOR)


def _ler_argumentos() -> argparse.Namespace:
    """
    Lê as competências e a flag --forcar da linha de comando.

    Sem competências -> [None] (competência mais recente).
    Ex.: python -m src.services.atualizacao_rfb 2026-08 2026-09 --forcar
    """

    parser = argparse.ArgumentParser(
        description="Atualiza os dados da RFB (CNPJ) no banco.",
    )

    parser.add_argument(
        "competencias",
        nargs="*",
        help="Competências a carregar (ex.: 2026-08 2026-09). Vazio = mais recente.",
    )

    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Reprocessa mesmo que a competência já esteja no banco.",
    )

    argumentos = parser.parse_args()

    argumentos.competencias = argumentos.competencias or [None]

    return argumentos


if __name__ == "__main__":
    # Só configura o log "simples" quando o service roda na mão. Quando é
    # importado pelo scheduler, quem manda no log é o configurar_logging().
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    argumentos = _ler_argumentos()

    # Cada competência roda separada: se uma falhar, as outras continuam.
    for competencia in argumentos.competencias:
        try:
            atualizar_rfb(
                competencia=competencia,
                forcar=argumentos.forcar,
            )

        except Exception:
            logger.exception(
                "Competência %s não foi carregada. Seguindo para a próxima.",
                competencia,
            )