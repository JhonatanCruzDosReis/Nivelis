"""
=============================================================
  NIVELIS — Indexador de Livros
=============================================================

  Lê um livro em PDF, identifica os capítulos via Gemini,
  e salva tudo no Firebase para que a API possa gerar
  questões depois SEM precisar reprocessar o livro.

  COMO USAR:
    1. Coloque seu PDF na pasta livros/ deste diretório
    2. Rode: python indexar_livro.py "livros/meu_livro.pdf"
    3. Opcionalmente, dê um título/disciplina:
       python indexar_livro.py "livros/x.pdf" --titulo "Direito Constitucional" --disciplina direito

  O QUE FAZ:
    1. Lê o PDF
    2. Pede pro Gemini identificar capítulos e tópicos
    3. Salva tudo no Firebase (coleção 'livros')
    4. Gera um ID único pro livro

  FUTURO: pode ser chamado também via rota da API.

=============================================================
"""

import os
import sys
import io
import json
import uuid
import argparse
import google.generativeai as genai
import firebase_admin
import pdfplumber
from pathlib            import Path
from dotenv             import load_dotenv
from firebase_admin     import credentials, firestore
from datetime           import datetime, timezone

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY não configurada no .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-2.5-flash-lite")

# ──────────────────────────────────────────
#  EXTRAÇÃO DE TRECHOS PARA INTERPRETAÇÃO
#  O Gemini já lê o PDF inteiro para montar o índice; aproveitamos a
#  MESMA chamada para extrair parágrafos analisados. Isso permite gerar
#  questões de interpretação depois, em Python, sem novas chamadas de IA.
# ──────────────────────────────────────────

# Quantidades calibradas para o JSON caber no limite de tokens de saída.
# Um livro de 200+ páginas com 20 trechos longos estoura o teto e o JSON
# trunca justamente na parte dos trechos (que vêm depois dos capítulos).
MIN_TRECHOS       = 6
MAX_TRECHOS       = 12
MIN_CHARS_TRECHO  = 250

# 1400 em vez de 600: texto acadêmico e de política pública tem parágrafo
# longo por natureza. Com o limite anterior, 9 de 10 trechos de um Caderno
# do Ministério da Saúde eram descartados — e o livro, que é justamente o
# tipo de material que rende boa interpretação, ficava inutilizável.
#
# Um parágrafo de 1400 caracteres ocupa cerca de 20 linhas na tela, que é
# o tamanho de texto-base de uma questão de ENADE.
MAX_CHARS_TRECHO  = 1400

# Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("chave-nivelis.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  FUNÇÕES AUXILIARES (hash + checagem de duplicata)
#  Definidas antes de indexar_livro, que as utiliza.
# ──────────────────────────────────────────

def calcular_hash_pdf(pdf_bytes: bytes) -> str:
    """
    Calcula um hash SHA-256 do conteúdo do PDF.
    Dois PDFs com mesmo conteúdo terão o mesmo hash,
    mesmo se renomeados.
    """
    import hashlib
    return hashlib.sha256(pdf_bytes).hexdigest()


def ja_indexado_por_nome(nome_arquivo: str) -> str:
    """
    Checa se livro com mesmo nome de arquivo já foi indexado.
    RÁPIDO — não precisa ler o PDF.
    """
    try:
        docs = (
            db.collection("livros")
              .where("arquivo_original", "==", nome_arquivo)
              .limit(1)
              .stream()
        )
        for doc in docs:
            return doc.to_dict().get("livro_id")
    except Exception:
        pass
    return None


def ja_indexado_por_hash(hash_pdf: str) -> tuple[str, str]:
    """
    Checa se livro com mesmo CONTEÚDO já foi indexado.
    Mais robusto — pega duplicata mesmo se o arquivo foi renomeado.
    Retorna (livro_id, nome_original) se achar, (None, None) se não.
    """
    try:
        docs = (
            db.collection("livros")
              .where("hash_conteudo", "==", hash_pdf)
              .limit(1)
              .stream()
        )
        for doc in docs:
            data = doc.to_dict()
            return data.get("livro_id"), data.get("arquivo_original")
    except Exception:
        pass
    return None, None


# Mantida por compatibilidade
def ja_indexado(nome_arquivo: str) -> str:
    """Alias para ja_indexado_por_nome (compatibilidade)."""
    return ja_indexado_por_nome(nome_arquivo)


def _decodificar_com_reparo(raw: str):
    """
    Decodifica o JSON da análise, tentando reparos progressivos.

    O Gemini às vezes estoura o limite de saída e trunca a resposta no meio.
    Sem reparo, o livro inteiro se perde DEPOIS de já ter consumido a cota.
    A ordem dos níveis importa: o nível 0 preserva capítulos E trechos; os
    seguintes vão descartando material até conseguir um JSON válido.

    Retorna o dicionário decodificado, ou None se nada funcionar.
    """
    # Tentativa direta
    try:
        return json.loads(raw)
    except json.JSONDecodeError as erro:
        pos_erro = erro.pos
        print(f"   ⚠ JSON com problema, tentando reparar...")

    # Nível 0 — fecha as estruturas abertas no último item íntegro.
    # Preserva as DUAS seções (capítulos e trechos); os demais níveis
    # cortariam tudo a partir do erro, perdendo os trechos.
    reparo = _fechar_estruturas(raw, pos_erro)
    if reparo is not None:
        n_cap = len(reparo.get("capitulos", []))
        n_tre = len(reparo.get("trechos", []))
        print(f"   ✅ Reparo preservou {n_cap} capítulo(s) e {n_tre} trecho(s)")
        return reparo

    # Nível 1 — corta depois do último ] e fecha o objeto se faltar
    candidato = raw
    ultimo_array = candidato.rfind("]")
    if ultimo_array > 0:
        candidato = candidato[:ultimo_array + 1]
        if candidato.count("{") > candidato.count("}"):
            candidato += "}"
        try:
            resultado = json.loads(candidato)
            print("   ✅ Reparo nível 1 funcionou!")
            return resultado
        except json.JSONDecodeError:
            pass

    # Nível 2 — corta no último objeto completo e fecha array + objeto
    ultimo_obj = raw[:pos_erro].rfind("}")
    if ultimo_obj > 0:
        try:
            resultado = json.loads(raw[:ultimo_obj + 1] + "\n  ]\n}")
            print("   ✅ Reparo nível 2 funcionou (cortou itens incompletos)!")
            return resultado
        except json.JSONDecodeError:
            pass

    return None


def _fechar_estruturas(raw: str, pos_erro: int):
    """
    Repara um JSON truncado fechando as estruturas abertas, em vez de
    descartar tudo a partir do ponto de erro.

    Por que isso importa: a resposta da indexação traz "capitulos" e depois
    "trechos". Quando o modelo estoura o limite de saída, o corte cai dentro
    dos trechos — e um reparo que simplesmente trunca no último objeto
    completo devolve os capítulos com "trechos": [] (foi o que acontecia).

    Aqui percorremos o texto até o último item ÍNTEGRO, fechando colchetes e
    chaves pendentes. O que já veio completo é aproveitado nas duas seções.

    Retorna o objeto decodificado, ou None se não for recuperável.
    """
    corte = raw[:pos_erro] if pos_erro and pos_erro < len(raw) else raw

    # Recua até o fim de um item completo (}) que não esteja dentro de string
    dentro_str, escapado, ultimo_fim = False, False, -1
    pilha = []
    for i, ch in enumerate(corte):
        if escapado:
            escapado = False
            continue
        if ch == "\\":
            escapado = True
            continue
        if ch == '"':
            dentro_str = not dentro_str
            continue
        if dentro_str:
            continue
        if ch in "[{":
            pilha.append(ch)
        elif ch in "]}":
            if pilha:
                pilha.pop()
            # fim de um objeto em nível de item de lista
            if ch == "}" and len(pilha) >= 1:
                ultimo_fim = i

    if ultimo_fim < 0:
        return None

    # Recalcula a pilha até o último item íntegro
    trecho = corte[:ultimo_fim + 1]
    dentro_str, escapado = False, False
    pilha = []
    for ch in trecho:
        if escapado:
            escapado = False
            continue
        if ch == "\\":
            escapado = True
            continue
        if ch == '"':
            dentro_str = not dentro_str
            continue
        if dentro_str:
            continue
        if ch in "[{":
            pilha.append(ch)
        elif ch in "]}":
            if pilha:
                pilha.pop()

    fechamento = "".join("]" if c == "[" else "}" for c in reversed(pilha))
    try:
        return json.loads(trecho + fechamento)
    except json.JSONDecodeError:
        return None


def _densidade_notacao(texto: str) -> float:
    """
    Estima o quanto o trecho é notação/diagrama em vez de prosa.

    A extração de PDF achata dois tipos de conteúdo visual:

      1. Fórmulas — "(x + a)²" vira "(x + a)2", "x³ + 3x²a" vira "x3 + 3x2a"
      2. Diagramas — um Venn com rótulos vira linhas soltas:
             B2 B3 B4 B5 B6
             B7
             A 10
             140

    O segundo caso é o mais traiçoeiro: as linhas são curtas e sem símbolo
    de operação, então passam por prosa num detector ingênuo. Aqui são
    reconhecidas pelo padrão — linha curta composta só de rótulos e
    números soltos, sem verbo nem preposição.

    Retorna a fração de linhas que não são prosa.
    """
    import re as _re
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    if not linhas:
        return 1.0

    # Palavras que denunciam prosa de verdade
    PROSA = _re.compile(
        r'\b(?:de|da|do|que|para|com|em|por|uma?|os?|as?|é|são|ser|'
        r'pode|deve|quando|se|não|mais|como|ao|à|nos?|nas?)\b', _re.I)

    suspeitas = 0
    for linha in linhas:
        colagens = len(_re.findall(r'[a-zA-Z]\d|\d[a-zA-Z]', linha))
        simbolos = len(_re.findall(r'[=+×⋅∈∩∪∅≤≥≠∑∏√·Ω∀]', linha))
        letras   = len(_re.findall(r'[a-zA-ZÀ-ÿ]', linha))
        tem_prosa = bool(PROSA.search(linha))

        if colagens >= 3 or simbolos >= 3:
            suspeitas += 1
        elif len(linha) < 40 and (colagens + simbolos) >= 2 and letras < 15:
            suspeitas += 1
        elif _re.fullmatch(r'[\s.·…]+', linha):
            suspeitas += 1
        # ── Linha de DIAGRAMA: curta, sem prosa, só rótulos e números ──
        elif len(linha) < 45 and not tem_prosa:
            # "B2 B3 B4 B5 B6" / "A 10" / "140" / "70 B"
            if _re.fullmatch(r'(?:[A-ZΩ]\d*|\d+|[a-z]\d*)(?:\s+(?:[A-ZΩ]\d*|\d+|[a-z]\d*))*',
                             linha):
                suspeitas += 1
            # Alternativas de exercício: "a) 10/500 = 1/50 d) 280/500 = 14/25"
            elif _re.search(r'^[a-e]\)\s', linha):
                suspeitas += 1

    return suspeitas / len(linhas)


