# 📋 Documentação — Nova Fonte de Dados: RFB (Receita Federal / CNPJ)

> Este documento explica o que é a base de CNPJ da Receita Federal, por que ela foi integrada a este servidor, como o dado flui dentro da arquitetura e quais decisões técnicas foram tomadas na implementação.

**Status:** ✅ implementado (coleta, transformação, banco, API e agendamento) · ⏳ testes automatizados pendentes.

---

## 🧭 O que é a RFB (dados abertos do CNPJ)

A Receita Federal publica, **todo mês**, o cadastro completo de todas as empresas do Brasil: situação cadastral (ativa, baixada etc.), data de abertura, atividade principal (CNAE), porte e opção pelo Simples Nacional / MEI.

Ela entra como **terceira fonte de dados**, ao lado do CAGED e do CEMPRE, dentro do mesmo servidor.

---

## 🧩 CAGED vs CEMPRE vs RFB

| | 🎬 CAGED | 📸 CEMPRE | 📋 RFB |
|---|---|---|---|
| **O que mostra** | Movimento de empregos (admissões/desligamentos) | Retrato de empregos e salários por setor | Cadastro de empresas: ativas, aberturas, encerramentos |
| **Frequência** | Mensal | Anual | Mensal |
| **Unidade** | Pessoas | Unidades locais e pessoas | Estabelecimentos (CNPJ) |

➡️ O CAGED fala de **pessoas** se movendo, o CEMPRE do **tamanho** de cada setor, a RFB das **empresas** nascendo e fechando. Como as três usam as seções da CNAE 2.0, dá para cruzar os setores entre elas.

---

## ⚠️ A grande diferença: RFB não é API, é arquivo

| | CEMPRE (SIDRA) | RFB |
|---|---|---|
| Como chega | API: pede só Joinville, recebe só Joinville | Arquivos `.zip` do **Brasil inteiro**, sem filtro |
| Tamanho | Alguns KB | Vários GB compactados |
| Formato | JSON | CSV sem cabeçalho, separador `;`, codificação ISO-8859-1 |

Consequências no projeto:

1. 💾 **Leitura em blocos** (`RFB_TAMANHO_BLOCO`): o arquivo nunca é carregado inteiro na memória; cada bloco é filtrado e só as linhas de Joinville ficam.
2. 🗑️ **Pasta temporária** (`../data/rfb_temp`, fora do Git): os zips são baixados ali e apagados ao final do processamento, com sucesso ou com erro.
3. 🔁 **Download com retry e timeout** (`RFB_TENTATIVAS`, `RFB_TIMEOUT_SEGUNDOS`): o servidor da Receita é lento e instável.
4. 🧾 **Zip validado antes da leitura**: tamanho e assinatura do arquivo são conferidos, para não processar um download corrompido ou uma página de erro salva como `.zip`.
5. ⏭️ **Competência já processada é pulada**: evita baixar GBs à toa.

---

## 🏭 Como o dado flui

```
🌐 Servidor de arquivos da RFB (WebDAV)
        ↓
🤖 Collector        → descobre o mês mais recente, baixa os zips, lê em blocos e filtra Joinville
        ↓
🔄 Transformer      → junta as bases, mapeia CNAE → seção, agrega e valida
        ↓
🗄️ Database         → grava os números agregados por competência + setor
        ↓
🚪 API (Router)     → disponibiliza o dado pronto (somente leitura)
        ↓
📱 Site Nexus       → consome e exibe o dado final
```

---

## 🗂️ Onde cada peça mora no projeto

