"""
Ferramentas de leitura que o LLM pode chamar.

Regras de segurança:
- só SELECT, feito pelo nosso código (o modelo nunca escreve SQL);
- argumentos validados antes de consultar (formato de período e seção);
- no máximo MAX_LINHAS por chamada;
- totais já calculados aqui, para o modelo não precisar fazer contas.
"""

import logging
import re
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.agent.secoes import SECOES_CNAE, secao_do_setor
from src.database.models import CagedMovimentacao, CempreEmprego, RfbEmpresa

logger = logging.getLogger(__name__)

MAX_LINHAS = 60

SETOR_TOTAL = "Total"

_RE_COMPETENCIA_CAGED = re.compile(r"^\d{4}-\d{2}$")
_RE_COMPETENCIA_RFB = re.compile(r"^\d{4}-\d{2}$")
_RE_ANO = re.compile(r"^\d{4}$")


class ArgumentoInvalido(ValueError):
    """Argumento de ferramenta fora do formato esperado."""


def _validar(valor: str | None, padrao: re.Pattern[str], nome: str) -> str | None:
    if valor is None or valor == "":
        return None
    valor = str(valor).strip()
    if not padrao.match(valor):
        raise ArgumentoInvalido(f"{nome} em formato inválido: {valor!r}")
    return valor


def _validar_secao(secao: str | None) -> str | None:
    if secao is None or secao == "":
        return None
    letra = str(secao).strip().upper()
    if letra not in SECOES_CNAE:
        raise ArgumentoInvalido(f"Seção CNAE inválida: {secao!r}. Use A a U.")
    return letra


# --------------------------------- tools ----------------------------------


def listar_periodos(db: Session) -> dict[str, Any]:
    """Períodos disponíveis em cada fonte e as seções CNAE."""

    caged = db.scalars(
        select(CagedMovimentacao.competencia)
        .distinct()
        .order_by(CagedMovimentacao.competencia),
    ).all()
    cempre = db.scalars(
        select(CempreEmprego.ano).distinct().order_by(CempreEmprego.ano),
    ).all()
    rfb = db.scalars(
        select(RfbEmpresa.competencia).distinct().order_by(RfbEmpresa.competencia),
    ).all()

    return {
        "caged_competencias_YYYY-MM": list(caged),
        "cempre_anos": list(cempre),
        "rfb_competencias_YYYY-MM": list(rfb),
        "secoes_cnae": SECOES_CNAE,
    }


def consultar_caged(
    db: Session,
    competencia: str | None = None,
    secao: str | None = None,
) -> dict[str, Any]:
    """Admissões, demissões e saldo de empregos formais (Novo CAGED)."""

    competencia = _validar(competencia, _RE_COMPETENCIA_CAGED, "competencia")
    secao = _validar_secao(secao)

    # Sem período e sem seção: usa só o mês mais recente, para a resposta
    # nunca sair de um recorte velho ou misturar meses num mesmo total
    if not competencia and not secao:
        competencia = db.scalar(select(func.max(CagedMovimentacao.competencia)))

    # Mais recente primeiro: se cortar no limite, corta o histórico antigo
    consulta = select(CagedMovimentacao).order_by(
        CagedMovimentacao.competencia.desc(),
        CagedMovimentacao.setor,
    )
    if competencia:
        consulta = consulta.where(CagedMovimentacao.competencia == competencia)
    if secao:
        consulta = consulta.where(CagedMovimentacao.setor == secao)

    # Busca uma linha a mais só para saber se houve corte
    registros = db.scalars(consulta.limit(MAX_LINHAS + 1)).all()
    truncado = len(registros) > MAX_LINHAS
    registros = registros[:MAX_LINHAS]

    linhas = [
        {
            "competencia": r.competencia,
            "secao": r.setor,
            "setor": SECOES_CNAE.get(r.setor, r.setor),
            "admissoes": r.admissoes,
            "demissoes": r.demissoes,
            "saldo": r.saldo,
        }
        for r in registros
    ]

    # Totais separados por mês: somar meses diferentes não tem significado
    totais: dict[str, dict[str, int]] = {}
    for linha in linhas:
        total = totais.setdefault(
            linha["competencia"],
            {"admissoes": 0, "demissoes": 0, "saldo": 0},
        )
        for campo in total:
            total[campo] += linha[campo]

    return {
        "fonte": "Novo CAGED (Ministério do Trabalho), Joinville/SC",
        "competencia_consultada": competencia or "todas (série da seção)",
        "linhas": linhas,
        "totais_por_competencia": totais,
        "truncado": truncado,
    }


def consultar_cempre(
    db: Session,
    ano: str | None = None,
    secao: str | None = None,
) -> dict[str, Any]:
    """Unidades locais, pessoal ocupado e salário médio (CEMPRE/IBGE)."""

    ano = _validar(ano, _RE_ANO, "ano")
    secao = _validar_secao(secao)

    consulta = select(CempreEmprego).order_by(CempreEmprego.ano, CempreEmprego.setor)
    if ano:
        consulta = consulta.where(CempreEmprego.ano == ano)

    registros = db.scalars(consulta).all()

    linhas = []
    total_oficial = {}
    for r in registros:
        letra = secao_do_setor(r.setor)
        if r.setor == SETOR_TOTAL:
            total_oficial[r.ano] = {
                "unidades_locais": r.unidades_locais,
                "pessoal_ocupado": r.pessoal_ocupado,
                "salario_medio_reais": r.salario_medio,
            }
            continue
        if secao and letra != secao:
            continue
        linhas.append(
            {
                "ano": r.ano,
                "secao": letra,
                "setor": SECOES_CNAE.get(letra or "", r.setor),
                "unidades_locais": r.unidades_locais,
                "pessoal_ocupado": r.pessoal_ocupado,
                "salario_medio_reais": r.salario_medio,
            },
        )

    return {
        "fonte": "CEMPRE (IBGE), Joinville/SC",
        "linhas": linhas[:MAX_LINHAS],
        # Total oficial do IBGE por ano (use este para "Joinville inteira")
        "total_oficial_por_ano": total_oficial if not secao else {},
        "truncado": len(linhas) > MAX_LINHAS,
        "observacao": (
            "salario_medio_reais é o salário médio mensal em reais. "
            "Campos nulos significam dado não divulgado pelo IBGE."
        ),
    }