# Acima disso o trecho é fórmula/diagrama, não prosa.
#
# 0.20 é mais rígido que o 0.35 inicial, e o motivo é específico da
# interpretação: quando a informação está na notação matemática, uma
# afirmação fiel ao texto e outra que o extrapola ficam indistinguíveis
# para qualquer verificação automática — só a leitura humana separa.
# Descartar esses trechos é mais seguro que gerar questão ambígua.
MAX_DENSIDADE_NOTACAO = 0.20


def _reduzir_trecho(texto: str, alvo: int) -> str:
    """
    Encurta um trecho longo mantendo unidades completas de sentido.

    Havia um conflito na especificação anterior: o prompt pedia o parágrafo
    INTEIRO (para não cortar o raciocínio no meio) e a validação rejeitava
    o que passasse do limite. Documentos como os Cadernos do Ministério da
    Saúde têm parágrafos de 1500 a 2300 caracteres — e eram descartados em
    bloco, justamente o material que melhor serve à interpretação.

    A solução é cortar em fronteira de FRASE, do fim para o começo, até
    caber. O leitor recebe um texto que começa e termina em ponto final;
    o que se perde é o desdobramento final do parágrafo, não o argumento.

    Retorna None se nem as duas primeiras frases couberem — aí o texto é
    denso demais para servir de base.
    """
    import re as _re
    t = " ".join(str(texto).split())
    if len(t) <= alvo:
        return t

    # Divide preservando o delimitador
    frases = _re.split(r'(?<=[.!?])\s+', t)
    if len(frases) < 2:
        return None

    acumulado = []
    total = 0
    for f in frases:
        if total + len(f) + 1 > alvo:
            break
        acumulado.append(f)
        total += len(f) + 1

    # Precisa sobrar argumento: ao menos duas frases
    if len(acumulado) < 2:
        return None

    return " ".join(acumulado)


def _ancora_automatica(afirmacao: str, texto: str) -> tuple:
    """
    Procura no parágrafo a passagem que melhor sustenta uma afirmação.

    Existe porque o modelo nem sempre fornece o campo "ancoras", e depender
    da cooperação dele deixaria a verificação sem efeito justamente quando
    ela mais importa.

    Divide o parágrafo em frases e mede quanto do vocabulário de conteúdo
    da afirmação aparece em cada uma. Retorna (melhor_frase, cobertura).

    Cobertura alta significa que a afirmação reformula algo presente no
    texto. Cobertura baixa significa que ela introduz conteúdo de fora —
    exatamente o caso de "fortalece o vínculo e a responsabilização" num
    parágrafo que só descreve quem faz a primeira escuta.
    """
    import re as _re
    import unicodedata as _ud

    def _conteudo(t):
        t = _ud.normalize("NFKD", str(t or "").lower())
        t = "".join(ch for ch in t if not _ud.combining(ch))
        palavras = _re.findall(r'[a-z]{4,}', t)
        return {p for p in palavras if p not in VAZIAS}

    alvo = _conteudo(afirmacao)
    if not alvo:
        return "", 0.0

    frases = [f.strip() for f in _re.split(r'(?<=[.;:!?])\s+', str(texto))
              if len(f.split()) >= 4]
    if not frases:
        frases = [str(texto)]

    melhor, melhor_cob = "", 0.0
    for f in frases:
        cob = len(alvo & _conteudo(f)) / len(alvo)
        if cob > melhor_cob:
            melhor, melhor_cob = f, cob

    # Também considera o parágrafo inteiro: uma tese pode sintetizar
    # ideias espalhadas por várias frases sem se concentrar em nenhuma
    cob_total = len(alvo & _conteudo(texto)) / len(alvo)
    if cob_total > melhor_cob:
        melhor, melhor_cob = str(texto)[:120], cob_total

    return melhor, melhor_cob


# Palavras funcionais que não indicam assunto — ignoradas na comparação,
# senão qualquer afirmação teria cobertura alta só por usar português.
VAZIAS = {
    "para", "como", "mais", "menos", "muito", "pouco", "todo", "toda",
    "cada", "esse", "essa", "este", "esta", "aquele", "aquela", "seus",
    "suas", "pelo", "pela", "quando", "onde", "porque", "entre", "sobre",
    "ainda", "apenas", "tambem", "assim", "entao", "sendo", "pode",
    "podem", "deve", "devem", "sera", "serao", "outro", "outra", "qual",
    "quais", "isso", "aquilo", "nesse", "nessa", "neste", "nesta",
}


MIN_COBERTURA_TESE = 0.35
MIN_COBERTURA_ITEM = 0.25


def _ancora_presente(ancora: str, texto: str, tolerancia: float = 0.7) -> bool:
    """
    A âncora citada existe mesmo no parágrafo?

    O modelo tende a "citar" passagens que reconstrói de memória em vez de
    copiar. Comparar palavra a palavra seria rígido demais (ele normaliza
    pontuação e acentos); comparar por sobreposição de vocabulário pega a
    citação inventada sem punir a transcrição imperfeita.

    Retorna False quando menos de `tolerancia` das palavras da âncora
    aparecem no texto — sinal de que a passagem não está lá.
    """
    import re as _re
    import unicodedata as _ud

    def _norm(t):
        t = _ud.normalize("NFKD", str(t or "").lower())
        t = "".join(ch for ch in t if not _ud.combining(ch))
        return set(_re.findall(r'[a-z]{4,}', t))

    pal_ancora = _norm(ancora)
    if not pal_ancora:
        return False
    pal_texto = _norm(texto)
    return len(pal_ancora & pal_texto) / len(pal_ancora) >= tolerancia


def verificar_ancoras(t: dict) -> tuple:
    """
    Confere se a análise está ancorada no parágrafo.

    O prompt exige que o modelo aponte, para cada afirmação, a passagem
    que a sustenta. Aqui essas passagens são conferidas contra o texto —
    sem isso a exigência seria decorativa, já que o modelo poderia citar
    qualquer coisa.

    Retorna (quantas_falharam, lista_de_avisos). Não descarta o trecho:
    uma âncora ausente indica risco, não erro certo, e descartar por isso
    zeraria livros inteiros. A contagem é reportada ao usuário.
    """
    ancoras = t.get("ancoras") or {}
    texto_t = t.get("texto") or ""

    # Sem o campo do modelo, verifica por conta própria: mede quanto de
    # cada afirmação está de fato no parágrafo. É menos preciso que uma
    # citação literal, mas pega o caso que importa — a afirmação que
    # introduz conteúdo ausente do texto.
    if not isinstance(ancoras, dict) or not ancoras:
        falhas, avisos = 0, []
        itens = [("tese", t.get("tese"), MIN_COBERTURA_TESE),
                 ("ideia_secundaria", t.get("ideia_secundaria"), MIN_COBERTURA_ITEM)]
        for p in (t.get("pressupostos") or []):
            itens.append(("pressuposto", p, MIN_COBERTURA_ITEM))

        for rotulo, valor, minimo in itens:
            if not valor:
                continue
            _, cobertura = _ancora_automatica(valor, texto_t)
            if cobertura < minimo:
                falhas += 1
                avisos.append(f"{rotulo}: so {cobertura:.0%} do conteudo aparece "
                              f"no paragrafo (\"{str(valor)[:42]}\")")
        return falhas, avisos

    texto = texto_t
    falhas, avisos = 0, []

    def _checar(rotulo, valor):
        nonlocal falhas
        if not valor:
            return
        itens = valor if isinstance(valor, list) else [valor]
        for i, a in enumerate(itens):
            if a and not _ancora_presente(a, texto):
                falhas += 1
                avisos.append(f"{rotulo}: ancora nao localizada no texto "
                              f"(\"{str(a)[:45]}\")")

    _checar("tese", ancoras.get("tese"))
    _checar("ideia_secundaria", ancoras.get("ideia_secundaria"))
    _checar("pressuposto", ancoras.get("pressupostos"))
    _checar("afirmacao_falsa", ancoras.get("afirmacoes_falsas"))

    return falhas, avisos


def _e_citacao_literal(afirmacao: str, texto: str, limiar: float = 0.85) -> bool:
    """
    A afirmação é um pedaço copiado do parágrafo?

    A análise deve REFORMULAR o que o texto diz, não recortá-lo. Um
    fragmento copiado costuma vir cortado no meio ("...permanecem nas
    áreas.") e não constitui afirmação — não é nem verdadeiro nem falso,
    é um trecho de frase.

    Além disso, uma alternativa que reproduz o texto literalmente permite
    acertar por busca visual, sem interpretar.

    Detecta comparando sequências de 4 palavras: se a maioria delas
    aparece igual no parágrafo, houve cópia.
    """
    import re as _re
    import unicodedata as _ud

    def _norm(t):
        t = _ud.normalize("NFKD", str(t or "").lower())
        t = "".join(ch for ch in t if not _ud.combining(ch))
        return _re.findall(r'[a-z]+', t)

    pal_af = _norm(afirmacao)
    if len(pal_af) < 5:
        return False

    texto_norm = " ".join(_norm(texto))

    # Trigramas em vez de tetragramas: recortes curtos como "Os
    # profissionais da recepção, ao identificarem riscos" têm poucas
    # sequências de 4 palavras, e a pontuação removida na normalização
    # ainda desloca as fronteiras.
    ngramas = [" ".join(pal_af[i:i + 3]) for i in range(len(pal_af) - 2)]
    if not ngramas:
        return False

    copiados = sum(1 for g in ngramas if g in texto_norm)
    return copiados / len(ngramas) >= limiar


