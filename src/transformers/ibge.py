import re
from typing import Any, TypedDict

RE_ANO = re.compile(r"^\d{4}$")

VALORES_SEM_DADO = {"", "-", "--", "...", "..", "X"}


class RegistroIbge(TypedDict):
    ano: str
    indicador: str
    descricao: str
    valor: float
    unidade: str


def transformar_ibge(
    linhas: list[dict[str, Any]],
) -> list[RegistroIbge]:
    registros: list[RegistroIbge] = []

    for linha in linhas:
        valor_bruto = str(linha.get("V", "")).strip()

        if valor_bruto in VALORES_SEM_DADO:
            continue

        try:
            valor = float(valor_bruto)
        except ValueError:
            continue

        registros.append(
            RegistroIbge(
                ano=str(linha.get("D3C", "")).strip(),
                indicador=str(linha.get("indicador", "")).strip(),
                descricao=str(linha.get("D2N", "")).strip()[:200],
                valor=valor,
                unidade=str(linha.get("MN", "")).strip()[:30],
            )
        )

    return registros


def validar_ibge(
    registros: list[RegistroIbge],
) -> tuple[list[RegistroIbge], list[dict[str, Any]]]:
    validos: list[RegistroIbge] = []
    invalidos: list[dict[str, Any]] = []

    for indice, registro in enumerate(registros):
        erros = []

        if not RE_ANO.fullmatch(registro["ano"]):
            erros.append("Ano deve estar no formato AAAA.")

        if not registro["indicador"]:
            erros.append("Indicador não informado.")

        if not registro["unidade"]:
            erros.append("Unidade não informada.")

        if registro["valor"] < 0:
            erros.append("Valor não pode ser negativo.")

        if erros:
            invalidos.append({**registro, "_erros": erros, "_linha": indice})
        else:
            validos.append(registro)

    return validos, invalidos
