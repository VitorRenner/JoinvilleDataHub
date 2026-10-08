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


class RegistroCempre(TypedDict):
    """
    Estrutura intermediária de um registro CEMPRE.
    """

    ano: str
    setor: str
    unidades_locais: int
    pessoal_ocupado: int
    salario_medio: float


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

    # O SIDRA usa "-", "X" e "..." quando o valor é zero, sigiloso ou não
    # existe. Tudo isso vira NaN aqui e depois 0.
    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce",
    )

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

    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            df[coluna] = 0

    for coluna in (
            "unidades_locais",
            "pessoal_ocupado",
    ):
        df[coluna] = (
            pd.to_numeric(
                df[coluna],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

    df["salario_medio"] = (
        pd.to_numeric(
            df["salario_medio"],
            errors="coerce",
        )
        .fillna(0)
        .astype(float)
        .round(2)
    )

    df["ano"] = df["ano"].astype(str).str[:4]

    df["setor"] = df["setor"].astype(str).str[:100]

    return df[list(COLUNAS_OBRIGATORIAS)].to_dict(orient="records")


def validar_dados(
        registros: list[RegistroCempre],
) -> tuple[
    list[RegistroCempre],
    list[dict],
]:
    """
    Valida registros antes da persistência.
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

        for campo in (
                "unidades_locais",
                "pessoal_ocupado",
        ):
            valor = registro.get(campo)

            if not isinstance(valor, int):
                erros.append(f"{campo} deve ser numérico.")

            elif valor < 0:
                erros.append(f"{campo} não pode ser negativo.")

        salario_medio = registro.get("salario_medio")

        if not isinstance(salario_medio, (int, float)):
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