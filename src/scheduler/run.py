"""
Processo dedicado do scheduler.

Roda SEPARADO da API: python -m src.scheduler.run

Motivo da separação: a API sobe com vários workers no gunicorn (-w 4).
Se o scheduler ligasse dentro da API, cada worker teria o próprio
scheduler e os jobs rodariam 4 vezes ao mesmo tempo. Aqui existe
um único processo, logo um único scheduler.
"""

import logging
import signal
import time
from types import FrameType

from src.core.logging import configurar_logging
from src.scheduler.scheduler import iniciar_scheduler, parar_scheduler

logger = logging.getLogger(__name__)

# De quanto em quanto tempo o laço "acorda". Não afeta os jobs:
# só define a rapidez com que o processo percebe um pedido de parada.
INTERVALO_ESPERA_SEGUNDOS = 5


def _tratar_sinal_de_parada(numero_sinal: int, _frame: FrameType | None) -> None:
    """
    Converte o SIGTERM (o "pare" que o Docker/systemd mandam) em SystemExit.

    Sem isso, o SIGTERM mata o processo na hora e o bloco "finally"
    abaixo não roda, ou seja, o scheduler não é encerrado direito.
    """

    logger.info("Sinal %s recebido. Encerrando o scheduler...", numero_sinal)
    raise SystemExit(0)


def main() -> None:
    configurar_logging()

    signal.signal(signal.SIGTERM, _tratar_sinal_de_parada)

    iniciar_scheduler()
    logger.info("Processo do scheduler em execução. Ctrl+C para parar.")

    try:
        # O BackgroundScheduler roda em segundo plano: se este script
        # terminar, o processo morre e leva o scheduler junto.
        # O laço só dorme, mantendo o "ginásio aberto".
        while True:
            time.sleep(INTERVALO_ESPERA_SEGUNDOS)

    except (KeyboardInterrupt, SystemExit):
        # KeyboardInterrupt = Ctrl+C no terminal
        # SystemExit       = SIGTERM convertido pela função acima
        logger.info("Parada solicitada.")

    finally:
        # Roda SEMPRE: Ctrl+C, Docker parando ou erro inesperado.
        parar_scheduler()


if __name__ == "__main__":
    main()