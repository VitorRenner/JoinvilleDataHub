# Como rodar o CAGED API em 5 minutos (macOS)

Este guia foi reescrito depois de ler o código-fonte inteiro do projeto, o `uv.lock` (dependência por dependência) e o histórico do Git. Ele substitui qualquer guia anterior.

> **Atualização de outubro/2026:** o projeto agora tem duas fontes de dados — **CAGED** (Ministério do Trabalho) e **CEMPRE** (IBGE) — e as tabelas do banco passaram a ser criadas pelo **Alembic**. Os Passos 8, 9c, 10, 11 e 12 foram atualizados.

---

## Achados antes de começar — provavelmente é um destes que te travou

1. **O caminho da pasta do projeto tem espaços** (`Estágio 2026`, `JOINVILLE DATA HUB`). Se você digitar o `cd` na mão sem aspas, o Terminal responde `No such file or directory`. A solução é usar aspas ou autocompletar (Tab) — veja o Passo 3.
2. **As tabelas são criadas pelo Alembic, não pelo `criar_tabelas`.** A primeira migration (`ff49cd00f76d_initial_schema.py`) cria a tabela do CAGED, e as seguintes criam e ajustam a tabela do CEMPRE. Num banco novo, `uv run alembic upgrade head` cria tudo (Passo 8). **Não misture com `src.scripts.criar_tabelas`**: ele cria as tabelas sem registrar a versão no Alembic, e o próximo `upgrade head` falha tentando criá-las de novo.
3. **O `.env` tem uma linha quebrada.** A segunda linha do arquivo é uma chave da OpenAI solta, sem `NOME_DA_VARIAVEL=` na frente. Isso não derruba o `python-dotenv` (ele ignora a linha com um aviso), mas é sujeira que vale limpar — Passo 6.
4. **A coleta de dados do CAGED depende de FTP (porta 21) para `ftp.mtps.gov.br`.** Redes de faculdade, corporativas ou com CGNAT costumam bloquear essa porta. Para garantir que o projeto rode em 5 minutos **independente da sua rede**, este guia usa por padrão os arquivos que **já estão em cache local** em `data/raw/caged/202605/` e `data/raw/caged/202606/` (competências 05/2026 e 06/2026, já baixadas e extraídas anteriormente). O pipeline detecta que os `.txt` já existem e pula o download — Passo 9.
5. **Os comandos usam caminhos relativos** (`data/raw/caged/...`), então todo `uv run` **precisa ser executado com o terminal já dentro da pasta raiz do projeto** (a que tem o `main.py`). Rodar de qualquer outro lugar quebra a coleta e a criação das tabelas.
6. **Todas as dependências nativas do projeto têm wheel pronta para macOS** (Intel e Apple Silicon) para Python 3.14 — conferido pacote a pacote no `uv.lock` (`py7zr`, `pyppmd`, `pybcj`, `inflate64`, `psycopg2-binary`, etc). Ou seja, **não precisa instalar Xcode Command Line Tools nem compilar nada** — `uv sync` só baixa wheels prontas.

---

## 0. Diagnóstico rápido (30 segundos)

Abra o **Terminal** (Spotlight → `Terminal`) e rode, um por um, só para saber o que já está instalado:

```bash
sw_vers
uname -m
brew --version
python3 --version
uv --version
pg_isready
```

- `uname -m` retorna `arm64` (Apple Silicon: M1/M2/M3/M4) ou `x86_64` (Intel) — não muda nenhum comando abaixo, é só referência.
- Se `brew --version` der `command not found`, siga o Passo 1. Se já tiver, pule para o Passo 2.
- Não se preocupe se `uv`, `pg_isready` derem erro — é esperado se ainda não instalou nada.

---

## 1. Instalar o Homebrew (pule se já tiver)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Ao final, o instalador mostra 1–2 comandos para adicionar o Homebrew ao `PATH` (algo como `echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile`). **Copie e cole exatamente o que aparecer no seu terminal**, depois feche e reabra o Terminal.

