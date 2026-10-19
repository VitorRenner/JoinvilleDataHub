# 🏛️ Plano — Nova Fonte de Dados: RFB (Receita Federal / CNPJ)

> Mesmo molde do CEMPRE: o *o quê* (o que é e por que entra), o *como* (pseudocódigo de cada peça, sem código real) e o *quando* (cronograma).
> Sugestão de lugar no projeto: `docs/PLANO_RFB.md`.

---

## 🧭 O que é a RFB (dados abertos do CNPJ)

A Receita Federal publica, **todo mês**, o cadastro completo de todas as empresas do Brasil: quem abriu, quem está ativa, quem fechou, em qual setor (CNAE), qual o porte, se é MEI ou Simples Nacional.

Ela entra como **terceira fonte**, ao lado do CAGED e do CEMPRE, no mesmo servidor.

---

## 🏀 CAGED vs CEMPRE vs RFB — o time completo

| | 🎬 CAGED | 📸 CEMPRE | 📋 RFB |
|---|---|---|---|
| **O que mostra** | Movimento de **empregos** (admissões/desligamentos) | Retrato de **empregos e salários** por setor | Cadastro de **empresas**: aberturas, fechamentos, ativas |
| **Frequência** | Mensal | Anual | Mensal |
| **Analogia NBA** | O *play-by-play* do jogo | A tabela de estatísticas da temporada | O **registro oficial de elencos da liga**: quem foi contratado, quem foi dispensado, quem está no *injury list* |

➡️ O CAGED fala de **pessoas** se movendo, o CEMPRE fala do **tamanho** de cada setor, a RFB fala das **empresas** nascendo e morrendo. Com as três, dá pra responder coisas como: *"A indústria de Joinville está abrindo mais empresas E contratando mais gente, ou só uma das duas?"*

---

## ⚠️ A grande diferença: RFB não é API, é arquivo gigante

Aqui está o ponto que muda o desenho em relação ao CEMPRE:

| | CEMPRE (SIDRA) | RFB |
|---|---|---|
| Como chega | API: você pede só Joinville, recebe só Joinville | **Arquivos .zip do Brasil inteiro**, sem filtro |
| Tamanho | Alguns KB | **Vários GB compactados** (muito mais descompactados) |
| Formato | JSON | CSV **sem cabeçalho**, separador `;`, codificação **ISO-8859-1** |
| Onde | `apisidra.ibge.gov.br` | `arquivos.receitafederal.gov.br` (pasta `Dados/Cadastros/CNPJ`, uma subpasta por mês `AAAA-MM`) |

🏀 **Analogia:** com o CEMPRE você liga pra liga e pede "me manda as estatísticas do Joinville". Com a RFB, a liga te entrega **o arquivo de todos os jogadores de todos os times do país** e você tem que achar os seus. Por isso o *collector* vira um **olheiro**: lê o arquivo inteiro em pedaços e só guarda o que é de Joinville.

**Consequências diretas no projeto:**
1. 💾 **Nunca carregar o arquivo inteiro na memória** → ler em blocos (*chunks*) e filtrar Joinville bloco a bloco.
2. 🗑️ **Pasta temporária** pros downloads, apagada no fim do processamento (senão o disco do servidor lota em poucos meses).
3. 🐢 **Servidor da Receita é lento e instável** → download com *retry* e timeout generoso.
4. 🧾 **Não reprocessar mês já processado** → guardar quais competências já entraram (baixar GBs à toa é caro).

---

## 🗂️ Quais arquivos da RFB interessam

| Arquivo | Usar? | Por quê |
|---|---|---|
| `Estabelecimentos0..9.zip` | ✅ **Sim (o principal)** | Tem o **município**, a situação cadastral, data de abertura, CNAE principal |
| `Empresas0..9.zip` | ✅ Sim | Tem o **porte** e a natureza jurídica (mas **não** tem município) |
| `Simples.zip` | ✅ Sim | Diz se é **MEI** / Simples Nacional |
| `Municipios.zip`, `Cnaes.zip` | ✅ Sim (tabelas de apoio) | Traduzem códigos em nomes |
| `Socios0..9.zip` | ❌ **Não** | Dados pessoais (nomes, CPF mascarado). Não agrega nada ao objetivo do projeto e cria risco de LGPD |