def _checar_redacao(texto: str, rotulo: str) -> list:
    """
    Confere a redação de uma afirmação vinda da análise do modelo.

    A análise entra DIRETO nas alternativas das questões, sem passar por
    reescrita. Um pressuposto truncado ou com erro de concordância chega
    ao aluno exatamente como foi gerado — por isso a checagem precisa
    acontecer aqui, na indexação, e não só nos testes do gerador.

    Retorna a lista de problemas encontrados.
    """
    import re as _re
    t = " ".join(str(texto or "").split())
    problemas = []

    if not t:
        return ["vazio"]

    # ── Frase incompleta ──
    if len(t.split()) < 4:
        problemas.append("curta demais para ser alternativa")

    PENDENTES = {
        # verbos de ligação e auxiliares
        "é", "são", "era", "eram", "foi", "seja", "sendo", "tem", "têm",
        "está", "estão", "pode", "podem", "deve", "devem", "há",
        # preposições e contrações
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "por", "para", "com", "sem", "sob", "sobre", "entre", "ao", "à",
        "aos", "às", "pelo", "pela", "pelos", "pelas", "num", "numa",
        # artigos e conectivos
        "que", "e", "ou", "mas", "a", "o", "as", "os", "um", "uma",
        "uns", "umas", "como", "quando", "onde", "se", "nem", "porque",
        # possessivos e demonstrativos
        "seu", "sua", "seus", "suas", "meu", "minha", "nosso", "nossa",
        "este", "esta", "esse", "essa", "aquele", "aquela", "isso",
        "cujo", "cuja", "cujos", "cujas",
        # quantificadores
        "todo", "toda", "todos", "todas", "cada", "qualquer", "algum",
        "alguma", "outro", "outra", "outros", "outras", "muito", "muita",
    }
    # ── Oração sem verbo principal ──
    #
    # "Os profissionais da recepção, ao identificarem riscos" tem sujeito e
    # oração reduzida, mas nenhum predicado — não afirma nada, e como
    # alternativa não pode ser julgada verdadeira nem falsa.
    #
    # Tentei detectar o verbo por terminação, e não funciona: "da", "ao" e
    # "recepção" casam com as mesmas desinências. Sem analisador
    # morfológico, o caminho viável é reconhecer a ESTRUTURA típica do
    # fragmento — oração reduzida ("ao identificar", "sendo", "tendo") sem
    # nenhum verbo de ligação ou modal em seguida.
    # ── Fragmento sem predicado ──
    #
    # Tentei duas abordagens que não funcionam: procurar o verbo por
    # terminação (onde "da", "ao" e "recepção" casam) e manter lista de
    # verbos finitos (onde sempre falta um).
    #
    # O que funciona é olhar o FIM da frase. Uma afirmação termina em
    # complemento; um fragmento termina no meio de um sintagma iniciado
    # por oração reduzida, sem nada depois que a feche.
    #
    #   "A atenção básica, atuando como porta de entrada e articuladora"
    #    → tudo após a vírgula é a reduzida. Nada fecha. Fragmento.
    #
    #   "A atenção básica, atuando como porta de entrada, ordena a rede"
    #    → a reduzida está entre vírgulas e há texto depois. Afirmação.
    # Formas que iniciam oração reduzida:
    #   gerúndio ....... "atuando como porta de entrada"
    #   infinitivo ..... "ao identificarem riscos"
    #   PARTICÍPIO ..... "exemplificada pelo caso de Joana"
    #
    # O particípio faltava, e por isso "A banalização do sofrimento
    # alheio, exemplificada pelo caso de Joana" passava — sintagma nominal
    # com adjunto, sem nada que afirme.
    # Locuções que introduzem oração reduzida. A lista de preposições
    # veio de uma varredura sistemática: eu vinha acrescentando uma por
    # vez conforme apareciam nos lotes ("ao", depois "apesar de"), e a
    # cobertura ficava em 74%. Estas são as formas do português que
    # antecedem infinitivo, gerúndio ou particípio em oração reduzida.
    INTRO_REDUZIDA = (
        r'(?:ao|à|aos|às|de|em|por|para|sem|com|após|antes de|'
        r'apesar de|além de|em vez de|ao invés de|a fim de|'
        r'no intuito de|com o objetivo de|em que pese|'
        r'depois de|até|desde)?'
    )
    m_red = _re.search(
        r',\s*' + INTRO_REDUZIDA + r'\s*'
        r'\w+(?:ando|endo|indo|arem|erem|irem|armos|ermos|irmos|'
        r'ar|er|ir|ad[oa]s?|id[oa]s?)\b',
        t, _re.IGNORECASE)
    if m_red:
        depois = t[m_red.end():]

        # A reduzida pode ser fechada por vírgula OU seguida direto do
        # predicado: "O acesso, fundamentado no princípio de justiça DEVE
        # ORIENTAR a organização" é frase completa sem a segunda vírgula.
        # Exigir a vírgula rejeitava um quinto das frases corretas.
        VERBO_APOS = _re.compile(
            r'\b(?:é|são|era|eram|foi|foram|será|serão|está|estão|'
            r'tem|têm|há|deve|devem|pode|podem|precisa|precisam|'
            r'exige|exigem|requer|requerem|constitui|constituem|'
            r'demanda|demandam|permite|permitem|garante|garantem|'
            r'representa|representam|significa|significam|'
            r'orienta|orientam|envolve|envolvem|depende|dependem|'
            r'implica|implicam|resulta|resultam|contribui|contribuem|'
            r'favorece|favorecem|reduz|reduzem|amplia|ampliam|'
            r'\w{3,}(?:am|em|ou|iu|ram|vam|rá|rão|ria|sse|imos|emos|amos))\b',
            _re.IGNORECASE)

        fechamento = depois.find(",")
        resto = depois[fechamento + 1:].strip() if fechamento >= 0 else ""
        tem_predicado = (len(resto.split()) >= 2) or bool(VERBO_APOS.search(depois))

        if not tem_predicado:
            problemas.append("oração reduzida sem predicado (não é uma afirmação)")

    # ── Adjunto adverbial sem oração principal ──
    #
    # "Para um acolhimento eficaz da demanda espontânea" é adjunto de
    # finalidade: prepara uma afirmação que nunca vem. Como alternativa,
    # não pode ser julgado verdadeiro nem falso.
    #
    # A marca é a frase INTEIRA ser o adjunto: começa com locução
    # prepositiva de finalidade, causa ou condição, e não há vírgula
    # seguida de oração que a complete.
    # As contrações do português (de+as=das, em+os=nos, a+a=à) precisam
    # entrar no padrão: escrever "d[aeo]" deixava passar "diante DAS
    # situações", "com base NOS princípios" e "devido À sobrecarga".
    CONTRAI = r'(?:d[aeo]s?|n[aeo]s?|à|às|ao|aos|em|a)'
    ABRE_ADJUNTO = _re.compile(
        rf'^\s*(?:para|a fim de|'
        rf'com o (?:objetivo|intuito|propósito|fim) de|'
        rf'com vistas? a|em razão {CONTRAI}|por causa {CONTRAI}|'
        rf'devido {CONTRAI}|em virtude {CONTRAI}|graças {CONTRAI}|'
        rf'mediante|apesar {CONTRAI}|no caso {CONTRAI}|'
        rf'diante {CONTRAI}|em face {CONTRAI}|a partir {CONTRAI}|'
        rf'com base {CONTRAI}|de acordo com|conforme|segundo|'
        rf'à luz {CONTRAI}|por meio {CONTRAI}|através {CONTRAI}|'
        rf'ao longo {CONTRAI}|além {CONTRAI}|dentro {CONTRAI})\b',
        _re.IGNORECASE)

    if ABRE_ADJUNTO.match(t):
        # Precisa haver vírgula E conteúdo depois dela para que a oração
        # principal exista: "Para acolher, a unidade precisa de estrutura."
        pos_virgula = t.find(",")
        resto = t[pos_virgula + 1:].strip() if pos_virgula >= 0 else ""
        if len(resto.split()) < 3:
            problemas.append("adjunto adverbial sem oração principal")

    # ── Adjetivo antepositivo pendurado ──
    #
    # Adjetivo no fim NÃO é truncamento por si: "uma definição única" está
    # correta, e barrá-la rejeitava trecho legítimo. O que indica corte é o
    # adjetivo ANTEPOSITIVO — aquele que, na ordem do português, exige
    # substantivo depois: "ou a simples", "de um mero", "o próprio".
    #
    # A marca é o DETERMINANTE antes dele: "a simples" (truncado) contra
    # "definição única" (completa).
    ANTEPOSITIVOS = (r'(?:simples|mero|mera|meros|meras|próprio|própria|'
                     r'mesmo|mesma|certo|certa|tal|tais|determinado|'
                     r'determinada|referido|referida|citado|dito|dita|'
                     r'presente|seguinte|primeiro|primeira|segundo|segunda|'
                     r'novo|nova|grande|maior|menor|único|única)')
    if _re.search(r'\b(?:o|a|os|as|um|uma|uns|umas|do|da|dos|das|no|na|'
                  r'ao|à|de|em|por|com|que)\s+' + ANTEPOSITIVOS + r'\s*$',
                  t.rstrip(".!?"), _re.IGNORECASE):
        problemas.append("adjetivo antepositivo sem substantivo (frase truncada)")

    ultima = t.rstrip(".!?").split()[-1].lower().strip(".,;:") if t.split() else ""
    if ultima in PENDENTES:
        problemas.append(f"termina em '{ultima}' (frase incompleta)")
    elif _re.fullmatch(r'\w+(?:ando|endo|indo)', ultima):
        problemas.append(f"termina em gerúndio '{ultima}'")

    # ── Maiúscula no meio da frase ──
    #
    # "Não É importante investigar" — a negação foi inserida antes de um
    # verbo que abria a frase, e a caixa não foi ajustada. Um verbo ou
    # palavra comum capitalizada longe do início indica emenda malfeita.
    m_caixa = _re.search(r'(?<=[a-zà-ÿ])\s+(É|São|Há|Está|Estão|Tem|Têm|'
                         r'Deve|Devem|Pode|Podem|Exige|Requer|Constitui|'
                         r'Permite|Garante|Envolve|Depende|Precisa)\b', t)
    if m_caixa:
        problemas.append(f"maiúscula indevida em '{m_caixa.group(1)}' "
                         f"(emenda malfeita)")

    # ── Pontuação e espaçamento ──
    if _re.search(r'[.,;:!?]{3,}', t):
        problemas.append("pontuação repetida")
    if _re.search(r'\s[,.;:]', t):
        problemas.append("espaço antes de pontuação")
    if _re.search(r'\(\s*\)|\[\s*\]', t):
        problemas.append("parênteses vazios")

    # ── Parênteses e aspas desbalanceados ──
    if t.count("(") != t.count(")"):
        problemas.append("parênteses desbalanceados")
    if t.count("\u201c") != t.count("\u201d"):
        problemas.append("aspas desbalanceadas")

    # ── Palavra repetida em sequência ──
    m = _re.search(r'\b(\w{3,})\s+\1\b', t, _re.IGNORECASE)
    if m:
        problemas.append(f"palavra repetida: '{m.group(1)}'")

    # ── Marcas de fragmento copiado do PDF ──
    if _re.search(r'\b[a-zà-ÿ]+[A-ZÀ-Ý][a-zà-ÿ]', t):
        problemas.append("palavras coladas (falha de extração)")
    if _re.search(r'\.\.\.$|…$', t.rstrip()):
        problemas.append("termina em reticências (truncado)")

    # ── Concordância em construções frequentes ──
    for padrao, desc in [
        (r'\bos\s+\w+a\b(?!s)', "artigo masculino com substantivo feminino"),
        (r'\bas\s+\w+os\b',      "artigo feminino com substantivo masculino"),
        (r'\bde\s+a\b',           "'de a' em vez de 'da'"),
        (r'\bem\s+o\b',           "'em o' em vez de 'no'"),
        (r'\ba\s+a\b',            "artigo duplicado"),
    ]:
        if _re.search(padrao, t, _re.IGNORECASE):
            problemas.append(desc)
            break

    return problemas


