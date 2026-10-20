# 🎯 Nivelis API — Guia de Integração Front-end

API REST para o app **Nivelis** — simulados ENADE, ENEM e exercícios por matéria.

> **Estratégia:** gerar questões NOVAS inspiradas em provas oficiais (não copiar).
> Vantagens: variedade infinita, sem problemas de copyright, mais rápido, mais barato.

---

## 📡 URL Base

```
https://nivelis-api-1.onrender.com
```

⚠️ **Atenção sobre o ambiente de produção:**

A API roda no plano **Free** do Render. Após 15 minutos de inatividade, o servidor "dorme" e a **primeira requisição depois disso demora 30-50 segundos** pra acordar.

**Dica de UX:** Faça uma chamada "warm-up" silenciosa quando o app abrir:

```javascript
useEffect(() => {
  fetch("https://nivelis-api-1.onrender.com/health").catch(() => {});
}, []);
```

---

## 🗂️ Estrutura da API

A API é dividida em **2 módulos**:

| Módulo | Prefixo | Para que serve |
|---|---|---|
| **Simulados** | `/v1/simulados` | Gera simulados completos (ENADE, ENEM, livros) |
| **Questões** | `/v1/questoes` | Gera exercícios individuais por matéria/tópico |

**Documentação interativa (Swagger):**

- Simulados: https://nivelis-api-1.onrender.com/v1/simulados/docs
- Questões: https://nivelis-api-1.onrender.com/v1/questoes/docs

---

## 🎬 Fluxo principal do app

```
1. Usuário escolhe: "Quero ENADE 2022 Direito, 10 questões"
   ↓
   POST /v1/simulados/enade/inspirar?ano=2022&area=direito&quantidade=10
   Resposta: { simulado_id, questoes }
   ↓
2. App exibe as questões. Usuário responde cada uma.
   App guarda: { 1: "A", 2: "B"... }
   ↓
3. Usuário clica "Finalizar"
   POST /v1/simulados/simulado/{simulado_id}/resultado
   Body: { respostas: {...} }
   Resposta: { acertos, erros, correcao_detalhada }
   ↓
4. App mostra resultado e explicações
```

---

## 🚀 Rotas que vocês vão usar

### 📚 SIMULADOS (`/v1/simulados`)

#### 🎯 Gerar simulado ENADE

```http
POST /v1/simulados/enade/inspirar
```

**Query string:**
- `ano` (obrigatório) — `2022`, `2023`, etc
- `area` (obrigatório) — `direito`, `turismo`, `pedagogia`, etc
- `quantidade` (opcional, padrão `5`, max `30`)
- `dificuldade` (opcional) — `facil`, `medio`, `dificil`

```javascript
const url = "https://nivelis-api-1.onrender.com/v1/simulados/enade/inspirar?ano=2022&area=direito&quantidade=10";
const res = await fetch(url, { method: "POST" });
const data = await res.json();

console.log(data.simulado_id);  // GUARDA esse ID
console.log(data.questoes);      // Array de questões
```

**Resposta:**
```json
{
  "simulado_id": "abc123...",
  "origem": "inspirado_em_enade",
  "ano": 2022,
  "area": "direito",
  "total_questoes": 10,
  "questoes": [
    {
      "numero": 1,
      "enunciado": "...",
      "alternativas": {
        "A": "...", "B": "...", "C": "...", "D": "...", "E": "..."
      },
      "contexto": "...",
      "topico_inspiracao": "Direito Constitucional"
    }
  ]
}
```

---

#### 🎯 Gerar simulado ENEM

```http
POST /v1/simulados/enem/inspirar
```

**Query string:**
- `ano` (obrigatório) — `2020`-`2025`
- `area` (obrigatório) — `linguagens`, `humanas`, `natureza`, `matematica`
- `quantidade` (opcional, padrão `5`, max `30`)

```javascript
const url = "https://nivelis-api-1.onrender.com/v1/simulados/enem/inspirar?ano=2024&area=matematica&quantidade=10";
const res = await fetch(url, { method: "POST" });
```

---

#### 🎯 Gerar simulado baseado em livro

```http
POST /v1/simulados/livro/inspirar
```

**Query string:**
- `livro_id` (obrigatório) — pegue da rota `GET /livros`
- `capitulo` (opcional)
- `quantidade` (opcional, padrão `5`, max `30`)

