# 📊 Documentação — Nova Fonte de Dados: CEMPRE (IBGE)

> Este documento explica o que é o CEMPRE, por que ele foi integrado a este servidor, como o dado flui dentro da arquitetura e quais decisões técnicas foram tomadas na implementação.

**Status:** ✅ implementado e validado com dados reais (anos 2022, 2023 e 2024).

---

## 🧭 O que é o CEMPRE

O **CEMPRE** (Cadastro Central de Empresas) é uma pesquisa anual do IBGE. Ele mostra, por município, quantas unidades de empresas existem, quantas pessoas estão ocupadas e quanto se paga em salários — tudo organizado por setor de atividade (seções da CNAE 2.0).

Ele entra como uma **segunda fonte de dados**, ao lado do CAGED, dentro do mesmo servidor.

---

## 🎬 CAGED vs 📸 CEMPRE — por que os dois juntos

| | 🎬 CAGED | 📸 CEMPRE |
|---|---|---|
| **O que mostra** | O movimento: quem foi admitido, quem foi desligado | O retrato: quantas unidades e empregos existem, parado no tempo |
| **Frequência** | Mensal | Anual |
| **Analogia** | Um filme — mostra a ação acontecendo, mês a mês | Uma fotografia — mostra o cenário completo, uma vez por ano |

➡️ Um mostra o **fluxo**, o outro mostra o **estoque**. Juntos, dão o quadro completo do mercado de trabalho de Joinville — não faz sentido ter um sem o outro.

---

## 🏭 Como o dado flui (linha de produção)

```
🌐 API do IBGE (SIDRA)
        ↓
🤖 Collector        → busca a matéria-prima bruta na fonte oficial
        ↓
🔄 Transformer      → limpa, padroniza, pivota e valida o material coletado
        ↓
🗄️ Database         → guarda o resultado já pronto, organizado
        ↓
🚪 API (Router)     → disponibiliza o dado pronto pra quem pedir
        ↓
📱 Site Nexus       → consome e exibe o dado final
```

Cada seta é uma etapa de uma esteira: o dado bruto entra de um lado, e só sai pronto pro consumo do outro lado depois de passar por todas as estações.

---

## 🗂️ Onde cada peça mora no projeto

| Camada | Arquivo | Status | O que faz |
|---|---|---|---|
| 🤖 Coleta | `src/collectors/cempre.py` | 🆕 novo | Busca os dados na API do SIDRA (IBGE) |
| 🔄 Transformação | `src/transformers/cempre.py` | 🆕 novo | Converte símbolos do IBGE, pivota as variáveis e valida os registros |
| 📐 Contrato de dados | `src/schemas/cempre.py` | 🆕 novo | Define o formato dos dados (Pydantic) |
| 🗄️ Modelo do banco | `src/database/models.py` | ✏️ editado | Adiciona a tabela `CempreEmprego` |
| 📦 Acesso ao banco | `src/database/repositorio_cempre.py` | 🆕 novo | Busca, contagem, upsert e remoção do CEMPRE (separado do CAGED) |
| ⚙️ Orquestração | `src/services/atualizacao_cempre.py` | 🆕 novo | Junta coleta → transformação → validação → gravação |
| 🚪 Endpoints | `src/api/routers/cempre.py` | 🆕 novo | Expõe o CEMPRE como rota `/cempre` (somente leitura) |
| 🔌 Registro na API | `src/api/app.py` | ✏️ editado | Liga o router à aplicação com registro protegido |
| ⏱️ Agendamento | `src/scheduler/scheduler.py` | ✏️ editado | Job mensal próprio, isolado do job do CAGED |
| 🔧 Configurações | `src/core/settings.py` | ✏️ editado | URL da fonte e data fixa do agendamento |
| 🧱 Migrações do banco | `alembic/versions/c54a3a3e7feb_...`, `7b2e4d9a1c3f_...` | 🆕 novo | Criam a tabela e liberam `NULL` nas colunas numéricas |
| 🧪 Testes | `tests/test_cempre_router.py`, `tests/test_transformer_cempre.py` | 🆕 novo | Rotas, filtros e tratamento dos valores do IBGE |

**Legenda:** 🆕 arquivo novo · ✏️ arquivo já existente, só ganhou um trecho a mais.

---

## 🏢 Um servidor novo, ou o mesmo servidor?

✅ **Decisão: o mesmo servidor, com cada fonte isolada nos próprios arquivos.**

Pensa assim: é o mesmo prédio, só uma sala nova sendo aberta dentro dele — mesma recepção (API), mesmo estoque (banco de dados), mesma equipe de manutenção (deploy). Criar um servidor separado significaria duplicar tudo isso (outro Docker, outro pipeline, outro monitoramento) sem nenhum ganho real hoje.

O isolamento acontece em três pontos:

| Ponto | Como funciona | O que protege |
|---|---|---|
| 📂 Arquivos separados | Cada fonte tem collector, transformer, repositório, service e router próprios | Um erro no código do CEMPRE não toca no código do CAGED |
| 🔌 Registro protegido | O router do CEMPRE é importado dentro de um `try` no `app.py` | Se o CEMPRE quebrar, a API sobe mesmo assim, só sem a rota `/cempre` |
| ⏱️ Job próprio | O job do CEMPRE tem tratamento de erro próprio no scheduler | Uma falha na coleta do CEMPRE não derruba o scheduler nem o job do CAGED |

