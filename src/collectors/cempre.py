import logging
from typing import Any

import pandas as pd
import requests

from src.collecotrs.base import BaseCollector

BASE_URL = "https://apisidra.ibge.gov.br"

# Tabela do CEMPRE no SIDRA (unidades locais, empresas atuantes, pessoal ocupado e salários, disponível por
# municípios.
# O número muda a cada edição do IBGE - conferir em https://sidra.ibge.gov.br/pesquisa/cempre/tabelas
# Caso este coletor for reaproveitado em breve

TABELA_CEMPRE = 9509

# Mesmo município usado no restante do projeto (código IBGE completo,
# diferente do código truncado usado nos microdados do CAGED).

CODIGO_JOINVILLE = 4209102

logger = logging.getlogger(__name__)

class CempreCollector(BaseCollector):
    """
   Responsável por coletar os dados do CEMPRE na API do SIDRA (IBGE).
   """

    def __init__(self) -> None:
        super().__init__(base_url=BASE_URL)

        def _buscar_json(self, url:str) -> list[dict[str, Any]]:

    """
       Realiza uma requisição GET à API do SIDRA e retorna o JSON da resposta.
       """
    logger.info("Realizando requisição para: %s", url)

    try:
        response = self.session.get(url, timeout=self.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.info("Requisição realizada com sucesso.")
        return response.json()

    except(requests.RequestException, ValueError) as erro:
        raise RuntimeError(f"Erro ao acessar os dados da API  do SIDRA: {erro}") from erro

    def _montar_url(self, periodo: int | str) -> str:



