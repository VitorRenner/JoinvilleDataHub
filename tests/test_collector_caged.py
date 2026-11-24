import pandas as pd

from src.collectors.caged import CagedCollector

COMPETENCIAS = ["202605", "202606"]


def montar_movimentacoes() -> pd.DataFrame:
    """Simula o cache de Joinville: MOV de 05 e 06, FOR e EXC chegando em 06."""
    return pd.DataFrame(
        {
            "competênciamov": [
                "202605",
                "202605",
                "202606",
                "202606",
                "202606",
                "202605",
                "202605",
                "201912",
            ],
            "seção": ["C", "C", "C", "C", "G", "C", "C", "C"],
            "saldomovimentação": ["1", "-1", "1", "-1", "1", "1", "1", "1"],
            "tipo": ["MOV", "MOV", "MOV", "MOV", "MOV", "FOR", "EXC", "EXC"],
        }
    )


def linha(resultado: pd.DataFrame, competencia: str, setor: str) -> pd.Series:
    filtro = (resultado["competencia"] == competencia) & (resultado["setor"] == setor)
    return resultado[filtro].iloc[0]


def test_competencia_sai_no_formato_aaaa_mm():
    resultado = CagedCollector.agregar_serie(montar_movimentacoes(), COMPETENCIAS)

    assert set(resultado["competencia"]) == {"2026-05", "2026-06"}


def test_for_soma_e_exc_desconta_no_mes_de_origem():
    resultado = CagedCollector.agregar_serie(montar_movimentacoes(), COMPETENCIAS)
    maio = linha(resultado, "2026-05", "C")

    assert maio["admissoes"] == 1
    assert maio["demissoes"] == 1
    assert maio["saldo"] == 0


def test_mes_sem_ajustes_usa_so_o_mov():
    resultado = CagedCollector.agregar_serie(montar_movimentacoes(), COMPETENCIAS)
    junho = linha(resultado, "2026-06", "C")

    assert junho["admissoes"] == 1
    assert junho["demissoes"] == 1
    assert junho["saldo"] == 0


def test_ignora_competencia_fora_da_serie():
    resultado = CagedCollector.agregar_serie(montar_movimentacoes(), COMPETENCIAS)

    assert "2019-12" not in set(resultado["competencia"])


def test_serie_vazia_devolve_colunas_finais():
    resultado = CagedCollector.agregar_serie(pd.DataFrame(), COMPETENCIAS)

    assert list(resultado.columns) == [
        "competencia",
        "setor",
        "admissoes",
        "demissoes",
        "saldo",
    ]


def test_collector_pode_ser_instanciado():
    assert isinstance(CagedCollector(), CagedCollector)
