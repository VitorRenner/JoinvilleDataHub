import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pandas.errors import ParserError

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Classe base para todos os coletores do projeto.
    """

    REQUEST_TIMEOUT_SECONDS = 30
    DOWNLOAD_CHUNK_SIZE = 8192

    def __init__(
        self,
        base_url: str,
        session: requests.Session | None = None,
    ) -> None:
        """
        Inicializa o coletor.
        """

        self.base_url = base_url
        self.session = session or requests.Session()

    @abstractmethod
    def coletar(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Executa a coleta dos dados.

        Deve ser implementado pelos coletores específicos.
        """

        raise NotImplementedError

    def download_file(
        self,
        url: str,
        caminho_arquivo: str,
    ) -> bool:
        """
        Realiza o download de um arquivo.
        """

        caminho = Path(caminho_arquivo)

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        logger.info(
            "Iniciando download: %s",
            url,
        )

        try:
            response = self.session.get(
                url,
                stream=True,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            with caminho.open("wb") as arquivo:
                for chunk in response.iter_content(
                    chunk_size=self.DOWNLOAD_CHUNK_SIZE,
                ):
                    if chunk:
                        arquivo.write(chunk)

            logger.info(
                "Arquivo salvo em: %s",
                caminho,
            )

            return True

        except requests.RequestException as erro:
            raise RuntimeError(f"Erro ao baixar arquivo: {erro}") from erro

    def read_excel(
        self,
        caminho_arquivo: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Lê um arquivo Excel e retorna um DataFrame.
        """

        try:
            dataframe = pd.read_excel(
                caminho_arquivo,
                **kwargs,
            )

            logger.info(
                "Arquivo Excel carregado: %s",
                caminho_arquivo,
            )

            return dataframe

        except (
            FileNotFoundError,
            PermissionError,
            ValueError,
            ParserError,
        ) as erro:
            raise RuntimeError(f"Erro ao ler arquivo Excel: {erro}") from erro
