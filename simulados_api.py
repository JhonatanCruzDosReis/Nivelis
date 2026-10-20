"""
=============================================================
  NIVELIS — API de Simulados (v6 — geração 100% procedural)
  Fontes : Geradores em Python + Banco Firebase + scraping INEP
  IA     : nenhuma na geração. O Gemini sobrou só como OCR das rotas
           /enade/extrair e /enem/extrair, e é opcional.
  Extra  : Cache Firebase + monitoramento de tokens
=============================================================

  DEPENDÊNCIAS:
    pip install fastapi uvicorn requests firebase-admin
                google-generativeai pdfplumber pymupdf playwright pillow

    Após instalar o playwright, rode:
    playwright install chromium

  COMO RODAR LOCALMENTE:
    uvicorn simulados_api:app --reload

  VARIÁVEIS DE AMBIENTE:
    GEMINI_API_KEY=sua_chave_aqui
    (pegue em https://aistudio.google.com/app/apikey)

  ARQUIVO NECESSÁRIO:
    chave-firebase.json → Console do Firebase

  >>> MELHORIAS DE QUALIDADE (v5) <<<
    1. PROMPTS reforçados (enade/enem/livro): o gabarito DEVE bater com a
       explicação, e a explicação deve TERMINAR no resultado (sem rascunho).
    2. TEMPERATURA baixada de 0.7 -> 0.3 nas gerações (precisão em cálculos).
    3. VALIDAÇÃO automática em salvar_questoes_banco: descarta questões com
       gabarito inconsistente ou explicação com rascunho ANTES de salvar.
       Protege TODAS as rotas (enade, enem, livro, extrair, pool).

=============================================================
"""

import os
import io
import json
import uuid
import base64
import asyncio
import logging
import requests
import pdfplumber
import fitz                          # pymupdf — converte página em imagem
try:
    import google.generativeai as genai
except ImportError:          # pacote nem instalado — ver bloco GEMINI abaixo
    genai = None
import firebase_admin
from pathlib                 import Path
from dotenv                  import load_dotenv
from firebase_admin          import credentials, firestore
from fastapi                 import FastAPI, HTTPException, Depends, Query, Request
from fastapi                 import Path as FastApiPath
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api     import sync_playwright, TimeoutError as PlaywrightTimeout
from datetime                import datetime, timezone
from typing                  import Optional, List, Dict, Any
from enum                    import Enum
from pydantic                import BaseModel, Field
from PIL                     import Image

# Módulo de autenticação (Firebase Auth + modo dev)
from auth import obter_usuario_atual, obter_usuario_opcional, exigir_admin

# ──────────────────────────────────────────
#  CARREGA AS VARIÁVEIS DO .env
# ──────────────────────────────────────────

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"[DOTENV] Carregando: {env_path} (existe: {env_path.exists()})")


# ──────────────────────────────────────────
#  LOGGING ESTRUTURADO
# ──────────────────────────────────────────

