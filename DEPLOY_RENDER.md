# 🚀 GUIA COMPLETO — Deploy do Nivelis no Render

## Sequência

```
1. Preparar arquivos locais (5 min)
2. Testar localmente (10 min)
3. Criar repositório no GitHub (10 min)
4. Criar conta no Render (5 min)
5. Conectar e deployar (10 min)
6. Configurar variáveis de ambiente (10 min)
7. Testar em produção (5 min)
```

**Tempo total:** ~55 minutos
**Custo:** R$ 0,00 (free tier permanente)

---

## 📦 Arquivos novos na pasta

Coloque na pasta `K:\nivelis-teste\Nivelis-Api\`:

```
✅ nivelis_api.py       → arquivo principal (wrapper)
✅ simulados_api.py     → atualizado (Firebase via env)
✅ questoes_api.py      → atualizado (Firebase via env)
✅ requirements.txt     → dependências Python
✅ Procfile             → comando de start
✅ render.yaml          → config do Render
✅ .gitignore           → o que NÃO subir pro Git
✅ .env.example         → modelo do .env
```

---

## ✅ FASE 1 — Testar Localmente PRIMEIRO

**Antes de subir pra Render, testa local.** Pra garantir que o wrapper funciona.

```bash
cd K:\nivelis-teste\Nivelis-Api
uvicorn nivelis_api:app --host 0.0.0.0 --port 8000
```

Esperado no terminal:
```
[FIREBASE] Usando arquivo chave-firebase.json
[GEMINI] Modelo: gemini-2.5-flash-lite | ...
============================================================
  🚀 NIVELIS API v3.0.0
