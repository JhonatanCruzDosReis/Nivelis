"""
=============================================================
  NIVELIS — API de Notícias com Cache no Firebase
  Concursos suportados: ENEM, ENADE, Militar
=============================================================

  DEPENDÊNCIAS:
    pip install fastapi uvicorn requests firebase-admin
    npm install react-native-dotenv
    python -m pip install python-dotenv

# Crie o ambiente virtual
python -m venv venv

# Ativa o ambiente
venv\Scripts\activate (comando funcional no windows)

 VARIÁVEIS DE AMBIENTE ( arquivo .env):
    GNEWS_API_KEY=sua_chave_aqui (OBS:primeiro crie uma conta no gnews e depois pegue e coloque o código do Gnews no aquivo. env)


COMO RODAR LOCALMENTE:
python -m uvicorn noticias_api:app --host 0.0.0.0 --port 8000 --reload

ou

uvicorn noticias_api:app --reload --host 0.0.0.0

Não importa mais de qual pasta você chama: a credencial do Firebase e o
.env são procurados na PASTA DESTE ARQUIVO. Antes eram caminhos relativos
ao diretório de trabalho, e chamar de outro lugar derrubava a API no
import, antes de qualquer rota existir.

Faltando a credencial, a API SOBE ASSIM MESMO e usa cache em memória.
Para saber o que está configurado:  GET /saude

ROTAS:
  GET    /noticias/{concurso}   enem | enade | militar | geral
  GET    /noticias              todas de uma vez, sem repetir entre elas
  GET    /saude                 o que está configurado e o que falta
  DELETE /cache/{concurso}      força nova busca

 para se concetar ao celular (estou usadno a versão 54.0.7 co celular, no computador 54.0.24): 
 npx expo start (use npx expo start -c caso tenha problemas com as informações antigas) 

  
=============================================================
"""
import hashlib
import os
import re
import unicodedata
from pathlib import Path

import requests
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# ──────────────────────────────────────────
#  CAMINHOS
# ──────────────────────────────────────────
#
# Tudo é resolvido a partir da PASTA DESTE ARQUIVO, não da pasta de onde o
# uvicorn foi chamado.
#
# Antes era `credentials.Certificate("chave-firebase.json")`, caminho
# relativo ao diretório de trabalho. Rodando de qualquer outro lugar — outra
# pasta, ou uma IDE que usa working dir próprio — dava FileNotFoundError.
# E como isso acontecia no import, o processo morria antes do FastAPI
# existir: nenhuma rota subia, e a API simplesmente "não rodava".
AQUI = Path(__file__).resolve().parent

load_dotenv(AQUI / ".env")

# ──────────────────────────────────────────
#  FIREBASE — opcional
# ──────────────────────────────────────────
#
# O Firebase aqui é só cache. Sem ele a API continua servindo notícia, com
# cache em memória. Antes, chave ausente derrubava o processo inteiro.
CAMINHO_CRED = Path(os.getenv("FIREBASE_CRED") or (AQUI / "chave-firebase.json"))

db = None
FIREBASE_ERRO = None

try:
    # Firebase JÁ INICIALIZADO vem primeiro. Em produção este módulo é
    # montado dentro do nivelis_api.py, onde a API principal já subiu o
    # firebase_admin — muitas vezes por variável de ambiente, sem arquivo
    # de credencial no disco. Checando o arquivo antes, ele dispensava um
    # Firebase que estava funcionando e caía para cache em memória, que no
    # Render se perde a cada vez que o serviço dorme.
    if firebase_admin._apps:
        db = firestore.client()
        print("[NOTICIAS] Firebase já inicializado pela API principal — "
              "cache persistente.")
    else:
        if not CAMINHO_CRED.exists():
            raise FileNotFoundError(
                f"credencial do Firebase não encontrada em {CAMINHO_CRED}. "
                f"Coloque o arquivo nessa pasta, aponte a variável "
                f"FIREBASE_CRED para ele, ou monte este módulo dentro de "
                f"uma API que já inicialize o Firebase."
            )
        firebase_admin.initialize_app(credentials.Certificate(str(CAMINHO_CRED)))
        db = firestore.client()
        print(f"[NOTICIAS] Firebase conectado ({CAMINHO_CRED.name}) — "
              f"cache persistente.")
