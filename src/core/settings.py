from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    "Configurações globais da aplicação."

    ENVIRONMENT: str = "development"

    API_TITLE: str = "Joinville Data Hub"
    API_VERSION: str = "1.1.0"
    API_DESCRIPTION: str = (
        "API de dados públicos de Joinville/SC: "
        "CAGED (emprego), CEMPRE/IBGE (empresas e salários) e RFB (CNPJ)."
    )

    DATABASE_URL: str  # sem padrão -> vem obrigatoriamente do .env

    # Novo CAGED: microdados no FTP do Ministério do Trabalho
    CAGED_FTP_HOST: str = "ftp.mtps.gov.br"
    CAGED_FTP_DIRETORIO: str = "pdet/microdados/NOVO CAGED"
    # Microdados do CAGED usam o código IBGE sem dígito verificador
    CAGED_MUNICIPIO_JOINVILLE: int = 420910

    # Código IBGE completo de Joinville (usado no CEMPRE/SIDRA e no IBGE)
    IBGE_MUNICIPIO_JOINVILLE: int = 4209102

    IBGE_BASE_URL: str = "https://servicodados.ibge.gov.br/api/v1"
    CEMPRE_BASE_URL: str = "https://apisidra.ibge.gov.br"

    # Novo CAGED é mensal -> checar uma vez ao dia, às 2h (horário de Brasília)
    SCHEDULER_CAGED_HORA: int = 2

    # CEMPRE é anual -> roda todo dia 1º às 3h
    SCHEDULER_CEMPRE_DIA: int = 1
    SCHEDULER_CEMPRE_HORA: int = 3

    # -------------------- RFB (Receita Federal Brasileira) --------------------
    # Servidor de arquivos da RFB, com uma pasta por competência (AAAA-MM)
    RFB_BASE_URL: str = "https://arquivos.receitafederal.gov.br"
    RFB_WEBDAV_PATH: str = "/public.php/webdav"

    # Token do link público (vem do .env). Vazio por padrão para a API e o CI
    # subirem sem ele; o collector da RFB recusa rodar se estiver vazio.
    RFB_SHARE_TOKEN: str = ""

    # Código de Joinville na tabela própria da RFB (não é o código IBGE).
    # Texto, e não inteiro, para preservar zeros à esquerda.
    RFB_MUNICIPIO_JOINVILLE: str = "8179"

    # Pasta dos downloads, apagada ao fim de cada execução (está no .gitignore)
    RFB_PASTA_TEMP: str = "data/rfb_temp"

    # Servidor da RFB é lento e instável: timeout alto e novas tentativas
    RFB_TIMEOUT_SEGUNDOS: int = 300
    RFB_TENTATIVAS: int = 3

    # Linhas do CSV lidas por vez; cada bloco é filtrado e descartado
    RFB_TAMANHO_BLOCO: int = 500_000

    # Publicação mensal sem data exata -> job todo dia 15 às 4h
    SCHEDULER_RFB_DIA: int = 15
    SCHEDULER_RFB_HORA: int = 4
    # ----------------------------- fim do bloco RFB ------------------------------

    # Origens liberadas no CORS (front Nexus). No .env, usar formato JSON:
    # CORS_ORIGINS=["http://localhost:3000","https://nexus.exemplo.com"]
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    DEBUG: bool = False
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
