"""
=============================================================
  NIVELIS API — Arquivo Principal (para deploy)
=============================================================

  Este arquivo é o ponto de entrada para o deploy no Render.
  Ele junta as 2 APIs (simulados + questoes) em 1 só servidor,
  cada uma com seu prefixo de URL.

  ROTAS:
    /v1/simulados/...   → todas as rotas do simulados_api.py
    /v1/questoes/...    → todas as rotas do questoes_api.py
    /                   → redireciona para o Swagger
    /docs               → documentação Swagger do wrapper

  COMO RODAR LOCAL:
    uvicorn nivelis_api:app --host 0.0.0.0 --port 8000

  COMO RODA EM PRODUÇÃO (Render):
    uvicorn nivelis_api:app --host 0.0.0.0 --port $PORT

=============================================================
"""

import os
from fastapi                 import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses       import JSONResponse, RedirectResponse


# ──────────────────────────────────────────
#  APP PRINCIPAL — wrapper das 2 APIs
# ──────────────────────────────────────────

app = FastAPI(
    title="Nivelis API",
    description="""
Plataforma de geração de simulados para ENADE, ENEM e concursos.

---

## Onde fica cada coisa

Sub-aplicações montadas têm documentação própria — esta página cobre apenas
o wrapper. Para ver as rotas de verdade:

| Módulo | Prefixo | Documentação |
|---|---|---|
| **Simulados** | `/v1/simulados` | [`/v1/simulados/docs`](/v1/simulados/docs) |
| **Exercícios por tópico** | `/v1/questoes` | [`/v1/questoes/docs`](/v1/questoes/docs) |

> A maior parte do que você procura está em **[`/v1/simulados/docs`](/v1/simulados/docs)** —
> geração de questões, simulados, acervo de livros e administração.

---

## Um motor só: procedural

Toda questão nasce de um gerador em Python que resolve o problema antes de
montá-lo. O gabarito é a conta, não o palpite de um modelo.

| | |
|---|---|
| Custo | zero, sem cota |
| Velocidade | instantânea |
| Cobertura | cálculo, memorização, conceito, interpretação sobre livros |

As rotas de geração por IA foram removidas. O Gemini sobrou só como OCR das
rotas de extração de PDF, e é **opcional**: sem `GEMINI_API_KEY` a API sobe
normalmente e apenas `/v1/simulados/{enade,enem}/extrair` respondem 503.

---

## Atalhos mais usados

```
GET  /v1/simulados/procedural/areas       o que os geradores cobrem
POST /v1/simulados/procedural/simulado    simulado completo, sem custo
GET  /v1/simulados/procedural/topicos     tópicos por disciplina
POST /v1/simulados/montar                 simulado a partir do banco
GET  /v1/noticias/enem                    notícias do ENEM
GET  /health                              status do serviço
```
""",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Status",
            "description": "Verificação de saúde e mapa dos módulos.",
        },
    ],
)

# CORS — em PRODUCAO, ajustar pra domínios específicos
from cors import aplicar_cors
aplicar_cors(app, ["GET", "POST", "DELETE", "OPTIONS"], "raiz")


# ──────────────────────────────────────────
#  IMPORTA E MONTA AS APIs
# ──────────────────────────────────────────

from simulados_api import app as simulados_app
from questoes_api  import app as questoes_app

app.mount("/v1/simulados", simulados_app)
app.mount("/v1/questoes",  questoes_app)

# ── Notícias ──
#
# Montado no MESMO serviço de propósito. No plano gratuito do Render o
# serviço dorme quando fica ocioso e leva 30-50 s para acordar; um segundo
# serviço seria um segundo cold start, sem ganho nenhum.
#
# Com isto o aplicativo publicado chama
#
#     https://<host>/v1/noticias/enem
#     https://<host>/v1/noticias/enade
#
# e ninguém precisa rodar nada localmente — o uvicorn na máquina do
# desenvolvedor é só para trabalhar no arquivo.
#
# O noticias_api reaproveita o firebase_admin que as APIs acima já
# inicializaram, então não exige arquivo de credencial próprio aqui.
#
# A falha é tolerada: se o módulo não subir (falta de chave do GNews, por
# exemplo), o resto da API continua no ar — as notícias é que ficam sem
# servidor, e o aplicativo cai para as fontes diretas no celular.
try:
    from noticias_api import app as noticias_app
    app.mount("/v1/noticias", noticias_app)
    print("[NIVELIS] /v1/noticias montado")
