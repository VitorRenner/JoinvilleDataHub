# 🚀 Do "copiar pasta" pro Git — Guia Rápido

## 😵 O que tá rolando hoje

Você copia a pasta inteira (`caged_api_1` → `caged_api_15`) toda vez que muda algo grande.

**Resultado:** configs velhas e segredos vão "de carona" de uma cópia pra outra — foi exatamente isso que causou o bug de conexão que caçamos hoje! 🐛

| ❌ Problema | 💥 Consequência |
|---|---|
| Sem histórico real | Não dá pra comparar v10 com v15 |
| Lixo se acumula | Configs e segredos se espalham |
| Sem "desfazer" preciso | Só copiando manualmente |
| Disco lotado | 15 pastas inteiras = muito espaço |

## ✅ A solução: Git

Em vez de duplicar a pasta → você salva só **o que mudou**, com histórico completo pra sempre. 🧠

### 🧩 4 conceitos, rapidinho

📁 **Repositório** — `git init` uma vez na pasta, pronto, o Git passa a vigiar tudo

📸 **Commit** — um "checkpoint" com mensagem, tipo salvar o jogo

🌿 **Branch** — uma linha paralela pra testar mudanças grandes sem bagunçar o que já funciona

🙈 **.gitignore** — lista de arquivos que NUNCA entram no histórico (segredos, configs pessoais)

## 🛠️ Migrando seu projeto (passo a passo)

**1️⃣ Escolha o ponto de partida**
Use a `caged_api_15` (a mais atual). Esquece as outras 14 por enquanto.

**2️⃣ Confira se tem Git**
```
git --version
```

**3️⃣ Crie o `.gitignore`** (⚠️ passo mais importante!)
```
.env
.env.local
.claude/settings.local.json
.idea/
venv/
__pycache__/
node_modules/
.DS_Store
```

**4️⃣ Crie um `.env.example`** (versão segura, sem senha de verdade)
```
DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/caged_db
OPENAI_API_KEY=sua-chave-aqui
```

**5️⃣ Primeiro commit** 🎉
```
git init
git add .
git commit -m "Versão inicial: consolidação da v15"
```

**6️⃣ (Bônus) Backup na nuvem**
Crie um repositório privado no [GitHub](https://github.com) e conecte com `git remote add origin ...` + `git push`

**7️⃣ Arquive as pastas antigas** 📦
Mova `caged_api_1` a `14` pra um HD externo ou lugar de arquivo morto — não precisa mais delas no dia a dia

## 🔁 Fluxo do dia a dia

**Mudança pequena:**
```
git add .
git commit -m "fix: corrige X"
```

**Mudança grande:**
```
git checkout -b feature/nome-da-mudanca
# ...trabalha normal...
git checkout main
git merge feature/nome-da-mudanca
```

**Ver histórico:**
```
git log --oneline
```

**Voltar atrás se quebrar:**
```
git checkout <hash-do-commit> -- .
```

## 🏷️ Prefixos de commit (cola aqui)

🆕 `feat:` — funcionalidade nova
🐛 `fix:` — correção de bug
♻️ `refactor:` — reorganizar sem mudar comportamento
📝 `docs:` — documentação
🔧 `chore:` — manutenção/dependências

## 💡 Resumo em 1 frase

**Pare de copiar a pasta inteira. Comece a registrar só o que muda.** O `.gitignore` certo já teria evitado o bug de hoje. 🎯
