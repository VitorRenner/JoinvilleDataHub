"""
Testes do agente /perguntar com um modelo falso: nenhum teste chama o
Gemini de verdade (sem custo, sem rede, sem chave).
"""

from types import SimpleNamespace

import pytest
from google.genai import types
from sqlalchemy.exc import SQLAlchemyError

from src.agent import ferramentas
from src.agent.agente import Agente, AgenteIndisponivel
from src.agent.avaliacao import Caso, corrigir, numeros_do_texto
from src.agent.limites import LimiteDeUso
from src.api.app import app
from src.api.routers import agente as rota_agente
from src.core.settings import settings
from src.database.models import CagedMovimentacao, CempreEmprego, RfbEmpresa
from tests.conftest import TestingSessionLocal

# ------------------------------- utilitários ------------------------------


def _resposta_chamada(nome: str, args: dict, tokens: tuple[int, int] = (10, 5)):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_function_call(name=nome, args=args)],
                ),
            ),
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=tokens[0],
            candidates_token_count=tokens[1],
        ),
    )


def _resposta_texto(texto: str, tokens: tuple[int, int] = (20, 8)):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=texto)],
                ),
            ),
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=tokens[0],
            candidates_token_count=tokens[1],
        ),
    )


class ModeloFalso:
    """Imita client.models.generate_content com respostas roteirizadas."""

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.chamadas.append(list(contents))
        if isinstance(self._respostas[0], Exception):
            raise self._respostas.pop(0)
        if len(self._respostas) == 1:
            return self._respostas[0]
        return self._respostas.pop(0)


@pytest.fixture
def db():
    sessao = TestingSessionLocal()
    sessao.add_all(
        [
            CagedMovimentacao(
                competencia="2026-06",
                setor="C",
                admissoes=900,
                demissoes=700,
                saldo=200,
            ),
            CagedMovimentacao(
                competencia="2026-06",
                setor="G",
                admissoes=500,
                demissoes=550,
                saldo=-50,
            ),
            CagedMovimentacao(
                competencia="2026-05",
                setor="C",
                admissoes=800,
                demissoes=800,
                saldo=0,
            ),
            CempreEmprego(
                ano="2024",
                setor="C Indústrias de transformação",
                unidades_locais=3000,
                pessoal_ocupado=90000,
                salario_medio=4494.44,
            ),
            CempreEmprego(
                ano="2024",
                setor="Total",
                unidades_locais=40000,
                pessoal_ocupado=250000,
                salario_medio=3900.0,
            ),
            RfbEmpresa(
                competencia="2026-10",
                setor="C Indústrias de transformação",
                ativas=5000,
                aberturas=40,
                encerramentos=20,
                ativas_mei=1200,
                ativas_simples=3000,
            ),
            RfbEmpresa(
                competencia="2026-10",
                setor="Total",
                ativas=80000,
                aberturas=900,
                encerramentos=400,
                ativas_mei=35000,
                ativas_simples=60000,
            ),
        ],
    )
    sessao.commit()
    yield sessao
    sessao.close()


# ------------------------------- ferramentas ------------------------------


def test_caged_filtra_e_soma_totais(db):
    saida = ferramentas.consultar_caged(db, competencia="2026-06")

    assert len(saida["linhas"]) == 2
    assert saida["totais_por_competencia"] == {
        "2026-06": {"admissoes": 1400, "demissoes": 1250, "saldo": 150},
    }
    assert saida["linhas"][0]["setor"] == "Indústrias de transformação"


def test_caged_sem_argumentos_usa_mes_mais_recente(db):
    saida = ferramentas.consultar_caged(db)

    assert saida["competencia_consultada"] == "2026-06"
    assert {linha["competencia"] for linha in saida["linhas"]} == {"2026-06"}


def test_caged_por_secao_traz_serie_com_totais_por_mes(db):
    saida = ferramentas.consultar_caged(db, secao="c")

    # Mais recente primeiro, e nunca um total misturando meses
    assert [linha["competencia"] for linha in saida["linhas"]] == ["2026-06", "2026-05"]
    assert set(saida["totais_por_competencia"]) == {"2026-05", "2026-06"}


