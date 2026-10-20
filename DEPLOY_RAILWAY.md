# 🚀 Guia de Deploy — Nivelis API

Guia passo-a-passo para colocar a API online usando Railway + GitHub.

> ⚠️ **Antes de começar:** confirme que sua API funciona 100% localmente.
> Testar em produção é caro (em tempo e dinheiro).

---

## 📋 Sumário

1. Preparar o código para produção
2. Subir o código no GitHub
3. Criar conta Railway e fazer deploy
4. Configurar variáveis de ambiente
5. Configurar Firebase para produção
6. Testar a API em produção
7. Compartilhar com o time do app
8. Manutenção e monitoramento

---

## 📦 Parte 1 — Preparar o código

### 1.1 Criar `requirements.txt`

Na pasta `Nivelis-Api`, cria um arquivo `requirements.txt` com:

```
fastapi
uvicorn[standard]
requests
firebase-admin
google-generativeai
pdfplumber
pymupdf
pillow
python-dotenv
playwright
```

Esse arquivo diz pro Railway quais pacotes Python instalar.

### 1.2 Criar `Procfile`

Cria um arquivo chamado **`Procfile`** (sem extensão) com:

```
web: uvicorn simulados_api:app --host 0.0.0.0 --port $PORT
```

⚠️ A variável `$PORT` é fornecida pelo Railway automaticamente. **Não substitua por 8000.**

### 1.3 Decidir sobre `questoes_api.py`

Você tem **2 APIs separadas** (porta 8000 e 8001). O Railway só permite **1 processo web por serviço**. Opções:

**Opção A — Mesclar as duas em uma só** (recomendado)
**Opção B — Criar 2 serviços Railway** (mais caro, ~$10/mês)
**Opção C — Deixar a `questoes_api.py` só localmente** (alguns endpoints inacessíveis)

Se for Opção A, eu te ajudo a mesclar quando for hora.

### 1.4 Criar `.gitignore` (importante!)

Se ainda não existir, cria com:

```
.env
chave-firebase.json
__pycache__/
*.pyc
.venv/
venv/
livros/
*.pdf
```

⚠️ **CRÍTICO**: `chave-firebase.json` e `.env` **NÃO podem ir pro GitHub**. São credenciais.

### 1.5 Criar `Dockerfile` (para Playwright)

Se quiser que o fallback do Playwright funcione em produção, cria um arquivo `Dockerfile`:

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8000

