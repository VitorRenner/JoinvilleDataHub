"""
Collector da RFB (dados abertos do CNPJ da Receita Federal Brasileira).

Baixa os arquivos .zip do Brasil inteiro, lê em blocos e guarda
só o que é de Joinville. Nunca carrega um arquivo inteiro na memória.

As funções de listar e baixar vieram do src/scripts/inspecionar_rfb.py.
"""

import logging
import re
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src.collectors.base import BaseCollector
from src.core.settings import settings

logger = logging.getLogger(__name__)


# ─────────────── Constantes ───────────────

WEBDAV_URL = settings.RFB_BASE_URL + settings.RFB_WEBDAV_PATH
PASTA_TEMP = Path(settings.RFB_PASTA_TEMP)
TAMANHO_PEDACO_DOWNLOAD = 1024 * 1024  # 1 MB

QUANTIDADE_PARTES = 10
# A Receita divide Estabelecimentos e Empresas em 10 arquivos (0 a 9).

# Posição da coluna no CSV (começando em 0) -> nome usado no projeto.
# Fonte: layout oficial da RFB, conferido na inspeção.

COLUNAS_ESTABELECIMENTOS = {
    0: "cnpj_basico",
    5: "situacao_cadastral",
    6: "data_situacao_cadastral",
    10: "data_inicio_atividade",
    11: "cnae_fiscal_principal",
    20: "municipio",
}

# COLUNAS_EMPRESAS e COLUNAS_SIMPLES entram depois,
# após conferir as posições no PDF da Receita.


# ─────────────── Collector ───────────────

class RfbCollector(BaseCollector):

    def __init__(self, session: requests.Session | None = None) -> None:
        super().__init__(base_url=WEBDAV_URL, session=session)
        self.session.auth = (settings.RFB_SHARE_TOKEN, "")

    def descobrir_competencia_mais_recente(self) -> str:

        """Lista as pastas AAAA-MM do servidor e devolve a mais recente."""

        resposta = self.session.request(
            method="PROPFIND",
            url=self.base_url + "/",
            headers={"Depth": "1"},
            timeout=settings.RFB_TIMEOUT_SEGUNDOS,
        )

        # PROPFIND é o comando do WebDAV para listar uma pasta.
        # Depth 1: lista só o primeiro nível (as pastas AAAA-MM).

        if resposta.status_code != 207:
            raise RuntimeError(
                f"Listagem da RFB falhou: status {resposta.status_code}"
            )

        # 207 (Multi-Status) é o código de sucesso do PROPFIND, não 200.

        competencias = sorted(set(re.findall(r"/(\d{4}-\d{2})/", resposta.text)))

        # As barras na regex garantem que só nomes de pasta são capturados.
        # No formato AAAA-MM, a ordem alfabética é a ordem cronológica.

        if not competencias:
            raise RuntimeError(
                "Nenhuma pasta AAAA-MM encontrada. A estrutura do servidor mudou?"
            )

        mais_recente = competencias[-1]
        logger.info("Competência mais recente da RFB: %s", mais_recente)
        return mais_recente

    def baixar(self, competencia: str, nome_arquivo: str) -> Path:

        """Baixa um zip em streaming, com retry. Devolve o caminho no disco."""

        url = f"{self.base_url}/{competencia}/{nome_arquivo}"
        PASTA_TEMP.mkdir(parents=True, exist_ok=True)
        destino = PASTA_TEMP / nome_arquivo

        for tentativa in range(1, settings.RFB_TENTATIVAS + 1):
            try:
                logger.info(
                    "Baixando %s (tentativa %s/%s)",
                    nome_arquivo, tentativa, settings.RFB_TENTATIVAS,
                )
                with self.session.get(
                        url,
                        stream=True,
                        timeout=settings.RFB_TIMEOUT_SEGUNDOS,
                ) as resposta:
                    resposta.raise_for_status()
                    with open(destino, "wb") as arquivo:
                        for pedaco in resposta.iter_content(chunk_size=TAMANHO_PEDACO_DOWNLOAD):
                            arquivo.write(pedaco)

                # stream=True grava o arquivo no disco em pedaços de 1 MB;
                # sem isso, os vários GB iriam inteiros para a memória.
                # raise_for_status evita salvar uma página de erro como se fosse o zip.

                logger.info("Download concluído: %s", destino)
                return destino

            except requests.RequestException as erro:
                destino.unlink(missing_ok=True)

                # Um zip baixado pela metade parece válido, por isso é apagado.

                logger.warning("Falha ao baixar %s: %s", nome_arquivo, erro)

                if tentativa < settings.RFB_TENTATIVAS:
                    espera = tentativa * 10
                    logger.info("Nova tentativa em %ss", espera)
                    time.sleep(espera)

                # Espera crescente (10s, 20s...): o servidor da Receita é instável.

        raise RuntimeError(
            f"Download da RFB falhou após {settings.RFB_TENTATIVAS} tentativas: {url}"
        )

    def ler_em_blocos(self, caminho_zip: Path, colunas: dict, filtro) -> pd.DataFrame:

        """Lê o CSV de dentro do zip em blocos e guarda só as linhas do filtro."""

        raise NotImplementedError

    def ler_estabelecimentos_joinville(self, competencia: str):

        """Percorre Estabelecimentos0..9 e devolve (tabela, conjunto de cnpj_basico)."""

        raise NotImplementedError

    def ler_empresas(self, conjunto_cnpj: set, competencia: str) -> pd.DataFrame:

        """Percorre Empresas0..9 e guarda só os cnpj_basico de Joinville."""

        raise NotImplementedError

    def ler_simples(self, conjunto_cnpj: set, competencia: str) -> pd.DataFrame:

        """Lê o Simples.zip e guarda só os cnpj_basico de Joinville."""

        raise NotImplementedError

    def coletar(self, competencia: str | None = None):

        """Junta tudo: devolve (competencia, estabelecimentos, empresas, simples)."""

        raise NotImplementedError