def test_caged_marca_truncado_so_quando_passa_do_limite(db, monkeypatch):
    monkeypatch.setattr(ferramentas, "MAX_LINHAS", 2)
    assert ferramentas.consultar_caged(db, competencia="2026-06")["truncado"] is False
    assert ferramentas.consultar_caged(db, secao="C")["truncado"] is False

    monkeypatch.setattr(ferramentas, "MAX_LINHAS", 1)
    assert ferramentas.consultar_caged(db, competencia="2026-06")["truncado"] is True


def test_erro_de_banco_vira_erro_generico(db, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def quebra(*_args, **_kwargs):
        raise OperationalError("SELECT", {}, Exception("senha=segredo"))

    monkeypatch.setitem(ferramentas.FERRAMENTAS, "consultar_caged", quebra)
    saida = ferramentas.executar(db, "consultar_caged", {})

    assert saida == {"erro": "Falha temporária ao consultar os dados."}


def test_cempre_separa_total_oficial(db):
    saida = ferramentas.consultar_cempre(db, ano="2024")

    assert [linha["secao"] for linha in saida["linhas"]] == ["C"]
    assert saida["total_oficial_por_ano"]["2024"]["pessoal_ocupado"] == 250000


def test_rfb_filtra_por_secao_sem_total(db):
    saida = ferramentas.consultar_rfb(db, competencia="2026-10", secao="C")

    assert saida["linhas"][0]["aberturas"] == 40
    assert saida["total_oficial_por_competencia"] == {}


def test_listar_periodos(db):
    saida = ferramentas.listar_periodos(db)
    assert saida["caged_competencias_YYYY-MM"] == ["2026-05", "2026-06"]
    assert saida["rfb_competencias_YYYY-MM"] == ["2026-10"]
    assert saida["secoes_cnae"]["C"] == "Indústrias de transformação"


@pytest.mark.parametrize(
    ("nome", "argumentos", "trecho"),
    [
        ("consultar_caged", {"competencia": "202606"}, "formato inválido"),
        ("consultar_caged", {"secao": "Z"}, "Seção CNAE inválida"),
        ("consultar_rfb", {"competencia": "202610"}, "formato inválido"),
        ("consultar_caged", {"sql": "DROP TABLE x"}, "não permitidos"),
        ("apagar_tudo", {}, "desconhecida"),
    ],
)
def test_executar_devolve_erro_em_vez_de_quebrar(db, nome, argumentos, trecho):
    saida = ferramentas.executar(db, nome, argumentos)
    assert trecho in saida["erro"]


def test_nenhuma_ferramenta_escreve():
    # Só leitura: a lista de ferramentas é fechada e conhecida
    assert set(ferramentas.FERRAMENTAS) == {
        "listar_periodos",
        "consultar_caged",
        "consultar_cempre",
        "consultar_rfb",
    }


# ---------------------------------- agente --------------------------------


def test_agente_usa_ferramenta_e_responde(db):
    modelo = ModeloFalso(
        [
            _resposta_chamada("consultar_caged", {"competencia": "2026-06"}),
            _resposta_texto("Em junho de 2026 o saldo foi de 150 empregos (CAGED)."),
        ],
    )
    agente = Agente(cliente=modelo, modelo="falso")

    resultado = agente.perguntar(db, "Qual o saldo de empregos em junho de 2026?")

    assert "150" in resultado.resposta
    assert [c.ferramenta for c in resultado.consultas] == ["consultar_caged"]
    assert resultado.tokens_entrada == 30
    assert resultado.tokens_saida == 13
    assert resultado.passos == 2

    # O modelo recebeu de volta os dados reais da ferramenta
    ultima_chamada = modelo.chamadas[-1]
    resposta_ferramenta = ultima_chamada[-1].parts[0].function_response.response
    assert resposta_ferramenta["totais_por_competencia"]["2026-06"]["saldo"] == 150
    # Respostas de ferramenta voltam com role "user" (o Gemini recusa "tool")
    assert ultima_chamada[-1].role == "user"


def test_agente_manda_periodos_no_contexto(db):
    modelo = ModeloFalso([_resposta_texto("ok")])
    Agente(cliente=modelo, modelo="falso").perguntar(db, "Qual o saldo?")

    # Os períodos chegam na primeira mensagem, sem gastar uma ida ao modelo
    partes = modelo.chamadas[0][0].parts
    assert "2026-06" in partes[0].text
    assert "2026-10" in partes[0].text
    # A pergunta continua separada e por último
    assert partes[-1].text == "Qual o saldo?"


def test_agente_segue_sem_contexto_se_o_banco_falhar(db, monkeypatch):
    def quebra(_db):
        raise SQLAlchemyError("banco fora")

    monkeypatch.setitem(ferramentas.FERRAMENTAS, "listar_periodos", quebra)
    modelo = ModeloFalso([_resposta_texto("ok")])
    resultado = Agente(cliente=modelo, modelo="falso").perguntar(db, "oi")

    assert resultado.resposta == "ok"
    assert [p.text for p in modelo.chamadas[0][0].parts] == ["oi"]


def test_agente_limita_o_raciocinio_do_modelo():
    agente = Agente(cliente=None, modelo="falso", thinking_level="low")
    assert agente.config.thinking_config.thinking_level == types.ThinkingLevel.LOW

    sem_limite = Agente(cliente=None, modelo="falso")
    assert sem_limite.config.thinking_config is None


def test_agente_limita_consultas_por_passo(db):
    muitas = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(name="listar_periodos", args={})
                        for _ in range(6)
                    ],
                ),
            ),
        ],
    )
    modelo = ModeloFalso([muitas, _resposta_texto("ok")])
    resultado = Agente(cliente=modelo, modelo="falso").perguntar(db, "?")

    erros = [c.erro for c in resultado.consultas]
    assert erros[:4] == [None] * 4
    assert all(erro and "Limite" in erro for erro in erros[4:])
    # Toda chamada recebe resposta, inclusive as que não rodaram
    assert len(modelo.chamadas[-1][-1].parts) == 6


