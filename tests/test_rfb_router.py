from src.database.models import RfbEmpresa
from tests.conftest import TestingSessionLocal


def _inserir_registro(
        competencia: str = "2026-10",
        setor: str = "C Indústrias de transformação",
) -> int:
    """
    Insere um registro direto pela sessão de teste e devolve o id.

    Não usa o upsert_rfb porque ele usa o INSERT ... ON CONFLICT do
    PostgreSQL, e os testes rodam em SQLite.
    """

    db = TestingSessionLocal()

    try:
        registro = RfbEmpresa(
            competencia=competencia,
            setor=setor,
            ativas=100,
            aberturas=5,
            encerramentos=2,
            ativas_mei=30,
            ativas_simples=20,
        )

        db.add(registro)
        db.commit()
        db.refresh(registro)

        return registro.id

    finally:
        db.close()


def test_listar_rfb_vazio(client):
    resp = client.get("/rfb/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_stats_resumo_rfb(client):
    resp = client.get("/rfb/stats/resumo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_registros"] == 0
    assert "competencias" in data


def test_buscar_rfb_id_inexistente(client):
    resp = client.get("/rfb/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Registro não encontrado."


def test_filtrar_rfb_por_competencia(client):
    _inserir_registro(competencia="2026-09")
    _inserir_registro(competencia="2026-10")

    resp = client.get("/rfb/", params={"competencia": "2026-10"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["competencia"] == "2026-10"


def test_incluir_total_false_esconde_linha_total(client):
    _inserir_registro(setor="C Indústrias de transformação")
    _inserir_registro(setor="Total")

    resp = client.get("/rfb/", params={"incluir_total": "false"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["setor"] != "Total"


def test_competencia_em_formato_errado_devolve_422(client):
    resp = client.get("/rfb/", params={"competencia": "2026/10"})
    assert resp.status_code == 422