CMD uvicorn simulados_api:app --host 0.0.0.0 --port ${PORT:-8000}
```

> Se preferir deploy mais simples sem Playwright, pule este passo.
> A função `buscar_url_inep` vai falhar silenciosamente (retorna None).

---

## 🐙 Parte 2 — Subir no GitHub

### 2.1 Criar repositório

1. Acessa https://github.com/new
2. Nome: `nivelis-api` (ou outro)
3. **PRIVADO** (importante)
4. **Não marca** "Add a README" (vamos subir o nosso código)
5. Clica **Create repository**

### 2.2 Inicializar Git localmente

Abre o CMD na pasta `Nivelis-Api`:

```bash
cd K:\nivelis-teste\Nivelis-Api
git init
git add .
git status
```

### 2.3 Verificar o que vai subir

⚠️ **CRÍTICO**: confere que `.env` e `chave-firebase.json` **NÃO** estão na lista.

Se aparecerem, é porque o `.gitignore` não está correto. Para de fazer e corrige.

### 2.4 Fazer o primeiro commit

```bash
git commit -m "Versão inicial da API Nivelis"
```

### 2.5 Conectar com GitHub

Volte na página do repositório no GitHub e copie o comando que aparece (algo tipo):

```bash
git remote add origin https://github.com/SEU_USUARIO/nivelis-api.git
git branch -M main
git push -u origin main
```

Cola no CMD e executa. Vai pedir login do GitHub (use token de acesso pessoal, não senha).

### 2.6 Confirmar no GitHub

Atualiza a página do repositório. Você deve ver todos os arquivos `.py` lá. **Confere que `.env` e `chave-firebase.json` não aparecem.**

---

## 🚂 Parte 3 — Deploy no Railway

### 3.1 Criar conta

1. Acessa https://railway.app
2. **Login com GitHub** (já vincula tudo)
3. Aceita os termos

### 3.2 Plano

- Plano **Hobby**: $5/mês, dá pra tudo que vc precisa
- **Trial**: $5 grátis no primeiro mês

### 3.3 Criar projeto

1. Dashboard → **New Project**
2. **Deploy from GitHub repo**
3. Autoriza Railway a acessar seus repos privados
4. Seleciona `nivelis-api`
5. Railway vai começar a fazer deploy automaticamente

### 3.4 Acompanhar o build

O Railway vai mostrar logs em tempo real. Vai instalar dependências, etc.

⏳ Primeira vez demora **5-10 minutos**.

Se der erro, geralmente é:
- Falta de algum pacote no `requirements.txt`
- Erro no `Procfile`
- Falta variável de ambiente (vamos configurar agora)

---

## 🔐 Parte 4 — Configurar variáveis de ambiente

A API não vai funcionar ainda — falta configurar as credenciais.

### 4.1 GEMINI_API_KEY

1. No Railway, clica no seu projeto
2. Aba **Variables**
3. Clica **New Variable**
4. Nome: `GEMINI_API_KEY`
5. Valor: cola sua chave do Gemini

### 4.2 Firebase Credentials

A `chave-firebase.json` precisa virar variável de ambiente. Tem 2 jeitos:

**Jeito A — Variável única com o JSON inteiro (mais simples)**

1. Abre o arquivo `chave-firebase.json` no Bloco de Notas
2. Copia TODO o conteúdo
3. No Railway, cria variável `FIREBASE_CREDENTIALS_JSON`
4. Cola o conteúdo inteiro como valor

Depois precisa alterar o código para ler dessa variável (faço junto contigo na hora).

**Jeito B — Cada campo como variável separada (mais limpo)**

Cria variáveis individuais: `FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL`, etc.

Recomendo Jeito A para começar.

### 4.3 Outras variáveis úteis

```
NIVELIS_LOG_LEVEL=WARNING       (reduz spam de logs em produção)
DESABILITAR_MODO_DEV=true       (desliga modo dev de auth se for usar)
```

### 4.4 Redeployar

Depois de adicionar as variáveis, Railway redeploya automaticamente. Aguarda 1-2 minutos.

---

## 🔥 Parte 5 — Firebase em produção

### 5.1 Regras de segurança

Acessa Firebase Console → seu projeto → **Firestore Database** → aba **Rules**

Cola:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;  // ninguém acessa direto
    }
  }
}
```

Isso BLOQUEIA acesso direto ao Firestore — só seu backend (com a chave admin) consegue ler/escrever. App e usuários acessam **apenas pela sua API**.

### 5.2 Confirmar funcionamento

Espera 1 minuto pras regras propagarem. Testa a API:

```
https://SEU_PROJETO.up.railway.app/
```

Deve retornar o healthcheck com Firebase OK.

---

## 🧪 Parte 6 — Testar a API em produção

### 6.1 Pegar a URL pública

Railway → seu projeto → aba **Settings** → seção **Domains** → **Generate Domain**

Vai gerar algo tipo: `nivelis-api-production.up.railway.app`

### 6.2 Testes essenciais

Substitui `<SUA_URL>` pelo domínio gerado:

**Healthcheck:**
```
GET https://<SUA_URL>/
```

**Listar concursos:**
```
GET https://<SUA_URL>/concursos
```

**Listar ENADE disponíveis:**
```
GET https://<SUA_URL>/enade/disponiveis
```

