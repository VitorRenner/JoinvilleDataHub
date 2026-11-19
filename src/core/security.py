from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from src.database.conexao import get_db
from src.database.repositorio_tokens import consumir_token

# auto_error=False: header ausente cai no mesmo 401 de token inválido,
# sem revelar qual dos casos aconteceu
token_header = APIKeyHeader(
    name="X-API-Token",
    auto_error=False,
    description=(
        "Token de uso único, emitido no servidor com "
        "`python -m src.scripts.gerar_token`. Vale para uma escrita."
    ),
)


def exigir_token_uso_unico(
    token: str | None = Security(token_header),
    db: Session = Depends(get_db),
) -> None:
    """
    Libera a rota de escrita consumindo um token de uso único.

    Não existe rota HTTP que emita tokens: só quem tem acesso ao servidor
    e ao banco consegue gerar um. Sem token emitido, a escrita fica
    fechada.
    """

    if not token or not consumir_token(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente, inválido, vencido ou já usado.",
            headers={"WWW-Authenticate": "APIKey"},
        )
