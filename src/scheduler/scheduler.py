import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.core.settings import settings

logger = logging.getLogger(__name__)

# Um único scheduler (o "técnico") para todas as fontes. Cada fonte tem o
# seu próprio job.
# timezone: o container roda em UTC. Sem isso, "3h" viraria meia-noite
# no horário de Brasília.
scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def _job_caged() -> None:
    """
    Executa a atualização do CAGED de forma isolada.

    Mesmo molde do CEMPRE: o import fica aqui dentro (e não no topo do
    arquivo) para que um erro no código do CAGED não impeça o scheduler,
    e os outros jobs, de subir. O erro é registrado no log e não é relançado.
    """

    try:
        from src.services.atualizacao_caged import atualizar_caged

        atualizar_caged()

    except Exception:
        logger.exception(
            "Falha na atualização automática do CAGED.",
        )


def _job_cempre() -> None:
    """
    Executa a atualização do CEMPRE de forma isolada.

    O import fica aqui dentro (e não no topo do arquivo) para que um erro
    no código do CEMPRE não impeça o scheduler, e o job do CAGED, de subir.
    O erro é registrado no log e não é relançado.
    """

    try:
        from src.services.atualizacao_cempre import atualizar_cempre

        atualizar_cempre()

    except Exception:
        logger.exception(
            "Falha na atualização automática do CEMPRE.",
        )


def iniciar_scheduler() -> None:
    """
    Inicia o scheduler caso ele ainda não esteja rodando.
    """

    if scheduler.running:
        logger.info(
            "O scheduler já está em execução.",
        )
        return

    try:
        # Gatilho "cron" (horário fixo no calendário) em vez de "interval":
        # um intervalo recomeça do zero a cada reinício do processo e, se
        # ele reiniciar com frequência, o job nunca roda.
        scheduler.add_job(
            _job_caged,
            trigger="cron",
            hour=settings.SCHEDULER_CAGED_HORA,
            id="atualizacao_caged",
            name="Atualização automática do CAGED",
            replace_existing=True,
        )

        scheduler.add_job(
            _job_cempre,
            trigger="cron",
            day=settings.SCHEDULER_CEMPRE_DIA,
            hour=settings.SCHEDULER_CEMPRE_HORA,
            id="atualizacao_cempre",
            name="Atualização automática do CEMPRE",
            replace_existing=True,
        )

        scheduler.start()

        logger.info(
            "Scheduler iniciado (horário de Brasília). CAGED todo dia às %sh; "
            "CEMPRE todo dia %s do mês, às %sh.",
            settings.SCHEDULER_CAGED_HORA,
            settings.SCHEDULER_CEMPRE_DIA,
            settings.SCHEDULER_CEMPRE_HORA,
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

    if not scheduler.running:
        logger.info(
            "O scheduler já está parado.",
        )
        return

    try:
        scheduler.shutdown(
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