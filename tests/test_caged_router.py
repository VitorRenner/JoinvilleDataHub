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