def consultar_rfb(
    db: Session,
    competencia: str | None = None,
    secao: str | None = None,
) -> dict[str, Any]:
    """Empresas ativas, aberturas, encerramentos, MEI e Simples (Receita)."""

    competencia = _validar(competencia, _RE_COMPETENCIA_RFB, "competencia")
    secao = _validar_secao(secao)

    consulta = select(RfbEmpresa).order_by(RfbEmpresa.competencia, RfbEmpresa.setor)
    if competencia:
        consulta = consulta.where(RfbEmpresa.competencia == competencia)

    registros = db.scalars(consulta).all()

    campos = ("ativas", "aberturas", "encerramentos", "ativas_mei", "ativas_simples")
    linhas = []
    total_oficial = {}
    for r in registros:
        valores = {campo: getattr(r, campo) for campo in campos}
        if r.setor == SETOR_TOTAL:
            total_oficial[r.competencia] = valores
            continue
        letra = secao_do_setor(r.setor)
        if secao and letra != secao:
            continue
        linhas.append(
            {
                "competencia": r.competencia,
                "secao": letra,
                "setor": SECOES_CNAE.get(letra or "", r.setor),
                **valores,
            },
        )

    return {
        "fonte": "Cadastro CNPJ (Receita Federal), agregado por setor, Joinville/SC",
        "linhas": linhas[:MAX_LINHAS],
        "total_oficial_por_competencia": total_oficial if not secao else {},
        "truncado": len(linhas) > MAX_LINHAS,
    }


# ------------------------- declarações para o LLM -------------------------

_PROP_SECAO = {
    "type": "string",
    "description": (
        "Letra da seção CNAE (A a U), ex.: C para indústria. Omitir = todas."
    ),
}

DECLARACOES: list[dict[str, Any]] = [
    {
        "name": "listar_periodos",
        "description": (
            "Lista os períodos disponíveis em cada fonte e as seções CNAE. "
            "Normalmente essa lista já vem no contexto da pergunta; chame só "
            "se o contexto não trouxer os períodos."
        ),
        "parameters_json_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_caged",
        "description": (
            "Empregos formais em Joinville por mês (Novo CAGED): admissões, "
            "demissões e saldo, por seção CNAE. Já devolve os totais de cada "
            "mês. Sem competência e sem seção, usa o mês mais recente; com "
            "seção e sem competência, devolve a série da seção."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "competencia": {
                    "type": "string",
                    "description": "Mês no formato YYYY-MM, ex.: 2026-06.",
                },
                "secao": _PROP_SECAO,
            },
        },
    },
    {
        "name": "consultar_cempre",
        "description": (
            "Estrutura empresarial anual de Joinville (CEMPRE/IBGE): unidades "
            "locais, pessoal ocupado e salário médio mensal, por seção CNAE. "
            "Inclui o total oficial do município por ano."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "ano": {"type": "string", "description": "Ano, ex.: 2024."},
                "secao": _PROP_SECAO,
            },
        },
    },
    {
        "name": "consultar_rfb",
        "description": (
            "Empresas de Joinville no cadastro CNPJ da Receita Federal, por "
            "seção CNAE: ativas, aberturas e encerramentos no mês, ativas MEI "
            "e ativas no Simples. Inclui o total oficial do município."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "competencia": {
                    "type": "string",
                    "description": "Mês no formato YYYY-MM, ex.: 2026-10.",
                },
                "secao": _PROP_SECAO,
            },
        },
    },
]

FERRAMENTAS: dict[str, Callable[..., dict[str, Any]]] = {
    "listar_periodos": listar_periodos,
    "consultar_caged": consultar_caged,
    "consultar_cempre": consultar_cempre,
    "consultar_rfb": consultar_rfb,
}

_ARGUMENTOS_PERMITIDOS = {
    "listar_periodos": set(),
    "consultar_caged": {"competencia", "secao"},
    "consultar_cempre": {"ano", "secao"},
    "consultar_rfb": {"competencia", "secao"},
}


def executar(db: Session, nome: str, argumentos: dict[str, Any]) -> dict[str, Any]:
    """
    Executa a ferramenta pedida pelo LLM.

    Nome desconhecido, argumento extra ou formato inválido viram uma
    resposta de erro para o modelo corrigir, nunca uma exceção na API.
    """

    if nome not in FERRAMENTAS:
        return {"erro": f"Ferramenta desconhecida: {nome}"}

    extras = set(argumentos) - _ARGUMENTOS_PERMITIDOS[nome]
    if extras:
        return {"erro": f"Argumentos não permitidos: {sorted(extras)}"}

    try:
        return FERRAMENTAS[nome](db, **argumentos)
    except ArgumentoInvalido as exc:
        return {"erro": str(exc)}
    except SQLAlchemyError:
        # Detalhe só no log; o modelo recebe um erro genérico
        logger.exception("Falha de banco na ferramenta %s.", nome)
        db.rollback()
        return {"erro": "Falha temporária ao consultar os dados."}