**Gerar simulado simples (gasta 1 Gemini):**
```
POST https://<SUA_URL>/enade/inspirar?ano=2022&area=direito&quantidade=3
```

### 6.3 Swagger online

A documentação interativa fica em:

```
https://<SUA_URL>/docs
```

---

## 📤 Parte 7 — Compartilhar com o time do app

### 7.1 Informações para passar

Envia para o time:

```
URL da API: https://<SUA_URL>
Documentação: https://<SUA_URL>/docs
Contrato: arquivo API_CONTRATO.md (anexo)
Exemplos: arquivo EXEMPLOS_REQUEST.http (anexo)
```

### 7.2 CORS (Cross-Origin)

Por padrão, se o app for web (não app mobile), pode dar erro de CORS. Sua API já tem CORS habilitado:

```python
# Já está no código:
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

Em produção, é melhor restringir para o domínio do app deles:

```python
allow_origins=["https://app-do-time.com", "https://app-do-time.vercel.app"]
```

(quando você souber o domínio, atualiza isso)

### 7.3 Limites de uso

Avisa o time que:
- Há limite de Gemini por dia (~1000 chamadas)
- Cache funciona — repetir a mesma prova é grátis
- Em desenvolvimento eles podem usar `X-Dev-User-Id: teste` em vez de Firebase Auth

---

## 🔧 Parte 8 — Manutenção e monitoramento

### 8.1 Logs

Railway → projeto → aba **Deployments** → **View Logs**
Mostra tudo em tempo real.

### 8.2 Atualizar código

Sempre que mudar algo localmente:

```bash
git add .
git commit -m "descrição da mudança"
git push
```

O Railway detecta o push e redeploya automaticamente.

### 8.3 Métricas

A rota `/admin/metricas` continua funcionando em produção.

### 8.4 Custos

Railway dá um aviso quando você está chegando perto do limite.
- Plano $5: ~10GB de tráfego/mês (suficiente pra milhares de requisições)
- Cobrança por uso real, não por contratação

### 8.5 Domínio customizado (opcional)

Se quiser `api.nivelis.com.br` em vez de `nivelis-api.up.railway.app`:
1. Compra o domínio (registro.br ou Hostinger)
2. Railway → Settings → Domains → Add Custom Domain
3. Configura DNS conforme instruções

Custo: ~R$40/ano pelo domínio.

---

## ⚠️ Checklist final antes de ir ao ar

- [ ] Código testado localmente, sem bugs
- [ ] `.env` e `chave-firebase.json` no `.gitignore`
- [ ] `requirements.txt` completo
- [ ] `Procfile` (ou `Dockerfile`) criado
- [ ] Variáveis de ambiente configuradas no Railway
- [ ] Regras Firebase configuradas
- [ ] CORS ajustado para o domínio do app
- [ ] Healthcheck retornando 200
- [ ] Pelo menos 1 simulado gerado com sucesso
- [ ] Time do app recebeu URL + documentação

---

## 🆘 Problemas comuns

**1. "Application failed to respond"**
→ Variável `PORT` não está no Procfile ou Dockerfile.

**2. "Firebase credentials not found"**
→ Variável `FIREBASE_CREDENTIALS_JSON` não está setada ou tá em formato errado.

**3. "GEMINI_API_KEY not configured"**
→ Falta a variável de ambiente no Railway.

**4. Deploy demora muito ou trava**
→ Provavelmente Playwright tentando baixar Chromium. Use o `Dockerfile` da seção 1.5.

**5. CORS bloqueado no app web**
→ Ajusta `allow_origins` na configuração de CORS.

---

## 💡 Quando você estiver pronto

Volta nesse arquivo e me avisa. Eu te ajudo a:

1. Ajustar o código para ler credenciais do ambiente em vez de `.env` / arquivo JSON
2. Decidir se vamos mesclar as 2 APIs em 1
3. Fazer o primeiro deploy junto contigo

Boa sorte! 🚀
