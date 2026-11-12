# BACKLOG - CAGED API

## Objetivo

Este documento registra a evolução técnica do projeto CAGED API.

O objetivo é organizar as funcionalidades, melhorias e decisões arquitetônicas adotadas durante o desenvolvimento, permitindo acompanhar a evolução do sistema de forma semelhante ao fluxo de trabalho de equipes profissionais de engenharia de software.

---

# Histórico de Desenvolvimento

## Sessão 01

### Concluído

- Estruturação inicial do projeto.
- Configuração do ambiente Python.
- Configuração do PostgreSQL.
- Integração inicial com FastAPI.
- Organização inicial da estrutura de diretórios.

---

## Sessão 02

### Concluído

- Organização da arquitetura em camadas.
- Separação entre Routers, Database, Collectors, Services e Transformers.
- Ajustes na inicialização da aplicação.
- Padronização da estrutura do projeto.

---

## Sessão 03

### Concluído

- Configuração da conexão com o banco de dados.
- Criação dos Models.
- Implementação do Repository.
- Primeiros testes de persistência dos dados.

---

## Sessão 04

### Concluído

- Implementação da API REST.
- Desenvolvimento do CRUD do CAGED.
- Integração com Swagger/OpenAPI.
- Ajustes nos endpoints e respostas HTTP.

---

## Sessão 05

### Concluído

- Implementação da estrutura BaseCollector.
- Criação do CagedCollector.
- Criação do IBGECollector.
- Organização da camada de coleta de dados.

---

## Sessão 06

### Concluído

- Implementação dos Transformers.
- Estruturação do pipeline de transformação.
- Validação dos registros.
- Preparação dos dados para persistência no banco.

---

## Sessão 07 (20/07/2026)

### Concluído

- Auditoria completa da arquitetura do projeto.
- Revisão técnica dos principais arquivos.
- Refatoração e padronização do código.
- Revisão dos Routers.
- Revisão dos Collectors.
- Revisão dos Transformers.
- Revisão do Repository.
- Revisão dos Models.
- Revisão dos Services.
- Padronização das responsabilidades entre as camadas.
- Definição da estratégia de evolução do projeto.
- Criação do BACKLOG.md.

### Decisões arquitetônicas

- O projeto deixa de ser tratado como um projeto universitário e passa a ser desenvolvido como um ecossistema profissional.
- Todas as decisões técnicas deverão possuir justificativa arquitetônica.
- Novas tecnologias serão adotadas apenas quando resolverem um problema real do projeto.
- O desenvolvimento seguirá uma evolução incremental, semelhante ao fluxo utilizado em equipes profissionais.

---

## Sessão 08 (04/08/2026)

### Concluído

- Implementação da coleta oficial dos dados do Novo CAGED via FTP do Ministério do Trabalho e Previdência (`ftp.mtps.gov.br/pdet/microdados/NOVO CAGED`).
- Download automático dos arquivos oficiais (CAGEDMOV, CAGEDFOR e CAGEDEXC) por competência, com cache local em `data/raw/caged`.
- Extração dos arquivos `.7z` oficiais (biblioteca `py7zr`).
- Correção do código do município de Joinville usado no filtro dos microdados (o arquivo oficial não usa o código IBGE completo, e sim o código sem dígito verificador).
- Correção do ano inicial de cobertura do coletor para 2020, início da série do Novo CAGED (o valor anterior correspondia ao CAGED antigo, de layout diferente).
- Implementação da agregação das movimentações individuais (uma linha por trabalhador) em saldo de admissões, demissões e saldo por competência e setor, combinando movimentações dentro do prazo, fora do prazo e exclusões — igual à metodologia oficial de apuração do Novo CAGED.
- Detecção automática da competência mais recente publicada, usada como padrão pelo coletor e pelo serviço de atualização quando nenhuma competência é informada.
- Ajuste do intervalo padrão do Scheduler (antes 30 segundos, incompatível com uma fonte de dados publicada mensalmente) para verificação diária.
- Validação do pipeline completo (Collector → Transformer → Repository → PostgreSQL) com dados reais da competência 2026/06, incluindo teste de idempotência do upsert.

## Sessão 09 (01/10/2026 – 15/10/2026) — Integração do CEMPRE (IBGE)

### Concluído

