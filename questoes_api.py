"""
=============================================================
  NIVELIS — API de Questões e Conteúdo por Tópico
  Concurso : ENADE Formação Geral
  IA       : Gemini (gratuito)
=============================================================

  DEPENDÊNCIAS:
    pip install fastapi uvicorn firebase-admin
                google-generativeai python-dotenv

  COMO RODAR LOCALMENTE:
    uvicorn questoes_api:app --reload --host 0.0.0.0 --port 8001

  IMPORTANTE:
    Rode popular_banco.py primeiro para popular o Firebase.
    Esta API serve o conteúdo já processado — custo zero.

  >>> MELHORIAS DE QUALIDADE (v2.2.0) <<<
    1. PROMPT reforçado: gabarito DEVE bater com a explicação, e a
       explicação deve TERMINAR no resultado (sem cortar). Manda o
       modelo resolver ANTES de escolher a letra.
    2. TEMPERATURA baixa (0.2) para precisão em cálculos.
    3. VALIDAÇÃO automática antes de salvar: descarta questões onde
       o gabarito não corresponde a nenhuma alternativa, ou onde a
       explicação vazou rascunho ("vamos recalcular", "oops", etc).

=============================================================
"""

import os
import re
import json
import uuid
try:
    import google.generativeai as genai
except ImportError:          # pacote nem instalado — ver bloco GEMINI abaixo
    genai = None
import firebase_admin
from pathlib                 import Path
from dotenv                  import load_dotenv
from firebase_admin          import credentials, firestore
from fastapi                 import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime                import datetime, timezone
from typing                  import Optional

# ──────────────────────────────────────────
#  CARREGA O .env
# ──────────────────────────────────────────

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"[DOTENV] Carregando: {env_path} (existe: {env_path.exists()})")

# ──────────────────────────────────────────
#  CONFIGURAÇÃO DO FIREBASE
# ──────────────────────────────────────────