def _negar_afirmacao(frase: str):
    """
    Nega uma afirmação verdadeira para usá-la como distrator.

    Serve à recuperação de trechos cuja limpeza removeu afirmações falsas
    demais: negar um pressuposto produz enunciado falso, sobre o mesmo
    assunto e verificável na leitura.

    Recusa estruturas que não sobrevivem à inversão — correlativas,
    concessivas, múltiplas orações —, pelo mesmo motivo documentado em
    gerador_interpretacao._negar.
    """
    import re as _re
    t = str(frase or "").strip().rstrip(".")
    if not t:
        return None

    baixo = t.lower()
    FRAGEIS = ("mas sim", "e sim", "senão", "apesar de", "embora",
               "ainda que", "por outro lado", "ao contrário", "em vez de",
               "não apenas", "não só", "nem sempre", "no entanto")
    if any(e in baixo for e in FRAGEIS):
        return None
    if _re.search(r'[;:]|,\s*(?:mas|porém|contudo|pois|enquanto)\b', t, _re.I):
        return None
    if len(t.split()) > 22:
        return None

    marcas = len(_re.findall(r'\b(?:não|nunca|jamais|nem)\b', baixo))
    if marcas > 1:
        return None
    if marcas == 1:
        r = _re.sub(r'\bnão\s+', "", t, count=1, flags=_re.I)
        return (r[0].upper() + r[1:]) if r != t else None

    # Ver comentário equivalente em gerador_interpretacao._negar: negar
    # termo já negativo produz "não é independente", difícil de ler —
    # sobretudo dentro de um comando que também é negativo.
    if _re.search(r'\b\w*(?:independente|independência|desnecessári|'
                  r'dispensáve|irrelevante|impossíve|improváve|inadequad|'
                  r'insuficiente|incapaz|incorret|inexistente|ausência|'
                  r'ausente|isent|exclu|impedi|proibi|nega|recusa|falta)'
                  r'\w*\b', t, _re.I):
        return None

    m = _re.search(r'\b(é|são|era|eram|foi|foram|pode|podem|deve|devem|'
                   r'tem|têm|existe|existem|depende|dependem|garante|'
                   r'garantem|permite|permitem|exige|exigem|requer|'
                   r'requerem|constitui|constituem|implica|implicam|'
                   r'representa|representam|significa|significam|'
                   r'contribui|contribuem|favorece|favorecem)\b', t)
    if not m or m.start() > len(t) * 0.7:
        return None
    # Ver comentário equivalente em gerador_interpretacao._negar: sem
    # ajustar a caixa sai "Não É importante investigar".
    inicio, resto = t[:m.start()], t[m.start():]
    if not inicio.strip() and resto[:1].isupper():
        resto = resto[0].lower() + resto[1:]
    prefixo = "Não " if not inicio.strip() else "não "
    return f"{inicio}{prefixo}{resto}"


def _texto_corrompido(texto: str) -> tuple:
    """
    O trecho transcrito tem sinais de extração defeituosa?

    A extração de PDF às vezes embaralha ou perde palavras, e o resultado
    passa por todos os outros filtros porque continua parecendo prosa. Um
    caso real: "O acolhimento se revela MENOS no discurso sobre ele DO QUE
    nas práticas" virou "O acolhimento se revela NO discurso sobre ele QUE
    DO as práticas" — o sentido se INVERTEU, e as alternativas, montadas a
    partir da análise do texto original, ficaram todas erradas.

    Detecta pelos padrões que a corrupção produz:
      • sequência de palavras funcionais sem núcleo ("que do as")
      • preposição seguida de artigo isolado sem substantivo
      • conector duplicado ("quanto em outros como")
      • concordância impossível entre determinante e núcleo

    Retorna (corrompido, motivo).
    """
    import re as _re
    t = " ".join(str(texto or "").split())
    if not t:
        return True, "vazio"

    # ── Três ou mais funcionais seguidas ──
    # Prosa correta raramente encadeia "que do as" ou "de a por o".
    FUNCIONAIS = (r'(?:de|do|da|dos|das|em|no|na|nos|nas|por|para|com|'
                  r'que|se|a|o|as|os|um|uma|ao|à|e|ou|mas|como|quanto)')
    m = _re.search(rf'\b{FUNCIONAIS}\s+{FUNCIONAIS}\s+{FUNCIONAIS}\b',
                   t, _re.IGNORECASE)
    if m:
        trecho_m = " ".join(m.group(0).lower().split())

        # Estruturas legítimas que encadeiam funcionais. Listar exceção
        # por exceção não funciona — "do que nas" é tão correto quanto
        # "do que as", e a lista nunca fecha. O critério é estrutural:
        # relativas ("a QUE SE refere") e comparativas ("mais DO QUE AS")
        # sempre têm "que" na posição do meio ou do fim, precedido de
        # preposição ou artigo, e seguido de pronome ou determinante.
        LEGITIMAS = (
            # relativa: preposição + que + pronome/verbo
            r'^(?:a|o|de|do|da|em|no|na|por|com|para)\s+que\s+'
            r'(?:se|a|o|as|os|um|uma|e)$',
            # comparativa: do/de + que + determinante
            r'^(?:do|de|da|dos|das)\s+que\s+'
            r'(?:a|o|as|os|na|no|nas|nos|um|uma|em|de)$',
            # "o que a/o" — sujeito oracional
            r'^(?:o|a)\s+que\s+(?:a|o|as|os|se|em|de)$',
        )
        import re as _re2
        if not any(_re2.fullmatch(p, trecho_m) for p in LEGITIMAS):
            return True, f"sequencia improvavel de palavras: '{m.group(0)}'"

    # ── Conectores correlativos quebrados ──
    # "tanto X quanto Y" exige os dois; sozinho indica perda de palavra.
    if _re.search(r'\bquanto\s+em\s+outros\b', t, _re.IGNORECASE):
        return True, "correlativa incompleta ('quanto em outros')"

    # ── Artigo indefinido antes de adjetivo sem núcleo ──
    # "não é um bom ou ruim" — falta o substantivo ("algo bom ou ruim").
    if _re.search(r'\b(?:um|uma)\s+(?:bom|boa|ruim|mau|má|melhor|pior)\s+'
                  r'(?:ou|e)\s+(?:bom|boa|ruim|mau|má|melhor|pior)\b',
                  t, _re.IGNORECASE):
        return True, "sintagma sem nucleo ('um bom ou ruim')"

    # ── Sintagma repetido ──
    #
    # A extração às vezes duplica um bloco: "aqueles de risco baixo COM
    # RISCO BAIXO que exigem". O detector de palavra repetida não pega,
    # porque as palavras não são adjacentes duas a duas — é a sequência
    # inteira que se repete.
    # A repetição pode vir colada ("da demanda espontânea da demanda
    # espontânea") ou separada por um conectivo ("de risco baixo COM
    # risco baixo") — a extração insere a preposição ao emendar os
    # fragmentos. Aceitamos até duas palavras de intervalo.
    CONECTIVOS = {"com", "de", "do", "da", "e", "ou", "em", "no", "na",
                  "que", "a", "o", "por", "para", "os", "as"}
    palavras = _re.findall(r'[a-zà-ÿ]+', t.lower())

    for tamanho in (4, 3, 2):
        for i in range(len(palavras) - tamanho + 1):
            a1 = palavras[i:i + tamanho]
            if len(" ".join(a1)) < 8:
                continue
            for lacuna in (0, 1, 2):
                j = i + tamanho + lacuna
                if j + tamanho > len(palavras):
                    continue
                # As palavras da lacuna precisam ser conectivos: um
                # sintagma repetido separado por conteúdo é coincidência.
                meio = palavras[i + tamanho:j]
                if meio and not all(p in CONECTIVOS for p in meio):
                    continue
                if a1 == palavras[j:j + tamanho]:
                    return True, f"sintagma repetido: '{' '.join(a1)}'"

    # ── Substantivo abstrato no plural onde cabia verbo ──
    # "várias definições OU REVELAÇÕES os múltiplos sentidos" (era "revela")
    if _re.search(r'\b(?:ou|e)\s+\w+ções\s+(?:os|as|o|a)\s+\w+', t, _re.IGNORECASE):
        return True, "provavel verbo substituido por substantivo"

    return False, ""