except Exception as e:
    FIREBASE_ERRO = str(e)
    print(f"[NOTICIAS] Sem Firebase: {e}")
    print( "[NOTICIAS] A API sobe assim mesmo; o cache fica só em memória.")

# Cache em memória — usado quando não há Firebase, e como primeira parada
# quando há. {concurso: (salvo_em, [noticias])}
_CACHE_MEMORIA: dict = {}

# ──────────────────────────────────────────
#  CONFIGURAÇÃO DA API
# ──────────────────────────────────────────
app = FastAPI(
    title="Nivelis — API de Notícias",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "DELETE"],
    allow_headers=["*"],
)

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
GNEWS_BASE_URL = "https://gnews.io/api/v4/search"
CACHE_HORAS = 8
# Busca que voltou vazia também é guardada, por pouco tempo. Sem isso, uma
# categoria seca (o ENADE, tipicamente) refazia a chamada ao GNews a CADA
# abertura da tela — foi assim que a cota de 100/dia estourou.
CACHE_VAZIO_MINUTOS = 30

CONCURSOS = {
    "enem": {
        "query": 'ENEM OR SISU OR ProUni OR Inep OR '
                 '"exame nacional do ensino médio"',
        "palavras": ["enem", "sisu", "prouni", "fies", "inep", "vestibular",
                     "exame nacional do ensino medio", "ensino medio",
                     "nota de corte", "redacao do enem"],
        "tag": "ACADÊMICO",
        "descricao": "ENEM e SISU"
    },
    # A consulta do ENADE era 'ENADE 2025 OR ENADE 2026 OR "MEC avaliação
    # cursos"' — presa a dois anos e casando só no título. Notícia de ENADE
    # já é escassa; com esse recorte a categoria voltava vazia, e era por
    # isso que só o ENEM aparecia na tela.
    "enade": {
        "query": 'ENADE OR "Exame Nacional de Desempenho dos Estudantes"',
        "palavras": ["enade", "exame nacional de desempenho", "sinaes",
                     "avaliacao de cursos", "conceito preliminar de curso",
                     "cpc do curso", "igc", "prova do enade"],
        "tag": "ENADE",
        "dias": 730,   # dois anos: matéria de ENADE é rara e não estraga
        "descricao": "Exame de Desempenho e MEC"
    },
    "militar": {
        "query": '"concurso militar" OR EsPCEx OR EEAR OR "Escola Naval" OR '
                 '"Academia Militar"',
        "palavras": ["concurso militar", "espcex", "eear", "escola naval",
                     "academia militar", "forcas armadas", "exercito",
                     "aeronautica", "marinha", "esa", "afa", "ime", "ita"],
        "tag": "MILITAR",
        "descricao": "Escolas Militares"
    },
    "geral": {
        "query": '"concurso público" OR "edital de concurso" OR '
                 '"concurso Banco do Brasil" OR "concurso Petrobras" OR '
                 '"concurso Correios"',
        "palavras": ["concurso publico", "concursos publicos", "edital",
                     "banco do brasil", "petrobras", "correios", "caixa",
                     "inscricoes abertas", "vagas efetivas"],
        "tag": "CONCURSOS",
        "descricao": "Grandes Órgãos Federais"
    }
}

# ──────────────────────────────────────────
#  GNEWS — BUSCA COM FILTRO DE TÍTULO ÚNICO
# ──────────────────────────────────────────

# ──────────────────────────────────────────
#  CONTEÚDO FIXO — o que o jornal não dá
# ──────────────────────────────────────────
#
# O ENADE não produz manchete toda semana como o ENEM. Insistir só em
# notícia deixava a aba vazia, ou enchia de fusão de universidade e
# política — nada que ajude quem vai fazer a prova.
#
# Estes cartões entram SEMPRE, depois do que vier de notícia. São fatos
# estáveis sobre a prova, não jornalismo, então não envelhecem em uma
# semana.
#
# ⚠️ CONFIRA NO INEP antes de confiar em número e data: a estrutura do
# ENADE mudou nos últimos anos e a lista abaixo é ponto de partida, não
# verdade eterna. Editar aqui é o jeito de manter a aba viva — acrescente,
# corte, reescreva.
LINK_INEP = ("https://www.gov.br/inep/pt-br/areas-de-atuacao/"
             "avaliacao-e-exames-educacionais/enade")

