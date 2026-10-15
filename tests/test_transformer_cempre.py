import pandas as pd

from src.transformers.cempre import (
    transformar_cempre,
    validar_dados,
)


def _linha(codigo_variavel: str, setor: str, valor: str) -> dict:
    """
    Monta uma linha no mesmo formato que o SIDRA devolve.
    """

    return {
        "D2C": codigo_variavel,
        "D3N": "2024",
        "D4N": setor,
        "V": valor,
    }


def _dataframe(*linhas: dict) -> pd.DataFrame:
    return pd.DataFrame(list(linhas))


def test_valores_numericos_sao_convertidos():
    df = _dataframe(
        _linha("706", "C Indústrias de transformação", "3847"),
        _linha("707", "C Indústrias de transformação", "78778"),
        _linha("10143", "C Indústrias de transformação", "4494.44"),
    )

    [registro] = transformar_cempre(df)

    assert registro == {
        "ano": "2024",
        "setor": "C Indústrias de transformação",
        "unidades_locais": 3847,
        "pessoal_ocupado": 78778,
        "salario_medio": 4494.44,
    }
    assert type(registro["unidades_locais"]) is int
    assert type(registro["salario_medio"]) is float


def test_traco_vira_zero_absoluto():
    df = _dataframe(
        _linha("706", "T Serviços domésticos", "-"),
        _linha("707", "T Serviços domésticos", "-"),
        _linha("10143", "T Serviços domésticos", "-"),
    )

    [registro] = transformar_cempre(df)

    assert registro["unidades_locais"] == 0
    assert registro["pessoal_ocupado"] == 0
    assert registro["salario_medio"] == 0.0


def test_sigiloso_e_nao_disponivel_viram_none():
    df = _dataframe(
        _linha("706", "B Indústrias extrativas", "X"),
        _linha("707", "B Indústrias extrativas", "..."),
        _linha("10143", "B Indústrias extrativas", ".."),
    )

    [registro] = transformar_cempre(df)

    assert registro["unidades_locais"] is None
    assert registro["pessoal_ocupado"] is None
    assert registro["salario_medio"] is None


def test_variavel_ausente_vira_none_e_nao_zero():
    df = _dataframe(
        _linha("706", "F Construção", "4789"),
        _linha("707", "F Construção", "14395"),
    )

    [registro] = transformar_cempre(df)

    assert registro["salario_medio"] is None


def test_validacao_aceita_none():
    df = _dataframe(
        _linha("706", "B Indústrias extrativas", "X"),
        _linha("707", "B Indústrias extrativas", "392"),
        _linha("10143", "B Indústrias extrativas", "5147.51"),
    )

    validos, invalidos = validar_dados(transformar_cempre(df))

    assert len(validos) == 1
    assert invalidos == []


def test_validacao_rejeita_negativo():
    registro = {
        "ano": "2024",
        "setor": "F Construção",
        "unidades_locais": -1,
        "pessoal_ocupado": 10,
        "salario_medio": 100.0,
    }

    validos, invalidos = validar_dados([registro])

    assert validos == []
    assert "unidades_locais não pode ser negativo." in invalidos[0]["_erros"]


def test_dataframe_vazio():
    assert transformar_cempre(pd.DataFrame()) == []