---

## 2. Instalar as dependências de sistema via Homebrew

```bash
brew install uv postgresql@16
brew install --cask pgadmin4
```

Isso instala:
- **`uv`** — gerenciador de pacotes e de versões do Python usado pelo projeto (não é `pip`).
- **`postgresql@16`** — o servidor de banco de dados.
- **`pgadmin4`** — a interface gráfica para ver e consultar o banco.

Iniciar o PostgreSQL como serviço (fica rodando em segundo plano, inclusive após reiniciar o Mac):

```bash
brew services start postgresql@16
```

Confirme que subiu:

```bash
pg_isready
```

Deve responder algo como `/tmp:5432 - accepting connections`.

---

## 3. Entrar na pasta do projeto

O caminho completo no seu Mac é:

```
/Users/vitaorenner/Estágio 2026/joinville-data-hub/JOINVILLE DATA HUB
```

Como o caminho tem espaços (ver "Achado 1" acima), use aspas:

```bash
cd ~/"Estágio 2026"/joinville-data-hub/"JOINVILLE DATA HUB"
```

Confirme que entrou no lugar certo:

```bash
pwd
ls
```

Você deve ver `main.py`, `pyproject.toml`, `src/`, `.env`, `alembic/`, `uv.lock`, etc. **A partir daqui, todos os comandos deste guia assumem que o terminal está dentro dessa pasta.** Se fechar o Terminal, repita o `cd` acima antes de continuar.

---

## 4. Instalar o Python 3.14

O projeto exige Python 3.14+ (`pyproject.toml` → `requires-python = ">=3.14"`). Deixe o `uv` cuidar disso — ele baixa um Python isolado, sem mexer no Python do sistema:

```bash
uv python install 3.14
```

---

## 5. Instalar as dependências do projeto

Ainda dentro da pasta do projeto:

```bash
uv sync
```

Isso lê o `uv.lock` e instala exatamente as versões travadas (FastAPI, SQLAlchemy, psycopg2, pandas, apscheduler, alembic, py7zr, etc.) dentro de uma `.venv/` local ao projeto. Como confirmado no achado 6, isso não deve baixar nem compilar nada pesado — só wheels prontas. Se demorar mais que ~1 minuto, é só o download normal dos pacotes.

Não use `pip install -r requirements.txt` — esse arquivo está desatualizado (falta `apscheduler`, `alembic`, `pydantic-settings`); a fonte de verdade é o `pyproject.toml` + `uv.lock`.

---

## 6. Conferir/corrigir o `.env`

O projeto já tem um `.env` na raiz com o seguinte conteúdo (confirmado lendo o arquivo real):

```env
DATABASE_URL=postgresql+psycopg2://postgres:1234@localhost:5432/caged_db
```

seguido de uma segunda linha solta com uma chave da OpenAI (sem nome de variável). Abra o arquivo para editar:

```bash
open -e .env
```

(abre no TextEdit; se preferir, `nano .env` direto no terminal)

Deixe o conteúdo assim, com cada variável em sua própria linha `NOME=valor`:

```env
ENVIRONMENT=development
DEBUG=True

DATABASE_URL=postgresql+psycopg2://postgres:1234@localhost:5432/caged_db

CAGED_BASE_URL=https://portaldatransparencia.gov.br
IBGE_BASE_URL=https://servicodados.ibge.gov.br/api/v1

SCHEDULER_INTERVAL_SECONDS=86400

CEMPRE_BASE_URL=https://apisidra.ibge.gov.br
SCHEDULER_CEMPRE_DIA=1
SCHEDULER_CEMPRE_HORA=3

# se você realmente precisa da chave da OpenAI em algum lugar do projeto,
# dê um nome pra ela, por exemplo:
# OPENAI_API_KEY=sk-proj-...
```

Ajuste `postgres:1234` se a senha do seu usuário `postgres` local for outra. `caged_db` é o nome do banco — vamos criá-lo no próximo passo com esse nome exato.