⚠️ **Limite do isolamento:** ele protege contra erros de uma fonte, não contra falhas da infraestrutura compartilhada (servidor ou banco fora do ar).

---

## 🧩 Fonte de dados

- 🌐 **SIDRA (IBGE)** — tabela **9510**: CEMPRE por seção da CNAE 2.0, para municípios com 50 mil habitantes ou mais
- 📍 **Código do município:** `4209102` (Joinville)
- 📅 **Anos disponíveis na tabela:** 2022, 2023 e 2024

| Código da variável | Variável | Coluna no banco |
|---|---|---|
| `706` | Número de unidades locais | `unidades_locais` |
| `707` | Pessoal ocupado total | `pessoal_ocupado` |
| `10143` | Salário médio mensal (R$) | `salario_medio` |

**Por que a 9510 e não a 9509:** a 9509 traz só o total do município, sem abrir por setor. O projeto inteiro trabalha com **ano + setor**, então a 9510 é a que serve.

**Por que a variável 367 (número de empresas) ficou de fora:** quando aberta por seção no nível de município, ela vem como `-` no SIDRA.

---

## 🔢 Tratamento dos valores especiais do IBGE

O SIDRA usa símbolos no lugar de números em alguns casos. Cada um tem um significado diferente, e o projeto respeita essa diferença:

| Símbolo | Significado no IBGE | Gravado no banco como |
|---|---|---|
| `-` | Zero absoluto | `0` |
| `X` | Valor omitido para não identificar o informante (sigiloso) | `NULL` |
| `...` | Valor não disponível | `NULL` |
| `..` | Não se aplica | `NULL` |

➡️ **Por quê:** gravar `X` como `0` diria "zero empregos" onde, na verdade, o número existe mas é secreto. `NULL` significa "não sabemos"; `0` significa "zero de verdade". Por isso as três colunas numéricas aceitam `NULL` e não têm valor padrão.

---

## ➕ A linha "Total"

O SIDRA também entrega uma linha **"Total"**, que é a soma de todas as seções. Ela é gravada no banco como um setor a mais.

⚠️ **Cuidado ao somar:** somar todos os registros de um ano conta o emprego **em dobro** (seções + Total). Para somar ou comparar setores, use o filtro `incluir_total=false`.

---

## 🚪 Endpoints

Todas as rotas são **somente leitura**: quem grava no banco é apenas o service de atualização.

| Método | Rota | O que retorna |
|---|---|---|
| `GET` | `/cempre/` | Lista de registros. Filtros: `ano`, `setor` (busca parcial), `skip`, `limit`, `incluir_total` |
| `GET` | `/cempre/stats/resumo` | Total de registros gravados |
| `GET` | `/cempre/{registro_id}` | Um registro pelo ID (404 se não existir) |

**Exemplos:**

```
/cempre/?ano=2024                        → 22 registros (21 seções + Total)
/cempre/?ano=2024&incluir_total=false    → 21 registros (só as seções)
/cempre/?setor=Total                     → evolução do total de Joinville por ano
/cempre/?setor=transformação             → indústria de transformação, todos os anos
```

---

## ⏱️ Atualização automática

- O job do CEMPRE roda **todo dia 1º do mês, às 3h** (`SCHEDULER_CEMPRE_DIA` e `SCHEDULER_CEMPRE_HORA` no `settings.py`).
- **Por que data fixa e não intervalo de 30 dias:** um intervalo recomeça do zero a cada reinício do servidor; se o servidor reiniciar com frequência, o job nunca roda. Uma data fixa no calendário não tem esse problema.
- **Por que mensal, se o CEMPRE é anual:** a data de publicação do IBGE varia. Checar uma vez por mês garante que o dado novo entra no máximo um mês depois de publicado, e o upsert torna as checagens repetidas inofensivas.

---

## ▶️ Como rodar manualmente

```bash
# ano mais recente publicado pelo IBGE
uv run python -m src.services.atualizacao_cempre

# anos específicos (carga histórica / backfill)
uv run python -m src.services.atualizacao_cempre 2022 2023
```

Cada ano é processado separadamente: se um falhar, os outros continuam. Rodar mais de uma vez não duplica dados (upsert pela chave `ano + setor`).

---

## ⚖️ Decisões tomadas

| Decisão | Escolha | Motivo |
|---|---|---|
| 🧱 Criação da tabela | **Alembic** | Migrações versionadas e reversíveis, em vez de repetir o `criar_tabelas.py` |
| ⏱️ Agendamento | **Mensal, com data fixa (`cron`)** | Resiste a reinícios do servidor |
| 🔢 Valores sigilosos | **`NULL`, não `0`** | Não confundir "não divulgado" com "zero" |
| 🚪 Rotas de escrita | **Nenhuma** | O dado é oficial; só o service grava |
| 📦 Repositório | **Arquivo próprio (`repositorio_cempre.py`)** | Isolamento entre as fontes |

---

## 🔮 Pendências e próximos passos

- 📜 **Anos anteriores a 2022:** ficam em outras tabelas do SIDRA, com outros códigos de variáveis e possível mudança de metodologia. Precisa de análise antes de misturar com a série 2022+.
- 🗂️ **Separar o `models.py` por fonte** (`models_caged.py` / `models_cempre.py`), completando o isolamento.
- 🧪 **Teste para o `__main__` do service** (leitura dos anos pela linha de comando).
