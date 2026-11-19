import time

import pytest
from sqlalchemy import select

from src.database.models.api_token import ApiToken
from src.database.repositorio_tokens import (
    VALIDADE_MAXIMA_MINUTOS,
    consumir_token,
    emitir_token,
)
from src.schemas.caged import CAGED_BULK_MAX_REGISTROS
from tests.conftest import TestingSessionLocal

REGISTRO = {
    "competencia": "202606",
    "setor": "Indústria",
    "admissoes": 10,
    "demissoes": 4,
    "saldo": 6,
}


@pytest.fixture
def db():
    sessao = TestingSessionLocal()
    yield sessao
    sessao.close()


@pytest.fixture
def novo_token(db):
    """Emite um token de uso único novo a cada chamada."""

    def _emitir(minutos: int = 15) -> str:
        return emitir_token(db, "teste", minutos)

    return _emitir


def cabecalho(token: str) -> dict[str, str]:
    return {"X-API-Token": token}


# ------------------------------ autenticação ------------------------------


def test_post_sem_token_retorna_401(client):
    resp = client.post("/caged/", json=REGISTRO)
    assert resp.status_code == 401


def test_post_com_token_inexistente_retorna_401(client):
    resp = client.post("/caged/", json=REGISTRO, headers=cabecalho("inventado"))
    assert resp.status_code == 401


def test_post_com_token_valido_grava(client, novo_token):
    resp = client.post("/caged/", json=REGISTRO, headers=cabecalho(novo_token()))
    assert resp.status_code == 201

    lista = client.get("/caged/").json()
    assert len(lista) == 1
    assert lista[0]["setor"] == "Indústria"


def test_token_nao_pode_ser_reutilizado(client, novo_token):
    token = novo_token()

    primeira = client.post("/caged/", json=REGISTRO, headers=cabecalho(token))
    segunda = client.post("/caged/", json=REGISTRO, headers=cabecalho(token))

    assert primeira.status_code == 201
    assert segunda.status_code == 401


def test_token_vencido_retorna_401(client, db, novo_token):
    token = novo_token()
    # Força o vencimento direto no banco
    registro = db.scalars(select(ApiToken)).one()
    registro.expira_em = int(time.time()) - 1
    db.commit()

    resp = client.post("/caged/", json=REGISTRO, headers=cabecalho(token))
    assert resp.status_code == 401


def test_bulk_sem_token_retorna_401(client):
    resp = client.post("/caged/bulk", json={"registros": [REGISTRO]})
    assert resp.status_code == 401


def test_delete_sem_token_retorna_401_e_nao_apaga(client, novo_token):
    client.post("/caged/", json=REGISTRO, headers=cabecalho(novo_token()))
    registro_id = client.get("/caged/").json()[0]["id"]

    resp = client.delete(f"/caged/{registro_id}")

    assert resp.status_code == 401
    assert len(client.get("/caged/").json()) == 1


def test_delete_com_token_valido_apaga(client, novo_token):
    client.post("/caged/", json=REGISTRO, headers=cabecalho(novo_token()))
    registro_id = client.get("/caged/").json()[0]["id"]

    resp = client.delete(f"/caged/{registro_id}", headers=cabecalho(novo_token()))

    assert resp.status_code == 200
    assert client.get("/caged/").json() == []


def test_leitura_continua_publica(client):
    assert client.get("/caged/").status_code == 200
    assert client.get("/caged/stats/resumo").status_code == 200


def test_nao_existe_rota_http_para_emitir_token(client):
    rotas = {getattr(r, "path", "") for r in client.app.routes}
    assert not any("token" in rota for rota in rotas)


# -------------------------- repositório de tokens -------------------------


def test_banco_guarda_so_o_hash(db, novo_token):
    token = novo_token()
    registro = db.scalars(select(ApiToken)).one()

    assert registro.token_hash != token
    assert len(registro.token_hash) == 64


def test_consumir_token_so_funciona_uma_vez(db, novo_token):
    token = novo_token()
    assert consumir_token(db, token) is True
    assert consumir_token(db, token) is False


@pytest.mark.parametrize("minutos", [0, VALIDADE_MAXIMA_MINUTOS + 1])
def test_emitir_rejeita_validade_fora_do_limite(db, minutos):
    with pytest.raises(ValueError):
        emitir_token(db, "teste", minutos)


def test_emitir_exige_descricao(db):
    with pytest.raises(ValueError):
        emitir_token(db, "   ", 15)


# ------------------------------- validação --------------------------------


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("competencia", "2026-06"),
        ("competencia", "20260"),
        ("setor", ""),
        ("setor", "x" * 101),
        ("admissoes", -1),
        ("demissoes", -5),
    ],
)
def test_post_rejeita_dado_invalido(client, novo_token, campo, valor):
    resp = client.post(
        "/caged/",
        json={**REGISTRO, campo: valor},
        headers=cabecalho(novo_token()),
    )
    assert resp.status_code == 422


def test_saldo_negativo_e_aceito(client, novo_token):
    registro = {**REGISTRO, "admissoes": 1, "demissoes": 5, "saldo": -4}
    resp = client.post("/caged/", json=registro, headers=cabecalho(novo_token()))
    assert resp.status_code == 201


def test_bulk_acima_do_limite_retorna_422(client, novo_token):
    registros = [REGISTRO] * (CAGED_BULK_MAX_REGISTROS + 1)
    resp = client.post(
        "/caged/bulk",
        json={"registros": registros},
        headers=cabecalho(novo_token()),
    )
    assert resp.status_code == 422


def test_bulk_vazio_retorna_422(client, novo_token):
    resp = client.post(
        "/caged/bulk",
        json={"registros": []},
        headers=cabecalho(novo_token()),
    )
    assert resp.status_code == 422


# ---------------------------------- CORS ----------------------------------


def test_cors_nao_libera_credenciais(client):
    resp = client.options(
        "/caged/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Token",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-credentials" not in resp.headers


def test_cors_bloqueia_metodo_nao_usado(client):
    resp = client.options(
        "/caged/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
        },
    )
    assert resp.status_code == 400
