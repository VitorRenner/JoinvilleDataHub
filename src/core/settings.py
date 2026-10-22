from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações globais da aplicação.
    """

    ENVIRONMENT: str = "development"

    API_TITLE: str = "CAGED API - Joinville"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API para dados do CAGED e IBGE."

    DATABASE_URL: str

    CAGED_BASE_URL: str = "https://portaldatransparencia.gov.br"

    IBGE_BASE_URL: str = "https://servicodados.ibge.gov.br/api/v1"

    CEMPRE_BASE_URL: str = "https://apisidra.ibge.gov.br"

    # O Novo CAGED é publicado mensalmente pelo Ministério do Trabalho, então
    # o padrão verifica por atualizações uma vez por dia.
    SCHEDULER_INTERVAL_SECONDS: int = 86400

    # O CEMPRE só sai uma vez por ano, então não faz sentido checar todo dia.
    # Roda uma vez por mês, numa data fixa (dia 1º, às 3h da manhã).
    SCHEDULER_CEMPRE_DIA: int = 1
    SCHEDULER_CEMPRE_HORA: int = 3

    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

#  RFB (Receita Federal / CNPJ)

RFB_BASE_URL: str = "<endereço da pasta de dados abertos do CNPJ>"
# ↑ confirme abrindo no navegador: deve listar pastas AAAA-MM

RFB_MUNICIPIO_JOINVILLE: str = ""
# ↑ vazio de propósito: quem preenche é o script de hoje
# É STRING, não int, pelo mesmo motivo do cnpj_basico (zeros à esquerda)

RFB_PASTA_TEMP: str = "data/rfb_temp"
# ↑ precisa bater EXATAMENTE com o que você pôs no .gitignore

RFB_TIMEOUT_SEGUNDOS: int = 300
RFB_TENTATIVAS: int = 3
# ↑ o servidor da Receita é lento e cai; valores generosos