nivel_log = os.getenv("NIVELIS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, nivel_log, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("nivelis")
log.info(f"Logging configurado em nível {nivel_log}")

# ──────────────────────────────────────────
#  CONFIGURAÇÃO DO FIREBASE
# ──────────────────────────────────────────

def inicializar_firebase():
    """
    Em produção (Render/Railway): lê o JSON da variável FIREBASE_CREDENTIALS
    Em dev (local): lê do arquivo chave-firebase.json
    """
    import json as _json

    if firebase_admin._apps:
        return firestore.client()

    cred_env = os.getenv("FIREBASE_CREDENTIALS")
    if cred_env:
        print("[FIREBASE] Usando credenciais da variável FIREBASE_CREDENTIALS")
        cred_dict = _json.loads(cred_env)
        cred      = credentials.Certificate(cred_dict)
    else:
        print("[FIREBASE] Usando arquivo chave-firebase.json")
        cred = credentials.Certificate("chave-firebase.json")

    firebase_admin.initialize_app(cred)
    return firestore.client()


db = inicializar_firebase()

# ──────────────────────────────────────────
#  CONFIGURAÇÃO DO GEMINI — agora OPCIONAL
# ──────────────────────────────────────────
#
# A chave deixou de ser obrigatória. Antes daqui, a ausência dela derrubava
# a API INTEIRA no import — inclusive as rotas procedurais, que resolvem a
# questão em Python e nunca falaram com IA nenhuma. Quem gerava pedia a
# chave; quem não gerava pagava por ela.
#
# Quem ainda usa o Gemini: só a extração de prova em PDF (/enade/extrair e
# /enem/extrair), onde ele faz o papel de OCR. Sem chave, essas duas rotas
# respondem 503 e o resto da API funciona igual.

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
    _falta = "pacote google-generativeai" if not genai else "GEMINI_API_KEY"
    print(f"[SIMULADOS] Sem {_falta} — extração de PDF desligada. "
          f"Geração procedural, banco e simulados funcionam normalmente.")


def exigir_ia():
    """Trava das rotas que ainda dependem do Gemini."""
    if not IA_DISPONIVEL:
        raise HTTPException(
            status_code=503,
            detail="Esta rota usa o Gemini para ler o PDF e a "
                   "GEMINI_API_KEY não está configurada. As rotas "
                   "procedurais (/procedural/*) não precisam dela.")


# ══════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO DE QUALIDADE DAS QUESTÕES (antes de salvar no banco)
#  Descarta questões com gabarito inconsistente ou explicação com rascunho.
# ══════════════════════════════════════════════════════════════════════════════

import re as _re_validacao

SINAIS_EXPLICACAO_RUIM = [
    "oops", "houve um erro", "houve um equívoco", "houve um engano",
    "vamos refazer", "vamos recalcular", "vamos revisar", "vamos verificar",
    "vamos analisar novamente", "ainda não cheguei", "parece que me confundi",
    "há um erro na minha", "me enganei", "vamos calcular novamente",
    "parece incorreta", "vamos reavaliar", "está inconsistente",
]


def _extrair_numeros(texto: str):
    """
    Extrai números de um texto, tratando formato BR (1.987,50 -> 1987.50).

    A ordem das alternativas na regex importa: primeiro tenta casar números
    com separador de milhar (2.500.000,00), depois decimais, e por último
    inteiros puros. Sem isso, "2500" seria quebrado em "250" + "0".
    """
    if not texto:
        return []
    numeros = []
    # fração (2/3) | milhar+decimal (2.125,00) | decimal-vírgula (45,90) |
    # decimal-ponto (45.90) | inteiro (2500)
    # A fração vem PRIMEIRO: sem isso "2/3" viraria dois números (2 e 3).
    padrao = r'\d+\s*/\s*\d+|\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+|\d+\.\d+|\d+'
    for match in _re_validacao.finditer(padrao, texto):
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
                # formato BR com vírgula decimal: 2.125,00 -> 2125.00
                numeros.append(float(s.replace('.', '').replace(',', '.')))
            elif s.count('.') == 1 and len(s.split('.')[-1]) <= 2:
                # decimal simples com ponto: 45.90
                numeros.append(float(s))
            elif '.' in s:
                # separador de milhar sem decimal: 2.500 -> 2500
                numeros.append(float(s.replace('.', '')))
            else:
                numeros.append(float(s))
        except (ValueError, ZeroDivisionError):
            pass
    return numeros


def limpar_control_chars(raw: str) -> str:
    """
    Escapa caracteres de controle CRUS que aparecem dentro de strings JSON.

    O Gemini frequentemente quebra linha dentro da "explicacao" (comum em
    matemática, onde ele formata a resolução em passos), o que produz um JSON
    inválido: "Invalid control character at ...". Isso NÃO é truncamento — o
    problema está no meio da string, então cortar o final não resolve.

    Esta função percorre o texto rastreando se está dentro de uma string
    (entre aspas não-escapadas) e converte \n, \r, \t e afins em suas versões
    escapadas, preservando o conteúdo.
    """
    if not raw:
        return raw

    resultado     = []
    dentro_string = False
    escapado      = False

    for char in raw:
        if escapado:
            resultado.append(char)
            escapado = False
            continue

        if char == '\\':
            resultado.append(char)
            escapado = True
            continue

        if char == '"':
            dentro_string = not dentro_string
            resultado.append(char)
            continue

        if dentro_string and ord(char) < 0x20:
            # Caractere de controle CRU dentro de string -> escapa
            if char == '\n':
                resultado.append('\\n')
            elif char == '\r':
                resultado.append('\\r')
            elif char == '\t':
                resultado.append('\\t')
            else:
                resultado.append(f'\\u{ord(char):04x}')
        else:
            resultado.append(char)

    return ''.join(resultado)


def validar_questao(q: dict) -> tuple:
    """
    Valida uma questão gerada. Retorna (ok: bool, motivo: str).
    Checa: campos essenciais, gabarito aponta alternativa existente,
    explicação sem rascunho, e (cálculo) o valor final da explicação não
    corresponde melhor a OUTRA alternativa que não a do gabarito.
    """
    # Blindagem: o Gemini às vezes manda um item que não é objeto, ou campos
    # explicitamente null (que passam pelo .get(campo, "") e chegam como None).
    if not isinstance(q, dict):
        return False, f"questao nao e um objeto (veio {type(q).__name__})"

    enunciado    = q.get("enunciado")    or ""
    alternativas = q.get("alternativas") or {}
    gabarito     = str(q.get("gabarito") or "").upper().strip()
    explicacao   = q.get("explicacao")   or ""

    if not isinstance(enunciado, str):
        enunciado = str(enunciado)
    if not isinstance(explicacao, str):
        explicacao = str(explicacao)

    if not enunciado or not alternativas or not gabarito:
        return False, "faltam campos essenciais"

    if not isinstance(alternativas, dict):
        return False, "alternativas em formato inesperado"

    letras = {k.upper() for k in alternativas.keys()}
    if gabarito not in letras:
        return False, f"gabarito '{gabarito}' nao existe nas alternativas"

    expl_low = explicacao.lower()
    for sinal in SINAIS_EXPLICACAO_RUIM:
        if sinal in expl_low:
            return False, f"explicacao contem rascunho ('{sinal}')"

    # ── Checagem de cálculo ──
    # Estratégia: pega o valor final da explicação e compara com o valor de
    # CADA alternativa. Se ele bate melhor com uma alternativa DIFERENTE do
    # gabarito, o gabarito provavelmente está errado. Isso pega o "distrator
    # próximo" (ex: 1200 vs 1210) sem punir arredondamento legítimo (o valor
    # continua mais perto da alternativa certa do que das outras).
    nums_expl = _extrair_numeros(explicacao)
    if nums_expl:
        valor_final = nums_expl[-1]  # último número = resultado provável

        # A checagem aritmética só faz sentido quando a resposta é um número
        # ÚNICO. Alternativas que são sequências ("37, 21, 22"), endereços IP
        # ("255.255.255.0"), fórmulas ou versões contêm vários números e a
        # comparação por "último número" daria falso positivo. Nesses casos a
        # estrutura já foi validada acima e a checagem numérica é pulada.
        def _resposta_escalar(txt: str) -> bool:
            return len(_extrair_numeros(str(txt))) <= 1

        alternativas_escalares = all(
            _resposta_escalar(t) for t in alternativas.values()
        )

        valores_alt = {}
        if alternativas_escalares:
            for letra, txt in alternativas.items():
                nums = _extrair_numeros(str(txt))
                if nums:
                    valores_alt[letra.upper()] = nums[0]

        # Só checa se o gabarito tem valor numérico e há alternativas numéricas
        if gabarito in valores_alt and len(valores_alt) >= 2:

            # TESTE A — o resultado existe em ALGUMA alternativa?
            # Se a conta dá 8640 e nenhuma alternativa vale 8640, a questão está
            # QUEBRADA (a resposta certa não está entre as opções). O modelo às
            # vezes gera isso mesmo mandando "refaça se não bater".
            def _bate(a, b, tol=0.01):
                if b == 0:
                    return abs(a - b) < 0.01
                return abs(a - b) / abs(b) < tol

            if not any(_bate(valor_final, v) for v in valores_alt.values()):
                return False, (
                    f"resultado da explicacao (={valor_final:g}) nao corresponde a "
                    f"NENHUMA alternativa - questao quebrada"
                )

            # TESTE B — o resultado bate melhor com OUTRA alternativa?
            dist_gab = abs(valor_final - valores_alt[gabarito])
            for letra, valor in valores_alt.items():
                if letra == gabarito:
                    continue
                if abs(valor_final - valor) < dist_gab:
                    return False, (
                        f"explicacao (={valor_final:g}) bate com alt {letra} "
                        f"(={valor:g}), nao com gabarito {gabarito} "
                        f"(={valores_alt[gabarito]:g})"
                    )

    return True, ""


# ──────────────────────────────────────────
#  CONFIGURAÇÃO DA API
# ──────────────────────────────────────────

# ──────────────────────────────────────────
#  ORGANIZAÇÃO DO SWAGGER
#  As tags agrupam as rotas por finalidade e definem a ordem em que
#  aparecem em /docs. Sem isso, as 30+ rotas ficam numa lista única.
# ──────────────────────────────────────────

TAGS_METADATA = [
    {
        "name": "Procedural (sem IA)",
        "description":
            "**O único motor de geração da API.** O gabarito é calculado ou "
            "simulado pelo Python, não estimado por um modelo — por isso é "
            "correto por construção, e custa zero.\n\n"
            "Cobre combinatória, computação, saúde, administração, questões "
            "conceituais e interpretação de texto sobre livros indexados. "
            "Comece por `/procedural/areas` para ver tudo que está disponível.",
    },
    {
        "name": "Provas oficiais",
        "description":
            "Catálogo das provas do INEP: o que existe por ano e área, e se o "
            "PDF está acessível. Não gera questão — só diz o que dá para "
            "extrair.",
    },
    {
        "name": "Extração de provas",
        "description":
            "Lê provas oficiais em PDF e extrai as questões reais, com o "
            "gabarito da própria banca.\n\n"
            "⚠️ Único lugar da API que ainda usa o Gemini, como OCR. Sem "
            "`GEMINI_API_KEY` estas rotas respondem 503 — e só elas; o resto "
            "da API sobe e funciona normalmente. Provas já processadas "
            "continuam vindo do cache do Firebase, sem chave.",
    },
    {
        "name": "Livros",
        "description":
            "Acervo indexado. Cada livro guarda seus capítulos, tópicos e "
            "trechos analisados — é o que alimenta as rotas procedurais e as "
            "de interpretação.",
    },
    {
        "name": "Sessões e resultados",
        "description":
            "Consulta de simulados gerados, gabaritos, correção de respostas "
            "e histórico de desempenho.",
    },
    {
        "name": "Pool de questões",
        "description":
            "Sorteia simulados de um lote pré-gerado.\n\n"
            "⚠️ Legado: a rota que criava o pool era movida a Gemini e saiu. "
            "Estas duas leem pools antigos; sem nada para ler, devolvem "
            "vazio. Para montar simulado hoje, use `/procedural/simulado` "
            "ou `/montar`.",
    },
    {
        "name": "Administração",
        "description":
            "Métricas de uso, controle de cache e limites diários.",
    },
]

app = FastAPI(
    title="Nivelis — API de Simulados",
    description="""
Geração de simulados para ENADE, ENEM e concursos.

## Um motor só: procedural

Toda questão nasce de um gerador em Python que **resolve o problema antes de
montá-lo**. O gabarito é a conta, não o palpite de um modelo — não existe
caminho pelo qual a resposta divirja da explicação.

| | |
|---|---|
| Custo | zero, sem cota |
| Velocidade | instantânea |
| Cobertura | cálculo, memorização, conceito e interpretação sobre livros indexados |

As rotas de geração por IA (`/enade/inspirar`, `/enem/inspirar`,
`/livro/inspirar`, os dois `-lote` e `/pool/gerar`) **foram removidas**.
Elas cobravam cota para entregar gabarito não verificável, coisa que os
geradores fazem de graça e com conferência automática.

O Gemini sobrou em um lugar só: ler PDF de prova oficial em
`/enade/extrair` e `/enem/extrair`. É opcional — sem a chave, a API sobe
igual e só essas duas rotas ficam fora do ar.

## Por onde começar

- `GET /procedural/areas` — o que os geradores em Python cobrem
- `POST /procedural/simulado` — simulado completo, sem custo
- `POST /montar` — simulado a partir do que já está no banco
- `GET /livros` — acervo indexado disponível

## Boas práticas

Use `salvar=false` para pré-visualizar antes de gravar no banco.
Passe `seed` para reproduzir exatamente o mesmo lote ao investigar um problema.
""",
    version="3.0.0",
    openapi_tags=TAGS_METADATA,
    contact={"name": "Nivelis"},
    swagger_ui_parameters={
        "docExpansion":            "none",   # começa recolhido
        "filter":                  True,     # caixa de busca de rotas
        "syntaxHighlight.theme":   "monokai",
        "tryItOutEnabled":         True,     # "Try it out" já ativo
        "displayRequestDuration":  True,     # mostra o tempo de resposta
        "persistAuthorization":    True,
        "defaultModelsExpandDepth": -1,      # esconde os schemas no rodapé
        "tagsSorter":              "alpha",
        "operationsSorter":        "alpha",
    },
)

from cors import aplicar_cors
aplicar_cors(app, ["GET", "POST", "DELETE"], "simulados")

# ──────────────────────────────────────────
#  MAPEAMENTO DE CONCURSOS / MATÉRIAS
# ──────────────────────────────────────────

MATERIAS = {
    "enem":    ["linguagens", "matematica", "ciencias_humanas", "ciencias_natureza"],
    "enade":   ["formacao_geral", "componente_especifico"],
    "militar": ["matematica", "portugues", "fisica", "quimica", "historia", "geografia"],
}

INEP_URL = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"

# ──────────────────────────────────────────────────────
#  BLOCO 1 — MONITORAMENTO DE TOKENS + LIMITE DIÁRIO
# ──────────────────────────────────────────────────────

LIMITE_TOKENS_DIA = 800_000


def tokens_usados_hoje() -> int:
    """Conta quantos tokens foram gastos HOJE (UTC)."""
    hoje      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc       = db.collection("limite_diario").document(hoje).get()

    if not doc.exists:
        return 0

    return doc.to_dict().get("total_tokens", 0)


# ──────────────────────────────────────────
#  ÁREAS ENADE — VARIAÇÕES DE URL CONHECIDAS
# ──────────────────────────────────────────
VARIACOES_AREA_INEP = {
    "relacoes_internacionais":         ["rel_internacionais"],
    "comunicacao_social_jornalismo":   ["jornalismo", "com_social_jornalismo"],
    "comunicacao_social_publicidade":  ["com_social_publicidade"],
    "administracao_publica":           ["adm_publica"],
    "tecnologia_comercio_exterior":    ["tec_comercio_exterior"],
    "tecnologia_gestao_comercial":     ["tec_gestao_comercial"],
    "tecnologia_gestao_financeira":    ["tec_gestao_financeira"],
    "tecnologia_gestao_rh":            ["tec_gestao_rh"],
    "tecnologia_gestao_publica":       ["tec_gestao_publica"],
    "tecnologia_logistica":            ["tec_logistica"],
    "tecnologia_marketing":            ["tec_marketing"],
    "tecnologia_processos_gerenciais": ["tec_processos_gerenciais"],
    "tecnologia_gastronomia":          ["tec_gastronomia"],
}


# ──────────────────────────────────────────
#  CICLO TRIENAL DO ENADE
# ──────────────────────────────────────────
CICLO_ENADE = {
    2019: ["sociais_aplicadas"],
    2022: ["sociais_aplicadas"],
    2025: ["sociais_aplicadas"],
    2018: ["saude_engenharias_exatas"],
    2023: ["saude_engenharias_exatas"],
    2017: ["licenciaturas"],
    2021: ["licenciaturas"],
    2024: ["licenciaturas"],
}

AREAS_POR_GRUPO = {
    "sociais_aplicadas": [
        "administracao", "administracao_publica", "ciencias_contabeis",
        "ciencias_economicas", "direito", "psicologia", "jornalismo",
        "comunicacao_social_publicidade", "relacoes_internacionais",
        "secretariado_executivo", "servico_social", "teologia", "turismo",
        "tecnologia_comercio_exterior", "tecnologia_design_interiores",
        "tecnologia_design_moda", "tecnologia_design_grafico",
        "tecnologia_gastronomia", "tecnologia_gestao_comercial",
        "tecnologia_gestao_qualidade", "tecnologia_gestao_rh",
        "tecnologia_gestao_financeira", "tecnologia_gestao_publica",
        "tecnologia_logistica", "tecnologia_marketing",
        "tecnologia_processos_gerenciais",
    ],
    "saude_engenharias_exatas": [
        "medicina", "enfermagem", "farmacia", "fisioterapia", "fonoaudiologia",
        "medicina_veterinaria", "odontologia", "nutricao", "biomedicina",
        "agronomia", "biologia", "educacao_fisica", "engenharia_civil",
        "engenharia_eletrica", "engenharia_mecanica", "engenharia_quimica",
        "engenharia_de_producao", "engenharia_de_computacao",
        "ciencia_da_computacao", "fisica", "matematica", "quimica",
        "estatistica", "arquitetura", "zootecnia",
    ],
    "licenciaturas": [
        "pedagogia", "letras_portugues", "historia", "geografia",
        "matematica_licenciatura", "fisica_licenciatura", "quimica_licenciatura",
        "biologia_licenciatura", "artes_visuais", "musica",
        "educacao_fisica_licenciatura", "filosofia", "sociologia",
        "ciencias_sociais", "formacao_geral_docente",
    ],
}


# ──────────────────────────────────────────
#  ENUMS — Dropdowns no Swagger /docs
# ──────────────────────────────────────────

class AnoEnadeEnum(int, Enum):
    """Anos válidos do ENADE (com prova aplicada)."""
    a2017 = 2017
    a2018 = 2018
    a2019 = 2019
    a2021 = 2021
    a2022 = 2022
    a2023 = 2023
    a2024 = 2024
    a2025 = 2025


class AreaEnadeEnum(str, Enum):
    """Áreas do ENADE (todas catalogadas no ciclo trienal)."""

    # ─── Sociais Aplicadas (2019, 2022, 2025) ───
    administracao                       = "administracao"
    administracao_publica               = "administracao_publica"
    ciencias_contabeis                  = "ciencias_contabeis"
    ciencias_economicas                 = "ciencias_economicas"
    direito                             = "direito"
    psicologia                          = "psicologia"
    jornalismo                          = "jornalismo"
    comunicacao_social_publicidade      = "comunicacao_social_publicidade"
    relacoes_internacionais             = "relacoes_internacionais"
    secretariado_executivo              = "secretariado_executivo"
    servico_social                      = "servico_social"
    teologia                            = "teologia"
    turismo                             = "turismo"
    tecnologia_comercio_exterior        = "tecnologia_comercio_exterior"
    tecnologia_design_interiores        = "tecnologia_design_interiores"
    tecnologia_design_moda              = "tecnologia_design_moda"
    tecnologia_design_grafico           = "tecnologia_design_grafico"
    tecnologia_gastronomia              = "tecnologia_gastronomia"
    tecnologia_gestao_comercial         = "tecnologia_gestao_comercial"
    tecnologia_gestao_qualidade         = "tecnologia_gestao_qualidade"
    tecnologia_gestao_rh                = "tecnologia_gestao_rh"
    tecnologia_gestao_financeira        = "tecnologia_gestao_financeira"
    tecnologia_gestao_publica           = "tecnologia_gestao_publica"
    tecnologia_logistica                = "tecnologia_logistica"
    tecnologia_marketing                = "tecnologia_marketing"
    tecnologia_processos_gerenciais     = "tecnologia_processos_gerenciais"

    # ─── Saúde, Engenharias, Exatas (2018, 2023) ───
    medicina                            = "medicina"
    enfermagem                          = "enfermagem"
    farmacia                            = "farmacia"
    fisioterapia                        = "fisioterapia"
    fonoaudiologia                      = "fonoaudiologia"
    medicina_veterinaria                = "medicina_veterinaria"
    odontologia                         = "odontologia"
    nutricao                            = "nutricao"
    biomedicina                         = "biomedicina"
    agronomia                           = "agronomia"
    biologia                            = "biologia"
    educacao_fisica                     = "educacao_fisica"
    engenharia_civil                    = "engenharia_civil"
    engenharia_eletrica                 = "engenharia_eletrica"
    engenharia_mecanica                 = "engenharia_mecanica"
    engenharia_quimica                  = "engenharia_quimica"
    engenharia_de_producao              = "engenharia_de_producao"
    engenharia_de_computacao            = "engenharia_de_computacao"
    ciencia_da_computacao               = "ciencia_da_computacao"
    fisica                              = "fisica"
    matematica                          = "matematica"
    quimica                             = "quimica"
    estatistica                         = "estatistica"
    arquitetura                         = "arquitetura"
    zootecnia                           = "zootecnia"

    # ─── Licenciaturas (2017, 2021, 2024) ───
    pedagogia                           = "pedagogia"
    letras_portugues                    = "letras_portugues"
    historia                            = "historia"
    geografia                           = "geografia"
    matematica_licenciatura             = "matematica_licenciatura"
    fisica_licenciatura                 = "fisica_licenciatura"
    quimica_licenciatura                = "quimica_licenciatura"
    biologia_licenciatura               = "biologia_licenciatura"
    artes_visuais                       = "artes_visuais"
    musica                              = "musica"
    educacao_fisica_licenciatura        = "educacao_fisica_licenciatura"
    filosofia                           = "filosofia"
    sociologia                          = "sociologia"
    ciencias_sociais                    = "ciencias_sociais"
    formacao_geral_docente              = "formacao_geral_docente"


class AnoEnemEnum(int, Enum):
    """Anos válidos do ENEM (de 2009 em diante)."""
    a2009 = 2009
    a2010 = 2010
    a2011 = 2011
    a2012 = 2012
    a2013 = 2013
    a2014 = 2014
    a2015 = 2015
    a2016 = 2016
    a2017 = 2017
    a2018 = 2018
    a2019 = 2019
    a2020 = 2020
    a2021 = 2021
    a2022 = 2022
    a2023 = 2023
    a2024 = 2024
    a2025 = 2025


class AreaEnemEnum(str, Enum):
    """Áreas do ENEM."""
    linguagens = "linguagens"
    humanas    = "humanas"
    natureza   = "natureza"
    matematica = "matematica"


# ──────────────────────────────────────────
#  CONSTANTES DE SEGURANÇA / VALIDAÇÃO
# ──────────────────────────────────────────

QUANTIDADE_MINIMA      = 1
QUANTIDADE_MAXIMA      = 30
QUANTIDADE_MAXIMA_POOL = 50
TOPICO_MAX_LENGTH      = 200
CONTEXTO_MAX_LENGTH    = 300


class DificuldadeEnum(str, Enum):
    """Níveis de dificuldade aceitos."""
    facil   = "facil"
    medio   = "medio"
    dificil = "dificil"


# ──────────────────────────────────────────
#  REFORÇO COM LIVROS
# ──────────────────────────────────────────

DISCIPLINAS_ENEM = {
    "linguagens":  ["portugues", "literatura", "redacao", "linguistica", "linguagens"],
    "humanas":     ["historia", "geografia", "filosofia", "sociologia", "humanas"],
    "natureza":    ["biologia", "quimica", "fisica", "natureza", "ciencias"],
    "matematica":  ["matematica"],
}

DISCIPLINAS_ENADE_EXTRA = {
    "direito":              ["direito", "direito_constitucional", "direito_civil", "direito_penal"],
    "administracao":        ["administracao", "gestao"],
    "matematica":           ["matematica"],
    "fisica":               ["fisica"],
    "biologia":             ["biologia"],
    "engenharia_civil":     ["engenharia_civil", "engenharias", "fisica", "matematica"],
    "engenharia_eletrica":  ["engenharia_eletrica", "engenharias", "fisica", "matematica"],
    "medicina":             ["medicina", "anatomia", "patologia"],
}

LIMITE_LIVROS_REFORCO = 3






def validar_area_ano(ano: int, area: str) -> Optional[str]:
    """Valida se a área tem prova naquele ano pelo ciclo trienal do ENADE."""
    grupos_do_ano = CICLO_ENADE.get(ano)
    if not grupos_do_ano:
        return None

    for grupo, areas_lista in AREAS_POR_GRUPO.items():
        if area in areas_lista and grupo not in grupos_do_ano:
            anos_disponiveis = sorted([
                a for a, g in CICLO_ENADE.items() if grupo in g
            ])
            return (
                f"A área '{area}' não foi avaliada no ENADE {ano}. "
                f"Em {ano} foi avaliado o grupo: {', '.join(grupos_do_ano)}. "
                f"Tente um destes anos: {anos_disponiveis}"
            )

    return None


def verificar_limite_diario():
    """Verifica se o limite diário já foi atingido. Lança 429 se sim."""
    usados = tokens_usados_hoje()
    restantes = LIMITE_TOKENS_DIA - usados

    if usados >= LIMITE_TOKENS_DIA:
        print(f"[LIMITE] 🚫 Limite diário atingido: {usados:,}/{LIMITE_TOKENS_DIA:,} tokens")
        raise HTTPException(
            status_code=429,
            detail={
                "erro":           "Limite diário de tokens atingido",
                "tokens_usados":  usados,
                "limite_diario":  LIMITE_TOKENS_DIA,
                "mensagem":       "A geração de conteúdo novo está temporariamente pausada. "
                                  "O limite reseta automaticamente à meia-noite UTC. "
                                  "Conteúdo já existente no banco continua disponível."
            }
        )

    if usados >= LIMITE_TOKENS_DIA * 0.9:
        print(f"[LIMITE] ⚠️  ATENÇÃO: {usados:,}/{LIMITE_TOKENS_DIA:,} tokens "
              f"(restam apenas {restantes:,})")


def gerar_com_retry(prompt_ou_conteudo, generation_config: dict, max_tentativas: int = 3):
    """Wrapper para chamadas ao Gemini com retry automático em erro 429."""
    import time
    from google.api_core.exceptions import ResourceExhausted

    for tentativa in range(1, max_tentativas + 1):
        try:
            return modelo.generate_content(prompt_ou_conteudo, generation_config=generation_config)

        except ResourceExhausted as e:
            mensagem_erro = str(e)

            tempo_espera = 15
            try:
                import re
                match = re.search(r'retry in (\d+(?:\.\d+)?)\s*s', mensagem_erro, re.IGNORECASE)
                if match:
                    tempo_espera = int(float(match.group(1))) + 2
            except Exception:
                pass

            if "PerDay" in mensagem_erro:
                print(f"[GEMINI] 🚫 Limite DIÁRIO do Gemini estourado. Sem retry.")
                raise

            if tentativa < max_tentativas:
                print(f"[GEMINI] ⏳ Limite por minuto atingido. Aguardando {tempo_espera}s "
                      f"(tentativa {tentativa}/{max_tentativas})...")
                time.sleep(tempo_espera)
                continue
            else:
                print(f"[GEMINI] ❌ Falhou após {max_tentativas} tentativas.")
                raise

        except Exception as e:
            raise

    raise RuntimeError("gerar_com_retry: loop terminou sem retornar")


def registrar_uso_tokens(operacao: str, input_tokens: int, output_tokens: int, simulado_id: str = ""):
    """Salva o consumo de tokens de cada chamada ao Gemini."""
    custo_estimado_usd = 0.0
    total              = input_tokens + output_tokens

    db.collection("uso_tokens").add({
        "operacao":          operacao,
        "simulado_id":       simulado_id,
        "input_tokens":      input_tokens,
        "output_tokens":     output_tokens,
        "total_tokens":      total,
        "custo_estimado_usd": custo_estimado_usd,
        "modelo":            GEMINI_MODEL,
        "registrado_em":     datetime.now(timezone.utc)
    })

    hoje      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc_ref   = db.collection("limite_diario").document(hoje)
    doc       = doc_ref.get()

    if doc.exists:
        dados_anteriores = doc.to_dict()
        novo_total       = dados_anteriores.get("total_tokens", 0) + total
        chamadas         = dados_anteriores.get("chamadas", 0) + 1
    else:
        novo_total = total
        chamadas   = 1

    doc_ref.set({
        "data":            hoje,
        "total_tokens":    novo_total,
        "custo_total_usd": 0.0,
        "chamadas":        chamadas,
        "limite":          LIMITE_TOKENS_DIA,
        "atualizado_em":   datetime.now(timezone.utc)
    })

    print(f"[TOKENS] {operacao}: {total} tokens "
          f"(gratuito) | Hoje: {novo_total:,}/{LIMITE_TOKENS_DIA:,}")


# ──────────────────────────────────────────────────────
#  BLOCO 2 — CACHE FIREBASE
# ──────────────────────────────────────────────────────

def prova_ja_processada(concurso: str, ano: int, materia: str) -> bool:
    """Verifica se esta prova já foi processada e salva no Firebase."""
    chave = f"{concurso}_{ano}_{materia}"
    doc   = db.collection("provas_processadas").document(chave).get()
    existe = doc.exists

    if existe:
        print(f"[CACHE] Prova {chave} já processada — pulando Claude ✅")
    return existe


def marcar_prova_processada(concurso: str, ano: int, materia: str, total_questoes: int):
    """Marca a prova como processada para evitar reprocessamento futuro."""
    chave = f"{concurso}_{ano}_{materia}"
    db.collection("provas_processadas").document(chave).set({
        "concurso":      concurso,
        "ano":           ano,
        "materia":       materia,
        "total_questoes": total_questoes,
        "processado_em": datetime.now(timezone.utc)
    })
    print(f"[CACHE] Prova {chave} marcada como processada")




# ──────────────────────────────────────────────────────
#  BLOCO 3 — SCRAPING DO INEP COM PLAYWRIGHT
# ──────────────────────────────────────────────────────

PALAVRAS_MATERIA = {
    "linguagens":        ["linguagens", "lingua", "ingles", "espanhol"],
    "matematica":        ["matematica", "matemática"],
    "ciencias_humanas":  ["humanas", "ciencias_humanas"],
    "ciencias_natureza": ["natureza", "ciencias_natureza"],
    "formacao_geral":    ["formacao_geral", "formação geral"],
}


def buscar_pdf_inep(ano: int, materia: str) -> Optional[str]:
    """Abre o site do INEP com Playwright e retorna a URL do PDF correto."""
    print(f"[INEP] Buscando PDF {ano} — {materia} com Playwright...")

    chaves = PALAVRAS_MATERIA.get(materia, [materia])

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()

            page.goto(INEP_URL, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

            try:
                page.click(f'text="{ano}"', timeout=8000)
                print(f"[INEP] Aba {ano} clicada")
            except PlaywrightTimeout:
                try:
                    page.click(f'[data-tab="{ano}"]', timeout=5000)
                except PlaywrightTimeout:
                    print(f"[INEP] Aba {ano} não encontrada")
                    browser.close()
                    return None

            page.wait_for_timeout(4000)

            links = page.query_selector_all("a[href]")
            pdf_url = None

            for link in links:
                href  = link.get_attribute("href") or ""
                texto = link.inner_text().lower()

                if href.lower().endswith(".pdf") and str(ano) in href:
                    if any(c in href.lower() or c in texto for c in chaves):
                        pdf_url = href
                        print(f"[INEP] PDF encontrado: {pdf_url}")
                        break

            browser.close()

            if not pdf_url:
                print(f"[INEP] PDF não encontrado para {ano} — {materia}")

            return pdf_url

    except Exception as e:
        print(f"[INEP] Erro no Playwright: {e}")
        return None


def buscar_url_inep(ano: int, area: str) -> Optional[str]:
    """Busca a URL real do PDF da prova ENADE no site oficial do INEP."""
    INEP_URL_ENADE = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos"

    area_busca = area.replace("_", " ").lower()

    print(f"[INEP] Buscando prova: ano={ano}, area='{area_busca}'")

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True)
            contexto  = navegador.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            pagina = contexto.new_page()

            print(f"[INEP] Abrindo página oficial...")
            pagina.goto(INEP_URL_ENADE, timeout=60000, wait_until="domcontentloaded")
            pagina.wait_for_timeout(5000)

            try:
                botao_cookies = pagina.locator("button:has-text('Aceitar todos')").first
                if botao_cookies.is_visible(timeout=2000):
                    botao_cookies.click()
                    print(f"[INEP] Banner de cookies fechado")
                    pagina.wait_for_timeout(1000)
            except Exception:
                pass

            print(f"[INEP] Procurando aba do ano {ano}...")
            aba_encontrada = False

            seletores_aba = [
                f"a[data-id='{ano}']",
                f"a[data-id=\"{ano}\"]",
                f".swiper-slide a:has-text('{ano}')",
                f"a[role='tab']:has-text('{ano}')",
                f"li:has-text('{ano}') a",
                f".nav-tabs a:has-text('{ano}')",
                f"text={ano}",
            ]

            for seletor in seletores_aba:
                try:
                    elemento = pagina.locator(seletor).first
                    if elemento.is_visible(timeout=3000):
                        elemento.click(timeout=5000)
                        print(f"[INEP] Aba {ano} clicada (seletor: {seletor})")
                        aba_encontrada = True
                        break
                except Exception:
                    continue

            if not aba_encontrada:
                print(f"[INEP] Aba do ano {ano} não encontrada com nenhum seletor")
                navegador.close()
                return None

            pagina.wait_for_timeout(3000)

            print(f"[INEP] Buscando link para '{area_busca}'...")
            links          = pagina.locator("a[href*='.pdf']").all()
            url_encontrada = None
            total_links    = len(links)
            print(f"[INEP] Total de links PDF na página: {total_links}")

            for link in links:
                try:
                    href = (link.get_attribute("href") or "").lower()
                    texto = (link.inner_text() or "").lower()

                    if area_busca in texto or area_busca in href:
                        if ("_pv_" in href or "prova" in texto) and "_gb_" not in href:
                            url_encontrada = link.get_attribute("href")
                            print(f"[INEP] Link encontrado: {url_encontrada}")
                            break
                except Exception:
                    continue

            navegador.close()

            if url_encontrada and not url_encontrada.startswith("http"):
                url_encontrada = "https://download.inep.gov.br" + url_encontrada

            if not url_encontrada:
                print(f"[INEP] Nenhum link encontrado para '{area_busca}' no ano {ano}")

            return url_encontrada

    except Exception as e:
        print(f"[INEP] Erro na busca: {e}")
        return None


def buscar_url_inep_enem(ano: int, dia: int = 1, caderno: int = 1) -> Optional[str]:
    """Versão ENEM da busca de URL — web scraping no site do INEP."""
    INEP_URL_ENEM = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"

    print(f"[INEP-ENEM] Buscando prova: ano={ano}, dia={dia}, caderno={caderno}")

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True)
            contexto  = navegador.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            pagina = contexto.new_page()

            print(f"[INEP-ENEM] Abrindo página oficial...")
            pagina.goto(INEP_URL_ENEM, timeout=60000, wait_until="domcontentloaded")
            pagina.wait_for_timeout(5000)

            try:
                botao_cookies = pagina.locator("button:has-text('Aceitar todos')").first
                if botao_cookies.is_visible(timeout=2000):
                    botao_cookies.click()
                    print(f"[INEP-ENEM] Banner de cookies fechado")
                    pagina.wait_for_timeout(1000)
            except Exception:
                pass

            print(f"[INEP-ENEM] Procurando aba do ano {ano}...")
            seletores_aba = [
                f"a[data-id='{ano}']",
                f"a[data-id=\"{ano}\"]",
                f".swiper-slide a:has-text('{ano}')",
                f"a[role='tab']:has-text('{ano}')",
                f"li:has-text('{ano}') a",
                f".nav-tabs a:has-text('{ano}')",
                f"text={ano}",
            ]

            aba_encontrada = False
            for seletor in seletores_aba:
                try:
                    elemento = pagina.locator(seletor).first
                    if elemento.is_visible(timeout=2000):
                        elemento.click()
                        print(f"[INEP-ENEM] Aba {ano} clicada (seletor: {seletor})")
                        aba_encontrada = True
                        pagina.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            if not aba_encontrada:
                print(f"[INEP-ENEM] ⚠ Aba do ano {ano} não encontrada")

            links_encontrados = pagina.locator("a[href$='.pdf']").all()
            print(f"[INEP-ENEM] Encontrei {len(links_encontrados)} links PDF na página")

            url_encontrada = None

            for link in links_encontrados:
                try:
                    href  = link.get_attribute("href") or ""
                    texto = (link.inner_text() or "").lower()
                    href_lower = href.lower()

                    if "impresso" not in href_lower:
                        continue
                    if str(ano) not in href_lower:
                        continue

                    tag_dia = f"d{dia}"
                    if tag_dia not in href_lower:
                        continue

                    tag_caderno = f"cd{caderno}"
                    if tag_caderno not in href_lower:
                        continue

                    url_encontrada = href
                    if not url_encontrada.startswith("http"):
                        url_encontrada = "https://www.gov.br" + url_encontrada
                    print(f"[INEP-ENEM] ✅ Achou: {url_encontrada}")
                    break

                except Exception as e:
                    continue

            navegador.close()

            if not url_encontrada:
                print(f"[INEP-ENEM] Nenhum link encontrado para ano={ano}, dia={dia}, caderno={caderno}")

            return url_encontrada

    except Exception as e:
        print(f"[INEP-ENEM] Erro na busca: {e}")
        return None


