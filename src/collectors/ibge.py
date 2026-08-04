import logging
from typing import Any

import requests

from src.collectors.base import BaseCollector

BASE_URL = "https://servicodados.ibge.gov.br/api/v1"
CODIGO_JOINVILLE = 4209102

logger = logging.getLogger(__name__)


class IBGECollector(BaseCollector):
    """
    Responsável por coletar dados da API do IBGE.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=BASE_URL,
        )

    def _buscar_json(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Realiza uma requisição GET e retorna o JSON da resposta.
        """

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

            logger.info("Requisição realizada com sucesso.")

            return response.json()

        except (
            requests.RequestException,
            ValueError,
        ) as erro:
            raise RuntimeError(f"Erro ao acessar a API do IBGE: {erro}") from erro

    def coletar(
        self,
        endpoint: str = "municipios",
    ) -> dict[str, Any]:
        """
        Coleta dados da API do IBGE.
        """

        url = f"{self.base_url}/localidades/estados/SC/{endpoint}"

        return self._buscar_json(url)

    def buscar_joinville(self) -> dict[str, Any]:
        """
        Busca as informações de Joinville.
        """

        url = f"{self.base_url}/localidades/municipios/{CODIGO_JOINVILLE}"

        return self._buscar_json(url)

