import logging
from typing import Any

import requests

from src.collectors.base import BaseCollector
from src.core.settings import settings

CODIGO_JOINVILLE = settings.IBGE_MUNICIPIO_JOINVILLE

INDICADORES_SIDRA = (
    ("populacao_estimada", 6579, 9324),
    ("pib", 5938, 37),
    ("participacao_pib_sc", 5938, 497),
)

logger = logging.getLogger(__name__)


class IBGECollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__(
            base_url=settings.IBGE_SIDRA_URL,
        )

    def _buscar_json(
        self,
        url: str,
    ) -> list[dict[str, Any]]:
        logger.info(
            "Realizando requisição para: %s",
            url,
        )

        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            return response.json()

        except (
            requests.RequestException,
            ValueError,
        ) as erro:
            raise RuntimeError(f"Erro ao acessar o SIDRA/IBGE: {erro}") from erro

    def coletar(self, **kwargs: Any) -> list[dict[str, Any]]:
        linhas: list[dict[str, Any]] = []

        for indicador, tabela, variavel in INDICADORES_SIDRA:
            url = (
                f"{self.base_url}/values/t/{tabela}/n6/{CODIGO_JOINVILLE}"
                f"/v/{variavel}/p/all"
            )

            resposta = self._buscar_json(url)

            for linha in resposta[1:]:
                linhas.append({**linha, "indicador": indicador})

            logger.info(
                "Indicador %s: %d anos coletados.",
                indicador,
                len(resposta) - 1,
            )

        return linhas
