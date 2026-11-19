import hashlib
import secrets
import time

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.database.models.api_token import ApiToken

# Teto de validade: um token esquecido não fica válido por muito tempo
VALIDADE_MAXIMA_MINUTOS = 60


def _hash(token: str) -> str:
    # O token tem 256 bits aleatórios: SHA-256 simples basta (não é senha
    # escolhida por humano, então não precisa de bcrypt/argon2)
    return hashlib.sha256(token.encode()).hexdigest()


def emitir_token(db: Session, descricao: str, validade_minutos: int = 15) -> str:
    """
    Cria um token de uso único e devolve o valor em texto puro.

    O texto puro só existe neste retorno; no banco fica apenas o hash.
    """

    if not 1 <= validade_minutos <= VALIDADE_MAXIMA_MINUTOS:
        raise ValueError(
            f"Validade deve ficar entre 1 e {VALIDADE_MAXIMA_MINUTOS} minutos.",
        )

    descricao = descricao.strip()
    if not descricao or len(descricao) > 100:
        raise ValueError("Descrição obrigatória, com até 100 caracteres.")

    token = secrets.token_urlsafe(32)
    agora = int(time.time())

    db.add(
        ApiToken(
            token_hash=_hash(token),
            descricao=descricao,
            criado_em=agora,
            expira_em=agora + validade_minutos * 60,
        ),
    )
    db.commit()

    return token


def consumir_token(db: Session, token: str) -> bool:
    """
    Marca o token como usado se ele existir, não tiver sido usado e não
    tiver vencido. Devolve True só para quem consumiu.

    Um único UPDATE condicional faz checagem e consumo juntos: duas
    requisições simultâneas com o mesmo token não passam as duas.
    """

    agora = int(time.time())

    resultado = db.execute(
        update(ApiToken)
        .where(
            ApiToken.token_hash == _hash(token),
            ApiToken.usado_em.is_(None),
            ApiToken.expira_em > agora,
        )
        .values(usado_em=agora),
    )
    db.commit()

    return resultado.rowcount == 1