- Integração do CEMPRE (Cadastro Central de Empresas, IBGE) como segunda fonte de dados, no mesmo servidor do CAGED.
- Coleta via API do SIDRA, tabela 9510 (CEMPRE por seção da CNAE 2.0), com as variáveis unidades locais (706), pessoal ocupado (707) e salário médio mensal (10143).
- Transformer com pivot do formato "esticado" do SIDRA (uma linha por variável) para o formato "achatado" do projeto (uma linha por ano + setor).
- Tratamento dos símbolos especiais do IBGE: `-` (zero absoluto) vira 0; `X` (sigiloso), `...` (não disponível) e `..` (não se aplica) viram NULL.
- Tabela `cempre_emprego` criada via Alembic (primeiro uso de migrações no projeto), com uma segunda migração liberando NULL nas colunas numéricas.
- Repositório próprio (`repositorio_cempre.py`) com upsert idempotente pela chave ano + setor.
- Service de atualização com carga histórica pela linha de comando (`python -m src.services.atualizacao_cempre 2022 2023`), processando cada ano de forma independente.
- Router somente leitura em `/cempre` (listagem com filtros, resumo e busca por ID), incluindo o filtro `incluir_total` para evitar soma dobrada com a linha "Total".
- Registro protegido do router no `app.py`: se o CEMPRE falhar, a API sobe sem a rota `/cempre` e o CAGED segue funcionando.
- Job mensal do CEMPRE no scheduler, com gatilho de data fixa (`cron`, dia 1º às 3h) e tratamento de erro próprio, isolado do job do CAGED.
- Testes do router e do transformer (18 testes passando).
- Validação do pipeline completo com dados reais de 2022, 2023 e 2024, incluindo teste de idempotência do upsert e teste do downgrade da migração.

### Decisões arquitetônicas

- Cada fonte de dados fica isolada nos próprios arquivos (collector, transformer, repositório, service, router), no mesmo servidor, para que a falha de uma não derrube a outra.
- Valores não divulgados pelo IBGE são gravados como NULL, e não como 0, para não confundir "não sabemos" com "zero".
- Rotas do CEMPRE são somente leitura: o dado é oficial e apenas o service grava no banco.
- Agendamentos de fontes com publicação esparsa usam data fixa no calendário, e não intervalo, porque o intervalo recomeça a cada reinício do servidor.

## Sessão 10 (20/10/2026 – 10/11/2026) — Integração da RFB (CNPJ)

### Concluído

- Integração da base de CNPJ da Receita Federal como terceira fonte de dados, no mesmo servidor do CAGED e do CEMPRE.
- Coleta via WebDAV do servidor de arquivos da RFB, com descoberta automática da competência mais recente (`PROPFIND`).
- Leitura dos arquivos Estabelecimentos, Empresas e Simples em blocos, filtrando Joinville (código RFB `8179`) sem carregar os arquivos inteiros na memória.
- Download com retry e timeout, validação de tamanho e assinatura do zip antes da leitura, e pasta temporária apagada ao final de cada execução.
- Transformer com mapa divisão da CNAE → seção, usando os mesmos nomes de setor do CEMPRE, e agregação em ativas, aberturas, encerramentos, ativas MEI e ativas Simples.
- Tabela `rfb_empresas` criada via Alembic, com chave única competência + setor.
- Repositório próprio (`repositorio_rfb.py`) com upsert idempotente e checagem de competência já processada.
- Service de atualização com competências e flag `--forcar` pela linha de comando.
- Router somente leitura em `/rfb` (listagem com filtros, resumo com competências disponíveis e busca por ID), com registro protegido no `app.py`.
- Job mensal da RFB no scheduler (`cron`, dia 15 às 4h), com tratamento de erro próprio e `max_instances=1`.
- Documentação da fonte em `docs/RFB_API.md`.

### Decisões arquitetônicas

- A RFB é gravada agregada por competência + setor, e não empresa por empresa: mantém o padrão do projeto e evita armazenar dados pessoais.
- O arquivo de sócios não é baixado, por risco de LGPD e por não agregar ao objetivo do projeto.
- As colunas numéricas da RFB são `NOT NULL` com padrão 0: a contagem é feita pelo próprio projeto, então não existe valor sigiloso ou indisponível.
- Competências já processadas são puladas, para não baixar vários GB sem necessidade.

## Sessão 11 (11/11/2026) — Validação ponta a ponta da v0.4

### Concluído

