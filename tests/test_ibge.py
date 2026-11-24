from src.database.models import IbgeIndicador
from src.transformers.ibge import transformar_ibge, validar_ibge
from tests.conftest import TestingSessionLocal


def _linha_sidra(ano: str, valor: str, indicador: str = "pib") -> dict:
    return {
        "V": valor,
        "D3C": ano,
        "D2N": "Produto Interno Bruto a preços correntes",
        "MN": "Mil Reais",
        "indicador": indicador,
    }


def _inserir(ano: str, indicador: str, valor: float) -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            IbgeIndicador(
                ano=ano,
                indicador=indicador,
                descricao=f"Descrição de {indicador}",
                valor=valor,
                unidade="Unidade",
            )
        )
        db.commit()
    finally:
        db.close()


def test_transformar_converte_valor_e_campos():
    registros = transformar_ibge([_linha_sidra("2023", "49815877")])

    assert registros == [
        {
            "ano": "2023",
            "indicador": "pib",
            "descricao": "Produto Interno Bruto a preços correntes",
            "valor": 49815877.0,
            "unidade": "Mil Reais",
        }
    ]


def test_transformar_ignora_valores_sem_dado():
    linhas = [_linha_sidra("2023", valor) for valor in ("-", "...", "X", "")]

    assert transformar_ibge(linhas) == []


def test_validar_separa_ano_invalido():
    registros = transformar_ibge([_linha_sidra("23", "10"), _linha_sidra("2023", "10")])

    validos, invalidos = validar_ibge(registros)

    assert [r["ano"] for r in validos] == ["2023"]
    assert len(invalidos) == 1


def test_listar_ibge_vazio(client):
    resp = client.get("/ibge/")

    assert resp.status_code == 200
    assert resp.json() == []


def test_listar_ibge_filtra_por_indicador_em_ordem(client):
    _inserir("2023", "pib", 3.0)
    _inserir("2021", "pib", 1.0)
    _inserir("2026", "populacao_estimada", 673980.0)

    resp = client.get("/ibge/", params={"indicador": "pib"})

    assert resp.status_code == 200
    assert [r["ano"] for r in resp.json()] == ["2021", "2023"]


def test_listar_ibge_rejeita_ano_invalido(client):
    resp = client.get("/ibge/", params={"ano": "23"})

    assert resp.status_code == 422


def test_joinville_devolve_ultimo_ano_de_cada_indicador(client):
    _inserir("2022", "pib", 2.0)
    _inserir("2023", "pib", 3.0)
    _inserir("2026", "populacao_estimada", 673980.0)

    resp = client.get("/ibge/joinville")

    assert resp.status_code == 200
    assert {(r["indicador"], r["ano"]) for r in resp.json()} == {
        ("pib", "2023"),
        ("populacao_estimada", "2026"),
    }


def test_stats_resumo_ibge(client):
    _inserir("2023", "pib", 3.0)

    resp = client.get("/ibge/stats/resumo")

    assert resp.status_code == 200
    assert resp.json() == {
        "total_registros": 1,
        "indicadores": ["pib"],
        "periodos": ["2023"],
        "ultimo_periodo": "2023",
    }


def test_buscar_ibge_por_id_inexistente(client):
    resp = client.get("/ibge/999")

    assert resp.status_code == 404