def baixar_pdf(url: str) -> Optional[bytes]:
    """Baixa o PDF e retorna os bytes."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/pdf,*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer":         "https://www.gov.br/",
    }

    try:
        print(f"[PDF] Tentando baixar: {url}")

        # O certificado é VERIFICADO (o padrão do requests, que usa o pacote
        # certifi). Antes vinha `verify=False` junto com
        # `urllib3.disable_warnings(InsecureRequestWarning)` — ou seja, a
        # verificação desligada E o aviso sobre isso silenciado, que é a
        # combinação que faz o problema não aparecer em lugar nenhum.
        #
        # Sem verificação, quem estiver no caminho da rede pode responder no
        # lugar do gov.br e entregar um PDF qualquer, que esta função devolve
        # como se fosse a prova oficial — e o conteúdo dele vira questão no
        # banco. A rota que chama isto já exige X-Admin-Token desde o item 6,
        # então não é qualquer um que dispara; mas o download em si não tinha
        # defesa nenhuma.
        r = requests.get(
            url,
            headers=headers,
            timeout=60,
            allow_redirects=True,
        )
        r.raise_for_status()
        print(f"[PDF] Baixado ({len(r.content) / 1024:.0f} KB)")
        return r.content
    except requests.exceptions.SSLError as e:
        # Falha de certificado agora é ERRO VISÍVEL, não algo a contornar.
        # Se o gov.br realmente estiver com a cadeia quebrada, a saída certa
        # é atualizar o certifi (`pip install -U certifi`) ou baixar o PDF à
        # mão — nunca voltar com verify=False.
        print(f"[PDF] ✗ Certificado TLS recusado em {url}: {e}")
        print( "[PDF]   Não vou baixar sem verificar. Atualize o certifi ou "
               "pegue o arquivo manualmente.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[PDF] HTTP {e.response.status_code}: {url}")
        return None
    except Exception as e:
        print(f"[PDF] Erro: {e}")
        return None


# ──────────────────────────────────────────────────────
#  BLOCO 4 — CONVERSÃO DE PÁGINAS EM IMAGEM
# ──────────────────────────────────────────────────────

def pdf_para_imagens_base64(pdf_bytes: bytes) -> list:
    """Converte cada página do PDF em uma imagem PNG base64."""
    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")
    paginas = []

    for num_pagina in range(len(doc)):
        page   = doc[num_pagina]
        matrix = fitz.Matrix(2.0, 2.0)
        pix    = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        paginas.append(img_b64)

    doc.close()
    print(f"[PDF] {len(paginas)} páginas convertidas para imagem")
    return paginas




# ──────────────────────────────────────────────────────
#  BLOCO 5 — GEMINI COM VISÃO (extração página por página)
# ──────────────────────────────────────────────────────

def extrair_questoes_e_gabarito_por_pagina(
    pagina_b64: str,
    numero_pagina: int,
    materia: str,
    simulado_id: str
) -> list:
    """Envia uma página (imagem) ao Gemini e extrai questões + gabarito + explicação."""
    # Único ponto do módulo que ainda fala com o Gemini. A trava fica aqui,
    # e não na rota, de propósito: /enade/extrair e /enem/extrair respondem
    # do cache do Firebase quando a prova já foi processada, e esse caminho
    # não precisa de chave nenhuma.
    exigir_ia()
    verificar_limite_diario()

    prompt = f"""
