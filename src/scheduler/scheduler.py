import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.core.settings import settings
from src.services.atualizacao_caged import atualizar_caged

logger = logging.getLogger(__name__)

scheduler_caged = BackgroundScheduler()


def iniciar_scheduler() -> None:
    """
    Inicia o scheduler caso ele ainda não esteja rodando.
    """

    if scheduler_caged.running:
        logger.info(
            "O scheduler já está em execução.",
        )
        return

    try:
        scheduler_caged.add_job(
            atualizar_caged,
            trigger="interval",
            seconds=settings.SCHEDULER_INTERVAL_SECONDS,
            id="atualizacao_caged",
            name="Atualização automática do CAGED",
            replace_existing=True,
        )

        scheduler_caged.start()

        logger.info(
            "Scheduler iniciado. Intervalo: %s segundos.",
            settings.SCHEDULER_INTERVAL_SECONDS,
        )

    except Exception:
        logger.exception(
            "Erro ao iniciar o scheduler.",
        )
        raise


def parar_scheduler() -> None:
    """
    Encerra o scheduler.
    """

    if not scheduler_caged.running:
        logger.info(
            "O scheduler já está parado.",
        )
        return

    try:
        scheduler_caged.shutdown(
            wait=False,
        )

        logger.info(
            "Scheduler encerrado com sucesso.",
        )

    except Exception:
        logger.exception(
            "Erro ao encerrar o scheduler.",
        )
        raise
