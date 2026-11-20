"""
Limite de uso do /perguntar: cada pergunta custa uma chamada paga ao LLM.

Em memória e por processo: com N workers do Gunicorn, o teto efetivo é N
vezes maior. Suficiente para conter abuso num serviço pequeno; para escalar,
trocar por Redis.
"""

import threading
import time
from collections import defaultdict, deque


class LimiteDeUso:
    def __init__(self, por_minuto_por_ip: int, por_dia_total: int) -> None:
        self.por_minuto_por_ip = por_minuto_por_ip
        self.por_dia_total = por_dia_total
        self._por_ip: dict[str, deque[float]] = defaultdict(deque)
        self._dia_atual = self._hoje()
        self._contagem_dia = 0
        self._trava = threading.Lock()

    @staticmethod
    def _hoje() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def permitir(self, ip: str) -> tuple[bool, str]:
        agora = time.monotonic()

        with self._trava:
            if self._hoje() != self._dia_atual:
                self._dia_atual = self._hoje()
                self._contagem_dia = 0

            if self._contagem_dia >= self.por_dia_total:
                return False, "Limite diário de perguntas atingido. Tente amanhã."

            # Remove IPs sem uso no último minuto, para o dicionário não
            # crescer sem fim com IPs diferentes
            for outro_ip in [
                chave
                for chave, fila in self._por_ip.items()
                if chave != ip and (not fila or agora - fila[-1] > 60)
            ]:
                del self._por_ip[outro_ip]

            janela = self._por_ip[ip]
            while janela and agora - janela[0] > 60:
                janela.popleft()

            if len(janela) >= self.por_minuto_por_ip:
                return False, "Muitas perguntas seguidas. Aguarde um minuto."

            janela.append(agora)
            self._contagem_dia += 1

        return True, ""