**Chave que liga tudo:** `cnpj_basico` (os 8 primeiros dígitos do CNPJ).

🔑 **A ordem importa** (porque só o Estabelecimentos tem município):
```
1. Lê Estabelecimentos  → filtra Joinville → guarda o conjunto de cnpj_basico de Joinville
2. Lê Empresas          → mantém só quem está nesse conjunto (pega porte)
3. Lê Simples           → mantém só quem está nesse conjunto (pega MEI/Simples)
```
🏀 É como montar o elenco: primeiro você descobre **quem joga no Joinville** (Estabelecimentos), depois vai buscar a **ficha física** (Empresas) e o **tipo de contrato** (Simples) só desses jogadores.

⚠️ **Pegadinha do município:** o código de município da RFB **não é** o do IBGE. Joinville no IBGE é `4209102`; na RFB é outro código (tabela própria, herdada do SIAFI). Confirmar no `Municipios.zip` na Semana 1 e guardar em `settings.py`.

---

## 🧱 O que gravar no banco: agregado, não empresa por empresa

✅ **Decisão recomendada: gravar só números agregados por `competencia + setor`**, igual o CEMPRE grava por `ano + setor`.

| Opção | Prós | Contras |
|---|---|---|
| 📋 Uma linha por estabelecimento | Máxima flexibilidade | Dezenas de milhares de linhas, **dados pessoais** (MEI costuma ter nome e CPF da pessoa na razão social), foge do padrão do projeto |
| 📊 **Agregado por competência + setor** | Leve, sem dado pessoal, conversa direto com CAGED e CEMPRE | Menos flexível (nova quebra = reprocessar) |

**Tabela `rfb_empresas` — colunas planejadas:**

| Coluna | O que significa |
|---|---|
| `competencia` | Mês do arquivo da RFB (`AAAA-MM`) |
| `setor` | Seção da CNAE 2.0 (mesmo nome usado no CEMPRE, pra dar pra cruzar) + linha `Total` |
| `ativas` | Estabelecimentos com situação **ativa** naquele mês |
| `aberturas` | Estabelecimentos com **data de início de atividade** dentro do mês |
| `encerramentos` | Estabelecimentos **baixados** com data da situação dentro do mês |
| `ativas_mei` | Das ativas, quantas são MEI |
| `ativas_simples` | Das ativas, quantas são do Simples (sem MEI) |
| `criado_em`, `atualizado_em` | Padrão das outras tabelas |

**Chave única:** `competencia + setor` → upsert idempotente, igual ao CEMPRE.

🔄 **CNAE → seção:** a RFB entrega a CNAE **subclasse** (7 dígitos). Os **2 primeiros dígitos** (divisão) já dizem a seção (ex.: divisões 10 a 33 = Indústrias de Transformação). Um mapa fixo divisão → seção resolve, e deixa os nomes **iguais aos do CEMPRE**.

⚠️ **Mesmo cuidado do CEMPRE com a linha `Total`:** somar todos os registros de uma competência conta em dobro. Mesmo filtro `incluir_total=false`.

---

## 🗂️ Onde cada peça vai morar

| Camada | Arquivo | Status | O que faz |
|---|---|---|---|
| 🤖 Coleta | `src/collectors/rfb.py` | 🆕 novo | Descobre a competência mais recente, baixa os zips, lê em blocos e filtra Joinville |
| 🔄 Transformação | `src/transformers/rfb.py` | 🆕 novo | Junta as 3 bases, mapeia CNAE → seção, agrega e valida |
| 📐 Contrato | `src/schemas/rfb.py` | 🆕 novo | Formato dos dados (Pydantic) |
| 🗄️ Modelo | `src/database/models.py` (ou `models_rfb.py`, ver pendência do CEMPRE) | ✏️ editado | Tabela `RfbEmpresa` |
| 📦 Acesso ao banco | `src/database/repositorio_rfb.py` | 🆕 novo | Busca, contagem, upsert, "competência já processada?" |
| ⚙️ Orquestração | `src/services/atualizacao_rfb.py` | 🆕 novo | Coleta → transformação → validação → gravação → limpeza dos temporários |
| 🚪 Endpoints | `src/api/routers/rfb.py` | 🆕 novo | Rota `/rfb` somente leitura |
| 🔌 Registro | `src/api/app.py` | ✏️ editado | Import dentro de `try`, igual ao CEMPRE |
| ⏱️ Agendamento | `src/scheduler/scheduler.py` | ✏️ editado | Job mensal próprio, isolado |
| 🔧 Configurações | `src/core/settings.py` | ✏️ editado | URL, código RFB de Joinville, pasta temporária, data do job |
| 🧱 Migração | `alembic/versions/..._cria_tabela_rfb_empresas.py` | 🆕 novo | Via `alembic revision --autogenerate` |
| 🧪 Testes | `tests/test_rfb_router.py`, `tests/test_transformer_rfb.py` | 🆕 novo | Rotas, filtros, mapa CNAE, agregação |
| 🙈 Ignorar | `.gitignore` | ✏️ editado | Adicionar a pasta temporária dos downloads |

