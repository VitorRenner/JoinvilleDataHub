import pandas as pd

from src.transformers.rfb import (
    SETOR_NAO_CLASSIFICADO,
    SETOR_TOTAL,
    transformar_rfb,
    validar_dados,
)

COMPETENCIA = "2026-10"


def _estabelecimento(
        cnpj_basico: str,
        cnae: str = "2512800",
        situacao: str = "02",
        data_situacao: str = "20200101",
        data_inicio: str = "20200101",
) -> dict:
    """
    Monta uma linha no mesmo formato que o collector entrega
    (tudo como texto, igual ao CSV da RFB).
    """

    return {
        "cnpj_basico": cnpj_basico,
        "situacao_cadastral": situacao,
        "data_situacao_cadastral": data_situacao,
        "data_inicio_atividade": data_inicio,
        "cnae_fiscal_principal": cnae,
    }


def _transformar(
        estabelecimentos: list[dict],
        simples: list[dict] | None = None,
) -> dict[str, dict]:
    """
    Roda o transformer e devolve os registros indexados pelo setor,
    para o teste não depender da ordem da lista.
    """

    empresas_df = pd.DataFrame(
        [{"cnpj_basico": e["cnpj_basico"], "porte": "01"} for e in estabelecimentos]
    )
    simples_df = pd.DataFrame(
        simples or [],
        columns=["cnpj_basico", "opcao_simples", "opcao_mei"],
    )

    registros = transformar_rfb(
        COMPETENCIA,
        pd.DataFrame(estabelecimentos),
        empresas_df,
        simples_df,
    )

    return {registro["setor"]: registro for registro in registros}


def test_estabelecimentos_vazio_devolve_lista_vazia():
    vazio = pd.DataFrame()

    assert transformar_rfb(COMPETENCIA, vazio, vazio, vazio) == []


def test_cnae_vira_secao_e_total_soma_os_setores():
    por_setor = _transformar([
        _estabelecimento("00000001", cnae="2512800"),
        _estabelecimento("00000002", cnae="2941700"),
        _estabelecimento("00000003", cnae="4711302"),
    ])

    assert por_setor["C Indústrias de transformação"]["ativas"] == 2
    assert por_setor[
        "G Comércio; reparação de veículos automotores e motocicletas"
    ]["ativas"] == 1
    assert por_setor[SETOR_TOTAL]["ativas"] == 3


def test_cnae_fora_do_mapa_vira_nao_classificado():
    por_setor = _transformar([
        _estabelecimento("00000001", cnae="0000000"),
    ])

    assert por_setor[SETOR_NAO_CLASSIFICADO]["ativas"] == 1


def test_aberturas_e_encerramentos_contam_so_o_mes_da_competencia():
    por_setor = _transformar([
        _estabelecimento("00000001", data_inicio="20261005"),
        _estabelecimento("00000002", data_inicio="20260915"),
        _estabelecimento(
            "00000003", situacao="08", data_situacao="20261020",
        ),
        _estabelecimento(
            "00000004", situacao="08", data_situacao="20260301",
        ),
    ])

    total = por_setor[SETOR_TOTAL]
    assert total["aberturas"] == 1
    assert total["encerramentos"] == 1
    assert total["ativas"] == 2


def test_mei_nao_conta_tambem_como_simples():
    por_setor = _transformar(
        [
            _estabelecimento("00000001"),
            _estabelecimento("00000002"),
            _estabelecimento("00000003"),
            _estabelecimento("00000004"),
        ],
        simples=[
            {"cnpj_basico": "00000001", "opcao_simples": "S", "opcao_mei": "S"},
            {"cnpj_basico": "00000002", "opcao_simples": "S", "opcao_mei": "N"},
            {"cnpj_basico": "00000003", "opcao_simples": "N", "opcao_mei": "N"},
        ],
    )

    total = por_setor[SETOR_TOTAL]
    assert total["ativas"] == 4
    assert total["ativas_mei"] == 1
    assert total["ativas_simples"] == 1


def test_validar_dados_separa_validos_e_invalidos():
    valido = {
        "competencia": COMPETENCIA,
        "setor": "F Construção",
        "ativas": 10,
        "aberturas": 1,
        "encerramentos": 0,
        "ativas_mei": 3,
        "ativas_simples": 2,
    }
    competencia_errada = {**valido, "competencia": "2026/10"}
    soma_estourada = {**valido, "ativas_mei": 8, "ativas_simples": 5}
    negativo = {**valido, "aberturas": -1}

    validos, invalidos = validar_dados(
        [valido, competencia_errada, soma_estourada, negativo]
    )

    assert validos == [valido]
    assert len(invalidos) == 3
    assert [registro["_linha"] for registro in invalidos] == [1, 2, 3]