---

## 7. Criar o banco de dados no pgAdmin (clique a clique)

1. Abra o **pgAdmin 4** (Spotlight → `pgAdmin 4`).
2. Na primeira vez, ele pede para você definir uma **master password** do próprio pgAdmin (não é a senha do Postgres) — defina uma e confirme.
3. No painel esquerdo (**Browser**), clique para expandir **Servers**. Se não houver nenhum servidor listado, clique com o botão direito em **Servers** → **Register** → **Server...**:
   - Aba **General** → **Name**: `Local` (ou o nome que quiser).
   - Aba **Connection** → **Host name/address**: `localhost`; **Port**: `5432`; **Username**: `postgres`; **Password**: a senha do seu usuário `postgres` (a mesma que está no `DATABASE_URL`, ex.: `1234`). Marque **Save password** e clique em **Save**.
4. Expanda o servidor. Clique com o **botão direito** em **Databases** → **Create** → **Database...**
5. Campo **Database**: `caged_db` (tem que ser exatamente esse nome, igual ao `.env`).
6. **Owner**: `postgres`.
7. Clique em **Save**.
8. `caged_db` aparece na árvore em **Databases**. Ainda sem tabelas — isso vem no próximo passo.

---

## 8. Criar as tabelas — **use só este comando**

```bash
uv run alembic upgrade head
```

Isso aplica, em ordem, todas as migrations de `alembic/versions/`:

1. `ff49cd00f76d` — cria a tabela `caged_movimentacao`;
2. `c54a3a3e7feb` — cria a tabela `cempre_emprego`;
3. `7b2e4d9a1c3f` — libera `NULL` nas colunas numéricas do CEMPRE (valores sigilosos do IBGE).

Confirme a versão aplicada:

```bash
uv run alembic current
```

Deve responder `7b2e4d9a1c3f (head)`.

**Não rode `uv run -m src.scripts.criar_tabelas` num banco novo** — como explicado no achado 2, ele cria as tabelas sem registrar a versão no Alembic. Se você já rodou por engano, marque o banco como atualizado com `uv run alembic stamp head`.

### Conferir no pgAdmin que as tabelas foram criadas

1. No pgAdmin, expanda `caged_db` → **Schemas** → **public** → **Tables**.
2. Clique com o botão direito em **Tables** → **Refresh...**
3. Devem aparecer `caged_movimentacao`, `cempre_emprego` e `alembic_version` (a tabela onde o Alembic guarda a versão atual).

---

## 9. Rodar o pipeline completo — modo garantido (sem depender da sua rede)

Este é o comando que roda o fluxo inteiro (coleta → transformação → validação → persistência), usando a competência **06/2026, que já está em cache local** (`data/raw/caged/202606/`) — ou seja, **sem tentar baixar nada pela internet**, o que evita qualquer problema de FTP bloqueado e garante os 5 minutos:

```bash
uv run python -c "from src.services.atualizacao_caged import atualizar_caged; atualizar_caged(ano=2026, mes=6)"
```

O que acontece:

1. O coletor vê que `data/raw/caged/202606/202606/CAGEDMOV202606.txt` (e os outros dois arquivos) já existem e **pula o download**.
2. Filtra os registros do município de Joinville (código `420910`) dentro desses arquivos — o arquivo `CAGEDMOV202606.txt` tem ~424 MB e 4,3 milhões de linhas (dado nacional bruto), então essa etapa de leitura/filtro pode levar de alguns segundos a 1–2 minutos, dependendo do seu Mac. É normal — é a etapa mais pesada de todo o pipeline.
3. Agrega em admissões/demissões/saldo por competência e setor.
4. Valida e insere no Postgres (`upsert`, idempotente — pode rodar de novo sem duplicar).

No console você verá logs terminando em algo como `Persistência concluída. Registros processados: N.`

### 9b. (Opcional/avançado) Buscar a competência mais nova, direto do FTP oficial