---

## 🧩 Pseudocódigo de cada peça

### `src/core/settings.py` (adições)

```
RFB_BASE_URL         = endereço da pasta de dados abertos do CNPJ
RFB_MUNICIPIO_JOINVILLE = código RFB de Joinville   // confirmar na Semana 1, NÃO é 4209102
RFB_PASTA_TEMP       = pasta onde os zips são baixados e apagados depois
RFB_TAMANHO_BLOCO    = quantas linhas ler por vez (ex.: algumas centenas de milhar)
SCHEDULER_RFB_DIA    = dia fixo do mês (ex.: 15)
SCHEDULER_RFB_HORA   = hora de madrugada, diferente do CAGED e do CEMPRE
```
**Por quê:** mesmo motivo do CEMPRE — nada fixo dentro do collector, tudo configurável por `.env`. Hora diferente pra não rodar os três jobs pesados ao mesmo tempo.

### `src/collectors/rfb.py`

```
classe RfbCollector:

    função descobrir_competencia_mais_recente():
        listar as subpastas AAAA-MM da RFB_BASE_URL
        retornar a maior

    função baixar(nome_arquivo, competencia):
        tentar até N vezes, com espera crescente entre tentativas:
            baixar em streaming (pedaço por pedaço) pra RFB_PASTA_TEMP
        retornar caminho do arquivo

    função ler_estabelecimentos_joinville(competencia):
        para cada Estabelecimentos0..9:
            baixar
            ler o CSV em blocos (sem cabeçalho, ';', ISO-8859-1, tudo como texto)
            em cada bloco: manter só linhas com municipio == RFB_MUNICIPIO_JOINVILLE
            guardar só as colunas úteis:
                cnpj_basico, situacao_cadastral, data_situacao_cadastral,
                data_inicio_atividade, cnae_fiscal_principal
            apagar o zip
        retornar tabela de Joinville + conjunto de cnpj_basico

    função ler_empresas(conjunto_cnpj, competencia):
        para cada Empresas0..9: ler em blocos, manter só cnpj_basico no conjunto
        guardar: cnpj_basico, porte

    função ler_simples(conjunto_cnpj, competencia):
        mesmo esquema; guardar: cnpj_basico, opcao_simples, opcao_mei

    função coletar(competencia=None):
        competencia = competencia ou descobrir_competencia_mais_recente()
        estab, conjunto = ler_estabelecimentos_joinville(competencia)
        empresas = ler_empresas(conjunto, competencia)
        simples  = ler_simples(conjunto, competencia)
        retornar (competencia, estab, empresas, simples)
```
**Por quê ler tudo como texto:** `cnpj_basico` tem zeros à esquerda (`00012345`). Se virar número, vira `12345` e o cruzamento entre os arquivos quebra silenciosamente.
**Por quê nada de razão social, nome fantasia, endereço, telefone, e-mail:** não são usados no agregado e são o tipo de dado que não queremos nem passando pela memória do servidor.

### `src/transformers/rfb.py`

