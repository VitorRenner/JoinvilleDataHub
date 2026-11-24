def test_list_caged_empty(client):
    resp = client.get("/caged/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_stats_resumo(client):
    resp = client.get("/caged/stats/resumo")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_registros" in data
    assert data["total_registros"] == 0

def _inserir_caged(competencia: str, setor: str, admissoes: int, demissoes: int):
    from src.database.models import CagedMovimentacao
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        db.add(
            CagedMovimentacao(
                competencia=competencia,
                setor=setor,
                admissoes=admissoes,
                demissoes=demissoes,
                saldo=admissoes - demissoes,
            )
        )
        db.commit()
    finally:
        db.close()


def test_serie_soma_setores_por_competencia_em_ordem(client):
    _inserir_caged("2026-02", "C", 10, 4)
    _inserir_caged("2026-01", "C", 5, 5)
    _inserir_caged("2026-02", "G", 3, 1)

    resp = client.get("/caged/serie")

    assert resp.status_code == 200
    assert resp.json() == [
        {"competencia": "2026-01", "admissoes": 5, "demissoes": 5, "saldo": 0},
        {"competencia": "2026-02", "admissoes": 13, "demissoes": 5, "saldo": 8},
    ]


def test_serie_filtra_intervalo(client):
    _inserir_caged("2025-12", "C", 1, 0)
    _inserir_caged("2026-01", "C", 2, 0)

    resp = client.get("/caged/serie", params={"competencia_inicial": "2026-01"})

    assert [linha["competencia"] for linha in resp.json()] == ["2026-01"]


def test_listar_caged_rejeita_competencia_fora_do_formato(client):
    resp = client.get("/caged/", params={"competencia": "202601"})

    assert resp.status_code == 422


def test_listar_caged_ordena_por_competencia(client):
    _inserir_caged("2026-02", "C", 1, 0)
    _inserir_caged("2026-01", "C", 1, 0)

    resp = client.get("/caged/")

    assert [linha["competencia"] for linha in resp.json()] == ["2026-01", "2026-02"]


def test_stats_resumo_caged_lista_periodos(client):
    _inserir_caged("2026-01", "C", 1, 0)
    _inserir_caged("2026-02", "C", 1, 0)

    data = client.get("/caged/stats/resumo").json()

    assert data["periodos"] == ["2026-01", "2026-02"]
    assert data["ultimo_periodo"] == "2026-02"
