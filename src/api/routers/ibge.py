from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def status_ibge() -> dict:
    """
    Retorna informações sobre os endpoints do IBGE.
    """

    return {
        "message": "Endpoints do IBGE.",
        "status": "Em desenvolvimento.",
    }


@router.get("/municipios")
def listar_municipios() -> dict:
    """
    Lista os municípios disponíveis.
    """

    return {
        "municipios": [
            {
                "id": 4209102,
                "nome": "Joinville",
                "estado": "SC",
            }
        ]
    }
