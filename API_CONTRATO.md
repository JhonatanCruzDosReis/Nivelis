# 📘 Nivelis API — Contrato de Integração

Documento para o time de **frontend** integrar com a API.

**Base URL (desenvolvimento):** `http://localhost:8000` ou `http://<IP-DA-MAQUINA>:8000`
**Base URL (produção):** _a definir quando subir no Railway_

---

## 🔐 Autenticação

Algumas rotas exigem autenticação via **Firebase Authentication**.

### Como autenticar

O frontend deve enviar o **ID Token** do Firebase no header de cada request:

```
Authorization: Bearer <ID_TOKEN>
```

O ID Token é obtido após o usuário fazer login no Firebase Auth (no app).

### Modo dev (apenas durante desenvolvimento)

Para testar via Swagger/Postman sem implementar login ainda:

```
X-Dev-User-Id: qualquer_string_de_teste
```

Em produção esse header é desligado via variável de ambiente.

### Resposta 401 (não autenticado)

```json
{
  "detail": {
    "erro": "Não autenticado",
    "como_resolver": [
      "Envie o header 'Authorization: Bearer <id_token_firebase>'",
      "Ou envie 'X-Dev-User-Id: <qualquer_id>' (modo dev)"
    ]
  }
}
```

---

## 📋 Rotas

### 🔓 Públicas (sem auth)

| Método | Rota | O que faz |
|---|---|---|
| GET | `/` | Health check |
| GET | `/concursos` | Lista concursos suportados |
| GET | `/enade/disponiveis` | Lista anos e áreas do ENADE com prova disponível |
| GET | `/enade/disponiveis?ano=2022` | Filtra por ano específico |
| POST | `/enade/inspirar` | Gera questões inéditas inspiradas em prova oficial |
| POST | `/simulado` | Gera simulado genérico |
| GET | `/simulado/{simulado_id}` | Busca dados de um simulado |
| DELETE | `/simulado/{simulado_id}` | Remove simulado |
| GET | `/tokens` | Monitora uso de tokens |
| GET | `/limite-diario` | Consulta cota diária |

### 🔒 Autenticadas

| Método | Rota | O que faz |
|---|---|---|
| POST | `/simulado/{simulado_id}/resultado` | Envia respostas e recebe correção |
| GET | `/historico` | Lista simulados feitos pelo usuário |
| GET | `/historico/estatisticas` | Estatísticas agregadas do usuário |
| GET | `/resultado/{resultado_id}` | Detalhes de um resultado específico |

---

## 📦 Schemas dos principais endpoints

### `GET /enade/disponiveis`

Use para preencher dropdowns no app sem o usuário precisar adivinhar nomes.

**Response 200:**
```json
{
  "anos_disponiveis": [2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025],
  "provas": {
    "2022": {
      "grupo": "sociais_aplicadas",
      "areas": ["administracao", "direito", "psicologia", "..."],
      "total": 26
    },
    "2023": { "grupo": "saude_engenharias_exatas", "areas": [...] }
  },
  "ciclo_explicado": {
    "sociais_aplicadas": "Administração, Direito, Psicologia, ...",
    "saude_engenharias_exatas": "Medicina, Enfermagem, ...",
    "licenciaturas": "Pedagogia, Letras, ..."
  }
}
```

---

### `POST /enade/inspirar`

Gera questões **novas** inspiradas em uma prova oficial do ENADE.

**Query params:**
| Param | Tipo | Obrigatório | Default | Descrição |
|---|---|---|---|---|
| ano | int | ✅ sim | - | Ano da prova de referência |
| area | str | ❌ não | `formacao_geral_docente` | Área (use `/enade/disponiveis`) |
| quantidade | int | ❌ não | 5 | Quantas questões gerar |

**Exemplo:**
```
POST /enade/inspirar?ano=2022&area=direito&quantidade=5
```

**Response 200:**
```json
{
  "simulado_id":         "62bf4d48-18c9-47dd-a5f9-b64c2d837bf0",
  "origem":              "inspirado_em_prova_oficial",
  "veio_do_cache":       true,
  "ano":                 2022,
  "area":                "direito",
  "prova_referencia":    "https://download.inep.gov.br/...",
  "topicos_analisados":  56,
  "total_questoes":      3,
  "questoes": [
    {
      "numero":            1,
      "enunciado":         "...",
      "alternativas":      { "A": "...", "B": "...", "C": "...", "D": "...", "E": "..." },
      "contexto":          "...",
      "topico_inspiracao": "..."
    }
  ]
}
```

