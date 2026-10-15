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
- Download automático dos arquivos oficiais (CAGEDMOV, CAGEDFOR e CAGEDEXC) por competência, com cache local em `data/raw/caged/`.
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
- [ ] Revisar configurações da aplicação.

---

## Prioridade P1

- [ ] Melhorar tratamento de erros.
- [ ] Melhorar documentação técnica.
- [ ] Revisar desempenho das consultas.
- [ ] Revisar tratamento de exceções da API.
- [ ] Avaliar a carga dos anos do CEMPRE anteriores a 2022 (outras tabelas do SIDRA, possível mudança de metodologia).
- [ ] Separar `models.py` por fonte de dados (`models_caged.py` / `models_cempre.py`).
- [ ] Criar migração para o índice `ix_caged_movimentacao_id`, que existe no model mas não no banco.

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

---

# Objetivo Final

Construir um ecossistema de engenharia de software que represente um sistema profissional, aplicando boas práticas de arquitetura, qualidade de código e escalabilidade, servindo como portfólio para oportunidades em empresas nacionais e internacionais.

# Changelog

| Data | Versão | Descrição |
|------|---------|-----------|
| 20/07/2026 | v0.1 | Conclusão da primeira auditoria arquitetônica. |
| 04/08/2026 | v0.2 | Coleta oficial do Novo CAGED implementada e validada com dados reais. |
| 15/10/2026 | v0.3 | Integração do CEMPRE (IBGE) como segunda fonte de dados, isolada do CAGED. |