def test_agente_repassa_erro_da_ferramenta_ao_modelo(db):
    modelo = ModeloFalso(
        [
            _resposta_chamada("consultar_caged", {"competencia": "junho"}),
            _resposta_texto("Não há esse dado."),
        ],
    )
    resultado = Agente(cliente=modelo, modelo="falso").perguntar(db, "junho?")

    assert resultado.consultas[0].erro is not None
    assert resultado.resposta == "Não há esse dado."


def test_agente_para_no_limite_de_passos(db):
    modelo = ModeloFalso([_resposta_chamada("listar_periodos", {})])
    resultado = Agente(cliente=modelo, modelo="falso", max_passos=3).perguntar(
        db,
        "loop?",
    )

    assert resultado.passos == 3
    assert len(modelo.chamadas) == 3
    assert "Não consegui" in resultado.resposta


def test_agente_falha_do_modelo_vira_indisponivel(db):
    modelo = ModeloFalso([RuntimeError("cota estourada")])
    with pytest.raises(AgenteIndisponivel):
        Agente(cliente=modelo, modelo="falso").perguntar(db, "oi")


# ---------------------------------- rota ----------------------------------


@pytest.fixture
def agente_falso():
    modelo = ModeloFalso([_resposta_texto("Resposta de teste.")])
    falso = Agente(cliente=modelo, modelo="falso")
    app.dependency_overrides[rota_agente.get_agente] = lambda: falso
    yield modelo
    app.dependency_overrides.pop(rota_agente.get_agente, None)


@pytest.fixture
def limite_folgado(monkeypatch):
    monkeypatch.setattr(rota_agente, "limite", LimiteDeUso(100, 1000))