Você é um professor especialista em concursos nacionais brasileiros (ENEM, ENADE, militares).

Esta é a página {numero_pagina} de uma prova de {materia}.

Analise a imagem com atenção total — leia textos, gráficos, mapas, tabelas, obras de arte
e qualquer elemento visual que faça parte das questões.

Para CADA questão encontrada nesta página, retorne um JSON com este formato exato:
[
  {{
    "numero": <número da questão>,
    "enunciado": "<enunciado completo, incluindo descrição de qualquer elemento visual>",
    "alternativas": {{
      "A": "<texto>",
      "B": "<texto>",
      "C": "<texto>",
      "D": "<texto>",
      "E": "<texto>"
    }},
    "gabarito": "<letra correta: A, B, C, D ou E>",
    "explicacao": "<explicação didática em até 2 parágrafos: por que a resposta está correta e por que as outras estão erradas>",
    "tem_elemento_visual": <true se havia gráfico/imagem/mapa, false caso contrário>
  }}
]

Se não houver questões nesta página (ex: página de rosto, instruções), retorne: []

Retorne SOMENTE o JSON. Sem markdown, sem texto extra.
"""

    img_bytes = base64.b64decode(pagina_b64)
    imagem    = Image.open(io.BytesIO(img_bytes))

    # Via gerar_com_retry, e não direto: uma prova tem dezenas de páginas e
    # um 429 no meio derrubava o job inteiro. O wrapper já existia — quem o
    # usava eram as rotas de geração, que saíram.
    resposta = gerar_com_retry(
        [imagem, prompt],
        generation_config={
            "max_output_tokens": 4000,
            "temperature":       0.3,
        }
    )

    try:
        usage = resposta.usage_metadata
        registrar_uso_tokens(
            operacao      = f"pagina_{numero_pagina}",
            input_tokens  = usage.prompt_token_count,
            output_tokens = usage.candidates_token_count,
            simulado_id   = simulado_id
        )
    except AttributeError:
        registrar_uso_tokens(
            operacao=f"pagina_{numero_pagina}",
            input_tokens=0, output_tokens=0, simulado_id=simulado_id
        )

    try:
        candidato = resposta.candidates[0] if resposta.candidates else None
        if candidato:
            fr = getattr(candidato, "finish_reason", None)
            fr_num = int(fr) if fr is not None else 0
            if fr_num == 4:
                print(f"[GEMINI] ⚠ Página {numero_pagina}: BLOQUEADO por copyright")
                return []
            if fr_num == 3:
                print(f"[GEMINI] ⚠ Página {numero_pagina}: BLOQUEADO por filtro de segurança")
                return []
    except Exception:
        pass

    try:
        raw = limpar_control_chars(resposta.text.strip())
    except (ValueError, AttributeError) as e:
        msg = str(e).lower()
        if "recitation" in msg or "copyrighted" in msg or "finish_reason" in msg:
            print(f"[GEMINI] ⚠ Página {numero_pagina}: bloqueado por copyright/safety. Pulando.")
        else:
            print(f"[GEMINI] ⚠ Página {numero_pagina}: erro ao ler resposta — {e}")
        return []

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        questoes = json.loads(raw)
        if questoes:
            print(f"[GEMINI] Página {numero_pagina}: {len(questoes)} questão(ões) extraída(s)")
        return questoes if isinstance(questoes, list) else []
    except json.JSONDecodeError:
        print(f"[GEMINI] Página {numero_pagina}: nenhuma questão ou erro de parse")
        return []


def processar_pdf_completo(
    pdf_bytes: bytes,
    materia: str,
    quantidade: int,
    simulado_id: str
) -> tuple:
    """Processa o PDF inteiro página por página."""
    paginas    = pdf_para_imagens_base64(pdf_bytes)
    todas      = []
    paginas_bloqueadas = 0
    paginas_com_erro   = 0

    for i, pagina_b64 in enumerate(paginas, start=1):
        if len(todas) >= quantidade:
            print(f"[PDF] Quantidade {quantidade} atingida — parando na página {i}")
            break

        try:
            questoes_pagina = extrair_questoes_e_gabarito_por_pagina(
                pagina_b64, i, materia, simulado_id
            )
            if not questoes_pagina:
                paginas_bloqueadas += 1
            todas.extend(questoes_pagina)
        except Exception as e:
            paginas_com_erro += 1
            print(f"[PDF] ⚠ Erro inesperado na página {i}: {e}. Continuando próxima página.")
            continue

    if paginas_bloqueadas > 0:
        print(f"[PDF] ⚠ {paginas_bloqueadas} página(s) sem questões (provavelmente bloqueio por copyright)")
    if paginas_com_erro > 0:
        print(f"[PDF] ❌ {paginas_com_erro} página(s) com erro")
    print(f"[PDF] Total extraído: {len(todas)} questões")

    todas = todas[:quantidade]

    questoes_limpas = []
    gabarito_final  = []

    for q in todas:
        questoes_limpas.append({
            "numero":             q.get("numero"),
            "enunciado":          q.get("enunciado", ""),
            "alternativas":       q.get("alternativas", {}),
            "materia":            materia,
            "tem_elemento_visual": q.get("tem_elemento_visual", False)
        })
        gabarito_final.append({
            "numero":           q.get("numero"),
            "resposta_correta": q.get("gabarito", "?"),
            "explicacao":       q.get("explicacao", "")
        })

    return questoes_limpas, gabarito_final


# ──────────────────────────────────────────────────────
#  BLOCO 6 — FIREBASE: SALVAR E BUSCAR
#  >>> AQUI: validação antes de salvar (protege as 3 rotas) <<<
# ──────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════
#  DEDUPLICAÇÃO DE QUESTÕES
#
#  Os geradores procedurais sorteiam parâmetros de um espaço finito.
#  Num único simulado o montador já evita repetição, mas entre chamadas
#  diferentes a mesma questão pode reaparecer — e o aluno percebe.
#
#  A checagem usa um HASH do enunciado normalizado, gravado num campo
#  indexável. Comparar o texto inteiro exigiria varrer a coleção;
#  comparar o hash é uma consulta por igualdade.
# ══════════════════════════════════════════════════════════════════

import hashlib as _hashlib


def _hash_enunciado(enunciado: str) -> str:
    """
    Identidade da questão: hash do enunciado normalizado.

    Normaliza espaços e caixa para que diferenças irrelevantes de
    formatação não escapem da deduplicação. O gabarito NÃO entra no hash:
    duas questões com o mesmo enunciado são a mesma questão, ainda que as
    alternativas tenham sido embaralhadas de forma diferente.
    """
    texto = " ".join(str(enunciado or "").lower().split())
    return _hashlib.sha256(texto.encode("utf-8")).hexdigest()[:32]


def _hashes_existentes(materia: str, limite: int = 5000) -> set:
    """
    Carrega os hashes já gravados para a matéria.

    Uma consulta só, em vez de uma por questão. O limite existe porque
    o custo cresce com o acervo; acima dele, aceita-se o risco de uma
    repetição eventual em troca de latência previsível.
    """
    try:
        docs = (db.collection("questoes")
                  .where("materia", "==", materia)
                  .limit(limite)
                  .stream())
        return {d.to_dict().get("hash_enunciado") for d in docs
                if d.to_dict().get("hash_enunciado")}
    except Exception as e:
        log.warning(f"[DEDUP] Não foi possível carregar hashes: {e}")
        return set()


def salvar_questoes_banco(questoes: list, gabarito: list, concurso: str, ano: int, materia: str):
    """
    Salva cada questão individualmente no banco 'questoes'.
    >>> v5: valida cada questão ANTES de salvar. Descarta as ruins. <<<

    Casa questão <-> gabarito por POSIÇÃO (índice), não pelo campo 'numero'.
    As duas listas são sempre montadas no mesmo loop, na mesma ordem, então
    o índice é o vínculo confiável. Casar por 'numero' seria frágil: o Gemini
    às vezes repete o número (colisão -> uma questão pega o gabarito de outra)
    ou omite (None). Por índice, cada questão recebe exatamente o seu gabarito.
    """
    salvas      = 0
    descartadas = 0
    repetidas   = 0

    # Carrega uma vez os hashes já existentes desta matéria
    vistos = _hashes_existentes(materia)

    for idx, q in enumerate(questoes):
        num = q.get("numero", idx + 1)
        gb  = gabarito[idx] if idx < len(gabarito) else {}

        # Monta objeto pra validação (junta questão + gabarito)
        q_para_validar = {
            "enunciado":    q.get("enunciado", ""),
            "alternativas": q.get("alternativas", {}),
            "gabarito":     gb.get("resposta_correta", ""),
            "explicacao":   gb.get("explicacao", ""),
        }
        ok, motivo = validar_questao(q_para_validar)
        if not ok:
            descartadas += 1
            print(f"[VALIDAÇÃO] ✗ Questão {num} descartada: {motivo}")
            continue

        # Deduplicação: mesma questão já está no banco?
        h = _hash_enunciado(q.get("enunciado", ""))
        if h in vistos:
            repetidas += 1
            continue
        vistos.add(h)

        db.collection("questoes").add({
            "concurso":          concurso,
            "ano":               ano,
            "materia":           materia,
            "numero_questao":    num,
            "enunciado":         q.get("enunciado", ""),
            "alternativas":      q.get("alternativas", {}),
            "gabarito":          gb.get("resposta_correta", "?"),
            "explicacao_ia":     gb.get("explicacao", ""),
            "tem_elemento_visual": q.get("tem_elemento_visual", False),
            "hash_enunciado":    h,
            "validado":          True,
            "ativo":             True,
            "criado_em":         datetime.now(timezone.utc)
        })
        salvas += 1

    if descartadas:
        print(f"[VALIDAÇÃO] {descartadas} questão(ões) descartada(s) por qualidade.")
    if repetidas:
        print(f"[DEDUP] {repetidas} questão(ões) já existiam no banco — não regravadas.")
    print(f"[FIREBASE] {salvas} questões salvas no banco")


def salvar_simulado_firebase(simulado_id: str, questoes: list, gabarito: list, meta: dict):
    """Salva o simulado (sem gabarito) e o gabarito em coleções separadas."""
    db.collection("simulados").document(simulado_id).set({
        "simulado_id": simulado_id,
        "questoes":    questoes,
        "meta":        meta,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })
    db.collection("gabaritos").document(simulado_id).set({
        "simulado_id": simulado_id,
        "gabarito":    gabarito,
        "criado_em":   datetime.now(timezone.utc)
    })
    print(f"[FIREBASE] Simulado {simulado_id} salvo")


def buscar_questoes_banco(concurso: str, materia: str, quantidade: int, ano: Optional[int] = None) -> tuple:
    """Busca questões já processadas no banco e retorna (questoes, gabarito)."""
    query = db.collection("questoes") \
               .where("concurso", "==", concurso) \
               .where("materia",  "==", materia) \
               .where("ativo",    "==", True)

    if ano:
        query = query.where("ano", "==", ano)

    docs = list(query.limit(quantidade).stream())

    questoes = []
    gabarito = []

    for doc in docs:
        d = doc.to_dict()
        questoes.append({
            "numero":             d.get("numero_questao"),
            "enunciado":          d.get("enunciado", ""),
            "alternativas":       d.get("alternativas", {}),
            "materia":            d.get("materia", materia),
            "tem_elemento_visual": d.get("tem_elemento_visual", False)
        })
        gabarito.append({
            "numero":           d.get("numero_questao"),
            "resposta_correta": d.get("gabarito", "?"),
            "explicacao":       d.get("explicacao_ia", "")
        })

    print(f"[FIREBASE] {len(questoes)} questões recuperadas do banco")
    return questoes, gabarito


# ──────────────────────────────────────────────────────
#  BLOCO 7 — ORQUESTRADOR PRINCIPAL
# ──────────────────────────────────────────────────────

def montar_simulado(
    concurso:  str,
    materia:   str,
    quantidade: int,
    ano:       Optional[int],
    fonte:     str
) -> tuple:
    """Lógica de decisão: banco / inep / automatico."""

    if fonte == "banco":
        questoes, gabarito = buscar_questoes_banco(concurso, materia, quantidade, ano)
        if not questoes:
            raise HTTPException(status_code=404, detail="Nenhuma questão no banco para este filtro.")
        return questoes, gabarito

    if fonte == "automatico" and ano and prova_ja_processada(concurso, ano, materia):
        questoes, gabarito = buscar_questoes_banco(concurso, materia, quantidade, ano)
        if questoes:
            return questoes, gabarito

    if fonte in ("inep", "automatico"):
        if not ano:
            raise HTTPException(status_code=400, detail="Informe o 'ano' para buscar no INEP.")

        pdf_url = buscar_pdf_inep(ano, materia)
        if not pdf_url:
            if fonte == "automatico":
                print("[ORQUESTRADOR] INEP falhou — tentando banco Firebase...")
                questoes, gabarito = buscar_questoes_banco(concurso, materia, quantidade, ano)
                if questoes:
                    return questoes, gabarito
            raise HTTPException(status_code=404, detail="PDF não encontrado no INEP.")

        pdf_bytes = baixar_pdf(pdf_url)
        if not pdf_bytes:
            raise HTTPException(status_code=502, detail="Falha ao baixar o PDF do INEP.")

        simulado_id_temp = str(uuid.uuid4())

        questoes, gabarito = processar_pdf_completo(
            pdf_bytes, materia, quantidade, simulado_id_temp
        )

        if not questoes:
            raise HTTPException(status_code=500, detail="Claude não encontrou questões no PDF.")

        salvar_questoes_banco(questoes, gabarito, concurso, ano, materia)
        marcar_prova_processada(concurso, ano, materia, len(questoes))

        return questoes, gabarito

    raise HTTPException(status_code=400, detail="Fonte inválida.")


# ──────────────────────────────────────────────────────
#  ROTAS DA API
# ──────────────────────────────────────────────────────

@app.get("/")
def raiz():
    """Healthcheck completo."""
    status_geral = "online"
    servicos = {}

    try:
        db.collection("provas_analisadas").limit(1).get()
        servicos["firebase"] = {"status": "ok", "tipo": "firestore"}
    except Exception as e:
        servicos["firebase"] = {"status": "erro", "detalhe": str(e)[:100]}
        status_geral = "degradado"

    servicos["gemini"] = {
        "status": "ok" if GEMINI_API_KEY else "sem_chave",
        "modelo": "gemini-2.5-flash-lite",
    }
    if not GEMINI_API_KEY:
        status_geral = "degradado"

    try:
        tokens_hoje = tokens_usados_hoje()
        servicos["quota"] = {
            "tokens_hoje":  tokens_hoje,
            "limite_dia":   LIMITE_TOKENS_DIA,
            "restante":     LIMITE_TOKENS_DIA - tokens_hoje,
            "percentual":   round((tokens_hoje / LIMITE_TOKENS_DIA) * 100, 1),
        }
    except Exception:
        servicos["quota"] = {"status": "indisponivel"}

    return {
        "status":   status_geral,
        "app":      "Nivelis API de Simulados",
        "versao":   "2.2.0",
        "servicos": servicos,
        "rotas_principais": {
            "Geração": "POST /procedural/simulado  |  POST /procedural/gerar",
            "Banco":   "POST /montar            |  GET  /procedural/topicos",
            "Provas":  "GET /enade/disponiveis  |  POST /enade/extrair",
            "Livros":  "GET /livros             |  GET  /livro/{livro_id}",
            "Estudo":  "POST /simulado          |  POST /simulado/{id}/resultado",
            "Admin":   "GET /admin/metricas     |  GET /tokens",
            "Docs":    "GET /docs (interface Swagger)",
        }
    }


@app.get("/concursos", tags=["Administração"], summary="Concursos suportados")
def listar_concursos():
    return {
        "concursos": [
            {"id": k, "materias": v}
            for k, v in MATERIAS.items()
        ]
    }


@app.get("/enade/disponiveis", tags=["Provas oficiais"], summary="Provas ENADE disponíveis")
def listar_provas_disponiveis(ano: Optional[AnoEnadeEnum] = None):
    """Lista quais áreas têm prova disponível em cada ano do ENADE."""
    ano = int(ano) if isinstance(ano, Enum) else ano

    provas = {}
    for ano_disp, grupos in CICLO_ENADE.items():
        if ano is not None and ano_disp != ano:
            continue

        areas_do_ano = []
        for grupo in grupos:
            areas_do_ano.extend(AREAS_POR_GRUPO.get(grupo, []))

        provas[str(ano_disp)] = {
            "grupo":  grupos[0] if len(grupos) == 1 else grupos,
            "areas":  sorted(areas_do_ano),
            "total":  len(areas_do_ano),
        }

    if ano is not None and not provas:
        raise HTTPException(
            status_code=404,
            detail=f"Ano {ano} não tem prova catalogada. "
                   f"Anos disponíveis: {sorted(CICLO_ENADE.keys())}"
        )

    return {
        "anos_disponiveis": sorted(CICLO_ENADE.keys()),
        "provas":           provas,
        "ciclo_explicado": {
            "sociais_aplicadas":          "Administração, Direito, Psicologia, Economia, Comunicação, Turismo, Tecnólogos de gestão...",
            "saude_engenharias_exatas":   "Medicina, Enfermagem, Engenharias, Biologia, Química, Física, Matemática, Arquitetura...",
            "licenciaturas":              "Pedagogia, Letras, História, Geografia, Artes, Filosofia, Sociologia, Formação Geral Docente...",
        },
        "como_usar": {
            "geral":   "Use os nomes das áreas exatamente como aparecem em 'areas'",
            "exemplo": "POST /enade/extrair?ano=2022&area=sociais_aplicadas",
            "obs":     "Anos com prova: 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025 (2020 foi cancelado pela pandemia)",
        },
    }


@app.get("/enade/testar-busca", tags=["Administração"], summary="Testa a busca de provas ENADE")
def testar_busca_url(ano: AnoEnadeEnum, area: AreaEnadeEnum):
    """Rota de teste para verificar se conseguimos achar e baixar o PDF (sem gastar Gemini)."""
    ano  = int(ano)   if isinstance(ano,  Enum) else ano
    area = area.value if isinstance(area, Enum) else area

    resultado = {
        "ano":              ano,
        "area":             area,
        "etapas": [],
        "sucesso":          False,
        "url_final":        None,
        "tamanho_pdf_kb":   None,
        "metodo_usado":     None,
    }

    erro_ciclo = validar_area_ano(ano, area)
    if erro_ciclo:
        resultado["etapas"].append({
            "etapa":   "ciclo_trienal",
            "sucesso": False,
            "msg":     erro_ciclo,
        })
        return resultado
    resultado["etapas"].append({
        "etapa":   "ciclo_trienal",
        "sucesso": True,
        "msg":     "Área permitida no ano",
    })

    url_padrao = f"https://download.inep.gov.br/enade/provas_e_gabaritos/{ano}_PV_{area}.pdf"
    pdf_bytes  = baixar_pdf(url_padrao)
    if pdf_bytes:
        resultado["etapas"].append({
            "etapa":   "url_padrao",
            "sucesso": True,
            "url":     url_padrao,
        })
        resultado["sucesso"]        = True
        resultado["url_final"]      = url_padrao
        resultado["tamanho_pdf_kb"] = round(len(pdf_bytes) / 1024)
        resultado["metodo_usado"]   = "url_padrao"
        return resultado
    resultado["etapas"].append({
        "etapa":   "url_padrao",
        "sucesso": False,
        "url":     url_padrao,
        "msg":     "Retornou 404 ou erro",
    })

    if area in VARIACOES_AREA_INEP:
        for variacao in VARIACOES_AREA_INEP[area]:
            url_variacao = f"https://download.inep.gov.br/enade/provas_e_gabaritos/{ano}_PV_{variacao}.pdf"
            pdf_bytes    = baixar_pdf(url_variacao)
            if pdf_bytes:
                resultado["etapas"].append({
                    "etapa":    "variacao_conhecida",
                    "sucesso":  True,
                    "variacao": variacao,
                    "url":      url_variacao,
                })
                resultado["sucesso"]        = True
                resultado["url_final"]      = url_variacao
                resultado["tamanho_pdf_kb"] = round(len(pdf_bytes) / 1024)
                resultado["metodo_usado"]   = f"variacao_conhecida ({variacao})"
                return resultado
        resultado["etapas"].append({
            "etapa":   "variacao_conhecida",
            "sucesso": False,
            "msg":     f"Nenhuma das {len(VARIACOES_AREA_INEP[area])} variações funcionou",
        })
    else:
        resultado["etapas"].append({
            "etapa":   "variacao_conhecida",
            "sucesso": False,
            "msg":     "Sem variações cadastradas para essa área",
        })

    url_encontrada = buscar_url_inep(ano, area)
    if url_encontrada:
        pdf_bytes = baixar_pdf(url_encontrada)
        if pdf_bytes:
            resultado["etapas"].append({
                "etapa":   "playwright_inep",
                "sucesso": True,
                "url":     url_encontrada,
            })
            resultado["sucesso"]        = True
            resultado["url_final"]      = url_encontrada
            resultado["tamanho_pdf_kb"] = round(len(pdf_bytes) / 1024)
            resultado["metodo_usado"]   = "playwright_inep"
            return resultado
        resultado["etapas"].append({
            "etapa":   "playwright_inep",
            "sucesso": False,
            "url":     url_encontrada,
            "msg":     "Achou URL mas falhou ao baixar",
        })
    else:
        resultado["etapas"].append({
            "etapa":   "playwright_inep",
            "sucesso": False,
            "msg":     "Não encontrou link no site INEP",
        })

    return resultado


@app.get("/enem/testar-busca", tags=["Administração"], summary="Testa a busca de provas ENEM")
def testar_busca_url_enem(
    ano:     AnoEnemEnum,
    dia:     int = Query(default=1, ge=1, le=2, description="1 = linguagens+humanas; 2 = matemática+natureza"),
    caderno: int = Query(default=1, ge=1, le=9, description="Cor do caderno (1=azul, 2=amarelo, ...)"),
):
    """Rota de teste para verificar se conseguimos achar e baixar o PDF ENEM (sem gastar Gemini)."""
    ano = int(ano) if isinstance(ano, Enum) else ano

    resultado = {
        "ano":            ano,
        "dia":            dia,
        "caderno":        caderno,
        "etapas":         [],
        "sucesso":        False,
        "url_final":      None,
        "tamanho_pdf_kb": None,
        "metodo_usado":   None,
    }

    url_padrao = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{caderno}.pdf"
    pdf_bytes  = baixar_pdf(url_padrao)
    if pdf_bytes:
        resultado["etapas"].append({
            "etapa":   "url_padrao",
            "sucesso": True,
            "url":     url_padrao,
        })
        resultado["sucesso"]        = True
        resultado["url_final"]      = url_padrao
        resultado["tamanho_pdf_kb"] = round(len(pdf_bytes) / 1024)
        resultado["metodo_usado"]   = "url_padrao"
        return resultado
    resultado["etapas"].append({
        "etapa":   "url_padrao",
        "sucesso": False,
        "url":     url_padrao,
        "msg":     "Retornou 404 ou erro",
    })

    cadernos_tentados = []
    for cd_alt in range(1, 10):
        if cd_alt == caderno:
            continue
        url_alt = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{cd_alt}.pdf"
        pdf_alt = baixar_pdf(url_alt)
        cadernos_tentados.append(cd_alt)
        if pdf_alt:
            resultado["etapas"].append({
                "etapa":           "caderno_alternativo",
                "sucesso":         True,
                "caderno":         cd_alt,
                "url":             url_alt,
                "tentados":        cadernos_tentados,
            })
            resultado["sucesso"]        = True
            resultado["url_final"]      = url_alt
            resultado["tamanho_pdf_kb"] = round(len(pdf_alt) / 1024)
            resultado["metodo_usado"]   = f"caderno_alternativo (CD{cd_alt})"
            return resultado
    resultado["etapas"].append({
        "etapa":    "caderno_alternativo",
        "sucesso":  False,
        "tentados": cadernos_tentados,
        "msg":      "Nenhum caderno funcionou",
    })

    url_encontrada = buscar_url_inep_enem(ano, dia, caderno)
    if url_encontrada:
        pdf_bytes = baixar_pdf(url_encontrada)
        if pdf_bytes:
            resultado["etapas"].append({
                "etapa":   "playwright_inep",
                "sucesso": True,
                "url":     url_encontrada,
            })
            resultado["sucesso"]        = True
            resultado["url_final"]      = url_encontrada
            resultado["tamanho_pdf_kb"] = round(len(pdf_bytes) / 1024)
            resultado["metodo_usado"]   = "playwright_inep"
            return resultado
        resultado["etapas"].append({
            "etapa":   "playwright_inep",
            "sucesso": False,
            "url":     url_encontrada,
            "msg":     "Achou URL mas falhou ao baixar",
        })
    else:
        resultado["etapas"].append({
            "etapa":   "playwright_inep",
            "sucesso": False,
            "msg":     "Não encontrou link no site INEP",
        })

    return resultado




# ──────────────────────────────────────────────
#  ENEM — Análise de prova oficial + geração
# ──────────────────────────────────────────────

ENEM_AREAS = {
    "linguagens":   {"dia": 1, "nome": "Linguagens, Códigos e suas Tecnologias"},
    "humanas":      {"dia": 1, "nome": "Ciências Humanas e suas Tecnologias"},
    "natureza":     {"dia": 2, "nome": "Ciências da Natureza e suas Tecnologias"},
    "matematica":   {"dia": 2, "nome": "Matemática e suas Tecnologias"},
}


@app.get("/enem/disponiveis", tags=["Provas oficiais"], summary="Provas ENEM disponíveis")
def listar_enem_disponivel():
    """Lista as áreas e anos do ENEM disponíveis para geração de questões."""
    return {
        "anos_disponiveis": list(range(2009, 2026)),
        "areas": {
            chave: {
                "nome":         info["nome"],
                "dia_aplicado": info["dia"],
            }
            for chave, info in ENEM_AREAS.items()
        },
        "como_usar": {
            "exemplo": "POST /enem/extrair?ano=2024&area=matematica",
            "obs":     "ENEM tem 2 dias de prova. Dia 1: linguagens + humanas. Dia 2: natureza + matemática.",
        },
    }


# ──────────────────────────────────────────────────────
#  ROTA: ENEM em LOTES — divide pedidos grandes em 5+5+5
# ──────────────────────────────────────────────────────







# ──────────────────────────────────────────────
#  LIVROS — Geração de questões baseadas em livros
# ──────────────────────────────────────────────


@app.get("/livros", tags=["Livros"], summary="Lista o acervo indexado")
def listar_livros():
    """Lista todos os livros indexados no Firebase."""
    docs = db.collection("livros").stream()
    livros = []

    for doc in docs:
        data = doc.to_dict()
        livros.append({
            "livro_id":         data.get("livro_id"),
            "titulo":           data.get("titulo"),
            "autor":            data.get("autor"),
            "disciplina":       data.get("disciplina"),
            "descricao":        data.get("descricao"),
            "total_capitulos":  data.get("total_capitulos"),
            "total_paginas":    data.get("total_paginas"),
            "indexado_em":      data.get("indexado_em"),
        })

    return {
        "total":  len(livros),
        "livros": livros,
    }


@app.get("/livro/{livro_id}", tags=["Livros"], summary="Detalhes de um livro")
def detalhar_livro(livro_id: str):
    """Retorna detalhes completos de um livro, incluindo lista de capítulos."""
    doc = db.collection("livros").document(livro_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Livro não encontrado.")
    return doc.to_dict()




@app.post("/enade/extrair", tags=["Extração de provas"], summary="Extrai questões reais do ENADE")
def extrair_prova_enade(
    ano:        int,
    _adm:       bool = Depends(exigir_admin),
    area:       str = "formacao_geral_docente",
    quantidade: int = 3
):
    """Extrai questões de uma prova oficial do ENADE (copia da prova)."""
    pdf_url = f"https://download.inep.gov.br/enade/provas_e_gabaritos/{ano}_PV_{area}.pdf"
    print(f"[ENADE] Tentando baixar: {pdf_url}")

    chave_cache = f"enade_{ano}_{area}"
    if prova_ja_processada("enade", ano, area):
        print(f"[CACHE] Prova {chave_cache} já processada — retornando do Firebase")
        questoes, gabarito = buscar_questoes_banco("enade", area, quantidade, ano)
        if questoes:
            simulado_id = str(uuid.uuid4())
            salvar_simulado_firebase(simulado_id, questoes, gabarito, {
                "concurso":  "enade",
                "ano":       ano,
                "area":      area,
                "fonte":     "cache"
            })
            return {
                "simulado_id": simulado_id,
                "origem":      "cache",
                "ano":         ano,
                "area":        area,
                "total":       len(questoes),
                "questoes":    questoes
            }

    pdf_bytes = baixar_pdf(pdf_url)
    if not pdf_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"PDF não encontrado: {pdf_url}\n"
                   f"Verifique se o ano e a área estão corretos."
        )

    simulado_id = str(uuid.uuid4())
    questoes, gabarito = processar_pdf_completo(
        pdf_bytes, area, quantidade, simulado_id
    )

    if not questoes:
        raise HTTPException(
            status_code=500,
            detail="Gemini não conseguiu extrair questões do PDF."
        )

    salvar_questoes_banco(questoes, gabarito, "enade", ano, area)
    marcar_prova_processada("enade", ano, area, len(questoes))

    salvar_simulado_firebase(simulado_id, questoes, gabarito, {
        "concurso":  "enade",
        "ano":       ano,
        "area":      area,
        "fonte":     "inep_direto"
    })

    return {
        "simulado_id": simulado_id,
        "origem":      "inep_direto",
        "ano":         ano,
        "area":        area,
        "total":       len(questoes),
        "questoes":    questoes,
        "url_pdf":     pdf_url
    }


@app.post("/enem/extrair", tags=["Extração de provas"], summary="Extrai questões reais do ENEM")
def extrair_prova_enem(
    ano:        AnoEnemEnum,
    _adm:       bool = Depends(exigir_admin),
    area:       AreaEnemEnum  = AreaEnemEnum.matematica,
    quantidade: int           = Query(default=45, ge=1, le=45, description="Até 45 questões (prova completa)"),
    caderno:    int           = Query(default=1, ge=1, le=9, description="Cor do caderno (1=azul, 5=ENEM 2025, ...)"),
):
    """Extrai questões REAIS de uma prova oficial do ENEM (copia da prova)."""
    ano = int(ano) if isinstance(ano, Enum) else ano
    area = area.value if isinstance(area, Enum) else area

    DIA_POR_AREA = {
        "linguagens":  1,
        "humanas":     1,
        "matematica":  2,
        "natureza":    2,
    }
    dia = DIA_POR_AREA.get(area, 2)

    chave_cache = f"enem_{ano}_{area}_cd{caderno}"

    if prova_ja_processada("enem", ano, area):
        print(f"[CACHE] Prova {chave_cache} já processada — retornando do Firebase")
        questoes, gabarito = buscar_questoes_banco("enem", area, quantidade, ano)
        if questoes:
            simulado_id = str(uuid.uuid4())
            salvar_simulado_firebase(simulado_id, questoes, gabarito, {
                "concurso":  "enem",
                "ano":       ano,
                "area":      area,
                "dia":       dia,
                "caderno":   caderno,
                "fonte":     "cache",
            })
            return {
                "simulado_id": simulado_id,
                "origem":      "cache",
                "ano":         ano,
                "area":        area,
                "total":       len(questoes),
                "questoes":    questoes,
            }

    pdf_url = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{caderno}.pdf"
    print(f"[ENEM] Tentando baixar: {pdf_url}")
    pdf_bytes = baixar_pdf(pdf_url)

    if not pdf_bytes:
        print(f"[ENEM] Caderno {caderno} não achado. Tentando outras cores...")
        for cd_alt in range(1, 10):
            if cd_alt == caderno:
                continue
            url_alt = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{cd_alt}.pdf"
            pdf_bytes = baixar_pdf(url_alt)
            if pdf_bytes:
                print(f"[ENEM] ✅ Encontrado no caderno {cd_alt}")
                caderno = cd_alt
                pdf_url = url_alt
                break

    if not pdf_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"PDF não encontrado: testei cadernos 1-9 para ENEM {ano} dia {dia}."
        )

    print(f"[ENEM] Iniciando extração de até {quantidade} questões via Gemini...")
    simulado_id = str(uuid.uuid4())
    questoes, gabarito = processar_pdf_completo(
        pdf_bytes, area, quantidade, simulado_id
    )

    if not questoes:
        raise HTTPException(
            status_code=500,
            detail="Gemini não conseguiu extrair questões do PDF."
        )

    salvar_questoes_banco(questoes, gabarito, "enem", ano, area)
    marcar_prova_processada("enem", ano, area, len(questoes))

    salvar_simulado_firebase(simulado_id, questoes, gabarito, {
        "concurso":  "enem",
        "ano":       ano,
        "area":      area,
        "dia":       dia,
        "caderno":   caderno,
        "fonte":     "inep_direto",
    })

    return {
        "simulado_id": simulado_id,
        "origem":      "inep_direto",
        "ano":         ano,
        "area":        area,
        "dia":         dia,
        "caderno":     caderno,
        "total":       len(questoes),
        "questoes":    questoes,
        "url_pdf":     pdf_url,
    }


@app.post("/simulado", tags=["Sessões e resultados"], summary="Cria um simulado")
def gerar_simulado(
    concurso:   str,
    materia:    str,
    quantidade: int = 10,
    ano:        Optional[int] = None,
    fonte:      str = "automatico"
):
    """Gera um simulado completo."""
    concurso = concurso.lower().strip()
    materia  = materia.lower().strip()

    if concurso not in MATERIAS:
        raise HTTPException(status_code=400, detail=f"Concurso inválido. Use: {list(MATERIAS.keys())}")
    if materia not in MATERIAS[concurso]:
        raise HTTPException(status_code=400, detail=f"Matéria inválida. Use: {MATERIAS[concurso]}")
    if not (1 <= quantidade <= 90):
        raise HTTPException(status_code=400, detail="Quantidade deve ser entre 1 e 90.")
    if fonte not in ("inep", "banco", "automatico"):
        raise HTTPException(status_code=400, detail="Fonte inválida. Use: 'inep', 'banco' ou 'automatico'.")

    questoes, gabarito = montar_simulado(concurso, materia, quantidade, ano, fonte)

    simulado_id = str(uuid.uuid4())
    meta = {
        "concurso":  concurso,
        "materia":   materia,
        "quantidade": len(questoes),
        "ano":       ano,
        "fonte":     fonte
    }
    salvar_simulado_firebase(simulado_id, questoes, gabarito, meta)

    return {
        "simulado_id": simulado_id,
        "meta":        meta,
        "total":       len(questoes),
        "questoes":    questoes
    }


@app.get("/simulado/{simulado_id}", tags=["Sessões e resultados"], summary="Consulta um simulado")
def buscar_simulado(simulado_id: str):
    """Busca um simulado já gerado pelo ID."""
    doc = db.collection("simulados").document(simulado_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Simulado não encontrado.")
    dados = doc.to_dict()
    return {
        "simulado_id": simulado_id,
        "meta":        dados.get("meta", {}),
        "total":       len(dados.get("questoes", [])),
        "questoes":    dados.get("questoes", [])
    }


@app.get("/simulado/{simulado_id}/gabarito", tags=["Sessões e resultados"], summary="Gabarito do simulado")
def consultar_gabarito_simulado(simulado_id: str):
    """Consulta direta do gabarito de um simulado (DEBUG)."""
    doc_gab = db.collection("gabaritos").document(simulado_id).get()
    if not doc_gab.exists:
        raise HTTPException(status_code=404, detail="Gabarito não encontrado.")

    dados    = doc_gab.to_dict()
    gabarito = dados.get("gabarito", [])

    return {
        "simulado_id":    simulado_id,
        "total_questoes": len(gabarito),
        "criado_em":      dados.get("criado_em"),
        "gabarito":       gabarito,
        "aviso":          "Rota DEBUG — em produção use POST /simulado/{id}/resultado.",
    }


@app.get("/simulado/{simulado_id}/completo", tags=["Sessões e resultados"], summary="Simulado com gabarito")
def consultar_simulado_completo(simulado_id: str):
    """Retorna o simulado COMPLETO: questões + gabaritos + explicações."""
    doc_sim = db.collection("simulados").document(simulado_id).get()
    if not doc_sim.exists:
        raise HTTPException(status_code=404, detail="Simulado não encontrado.")

    doc_gab = db.collection("gabaritos").document(simulado_id).get()
    if not doc_gab.exists:
        raise HTTPException(status_code=404, detail="Gabarito não encontrado para este simulado.")

    dados_sim = doc_sim.to_dict()
    dados_gab = doc_gab.to_dict()
    questoes  = dados_sim.get("questoes", [])
    gabarito  = dados_gab.get("gabarito", [])

    gab_por_num = {g.get("numero"): g for g in gabarito}
    questoes_completas = []

    for q in questoes:
        num = q.get("numero")
        gab_item = gab_por_num.get(num, {})

        questoes_completas.append({
            "numero":            num,
            "contexto":          q.get("contexto", ""),
            "enunciado":         q.get("enunciado", ""),
            "alternativas":      q.get("alternativas", {}),
            "topico_inspiracao": q.get("topico_inspiracao", ""),
            "capitulo_origem":   q.get("capitulo_origem", ""),
            "materia":           q.get("materia", ""),
            "resposta_correta":  gab_item.get("resposta_correta"),
            "explicacao":        gab_item.get("explicacao"),
        })

    questoes_completas.sort(key=lambda x: x.get("numero", 0))

    return {
        "simulado_id":    simulado_id,
        "meta":           dados_sim.get("meta", {}),
        "total_questoes": len(questoes_completas),
        "questoes":       questoes_completas,
        "aviso":          "⚠️ Rota DEBUG — em produção use o fluxo gerar → resultado.",
    }


@app.post("/simulado/{simulado_id}/resultado", tags=["Sessões e resultados"], summary="Corrige as respostas")
def corrigir_simulado(
    simulado_id: str,
    respostas:   dict,
    usuario:     dict = Depends(obter_usuario_atual),
):
    """Recebe respostas do usuário e libera o gabarito com explicações."""
    user_id = usuario["uid"]

    doc_gab = db.collection("gabaritos").document(simulado_id).get()
    if not doc_gab.exists:
        raise HTTPException(status_code=404, detail="Gabarito não encontrado.")

    gabarito          = doc_gab.to_dict().get("gabarito", [])
    respostas_usuario = respostas.get("respostas", {})
    acertos = erros   = 0
    detalhes          = []

    for item in gabarito:
        num     = str(item["numero"])
        correta = item["resposta_correta"]
        marcada = respostas_usuario.get(num, "").upper()
        acertou = marcada == correta

        if acertou: acertos += 1
        else:       erros   += 1

        detalhes.append({
            "numero":           item["numero"],
            "resposta_correta": correta,
            "resposta_usuario": marcada,
            "acertou":          acertou,
            "explicacao":       item["explicacao"]
        })

    total          = acertos + erros
    aproveitamento = round((acertos / total) * 100, 1) if total > 0 else 0

    resultado_id = str(uuid.uuid4())
    db.collection("resultados").document(resultado_id).set({
        "resultado_id":   resultado_id,
        "user_id":        user_id,
        "simulado_id":    simulado_id,
        "acertos":        acertos,
        "erros":          erros,
        "total":          total,
        "aproveitamento": aproveitamento,
        "detalhes":       detalhes,
        "finalizado_em":  datetime.now(timezone.utc),
    })

    return {
        "resultado_id":   resultado_id,
        "simulado_id":    simulado_id,
        "user_id":        user_id,
        "acertos":        acertos,
        "erros":          erros,
        "total":          total,
        "aproveitamento": f"{aproveitamento}%",
        "gabarito":       detalhes,
    }


# ──────────────────────────────────────────────────────
#  ROTA: Listar simulados disponíveis no banco
# ──────────────────────────────────────────────────────

@app.get("/disponiveis", tags=["Administração"], summary="Recursos disponíveis")
def listar_simulados_disponiveis(
    concurso: str           = Query(..., pattern="^(enem|enade)$", description="Tipo de concurso"),
    materia:  Optional[str] = Query(default=None, max_length=100, description="Filtrar por matéria/área (opcional)"),
    ano:      Optional[int] = Query(default=None, ge=2000, le=2030, description="Filtrar por ano (opcional)"),
    limite:   int           = Query(default=20, ge=1, le=100, description="Máximo de resultados"),
):

    concurso_norm = concurso.lower().strip()

    def normalizar_materia(valor):
        if not valor:
            return None
        v = str(valor).lower().strip()
        equivalencias = {
            "ciencias_humanas":  "humanas",
            "ciencias_natureza": "natureza",
            "ciencias da humanas":  "humanas",
            "ciencias da natureza": "natureza",
            "linguagem":   "linguagens",
            "matemática":  "matematica",
        }
        return equivalencias.get(v, v)

    materia_norm = normalizar_materia(materia)

    try:
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .where("ativo", "==", True) \
                  .limit(100)
        docs = list(query.stream())
    except Exception as e:
        log.warning(f"Query com 'ativo' falhou, tentando sem: {e}")
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .limit(100)
        docs = list(query.stream())

    simulados = []
    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        materia_raw = meta.get("materia") or meta.get("area")
        materia_doc = normalizar_materia(materia_raw)

        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        criado_em = d.get("criado_em")
        criado_iso = criado_em.isoformat() if hasattr(criado_em, "isoformat") else str(criado_em)

        simulados.append({
            "simulado_id":     d.get("simulado_id") or doc_snap.id,
            "concurso":        meta.get("concurso"),
            "materia":         materia_doc,
            "ano":             meta.get("ano"),
            "total_questoes":  len(d.get("questoes", [])),
            "criado_em":       criado_iso,
        })

        if len(simulados) >= limite:
            break

    simulados.sort(key=lambda s: s.get("criado_em", ""), reverse=True)

    return {
        "total":      len(simulados),
        "filtros":    {"concurso": concurso_norm, "materia": materia_norm, "ano": ano},
        "simulados":  simulados,
    }


@app.post("/montar", tags=["Sessões e resultados"], summary="Monta simulado a partir do banco")
def montar_simulado_do_banco(
    concurso:    str            = Query(..., pattern="^(enem|enade)$", description="Tipo de concurso"),
    quantidade:  int            = Query(default=20, ge=5, le=50, description="Quantidade de questões (5-50)"),
    materia:     Optional[str]  = Query(default=None, max_length=100, description="Filtrar por matéria/área"),
    ano:         Optional[int]  = Query(default=None, ge=2000, le=2030, description="Filtrar por ano"),
    embaralhar:  bool           = Query(default=True, description="Embaralhar questões"),
):
    """Cria simulado JUNTANDO questões de simulados já existentes. Zero custo Gemini."""
    import random

    def _normalizar_mat(valor):
        if not valor:
            return None
        v = str(valor).lower().strip()
        equivalencias = {
            "ciencias_humanas":  "humanas",
            "ciencias_natureza": "natureza",
            "ciencias da humanas":  "humanas",
            "ciencias da natureza": "natureza",
            "linguagem":   "linguagens",
            "matemática":  "matematica",
        }
        return equivalencias.get(v, v)

    concurso_norm = concurso.lower().strip()
    materia_norm  = _normalizar_mat(materia)

    try:
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .where("ativo", "==", True) \
                  .limit(100)
        docs = list(query.stream())
    except Exception as e:
        log.warning(f"Query com 'ativo' falhou: {e}")
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .limit(100)
        docs = list(query.stream())

    if not docs:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum simulado de '{concurso_norm}' encontrado no banco."
        )

    todas_questoes = []
    fontes_usadas  = []

    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        materia_doc = _normalizar_mat(meta.get("materia") or meta.get("area"))
        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        questoes_doc = d.get("questoes", [])
        if not questoes_doc:
            continue

        sim_id = d.get("simulado_id") or doc_snap.id
        for q in questoes_doc:
            q_copy = dict(q)
            q_copy["_origem_simulado"] = sim_id
            q_copy["_numero_original"] = q.get("numero")
            todas_questoes.append(q_copy)

        fontes_usadas.append(sim_id)

    if not todas_questoes:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma questão encontrada com os filtros (concurso={concurso_norm}, materia={materia_norm}, ano={ano})"
        )

    vistos = set()
    questoes_unicas = []
    for q in todas_questoes:
        enunciado = (q.get("enunciado") or "").strip()[:200]
        if enunciado and enunciado not in vistos:
            vistos.add(enunciado)
            questoes_unicas.append(q)

    if len(questoes_unicas) < 5:
        raise HTTPException(
            status_code=404,
            detail=f"Apenas {len(questoes_unicas)} questões únicas no banco. Mínimo é 5."
        )

    if embaralhar:
        random.shuffle(questoes_unicas)

    questoes_finais = questoes_unicas[:quantidade]

    gabarito_final = []
    for idx, q in enumerate(questoes_finais, start=1):
        sim_origem = q.get("_origem_simulado")
        numero_original = q.get("_numero_original")
        if sim_origem and numero_original is not None:
            try:
                gab_doc = db.collection("gabaritos").document(sim_origem).get()
                if gab_doc.exists:
                    gab_data = gab_doc.to_dict() or {}
                    gab_list = gab_data.get("gabarito", [])
                    for g in gab_list:
                        if g.get("numero") == numero_original:
                            gabarito_final.append({
                                "numero":           idx,
                                "resposta_correta": g.get("resposta_correta", "?"),
                                "explicacao":       g.get("explicacao", "")
                            })
                            break
            except Exception as e:
                log.warning(f"Erro ao buscar gabarito de {sim_origem}: {e}")

    questoes_limpas = []
    for idx, q in enumerate(questoes_finais, start=1):
        q_limpa = {k: v for k, v in q.items() if not k.startswith("_")}
        q_limpa["numero"] = idx
        questoes_limpas.append(q_limpa)

    novo_simulado_id = str(uuid.uuid4())

    meta_novo = {
        "concurso":         concurso_norm,
        "materia":          materia_norm,
        "ano":              ano,
        "quantidade":       len(questoes_limpas),
        "fonte":            "montado_do_banco",
        "simulados_origem": fontes_usadas[:10],
    }

    db.collection("simulados").document(novo_simulado_id).set({
        "simulado_id": novo_simulado_id,
        "questoes":    questoes_limpas,
        "meta":        meta_novo,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })

    if gabarito_final:
        db.collection("gabaritos").document(novo_simulado_id).set({
            "simulado_id": novo_simulado_id,
            "gabarito":    gabarito_final,
            "criado_em":   datetime.now(timezone.utc)
        })

    return {
        "simulado_id":      novo_simulado_id,
        "origem":           "montado_do_banco",
        "concurso":         concurso_norm,
        "materia":          materia_norm,
        "ano":              ano,
        "total_questoes":   len(questoes_limpas),
        "questoes":         questoes_limpas,
        "fonte_simulados":  fontes_usadas[:5],
        "custo_gemini":     0,
        "mensagem":         f"Simulado montado com {len(questoes_limpas)} questões do banco. Zero custo Gemini.",
    }


@app.get("/historico", tags=["Sessões e resultados"], summary="Histórico de simulados")
def historico_usuario(
    limite:  int  = 20,
    usuario: dict = Depends(obter_usuario_atual),
):
    """Retorna o histórico de simulados feitos pelo usuário autenticado."""
    user_id = usuario["uid"]
    limite  = min(max(limite, 1), 100)

    query = (
        db.collection("resultados")
          .where("user_id", "==", user_id)
          .order_by("finalizado_em", direction=firestore.Query.DESCENDING)
          .limit(limite)
    )

    docs = query.stream()

    historico = []
    for doc in docs:
        data = doc.to_dict()
        historico.append({
            "resultado_id":   data.get("resultado_id"),
            "simulado_id":    data.get("simulado_id"),
            "acertos":        data.get("acertos", 0),
            "erros":          data.get("erros", 0),
            "total":          data.get("total", 0),
            "aproveitamento": data.get("aproveitamento", 0),
            "finalizado_em":  data.get("finalizado_em"),
        })

    return {
        "user_id":   user_id,
        "total":     len(historico),
        "historico": historico,
    }


@app.get("/historico/estatisticas", tags=["Sessões e resultados"], summary="Estatísticas de desempenho")
def estatisticas_usuario(
    usuario: dict = Depends(obter_usuario_atual),
):
    """Retorna estatísticas agregadas do usuário autenticado."""
    user_id = usuario["uid"]

    docs = db.collection("resultados").where("user_id", "==", user_id).stream()
    resultados = [d.to_dict() for d in docs]

    if not resultados:
        return {
            "user_id":              user_id,
            "total_simulados":      0,
            "total_questoes":       0,
            "total_acertos":        0,
            "taxa_acerto_media":    0,
            "mensagem":             "Faça seu primeiro simulado!",
        }

    total_simulados = len(resultados)
    total_questoes  = sum(r.get("total", 0)    for r in resultados)
    total_acertos   = sum(r.get("acertos", 0)  for r in resultados)
    total_erros     = sum(r.get("erros", 0)    for r in resultados)

    taxa_media = round((total_acertos / total_questoes) * 100, 1) if total_questoes else 0

    aproveitamentos = [r.get("aproveitamento", 0) for r in resultados]
    melhor = max(aproveitamentos) if aproveitamentos else 0
    pior   = min(aproveitamentos) if aproveitamentos else 0

    return {
        "user_id":            user_id,
        "total_simulados":    total_simulados,
        "total_questoes":     total_questoes,
        "total_acertos":      total_acertos,
        "total_erros":        total_erros,
        "taxa_acerto_media":  taxa_media,
        "melhor_desempenho":  melhor,
        "pior_desempenho":    pior,
    }


@app.get("/resultado/{resultado_id}", tags=["Sessões e resultados"], summary="Consulta um resultado")
def detalhar_resultado(
    resultado_id: str,
    usuario:      dict = Depends(obter_usuario_atual),
):
    """Retorna detalhes completos de um resultado específico."""
    user_id = usuario["uid"]

    doc = db.collection("resultados").document(resultado_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Resultado não encontrado.")

    data = doc.to_dict()

    if data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Esse resultado não pertence a você.")

    return data


@app.get("/tokens", tags=["Administração"], summary="Consumo de tokens")
def monitorar_tokens(simulado_id: Optional[str] = None,
                     _adm: bool = Depends(exigir_admin)):
    """Mostra o consumo total de tokens e custo estimado."""
    query = db.collection("uso_tokens")
    if simulado_id:
        query = query.where("simulado_id", "==", simulado_id)

    docs = list(query.stream())

    total_input  = sum(d.to_dict().get("input_tokens", 0)  for d in docs)
    total_output = sum(d.to_dict().get("output_tokens", 0) for d in docs)
    total_custo  = sum(d.to_dict().get("custo_estimado_usd", 0) for d in docs)

    return {
        "total_chamadas":    len(docs),
        "total_input_tokens":  total_input,
        "total_output_tokens": total_output,
        "total_tokens":        total_input + total_output,
        "custo_estimado_usd":  round(total_custo, 4),
        "filtro_simulado_id":  simulado_id or "todos"
    }


@app.get("/limite-diario", tags=["Administração"], summary="Cota diária restante")
def consultar_limite_diario(_adm: bool = Depends(exigir_admin)):
    """Mostra quantos tokens já foram gastos HOJE e quantos restam."""
    hoje      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc       = db.collection("limite_diario").document(hoje).get()

    if not doc.exists:
        return {
            "data":            hoje,
            "tokens_usados":   0,
            "tokens_restantes": LIMITE_TOKENS_DIA,
            "limite_diario":   LIMITE_TOKENS_DIA,
            "custo_total_usd": 0,
            "chamadas":        0,
            "percentual":      "0%",
            "status":          "✅ Disponível",
            "bloqueado":       False
        }

    dados     = doc.to_dict()
    usados    = dados.get("total_tokens", 0)
    restantes = max(0, LIMITE_TOKENS_DIA - usados)
    pct       = (usados / LIMITE_TOKENS_DIA) * 100
    bloqueado = usados >= LIMITE_TOKENS_DIA

    if bloqueado:
        status = "🚫 Bloqueado — limite atingido"
    elif pct >= 90:
        status = "⚠️ Atenção — próximo do limite"
    elif pct >= 50:
        status = "🟡 Em uso moderado"
    else:
        status = "✅ Disponível"

    return {
        "data":            hoje,
        "tokens_usados":   usados,
        "tokens_restantes": restantes,
        "limite_diario":   LIMITE_TOKENS_DIA,
        "custo_total_usd": dados.get("custo_total_usd", 0),
        "chamadas":        dados.get("chamadas", 0),
        "percentual":      f"{pct:.1f}%",
        "status":          status,
        "bloqueado":       bloqueado,
        "mensagem":        "Resetará automaticamente à meia-noite UTC." if bloqueado else None
    }


@app.delete("/simulado/{simulado_id}", tags=["Sessões e resultados"], summary="Remove um simulado")
def deletar_simulado(simulado_id: str,
                     _adm: bool = Depends(exigir_admin)):
    """
    Remove simulado e gabarito do Firebase.

    Exige segredo de ADMIN, não apenas login. Simulado é conteúdo
    compartilhado: deixar qualquer usuário autenticado apagar o de qualquer
    outro seria quase tão aberto quanto deixar sem trava nenhuma. O app não
    chama esta rota — verificado: não há um único DELETE no cliente.
    """
    db.collection("simulados").document(simulado_id).delete()
    db.collection("gabaritos").document(simulado_id).delete()
    print(f"[ADMIN] simulado {simulado_id} e gabarito removidos")
    return {"status": "ok", "mensagem": f"Simulado {simulado_id} removido."}


# ──────────────────────────────────────────────
#  ADMIN — Limpeza e métricas
# ──────────────────────────────────────────────

@app.delete("/admin/cache/{chave_prova}", tags=["Administração"], summary="Limpa uma entrada de cache")
def deletar_cache_prova(chave_prova: str,
                        _adm: bool = Depends(exigir_admin)):
    """Remove o cache de uma prova analisada."""
    doc = db.collection("provas_analisadas").document(chave_prova).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Cache '{chave_prova}' não existe.")

    db.collection("provas_analisadas").document(chave_prova).delete()
    return {
        "status":   "ok",
        "mensagem": f"Cache '{chave_prova}' removido. Próxima chamada vai reanalisar a prova.",
    }


@app.get("/admin/cache", tags=["Administração"], summary="Estado do cache")
def listar_cache_provas(_adm: bool = Depends(exigir_admin)):
    """Lista todas as provas em cache."""
    docs = db.collection("provas_analisadas").stream()
    provas = []

    for doc in docs:
        data = doc.to_dict()
        provas.append({
            "chave":           doc.id,
            "concurso":        data.get("concurso"),
            "ano":             data.get("ano"),
            "area":            data.get("area"),
            "total_topicos":   data.get("total_topicos", 0),
            "total_paginas":   data.get("total_paginas", 0),
            "modo_analise":    data.get("modo_analise"),
            "analisado_em":    data.get("analisado_em"),
        })

    provas.sort(key=lambda x: x.get("analisado_em") or 0, reverse=True)

    return {
        "total":  len(provas),
        "provas": provas,
    }


@app.get("/admin/metricas", tags=["Administração"], summary="Métricas de uso")
def metricas_uso(_adm: bool = Depends(exigir_admin)):
    """Métricas agregadas de uso da API."""
    contagens = {}
    for colecao in ["simulados", "questoes", "resultados", "provas_analisadas", "livros"]:
        try:
            docs = db.collection(colecao).stream()
            contagens[colecao] = sum(1 for _ in docs)
        except Exception:
            contagens[colecao] = "erro"

    concursos_count = {}
    try:
        for doc in db.collection("simulados").stream():
            data = doc.to_dict()
            concurso = data.get("concurso", "desconhecido")
            concursos_count[concurso] = concursos_count.get(concurso, 0) + 1
    except Exception:
        pass

    areas_count = {}
    try:
        for doc in db.collection("provas_analisadas").stream():
            data = doc.to_dict()
            chave = f"{data.get('concurso')}_{data.get('area')}"
            areas_count[chave] = areas_count.get(chave, 0) + 1
    except Exception:
        pass

    tokens_hoje = tokens_usados_hoje()

    return {
        "contagens":        contagens,
        "tokens_hoje":      tokens_hoje,
        "limite_dia":       LIMITE_TOKENS_DIA,
        "tokens_restantes": LIMITE_TOKENS_DIA - tokens_hoje,
        "top_concursos":    dict(sorted(concursos_count.items(), key=lambda x: -x[1])[:10]),
        "top_areas":        dict(sorted(areas_count.items(), key=lambda x: -x[1])[:10]),
    }


# ──────────────────────────────────────────────
#  POOL DE QUESTÕES — removido
#
#  Havia duas rotas aqui, `GET /pool` e `GET /pool/sortear/{pool_id}`.
#  Saíram porque as três coisas abaixo valiam ao mesmo tempo:
#
#   1. Nada as chamava. O aplicativo não cita "/pool" em lugar nenhum.
#   2. Não dava mais para criar pool: `/pool/gerar` saiu junto com as
#      rotas de criação por Gemini, então `pools_questoes` estava
#      congelada no que já existisse.
#   3. As duas eram ABERTAS, sem token. `GET /pool` listava todos os
#      pool_id e `GET /pool/sortear/{id}` devolvia os enunciados — não
#      o gabarito, que mora em coleção separada, mas ainda assim era a
#      única porta da API servindo conteúdo sem autenticação nenhuma.
#
#  Nada de conteúdo se perde: as questões continuam nos documentos de
#  `simulados`, alcançáveis pelas rotas normais. Se sobrou lixo na
#  coleção `pools_questoes`, o limpar_banco.py dá conta.
# ──────────────────────────────────────────────
    return {"total": len(pools), "pools": pools}


# ──────────────────────────────────────────────
#  ROTAS PROCEDURAIS (módulo separado)
#
#  As rotas dos geradores em Python vivem em rotas_procedurais.py.
#  Manter fora deste arquivo evita que uma substituição do
#  simulados_api.py apague o bloco — problema recorrente quando ele
#  era colado aqui dentro.
# ──────────────────────────────────────────────

try:
    from rotas_procedurais import registrar_rotas
    registrar_rotas(app, db, log, salvar_questoes_banco,
                    salvar_simulado_firebase)
except ImportError as _e:
    print(f"[PROCEDURAL] ⚠ rotas_procedurais.py não encontrado: {_e}")


# ──────────────────────────────────────────────
#  PYDANTIC MODELS — Documentação do /docs
# ──────────────────────────────────────────────


class AlternativasModel(BaseModel):
    A: str
    B: str
    C: str
    D: str
    E: str


class QuestaoModel(BaseModel):
    numero:            int
    enunciado:         str
    alternativas:      Dict[str, str]
    contexto:          Optional[str] = None
    topico_inspiracao: Optional[str] = None
    materia:           Optional[str] = None


class GabaritoItemModel(BaseModel):
    numero:           int
    resposta_correta: str
    resposta_usuario: Optional[str] = None
    acertou:          Optional[bool] = None
    explicacao:       str


class RespostaSimuladoModel(BaseModel):
    """Body para POST /simulado/{id}/resultado"""
    respostas: Dict[str, str] = Field(
        ...,
        description="Dicionário {numero_questao: letra_marcada}",
        examples=[{"1": "B", "2": "C", "3": "A"}],
    )


class ResultadoCorrecaoModel(BaseModel):
    resultado_id:    str
    simulado_id:     str
    user_id:         str
    acertos:         int
    erros:           int
    total:           int
    aproveitamento:  str
    gabarito:        List[GabaritoItemModel]


# ──────────────────────────────────────────────
#  EXCEPTION HANDLERS — Erros padronizados
# ──────────────────────────────────────────────

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import os as _os
PRODUCAO = _os.getenv("DESABILITAR_DETALHES_ERRO", "false").lower() in ("true", "1", "yes")


@app.exception_handler(RequestValidationError)
async def handler_validacao(request: Request, exc: RequestValidationError):
    """Captura erros de validação (parâmetros inválidos, tipos errados, etc)."""
    erros_amigaveis = []
    for err in exc.errors():
        campo = " → ".join(str(x) for x in err.get("loc", []) if x != "query")
        msg   = err.get("msg", "Valor inválido")
        erros_amigaveis.append({"campo": campo, "erro": msg})

    log.warning(f"Validação falhou em {request.url.path}: {erros_amigaveis}")

    return JSONResponse(
        status_code=422,
        content={
            "erro":      "Parâmetros inválidos",
            "detalhes":  erros_amigaveis,
            "endpoint":  str(request.url.path),
        }
    )


@app.exception_handler(Exception)
async def handler_geral(request: Request, exc: Exception):
    """Captura qualquer exceção não tratada e retorna JSON padronizado."""
    log.exception(f"Erro não tratado em {request.url.path}: {exc}")

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
                "erro":      "Erro interno do servidor",
                "detalhe":   str(exc)[:200],
                "endpoint":  str(request.url.path),
                "metodo":    request.method,
            }
        )