**⚠️ Atenção:**
- A primeira chamada de uma prova nova pode demorar **2-3 minutos** (analisa o PDF).
- Próximas chamadas com mesma prova são **rápidas** (~10s) por causa do cache.
- O retorno **NÃO inclui o gabarito**. Ele só é revelado em `POST /simulado/{id}/resultado`.

**Erros possíveis:**
- `400` — Área não foi avaliada nesse ano (ciclo trienal). Resposta sugere anos válidos.
- `404` — PDF não encontrado mesmo após tentar fallback automático.
- `429` — Limite diário de Gemini atingido (reseta à meia-noite UTC).

---

### `POST /simulado/{simulado_id}/resultado` 🔒

Envia as respostas do usuário e recebe o gabarito + estatísticas.
**Salva o resultado vinculado ao usuário.**

**Headers:**
```
Authorization: Bearer <id_token>
```

**Body:**
```json
{
  "respostas": { "1": "B", "2": "C", "3": "A" }
}
```

**Response 200:**
```json
{
  "resultado_id":   "uuid-do-resultado",
  "simulado_id":    "uuid-do-simulado",
  "user_id":        "uid-do-firebase",
  "acertos":        2,
  "erros":          1,
  "total":          3,
  "aproveitamento": "66.7%",
  "gabarito": [
    {
      "numero":           1,
      "resposta_correta": "B",
      "resposta_usuario": "B",
      "acertou":          true,
      "explicacao":       "..."
    }
  ]
}
```

---

### `GET /historico` 🔒

Lista os simulados feitos pelo usuário, ordenados do mais recente.

**Headers:**
```
Authorization: Bearer <id_token>
```

**Query params:**
| Param | Tipo | Default | Descrição |
|---|---|---|---|
| limite | int | 20 | Quantos resultados retornar (máx 100) |

**Response 200:**
```json
{
  "user_id":   "uid-do-firebase",
  "total":     12,
  "historico": [
    {
      "resultado_id":   "uuid",
      "simulado_id":    "uuid",
      "acertos":        4,
      "erros":          1,
      "total":          5,
      "aproveitamento": 80.0,
      "finalizado_em":  "2026-05-16T12:30:00Z"
    }
  ]
}
```

---

### `GET /historico/estatisticas` 🔒

Estatísticas agregadas do usuário (para dashboard).

**Response 200:**
```json
{
  "user_id":            "uid-do-firebase",
  "total_simulados":    12,
  "total_questoes":     60,
  "total_acertos":      45,
  "total_erros":        15,
  "taxa_acerto_media":  75.0,
  "melhor_desempenho":  100.0,
  "pior_desempenho":    40.0
}
```

---

### `GET /resultado/{resultado_id}` 🔒

Detalhes completos de um resultado específico (com gabarito e explicações).

⚠️ Só retorna se o resultado pertencer ao usuário autenticado (senão dá `403`).

---

## 🔥 Configuração necessária no Firebase

O time do app deve usar este projeto Firebase:

- **Project ID:** `api-teste-78277`
- **Região:** `southamerica-east1`

### Ativar Authentication
1. Console Firebase → Authentication → Sign-in method
2. Habilitar: **Email/Password** e **Google**

### Configurar regras do Firestore
Em **Firestore Database → Rules**:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Resultados: usuário só vê os próprios
    match /resultados/{resultadoId} {
      allow read:  if request.auth != null
                   && resource.data.user_id == request.auth.uid;
      allow write: if request.auth != null
                   && request.resource.data.user_id == request.auth.uid;
    }

    // Demais coleções: leitura pública, escrita só pelo backend
    match /{path=**} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

---

## 🧪 Como testar

### Pelo Swagger
1. Sobe a API: `uvicorn simulados_api:app --host 0.0.0.0 --port 8000`
2. Abre: `http://localhost:8000/docs`
3. Em rotas com cadeado, no header `X-Dev-User-Id` coloca qualquer string

### Pelo arquivo de exemplos
Veja `EXEMPLOS_REQUEST.http` com requests prontos para usar no VS Code
(extensão "REST Client") ou no Postman.

---

## 📞 Suporte

Bugs e dúvidas: contatar a pessoa do backend (você).

---

**Última atualização:** Maio/2026