```
MAPA_DIVISAO_SECAO = { "01".."03": "Agricultura...", "05".."09": "Indústrias extrativas",
                       "10".."33": "Indústrias de transformação", ... }
                       // nomes IDÊNTICOS aos do CEMPRE

SITUACAO_ATIVA   = "02"
SITUACAO_BAIXADA = "08"

função transformar_rfb(competencia, estab, empresas, simples):
    se estab vazio: retornar []

    juntar estab + empresas + simples pela chave cnpj_basico (junção à esquerda)
    setor = MAPA_DIVISAO_SECAO[2 primeiros dígitos do cnae_fiscal_principal]
        // CNAE fora do mapa → setor "Não classificado" + log de aviso

    marcar cada linha:
        é_ativa       = situacao == ativa
        abriu_no_mes  = data_inicio_atividade começa com competencia
        fechou_no_mes = situacao == baixada E data_situacao começa com competencia
        é_mei         = é_ativa E opcao_mei == "S"
        é_simples     = é_ativa E opcao_simples == "S" E não é_mei

    agrupar por setor e contar cada marcação
    adicionar linha "Total" (soma de todos os setores)
    retornar lista de dicionários { competencia, setor, ativas, aberturas, ... }


função validar_dados(registros):
    igual ao CEMPRE:
        competencia no formato AAAA-MM
        setor não vazio
        contagens inteiras e >= 0
        ativas_mei + ativas_simples <= ativas   // checagem de sanidade extra
    retornar (validos, invalidos)
```
⚠️ **Sobre "aberturas":** a RFB atualiza o cadastro com algum atraso, então a contagem do mês mais recente tende a vir **subestimada** e "crescer" no arquivo do mês seguinte. O upsert por `competencia + setor` não resolve isso sozinho → ver pendências.

### `src/schemas/rfb.py`

```
classe RfbBase:     competencia: str, setor: str,
                    ativas, aberturas, encerramentos, ativas_mei, ativas_simples: int
classe RfbCreate(RfbBase)
classe RfbResponse(RfbBase): id, criado_em, atualizado_em  (from_attributes=True)
```

### `src/database/models.py` → `RfbEmpresa`

```
__tablename__ = "rfb_empresas"
UniqueConstraint(competencia, setor, name="uq_competencia_setor_rfb")

id, competencia String(7) indexado, setor String(100) indexado,
ativas, aberturas, encerramentos, ativas_mei, ativas_simples: Integer, obrigatórios
criado_em, atualizado_em
```
**Por que aqui pode ser `NOT NULL` (diferente do CEMPRE):** a RFB não tem `X` nem `...` — se não tem empresa, é zero de verdade, porque nós mesmos contamos.

Depois: `alembic revision --autogenerate -m "cria tabela rfb_empresas"` + `alembic upgrade head`.

### `src/database/repositorio_rfb.py`

```
buscar_rfb(db, competencia?, setor?, incluir_total=True, skip, limit)
buscar_por_id_rfb(db, id)
contar_registros_rfb(db)
competencia_ja_processada(db, competencia) → existe alguma linha com essa competência?
upsert_rfb(db, registros) → ON CONFLICT (competencia, setor) DO UPDATE
```

### `src/services/atualizacao_rfb.py`

```
função atualizar_rfb(competencia=None, forcar=False):
    db = SessionLocal()
    tentar:
        competencia = competencia ou collector.descobrir_competencia_mais_recente()
        se competencia_ja_processada(competencia) e não forcar:
            logar "já processada, pulando"   // evita baixar GBs à toa
            retornar 0

        dados = collector.coletar(competencia)
        registros = transformar_rfb(*dados)
        validos, invalidos = validar_dados(registros)
        processados = upsert_rfb(db, validos)
        retornar processados
    se der erro: rollback, logar, relançar
    finalmente:
        apagar RFB_PASTA_TEMP inteira   // SEMPRE, mesmo com erro
        fechar db, logar tempo

se executado diretamente:
    aceitar competências pela linha de comando (ex.: 2026-08 2026-09)
    aceitar flag --forcar
```
🏀 **O `finalmente` é a regra de ouro:** dá certo ou dá errado, o vestiário é limpo no fim do jogo. Sem isso, uma falha no meio deixa gigabytes órfãos no disco.

### `src/api/routers/rfb.py`

```
GET "/"             → listar_rfb(competencia?, setor?, incluir_total?, skip, limit)
GET "/stats/resumo" → total de registros + competências disponíveis
GET "/{id}"         → um registro, 404 se não existir
// sem POST/DELETE: dado oficial, só o service grava (mesma decisão do CEMPRE)
```

### `src/api/app.py` (adição)