============================================================
  Modo: DESENVOLVIMENTO
  Simulados → /v1/simulados/*
  Questões  → /v1/questoes/*
  Swagger   → /docs
============================================================
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Testes locais:

1. **Página inicial:** `http://127.0.0.1:8000/`  → redireciona pro /docs
2. **Swagger:** `http://127.0.0.1:8000/docs`
3. **Health check:** `http://127.0.0.1:8000/health`
4. **Sub-API simulados:** `http://127.0.0.1:8000/v1/simulados/livros`
5. **Sub-API questoes:** `http://127.0.0.1:8000/v1/questoes/materias`

Se TUDO funcionar, **mata o uvicorn** (Ctrl+C) e vai pra próxima fase.

---

## 🐙 FASE 2 — GitHub

### 1. Criar conta (se não tiver)
- Acessa github.com
- Cadastra com email

### 2. Criar repositório PRIVADO
- Botão **"New repository"**
- Nome: `nivelis-api`
- **Marca "Private"** (importante! sua chave está no código de teste)
- NÃO inicialize com README, .gitignore ou licença
- Clica em **"Create repository"**

### 3. Subir o código

No CMD da pasta `Nivelis-Api`:

```bash
git init
git add .
git commit -m "Versão inicial do Nivelis API"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/nivelis-api.git
git push -u origin main
```

⚠️ **Substitui `SEU_USUARIO` pelo seu nome do GitHub!**

### 4. Confirma que o .gitignore funcionou

No GitHub, abre o repositório e verifica que **NÃO ESTÁ LÁ**:
- ❌ `chave-firebase.json` ou qualquer arquivo de chave
- ❌ `.env`
- ❌ `__pycache__/`

Se algum desses arquivos estiver no GitHub:
1. **PARE TUDO**
2. Apague o repositório
3. Cria de novo
4. Verifica o .gitignore antes de subir

---

## 🚀 FASE 3 — Render

### 1. Criar conta
- Acessa render.com
- Botão "Get Started" (em cima)
- "Sign in with GitHub" (facilita)
- Autoriza o Render no GitHub

### 2. Novo Web Service
- Dashboard → **"New +"** → **"Web Service"**
- "Connect a repository" → autoriza Render no GitHub
- Acha o `nivelis-api` → "Connect"

### 3. Configurar o serviço

**Name:** `nivelis-api`
**Region:** `Oregon (US West)` — mais barata
**Branch:** `main`
**Runtime:** `Python 3`
**Build Command:** `pip install -r requirements.txt`
**Start Command:** `uvicorn nivelis_api:app --host 0.0.0.0 --port $PORT`
**Plan:** **Free** ⭐

⚠️ Se o Render detectar o `render.yaml`, ele faz tudo isso sozinho.

### 4. Variáveis de ambiente

Antes de clicar em "Create Web Service", scrolla até **"Environment Variables"** e adiciona:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | (cola sua chave Gemini, mesma do .env local) |
| `FIREBASE_CREDENTIALS` | (cola o conteúdo INTEIRO do `chave-firebase.json`) |
| `DESABILITAR_DETALHES_ERRO` | `true` |
| `PYTHON_VERSION` | `3.11.9` |

### Como pegar o conteúdo do FIREBASE_CREDENTIALS:

1. Abre o `chave-firebase.json` no Notepad
2. Copia TUDO (Ctrl+A → Ctrl+C)
3. Cola no campo "Value" do Render

⚠️ O JSON inteiro deve estar em **uma única linha ou várias** — não tem problema. Só não adicione espaços ou quebras a mais.

### 5. Clicar em "Create Web Service"

Render vai:
1. Clonar o repositório
2. Instalar dependências
3. Iniciar o `uvicorn`

⏳ **Demora ~5-10 minutos** na primeira vez.

---

## ✅ FASE 4 — Validar em produção

### URL pública

Render vai te dar uma URL tipo:
```
https://nivelis-api.onrender.com
```

### Testes:

1. **Página inicial:** `https://nivelis-api.onrender.com/` → redireciona /docs
2. **Health:** `https://nivelis-api.onrender.com/health`
3. **Info:** `https://nivelis-api.onrender.com/info`
4. **Swagger:** `https://nivelis-api.onrender.com/docs`
5. **Listar livros:** `https://nivelis-api.onrender.com/v1/simulados/livros`

Se aparecer o Hazzan → **🎉 DEPLOY COMPLETO!**

---

## ⚠️ Coisas pra esperar

### 1. Primeira requisição é LENTA
30-50 segundos pra acordar. Depois fica rápido.

### 2. Adormece após 15 minutos sem uso
Comportamento normal do free tier.

### 3. Cota Gemini compartilhada
Sua chave Gemini é a MESMA do local. Cuidado pra não estourar.

### 4. Logs do Render
Dashboard → seu serviço → aba "Logs"
Acompanha em tempo real o que está acontecendo.

---

## 🐛 Troubleshooting

### Build falhou:
- Confere se `requirements.txt` está no repositório
- Vê o log do Render pra identificar qual lib falhou

### Serviço não inicia:
- Confere as variáveis de ambiente
- O `FIREBASE_CREDENTIALS` está com JSON válido?
- A `GEMINI_API_KEY` está preenchida?

### Erro 500 em todas as rotas:
- Provavelmente Firebase não conectou
- Confere o log pra ver a mensagem exata

### URLs antigas não funcionam:
- Lembra que mudaram! `/livros` virou `/v1/simulados/livros`
- Vai precisar atualizar no app React Native

---

## 📱 Próximo passo: app React Native

No app, mudar a base URL:

```javascript
// ANTES
const API_BASE = "http://192.168.x.x:8000";

// DEPOIS
const API_BASE = "https://nivelis-api.onrender.com/v1/simulados";
// ou
const API_BASE = "https://nivelis-api.onrender.com/v1/questoes";
```

E ajustar os caminhos das rotas conforme o módulo.

---

## 💰 Custos esperados

- **Render:** R$ 0 (free tier permanente)
- **Firebase:** R$ 0 (free tier do Spark)
- **Gemini:** R$ 0 (free tier com cota diária)

**Total: R$ 0,00/mês** 🎉

---

## 🔄 Quando precisar atualizar o código

```bash
# Na pasta local
git add .
git commit -m "Descrição da mudança"
git push
```

Render **detecta o push automaticamente** e faz redeploy em ~3-5 minutos.

---

## 🆘 Se algo der MUITO errado

1. **Reverter para versão anterior:**
   - Dashboard → Deploy → "Manual Deploy" → escolhe um deploy antigo

2. **Deletar tudo e começar de novo:**
   - Settings → Delete Service
   - Cria de novo

3. **Pedir ajuda no Claude:**
   - Cola o log do Render
   - Cola o que você fez
   - Pede orientação
