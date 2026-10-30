"""
Transformer da Receita Federal Brasileira(RFB).

Recebe as tabelas juntas de Joinville do collector (Estabelecimentos, Empresas e Simples), junta pelo
cnpj_basico e agrega por seção da CNAE 2.0.
Nenhum dado de empresa individual sai daqui: só contagem por setor,
"""

import logging

import re

from typing import TypedDict

import pandas as pd

logger = logging.getLogger(__name__)

#----------------------------------- Constantes -----------------------------------------

SITUACAO_ATIVA = "02"
SITUACAO_BAIXADA = "08"
# Códigos do layout oficial da RFB (docs/cnpj-metadados.pdf).

SETOR_TOTAL = "Total"
SETOR_NAO_CLASSIFICADO = "Não classificado"

CONTAGENS = (
    "ativas",
    "aberturas",
    "encerramentos",
    "ativas_mei",
    "ativas_simples",
)

# Divisão CNAE (2 primeiros dígitos) -> seção.
# Nomes idênticos aos do CEMPRE (tabela 9510 do SIDRA), para permitir o cruzamento.
FAIXAS_DIVISAO_SECAO = (
    (1, 3, "A Agricultura, pecuária, produção florestal, pesca e aquicultura"),
    (5, 9, "B Indústrias extrativas"),
    (10, 33, "C Indústrias de transformação"),
    (35, 35, "D Eletricidade e gás"),
    (36, 39, "E Água, esgoto, atividades de gestão de resíduos e descontaminação"),
    (41, 43, "F Construção"),
    (45, 47, "G Comércio; reparação de veículos automotores e motocicletas"),
    (49, 53, "H Transporte, armazenagem e correio"),
    (55, 56, "I Alojamento e alimentação"),
    (58, 63, "J Informação e comunicação"),
    (64, 66, "K Atividades financeiras, de seguros e serviços relacionados"),
    (68, 68, "L Atividades imobiliárias"),
    (69, 75, "M Atividades profissionais, científicas e técnicas"),
    (77, 82, "N Atividades administrativas e serviços complementares"),
    (84, 84, "O Administração pública, defesa e seguridade social"),
    (85, 85, "P Educação"),
    (86, 88, "Q Saúde humana e serviços sociais"),
    (90, 93, "R Artes, cultura, esporte e recreação"),
    (94, 96, "S Outras atividades de serviços"),
    (97, 97, "T Serviços domésticos"),
    (99, 99, "U Organismos internacionais e outras instituições extraterritoriais"),
)

MAPA_DIVISAO_SECAO = {
    f"{divisao:02d}": secao
    for inicio, fim, secao in FAIXAS_DIVISAO_SECAO
    for divisao in range(inicio, fim + 1)
}
# f"{divisao:02d}" gera "01", "02"... no mesmo formato de texto do CSV.


class RegistroRfb(TypedDict):
    """Estrutura de um registro agregado da RFB (competência + setor)."""

    competencia: str
    setor: str
    ativas: int
    aberturas: int
    encerramentos: int
    ativas_mei: int
    ativas_simples: int

def transformar_rfb(
        competencia: str,
        estabelecimentos: pd.DataFrame,
        empresas: pd.DataFrame,
        simples: pd.DataFrame,
) -> list[RegistroRfb]:
    """
    Junta as três bases pelo cnpj_basico e conta, por setor:
    ativas, aberturas, encerramentos, ativas MEI e ativas Simples (sem MEI).
    Adiciona uma linha "Total" com a soma de todos os setores.
    """

    if estabelecimentos.empty:
        return []

    df = (
        estabelecimentos
        .merge(empresas, on="cnpj_basico", how="left")
        .merge(simples, on="cnpj_basico", how="left")
    )
    # how="left": mantém todo estabelecimento, mesmo sem par em Empresas ou Simples.
    # O collector já removeu cnpj_basico duplicado, então a junção não multiplica linhas.

    divisao = df["cnae_fiscal_principal"].fillna("").str.strip().str[:2]
    df["setor"] = divisao.map(MAPA_DIVISAO_SECAO).fillna(SETOR_NAO_CLASSIFICADO)

    nao_classificados = int((df["setor"] == SETOR_NAO_CLASSIFICADO).sum())
    if nao_classificados:
        logger.warning(
            "%s estabelecimentos com CNAE fora do mapa (setor '%s')",
            nao_classificados, SETOR_NAO_CLASSIFICADO,
        )

    mes = competencia.replace("-", "")
    # Datas da RFB vêm como AAAAMMDD; a competência vem como AAAA-MM.
    # Sem remover o traço, startswith nunca encontraria o mês.

    situacao = df["situacao_cadastral"].fillna("")
    data_inicio = df["data_inicio_atividade"].fillna("")
    data_situacao = df["data_situacao_cadastral"].fillna("")

    df["ativas"] = situacao == SITUACAO_ATIVA
    df["aberturas"] = data_inicio.str.startswith(mes)
    df["encerramentos"] = (situacao == SITUACAO_BAIXADA) & data_situacao.str.startswith(mes)
    df["ativas_mei"] = df["ativas"] & (df["opcao_mei"] == "S")
    df["ativas_simples"] = df["ativas"] & (df["opcao_simples"] == "S") & ~df["ativas_mei"]
    # Todo MEI também é optante do Simples; ~ativas_mei evita contar a mesma empresa duas vezes.

    por_setor = df.groupby("setor")[list(CONTAGENS)].sum()
    # Soma de colunas booleanas = quantidade de True.

    por_setor.loc[SETOR_TOTAL] = por_setor.sum()
    # Total calculado a partir dos setores: sempre consistente com eles.

    registros: list[RegistroRfb] = []
    for setor, linha in por_setor.iterrows():
        registros.append(
            {
                "competencia": competencia,
                "setor": setor,
                **{campo: int(linha[campo]) for campo in CONTAGENS},
            }
        )
    # int() converte numpy.int64 para int nativo antes do Pydantic e do banco.

    logger.info(
        "RFB %s: %s registros agregados (%s setores + Total)",
        competencia, len(registros), len(registros) - 1,
                                     )
    return registros

def validar_dados(
        registros: list[RegistroRfb],
) -> tuple[list[RegistroRfb], list[dict]]:
    """Valida registros antes da persistência. Devolve (validos, invalidos)."""

    registros_validos = []
    registros_invalidos = []

    for indice, registro in enumerate(registros):
        erros = []

        if not re.fullmatch(r"\d{4}-\d{2}", str(registro.get("competencia", ""))):
            erros.append("Competência deve estar no formato AAAA-MM.")

        if not registro.get("setor"):
            erros.append("Setor não informado.")

        for campo in CONTAGENS:
            valor = registro.get(campo)
            if not isinstance(valor, int) or isinstance(valor, bool):
                erros.append(f"{campo} deve ser inteiro.")
            elif valor < 0:
                erros.append(f"{campo} não pode ser negativo.")

        if not erros and registro["ativas_mei"] + registro["ativas_simples"] > registro["ativas"]:
            erros.append("ativas_mei + ativas_simples não pode ser maior que ativas.")
        # Só checa a soma se os campos já passaram nas validações de tipo.

        if erros:
            registro_invalido = dict(registro)
            registro_invalido["_erros"] = erros
            registro_invalido["_linha"] = indice
            registros_invalidos.append(registro_invalido)
        else:
            registros_validos.append(registro)

    return registros_validos, registros_invalidos