- Execução da suíte de testes automáticos (`uv run pytest -q`): 18 testes passando.
- Teste manual da API pelo Swagger (`/docs`) com o PostgreSQL local: `/health` respondendo 200 com o banco conectado e as quatro rotas (`/caged`, `/ibge`, `/cempre`, `/rfb`) registradas.
- Validação do CAGED (`/caged/stats/resumo`): 118 registros no banco.
- Validação do CEMPRE (`/cempre/stats/resumo` e `/cempre/`): 66 registros (3 anos x 22 linhas); filtro por `ano` funcionando; `incluir_total=false` removendo a linha "Total"; soma dos setores de 2022 igual à linha "Total" (44.425 unidades locais).
- Primeira carga real da RFB no banco local (competência 2026-10), em cerca de 92 minutos: 302.338 estabelecimentos de Joinville filtrados dos arquivos nacionais, 293.558 CNPJs básicos, todos encontrados no arquivo Empresas, e 225.457 registros no Simples.
- Retry do download validado na prática: a conexão com a RFB caiu na primeira tentativa do `Estabelecimentos0.zip` e a segunda tentativa concluiu o arquivo.
- Pasta temporária `data/rfb_temp` apagada ao final da execução, como planejado.
- Validação da RFB na API (`/rfb/stats/resumo` e `/rfb/`): 21 registros (20 setores + Total); soma dos setores igual à linha "Total" em todas as colunas (134.732 ativas, 781 aberturas, 478 encerramentos, 68.936 MEI, 35.702 Simples).
- Conferência de coerência dos dados: setores K (financeiro) e L (imobiliário) sem MEI, o que está de acordo com a legislação do MEI; setor U ausente por não ter empresas em Joinville.

### Problemas encontrados

- O retry do download da RFB recomeça o arquivo do zero quando a conexão cai (cerca de 8 minutos perdidos no `Estabelecimentos0.zip`, de 2,2 GB).
- O `criado_em` dos registros da RFB marca o início da execução (14:00) e não o momento da gravação (15:32): a sessão do banco fica com uma transação aberta durante todo o download.
- O router `/ibge` é um placeholder: `/ibge/municipios` devolve Joinville fixo no código e `/ibge/` responde "Em desenvolvimento". Os dados reais do IBGE entram pelo CEMPRE.
- Na listagem do CEMPRE, a linha "Total" aparece entre os setores T e U, por causa da ordenação alfabética.
## Sessão 12 (12/11/2026) — Testes no Swagger e correção do CAGED

### Concluído

- Bateria de testes manuais no Swagger das três fontes:
    - RFB: 8 de 8 cenários aprovados (`stats/resumo`, `incluir_total` false/true, filtro por setor, competência inválida → 422, `limit=0` barrado, id inexistente → 404, id 21 → linha "Total").
    - CEMPRE: `stats/resumo` (66 registros), filtro por setor e id inexistente → 404.
    - CAGED: `stats/resumo` e listagem.
- Cruzamento RFB x CEMPRE na indústria: 13.318 ativas na RFB, sendo 8.518 MEI; sem MEI restam cerca de 4.800, próximo das 3.847 unidades locais do CEMPRE 2024 (as duas fontes são coerentes).
- Correção do bug de sobrescrita do CAGED (branch `fix/caged-sobrescrita-competencias`):
    - Causa raiz: o collector agregava MOV + FOR + EXC pela `competênciamov`; declarações atrasadas de meses anteriores (FOR/EXC) viravam linhas desses meses, e o upsert (`ON CONFLICT DO UPDATE`) substituía os valores completos já gravados por valores parciais.
    - Teste escrito antes da correção (`tests/test_collector_caged.py`), falhando (vermelho) e depois passando (verde).
    - `_agregar_movimentacoes` passou a receber a competência e a descartar registros de outras competências.
    - Backup da tabela em `caged_backup_20261112` (118 linhas) antes da limpeza.
    - Recarga de 202605 (18 setores, 436 registros FOR/EXC descartados) e 202606 (19 setores, 370 descartados).
    - Validação: 37 registros; indústria em 202605 com 3.724 admissões (antes 13); `admissoes − demissoes = saldo` em todas as linhas.
- Suíte de testes: 20 testes passando.

### Problemas encontrados

- Registro de teste manual no CAGED (`setor = "TECNOLOGIA"`, competência 202608), removido na limpeza.
- Listagens do CAGED e do CEMPRE sem `order_by` (os anos do CEMPRE vieram como 2024, 2022, 2023).
- A rota `/caged` não valida o formato da competência (AAAAMM), diferente da `/rfb`, que devolve 422.
- O `stats/resumo` do CAGED e do CEMPRE não lista as competências/anos disponíveis, diferente da RFB.

### Backlog Atual

## Prioridade P0 (Versão 1.0)

