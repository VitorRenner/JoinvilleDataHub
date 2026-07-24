from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import caged, ibge
from src.scheduler.scheduler import iniciar_scheduler, parar_scheduler

API_TITLE = "CAGED API - Joinville"
API_DESCRIPTION = "API para dados de emprego e desemprego de Joinville/SC"
API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Executa ações durante inicialização e encerramento da aplicação.
    """

    iniciar_scheduler()

    yield

    parar_scheduler()


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    caged.router,
    prefix="/caged",
    tags=["CAGED"],
)

app.include_router(
    ibge.router,
    prefix="/ibge",
    tags=["IBGE"],
)


@app.get(
    "/",
    summary="Informações da API",
)
def root() -> dict:
    """
    Retorna informações básicas da API.
    """

    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "endpoints": {
            "caged": "/caged",
            "ibge": "/ibge",
        },
    }


@app.get(
    "/health",
    summary="Status da aplicação",
)
def health_check() -> dict:
    """
    Verifica se a aplicação está disponível.
    """

    return {
        "status": "healthy",
        "application": API_TITLE,
        "version": API_VERSION,
        "scheduler": "enabled",
    }