def _extrair_texto_local(pdf_bytes: bytes, max_paginas: int = None) -> str:
    """
    Extrai o texto do PDF localmente, para conferência.

    O Gemini recebe o PDF e faz a própria extração — que às vezes troca
    palavras ("irritados" vira "irredentos"), duplica blocos ("de risco
    baixo com risco baixo") ou perde trechos inteiros. Quando isso
    acontece, o campo "texto" da análise não corresponde ao livro, e as
    questões passam a perguntar sobre um parágrafo que não existe.

    Extraindo aqui em paralelo, podemos conferir se o que o modelo diz
    ter transcrito está mesmo no arquivo.
    """
    import io as _io
    try:
        import pdfplumber as _pp
        partes = []
        with _pp.open(_io.BytesIO(pdf_bytes)) as pdf:
            paginas = pdf.pages[:max_paginas] if max_paginas else pdf.pages
            for p in paginas:
                try:
                    txt = p.extract_text() or ""
                except Exception:
                    txt = ""
                if txt:
                    partes.append(txt)
        return " ".join(partes)
    except Exception:
        return ""


def _trecho_confere_com_pdf(texto_trecho: str, texto_pdf: str,
                            limiar: float = 0.55) -> tuple:
    """
    O parágrafo transcrito existe mesmo no PDF?

    Compara sequências de 4 palavras. Uma transcrição fiel reencontra
    quase todas no arquivo; uma com palavras trocadas ou blocos
    duplicados reencontra poucas.

    O limiar é tolerante (55%) porque as duas extrações — a do Gemini e a
    do pdfplumber — normalizam hifenização, quebras de linha e
    ligaduras de formas diferentes. O que se quer pegar é a divergência
    grosseira, não a variação de formatação.

    Retorna (confere, taxa). Se a extração local falhou, devolve
    (True, 1.0): sem base de comparação, não se acusa.
    """
    import re as _re
    import unicodedata as _ud

    if not texto_pdf or len(texto_pdf) < 500:
        return True, 1.0

    def _norm(t):
        t = _ud.normalize("NFKD", str(t or "").lower())
        t = "".join(ch for ch in t if not _ud.combining(ch))
        return _re.findall(r'[a-z0-9]+', t)

    pal_trecho = _norm(texto_trecho)
    if len(pal_trecho) < 12:
        return True, 1.0

    corpo = " ".join(_norm(texto_pdf))
    ngramas = [" ".join(pal_trecho[i:i + 4])
               for i in range(0, len(pal_trecho) - 3, 2)]
    if not ngramas:
        return True, 1.0

    achados = sum(1 for g in ngramas if g in corpo)
    taxa = achados / len(ngramas)
    return taxa >= limiar, taxa


def validar_trecho(t: dict) -> tuple:
    """
    Valida um trecho extraído pelo Gemini antes de salvá-lo.
    Retorna (ok: bool, motivo: str).

    A análise do modelo (tese, pressupostos, afirmações falsas) é o gabarito
    das futuras questões de interpretação — por isso passa pelo mesmo rigor
    que aplicamos às questões geradas.
    """
    if not isinstance(t, dict):
        return False, f"trecho nao e objeto (veio {type(t).__name__})"

    texto = (t.get("texto") or "").strip()
    tese  = (t.get("tese")  or "").strip()
    press = t.get("pressupostos") or []
    falsas = t.get("afirmacoes_falsas") or []

    if not texto:
        return False, "sem texto"
    if not tese:
        return False, "sem tese"

    if len(texto) < MIN_CHARS_TRECHO:
        return False, f"texto curto demais ({len(texto)} car.)"
    if len(texto) > MAX_CHARS_TRECHO:
        reduzido = _reduzir_trecho(texto, MAX_CHARS_TRECHO)
        if reduzido is None:
            return False, (f"texto longo ({len(texto)} car.) e sem fronteira "
                           f"de frase aproveitável")
        # A redução pode ter cortado justamente onde estava o fundamento da
        # tese. Confere se o que sobrou ainda ancora a análise: ao menos
        # metade das palavras de conteúdo da tese deve aparecer no texto
        # reduzido. Sem isso, a questão perguntaria sobre algo que o aluno
        # não tem como ler.
        import re as _re_anc
        def _radicais(txt):
            return {p[:6] for p in _re_anc.findall(r'[a-zà-ÿ]{5,}', str(txt).lower())}

        rad_tese = _radicais(tese)
        rad_red  = _radicais(reduzido)
        if rad_tese:
            ancoragem = len(rad_tese & rad_red) / len(rad_tese)
            # 0.25 em vez de 0.4: uma tese bem escrita REFORMULA o
            # parágrafo, então compartilha menos vocabulário do que uma
            # paráfrase próxima. O limiar alto punia justamente a análise
            # de melhor qualidade.
            if ancoragem < 0.25:
                return False, (f"reducao do texto ({len(texto)}→{len(reduzido)} "
                               f"car.) removeu o fundamento da tese "
                               f"(ancoragem {ancoragem:.0%})")

        t["texto"] = reduzido          # grava a versão encurtada
        texto = reduzido

    if not isinstance(press, list) or len(press) < 1:
        return False, "sem pressupostos"

    # A checagem de quantidade de falsas ficou para o FIM da validação:
    # antes ela derrubava o trecho aqui, e a recuperação por negação (que
    # completa a lista a partir das afirmações verdadeiras) nunca chegava
    # a rodar. Foi o que reduziu um livro de 9 trechos para 3.
    if not isinstance(falsas, list):
        return False, "afirmacoes falsas em formato inesperado"

    # Trechos majoritariamente compostos de fórmula não servem como
    # texto-base: a extração de PDF achata expoentes ("x²" vira "x2") e o
    # enunciado fica ilegível.
    # Extração defeituosa: o texto continua parecendo prosa mas perdeu ou
    # embaralhou palavras, e o sentido pode ter se invertido.
    corrompido, motivo_corr = _texto_corrompido(texto)
    if corrompido:
        return False, f"texto com extracao defeituosa: {motivo_corr}"

    # Frases completas de prosa: o trecho precisa argumentar em palavras,
    # não só apresentar definições simbólicas.
    import re as _re_prosa
    # Lista fechada de verbos não funciona: rejeitava "exige", "precede",
    # "organiza", "reconhece" — que são justamente os verbos de texto
    # argumentativo. O critério agora é estrutural: a frase precisa ter
    # extensão e conter marcas de prosa (preposições, artigos, conectivos)
    # em densidade compatível com linguagem corrente, não com notação.
    MARCAS_PROSA = _re_prosa.compile(
        r'\b(?:de|da|do|das|dos|em|no|na|nos|nas|para|por|com|sem|'
        r'que|se|como|quando|onde|ao|à|às|aos|um|uma|uns|umas|'
        r'o|a|os|as|e|ou|mas|porém|entretanto|portanto|assim)\b',
        _re_prosa.I)

    frases_prosa = []
    for f in _re_prosa.split(r'[.;]\s+', texto):
        palavras = f.split()
        if len(palavras) < 8:
            continue
        # Densidade de marcas de prosa: texto corrente fica acima de 20%
        marcas = len(MARCAS_PROSA.findall(f))
        if marcas / len(palavras) >= 0.20:
            frases_prosa.append(f)
    # Uma frase argumentativa basta: textos acadêmicos usam períodos
    # longos, e um parágrafo inteiro pode ser uma oração só bem
    # desenvolvida. Exigir duas descartava material aproveitável.
    if len(frases_prosa) < 1:
        return False, "trecho sem nenhuma frase de prosa argumentativa"

    densidade = _densidade_notacao(texto)
    if densidade > MAX_DENSIDADE_NOTACAO:
        return False, (f"trecho e majoritariamente notacao ou diagrama "
                       f"({densidade:.0%} das linhas)")

    # Enunciado de exercício resolvido não é texto argumentativo: o autor
    # não defende tese ali, apenas resolve. Reconhecido pelo par
    # "pergunta em itens" + "Solução".
    import re as _re_ex
    if _re_ex.search(r'\b[a-e]\)\s', texto) and _re_ex.search(
            r'\bSolu[çc][ãa]o\b|\bResolu[çc][ãa]o\b|\bResposta:', texto):
        return False, "trecho e exercicio resolvido, nao texto argumentativo"

    # Citação literal: a análise deve reformular, não recortar o texto.
    # Um fragmento copiado vira alternativa cortada no meio da frase e
    # ainda permite acertar por busca visual no parágrafo.
    # A tese é obrigatória: se ela for cópia, o trecho não serve.
    if tese and _e_citacao_literal(tese, texto):
        return False, (f"tese e citacao literal do texto, nao reformulacao "
                       f"(\"{str(tese)[:40]}\")")

    # Os demais campos são REMOVIDOS individualmente em vez de derrubarem
    # o trecho: um pressuposto copiado é perda pequena diante de descartar
    # um parágrafo inteiro que serve para as outras questões. A validação
    # posterior confere se sobrou material suficiente.
    if t.get("ideia_secundaria") and _e_citacao_literal(t["ideia_secundaria"], texto):
        t["ideia_secundaria"] = ""

    t["pressupostos"] = [
        p for p in (t.get("pressupostos") or [])
        if not _e_citacao_literal(p, texto) and not _checar_redacao(p, "p")]

    t["afirmacoes_falsas"] = [
        f for f in (t.get("afirmacoes_falsas") or [])
        if not _e_citacao_literal(f, texto) and not _checar_redacao(f, "f")]

    # Redação de cada afirmação: elas entram direto nas alternativas
    # Só a TESE derruba o trecho: sem ela não há questão possível. Um
    # problema na ideia secundária custa um tipo de questão, não o
    # parágrafo inteiro.
    probs_tese = _checar_redacao(tese, "tese") if tese else ["sem tese"]
    if probs_tese:
        return False, f"tese com problema de redacao: {probs_tese[0]}"

    if t.get("ideia_secundaria") and _checar_redacao(t["ideia_secundaria"], "i"):
        t["ideia_secundaria"] = ""

    # Após a limpeza, confere se restou material para montar as questões
    # Se a limpeza deixou poucas falsas, tenta completar negando as
    # afirmações verdadeiras do próprio trecho — falsas por construção e
    # sobre o mesmo assunto. Só descarta se nem assim chegar a duas.
    falsas_ok = t.get("afirmacoes_falsas") or []
    if len(falsas_ok) < 2:
        candidatas = [tese, t.get("ideia_secundaria")] + \
                     list(t.get("pressupostos") or [])
        for base in candidatas:
            if len(falsas_ok) >= 2:
                break
            if not base:
                continue
            neg = _negar_afirmacao(base)
            if neg and neg not in falsas_ok and not _checar_redacao(neg, "f"):
                falsas_ok.append(neg)
        t["afirmacoes_falsas"] = falsas_ok

    if len(t.get("afirmacoes_falsas") or []) < 2:
        return False, ("restaram menos de 2 afirmacoes falsas aproveitaveis "
                       "apos remover copias e frases mal formadas")

    # A tese não pode ser cópia literal do trecho — nesse caso a questão
    # se responderia por busca visual, sem interpretação.
    if tese.lower() in texto.lower():
        return False, "tese e copia literal do texto"

    # Nenhuma afirmação falsa pode repetir a tese (seria gabarito duplicado)
    tese_norm = " ".join(tese.lower().split())
    for f in falsas:
        if " ".join(str(f).lower().split()) == tese_norm:
            return False, "afirmacao falsa identica a tese"

    # Alternativas precisam ser distintas entre si
    todas = [tese] + [str(x) for x in falsas] + [str(x) for x in press]
    norm = [" ".join(x.lower().split()) for x in todas if x]
    if len(set(norm)) != len(norm):
        return False, "ha alternativas repetidas entre tese/pressupostos/falsas"

    # Cada alternativa precisa ter conteúdo real
    for x in todas:
        if len(str(x).strip()) < 15:
            return False, f"alternativa curta demais: '{str(x)[:25]}'"

    return True, ""


