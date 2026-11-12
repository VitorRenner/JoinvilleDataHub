import pandas as pd

from src.collectors.caged import CagedCollector


def montar_movimentacoes() -> pd.DataFrame:
    """Simula registros de Joinville vindos dos arquivos MOV, FOR e EXC de 202606."""
    return pd.DataFrame(
        {
            "competênciamov": [202606, 202606, 202606, 202605],
            "seção": ["C", "C", "G", "C"],
            "saldomovimentação": [1, -1, 1, 1],
        }
    )


def test_agregar_mantem_so_a_competencia_do_arquivo():
    resultado = CagedCollector._agregar_movimentacoes(montar_movimentacoes(), "202606")

    assert set(resultado["competencia"].astype(str)) == {"202606"}


def test_agregar_conta_admissoes_e_demissoes_da_competencia():
    resultado = CagedCollector._agregar_movimentacoes(montar_movimentacoes(), "202606")
    industria = resultado[resultado["setor"] == "C"].iloc[0]

    assert industria["admissoes"] == 1
    assert industria["demissoes"] == 1
    assert industria["saldo"] == 0