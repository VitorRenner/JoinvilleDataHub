import logging
import time
from ftplib import FTP
from pathlib import Path
from typing import Any

import pandas as pd
import py7zr

from src.collectors.base import BaseCollector
from src.core.settings import settings

FTP_HOST = settings.CAGED_FTP_HOST
FTP_DIRETORIO_BASE = settings.CAGED_FTP_DIRETORIO
BASE_URL = f"ftp://{FTP_HOST}/{FTP_DIRETORIO_BASE}"

# Código do município de Joinville sem o dígito verificador, formato utilizado
# pela coluna "município" dos microdados do Novo CAGED (IBGE completo: 4209102).
CODIGO_JOINVILLE = settings.CAGED_MUNICIPIO_JOINVILLE

# O Novo CAGED (layout CAGEDMOV/FOR/EXC) está disponível no FTP oficial a
# partir da competência 202001. Competências anteriores pertencem ao CAGED
# legado, com layout diferente, não coberto por este coletor.
ANO_INICIAL_CAGED = 2020

TIPOS_ARQUIVO = ("MOV", "FOR", "EXC")
TIPO_ARQUIVO_OBRIGATORIO = "MOV"

COLUNAS_MOVIMENTACAO = (
    "competênciamov",
    "seção",
    "saldomovimentação",
)

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

        self.cache_dir = Path("data") / "raw" / "caged_joinville"

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _conectar_ftp(self) -> FTP:
        """
        Abre uma conexão com o FTP oficial de microdados do Ministério do Trabalho.
        Tenta até 3 vezes com backoff exponencial.
        """
        max_tentativas = 3
        for tentativa in range(1, max_tentativas + 1):
            try:
                ftp = FTP(encoding="latin-1")
                ftp.connect(
                    FTP_HOST,
                    timeout=self.REQUEST_TIMEOUT_SECONDS,
                )
                ftp.login()
                return ftp
            except OSError as erro:
                if tentativa == max_tentativas:
                    raise RuntimeError(
                        f"Erro ao conectar ao FTP do CAGED após "
                        f"{max_tentativas} tentativas: {erro}"
                    ) from erro
                wait = 2**tentativa
                logger.warning(
                    "Tentativa %d/%d de conexão FTP falhou: %s. "
                    "Aguardando %ds para retry.",
                    tentativa,
                    max_tentativas,
                    erro,
                    wait,
                )
                time.sleep(wait)

    def listar_competencias(self) -> list[str]:
        """
        Lista, no FTP oficial, todas as competências (YYYYMM) do Novo CAGED
        a partir de ANO_INICIAL_CAGED, em ordem crescente.
        """

        logger.info("Consultando competências disponíveis no FTP.")

        ftp = self._conectar_ftp()

        try:
            ftp.cwd(FTP_DIRETORIO_BASE)

            anos = sorted(
                item
                for item in ftp.nlst()
                if item.isdigit() and int(item) >= ANO_INICIAL_CAGED
            )

            competencias: list[str] = []
            for ano in anos:
                itens = ftp.nlst(ano)
                competencias.extend(
                    nome
                    for nome in (item.rsplit("/", 1)[-1] for item in itens)
                    if len(nome) == 6 and nome.isdigit()
                )

        except OSError as erro:
            raise RuntimeError(
                f"Erro ao consultar competências no FTP do CAGED: {erro}"
            ) from erro

        finally:
            ftp.close()

        if not competencias:
            raise RuntimeError("Nenhuma competência disponível no FTP do CAGED.")

        competencias = sorted(set(competencias))

        logger.info(
            "%d competências disponíveis (%s a %s).",
            len(competencias),
            competencias[0],
            competencias[-1],
        )

        return competencias

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
                    max_tentativas = 3
                    for tentativa in range(1, max_tentativas + 1):
                        try:
                            with caminho_7z.open("wb") as arquivo:
                                ftp.retrbinary(
                                    f"RETR {nome_arquivo}",
                                    arquivo.write,
                                )
                            break
                        except OSError as erro:
                            if tentativa == max_tentativas:
                                raise RuntimeError(
                                    f"Falha ao baixar {nome_arquivo} após "
                                    f"{max_tentativas} tentativas: {erro}"
                                ) from erro
                            wait = 2**tentativa
                            logger.warning(
                                "Tentativa %d/%d de download de %s falhou: "
                                "%s. Aguardando %ds.",
                                tentativa,
                                max_tentativas,
                                nome_arquivo,
                                erro,
                                wait,
                            )
                            time.sleep(wait)

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

    def coletar(self, **kwargs: Any) -> pd.DataFrame:
        """
        Coleta a série completa do Novo CAGED de Joinville: garante o cache
        de todas as competências do FTP e devolve a série agregada
        (MOV + FOR - EXC) por competência e setor.
        """

        competencias = self.listar_competencias()

        pendentes = [c for c in competencias if not self.cache_completo(c)]
        logger.info(
            "Competências no cache: %d. A baixar: %d.",
            len(competencias) - len(pendentes),
            len(pendentes),
        )

        for posicao, competencia in enumerate(pendentes, start=1):
            logger.info(
                "[%d/%d] Baixando e filtrando %s.",
                posicao,
                len(pendentes),
                competencia,
            )
            self.garantir_cache_joinville(competencia)

        movimentacoes = self.ler_cache(competencias)

        logger.info(
            "Movimentações de Joinville no cache: %d.",
            len(movimentacoes),
        )

        return self.agregar_serie(movimentacoes, competencias)

    def _caminho_cache(self, tipo: str, competencia: str) -> Path:
        return self.cache_dir / f"CAGED{tipo}{competencia}.csv"

    def cache_completo(self, competencia: str) -> bool:
        return all(
            self._caminho_cache(tipo, competencia).exists() for tipo in TIPOS_ARQUIVO
        )

    def garantir_cache_joinville(self, competencia: str) -> None:
        """
        Garante, para uma competência, um CSV pequeno por tipo de arquivo
        (MOV, FOR, EXC) só com as movimentações de Joinville.

        Os arquivos oficiais têm ~500 MB por mês. Depois de filtrados, o .7z
        e o .txt são apagados: só o recorte de Joinville fica em disco.
        """

        if self.cache_completo(competencia):
            return

        arquivos = self._baixar_competencia(competencia)

        for tipo in TIPOS_ARQUIVO:
            destino = self._caminho_cache(tipo, competencia)

            if tipo in arquivos:
                df = self.processar_arquivo_local(str(arquivos[tipo]))
                df = df[list(COLUNAS_MOVIMENTACAO)]
            else:
                df = pd.DataFrame(columns=list(COLUNAS_MOVIMENTACAO))

            arquivo_temporario = destino.with_suffix(".tmp")
            df.to_csv(arquivo_temporario, index=False)
            arquivo_temporario.replace(destino)

        diretorio_bruto = self.download_dir / competencia
        for arquivo in sorted(diretorio_bruto.rglob("*"), reverse=True):
            if arquivo.is_file():
                arquivo.unlink()
            else:
                arquivo.rmdir()
        diretorio_bruto.rmdir()

        logger.info("Cache de Joinville pronto para %s.", competencia)

    def ler_cache(self, competencias: list[str]) -> pd.DataFrame:
        """
        Junta os CSVs de Joinville das competências informadas, com a coluna
        "tipo" (MOV, FOR ou EXC) indicando o arquivo de origem.
        """

        partes = []
        for competencia in competencias:
            for tipo in TIPOS_ARQUIVO:
                df = pd.read_csv(
                    self._caminho_cache(tipo, competencia),
                    dtype={"competênciamov": str, "seção": str},
                )
                df["tipo"] = tipo
                partes.append(df)

        if not partes:
            return pd.DataFrame(columns=[*COLUNAS_MOVIMENTACAO, "tipo"])

        return pd.concat(partes, ignore_index=True)

    @staticmethod
    def agregar_serie(
        df: pd.DataFrame,
        competencias: list[str],
    ) -> pd.DataFrame:
        """
        Calcula admissões, demissões e saldo por competência e setor com a
        metodologia do Ministério do Trabalho:

            MOV da competência
            + FOR (declarações fora do prazo) com aquela competênciamov
            - EXC (exclusões) com aquela competênciamov

        FOR e EXC chegam nos arquivos de meses posteriores, por isso a série
        inteira é recalculada a cada atualização.
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

        df["competencia"] = df["competencia"].astype(str).str[:6]
        df = df[df["competencia"].isin(set(competencias))]

        movimento = (
            pd.to_numeric(df["saldomovimentação"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        sinal = df["tipo"].map({"MOV": 1, "FOR": 1, "EXC": -1}).fillna(0).astype(int)

        df = df.assign(
            admissoes=(movimento == 1).astype(int) * sinal,
            demissoes=(movimento == -1).astype(int) * sinal,
        )

        agregados = df.groupby(
            ["competencia", "setor"],
            as_index=False,
        )[["admissoes", "demissoes"]].sum()

        agregados["saldo"] = agregados["admissoes"] - agregados["demissoes"]
        agregados["competencia"] = (
            agregados["competencia"].str[:4] + "-" + agregados["competencia"].str[4:6]
        )

        return agregados[colunas_finais].sort_values(
            ["competencia", "setor"],
            ignore_index=True,
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

        colunas = {"município", *COLUNAS_MOVIMENTACAO}

        try:
            df = self.read_csv(
                str(caminho),
                sep=";",
                encoding="UTF-8",
                usecols=lambda coluna: coluna in colunas,
                dtype=str,
            )
        except RuntimeError:
            logger.warning("Arquivo fora de UTF-8, relendo em latin-1: %s", caminho)
            df = self.read_csv(
                str(caminho),
                sep=";",
                encoding="latin-1",
                usecols=lambda coluna: coluna in colunas,
                dtype=str,
            )

        if "município" not in df.columns:
            raise ValueError("A coluna 'municipio' não foi encontrada no arquivo.")

        df = df[df["município"].str.strip() == str(codigo_municipio)]

        logger.info(
            "Encontrados %d registros para o município %d.",
            len(df),
            codigo_municipio,
        )

        return df
