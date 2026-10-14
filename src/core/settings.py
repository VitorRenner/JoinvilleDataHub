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