```javascript
const livros = await fetch("https://nivelis-api-1.onrender.com/v1/simulados/livros")
  .then(r => r.json());

const livroId = livros.livros[0].livro_id;
const url = `https://nivelis-api-1.onrender.com/v1/simulados/livro/inspirar?livro_id=${livroId}&capitulo=1&quantidade=5`;
const simulado = await fetch(url, { method: "POST" }).then(r => r.json());
```

---

#### ✅ Enviar respostas e receber correção

```http
POST /v1/simulados/simulado/{simulado_id}/resultado
```

**Body (JSON):**
```json
{
  "respostas": {
    "1": "A",
    "2": "C",
    "3": "B"
  }
}
```

```javascript
const url = `https://nivelis-api-1.onrender.com/v1/simulados/simulado/${simuladoId}/resultado`;
const res = await fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    respostas: { "1": "A", "2": "C", "3": "B" }
  })
});
const resultado = await res.json();
```

**Resposta:**
```json
{
  "total_questoes": 3,
  "acertos": 2,
  "erros": 1,
  "porcentagem_acerto": 66.6,
  "correcao_detalhada": [
    {
      "numero": 1,
      "resposta_usuario": "A",
      "resposta_correta": "B",
      "acertou": false,
      "explicacao": "A resposta correta é B porque..."
    }
  ]
}
```

---

#### 📖 Listagens

```http
GET /v1/simulados/livros              # Lista todos os livros indexados
GET /v1/simulados/enade/disponiveis   # Anos/áreas disponíveis pra ENADE
GET /v1/simulados/enem/disponiveis    # Anos/áreas disponíveis pra ENEM
```

---

### 🎓 QUESTÕES por matéria/tópico (`/v1/questoes`)

#### 📚 Listar matérias

```http
GET /v1/questoes/materias
```

```javascript
const { materias } = await fetch("https://nivelis-api-1.onrender.com/v1/questoes/materias")
  .then(r => r.json());
// ["portugues", "matematica", "atualidades", "filosofia", "sociologia"]
```

---

#### 📚 Listar tópicos de uma matéria

```http
GET /v1/questoes/topicos/{materia}
```

```javascript
const data = await fetch("https://nivelis-api-1.onrender.com/v1/questoes/topicos/matematica")
  .then(r => r.json());
```

---

#### 🎯 Buscar exercícios já gerados (rápido)

```http
GET /v1/questoes/exercicios/{materia}/{topico}?quantidade=5
```

⚡ Lê do banco, não chama IA.

```javascript
const url = "https://nivelis-api-1.onrender.com/v1/questoes/exercicios/matematica/funcoes_e_graficos?quantidade=5";
const data = await fetch(url).then(r => r.json());
```

---

#### 🎯 Gerar exercícios novos (com IA)

```http
POST /v1/questoes/exercicios/gerar?materia=X&topico=Y&quantidade=5
```

---

#### ✅ Enviar respostas dos exercícios

```http
POST /v1/questoes/exercicios/{sessao_id}/resultado
```

Mesmo formato do `/v1/simulados/simulado/{id}/resultado`.

---

## 📦 Estrutura padrão de uma questão

```json
{
  "numero": 1,
  "enunciado": "Texto da questão...",
  "alternativas": {
    "A": "Primeira opção",
    "B": "Segunda opção",
    "C": "Terceira opção",
    "D": "Quarta opção",
    "E": "Quinta opção"
  },
  "contexto": "Contexto da questão",
  "topico_inspiracao": "Tema da questão",
  "materia": "matematica"
}
```

⚠️ **O `gabarito` NÃO vem nas questões.** Só após a correção (POST `/resultado`).

---

## 🎨 Service completo em React/React Native

Crie um arquivo `services/api.js`:

```javascript
const API_BASE = "https://nivelis-api-1.onrender.com";

// ============================
//  SIMULADOS
// ============================