| Camada | Arquivo | Status | O que faz |
|---|---|---|---|
| 🤖 Coleta | `../src/collectors/rfb.py` | 🆕 novo | Lista as competências via WebDAV, baixa e lê os zips em blocos, filtra Joinville |
| 🔄 Transformação | `../src/transformers/rfb.py` | 🆕 novo | Junta as 3 bases, mapeia CNAE → seção, agrega e valida |
| 📐 Contrato de dados | `../src/schemas/rfb.py` | 🆕 novo | Formato dos dados (Pydantic) |
| 🗄️ Modelo do banco | `../src/database/models.py` | ✏️ editado | Adiciona a tabela `RfbEmpresa` |
| 📦 Acesso ao banco | `../src/database/repositorio_rfb.py` | 🆕 novo | Busca, contagem, upsert, lista de competências e checagem de competência processada |
| ⚙️ Orquestração | `../src/services/atualizacao_rfb.py` | 🆕 novo | Coleta → transformação → validação → gravação → limpeza dos temporários |
| 🚪 Endpoints | `../src/api/routers/rfb.py` | 🆕 novo | Rota `/rfb` somente leitura |
| 🔌 Registro na API | `../src/api/app.py` | ✏️ editado | Registro protegido (`try`), igual ao CEMPRE |
| ⏱️ Agendamento | `../src/scheduler/scheduler.py` | ✏️ editado | Job mensal próprio, isolado, com `max_instances=1` |
| 🔧 Configurações | `../src/core/settings.py` | ✏️ editado | URL, caminho WebDAV, código de Joinville, pasta temporária, retry, blocos, data do job |
| 🧱 Migração | `../alembic/versions/3101cdc26c6d_cria_tabela_rfb_empresas.py` | 🆕 novo | Cria a tabela `rfb_empresas` |
| 🙈 Git | `../.gitignore` | ✏️ editado | Ignora `../data/rfb_temp` |

**Legenda:** 🆕 arquivo novo · ✏️ arquivo já existente, só ganhou um trecho a mais.

---

## 🧩 Fonte de dados

- 🌐 **Servidor:** `arquivos.receitafederal.gov.br`, acessado via **WebDAV** (`/public.php/webdav`), com uma pasta por mês no formato `AAAA-MM`
- 🔎 **Descoberta do mês mais recente:** comando `PROPFIND` (lista a pasta; o sucesso vem como `207 Multi-Status`, não `200`)
- 📍 **Código do município:** `8179` (Joinville na tabela da RFB, herdada do SIAFI) — **não é** o código do IBGE (`4209102`)

| Arquivo | Usado? | Para quê |
|---|---|---|
| `Estabelecimentos0..9.zip` | ✅ | Município, situação cadastral, datas, CNAE principal |
| `Empresas0..9.zip` | ✅ | Porte (não tem município) |
| `Simples.zip` | ✅ | Opção pelo Simples Nacional e pelo MEI |
| `Socios0..9.zip` | ❌ | Dados pessoais; não agregam ao objetivo e geram risco de LGPD |

🔑 **A ordem de leitura importa**, porque só o Estabelecimentos tem município:

```
1. Estabelecimentos → filtra Joinville → guarda o conjunto de cnpj_basico
2. Empresas         → mantém só quem está nesse conjunto
3. Simples          → mantém só quem está nesse conjunto
```

Se Joinville não tiver nenhum CNPJ na competência, Empresas e Simples não são baixados.

**Por que tudo é lido como texto:** o `cnpj_basico` tem zeros à esquerda (`00012345`). Lido como número, viraria `12345` e o cruzamento entre os arquivos quebraria sem erro.

---

## 🔢 Regras de contagem

| Coluna | Regra |
|---|---|
| `ativas` | Situação cadastral `02` (ativa) |
| `aberturas` | Data de início de atividade dentro da competência |
| `encerramentos` | Situação `08` (baixada) **e** data da situação dentro da competência |
| `ativas_mei` | Ativas com opção pelo MEI |
| `ativas_simples` | Ativas no Simples Nacional, sem contar MEI |

**CNAE → seção:** os 2 primeiros dígitos da CNAE (a divisão) indicam a seção. Os nomes das seções são **os mesmos do CEMPRE**, para permitir o cruzamento. CNAE fora do mapa entra como `Não classificado`.

---

## 🗄️ Tabela `rfb_empresas`

- **Granularidade:** números agregados por **competência + setor** — nenhum dado de empresa individual é gravado.
- **Chave única:** `competencia + setor` (`uq_competencia_setor_rfb`) → upsert idempotente.
- **Colunas numéricas `NOT NULL`, padrão `0`:** diferente do IBGE, aqui não existe valor sigiloso ou indisponível; a contagem é feita pelo próprio projeto, então ausência de empresas é zero de verdade.

