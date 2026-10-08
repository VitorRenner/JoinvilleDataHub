import logging
from typing import Any

import pandas as pd
import requests

from src.collectors.base import BaseCollector
from src.core.settings import settings

# Tabela 9510 do SIDRA: CEMPRE por seção da CNAE 2.0, para municípios com
# 50 mil habitantes ou mais. A 9509 (usada antes) não abre por setor, só traz
# o total do município, e o projeto inteiro trabalha com ano + setor.
TABELA_CEMPRE = 9510

CODIGO_JOINVILLE = 4209102

# Variáveis da tabela 9510 que o projeto usa:
# 706   -> Número de unidades locais (Unidades)
# 707   -> Pessoal ocupado total (Pessoas)
# 10143 -> Salário médio mensal em reais (Reais)
#
# Obs.: a 367 (número de empresas) vem com "-" quando aberta por seção no
# nível de município, por isso ficou de fora.
VARIAVEIS_CEMPRE = (
    706,
    707,
    10143,
)

# Classificação C12762 = CNAE 2.0. Só as seções (A até U) + o total geral,
# sem descer pras divisões, senão a tabela explode de linhas.
CLASSIFICACAO_CNAE = "c12762"

SECOES_CNAE = (
    117897,  # Total
    116830,  # A Agricultura, pecuária, produção florestal, pesca e aquicultura
    116880,  # B Indústrias extrativas
    116910,  # C Indústrias de transformação
    117296,  # D Eletricidade e gás
    117307,  # E Água, esgoto, atividades de gestão de resíduos
    117329,  # F Construção
    117363,  # G Comércio; reparação de veículos automotores
    117484,  # H Transporte, armazenagem e correio
    117543,  # I Alojamento e alimentação
    117555,  # J Informação e comunicação
    117608,  # K Atividades financeiras, de seguros
    117666,  # L Atividades imobiliárias
    117673,  # M Atividades profissionais, científicas e técnicas
    117714,  # N Atividades administrativas e serviços complementares
    117774,  # O Administração pública, defesa e seguridade social
    117788,  # P Educação
    117810,  # Q Saúde humana e serviços sociais
    117838,  # R Artes, cultura, esporte e recreação
    117861,  # S Outras atividades de serviços
    117888,  # T Serviços domésticos
    117892,  # U Organismos internacionais
)

logger = logging.getLogger(__name__)


class CempreCollector(BaseCollector):
    """
    Responsável pela coleta dos dados do CEMPRE.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.CEMPRE_BASE_URL,
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
        Joinville, pelas variáveis usadas e pelas seções da CNAE.
        """

        variaveis = ",".join(str(codigo) for codigo in VARIAVEIS_CEMPRE)
        secoes = ",".join(str(codigo) for codigo in SECOES_CNAE)

        return (
            f"{self.base_url}/values/t/{TABELA_CEMPRE}"
            f"/n6/{CODIGO_JOINVILLE}"
            f"/v/{variaveis}"
            f"/p/{periodo}"
            f"/{CLASSIFICACAO_CNAE}/{secoes}"
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