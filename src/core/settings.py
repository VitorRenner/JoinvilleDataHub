from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    "Configurações globais da aplicação."

    ENVIRONMENT: str = "development"

    API_TITLE: str = "CAGED_API - Joinville"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API para dados do CAGED e do IBGE."

    DATABASE_URL: str                  #sem padrão -> vem obrigatoriamente do .env

    CAGED_BASE_URL: str = "https://portaldatransparencia.gov.br"
    IBGE_BASE_URL: str = "https://servicodados.ibge.gov.br/api/v1"
    CEMPRE_BASE_URL: str = "https://apisidra.ibge.gov.br"

    #Novo CAGED é mensal -> checar uma vez ao dia
    SCHEDULER_INTERVAL_SECONDS: int = 86400

    # CEMPRE é anual -> roda todo dia 1º às 3h
    SCHEDULER_CEMPRE_DIA: int = 1
    SCHEDULER_CEMPRE_HORA: int = 3

    # ------------------------- RFB (Receita Federal Brasileira ) --------------------------------------
    # Movido para esta seção
    # (antes estava fora do padrão da classe -> settings.RFB ... resultava em erro AttributeError).

    RFB_BASE_URL: str = "https://arquivos.receitafederal.gov.br"
    #URL confirmada no Google Chrome, entra listando os arquivos do site da Receita Federal Brasileira
    # (RFB), com pastas mensais.

    #Ela (RFB) lista as pastas com AAAA-MM



    RFB_SHARE_TOKEN: str = "YggdBLfdninEJX9"

    RFB_WEBDAV_PATH: str = "/public.php/webdav"

    RFB_MUNICIPIO_JOINVILLE: str = "8179"

    # Continua o campo de configuração da URL até o script de hoje encontrar o código.
    # Também valora como TEXTO, não como INTEIRO, preservando os zeros à esquerda.

    RFB_PASTA_TEMP: str = "data/rfb_temp"
    # É necessário fechar e completar exatamente com a linha do arquivo.gitignore

    RFB_TIMEOUT_SEGUNDOS: int = 300
    RFB_TENTATIVAS: int = 3

    # Como o servidor da Receita Federal Brasileira é lento e cai, deixamos como 3 com um valor generoso.

    #--------------------------------------------------------------------------------- fim do bloco

    DEBUG: bool = False
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = True,
        extra = "ignore",
     )

settings = Settings()

# Nada mais da RFB para cá