---

## ➕ A linha "Total"

Assim como no CEMPRE, cada competência ganha uma linha **"Total"** (soma de todos os setores).

⚠️ **Cuidado ao somar:** somar todos os registros de uma competência conta tudo **em dobro**. Para somar ou comparar setores, use `incluir_total=false`.

---

## 🚪 Endpoints

Todas as rotas são **somente leitura**: quem grava no banco é apenas o service de atualização.

| Método | Rota | O que retorna |
|---|---|---|
| `GET` | `/rfb/` | Lista de registros. Filtros: `competencia` (`AAAA-MM`), `setor` (busca parcial), `skip`, `limit` (1 a 1000), `incluir_total` |
| `GET` | `/rfb/stats/resumo` | Total de registros e lista de competências disponíveis |
| `GET` | `/rfb/{registro_id}` | Um registro pelo ID (404 se não existir) |

**Exemplos:**

```
/rfb/?competencia=2026-09                       → todos os setores + Total do mês
/rfb/?competencia=2026-09&incluir_total=false   → só os setores
/rfb/?setor=Total                               → evolução do total de Joinville mês a mês
/rfb/?setor=transformação                       → indústria de transformação, todos os meses
```

---

## ⏱️ Atualização automática

- O job da RFB roda **todo dia 15 do mês, às 4h** (`SCHEDULER_RFB_DIA` e `SCHEDULER_RFB_HORA`), em horário diferente do CAGED e do CEMPRE.
- **Data fixa (`cron`):** resiste a reinícios do servidor, mesmo motivo do CEMPRE.
- **`max_instances=1`:** o download pode levar horas; impede que uma nova execução comece enquanto a anterior ainda roda.
- **Se a Receita ainda não publicou o mês:** a competência mais recente já está no banco e o job pula; o mês novo entra na execução seguinte.

---

## ▶️ Como rodar manualmente

```bash
# competência mais recente publicada pela RFB
uv run python -m src.services.atualizacao_rfb

# competências específicas
uv run python -m src.services.atualizacao_rfb 2026-08 2026-09

# reprocessar uma competência que já está no banco
uv run python -m src.services.atualizacao_rfb 2026-09 --forcar
```

Rodar mais de uma vez não duplica dados (upsert por `competencia + setor`).

---

## ⚖️ Decisões tomadas

| Decisão | Escolha | Motivo |
|---|---|---|
| 📦 Granularidade | **Agregado por competência + setor** | Leve, sem dado pessoal, cruza com o CEMPRE |
| 👥 Sócios | **Fora** | LGPD, sem ganho para o objetivo |
| 🔢 Nulos | **`NOT NULL`, padrão `0`** | A contagem é do projeto; não há valor sigiloso |
| 🚪 Rotas de escrita | **Nenhuma** | Dado oficial; só o service grava |
| ⏱️ Agendamento | **Cron mensal + "competência já processada?"** | Resiste a reinício e não baixa GBs à toa |
| 🗑️ Temporários | **Apagados sempre, mesmo com erro** | Evita encher o disco do servidor |

---

## 🔮 Pendências e próximos passos

- 🧪 **Testes automatizados:** `tests/test_transformer_rfb.py` e `tests/test_rfb_router.py`, com CSV pequeno de exemplo (sem baixar da Receita).
- 🔁 **Atraso do cadastro:** as aberturas do mês mais recente tendem a vir subestimadas; avaliar reprocessar as últimas 2–3 competências a cada execução.
- 🕰️ **Série histórica de aberturas:** o arquivo de um único mês já traz a data de abertura de todas as empresas; dá para montar o histórico numa carga só.
- 🔧 **`RFB_SHARE_TOKEN` no `../.env`:** hoje está fixo no `settings.py`.
- 🗂️ **Separar `models.py` por fonte:** pendente desde o CEMPRE; com três fontes fica mais urgente.