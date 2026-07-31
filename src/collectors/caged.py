import logging
from pathlib import Path

import pandas as pd

from src.collectors.base import BaseCollector

BASE_URL = "https://portaldatransparencia.gov.br"
CODIGO_JOINVILLE = 4209102
ANO_INICIAL_CAGED = 2002

logger = logging.getLogger(__name__)


class CagedCollector(BaseCollector):
    """
    Responsável pela coleta dos dados do CAGED.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=BASE_URL,
        )

        self.download_dir = Path("data") / "caged"

        self.download_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def coletar(
        self,
        ano: int = 2024,
        mes: int = 1,
    ) -> pd.DataFrame:
        """
        Coleta os dados do CAGED.

        Retorna:
            DataFrame contendo os dados brutos coletados.
        """

        if ano < ANO_INICIAL_CAGED:
            raise ValueError(f"O ano deve ser maior ou igual a {ANO_INICIAL_CAGED}.")

        if not 1 <= mes <= 12:
            raise ValueError("O mês deve estar entre 1 e 12.")

        competencia = f"{ano}{mes:02d}"

        logger.info(
            "Coletando dados do CAGED - competência %s.",
            competencia,
        )

        # TODO:
        # Implementar download dos arquivos oficiais do CAGED.

        return pd.DataFrame(
            columns=[
                "competencia",
                "município",
                "setor",
                "admissoes",
                "demissoes",
                "saldo",
            ],
        )

    def processar_arquivo_local(
        self,
        caminho_arquivo: str,
        codigo_municipio: int = CODIGO_JOINVILLE,
    ) -> pd.DataFrame:
        """
        Processa um arquivo local e filtra os dados do município informado.
        """

        logger.info(
            "Processando arquivo local: %s",
            caminho_arquivo,
        )

        caminho = Path(caminho_arquivo)

        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        df = self.read_csv(
            str(caminho),
            sep ';',
            encoding="UTF-8",
            low_memory=False,
        )

        if "município" not in df.columns:
            raise ValueError("A coluna 'municipio' não foi encontrada no arquivo.")

        df = df[df["município"] == codigo_municipio]

        logger.info(
            "Encontrados %d registros para o município %d.",
            len(df),
            codigo_municipio,
        )

        return df