def test_rota_responde_com_consultas_e_custos(client, agente_falso, limite_folgado):
    resp = client.post("/perguntar", json={"pergunta": "Como está o emprego?"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["resposta"] == "Resposta de teste."
    assert corpo["modelo"] == "falso"
    assert set(corpo) >= {"consultas", "tokens_entrada", "tokens_saida", "latencia_ms"}


@pytest.mark.parametrize("pergunta", ["", "oi", "x" * 301])
def test_rota_rejeita_pergunta_fora_do_tamanho(client, agente_falso, pergunta):
    resp = client.post("/perguntar", json={"pergunta": pergunta})
    assert resp.status_code == 422


def test_rota_desligada_sem_chave(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    resp = client.post("/perguntar", json={"pergunta": "Como está o emprego?"})
    assert resp.status_code == 503


def test_rota_limita_perguntas_por_minuto(client, agente_falso, monkeypatch):
    monkeypatch.setattr(rota_agente, "limite", LimiteDeUso(2, 1000))

    codigos = [
        client.post("/perguntar", json={"pergunta": "Pergunta?"}).status_code
        for _ in range(3)
    ]
    assert codigos == [200, 200, 429]


def test_rota_modelo_fora_do_ar_vira_502(client, limite_folgado):
    modelo = ModeloFalso([RuntimeError("timeout")])
    falso = Agente(cliente=modelo, modelo="falso")
    app.dependency_overrides[rota_agente.get_agente] = lambda: falso
    try:
        resp = client.post("/perguntar", json={"pergunta": "Pergunta?"})
    finally:
        app.dependency_overrides.pop(rota_agente.get_agente, None)

    assert resp.status_code == 502
    assert "timeout" not in resp.text


def test_limite_diario_global():
    limite = LimiteDeUso(por_minuto_por_ip=100, por_dia_total=2)
    assert limite.permitir("a")[0]
    assert limite.permitir("b")[0]
    permitido, motivo = limite.permitir("c")
    assert not permitido
    assert "diário" in motivo


def test_limite_esquece_ips_inativos(monkeypatch):
    relogio = iter([0.0, 0.0, 100.0])
    monkeypatch.setattr("src.agent.limites.time.monotonic", lambda: next(relogio))
    limite = LimiteDeUso(por_minuto_por_ip=5, por_dia_total=100)

    limite.permitir("a")
    limite.permitir("b")
    limite.permitir("c")  # 100 s depois: "a" e "b" já podem ser esquecidos

    assert set(limite._por_ip) == {"c"}


# ------------------------------- avaliação --------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("saldo de 14.223 vagas", [14223.0]),
        ("salário de R$ 4.494,44", [4494.44]),
        ("foram 254 empregos", [254.0]),
        ("valor 3448.28", [3448.28]),
    ],
)
def test_numeros_do_texto(texto, esperado):
    assert numeros_do_texto(texto) == esperado


def _caso(tipo="numero"):
    return Caso("?", lambda _db: None, tipo)


def test_corrigir_exige_sinal_quando_esperado_e_negativo():
    assert corrigir(_caso(), -201, "saldo negativo de 201 empregos")
    assert corrigir(_caso(), -201, "saldo de -201 empregos")
    assert not corrigir(_caso(), -201, "saldo positivo de 201 empregos")


def test_corrigir_aceita_salario_arredondado():
    assert corrigir(_caso(), 4494.44, "salário médio de R$ 4.494")
    assert not corrigir(_caso(), 4494.44, "salário médio de R$ 4.300")


def test_corrigir_texto_ignora_plural():
    nome = "Indústrias de transformação"
    assert corrigir(_caso("texto"), nome, "A indústria de transformação liderou.")
    assert not corrigir(_caso("texto"), nome, "O comércio liderou.")


def test_corrigir_recusa_que_inventa_numero_nao_vale():
    recusa = _caso("recusa")
    assert corrigir(recusa, None, "Não há esse dado. Tenho dados de 2022 a 2024.")
    assert not corrigir(
        recusa,
        None,
        "Não há o dado exato, mas o PIB é de aproximadamente 30.000 milhões.",
    )
    assert not corrigir(recusa, None, "O PIB de Joinville é alto.")


def test_resposta_vazia_do_modelo_tem_mensagem_padrao(db):
    vazio = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[]))],
    )
    modelo = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: vazio),
    )
    resultado = Agente(cliente=modelo, modelo="falso").perguntar(db, "?")
    assert resultado.resposta
