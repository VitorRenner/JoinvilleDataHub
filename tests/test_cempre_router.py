from src.database.models import CempreEmprego
from tests.conftest import TestingSessionLocal


def _inserir_registro(
        ano: str = "2023",
        setor: str = "C Indústrias de transformação",
) -> int:
    """
    Insere um registro direto pela sessão de teste e devolve o id.

    Não usa o upsert_cempre porque ele usa o INSERT ... ON CONFLICT do
    PostgreSQL, e os testes rodam em SQLite.
    """

    db = TestingSessionLocal()

    try:
        registro = CempreEmprego(
            ano=ano,
            setor=setor,
            unidades_locais=1500,
            pessoal_ocupado=60000,
            salario_medio=4321.5,
        )

        db.add(registro)
        db.commit()
        db.refresh(registro)

        return registro.id

    finally:
        db.close()


def test_listar_cempre_vazio(client):
    resp = client.get("/cempre/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_stats_resumo_cempre(client):
    resp = client.get("/cempre/stats/resumo")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_registros" in data
    assert data["total_registros"] == 0


def test_buscar_cempre_id_inexistente(client):
    resp = client.get("/cempre/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Registro não encontrado."


def test_listar_cempre_com_registro(client):
    _inserir_registro()

    resp = client.get("/cempre/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ano"] == "2023"
    assert data[0]["salario_medio"] == 4321.5


def test_filtrar_cempre_por_ano_e_setor(client):
    _inserir_registro(ano="2022")
    _inserir_registro(ano="2023", setor="G Comércio")

    resp = client.get("/cempre/", params={"ano": "2023", "setor": "comércio"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["setor"] == "G Comércio"


def test_buscar_cempre_por_id(client):
    registro_id = _inserir_registro()

    resp = client.get(f"/cempre/{registro_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == registro_id


def test_root_lista_cempre(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["endpoints"]["cempre"] == "/cempre" \


def test_listar_cempre_sem_total(client):
    _inserir_registro(setor="Total")
    _inserir_registro(setor="C Indústrias de transformação")

    resp = client.get("/cempre/")
    assert len(resp.json()) == 2

    resp = client.get("/cempre/", params={"incluir_total": "false"})
    assert resp.status_code == 200
    setores = [registro["setor"] for registro in resp.json()]
    assert setores == ["C Indústrias de transformação"]