- [x] Implementar coleta oficial dos dados do CAGED.
- [x] Implementar download automático dos arquivos.
- [x] Processar os arquivos oficiais.
- [x] Integrar Collector → Transformer → Repository.
- [x] Finalizar o fluxo automático do Scheduler.
- [x] Validar todo o pipeline de atualização.
- [x] Concluir a integração prática com o IBGE (CEMPRE).
- [x] Disponibilizar o CEMPRE na API (`/cempre`).
- [x] Agendar a atualização automática do CEMPRE.
- [x] Concluir a integração prática com a RFB (CNPJ).
- [x] Disponibilizar a RFB na API (`/rfb`).
- [x] Agendar a atualização automática da RFB.
- [ ] Revisar configurações da aplicação.

---

## Prioridade P1

- [ ] Melhorar tratamento de erros.
- [ ] Melhorar documentação técnica.
- [ ] Revisar desempenho das consultas.
- [ ] Revisar tratamento de exceções da API.
- [ ] Avaliar a carga dos anos do CEMPRE anteriores a 2022 (outras tabelas do SIDRA, possível mudança de metodologia).
- [ ] Separar `models.py` por fonte de dados (`models_caged.py` / `models_cempre.py` / `models_rfb.py`).
- [ ] Mover o `RFB_SHARE_TOKEN` do `settings.py` para o `.env`.
- [ ] Avaliar reprocessar as últimas 2–3 competências da RFB a cada execução (aberturas do mês mais recente vêm subestimadas).
- [ ] Avaliar a carga da série histórica de aberturas da RFB a partir de um único arquivo mensal.
- [ ] Criar migração para o índice `ix_caged_movimentacao_id`, que existe no model mas não no banco.
- [ ] Fazer o retry do download da RFB continuar de onde parou (cabeçalho HTTP `Range`), em vez de recomeçar o arquivo do zero.
- [ ] CAGED: tratar FOR/EXC nos meses de origem (somar FOR, descontar EXC) em vez de descartá-los.
- [ ] Adicionar `order_by` nas listagens do CAGED (competência, setor) e do CEMPRE (ano, setor).
- [ ] Validar o formato da competência na rota `/caged` (hoje aceita qualquer texto).
- [ ] Padronizar o `stats/resumo` das três fontes (listar competências/anos disponíveis).
- [ ] Apagar a tabela `caged_backup_20261112` após uma semana sem problemas.
---

## Prioridade P2

- [ ] Implementar testes unitários.
- [ ] Implementar testes de integração.
- [ ] Configurar Docker.
- [ ] Configurar Docker Compose.
- [ ] Implementar GitHub Actions.
- [x] Implementar Alembic.
- [ ] Adicionar Logging estruturado.
- [ ] Implementar Health Check.
- [ ] Configurar Observabilidade.
- [ ] Planejar Deploy.
- [ ] Avaliar troca de `httpx` por `httpx2` (aviso de depreciação do Starlette nos testes).
- [ ] Adicionar teste para a leitura dos anos pela linha de comando no service do CEMPRE.
- [ ] Criar testes do transformer e do router da RFB (`test_transformer_rfb.py`, `test_rfb_router.py`), com CSV pequeno de exemplo.
- [ ] Abrir a sessão do banco no service da RFB só na hora de gravar, para não manter uma transação aberta durante o download.
- [ ] Implementar o router `/ibge` de verdade ou removê-lo (hoje devolve Joinville fixo no código).
- [ ] Ordenar a listagem do CEMPRE com a linha "Total" sempre no fim.
- [ ] Trocar `datetime.utcfromtimestamp()` em `src/core/logging.py` por `datetime.fromtimestamp(..., datetime.UTC)` (aviso de depreciação nos testes).

---

# Objetivo Final

Construir um ecossistema de engenharia de software que represente um sistema profissional, aplicando boas práticas de arquitetura, qualidade de código e escalabilidade, servindo como portfólio para oportunidades em empresas nacionais e internacionais.

# Changelog

| Data | Versão | Descrição |
|------|---------|-----------|
| 20/07/2026 | v0.1 | Conclusão da primeira auditoria arquitetônica. |
| 04/08/2026 | v0.2 | Coleta oficial do Novo CAGED implementada e validada com dados reais. |
| 15/10/2026 | v0.3 | Integração do CEMPRE (IBGE) como segunda fonte de dados, isolada do CAGED. |
| 10/11/2026 | v0.4 | Integração da RFB (CNPJ da Receita Federal) como terceira fonte de dados, isolada do CAGED e do CEMPRE. |
| 11/11/2026 | v0.4.1 | Validação ponta a ponta das três fontes (CAGED, CEMPRE e RFB) com dados reais, incluindo a primeira carga da RFB. |
| 12/11/2026 | v0.4.2 | Correção do CAGED: declarações FOR/EXC sobrescreviam meses já carregados; recarga de 202605 e 202606 e testes do collector. |