export async function gerarSimuladoEnade(ano, area, quantidade = 5, dificuldade = null) {
  let url = `${API_BASE}/v1/simulados/enade/inspirar?ano=${ano}&area=${area}&quantidade=${quantidade}`;
  if (dificuldade) url += `&dificuldade=${dificuldade}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export async function gerarSimuladoEnem(ano, area, quantidade = 5, caderno = 1) {
  const url = `${API_BASE}/v1/simulados/enem/inspirar?ano=${ano}&area=${area}&quantidade=${quantidade}&caderno=${caderno}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export async function gerarSimuladoLivro(livroId, capitulo = null, quantidade = 5) {
  let url = `${API_BASE}/v1/simulados/livro/inspirar?livro_id=${livroId}&quantidade=${quantidade}`;
  if (capitulo) url += `&capitulo=${capitulo}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export async function enviarRespostasSimulado(simuladoId, respostas) {
  const url = `${API_BASE}/v1/simulados/simulado/${simuladoId}/resultado`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ respostas })
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

// ============================
//  LISTAGENS
// ============================

export async function listarLivros() {
  const res = await fetch(`${API_BASE}/v1/simulados/livros`);
  return res.json();
}

export async function listarMaterias() {
  const res = await fetch(`${API_BASE}/v1/questoes/materias`);
  return res.json();
}

export async function listarTopicos(materia) {
  const res = await fetch(`${API_BASE}/v1/questoes/topicos/${materia}`);
  return res.json();
}

// ============================
//  EXERCÍCIOS POR MATÉRIA
// ============================

export async function buscarExercicios(materia, topico, quantidade = 5) {
  const url = `${API_BASE}/v1/questoes/exercicios/${materia}/${topico}?quantidade=${quantidade}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export async function gerarExercicios(materia, topico, quantidade = 5) {
  const url = `${API_BASE}/v1/questoes/exercicios/gerar?materia=${materia}&topico=${topico}&quantidade=${quantidade}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export async function enviarRespostasExercicios(sessaoId, respostas) {
  const url = `${API_BASE}/v1/questoes/exercicios/${sessaoId}/resultado`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ respostas })
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

// ============================
//  WARM-UP
// ============================

export function warmupApi() {
  fetch(`${API_BASE}/health`).catch(() => {});
}
```

---

## 🎬 Exemplo de uso completo

```javascript
import { useState, useEffect } from 'react';
import { gerarSimuladoEnade, enviarRespostasSimulado, warmupApi } from './services/api';

export default function TelaSimuladoEnade() {
  const [simuladoId, setSimuladoId] = useState(null);
  const [questoes, setQuestoes] = useState([]);
  const [respostas, setRespostas] = useState({});
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);

  // Warm-up quando a tela abre
  useEffect(() => {
    warmupApi();
  }, []);

  async function iniciarSimulado() {
    setLoading(true);
    try {
      const data = await gerarSimuladoEnade(2022, "direito", 10);
      setSimuladoId(data.simulado_id);
      setQuestoes(data.questoes);
    } catch (e) {
      alert("Erro: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  function marcarResposta(numero, letra) {
    setRespostas(prev => ({ ...prev, [numero]: letra }));
  }

  async function finalizarSimulado() {
    setLoading(true);
    try {
      const data = await enviarRespostasSimulado(simuladoId, respostas);
      setResultado(data);
    } catch (e) {
      alert("Erro: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  // ... resto da UI
}
```

---

## ⚠️ Códigos de resposta HTTP

| Código | Significado | O que fazer |
|---|---|---|
| `200` | OK | Tudo certo |
| `404` | Não encontrado | Recurso não existe |
| `422` | Parâmetros inválidos | Validar dados antes |
| `500` | Erro interno | Tentar de novo |

**Exemplo de erro 422:**
```json
{
  "erro": "Parâmetros inválidos",
  "detalhes": [
    {"campo": "quantidade", "erro": "Input should be less than or equal to 30"}
  ]
}
```

---

## 💡 Dicas importantes

### 1. ⏰ Primeira requisição lenta
Sempre chama `/health` quando o app abre (warm-up silencioso).

### 2. ⌛ Geração de simulado demora ~10-15s
Mostra um loading legal:

```javascript
{loading && (
  <View>
    <ActivityIndicator size="large" />
    <Text>Gerando suas questões... isso pode levar alguns segundos.</Text>
  </View>
)}
```

### 3. 💾 Cache local
Salva o simulado em AsyncStorage pra o usuário poder continuar depois.

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

await AsyncStorage.setItem(`simulado_${id}`, JSON.stringify(dados));
const dados = JSON.parse(await AsyncStorage.getItem(`simulado_${id}`));
```

### 4. 📊 Limite diário
~20-30 simulados/dia. Se aparecer erro 500 com "cota", é isso.

```javascript
if (erro.message.includes("cota") || erro.message.includes("quota")) {
  alert("Limite diário atingido. Tente novamente amanhã.");
}
```

---

## 🚀 Próximos passos pra você

1. **Testem os endpoints no Swagger** primeiro:
   - https://nivelis-api-1.onrender.com/v1/simulados/docs
   - https://nivelis-api-1.onrender.com/v1/questoes/docs

2. **Copiem o `services/api.js`** desse documento pro projeto

3. **Implementem as telas** usando os exemplos

4. **Dúvidas?** Falar com o Nicolas

---

## 📞 Contato

Backend: **Nicolas** ([@Nick-gif9162](https://github.com/Nick-gif9162))

URL Produção: https://nivelis-api-1.onrender.com