# ══════════════════════════════════════════════════════════════════
#  AUTOTESTE DOS VALIDADORES
# ══════════════════════════════════════════════════════════════════
#
#  Roda a cada indexação, antes de chamar a API. Verifica se os
#  validadores deste arquivo rejeitam os defeitos já conhecidos.
#
#  Existe porque houve várias rodadas em que a correção estava pronta
#  mas o arquivo em uso era o anterior, e o mesmo defeito reaparecia
#  sem que ficasse claro se o problema era do código ou da cópia.
#  Agora o próprio programa responde isso.
#
VERSAO_VALIDADORES = "2026-08-19"

CASOS_CONHECIDOS = [
    # (texto, deve_ser_rejeitado, apelido)
    ("Os profissionais da recepção, ao identificarem riscos e vulnerabilidades",
     True,  "fragmento: infinitivo"),
    ("O SUS, apesar de ser um exemplo de política pública e um patrimônio público",
     True,  "fragmento: infinitivo apos concessiva"),
    ("A atenção básica, atuando como porta de entrada e articuladora da rede",
     True,  "fragmento: gerundio"),
    ("A banalização do sofrimento alheio, exemplificada pelo caso de Joana",
     True,  "fragmento: participio"),
    ("O acolhimento reconhece o usuário como definidor de suas",
     True,  "termina em possessivo"),
    ("A implementação requer mais do que ações normativas ou a simples",
     True,  "termina em adjetivo"),
    ("A equipe organiza o atendimento considerando",
     True,  "termina em gerundio"),
    ("O acolhimento é uma uma prática constitutiva do cuidado",
     True,  "palavra repetida"),
    ("A escuta precede a triagem , conforme o texto afirma",
     True,  "espaco antes de pontuacao"),
    ("A equipeDe saúde realiza a primeira escuta do usuário",
     True,  "palavras coladas"),
    ("Para um acolhimento eficaz da demanda espontânea",
     True,  "adjunto sem oracao principal"),
    ("Não É importante investigar quem atua na recepção da unidade",
     True,  "caixa quebrada apos negacao"),
    ("Diante das situações imprevistas que chegam ao serviço",
     True,  "adjunto com contracao"),
    ("A implementação requer mais do que ações normativas ou a simples",
     True,  "adjetivo antepositivo pendurado"),
    # ── Casos que DEVEM passar: guarda contra excesso de rigor ──
    ("A equipe, ao identificar o risco, deve priorizar o atendimento",
     False, "reduzida fechada por predicado"),
    ("Trabalhadores da recepção devem participar das reuniões da equipe",
     False, "afirmacao simples"),
    ("A identificação de risco não depende de formação específica em saúde",
     False, "afirmacao com negacao"),
    ("O acolhimento envolve escuta, análise e definição de oferta de cuidado",
     False, "enumeracao com virgula"),
    ("Para garantir o acesso equitativo, a unidade precisa rever seus fluxos",
     False, "adjunto COM oracao principal"),
    ("O mais importante não é encontrar uma definição única",
     False, "adjetivo posposto legitimo"),
    ("Diante de situações imprevistas, a equipe aciona a retaguarda",
     False, "adjunto com contracao E principal"),
]


CASOS_CORRUPCAO = [
    # (texto, deve_ser_detectado, apelido)
    ("aqueles de risco baixo com risco baixo que exigem atendimento imediato",
     True,  "sintagma repetido com conectivo"),
    ("A equipe de saúde de saúde realiza a primeira escuta do usuário",
     True,  "sintagma repetido colado"),
    ("O acolhimento se revela no discurso sobre ele que do as práticas",
     True,  "sequencia improvavel de funcionais"),
    ("A existência de várias definições ou revelações os múltiplos sentidos",
     True,  "verbo trocado por substantivo"),
    ("O acolhimento à demanda espontânea exige que a equipe reconheça a "
     "necessidade apresentada pelo usuário como legítima",
     False, "prosa correta"),
    ("A prática revela mais do que as declarações formais da gestão local",
     False, "comparativa legitima"),
    ("As situações a que se refere o texto exigem escuta qualificada",
     False, "relativa legitima"),
    ("Cada usuário tem sua equipe, e cada equipe tem sua área de abrangência",
     False, "repeticao legitima"),
]


def autoteste_validadores(verbose: bool = True) -> bool:
    """
    Confere se os validadores deste arquivo estão completos.

    Retorna True se todos os casos conhecidos forem tratados como
    esperado. Um resultado negativo significa que este arquivo não tem
    todas as correções — provavelmente é uma cópia antiga.
    """
    falhas = []
    for texto, deve_rejeitar, apelido in CASOS_CONHECIDOS:
        rejeitou = bool(_checar_redacao(texto, "autoteste"))
        if rejeitou != deve_rejeitar:
            falhas.append((apelido,
                           "passou quando devia barrar" if deve_rejeitar
                           else "barrou quando devia passar"))

    if verbose:
        if falhas:
            print(f"   ⚠ AUTOTESTE: {len(falhas)} de {len(CASOS_CONHECIDOS)} "
                  f"casos falharam")
            for apelido, o_que in falhas[:5]:
                print(f"      ✗ {apelido}: {o_que}")
            print(f"      → este indexar_livro.py NAO tem todas as correcoes")
            print(f"      → versao esperada: {VERSAO_VALIDADORES}")
        else:
            print(f"   ✓ validadores ok "
                  f"({len(CASOS_CONHECIDOS) + len(CASOS_CORRUPCAO)} casos, "
                  f"versao {VERSAO_VALIDADORES})")
    return not falhas


