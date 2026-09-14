# 📊 Documentação — Nova Fonte de Dados: CEMPRE (IBGE)

> Este documento explica o que é o CEMPRE, por que ele está sendo integrado a este servidor e como o dado vai fluir dentro da arquitetura já existente.

---

## 🧭 O que é o CEMPRE

O **CEMPRE** (Cadastro Central de Empresas) é uma pesquisa anual do IBGE. Ele mostra, por município, quantas empresas existem, quantas pessoas estão empregadas, quanto se paga em salários — tudo organizado por setor de atividade.

Ele entra como uma **segunda fonte de dados**, ao lado do CAGED, dentro do mesmo servidor.

---

## 🎬 CAGED vs 📸 CEMPRE — por que os dois juntos

| | 🎬 CAGED | 📸 CEMPRE |
|---|---|---|
| **O que mostra** | O movimento: quem foi admitido, quem foi desligado | O retrato: quantas empresas e empregos existem, parado no tempo |
| **Frequência** | Mensal | Anual |
| **Analogia** | Um filme — mostra a ação acontecendo, mês a mês | Uma fotografia — mostra o cenário completo, uma vez por ano |

➡️ Um mostra o **fluxo**, o outro mostra o **estoque**. Juntos, dão o quadro completo do mercado de trabalho de Joinville — não faz sentido ter um sem o outro.

---

## 🏭 Como o dado vai fluir (linha de produção)

```
🌐 API do IBGE (SIDRA)
        ↓
🤖 Collector        → busca a matéria-prima bruta na fonte oficial
        ↓
🔄 Transformer      → limpa, padroniza e valida o material coletado
        ↓
🗄️ Database         → guarda o resultado já pronto, organizado
        ↓
🚪 API (Router)     → disponibiliza o dado pronto pra quem pedir
        ↓
📱 Site Nexus       → consome e exibe o dado final
```

Cada seta é uma etapa de uma esteira: o dado bruto entra de um lado, e só sai pronto pro consumo do outro lado depois de passar por todas as estações.

---

## 🗂️ Onde cada peça vai morar no projeto

| Camada | Arquivo | Status | O que faz |
|---|---|---|---|
| 🤖 Coleta | `src/collectors/cempre.py` | 🆕 novo | Busca os dados na API do SIDRA (IBGE) |
| 🔄 Transformação | `src/transformers/cempre.py` | 🆕 novo | Padroniza colunas e valida os registros |
| 📐 Contrato de dados | `src/schemas/cempre.py` | 🆕 novo | Define o formato dos dados (Pydantic) |
| 🗄️ Modelo do banco | `src/database/models.py` | ✏️ editado | Adiciona a tabela `CempreEmprego` |
| 📦 Acesso ao banco | `src/database/repositorio.py` | ✏️ editado | Funções de busca/inserção/remoção do CEMPRE |
| ⚙️ Orquestração | `src/services/atualizacao_cempre.py` | 🆕 novo | Junta coleta → transformação → gravação |
| 🚪 Endpoints | `src/api/routers/cempre.py` | 🆕 novo | Expõe o CEMPRE como rota `/cempre` |
| 🔌 Registro na API | `src/api/app.py` | ✏️ editado | Liga o novo router à aplicação |
| ⏱️ Agendamento | `src/scheduler/scheduler.py` | ✏️ editado | Cria a rotina automática de atualização |
| 🔧 Configurações | `src/core/settings.py` | ✏️ editado | Guarda a URL da fonte e o intervalo do agendamento |
| 🧱 Migração do banco | `alembic/versions/` | 🆕 novo | Cria a tabela nova de forma controlada |

**Legenda:** 🆕 arquivo novo · ✏️ arquivo já existente, só ganha um trecho a mais.

---

## 🏢 Um servidor novo, ou o mesmo servidor?

✅ **Decisão: o mesmo servidor.**

Pensa assim: é o mesmo prédio, só uma sala nova sendo aberta dentro dele — mesma recepção (API), mesmo estoque (banco de dados), mesma equipe de manutenção (deploy). Criar um servidor separado significaria duplicar tudo isso (outro Docker, outro pipeline, outro monitoramento) sem nenhum ganho real hoje.

---

## 🧩 Fonte de dados escolhida

- 🌐 **SIDRA (IBGE)** — tabela **9509** (unidades locais, empresas atuantes, pessoal ocupado e salários, disponível por município)
- 📍 **Código do município:** `4209102` (Joinville)
- ⚠️ *Pendente:* confirmar o nome exato de cada variável da tabela na hora de implementar o Collector — o número da tabela muda de vez em quando nas edições do IBGE.

---

## ⚖️ Decisões em aberto

- 🧱 **Criação da tabela:** via **Alembic** (recomendado, já está configurado no projeto e nunca foi usado) ou repetir o script `criar_tabelas.py`?
- ⏱️ **Intervalo do agendamento:** como o CEMPRE só atualiza uma vez por ano, o intervalo diário usado pelo CAGED não se aplica aqui — precisa de um intervalo próprio (ex.: checagem mensal).

---

## ✅ Próximos passos

1. 🔎 Confirmar a tabela e as variáveis exatas no SIDRA
2. 🤖 Implementar o `collector`
3. 🔄 Implementar `transformer` + `schema`
4. 🗄️ Criar o modelo da tabela + migração
5. 📦 Implementar `repository` + `service`
6. 🚪 Criar o `router` e registrar na aplicação
7. ⏱️ Configurar o agendamento
8. 🧪 Testar o fluxo completo, ponta a ponta