```
tentar:
    importar router rfb
    incluir com prefix="/rfb", tags=["RFB"]
se falhar:
    logar erro e seguir — API sobe sem /rfb
atualizar root() pra listar "/rfb"
```

### `src/scheduler/scheduler.py` (adição)

```
adicionar job "atualizacao_rfb":
    trigger = cron, dia = SCHEDULER_RFB_DIA, hora = SCHEDULER_RFB_HORA
    função = versão protegida de atualizar_rfb (try/except próprio)
    max_instances = 1    // um download de GBs não pode começar enquanto o anterior roda
```
**Por que mensal com data fixa:** mesmo raciocínio do CEMPRE (sobrevive a reinícios). **Por que não importa errar o dia:** se o arquivo do mês ainda não saiu, `competencia_ja_processada` pula; no mês seguinte ele pega.

---

## 📅 Cronograma — 3 semanas (3h/dia)

### 🗓️ Semana 1 (20–26/10) — Reconhecer o terreno 🔍
- [ ] Criar branch `feature/rfb`
- [ ] Baixar **uma** competência manualmente e abrir `Municipios`, um `Estabelecimentos` e um `Empresas`
- [ ] Confirmar o **código RFB de Joinville**, a ordem das colunas e os códigos de situação/porte (layout oficial em PDF da RFB)
- [ ] Medir: tamanho dos arquivos, tempo de download, quantos estabelecimentos Joinville tem
- [ ] Montar o mapa divisão CNAE → seção com os nomes do CEMPRE
- [ ] Adicionar a pasta temporária no `.gitignore`

### 🗓️ Semana 2 (27/10–02/11) — Pipeline de dados 🏭
- [ ] `settings.py` → `collectors/rfb.py` → `transformers/rfb.py` → `schemas/rfb.py`
- [ ] `RfbEmpresa` + migração Alembic
- [ ] `repositorio_rfb.py` → `services/atualizacao_rfb.py`
- [ ] Rodar o service à mão e conferir: soma das seções = linha Total? Ativas batem com a ordem de grandeza do CEMPRE (unidades locais)?

### 🗓️ Semana 3 (03–09/11) — Expor e fechar 🏁
- [ ] `routers/rfb.py` + registro protegido no `app.py`
- [ ] Job no `scheduler.py`
- [ ] Testes do router e do transformer (com CSV pequeno de exemplo, **sem** baixar da Receita)
- [ ] `docs/RFB_API.md` (irmão do `CEMPRE_API.md`) + `README.md` + `BACKLOG.md`
- [ ] Merge de `feature/rfb` pra `main`

```
Semana 1              Semana 2                           Semana 3
Baixar 1 mês    →     Collector → Transformer →      →   Router → Scheduler →
Confirmar layout      Model → Migração → Repo →          Testes → Docs → Merge
                      Service
```

---

## ⚖️ Decisões (pra você confirmar)

| Decisão | Recomendação | Motivo |
|---|---|---|
| 📦 Granularidade | **Agregado por competência + setor** | Leve, sem dado pessoal, cruza com CEMPRE |
| 👥 Sócios | **Fora** | LGPD, sem ganho pro objetivo |
| 🔢 Nulos | **`NOT NULL`, padrão 0** | Diferente do IBGE, aqui a contagem é nossa |
| 🚪 Escrita na API | **Nenhuma** | Igual ao CEMPRE |
| ⏱️ Agendamento | **Cron mensal + "já processada?"** | Resiste a reinício e não baixa GBs à toa |

---

## 🔮 Pendências e próximos passos

- 🕰️ **Histórico de aberturas:** o arquivo de um único mês já contém a data de abertura de todas as empresas (ativas e baixadas) → dá pra montar uma série histórica de aberturas por mês numa carga só. Avaliar depois de o básico funcionar.
- 🔁 **Atraso do cadastro:** reprocessar as últimas 2–3 competências a cada execução, pra corrigir as aberturas subestimadas do mês mais recente.
- 🏘️ **Quebra por bairro:** o Estabelecimentos tem bairro → possível dimensão futura (cuidado com bairros com poucas empresas, que podem identificar alguém).
- 🗂️ **Separar `models.py` por fonte** — já pendente desde o CEMPRE; com três fontes fica mais urgente.