if not firebase_admin._apps:
    import json as _json
    cred_env = os.getenv("FIREBASE_CREDENTIALS")
    if cred_env:
        print("[FIREBASE] Usando credenciais da variável FIREBASE_CREDENTIALS")
        cred_dict = _json.loads(cred_env)
        cred      = credentials.Certificate(cred_dict)
    else:
        print("[FIREBASE] Usando arquivo chave-firebase.json")
        cred = credentials.Certificate("chave-firebase.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ──────────────────────────────────────────
#  CONFIGURAÇÃO DO GEMINI
# ──────────────────────────────────────────

# A chave deixou de ser obrigatória junto com a saída do /exercicios/gerar,
# que era a única rota deste módulo a usar IA. Hoje nada aqui gera com
# Gemini: os exercícios vêm do banco e do gerador procedural. O bloco fica
# só para o caso de algum script antigo importar `modelo`.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-lite"

IA_DISPONIVEL = bool(genai
                     and GEMINI_API_KEY
                     and GEMINI_API_KEY != "COLE_SUA_CHAVE_AQUI")

if IA_DISPONIVEL:
    genai.configure(api_key=GEMINI_API_KEY)
    modelo = genai.GenerativeModel(GEMINI_MODEL)
else:
    modelo = None


# ══════════════════════════════════════════════════════════════════════════════
#  >>> NOVO: VALIDAÇÃO DE QUALIDADE DAS QUESTÕES GERADAS <<<
#  Antes de salvar, checa se a questão faz sentido. Descarta as ruins.
# ══════════════════════════════════════════════════════════════════════════════

# Sinais de que a explicação vazou rascunho (não deve ser salva assim)
SINAIS_EXPLICACAO_RUIM = [
    "oops", "houve um erro", "houve um equívoco", "houve um engano",
    "vamos refazer", "vamos recalcular", "vamos revisar", "vamos verificar",
    "vamos analisar novamente", "ainda não cheguei", "parece que me confundi",
    "há um erro na minha", "me enganei", "vamos calcular novamente",
    "parece incorreta", "vamos reavaliar", "está inconsistente",
]


def _extrair_numeros(texto: str):
    """
    Extrai números de um texto, tratando formato BR (1.987,50 → 1987.50).

    A ordem das alternativas na regex importa: primeiro casa números com
    separador de milhar (2.500.000,00), depois decimais, e por último inteiros
    puros. Sem isso, "2500" seria quebrado em "250" + "0".
    """
    if not texto:
        return []
    numeros = []
    # fração (2/3) primeiro — sem isso "2/3" viraria dois números separados
    padrao = r'\d+\s*/\s*\d+|\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+|\d+\.\d+|\d+'
    for match in re.finditer(padrao, texto):
        s = match.group()
        try:
            if '/' in s:
                # fração: 6/9 -> 0.6667 (comum em probabilidade)
                num, den = s.split('/')
                den_f = float(den.strip())
                if den_f == 0:
                    continue
                numeros.append(float(num.strip()) / den_f)
            elif ',' in s:
                numeros.append(float(s.replace('.', '').replace(',', '.')))
            elif s.count('.') == 1 and len(s.split('.')[-1]) <= 2:
                numeros.append(float(s))
            elif '.' in s:
                numeros.append(float(s.replace('.', '')))
            else:
                numeros.append(float(s))
        except (ValueError, ZeroDivisionError):
            pass
    return numeros






# ──────────────────────────────────────────
#  REFORÇO COM LIVROS
# ──────────────────────────────────────────

LIMITE_LIVROS_REFORCO = 3

DISCIPLINAS_REFORCO = {
    "portugues":   ["portugues", "literatura", "redacao", "linguistica", "linguagens"],
    "matematica":  ["matematica"],
    "atualidades": ["atualidades", "geografia", "historia", "politica", "sociologia"],
    "filosofia":   ["filosofia"],
    "sociologia":  ["sociologia", "ciencias_sociais"],
}


def _normalizar(texto: str) -> str:
    """Remove acentos e converte pra minúsculo pra comparação flexível."""
    import unicodedata
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().strip()






# ──────────────────────────────────────────
#  REFORÇO COM PROVAS OFICIAIS
# ──────────────────────────────────────────

LIMITE_PROVAS_REFORCO = 3

PROVAS_REFORCO = {
    "portugues":   {
        "termos":   ["portugues", "linguagens", "jornalismo", "letras", "literatura"],
        "concursos": ["enem", "enade"],
    },
    "matematica":  {
        "termos":   ["matematica", "engenharia", "fisica"],
        "concursos": ["enem", "enade"],
    },
    "atualidades": {
        "termos":   ["humanas", "direito", "historia", "geografia", "sociologia"],
        "concursos": ["enem", "enade"],
    },
    "filosofia":   {
        "termos":   ["filosofia", "humanas"],
        "concursos": ["enem", "enade"],
    },
    "sociologia":  {
        "termos":   ["sociologia", "ciencias_sociais", "humanas"],
        "concursos": ["enem", "enade"],
    },
}






# ──────────────────────────────────────────
#  CONFIGURAÇÃO DA API
# ──────────────────────────────────────────

app = FastAPI(
    title="Nivelis — API de Questões por Tópico",
    description="""
**Nivelis Questões** — Serve questões de cada matéria/tópico.

🎯 **Rotas:**
- `/exercicios/{materia}/{topico}` — Busca questões já salvas
- `/topicos/{materia}` — Lista tópicos de uma matéria
- `/conteudo/{materia}/{topico}` — Conteúdo didático de um tópico
- `/exercicios/{id}/resultado` — Corrige uma sessão respondida

⚙️ **Este módulo não gera mais nada.** O `POST /exercicios/gerar`, que
criava questões com Gemini, foi removido: gastava cota para produzir
gabarito que ninguém conferia.

Para gerar, use as rotas procedurais em `/v1/simulados/procedural/*` — o
gabarito é calculado em Python, sai na hora e não consome cota. Para
encher o banco, `popular_banco.py`.
""",
    version="2.2.0",
    swagger_ui_parameters={
        "docExpansion":           "none",
        "filter":                  True,
        "syntaxHighlight.theme":  "monokai",
        "tryItOutEnabled":         True,
        "displayRequestDuration":  True,
        "persistAuthorization":    True,
    },
)

from cors import aplicar_cors
aplicar_cors(app, ["GET", "POST"], "questoes")

# ──────────────────────────────────────────
#  MATÉRIAS DISPONÍVEIS
# ──────────────────────────────────────────

MATERIAS_DISPONIVEIS = [
    "portugues",
    "matematica",
    "atualidades",
    "filosofia",
    "sociologia"
]

# ──────────────────────────────────────────────────────
#  BLOCO 1 — ROTAS DE CONTEÚDO
# ──────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════
#  DEDUPLICAÇÃO DE QUESTÕES
#
#  Mesma lógica do simulados_api: hash do enunciado normalizado, gravado
#  em campo próprio. Os dois módulos gravam na MESMA coleção 'questoes',
#  então usar o mesmo algoritmo faz com que um enxergue as questões do
#  outro — evitando duplicata entre as rotas /exercicios e /simulados.
# ══════════════════════════════════════════════════════════════════

import hashlib as _hashlib






@app.get("/")
def raiz():
    return {
        "status": "online",
        "app":    "Nivelis API de Questões",
        "versao": "2.2.0",
        "geracao": "procedural (em /v1/simulados/procedural/*)",
        "rotas": {
            "GET  /materias":                       "Lista matérias disponíveis",
            "GET  /topicos/{materia}":              "Lista tópicos de uma matéria",
            "GET  /conteudo/{materia}/{topico}":    "Retorna conteúdo teórico do tópico",
            "GET  /exercicios/{materia}/{topico}":  "Retorna exercícios do tópico",
            "POST /exercicios/{id}/resultado":      "Corrige exercícios respondidos",
        }
    }


@app.get("/materias")
def listar_materias():
    """Lista todas as matérias disponíveis do ENADE Formação Geral."""
    return {
        "concurso": "enade",
        "area":     "formacao_geral",
        "materias": MATERIAS_DISPONIVEIS
    }


@app.get("/topicos/{materia}")
def listar_topicos(materia: str):
    """Lista todos os tópicos disponíveis de uma matéria."""
    materia = materia.lower().strip()

    if materia not in MATERIAS_DISPONIVEIS:
        raise HTTPException(status_code=404, detail=f"Matéria não encontrada. Use: {MATERIAS_DISPONIVEIS}")

    docs = (
        db.collection("topicos")
          .where("materia",  "==", materia)
          .where("concurso", "==", "enade")
          .where("ativo",    "==", True)
          .stream()
    )

    topicos = []
    for doc in docs:
        d = doc.to_dict()
        topicos.append({
            "id":             doc.id,
            "topico":         d.get("topico"),
            "total_questoes": d.get("total_questoes", 0)
        })

    if not topicos:
        raise HTTPException(
            status_code=404,
            detail="Nenhum tópico encontrado. Rode popular_banco.py primeiro."
        )

    return {
        "materia": materia,
        "total":   len(topicos),
        "topicos": topicos
    }


@app.get("/conteudo/{materia}/{topico}")
def buscar_conteudo(materia: str, topico: str):
    """Retorna o conteúdo teórico completo de um tópico."""
    materia = materia.lower().strip()
    topico  = topico.lower().strip()
    chave   = f"{materia}_{topico}".replace(" ", "_")

    doc = db.collection("topicos").document(chave).get()

    if not doc.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Tópico '{topico}' não encontrado em '{materia}'. Verifique se popular_banco.py foi executado."
        )

    d = doc.to_dict()
    return {
        "materia":          d.get("materia"),
        "topico":           d.get("topico"),
        "concurso":         "enade",
        "resumo":           d.get("resumo", ""),
        "conceitos_chave":  d.get("conceitos_chave", []),
        "exemplo_resolvido": d.get("exemplo_resolvido", {}),
        "total_questoes":   d.get("total_questoes", 0)
    }


