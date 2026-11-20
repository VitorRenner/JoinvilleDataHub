"""
Roda o conjunto de avaliação do agente contra o modelo real.

Custa chamadas ao LLM: rodar manualmente, nunca no CI.

Retomável: cada caso respondido fica salvo em docs/agent_eval.json. Uma
nova rodada pula os casos já salvos e tenta só os pendentes (útil com a
cota gratuita do Gemini, que é de poucas chamadas por dia). Falha de API
(cota, rede) não conta como erro do agente: o caso fica pendente.

Uso:
    uv run python -m src.scripts.avaliar_agente              # pendentes
    uv run python -m src.scripts.avaliar_agente --refazer    # todos de novo
"""

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

from google import genai

from src.agent.agente import Agente, AgenteIndisponivel
from src.agent.avaliacao import CASOS, corrigir
from src.core.settings import settings
from src.database.conexao import SessionLocal

RESULTADOS = Path("docs/agent_eval.json")
RELATORIO = Path("docs/AGENT_EVAL.md")


def _carregar() -> dict:
    if RESULTADOS.exists():
        return json.loads(RESULTADOS.read_text(encoding="utf-8"))
    return {}


def _salvar(resultados: dict) -> None:
    RESULTADOS.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _escrever_relatorio(resultados: dict) -> str:
    respondidos = [resultados[c.pergunta] for c in CASOS if c.pergunta in resultados]
    acertos = sum(r["ok"] for r in respondidos)
    latencias = [r["latencia_ms"] for r in respondidos if r.get("latencia_ms")]
    modelos = sorted({r["modelo"] for r in respondidos})
    pendentes = len(CASOS) - len(respondidos)

    if respondidos:
        resumo = (
            f"Correct: {acertos}/{len(respondidos)} answered "
            f"({acertos / len(respondidos):.0%})"
        )
    else:
        resumo = "No answered cases yet"
    if latencias:
        resumo += f" · median latency: {statistics.median(latencias) / 1000:.1f} s"
    if pendentes:
        resumo += f" · {pendentes} pending (API quota)"

    linhas = [
        "# Agent evaluation",
        "",
        "Each question runs against the real database and the real model. The",
        "expected answer is computed from the database at run time",
        "([`src/agent/avaliacao.py`](../src/agent/avaliacao.py)), so the answer",
        "key always matches the data.",
        "",
        "- **Numeric questions** pass if the expected number appears in the answer.",
        "- **Decline questions** pass if the agent says it doesn't have the data,",
        "  instead of making something up.",
        "",
        f"Model: {', '.join(f'`{m}`' for m in modelos) or '-'} · "
        f"last run: {date.today().isoformat()}",
        "",
        f"**{resumo}**",
        "",
        "| | Question | Expected | Tools used |",
        "| --- | --- | --- | --- |",
    ]
    for caso in CASOS:
        r = resultados.get(caso.pergunta)
        if r is None:
            linhas.append(f"| ⏳ | {caso.pergunta} | pending | - |")
            continue
        marca = "✅" if r["ok"] else "❌"
        esperado = "should decline" if caso.tipo == "recusa" else r["esperado"]
        linhas.append(
            f"| {marca} | {caso.pergunta} | {esperado} | {r['ferramentas']} |",
        )

    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o agente /perguntar.")
    parser.add_argument(
        "--refazer",
        action="store_true",
        help="Ignora os resultados salvos e roda todos os casos.",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=25.0,
        help="Segundos entre perguntas (cota gratuita: poucas por minuto).",
    )
    args = parser.parse_args()

    if not settings.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY não configurada no .env.")

    agente = Agente(
        cliente=genai.Client(api_key=settings.GEMINI_API_KEY),
        modelo=settings.GEMINI_MODEL,
        max_passos=settings.AGENTE_MAX_PASSOS,
    )

    resultados = {} if args.refazer else _carregar()
    pendentes = [c for c in CASOS if c.pergunta not in resultados]
    print(f"{len(pendentes)} caso(s) pendente(s) de {len(CASOS)}.\n")

    db = SessionLocal()
    try:
        for indice, caso in enumerate(pendentes, start=1):
            esperado = caso.esperado(db)
            try:
                resultado = agente.perguntar(db, caso.pergunta)
            except AgenteIndisponivel:
                print(f"⏳ {caso.pergunta}")
                print("     falha de API (cota?); fica pendente.\n")
                # Cota diária esgotada costuma afetar todos os próximos
                break

            ok = corrigir(caso, esperado, resultado.resposta)
            resultados[caso.pergunta] = {
                "ok": ok,
                "esperado": esperado,
                "resposta": resultado.resposta,
                "ferramentas": ", ".join(c.ferramenta for c in resultado.consultas)
                or "-",
                "modelo": resultado.modelo,
                "latencia_ms": resultado.latencia_ms,
                "tokens": resultado.tokens_entrada + resultado.tokens_saida,
            }
            _salvar(resultados)

            print(f"{'✅' if ok else '❌'} {caso.pergunta}")
            print(f"     esperado: {esperado}")
            print(f"     resposta: {resultado.resposta}\n")

            if indice < len(pendentes):
                time.sleep(args.pausa)

        # Recorrige as respostas salvas com o gabarito de agora: se os dados
        # mudaram, o relatório acompanha
        for caso in CASOS:
            salvo = resultados.get(caso.pergunta)
            if salvo is None:
                continue
            esperado = caso.esperado(db)
            salvo["esperado"] = esperado
            salvo["ok"] = corrigir(caso, esperado, salvo["resposta"])
        _salvar(resultados)
    finally:
        db.close()

    print(_escrever_relatorio(resultados))
    print(f"Relatório: {RELATORIO} · resultados: {RESULTADOS}")


if __name__ == "__main__":
    main()