def indexar_livro(caminho_pdf: str, titulo: str = None, disciplina: str = None, forcar: bool = False):
    """
    Lê o PDF e usa o Gemini para identificar a estrutura do livro.
    Salva tudo no Firebase para reuso.

    Checa duplicatas em 2 níveis ANTES de chamar Gemini:
    1. Por nome do arquivo (rápido)
    2. Por hash do conteúdo (à prova de renomeação)

    Use forcar=True para indexar mesmo se já existir.
    """
    if not os.path.isfile(caminho_pdf):
        print(f"❌ Arquivo não encontrado: {caminho_pdf}")
        return

    nome_arquivo = os.path.basename(caminho_pdf)
    autoteste_validadores()
    print(f"\n📚 Indexando: {nome_arquivo}")

    # ─── CHECAGEM 1: por nome do arquivo (rápida, sem ler PDF) ───
    if not forcar:
        existente = ja_indexado_por_nome(nome_arquivo)
        if existente:
            print(f"   ⏭  Já indexado anteriormente (mesmo nome de arquivo).")
            print(f"   ID existente: {existente}")
            print(f"   Use --forcar pra re-indexar.")
            return existente

    # Lê o PDF
    with open(caminho_pdf, "rb") as f:
        pdf_bytes = f.read()

    tamanho_mb = len(pdf_bytes) / 1024 / 1024
    print(f"   Tamanho: {tamanho_mb:.1f} MB")

    # ─── CHECAGEM 2: por hash do conteúdo (à prova de renomeação) ───
    if not forcar:
        hash_pdf = calcular_hash_pdf(pdf_bytes)
        print(f"   Hash: {hash_pdf[:16]}...")

        existente_id, nome_original = ja_indexado_por_hash(hash_pdf)
        if existente_id:
            print(f"   ⏭  CONTEÚDO já indexado antes como '{nome_original}'.")
            print(f"   ID existente: {existente_id}")
            print(f"   (Você renomeou o arquivo? O conteúdo é idêntico.)")
            print(f"   Use --forcar pra re-indexar mesmo assim.")
            return existente_id
    else:
        hash_pdf = calcular_hash_pdf(pdf_bytes)

    # Conta páginas
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_paginas = len(pdf.pages)
        print(f"   Páginas: {total_paginas}")
    except Exception as e:
        print(f"⚠ Não consegui contar páginas: {e}")
        total_paginas = 0

    # Estima tokens (~258 por página)
    tokens_estimados = total_paginas * 258
    print(f"   Tokens estimados: {tokens_estimados:,}")

    if tokens_estimados > 800_000:
        print(f"⚠ ATENÇÃO: livro muito grande, pode demorar ou estourar contexto.")
        print(f"   Vou tentar mesmo assim.")

    # ───────────────────────────────────────
    # Pede pro Gemini analisar o livro
    # ───────────────────────────────────────
    print(f"\n🤖 Enviando para o Gemini analisar...")

    prompt = f"""
Você é um especialista em análise de livros didáticos e técnicos.

Recebeu o livro "{titulo or nome_arquivo}" para análise.

Sua tarefa tem DUAS partes:

PARTE 1 — ESTRUTURA
Identifique título, autor, disciplina e os capítulos com seus tópicos.

PARTE 2 — TRECHOS PARA INTERPRETAÇÃO
Selecione de {MIN_TRECHOS} a {MAX_TRECHOS} parágrafos do livro que sirvam
como base para questões de interpretação de texto, e ANALISE cada um.

Critérios para escolher um parágrafo:
- Ter entre {MIN_CHARS_TRECHO} e {MAX_CHARS_TRECHO} caracteres.
  Prefira o PARÁGRAFO INTEIRO a um recorte: cortar no meio deixa o
  raciocínio incompleto e inviabiliza a questão
- Ser autossuficiente (compreensível fora do contexto do capítulo)
- Apresentar uma ideia defendida, um argumento ou uma explicação
  (evite listas, sumários, definições soltas e trechos meramente descritivos)
- Ser PROSA CORRIDA. Não selecione demonstrações, sequências de fórmulas,
  tabelas nem enunciados de exercício. Expoentes e índices se perdem na
  extração do PDF ("x²" vira "x2"), tornando o trecho ilegível para o aluno.
  Prefira parágrafos onde o autor EXPLICA ou ARGUMENTA em palavras
- Estar distribuído ao longo do livro, não todos do mesmo capítulo

╔══════════════════════════════════════════════════════════════════╗
║  REGRA QUE GOVERNA TODA A PARTE 2                                ║
║                                                                  ║
║  Você NÃO está explicando o assunto. Está descrevendo o que      ║
║  ESTE parágrafo, e apenas ele, afirma.                           ║
║                                                                  ║
║  Antes de escrever cada campo, localize no texto transcrito a    ║
║  passagem exata que o sustenta. Se não conseguir apontar as      ║
║  palavras do autor, a afirmação NÃO ENTRA — por mais correta     ║
║  que seja no assunto.                                            ║
║                                                                  ║
║  O que você sabe sobre o tema é IRRELEVANTE aqui, e atrapalha.   ║
╚══════════════════════════════════════════════════════════════════╝

Para CADA trecho selecionado, informe:

- "texto": o parágrafo TRANSCRITO LITERALMENTE do livro, sem alterações

- "tese": a ideia central que o autor defende NESTE parágrafo, em uma frase.

  ⚠️ REFORMULE com suas palavras. Não copie um pedaço do parágrafo: um
  recorte fica cortado no meio ("...permanecem nas áreas.") e não é uma
  afirmação, além de permitir acertar a questão por busca visual no texto.

  ⚠️ A tese é o que o autor AFIRMA, não o valor do que ele descreve.
  Se o parágrafo explica COMO um procedimento funciona, a tese é sobre
  o funcionamento — não sobre seus benefícios.

  ✗ ERRADO: o parágrafo detalha quem faz a primeira escuta e quem fica
    na retaguarda, e a tese vira "fortalece o vínculo e a
    responsabilização". Vínculo não é mencionado no trecho.
  ✓ CERTO: "a primeira escuta é feita por profissionais da própria
    equipe de referência, em arranjos que variam conforme a unidade."

  ⚠️ Preserve a ÊNFASE do autor. Construções como "não só X, mas
  sobretudo Y" colocam o peso em Y; inverter isso falsifica a tese.

  ✗ ERRADO: texto diz "deve fazer diferença não só para os gestores,
    mas sobretudo para usuários e trabalhadores" → tese "deve gerar
    impacto para os gestores". Inverteu o que o autor destacou.
  ✓ CERTO: "o acolhimento precisa fazer diferença principalmente para
    usuários e trabalhadores, não apenas para a gestão."

- "pressupostos": de 1 a 3 ideias que o texto ASSUME como verdadeiras sem
  afirmar explicitamente — mas que decorrem necessariamente do que está
  escrito.

  Teste: se o pressuposto fosse falso, alguma frase do parágrafo deixaria
  de fazer sentido? Se não, não é pressuposto do texto.

  ✗ ERRADO: texto afirma "se A independe de B, então B independe de A"
    → pressuposto "e também seus complementares". Verdade na teoria,
    ausente do trecho.
  ✓ CERTO: "a independência entre eventos é uma relação simétrica."

- "ideia_secundaria": um argumento de apoio EXPLICITAMENTE presente no
  trecho — algo que o autor diz para sustentar a tese, não a tese em
  outras palavras.

- "afirmacoes_falsas": de 2 a 4 afirmações que o trecho CONTRADIZ.

  ⚠️ CRÍTICO: elas serão embaralhadas com as verdadeiras numa questão
  do tipo "assinale a que NÃO encontra apoio no texto". Para essa
  questão ter UMA resposta, cada falsa precisa ser contradita por uma
  passagem localizável, e cada verdadeira precisa estar no texto.

  Cada falsa deve tratar do MESMO ponto abordado no parágrafo, invertendo
  ou exagerando o que o autor diz. Uma afirmação sobre outro assunto é
  eliminada sem leitura e não serve.

  ✗ ERRADO: "a irritação dos usuários é infundada" — o texto diz que ela
    é comum e deve ser acolhida, mas em momento nenhum discute se é
    fundada. Não há passagem que a contradiga diretamente.
  ✓ CERTO: "diante da irritação do usuário, cabe à equipe reagir e
    esclarecer as regras" — o texto diz o oposto: acolher em vez de
    reagir. A contradição é localizável.

- "ancoras": OBRIGATÓRIO. Para cada item acima, a passagem do parágrafo
  que o sustenta (ou, no caso das falsas, que a contradiz), COPIADA
  LITERALMENTE, em até 12 palavras.

  Um trecho sem este campo será descartado.

  Escreva a âncora ANTES de escrever o item que ela sustenta: localize a
  passagem no parágrafo, depois formule a afirmação a partir dela. Fazer
  o contrário — escrever a afirmação e procurar justificativa — é o que
  produz teses que o texto não contém.

  Formato:
    "ancoras": {{
      "tese": "palavras copiadas do parágrafo",
      "pressupostos": ["palavras do 1º", "palavras do 2º"],
      "ideia_secundaria": "palavras copiadas",
      "afirmacoes_falsas": ["passagem que contradiz a 1ª",
                            "passagem que contradiz a 2ª"]
    }}

Retorne SOMENTE um JSON válido neste formato:
{{
  "titulo":     "Título do livro",
  "autor":      "Nome do autor (ou 'Desconhecido')",
  "disciplina": "Disciplina principal",
  "descricao":  "Resumo do livro em 2 frases",
  "capitulos": [
    {{
      "numero":    1,
      "titulo":    "Nome do capítulo",
      "pagina_inicial": 12,
      "pagina_final":   45,
      "topicos": ["Tópico 1", "Tópico 2", "Tópico 3"],
      "resumo":    "O que esse capítulo aborda em 1-2 frases"
    }}
  ],
  "trechos": [
    {{
      "capitulo":  1,
      "pagina":    23,
      "texto":     "Parágrafo transcrito literalmente do livro.",
      "tese":      "A ideia central defendida no parágrafo.",
      "pressupostos": [
        "Algo que o texto assume sem afirmar",
        "Outro pressuposto"
      ],
      "ideia_secundaria": "Um argumento de apoio presente no trecho.",
      "ancoras": {{
        "tese": "palavras exatas do parágrafo que sustentam a tese",
        "pressupostos": ["palavras que sustentam o 1º", "as do 2º"],
        "ideia_secundaria": "palavras que sustentam a ideia secundária",
        "afirmacoes_falsas": ["palavras que CONTRADIZEM a 1ª falsa",
                              "as que contradizem a 2ª"]
      }},
      "afirmacoes_falsas": [
        "Afirmação que contradiz o trecho",
        "Afirmação que o trecho não sustenta"
      ]
    }}
  ]
}}

REGRAS CRÍTICAS:
- O campo "texto" DEVE ser transcrição literal. Não resuma nem reescreva.
- A "tese" precisa ser sustentada pelo próprio trecho, sem depender de
  conhecimento externo ao parágrafo.
- As "afirmacoes_falsas" NÃO podem ser verdadeiras segundo o trecho.
- Se o livro não tiver parágrafos adequados (por exemplo, se for uma
  coletânea de exercícios ou uma tabela de dados), retorne "trechos": [].

Identifique TODOS os capítulos. Liste 3-8 tópicos por capítulo.
VERIFICAÇÃO FINAL, antes de responder: percorra cada trecho e confirme que
o campo "ancoras" existe e que cada âncora aparece LITERALMENTE no campo
"texto" do mesmo trecho. Trechos sem âncora são descartados; âncoras que
não aparecem no texto invalidam o item que sustentam.

Use apenas aspas duplas. Não use quebras de linha dentro dos campos.
"""

    arquivo_pdf = {
        "mime_type": "application/pdf",
        "data":      pdf_bytes,
    }

    try:
        resposta = modelo.generate_content(
            [arquivo_pdf, prompt],
            generation_config={
                "max_output_tokens":  32000,
                "temperature":        0.2,
                "response_mime_type": "application/json",
            }
        )

        # Tokens usados
        try:
            usage = resposta.usage_metadata
            print(f"   Tokens: {usage.prompt_token_count:,} input | {usage.candidates_token_count:,} output")
        except AttributeError:
            pass

        raw = resposta.text.strip().replace("```json", "").replace("```", "").strip()

        # ─── Reparo de JSON (mesma estratégia da simulados_api) ───
        # Livros grandes geram respostas longas, onde o Gemini frequentemente
        # trunca o JSON. Sem reparo, o livro inteiro é perdido DEPOIS de já ter
        # gastado a cota do Gemini. O reparo tenta salvar o que der.
        analise = _decodificar_com_reparo(raw)
        if analise is None:
            print("❌ Gemini retornou JSON inválido (irreparável).")
            return

    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return

    # Garante que veio um objeto (dict). Se o Gemini devolver uma lista ou
    # outro tipo, analise.get(...) quebraria com AttributeError.
    if not isinstance(analise, dict):
        print(f"❌ Gemini retornou formato inesperado "
              f"(esperava objeto, veio {type(analise).__name__}). Abortando.")
        return

    # ───────────────────────────────────────
    # Salva no Firebase
    # ───────────────────────────────────────
    livro_id = str(uuid.uuid4())

    print(f"\n💾 Salvando no Firebase...")
    print(f"   Título identificado: {analise.get('titulo')}")
    print(f"   Autor: {analise.get('autor')}")
    print(f"   Disciplina: {analise.get('disciplina')}")
    print(f"   Capítulos: {len(analise.get('capitulos', []))}")

    # ─── Valida os trechos extraídos ───
    trechos_brutos = analise.get("trechos") or []
    if not isinstance(trechos_brutos, list):
        trechos_brutos = []

    trechos_ok, descartados, sem_ancora = [], [], []
    fora_do_pdf = []

    # Extração local do PDF, para conferir as transcrições. O Gemini faz
    # a própria leitura do arquivo e às vezes troca palavras ou duplica
    # blocos; sem uma segunda fonte, não há como saber.
    texto_pdf_local = _extrair_texto_local(pdf_bytes)
    if texto_pdf_local:
        print(f"   Texto extraído localmente para conferência: "
              f"{len(texto_pdf_local):,} caracteres")
    for i, t in enumerate(trechos_brutos):
        ok, motivo = validar_trecho(t)
        if ok:
            # Confere se a análise está ancorada no parágrafo. Uma âncora
            # que não existe no texto indica que o modelo escreveu a partir
            # do que sabe do assunto, não do que leu — a causa raiz das
            # questões cujo gabarito não se sustenta na leitura.
            n_falhas, avisos_ancora = verificar_ancoras(t)
            if n_falhas:
                sem_ancora.append((i + 1, n_falhas, avisos_ancora))

            # A transcrição existe mesmo no arquivo?
            confere, taxa = _trecho_confere_com_pdf(t["texto"], texto_pdf_local)
            if not confere:
                fora_do_pdf.append((i + 1, taxa))
                descartados.append(
                    (i + 1, f"transcricao nao confere com o PDF "
                            f"(apenas {taxa:.0%} do texto foi localizado)"))
                continue

            trechos_ok.append({
                "trecho_id":        f"{livro_id[:8]}-{len(trechos_ok)+1:02d}",
                "capitulo":         t.get("capitulo"),
                "pagina":           t.get("pagina"),
                "texto":            t["texto"].strip(),
                "tese":             t["tese"].strip(),
                "pressupostos":     [str(p).strip() for p in t.get("pressupostos", [])],
                "ideia_secundaria": (t.get("ideia_secundaria") or "").strip(),
                "afirmacoes_falsas": [str(f).strip() for f in t.get("afirmacoes_falsas", [])],
                "ancoras":          t.get("ancoras") or {},
                "ancoras_verificadas": n_falhas == 0,
            })
        else:
            descartados.append((i + 1, motivo))

    if descartados:
        print(f"   ⚠ {len(descartados)} trecho(s) descartado(s) na validação:")
        for num, motivo in descartados[:5]:
            print(f"      trecho {num}: {motivo}")

    if fora_do_pdf:
        print(f"   ⚠ {len(fora_do_pdf)} trecho(s) descartado(s) por divergirem "
              f"do PDF original:")
        for num, taxa in fora_do_pdf[:3]:
            print(f"      trecho {num}: só {taxa:.0%} do texto foi localizado "
                  f"no arquivo")
        print(f"      → a extração do modelo trocou palavras ou duplicou "
              f"blocos nesses trechos.")

    if sem_ancora:
        total_falhas = sum(n for _, n, _ in sem_ancora)
        print(f"   ⚠ {len(sem_ancora)} trecho(s) com {total_falhas} afirmação(ões) "
              f"não localizada(s) no texto:")
        for num, n, avisos in sem_ancora[:3]:
            print(f"      trecho {num}: {avisos[0]}")
        print(f"      → esses trechos foram mantidos, mas as questões geradas "
              f"a partir deles merecem conferência.")
    print(f"   Trechos para interpretação: {len(trechos_ok)} "
          f"(de {len(trechos_brutos)} extraídos)")

    documento = {
        "livro_id":          livro_id,
        "arquivo_original":  nome_arquivo,
        "hash_conteudo":     hash_pdf,                                   # ← NOVO
        "titulo":            analise.get("titulo", titulo or nome_arquivo),
        "autor":             analise.get("autor", "Desconhecido"),
        "disciplina":        analise.get("disciplina", disciplina or "geral"),
        "descricao":         analise.get("descricao", ""),
        "capitulos":         analise.get("capitulos", []),
        "total_capitulos":   len(analise.get("capitulos", [])),
        "trechos":           trechos_ok,
        "total_trechos":     len(trechos_ok),
        "total_paginas":     total_paginas,
        "indexado_em":       datetime.now(timezone.utc),
    }

    db.collection("livros").document(livro_id).set(documento)

    print(f"\n✅ Livro indexado!")
    print(f"   ID:    {livro_id}")
    print(f"\nPara gerar questões deste livro:")
    print(f'   POST /livro/inspirar?livro_id={livro_id}&capitulo=1&quantidade=5\n')

    return livro_id