# ──────────────────────────────────────────────────────
#  BLOCO 2 — ROTAS DE EXERCÍCIOS
# ──────────────────────────────────────────────────────

@app.get("/exercicios/{materia}/{topico}")
def buscar_exercicios(
    materia:    str,
    topico:     str,
    quantidade: int = Query(default=5, ge=1, le=30, description="Quantidade (1-30)"),
    dificuldade: Optional[str] = Query(default=None, pattern="^(facil|media|dificil)$"),
):
    """Retorna exercícios de um tópico específico. Busca do Firebase — custo zero."""
    materia = materia.lower().strip()
    topico  = topico.lower().strip()

    if materia not in MATERIAS_DISPONIVEIS:
        raise HTTPException(status_code=404, detail=f"Matéria não encontrada. Use: {MATERIAS_DISPONIVEIS}")

    query = (
        db.collection("questoes")
          .where("concurso", "==", "enade")
          .where("materia",  "==", materia)
          .where("topico",   "==", topico)
          .where("ativo",    "==", True)
    )

    if dificuldade:
        dificuldade = dificuldade.lower()
        if dificuldade not in ("facil", "media", "dificil"):
            raise HTTPException(status_code=400, detail="Dificuldade inválida. Use: 'facil', 'media' ou 'dificil'.")
        query = query.where("dificuldade", "==", dificuldade)

    docs = list(query.limit(quantidade).stream())

    if not docs:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma questão encontrada para este tópico. Gere pelas rotas procedurais (/v1/simulados/procedural/gerar) ou rode popular_banco.py."
        )

    questoes  = []
    gabarito  = []
    sessao_id = str(uuid.uuid4())

    for doc in docs:
        d = doc.to_dict()
        questoes.append({
            "id":           doc.id,
            "numero":       d.get("numero"),
            "contexto":     d.get("contexto", ""),
            "enunciado":    d.get("enunciado", ""),
            "alternativas": d.get("alternativas", {}),
            "dificuldade":  d.get("dificuldade", "")
        })
        gabarito.append({
            "questao_id":       doc.id,
            "numero":           d.get("numero"),
            "resposta_correta": d.get("gabarito", ""),
            "explicacao":       d.get("explicacao", "")
        })

    db.collection("sessoes_exercicio").document(sessao_id).set({
        "sessao_id":  sessao_id,
        "materia":    materia,
        "topico":     topico,
        "gabarito":   gabarito,
        "criado_em":  datetime.now(timezone.utc)
    })

    if repetidas:
        print(f"[DEDUP] {repetidas} questão(ões) já existiam no banco — "
              f"não regravadas.")

    return {
        "sessao_id":  sessao_id,
        "materia":    materia,
        "topico":     topico,
        "total":      len(questoes),
        "questoes":   questoes
    }