FIXAS = {
    "enade": [
        {
            "titulo": "Como a prova é dividida",
            "descricao": "São 40 questões: 10 de formação geral e 30 do "
                         "componente específico do seu curso. A formação "
                         "geral pesa 25% da nota e o específico, 75% — "
                         "errar a conta de peso é o deslize mais comum de "
                         "quem estuda por conta.",
            "fonte": "INEP",
        },
        {
            "titulo": "As discursivas valem mais do que parecem",
            "descricao": "Há questões discursivas nas duas partes, e elas "
                         "costumam ser onde a nota se decide, porque muita "
                         "gente deixa em branco. Responder algo coerente, "
                         "mesmo sem certeza, rende mais do que pular.",
            "fonte": "INEP",
        },
        {
            "titulo": "O ENADE é requisito para se formar",
            "descricao": "Quem é convocado e não comparece fica em situação "
                         "irregular, e isso trava a colação de grau e a "
                         "emissão do diploma. Regularizar depois dá muito "
                         "mais trabalho do que fazer a prova.",
            "fonte": "INEP",
        },
        {
            "titulo": "Formação geral não é matéria do seu curso",
            "descricao": "Essa parte cobra leitura de texto, gráfico e "
                         "tabela sobre temas atuais — meio ambiente, "
                         "tecnologia, cidadania, diversidade. É a que dá "
                         "para treinar independentemente da graduação, e é "
                         "onde o simulado do app ajuda mais.",
            "fonte": "INEP",
        },
        {
            "titulo": "A nota do curso, não a sua",
            "descricao": "O Conceito Enade vai de 1 a 5 e avalia o CURSO, "
                         "não o aluno individualmente. Ele alimenta o CPC e "
                         "o IGC da instituição — por isso a faculdade "
                         "insiste tanto para você ir bem.",
            "fonte": "INEP",
        },
        {
            "titulo": "Confira o edital do seu ano",
            "descricao": "Quais cursos são avaliados muda de ano para ano, "
                         "e a estrutura da prova já foi alterada mais de "
                         "uma vez. Antes de montar seu cronograma, abra o "
                         "edital vigente no site do INEP.",
            "fonte": "INEP",
        },
    ],
}


def _cartoes_fixos(concurso: str) -> list:
    return [{
        "titulo":       f["titulo"],
        "descricao":    f["descricao"],
        "imagem":       "",
        "link":         LINK_INEP,
        "fonte":        f.get("fonte", "INEP"),
        "publicado_em": "",
        "fixa":         True,
    } for f in FIXAS.get(concurso, [])]