Só faça isso depois que o modo garantido acima já tiver funcionado uma vez, e se sua rede permitir FTP (porta 21) de saída:

```bash
uv run -m src.services.atualizacao_caged
```

Sem argumentos, o serviço pergunta ao FTP `ftp.mtps.gov.br` qual é a competência mais recente publicada e baixa o que ainda não estiver em `data/raw/caged/`. Se travar por muito tempo ou der erro de timeout/conexão recusada, é provável que sua rede esteja bloqueando FTP — nesse caso, use uma rede diferente (ex.: hotspot do celular) ou fique no modo do Passo 9.

---

### 9c. Carregar os dados do CEMPRE (IBGE)

O CEMPRE vem da API do SIDRA (IBGE), por HTTPS — não depende de FTP. Para carregar os anos disponíveis (2022, 2023 e 2024):

```bash
uv run python -m src.services.atualizacao_cempre 2022 2023 2024
```

Sem argumentos, o serviço busca só o ano mais recente publicado:

```bash
uv run python -m src.services.atualizacao_cempre
```

Cada ano gera um bloco de log terminando em `Persistência concluída. Registros processados: 22.` (21 seções da CNAE + a linha "Total"). Se um ano falhar, os outros continuam, e o erro aparece completo no log. Pode rodar de novo sem duplicar (upsert pela chave ano + setor).

Detalhes da fonte, das variáveis e do tratamento dos valores especiais do IBGE em `docs/CEMPRE_API.md`.

---

## 10. Ver os dados no pgAdmin (clique a clique)

1. Expanda **Databases** → `caged_db` → **Schemas** → **public** → **Tables**.
2. Clique com o botão direito em **caged_movimentacao** → **View/Edit Data** → **All Rows**.
3. Abre uma grade com todas as linhas: `id`, `competencia`, `setor`, `admissoes`, `demissoes`, `saldo`, `criado_em`, `atualizado_em`.
4. Para uma consulta manual: botão direito em `caged_movimentacao` → **Query Tool**, digite:
   ```sql
   SELECT * FROM caged_movimentacao ORDER BY competencia DESC;
   ```
   e aperte **F5** (ou o botão ▶) para executar.
5. Para o CEMPRE, o mesmo caminho com a tabela **cempre_emprego**. Consulta útil (evolução do emprego total de Joinville):
   ```sql
   SELECT ano, pessoal_ocupado, salario_medio FROM cempre_emprego WHERE setor = 'Total' ORDER BY ano;
   ```
   Células vazias (`NULL`) significam valor sigiloso ou não divulgado pelo IBGE — não é zero.

---

## 11. Subir a API

```bash
uv run uvicorn src.api.app:app --reload
```

Isso sobe o FastAPI em `http://127.0.0.1:8000`.

**Sobre a atualização automática:** o scheduler está **desligado dentro da API** por padrão (ver `lifespan` em `src/api/app.py`); a recomendação é agendar externamente (cron/systemd) os comandos dos Passos 9b e 9c. Se quiser rodá-lo dentro da API, descomente `iniciar_scheduler()` no `lifespan`. Ele tem dois jobs isolados: o do CAGED (a cada `SCHEDULER_INTERVAL_SECONDS`, padrão uma vez por dia) e o do CEMPRE (todo dia 1º do mês, às 3h).

### Testar no Swagger

1. Abra `http://127.0.0.1:8000/docs` no navegador.
2. `GET /caged/` → **Try it out** → **Execute** → deve retornar a lista de registros.
3. `GET /caged/stats/resumo` → **Execute** → total de registros.
4. `GET /health` → **Execute** → confirma `"database": "connected"`.
5. `GET /cempre/` → **Try it out** → preencha `ano` com `2024` → **Execute** → 22 registros.
6. Mesmo teste com `incluir_total` = `false` → 21 registros (sem a linha "Total", que é a soma das seções).
7. `GET /cempre/stats/resumo` → **Execute** → total de registros do CEMPRE.

---

## 12. Checklist de 5 minutos — tudo em um bloco só