# ──────────────────────────────────────────────────────
#  BLOCO 3 — CORREÇÃO
# ──────────────────────────────────────────────────────

@app.post("/exercicios/{sessao_id}/resultado")
def corrigir_exercicios(sessao_id: str, respostas: dict):
    """Corrige os exercícios respondidos e libera o gabarito com explicações."""
    doc = db.collection("sessoes_exercicio").document(sessao_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    dados             = doc.to_dict()
    gabarito          = dados.get("gabarito", [])
    respostas_usuario = respostas.get("respostas", {})
    materia           = dados.get("materia")
    topico            = dados.get("topico")

    # Busca as questões DESTA sessão pelo questao_id guardado no gabarito.
    # (Antes buscava por materia+topico, que trazia TODAS as questões do
    #  tópico no banco e casava por 'numero' — sujeito a colisão quando há
    #  várias sessões do mesmo tópico. Por questao_id é preciso e único.)
    questoes_completas = {}
    try:
        for item in gabarito:
            qid = item.get("questao_id")
            if not qid:
                continue
            doc_q = db.collection("questoes").document(qid).get()
            if doc_q.exists:
                data = doc_q.to_dict()
                questoes_completas[qid] = {
                    "enunciado":    data.get("enunciado"),
                    "contexto":     data.get("contexto"),
                    "alternativas": data.get("alternativas", {}),
                }
    except Exception as e:
        print(f"[CORREÇÃO] Erro ao buscar questões completas: {e}")

    acertos  = 0
    erros    = 0
    detalhes = []

    for item in gabarito:
        num         = item["numero"]
        num_str     = str(num)
        correta     = item["resposta_correta"]
        marcada     = respostas_usuario.get(num_str, "").upper()
        acertou     = marcada == correta
        questao_ext = questoes_completas.get(item.get("questao_id"), {})

        if acertou: acertos += 1
        else:       erros   += 1

        detalhes.append({
            "numero":           num,
            "contexto":         questao_ext.get("contexto", ""),
            "enunciado":        questao_ext.get("enunciado", ""),
            "alternativas":     questao_ext.get("alternativas", {}),
            "resposta_correta": correta,
            "resposta_usuario": marcada,
            "acertou":          acertou,
            "explicacao":       item.get("explicacao", "")
        })

    total          = acertos + erros
    aproveitamento = round((acertos / total) * 100, 1) if total > 0 else 0

    db.collection("resultados_exercicio").add({
        "sessao_id":      sessao_id,
        "materia":        materia,
        "topico":         topico,
        "acertos":        acertos,
        "erros":          erros,
        "aproveitamento": aproveitamento,
        "finalizado_em":  datetime.now(timezone.utc)
    })

    return {
        "sessao_id":      sessao_id,
        "materia":        materia,
        "topico":         topico,
        "acertos":        acertos,
        "erros":          erros,
        "total":          total,
        "aproveitamento": f"{aproveitamento}%",
        "gabarito":       detalhes
    }


@app.get("/sessao/{sessao_id}/gabarito")
def consultar_gabarito_sessao(sessao_id: str):
    """Consulta direta do gabarito de uma sessão (DEBUG)."""
    doc = db.collection("sessoes_exercicio").document(sessao_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    dados    = doc.to_dict()
    gabarito = dados.get("gabarito", [])

    return {
        "sessao_id":      sessao_id,
        "materia":        dados.get("materia"),
        "topico":         dados.get("topico"),
        "total_questoes": len(gabarito),
        "criado_em":      dados.get("criado_em"),
        "gabarito":       gabarito,
        "aviso":          "Esta rota é apenas para debug. App deve usar POST /exercicios/{id}/resultado.",
    }


@app.get("/sessao/{sessao_id}/completo")
def consultar_sessao_completa(sessao_id: str):
    """Retorna a sessão COMPLETA: questões + gabaritos + explicações."""
    doc = db.collection("sessoes_exercicio").document(sessao_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    dados    = doc.to_dict()
    gabarito = dados.get("gabarito", [])
    materia  = dados.get("materia")
    topico   = dados.get("topico")

    # Itera o gabarito DESTA sessão e busca cada questão pelo seu questao_id.
    # (Antes buscava por materia+topico e casava por 'numero', o que podia
    #  trazer questões de OUTRAS sessões do mesmo tópico.)
    questoes_completas = []
    try:
        for gab_item in gabarito:
            qid = gab_item.get("questao_id")
            num = gab_item.get("numero")
            if not qid:
                continue

            doc_q = db.collection("questoes").document(qid).get()
            if not doc_q.exists:
                continue
            data = doc_q.to_dict()

            questoes_completas.append({
                "numero":           num,
                "contexto":         data.get("contexto", ""),
                "enunciado":        data.get("enunciado", ""),
                "alternativas":     data.get("alternativas", {}),
                "resposta_correta": gab_item.get("resposta_correta"),
                "explicacao":       gab_item.get("explicacao"),
            })
    except Exception as e:
        print(f"[SESSAO] Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar questões: {e}")

    questoes_completas.sort(key=lambda x: x.get("numero", 0))

    return {
        "sessao_id":      sessao_id,
        "materia":        materia,
        "topico":         topico,
        "total_questoes": len(questoes_completas),
        "criado_em":      dados.get("criado_em"),
        "questoes":       questoes_completas,
        "aviso":          "⚠️ Rota DEBUG — em produção use o fluxo gerar → resultado.",
    }


# ──────────────────────────────────────────
#  HANDLERS DE EXCEÇÃO (SEGURANÇA)
# ──────────────────────────────────────────

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import os as _os
PRODUCAO = _os.getenv("DESABILITAR_DETALHES_ERRO", "false").lower() in ("true", "1", "yes")


@app.exception_handler(RequestValidationError)
async def handler_validacao(request: Request, exc: RequestValidationError):
    """Captura erros de validação e retorna mensagem amigável."""
    erros_amigaveis = []
    for err in exc.errors():
        campo = " → ".join(str(x) for x in err.get("loc", []) if x != "query")
        msg   = err.get("msg", "Valor inválido")
        erros_amigaveis.append({"campo": campo, "erro": msg})

    print(f"[VALIDACAO] {request.url.path} falhou: {erros_amigaveis}")

    return JSONResponse(
        status_code=422,
        content={
            "erro":     "Parâmetros inválidos",
            "detalhes": erros_amigaveis,
            "endpoint": str(request.url.path),
        }
    )


@app.exception_handler(Exception)
async def handler_geral(request: Request, exc: Exception):
    """Em PRODUCAO=true esconde stack trace; em dev mostra detalhes."""
    print(f"[ERRO] Não tratado em {request.url.path}: {exc}")

    if PRODUCAO:
        return JSONResponse(
            status_code=500,
            content={
                "erro":     "Erro interno do servidor. Tente novamente em alguns minutos.",
                "codigo":   "INTERNAL_ERROR",
                "endpoint": str(request.url.path),
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "erro":    "Erro interno do servidor",
                "detalhe": str(exc)[:200],
                "endpoint": str(request.url.path),
            }
        )