except Exception as _e:
    print(f"[NIVELIS] ⚠ noticias_api não montado: {_e}")


# ──────────────────────────────────────────
#  ROTAS DO WRAPPER (raiz + health check)
# ──────────────────────────────────────────

@app.get("/", include_in_schema=False)
def home():
    """Página inicial — redireciona para o Swagger."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Status"], summary="Verificação de saúde")
def health_check():
    """
    Health check usado pelo Render para verificar se o serviço está vivo.

    Não acessa banco nem IA — resposta imediata.
    """
    return {
        "status":  "ok",
        "service": "nivelis-api",
        "version": "3.0.0",
    }


@app.get("/info", tags=["Status"], summary="Mapa dos módulos e rotas")
def info():
    """Informações sobre a API, seus módulos e onde encontrar cada coisa."""
    return {
        "nome":    "Nivelis API",
        "versao":  "3.0.0",
        "modulos": {
            "simulados": {
                "prefixo":   "/v1/simulados",
                "descricao": "Geração de simulados, questões e acervo de livros",
                "docs":      "/v1/simulados/docs",
                "destaques": [
                    "POST /procedural/simulado       — simulado completo, gabarito calculado",
                    "GET  /procedural/areas          — cobertura dos geradores em Python",
                    "POST /procedural/interpretacao  — questões sobre trechos de livros",
                    "POST /montar                    — simulado a partir do banco",
                ],
            },
            "questoes": {
                "prefixo":   "/v1/questoes",
                "descricao": "Exercícios por matéria e tópico",
                "docs":      "/v1/questoes/docs",
                "destaques": [
                    "GET  /exercicios/{materia}/{topico} — questões já salvas",
                    "GET  /topicos/{materia}             — tópicos disponíveis",
                ],
            },
        },
        "motores": {
            "procedural": "gabarito calculado pelo Python — custo zero, sem cota",
            "ia":         "geração via Gemini — consome cota diária",
        },
        "endpoints_uteis": {
            "swagger": "/docs",
            "redoc":   "/redoc",
            "health":  "/health",
        },
    }


# ──────────────────────────────────────────
#  HANDLER GLOBAL (segurança em produção)
# ──────────────────────────────────────────

PRODUCAO = os.getenv("DESABILITAR_DETALHES_ERRO", "false").lower() in ("true", "1", "yes")


@app.exception_handler(Exception)
async def handler_global(request, exc):
    """Captura erros não tratados no wrapper (sub-apps têm seus próprios)."""
    print(f"[NIVELIS] Erro não tratado em {request.url.path}: {exc}")

    if PRODUCAO:
        return JSONResponse(
            status_code=500,
            content={
                "erro":   "Erro interno do servidor",
                "codigo": "INTERNAL_ERROR",
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "erro":     "Erro interno do servidor",
                "detalhe":  str(exc)[:200],
                "endpoint": str(request.url.path),
            }
        )


# ──────────────────────────────────────────
#  PRINT DE INICIALIZAÇÃO
# ──────────────────────────────────────────

print("=" * 60)
print("  🚀 NIVELIS API v3.0.0")
print("=" * 60)
print(f"  Modo: {'PRODUÇÃO' if PRODUCAO else 'DESENVOLVIMENTO'}")
print(f"  Simulados → /v1/simulados/*   (docs em /v1/simulados/docs)")
print(f"  Questões  → /v1/questoes/*    (docs em /v1/questoes/docs)")
print(f"  Swagger   → /docs")
print("=" * 60)
