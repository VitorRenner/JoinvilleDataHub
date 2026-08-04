import logging
from ftplib import FTP
from pathlib import Path

import pandas as pd
import py7zr

from src.collectors.base import BaseCollector

FTP_HOST = "ftp.mtps.gov.br"
FTP_DIRETORIO_BASE = "pdet/microdados/NOVO CAGED"
BASE_URL = f"ftp://{FTP_HOST}/{FTP_DIRETORIO_BASE}"

# Código do município de Joinville sem o dígito verificador, formato utilizado
# pela coluna "município" dos microdados do Novo CAGED (IBGE completo: 4209102).
CODIGO_JOINVILLE = 420910

# O Novo CAGED (layout CAGEDMOV/FOR/EXC) está disponível no FTP oficial a
# partir da competência 202001. Competências anteriores pertencem ao CAGED
# legado, com layout diferente, não coberto por este coletor.
ANO_INICIAL_CAGED = 2020

TIPOS_ARQUIVO = ("MOV", "FOR", "EXC")
TIPO_ARQUIVO_OBRIGATORIO = "MOV"

logger = logging.getLogger(__name__)


class CagedCollector(BaseCollector):
    """
    Responsável pela coleta dos dados do CAGED.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=BASE_URL,
        )

        self.download_dir = Path("data") / "raw" / "caged"

        self.download_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _conectar_ftp(self) -> FTP:
        """
        Abre uma conexão com o FTP oficial de microdados do Ministério do Trabalho.
        """

        try:
            ftp = FTP(encoding="latin-1")

            ftp.connect(
                FTP_HOST,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )

            ftp.login()

            return ftp

        except OSError as erro:
            raise RuntimeError(
                f"Erro ao conectar ao FTP do CAGED: {erro}"
            ) from erro

    def competencia_mais_recente(self) -> tuple[int, int]:
        """
        Descobre, no FTP oficial, a competência (ano, mês) mais recente disponível.
        """

        logger.info("Consultando competência mais recente disponível no FTP.")

        ftp = self._conectar_ftp()

        try:
            ftp.cwd(FTP_DIRETORIO_BASE)

            anos = sorted(item for item in ftp.nlst() if item.isdigit())

            if not anos:
                raise RuntimeError("Nenhum ano disponível no FTP do CAGED.")

            ftp.cwd(anos[-1])

            competencias = sorted(item for item in ftp.nlst() if item.isdigit())

            if not competencias:
                raise RuntimeError("Nenhuma competência disponível no FTP do CAGED.")

            competencia = competencias[-1]

        except OSError as erro:
            raise RuntimeError(
                f"Erro ao consultar competências no FTP do CAGED: {erro}"
            ) from erro

        finally:
            ftp.close()

        logger.info("Competência mais recente encontrada: %s.", competencia)

        return int(competencia[:4]), int(competencia[4:6])

    def _baixar_competencia(
        self,
        competencia: str,
    ) -> dict[str, Path]:
        """
        Garante localmente os arquivos oficiais (MOV, FOR, EXC) de uma competência,
        baixando e extraindo do FTP apenas o que ainda não estiver disponível.

        Retorna:
            Dicionário com o tipo do arquivo e o caminho do .txt já extraído.
        """

        diretorio_competencia = self.download_dir / competencia / competencia

        diretorio_competencia.mkdir(
            parents=True,
            exist_ok=True,
        )

        diretorio_remoto = f"{FTP_DIRETORIO_BASE}/{competencia[:4]}/{competencia}"

        arquivos_extraidos: dict[str, Path] = {}
        ftp: FTP | None = None

        try:
            for tipo in TIPOS_ARQUIVO:
                nome_arquivo = f"CAGED{tipo}{competencia}.7z"
                caminho_7z = diretorio_competencia / nome_arquivo
                caminho_txt = diretorio_competencia / f"CAGED{tipo}{competencia}.txt"

                if caminho_txt.exists():
                    arquivos_extraidos[tipo] = caminho_txt
                    continue

                if not caminho_7z.exists():
                    if ftp is None:
                        ftp = self._conectar_ftp()
                        ftp.cwd(diretorio_remoto)

                    if nome_arquivo not in ftp.nlst():
                        if tipo == TIPO_ARQUIVO_OBRIGATORIO:
                            raise RuntimeError(
                                "Arquivo obrigatório não encontrado no FTP: "
                                f"{nome_arquivo}"
                            )

                        logger.warning(
                            "Arquivo %s não disponível para a competência %s.",
                            nome_arquivo,
                            competencia,
                        )
                        continue

                    logger.info(
                        "Baixando %s via FTP.",
                        nome_arquivo,
                    )

                    with caminho_7z.open("wb") as arquivo:
                        ftp.retrbinary(
                            f"RETR {nome_arquivo}",
                            arquivo.write,
                        )

                logger.info(
                    "Extraindo %s.",
                    caminho_7z.name,
                )

                with py7zr.SevenZipFile(
                    caminho_7z,
                    mode="r",
                ) as arquivo_7z:
                    arquivo_7z.extractall(
                        path=diretorio_competencia,
                    )

                arquivos_extraidos[tipo] = caminho_txt

        except OSError as erro:
            raise RuntimeError(
                f"Erro ao baixar arquivos do CAGED via FTP: {erro}"
            ) from erro

        finally:
            if ftp is not None:
                ftp.close()

        return arquivos_extraidos

    def coletar(
        self,
        ano: int | None = None,
        mes: int | None = None,
    ) -> pd.DataFrame:
        """
        Coleta os dados oficiais do CAGED e agrega as movimentações do
        município de Joinville em admissões, demissões e saldo por competência
        e setor.

        Quando `ano`/`mes` não são informados, coleta a competência mais
        recente disponível no FTP oficial.

        Retorna:
            DataFrame contendo os dados brutos coletados.
        """

        if ano is None or mes is None:
            ano, mes = self.competencia_mais_recente()

        if ano < ANO_INICIAL_CAGED:
            raise ValueError(f"O ano deve ser maior ou igual a {ANO_INICIAL_CAGED}.")

        if not 1 <= mes <= 12:
            raise ValueError("O mês deve estar entre 1 e 12.")

        competencia = f"{ano}{mes:02d}"

        logger.info(
            "Coletando dados do CAGED - competência %s.",
            competencia,
        )

        arquivos = self._baixar_competencia(competencia)

        dataframes_joinville = [
            self.processar_arquivo_local(str(caminho))
            for caminho in arquivos.values()
        ]

        dados_joinville = (
            pd.concat(dataframes_joinville, ignore_index=True)
            if dataframes_joinville
            else pd.DataFrame()
        )

        logger.info(
            "Registros brutos de Joinville coletados: %d.",
            len(dados_joinville),
        )

        return self._agregar_movimentacoes(dados_joinville)

    @staticmethod
    def _agregar_movimentacoes(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Agrega os registros individuais de movimentação (um por trabalhador)
        em saldo de admissões/demissões por competência e setor (seção CNAE).
        """

        colunas_finais = [
            "competencia",
            "setor",
            "admissoes",
            "demissoes",
            "saldo",
        ]

        if df.empty:
            return pd.DataFrame(columns=colunas_finais)

        df = df.rename(
            columns={
                "competênciamov": "competencia",
                "seção": "setor",
            }
        )

        df["saldomovimentação"] = (
            pd.to_numeric(
                df["saldomovimentação"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        agregados = (
            df.groupby(
                [
                    "competencia",
                    "setor",
                ],
                as_index=False,
            ).agg(
                admissoes=(
                    "saldomovimentação",
                    lambda serie: int((serie == 1).sum()),
                ),
                demissoes=(
                    "saldomovimentação",
                    lambda serie: int((serie == -1).sum()),
                ),
                saldo=(
                    "saldomovimentação",
                    "sum",
                ),
            )
        )

        return agregados[colunas_finais]

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
            sep=';',
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