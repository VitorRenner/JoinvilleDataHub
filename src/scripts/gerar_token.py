"""
Emite um token de uso único para as rotas de escrita da API.

Roda só no servidor (precisa do DATABASE_URL do .env). Não existe rota
HTTP equivalente, de propósito.

Uso:
    uv run python -m src.scripts.gerar_token --descricao "carga manual CAGED"
    uv run python -m src.scripts.gerar_token --descricao "correção" --minutos 5
"""

import argparse

from src.database.conexao import SessionLocal
from src.database.repositorio_tokens import VALIDADE_MAXIMA_MINUTOS, emitir_token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--descricao",
        required=True,
        help="Para que o token será usado (fica registrado no banco).",
    )
    parser.add_argument(
        "--minutos",
        type=int,
        default=15,
        help=f"Validade em minutos (1 a {VALIDADE_MAXIMA_MINUTOS}, padrão 15).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        token = emitir_token(db, args.descricao, args.minutos)
    finally:
        db.close()

    # Impresso uma única vez: o banco guarda só o hash
    print(token)
    print(
        f"Uso único, válido por {args.minutos} min. "
        "Envie no header X-API-Token.",
    )


if __name__ == "__main__":
    main()