Depois de fazer os Passos 1–4 (Homebrew, uv, PostgreSQL, pgAdmin, Python 3.14) **uma única vez**, todo o resto pode ser colado de uma vez, com o terminal já dentro da pasta do projeto:

```bash
uv sync
uv run alembic upgrade head
uv run python -c "from src.services.atualizacao_caged import atualizar_caged; atualizar_caged(ano=2026, mes=6)"
uv run python -m src.services.atualizacao_cempre 2022 2023 2024
uv run uvicorn src.api.app:app --reload
```

(O Passo 7 — criar o banco `caged_db` no pgAdmin — precisa ser feito manualmente uma vez antes de rodar o `alembic upgrade head`, já que ainda não existe um comando no projeto que crie o banco em si, só as tabelas dentro dele.)

---

## 13. Solução de problemas (causa raiz, não só sintoma)

- **`cd: no such file or directory`** → os espaços no caminho da pasta (achado 1). Use o comando com aspas do Passo 3, ou abra a pasta no Finder e arraste-a para dentro da janela do Terminal depois de digitar `cd `.
- **`uv: command not found`** → fechou e abriu o Terminal antes do Homebrew terminar de configurar o `PATH`? Rode `brew list uv` para confirmar que instalou, e reabra o Terminal.
- **`pydantic_core._pydantic_core.ValidationError: DATABASE_URL Field required`** → o `.env` não está sendo lido. Confirme que o arquivo se chama exatamente `.env` (não `.env.txt`) e está na raiz do projeto (mesmo nível do `main.py`), e que você está rodando o comando de dentro dessa pasta.
- **`sqlalchemy.exc.OperationalError: connection to server ... failed`** → o PostgreSQL não está rodando. Rode `brew services list` (deve mostrar `postgresql@16` como `started`); se não, `brew services start postgresql@16`. Depois `pg_isready` para confirmar.
- **`sqlalchemy.exc.OperationalError: database "caged_db" does not exist`** → você pulou o Passo 7 (criar o banco no pgAdmin), ou criou com outro nome. O nome tem que bater exatamente com o `DATABASE_URL` do `.env`.
- **`relation "caged_movimentacao" does not exist`** (ou `cempre_emprego`) → você pulou o Passo 8. Rode `uv run alembic upgrade head`.
- **`relation "..." already exists` ao rodar o Alembic** → as tabelas foram criadas antes pelo `criar_tabelas`, sem registrar a versão (achado 2). Rode `uv run alembic stamp head` uma vez.
- **`null value in column ... violates not-null constraint` no CEMPRE** → o banco está numa versão antiga do schema. Rode `uv run alembic upgrade head` e confira com `uv run alembic current` (deve ser `7b2e4d9a1c3f`).
- **`Ano XXXX não foi carregado` no CEMPRE** → o traceback logo abaixo mostra a causa. Os mais comuns: ano inexistente na tabela 9510 do SIDRA (disponíveis: 2022 a 2024) ou API do IBGE fora do ar.
- **`FTP` travado, timeout, ou `ConnectionRefusedError` na porta 21** → sua rede está bloqueando FTP de saída (comum em redes de faculdade/corporativas). Use o modo do Passo 9 (dados em cache, sem rede) ou troque de rede para o Passo 9b.
- **`KeyError: 'município'`** → algum editor salvou o `.txt` do CAGED com outra codificação. Não edite os arquivos dentro de `data/raw/caged/` manualmente; se corromper, apague a pasta da competência (ex.: `rm -rf data/raw/caged/202606`) e rode o Passo 9b para baixar de novo.
- **Porta 8000 já em uso** → `uv run uvicorn src.api.app:app --reload --port 8001`.
- **Alterou `models.py`** → crie uma migration: `uv run alembic revision --autogenerate -m "descricao"`, **revise o arquivo gerado** (o autogenerate pode incluir diferenças antigas de outra tabela, como o índice `ix_caged_movimentacao_id`) e depois `uv run alembic upgrade head`.