def _sem_acento(txt: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(txt or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _relevante(artigo: dict, palavras: list) -> bool:
    """
    A matéria fala mesmo do assunto da categoria?

    A consulta precisa ser AMPLA para o GNews devolver volume — com o
    recorte estreito a categoria vinha vazia. Mas amplo demais traz
    qualquer coisa: apareceu "Renan Santos defende reforma da Previdência"
    marcada como ENADE. Então a consulta abre e o filtro fecha.

    Casa por PALAVRA INTEIRA: "mec" não pode casar dentro de "mecânica",
    nem "esa" dentro de "pesagem".
    """
    texto = _sem_acento(f"{artigo.get('title', '')} {artigo.get('description', '')}")
    for p in palavras:
        alvo = _sem_acento(p)
        if " " in alvo:
            if alvo in texto:
                return True
        elif re.search(rf"\b{re.escape(alvo)}\b", texto):
            return True
    return False


def _parametros(query: str, dias: int = 60) -> dict:
    """
    Parâmetros da chamada ao GNews.

    TRÊS RESTRIÇÕES SE MULTIPLICAVAM AQUI, e juntas explicam por que uma
    busca por "ENEM" no Google acha dezenas e o app trazia uma:

      • in="title" — o termo tinha que estar no TÍTULO. Manchete que só
        cita o ENEM no corpo ficava de fora. Agora vale o resumo também.

      • o ANO dentro da consulta — no GNews o espaço significa E, não OU.
        "ENEM 2026" exigia as duas palavras no mesmo título, e manchete
        como "Enem: inscrições terminam sexta" não casava. Os anos saíram
        de todas as consultas.

      • max=15 — o plano gratuito devolve no máximo 10. Pedir mais não
        traz mais, e conforme o plano a chamada é recusada inteira.
    """
    agora = datetime.now(timezone.utc)
    data_inicio = (agora - timedelta(days=dias)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return {
        "q":        query,
        "lang":     "pt",
        "country":  "br",
        "max":      10,
        "in":       "title,description",
        "from":     data_inicio,
        "sortby":   "publishedAt",
        "apikey":   GNEWS_API_KEY,
    }


def _consultar_gnews(query: str, dias: int = 60):
    """Devolve (artigos, diagnostico). Nunca levanta."""
    diag = {"query": query, "status": None, "total_informado": None,
            "artigos_recebidos": 0, "erro": None}
    try:
        resposta = requests.get(GNEWS_BASE_URL, params=_parametros(query, dias), timeout=10)
        diag["status"] = resposta.status_code
        if resposta.status_code != 200:
            diag["erro"] = resposta.text[:300]
            print(f"[GNEWS] {resposta.status_code}: {resposta.text[:200]}")
            return [], diag
        dados = resposta.json()
    except Exception as e:
        diag["erro"] = f"{type(e).__name__}: {e}"
        print(f"Erro na chamada: {e}")
        return [], diag

    artigos = dados.get("articles", []) or []
    diag["total_informado"] = dados.get("totalArticles")
    diag["artigos_recebidos"] = len(artigos)
    return artigos, diag


def buscar_noticias_gnews(query: str, quantidade: int = 5,
                          palavras: list = None, dias: int = 60) -> list:
    print(f"[GNEWS] Buscando notícias únicas para: '{query}'...")
    artigos, _ = _consultar_gnews(query, dias)
    if palavras:
        antes = len(artigos)
        artigos = [a for a in artigos if _relevante(a, palavras)]
        if antes != len(artigos):
            print(f"[GNEWS] {antes - len(artigos)} fora do assunto, descartadas")
    noticias_formatadas = []
    titulos_vistos = set()

    for artigo in artigos:
        # Notícia SEM FOTO continua entrando. Descartar por isso deixava a
        # categoria vazia quando a busca trazia poucos resultados — era o
        # caso do ENADE, que tem muito menos matéria que o ENEM. O app já
        # escolhe uma imagem de reserva quando o campo vem vazio.
        imagem = artigo.get("image") or ""

        # Limpeza do título: remove o nome da fonte (Ex: "- G1") e espaços extras
        titulo_raw = artigo.get("title", "Sem título")
        titulo_limpo = titulo_raw.split(" - ")[0].split(" | ")[0]
        titulo_comparacao = " ".join(titulo_limpo.lower().split())

        # Verifica se o título já foi adicionado
        if titulo_comparacao not in titulos_vistos:
            titulos_vistos.add(titulo_comparacao)
            noticias_formatadas.append({
                "titulo":       titulo_limpo,
                "descricao":    artigo.get("description", ""),
                "imagem":       imagem,
                "link":         artigo.get("url", ""),
                "fonte":        artigo.get("source", {}).get("name", "Desconhecida"),
                "publicado_em": artigo.get("publishedAt", "")
            })

        if len(noticias_formatadas) >= quantidade:
            break

    return noticias_formatadas

# ──────────────────────────────────────────
#  FUNÇÕES DE CACHE E ROTAS
# ──────────────────────────────────────────

def _chave_titulo(titulo: str) -> str:
    """Título comparável: sem o veículo no fim, sem acento, sem espaço duplo."""
    limpo = str(titulo).split(" - ")[0].split(" | ")[0]
    nfkd = unicodedata.normalize("NFKD", limpo)
    sem = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem.lower().split())


def _assinatura(concurso: str) -> str:
    """
    Impressão digital da configuração da categoria.

    Sem isto, mexer na consulta ou nas palavras do filtro não mudava nada
    por 8 horas: o cache continuava servindo o resultado velho, inclusive
    do Firestore, que sobrevive ao restart do uvicorn. Guardar a
    assinatura junto faz o cache se invalidar sozinho quando a regra muda.
    """
    cfg = CONCURSOS.get(concurso, {})
    bruto = repr((cfg.get("query"), cfg.get("palavras"), cfg.get("dias")))
    return hashlib.md5(bruto.encode("utf-8")).hexdigest()[:10]


def _do_cache(concurso: str):
    """Notícias em cache ainda dentro da validade, ou None."""
    agora = datetime.now(timezone.utc)

    def _validade(noticias):
        return (timedelta(hours=CACHE_HORAS) if noticias
                else timedelta(minutes=CACHE_VAZIO_MINUTOS))

    assinatura = _assinatura(concurso)

    em_memoria = _CACHE_MEMORIA.get(concurso)
    if (em_memoria and em_memoria[2] == assinatura
            and (agora - em_memoria[0]) < _validade(em_memoria[1])):
        return em_memoria[1]

    if db is None:
        return None

    try:
        doc = db.collection("cache_noticias").document(concurso).get()
        if doc.exists:
            dados = doc.to_dict()
            salvo_em = dados.get("salvo_em")
            noticias = dados.get("noticias", [])
            if dados.get("assinatura") != assinatura:
                print(f"[CACHE] {concurso}: configuração mudou, descartando")
            elif salvo_em and (agora - salvo_em) < _validade(noticias):
                _CACHE_MEMORIA[concurso] = (salvo_em, noticias, assinatura)
                print(f"[CACHE] Firebase: {concurso}")
                return noticias
    except Exception as e:
        # Firebase fora do ar não pode impedir a busca — segue para o GNews.
        print(f"[CACHE] falha ao ler {concurso}: {e}")
    return None


def _gravar_cache(concurso: str, noticias: list) -> None:
    agora = datetime.now(timezone.utc)
    _CACHE_MEMORIA[concurso] = (agora, noticias, _assinatura(concurso))
    # Vazio fica só na memória: não vale poluir o Firestore com lista vazia,
    # e a trava de 30 min já impede a repetição de chamadas.
    if db is None or not noticias:
        return
    try:
        db.collection("cache_noticias").document(concurso).set({
            "noticias":   noticias,
            "salvo_em":   agora,
            "concurso":   concurso,
            "assinatura": _assinatura(concurso),
        })
    except Exception as e:
        print(f"[CACHE] falha ao gravar {concurso}: {e}")


def obter_noticias(concurso: str, quantidade: int = 5,
                   forcar: bool = False) -> list:
    # O cache guarda o LOTE INTEIRO e o corte por quantidade acontece na
    # saída. Antes o corte era só na busca, então quem pedisse 10 depois de
    # um pedido de 5 continuava recebendo 5 até o cache vencer.
    cacheadas = None if forcar else _do_cache(concurso)
    if cacheadas is not None:
        return (cacheadas + _cartoes_fixos(concurso))[:quantidade]

    config = CONCURSOS[concurso]
    # Busca com folga: a deduplicação entre categorias corta parte.
    noticias = buscar_noticias_gnews(config["query"], max(quantidade, 10),
                                     config.get("palavras"),
                                     config.get("dias", 60))

    _gravar_cache(concurso, noticias)

    # Os cartões fixos entram DEPOIS da notícia: quando há matéria nova ela
    # aparece primeiro, e quando não há a aba continua com conteúdo útil em
    # vez de "nenhuma notícia".
    return (noticias + _cartoes_fixos(concurso))[:quantidade]


@app.get("/noticias/{concurso}")
def listar_noticias(concurso: str, quantidade: int = 5, forcar: bool = False):
    concurso = concurso.lower().strip()
    if concurso not in CONCURSOS:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    if not GNEWS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GNEWS_API_KEY não configurada. Crie o arquivo .env nesta "
                   "pasta com GNEWS_API_KEY=sua_chave.",
        )

    noticias = obter_noticias(concurso, min(quantidade, 10), forcar)
    return {"noticias": noticias, "concurso": concurso, "total": len(noticias)}


@app.get("/noticias")
def listar_todas(quantidade_por_concurso: int = 3):
    """
    Todas as categorias de uma vez, SEM repetir matéria entre elas.

    As consultas se sobrepõem — uma notícia sobre o MEC cai tanto em
    'enade' quanto em 'geral'. Pedindo categoria por categoria, o app
    mostrava a mesma matéria em abas diferentes. Aqui a primeira categoria
    que trouxer a matéria fica com ela.
    """
    vistos: set = set()
    saida: dict = {}

    for chave in CONCURSOS:
        unicas = []
        for n in obter_noticias(chave, 10):
            k = _chave_titulo(n.get("titulo", ""))
            if not k or k in vistos:
                continue
            vistos.add(k)
            unicas.append(n)
            if len(unicas) >= quantidade_por_concurso:
                break
        saida[chave] = unicas

    return {"noticias": saida, "total": sum(len(v) for v in saida.values())}


@app.get("/diagnostico/{concurso}")
def diagnosticar(concurso: str, query: str = None):
    """
    Mostra ONDE a busca perde notícia, em vez de só devolver lista curta.

    Passando ?query=... testa uma consulta sua sem mexer no código — é o
    jeito rápido de descobrir qual recorte funciona:

        /diagnostico/enem?query=ENEM
        /diagnostico/enem?query=ENEM OR SISU
        /diagnostico/enade?query=ENADE OR "ensino superior"
    """
    concurso = concurso.lower().strip()
    if concurso not in CONCURSOS and not query:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    if not GNEWS_API_KEY:
        raise HTTPException(status_code=503, detail="GNEWS_API_KEY não configurada.")

    consulta = query or CONCURSOS[concurso]["query"]
    artigos, diag = _consultar_gnews(consulta)

    palavras = CONCURSOS.get(concurso, {}).get("palavras")
    sem_foto = sum(1 for a in artigos if not a.get("image"))
    relevantes = [a for a in artigos if not palavras or _relevante(a, palavras)]
    formatadas = buscar_noticias_gnews(consulta, 50, palavras)

    return {
        **diag,
        "parametros":        {k: v for k, v in _parametros(consulta).items()
                              if k != "apikey"},
        "artigos_sem_foto":  sem_foto,
        "no_assunto":        len(relevantes),
        "fora_do_assunto":   [a.get("title") for a in artigos
                              if a not in relevantes],
        "apos_deduplicacao": len(formatadas),
        "titulos":           [n["titulo"] for n in formatadas],
        "palavras_do_filtro": palavras,
        "leitura": (
            "recebidos 0 → consulta restritiva demais, ou o GNews recusou "
            "(veja status/erro). recebidos alto e no_assunto baixo → a "
            "consulta está trazendo coisa de fora; olhe fora_do_assunto e "
            "acrescente a palavra que falta. no_assunto alto e "
            "apos_deduplicacao baixo → matéria repetida entre veículos."
        ),
    }


@app.get("/saude")
def saude():
    """Diz o que está faltando, em vez de falhar calado."""
    return {
        "ok":            bool(GNEWS_API_KEY),
        "firebase":      "conectado" if db is not None else "indisponível",
        "firebase_erro": FIREBASE_ERRO,
        "gnews_key":     "configurada" if GNEWS_API_KEY else "AUSENTE",
        "cache_horas":   CACHE_HORAS,
        "pasta":         str(AQUI),
        "concursos":     list(CONCURSOS),
    }


@app.delete("/cache/{concurso}")
def limpar_cache(concurso: str):
    chave = concurso.lower().strip()
    _CACHE_MEMORIA.pop(chave, None)
    if db is not None:
        try:
            db.collection("cache_noticias").document(chave).delete()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Firebase: {e}")
    return {"status": "ok", "concurso": chave}

# ──────────────────────────────────────────
#  ROTAS CURTAS — para quando este módulo é MONTADO
# ──────────────────────────────────────────
#
# Em produção o nivelis_api.py monta este app:
#
#     from noticias_api import app as noticias_app
#     app.mount("/v1/noticias", noticias_app)
#
# Com o prefixo do mount, "/noticias/{concurso}" viraria
# "/v1/noticias/noticias/enade". As rotas abaixo dão a forma curta —
# "/v1/noticias/enade" — sem tirar as antigas, que continuam valendo
# para quem roda este arquivo sozinho durante o desenvolvimento.
#
# ORDEM IMPORTA: "/{concurso}" é curinga e engoliria "/saude" e
# "/diagnostico/...". Por isso ficam aqui no FIM do arquivo, depois de
# todas as rotas específicas já terem sido declaradas.

@app.get("/{concurso}", tags=["Atalhos"])
def listar_noticias_curto(concurso: str, quantidade: int = 5,
                          forcar: bool = False):
    return listar_noticias(concurso, quantidade, forcar)
