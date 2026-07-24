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

    SCHEDULER_INTERVAL_SECONDS: int = 30

    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