def indexar_em_lote(padrao: str, disciplina: str = None, forcar: bool = False, pausa: int = 5):
    """
    Indexa todos os PDFs que casam com o padrão fornecido.
    Ex: 'livros/*.pdf' ou 'livros/matematica/*.pdf'

    Respeita a regra de NÃO-REGENERAR: livros já indexados são pulados,
    exceto se forcar=True.
    """
    import glob

    arquivos = sorted(glob.glob(padrao))

    if not arquivos:
        print(f"❌ Nenhum arquivo encontrado para o padrão: {padrao}")
        return

    print("\n" + "=" * 60)
    print(f"  INDEXANDO {len(arquivos)} LIVRO(S) EM LOTE")
    print(f"  Disciplina forçada: {disciplina or '(detectar automaticamente)'}")
    print(f"  Forçar re-indexar:  {forcar}")
    print(f"  Pausa entre livros: {pausa}s")
    print("=" * 60)

    sucessos = 0
    pulados  = 0
    falhas   = 0
    ids      = []

    for i, caminho in enumerate(arquivos, start=1):
        nome = os.path.basename(caminho)
        print(f"\n[{i}/{len(arquivos)}] {nome}")

        # Checa duplicata
        if not forcar:
            existente = ja_indexado(nome)
            if existente:
                print(f"   ⏭  Já indexado anteriormente (ID: {existente}). Pulando.")
                pulados += 1
                ids.append(existente)
                continue

        try:
            livro_id = indexar_livro(caminho, titulo=None, disciplina=disciplina, forcar=forcar)
            if livro_id:
                sucessos += 1
                ids.append(livro_id)

                # Pausa pra respeitar RPM
                if i < len(arquivos) and pausa > 0:
                    print(f"   ⏳ Pausando {pausa}s antes do próximo...")
                    import time
                    time.sleep(pausa)
            else:
                falhas += 1
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            falhas += 1
            continue

    print("\n" + "=" * 60)
    print(f"  ✅ CONCLUÍDO")
    print(f"     Indexados:  {sucessos}")
    print(f"     Pulados:    {pulados} (já existiam)")
    print(f"     Falhas:     {falhas}")
    print(f"\n  IDs dos livros (anote!):")
    for i, livro_id in enumerate(ids, start=1):
        print(f"     {i}. {livro_id}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Indexa um ou vários livros no Firebase."
    )
    parser.add_argument("pdf",
        help="Caminho de UM PDF ou padrão glob (ex: 'livros/*.pdf')")
    parser.add_argument("--titulo",
        help="Título customizado (só faz sentido para 1 livro)",
        default=None)
    parser.add_argument("--disciplina",
        help="Disciplina principal (aplicada a todos no lote)",
        default=None)
    parser.add_argument("--lote",
        action="store_true",
        help="Trata 'pdf' como padrão glob e indexa vários livros")
    parser.add_argument("--forcar",
        action="store_true",
        help="Re-indexa mesmo se já existir (cuidado: gasta Gemini)")
    parser.add_argument("--pausa",
        type=int, default=5,
        help="Pausa em segundos entre livros (padrão 5)")

    args = parser.parse_args()

    # Decide entre modo único e modo lote
    if args.lote or "*" in args.pdf:
        indexar_em_lote(args.pdf, args.disciplina, args.forcar, args.pausa)
    else:
        indexar_livro(args.pdf, args.titulo, args.disciplina, args.forcar)
