import math
from typing import TypedDict

import pandas as pd

COLUNAS_OBRIGATORIAS = (
    "ano",
    "setor",
    "unidades_locais",
    "pessoal_ocupado",
    "salario_medio",
)


# O SIDRA devolve as colunas com nomes genéricos (D1N, D2C, V...). Aqui elas
# ganham o nome que o resto do projeto usa.
MAPEAMENTO_COLUNAS = {
    "D3N": "ano",
    "D4N": "setor",
    "D2C": "codigo_variavel",
    "V": "valor",
}


# Cada variável do SIDRA vira uma coluna depois do pivot.
MAPEAMENTO_VARIAVEIS = {
    "706": "unidades_locais",
    "707": "pessoal_ocupado",
    "10143": "salario_medio",
}


# Símbolos especiais do IBGE no lugar de números:
#   "-"   -> zero absoluto (não resultante de arredondamento) -> vira 0
#   "X"   -> valor omitido para não identificar o informante (sigiloso)
#   "..." -> valor não disponível
#   ".."  -> não se aplica
# Só o "-" é um zero de verdade. Os outros significam "não sabemos" e
# viram None (NULL no banco), para não se passarem por zero.
SIMBOLO_ZERO_ABSOLUTO = "-"

COLUNAS_INTEIRAS = (
    "unidades_locais",
    "pessoal_ocupado",
)


class RegistroCempre(TypedDict):
    """
    Estrutura intermediária de um registro CEMPRE.

    Campos numéricos podem ser None quando o IBGE não divulga o valor
    (sigiloso ou não disponível).
    """

    ano: str
    setor: str
    unidades_locais: int | None
    pessoal_ocupado: int | None
    salario_medio: float | None


def _converter_valor_sidra(
        valor: object,
) -> float:
    """
    Converte um valor bruto do SIDRA em número.

    "-" vira 0.0. Qualquer outro texto não numérico ("X", "...", "..")
    vira NaN, que mais adiante se torna None.
    """

    texto = str(valor).strip()

    if texto == SIMBOLO_ZERO_ABSOLUTO:
        return 0.0

    return pd.to_numeric(
        texto,
        errors="coerce",
    )


def _para_inteiro_ou_none(
        valor: float,
) -> int | None:
    """
    Converte para int nativo do Python, ou None quando for NaN.
    """

    if valor is None or math.isnan(valor):
        return None

    return int(round(valor))


def _para_float_ou_none(
        valor: float,
) -> float | None:
    """
    Converte para float nativo do Python (2 casas), ou None quando for NaN.
    """

    if valor is None or math.isnan(valor):
        return None

    return round(float(valor), 2)


def transformar_cempre(
        df: pd.DataFrame,
) -> list[RegistroCempre]:
    """
    Padroniza os dados brutos do CEMPRE para persistência.

    O SIDRA entrega o dado "esticado": uma linha por variável, para cada
    ano + setor. Aqui ele é pivotado pra ficar "achatado", igual ao CAGED,
    com uma linha por ano + setor e uma coluna por variável.
    """

    if df.empty:
        return []

    df = df.rename(
        columns={
            antiga: nova
            for antiga, nova in MAPEAMENTO_COLUNAS.items()
            if antiga in df.columns
        }
    )

    for coluna in (
            "ano",
            "setor",
            "codigo_variavel",
            "valor",
    ):
        if coluna not in df.columns:
            df[coluna] = ""

    # Converte valor a valor para respeitar o significado de cada símbolo
    # do IBGE (ver SIMBOLO_ZERO_ABSOLUTO).
    df["valor"] = df["valor"].map(_converter_valor_sidra).astype(float)

    df["codigo_variavel"] = df["codigo_variavel"].astype(str)

    df = df[df["codigo_variavel"].isin(MAPEAMENTO_VARIAVEIS.keys())]

    if df.empty:
        return []

    df = (
        df.pivot_table(
            index=["ano", "setor"],
            columns="codigo_variavel",
            values="valor",
            aggfunc="first",
            dropna=False,
        )
        .rename(columns=MAPEAMENTO_VARIAVEIS)
        .reset_index()
    )

    df.columns.name = None

    # Se uma variável inteira não veio na resposta, a coluna é criada vazia
    # (NaN -> None), e não com zeros.
    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            df[coluna] = float("nan")

    df["ano"] = df["ano"].astype(str).str[:4]

    df["setor"] = df["setor"].astype(str).str[:100]

    # Monta os registros já com tipos nativos do Python (int, float, None).
    # Isso evita tipos do numpy (numpy.int64, NaN) chegarem ao Pydantic e
    # ao banco.
    registros: list[RegistroCempre] = []

    for linha in df[list(COLUNAS_OBRIGATORIAS)].itertuples(index=False):
        registros.append(
            {
                "ano": linha.ano,
                "setor": linha.setor,
                "unidades_locais": _para_inteiro_ou_none(linha.unidades_locais),
                "pessoal_ocupado": _para_inteiro_ou_none(linha.pessoal_ocupado),
                "salario_medio": _para_float_ou_none(linha.salario_medio),
            }
        )

    return registros


def validar_dados(
        registros: list[RegistroCempre],
) -> tuple[
    list[RegistroCempre],
    list[dict],
]:
    """
    Valida registros antes da persistência.

    None é aceito nos campos numéricos: significa que o IBGE não divulgou
    o valor, o que não é um erro do dado.
    """

    registros_validos = []
    registros_invalidos = []

    for indice, registro in enumerate(registros):
        erros = []

        ano = str(registro["ano"])

        if len(ano) != 4 or not ano.isdigit():
            erros.append("Ano deve estar no formato YYYY.")

        if not registro.get("setor"):
            erros.append("Setor não informado.")

        for campo in COLUNAS_INTEIRAS:
            valor = registro.get(campo)

            if valor is None:
                continue

            if not isinstance(valor, int) or isinstance(valor, bool):
                erros.append(f"{campo} deve ser numérico.")

            elif valor < 0:
                erros.append(f"{campo} não pode ser negativo.")

        salario_medio = registro.get("salario_medio")

        if salario_medio is not None:
            if not isinstance(salario_medio, (int, float)) or isinstance(
                    salario_medio, bool
            ):
                erros.append("salario_medio deve ser numérico.")

            elif salario_medio < 0:
                erros.append("salario_medio não pode ser negativo.")

        if erros:
            registro_invalido = registro.copy()

            registro_invalido["_erros"] = erros
            registro_invalido["_linha"] = indice

            registros_invalidos.append(registro_invalido)

        else:
            registros_validos.append(registro)

    return (
        registros_validos,
        registros_invalidos,
    )