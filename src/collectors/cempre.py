import logging
from typing import Any

import pandas as pd
import requests

from src.collectors.base import BaseCollector

BASE_URL = "https://apisidra.ibge.gov.br"

# Tabela do CEMPRE no SIDRA (unidades locais, pessoal ocupado e salários,
# por município). Conferir a tabela vigente em
# sidra.ibge.gov.br/pesquisa/cempre/tabelas antes de reaproveitar isso.
TABELA_CEMPRE = 9509

CODIGO_JOINVILLE = 4209102

logger = logging.getLogger(__name__)


class CempreCollector(BaseCollector):
    """
    Responsável pela coleta dos dados do CEMPRE.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=BASE_URL,
        )

    def _buscar_json(
            self,
            url: str,
    ) -> list[dict[str, Any]]:
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
            raise RuntimeError(
                f"Erro ao acessar a API do SIDRA: {erro}"
            ) from erro

    def _montar_url(
            self,
            periodo: int | str,
    ) -> str:
        """
        Monta a URL de consulta da tabela do CEMPRE, filtrando por
        Joinville e trazendo todas as variáveis disponíveis.
        """

        return (
            f"{self.base_url}/values/t/{TABELA_CEMPRE}"
            f"/n6/{CODIGO_JOINVILLE}"
            f"/v/all"
            f"/p/{periodo}"
        )

    def coletar(
            self,
            ano: int | None = None,
    ) -> pd.DataFrame:
        """
        Coleta os dados do CEMPRE para o município de Joinville.

        Quando `ano` não é informado, coleta o período mais recente
        publicado pelo IBGE.
        """

        periodo = ano if ano is not None else "last"

        logger.info(
            "Coletando dados do CEMPRE - período: %s.",
            periodo,
        )

        url = self._montar_url(periodo)

        dados_json = self._buscar_json(url)

        if not dados_json:
            logger.warning("Nenhum dado retornado pela API do SIDRA.")
            return pd.DataFrame()

        # Primeiro item da lista é sempre o cabeçalho descritivo, não uma
        # linha de dados.
        _, *linhas = dados_json

        if not linhas:
            logger.warning(
                "A API retornou apenas o cabeçalho para o período '%s'.",
                periodo,
            )
            return pd.DataFrame()

        dataframe = pd.DataFrame(linhas)

        logger.info(
            "Registros brutos coletados: %d.",
            len(dataframe),
        )

        return dataframe
