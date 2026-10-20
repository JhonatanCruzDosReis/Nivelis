"""
=============================================================
  GERADOR DE ANATOMIA
=============================================================
  Questões de anatomia humana geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Fatos tabelados — nervos cranianos, terminologia,
       forames, ossos, inervação
    ✅ Terminologia Anatômica oficial versus epônimos
    ❌ Anatomia aplicada à clínica ("lesão aqui causa qual
       déficit") — já é raciocínio diagnóstico
    ❌ Questões que dependem de imagem ou peça anatômica

  VERIFICAÇÃO DAS FONTES

  Registradas em anatomia/_fontes.md. Na conferência dos
  nervos cranianos, uma fonte atribuiu ao glossofaríngeo a
  gustação do terço ANTERIOR da língua — está trocado, e foi
  descartada. As demais concordam entre si.

  USO:
      from gerador_anatomia import gerar_lote, gerar_para_api
=============================================================
"""

import random
import re
import unicodedata

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


# ══════════════════════════════════════════════════════════
#  BASE DE FATOS
# ══════════════════════════════════════════════════════════

# ── Nervos cranianos ──
#
# Fontes: auladeanatomia.com; anatomia-papel-e-caneta.com; Toda Matéria;
# Estratégia MED. Cruzadas entre si.
#
# Campos: (romano, número, nome, tipo, função, saída do crânio, parassimpático)
NERVOS_CRANIANOS = [
    ("I", 1, "olfatório", "sensitivo",
     "condução dos impulsos olfatórios",
     "lâmina cribriforme do osso etmoide", False),
    ("II", 2, "óptico", "sensitivo",
     "condução dos impulsos visuais",
     "canal óptico", False),
    ("III", 3, "oculomotor", "motor",
     "inervação da maioria dos músculos extraoculares e constrição pupilar",
     "fissura orbital superior", True),
    ("IV", 4, "troclear", "motor",
     "inervação do músculo oblíquo superior do olho",
     "fissura orbital superior", False),
    ("V", 5, "trigêmeo", "misto",
     "sensibilidade da face e inervação dos músculos da mastigação",
     "fissura orbital superior, forame redondo e forame oval, conforme o ramo",
     False),
    ("VI", 6, "abducente", "motor",
     "inervação do músculo reto lateral do olho",
     "fissura orbital superior", False),
    ("VII", 7, "facial", "misto",
     "inervação dos músculos da expressão facial e gustação dos dois terços "
     "anteriores da língua",
     "meato acústico interno, com saída pelo forame estilomastóideo", True),
    ("VIII", 8, "vestibulococlear", "sensitivo",
     "audição, pela porção coclear, e equilíbrio, pela porção vestibular",
     "meato acústico interno", False),
    ("IX", 9, "glossofaríngeo", "misto",
     "gustação do terço posterior da língua e inervação da glândula parótida",
     "forame jugular", True),
    ("X", 10, "vago", "misto",
     "inervação parassimpática das vísceras torácicas e abdominais",
     "forame jugular", True),
    ("XI", 11, "acessório", "motor",
     "inervação dos músculos esternocleidomastóideo e trapézio",
     "forame jugular", False),
    ("XII", 12, "hipoglosso", "motor",
     "inervação dos músculos da língua",
     "canal do hipoglosso", False),
]

# ── Epônimos abolidos pela Terminologia Anatômica ──
#
# Fonte: Revista Brasileira de Ortopedia, "Terminologia Anatômica em
# Ortopedia"; Sociedade Brasileira de Anatomia.
#
# A TA aboliu os nomes de pessoas: o termo deve indicar forma, posição,
# função ou critério misto.
# Agrupados por sistema, para que os distratores possam vir da MESMA
# região do corpo quando isso tornar a questão mais exigente.
EPONIMOS = [
    # O terceiro campo é o SISTEMA. Antes ele existia só como comentário
    # de seção, e as 41 entradas saíam todas sob o rótulo único
    # "Terminologia Anatômica" — que respondia por mais da metade do que
    # este gerador produz. Num caderno de 30 de anatomia, treze questões
    # caíam no mesmo tópico, porque o teto de repetição por assunto não
    # tinha como separá-las.
    #
    # Com o sistema no rótulo, o teto volta a agir e o caderno se
    # espalha. Nenhum fato foi acrescentado: isto arruma a distribuição,
    # não o lastro.
    # ── Aparelho reprodutor e urinário ──
    ("trompa de Falópio",       "tuba uterina",
     "urogenital"),
    ("glândula de Bartholin",   "glândula vestibular maior",
     "urogenital"),
    ("glândula de Cowper",      "glândula bulbouretral",
     "urogenital"),
    ("glândulas de Skene",      "glândulas parauretrais",
     "urogenital"),
    ("bolsa de Douglas",        "escavação retouterina",
     "urogenital"),
    ("espaço de Retzius",       "espaço retropúbico",
     "urogenital"),
    ("corpúsculo de Malpighi",  "corpúsculo renal",
     "urogenital"),

    # ── Cabeça e pescoço ──
    ("trompa de Eustáquio",     "tuba auditiva",
     "cabeça e pescoço"),
    ("antro de Highmore",       "seio maxilar",
     "cabeça e pescoço"),
    ("fossa de Rosenmüller",    "recesso faríngeo",
     "cabeça e pescoço"),
    ("ducto de Stensen",        "ducto parotídeo",
     "cabeça e pescoço"),
    ("ducto de Wharton",        "ducto submandibular",
     "cabeça e pescoço"),
    ("aqueduto de Falópio",     "canal do nervo facial",
     "cabeça e pescoço"),

    # ── Sistema nervoso ──
    ("aqueduto de Sylvius",     "aqueduto do mesencéfalo",
     "sistema nervoso"),
    ("forame de Monro",         "forame interventricular",
     "sistema nervoso"),
    ("círculo de Willis",       "círculo arterial do cérebro",
     "sistema nervoso"),
    ("veia de Galeno",          "veia magna do cérebro",
     "sistema nervoso"),
    ("fissura de Sylvius",      "sulco lateral do cérebro",
     "sistema nervoso"),
    ("ponte de Varólio",        "ponte",
     "sistema nervoso"),
    ("canal de Alcock",         "canal do pudendo",
     "sistema nervoso"),

    # ── Aparelho digestório ──
    ("ducto de Wirsung",        "ducto pancreático",
     "digestório"),
    ("ducto de Santorini",      "ducto pancreático acessório",
     "digestório"),
    ("ampola de Vater",         "ampola hepatopancreática",
     "digestório"),
    ("esfíncter de Oddi",       "esfíncter da ampola hepatopancreática",
     "digestório"),
    ("ilhotas de Langerhans",   "ilhotas pancreáticas",
     "digestório"),
    ("válvula de Bauhin",       "valva ileocecal",
     "digestório"),
    ("ligamento de Treitz",     "músculo suspensor do duodeno",
     "digestório"),
    ("forame de Winslow",       "forame omental",
     "digestório"),
    ("válvulas de Houston",     "pregas transversas do reto",
     "digestório"),

    # ── Sistema cardiovascular ──
    ("nó de Keith-Flack",       "nó sinoatrial",
     "cardiovascular"),
    ("nó de Aschoff-Tawara",    "nó atrioventricular",
     "cardiovascular"),
    ("feixe de His",            "fascículo atrioventricular",
     "cardiovascular"),
    ("canal de Botallo",        "ligamento arterial",
     "cardiovascular"),
    ("cisterna de Pecquet",     "cisterna do quilo",
     "cardiovascular"),

    # ── Sistema locomotor e tegumentar ──
    ("ligamento de Poupart",    "ligamento inguinal",
     "locomotor"),
    ("tendão de Aquiles",       "tendão do calcâneo",
     "locomotor"),
    ("canal de Havers",         "canal central do ósteon",
     "locomotor"),
    ("ligamentos de Cooper",    "ligamentos suspensores da mama",
     "locomotor"),
    ("ângulo de Louis",         "ângulo do esterno",
     "locomotor"),
    ("linha de Douglas",        "linha arqueada",
     "locomotor"),
    ("ossos de Wormian",        "ossos suturais",
     "locomotor"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _frase(t) -> str:
    s = " ".join(str(t).split())
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return s if s[-1] in ".!?" else s + "."


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str):
    """Monta a questão com cinco alternativas embaralhadas."""
    unicos = []
    for d in distratores:
        if d != correta and d not in unicos:
            unicos.append(d)
    if len(unicos) < 4:
        return None

    # A POSIÇÃO da resposta certa é sorteada, não deixada ao acaso da
    # ordem em que o template escreveu os distratores. Sem isto, o
    # valor certo cai no meio das cinco questão após questão — ver
    # equilibrio_numerico.py.
    unicos = _EQ.escolher(correta, unicos, rng,
                          chave=lambda d: _EQ.valor_de(formatador(d)))
    valores = [correta] + unicos[:4]
    rng.shuffle(valores)

    alternativas = {L: formatador(v) for L, v in zip(LETRAS, valores)}
    if len(set(alternativas.values())) < 5:
        return None

    gabarito = next(L for L, v in zip(LETRAS, valores) if v == correta)
    return {
        "enunciado":         enunciado,
        "alternativas":      alternativas,
        "gabarito":          gabarito,
        "explicacao":        explicacao,
        "topico":            topico,
        "tem_elemento_visual": False,
    }


# ══════════════════════════════════════════════════════════
#  TEMPLATES — NERVOS CRANIANOS
# ══════════════════════════════════════════════════════════

def _nome_no_texto(nome: str, texto: str) -> bool:
    """A resposta repete o nome do nervo que o enunciado já deu?"""
    return nome.lower().rstrip("o").rstrip("a") in texto.lower()


def gerar_nervo_funcao(rng):
    """Qual a função de determinado par craniano?"""
    # O olfatório fica de fora: sua função é "condução dos impulsos
    # OLFATÓRIOS", e o enunciado nomeia o nervo. Quem nunca estudou
    # acerta repetindo a palavra — mesmo caso do hipoglosso no template
    # de abertura do crânio. Ele continua nos templates de número, de
    # tipo e de componente funcional.
    candidatos = [n for n in NERVOS_CRANIANOS
                  if not _nome_no_texto(n[2], n[4])]
    romano, num, nome, tipo, funcao, saida, _ = rng.choice(candidatos)

    CENARIOS = [
        f"Considere o {romano} par de nervos cranianos, o nervo {nome}.",
        f"Durante o exame neurológico, avalia-se o nervo {nome} ({romano} par).",
        f"O nervo {nome} corresponde ao {romano} par craniano.",
        f"Em uma aula de neuroanatomia, estuda-se o {romano} par craniano.",
        f"Um estudante revisa as funções do nervo {nome}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função principal.",
        "Qual é a função desse nervo?",
        "Sua função principal é:",
        "Assinale a alternativa que descreve corretamente sua função.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [n[4] for n in NERVOS_CRANIANOS if n[4] != funcao]
    rng.shuffle(distratores)

    explicacao = (
        f"O {romano} par craniano é o nervo {nome}, de natureza {tipo}, "
        f"responsável pela {funcao}. Sua saída do crânio ocorre pelo "
        f"{saida}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Neuroanatomia (nervos cranianos)", rng)
    if q:
        q["_fato"] = f"nervo:{romano}"
    return q


def gerar_nervo_tipo(rng):
    """O nervo é sensitivo, motor ou misto?"""
    romano, num, nome, tipo, funcao, _, _ = rng.choice(NERVOS_CRANIANOS)

    CENARIOS = [
        f"Quanto ao componente funcional, o nervo {nome} ({romano} par)",
        f"Na classificação funcional dos nervos cranianos, o nervo {nome}",
        f"O {romano} par craniano, denominado nervo {nome},",
        f"Considerando a natureza de suas fibras, o nervo {nome}",
    ]
    COMANDOS = [
        "é classificado como:",
        "corresponde a um nervo:",
        "é um nervo do tipo:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # As três respostas reais são palavras únicas de tamanhos diferentes
    # — "motor" com 5 caracteres, "sensitivo" com 9 —, enquanto os
    # distratores inventados chegavam a 58. O gabarito ficava sempre
    # entre os menores, e a estratégia "marque a mais curta" acertava
    # metade das vezes.
    #
    # Qualificar TODAS as opções com a mesma estrutura desfaz a
    # correlação entre tamanho e resposta.
    QUALIFICADO = {
        "sensitivo": "exclusivamente sensitivo",
        "motor":     "exclusivamente motor",
        "misto":     "misto, com fibras sensitivas e motoras",
    }
    correta = QUALIFICADO[tipo]
    distratores = [v for k, v in QUALIFICADO.items() if k != tipo]
    distratores += [
        "exclusivamente vasomotor",
        "misto, com fibras motoras e proprioceptivas",
        "exclusivamente secretomotor",
        "misto, com fibras sensitivas e vasomotoras",
    ]

    explicacao = (
        f"O nervo {nome} ({romano} par) é {tipo}, pois é responsável pela "
        f"{funcao}."
    )
    if tipo == "misto":
        explicacao += (" Nervo misto é aquele que conduz tanto fibras "
                       "sensitivas quanto motoras.")
    q = _montar(enunciado, correta, distratores, explicacao,
                "Neuroanatomia (nervos cranianos)", rng)
    if q:
        q["_fato"] = f"nervo:{romano}"
    return q


def gerar_nervo_numero(rng):
    """Qual o número de determinado nervo, ou qual nervo tem tal número?"""
    romano, num, nome, tipo, funcao, _, _ = rng.choice(NERVOS_CRANIANOS)
    modo = rng.choice(["pelo_nome", "pelo_numero"])

    if modo == "pelo_nome":
        CENARIOS = [
            f"O nervo {nome} é responsável pela {funcao}.",
            f"Entre os doze pares cranianos encontra-se o nervo {nome}.",
            f"Um estudante identifica, em uma peça anatômica, o nervo {nome}.",
        ]
        COMANDOS = [
            "Esse nervo corresponde a qual par craniano?",
            "Assinale a alternativa que indica seu número de ordem.",
            "Trata-se do par craniano de número:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = romano
        distratores = [n[0] for n in NERVOS_CRANIANOS if n[0] != romano]
    else:
        # Cenário e comando precisam concordar sintaticamente. Antes,
        # "...identificação do X par craniano." + "corresponde a qual
        # nervo?" produzia frase sem sujeito.
        #
        # Cada cenário termina em PONTO, e todos os comandos são orações
        # completas.
        CENARIOS = [
            f"Considere o {romano} par de nervos cranianos.",
            f"Os nervos cranianos são numerados em sequência craniocaudal, "
            f"e o {romano} par ocupa a posição correspondente.",
            f"Em uma prova de neuroanatomia, pede-se a identificação do "
            f"{romano} par craniano.",
            f"Durante a revisão dos pares cranianos, chega-se ao "
            f"{romano} par.",
        ]
        COMANDOS = [
            "Assinale a alternativa que apresenta seu nome.",
            "A qual nervo esse par corresponde?",
            "Esse par corresponde ao nervo:",
            "Assinale a alternativa que o identifica corretamente.",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = f"nervo {nome}"
        distratores = [f"nervo {n[2]}" for n in NERVOS_CRANIANOS if n[2] != nome]

    rng.shuffle(distratores)
    explicacao = (
        f"O {romano} par craniano é o nervo {nome}, de natureza {tipo}, "
        f"responsável pela {funcao}. A numeração dos pares cranianos segue "
        f"a ordem craniocaudal de emergência no sistema nervoso."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Neuroanatomia (nervos cranianos)", rng)
    if q:
        q["_fato"] = f"nervo:{romano}"
    return q


def gerar_nervo_saida(rng):
    """Por onde o nervo deixa o crânio?"""
    # O trigêmeo tem três saídas, o que tornaria a alternativa longa e
    # destoante — fica fora deste template.
    #
    # Fora também os nervos cuja abertura LEVA O NOME DELES: o hipoglosso
    # sai pelo canal do hipoglosso e o óptico, pelo canal óptico. Quem
    # nunca abriu um atlas acerta essas duas só repetindo a palavra do
    # enunciado, e a questão não mede nada. Os dois continuam nos demais
    # templates — número, nome, função e componente.
    candidatos = [n for n in NERVOS_CRANIANOS
                  if n[2] != "trigêmeo" and not _nome_no_texto(n[2], n[5])]
    romano, num, nome, tipo, funcao, saida, _ = rng.choice(candidatos)

    CENARIOS = [
        f"O nervo {nome} ({romano} par) deixa a cavidade craniana",
        f"Em um estudo de osteologia do crânio, acompanha-se o trajeto do "
        f"nervo {nome}, que sai",
        f"Durante a dissecção da base do crânio, identifica-se a passagem "
        f"do nervo {nome}",
    ]
    COMANDOS = [
        "por qual estrutura?",
        "pela seguinte abertura:",
        "através de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # Um distrator que CONTÉM a resposta certa torna a questão ambígua:
    # "meato acústico interno" está dentro de "meato acústico interno,
    # com saída pelo forame estilomastóideo". A verificação vale entre
    # TODAS as alternativas, não só contra o gabarito.
    def _sobrepoe(a, b):
        return a.lower() in b.lower() or b.lower() in a.lower()

    correta = saida
    candidatos_d = [n[5] for n in candidatos if n[5] != saida]
    candidatos_d += ["forame magno", "forame espinhoso", "canal carótico",
                     "forame lacerado", "canal condilar"]
    rng.shuffle(candidatos_d)

    distratores = []
    for cand in candidatos_d:
        if _sobrepoe(cand, correta):
            continue
        if any(_sobrepoe(cand, d) for d in distratores):
            continue
        distratores.append(cand)

    explicacao = f"O nervo {nome} ({romano} par) deixa o crânio pelo {saida}. "
    if saida == "forame jugular":
        explicacao += ("Convém lembrar que TRÊS nervos passam pelo forame "
                       "jugular: glossofaríngeo (IX), vago (X) e acessório (XI).")
    elif saida == "fissura orbital superior":
        explicacao += ("Pela fissura orbital superior passam o oculomotor "
                       "(III), o troclear (IV), o abducente (VI) e o ramo "
                       "oftálmico do trigêmeo (V1).")
    elif saida == "meato acústico interno":
        explicacao += ("Pelo meato acústico interno passam o facial (VII) e "
                       "o vestibulococlear (VIII).")
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Neuroanatomia (base do crânio)", rng)
    if q:
        q["_fato"] = f"nervo:{romano}"
    return q


def gerar_nervo_parassimpatico(rng):
    """Quais pares cranianos têm componente parassimpático?"""
    com = [n for n in NERVOS_CRANIANOS if n[6]]
    sem = [n for n in NERVOS_CRANIANOS if not n[6]]
    tem = rng.choice([True, False])

    if tem:
        alvo = rng.choice(com)
        outros = sem
        palavra = "possui"
    else:
        alvo = rng.choice(sem)
        outros = com
        palavra = "não possui"

    # O espaço deste template é pequeno por natureza: 4 nervos com
    # componente parassimpático e 8 sem. A variação vem dos cenários e
    # comandos — com apenas 3 e 2, o template rendia 12 enunciados.
    CENARIOS = [
        "Apenas quatro pares cranianos conduzem fibras parassimpáticas "
        "pré-ganglionares.",
        "Entre os doze pares cranianos, alguns integram a porção craniana "
        "do sistema nervoso autônomo.",
        "O componente parassimpático dos nervos cranianos está restrito a "
        "alguns pares.",
        "A porção craniana da divisão parassimpática do sistema nervoso "
        "autônomo é veiculada por poucos pares cranianos.",
        "Nem todos os nervos cranianos conduzem fibras autônomas.",
        "Em uma aula de neuroanatomia, discute-se quais pares cranianos "
        "participam do sistema nervoso autônomo.",
        "Um estudante revisa a distribuição das fibras parassimpáticas "
        "entre os pares cranianos.",
        "A inervação parassimpática da cabeça e do pescoço depende de "
        "pares cranianos específicos.",
    ]
    COMANDOS = [
        f"Assinale a alternativa que apresenta um nervo que {palavra} "
        f"componente parassimpático.",
        f"Qual dos nervos abaixo {palavra} fibras parassimpáticas?",
        f"Entre os nervos listados, qual {palavra} esse componente?",
        f"Assinale a alternativa que indica um nervo que {palavra} fibras "
        f"parassimpáticas pré-ganglionares.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = f"nervo {alvo[2]} ({alvo[0]} par)"
    distratores = [f"nervo {n[2]} ({n[0]} par)" for n in outros]
    rng.shuffle(distratores)

    lista = ", ".join(f"{n[2]} ({n[0]})" for n in com)
    explicacao = (
        f"Os pares cranianos com componente parassimpático são quatro: "
        f"{lista}. Portanto, o nervo {alvo[2]} ({alvo[0]} par) {palavra} "
        f"esse componente."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Neuroanatomia (sistema autônomo)", rng)
    if q:
        q["_fato"] = f"parassimp:{alvo[0]}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — TERMINOLOGIA ANATÔMICA
# ══════════════════════════════════════════════════════════

def gerar_eponimo_termo(rng):
    """
    Qual o termo oficial que substituiu determinado epônimo?

    A Terminologia Anatômica aboliu os nomes de pessoas. O aluno de
    primeiro ano precisa fazer essa conversão, e o erro comum é achar
    que o epônimo continua válido.
    """
    eponimo, oficial, sistema = rng.choice(EPONIMOS)

    CENARIOS = [
        f"A Terminologia Anatômica aboliu os epônimos, substituindo nomes "
        f"de pessoas por termos que indicam forma, posição ou função. "
        f"O epônimo \"{eponimo}\" foi substituído.",
        f"Em textos antigos encontra-se a expressão \"{eponimo}\", hoje "
        f"em desuso.",
        f"Um estudante lê, em uma obra da década de 1950, a menção a "
        f"\"{eponimo}\".",
        f"A estrutura anteriormente designada como \"{eponimo}\" recebeu "
        f"nova denominação na Terminologia Anatômica.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta o termo oficial correspondente.",
        "Qual o termo atualmente aceito?",
        "O termo oficial correspondente é:",
        "Assinale a alternativa com a denominação vigente.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # "ducto pancreático" e "ducto pancreático acessório" são
    # estruturas distintas, mas um nome contém o outro — a alternativa
    # mais curta parece abranger a mais longa, e a questão fica ambígua.
    def _sobrepoe(a, b):
        return a.lower() in b.lower() or b.lower() in a.lower()

    correta = oficial
    # Os distratores vêm do MESMO sistema quando há quantidade para
    # isso. Termo oficial de outro aparelho se descarta por eliminação
    # temática; dentro do mesmo sistema, é preciso saber o epônimo.
    _mesmo = [o for _, o, sis in EPONIMOS if o != oficial and sis == sistema]
    _outros = [o for _, o, sis in EPONIMOS if o != oficial and sis != sistema]
    rng.shuffle(_mesmo)
    rng.shuffle(_outros)
    candidatos_d = _mesmo + _outros
    distratores = []
    for cand in candidatos_d:
        if _sobrepoe(cand, correta):
            continue
        if any(_sobrepoe(cand, d) for d in distratores):
            continue
        distratores.append(cand)

    explicacao = (
        f"O termo oficial é \"{oficial}\". A Terminologia Anatômica, "
        f"publicada pelo Federative Committee on Anatomical Terminology e "
        f"traduzida pela Sociedade Brasileira de Anatomia, aboliu os "
        f"epônimos: o nome da estrutura deve indicar sua forma, posição, "
        f"função ou uma combinação desses critérios, e não homenagear uma "
        f"pessoa."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                f"Terminologia Anatômica ({sistema})", rng)
    if q:
        # Identifica o PAR usado, não a direção. Permite ao gerar_lote
        # evitar que o mesmo par apareça nos dois sentidos no mesmo lote:
        # quem responde "Malpighi → corpúsculo renal" já sabe a inversa.
        q["_fato"] = f"eponimo:{oficial}"
    return q


def gerar_termo_eponimo(rng):
    """Caminho inverso: qual epônimo corresponde ao termo oficial?"""
    eponimo, oficial, sistema = rng.choice(EPONIMOS)

    CENARIOS = [
        f"A estrutura denominada \"{oficial}\" pela Terminologia "
        f"Anatômica era anteriormente conhecida por um epônimo.",
        f"O termo oficial \"{oficial}\" substituiu uma denominação que "
        f"homenageava um anatomista.",
        f"Ao consultar literatura antiga sobre a estrutura hoje chamada "
        f"\"{oficial}\", encontra-se outra denominação.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta esse epônimo.",
        "Qual era essa denominação?",
        "O epônimo correspondente é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    def _sobrepoe_ep(a, b):
        return a.lower() in b.lower() or b.lower() in a.lower()

    correta = eponimo
    _mesmo = [e for e, _, sis in EPONIMOS if e != eponimo and sis == sistema]
    _outros = [e for e, _, sis in EPONIMOS if e != eponimo and sis != sistema]
    rng.shuffle(_mesmo)
    rng.shuffle(_outros)
    candidatos_e = _mesmo + _outros
    distratores = []
    for cand in candidatos_e:
        if _sobrepoe_ep(cand, correta):
            continue
        if any(_sobrepoe_ep(cand, d) for d in distratores):
            continue
        distratores.append(cand)

    explicacao = (
        f"O epônimo correspondente é \"{eponimo}\". A Terminologia "
        f"Anatômica substituiu essa designação por \"{oficial}\", em "
        f"consonância com o princípio de que o termo deve descrever a "
        f"estrutura, não homenagear uma pessoa."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                f"Terminologia Anatômica ({sistema})", rng)
    if q:
        q["_fato"] = f"eponimo:{oficial}"     # mesmo par, direção inversa
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_ANATOMIA = {
    "nervo_funcao":         gerar_nervo_funcao,
    "nervo_tipo":           gerar_nervo_tipo,
    "nervo_numero":         gerar_nervo_numero,
    "nervo_saida":          gerar_nervo_saida,
    "nervo_parassimpatico": gerar_nervo_parassimpatico,
    "eponimo_termo":        gerar_eponimo_termo,
    "termo_eponimo":        gerar_termo_eponimo,
}

TOPICOS_ANATOMIA = {
    "neuroanatomia": [
        "nervo_funcao",
        "nervo_tipo",
        "nervo_numero",
        "nervo_saida",
        "nervo_parassimpatico",
    ],
    "terminologia": [
        "eponimo_termo",
        "termo_eponimo",
    ],
}

# As chaves incluem SINGULAR e PLURAL. O casamento é por palavra
# inteira, então "nervo craniano" não encontra "nervos cranianos" — e o
# índice de um livro costuma usar o plural.
PALAVRAS_CHAVE = {
    "nervo_funcao":         ["nervo craniano", "nervos cranianos",
                             "par craniano", "pares cranianos", "trigemeo",
                             "hipoglosso", "oculomotor", "glossofaringeo",
                             "vestibulococlear", "abducente", "troclear"],
    "nervo_tipo":           ["nervo craniano", "nervos cranianos",
                             "par craniano", "pares cranianos",
                             "componente funcional", "nervo misto"],
    "nervo_numero":         ["nervo craniano", "nervos cranianos",
                             "par craniano", "pares cranianos",
                             "neuroanatomia"],
    "nervo_saida":          ["forame jugular", "fissura orbital",
                             "base do cranio", "meato acustico",
                             "forame oval", "forame redondo", "canal optico",
                             "nervos cranianos", "nervo craniano"],
    "nervo_parassimpatico": ["parassimpatico", "sistema autonomo",
                             "nervo craniano", "nervos cranianos"],
    "eponimo_termo":        ["terminologia anatomica", "eponimo", "eponimos",
                             "nomina anatomica", "nomenclatura anatomica"],
    "termo_eponimo":        ["terminologia anatomica", "eponimo", "eponimos",
                             "nomenclatura anatomica"],
}

# Termos que existem fora da anatomia e não devem acionar o gerador
CHAVES_GENERICAS = {
    "nervo", "funcao", "tipo", "numero", "saida", "estrutura",
    "sistema", "componente", "termo", "nome",
}


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def templates_para_topicos(topicos):
    """Quais templates casam com os tópicos de um livro?"""
    texto = " " + " ".join(_normalizar(t) for t in (topicos or [])) + " "
    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        for chave in chaves:
            cn = _normalizar(chave)
            if cn in CHAVES_GENERICAS:
                continue
            if re.search(r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])',
                         texto):
                achados.append(nome)
                break
    return achados


def gerar_lote(quantidade: int = 10, seed: int = None,
               topico: str = None, templates: list = None):
    """Gera um lote de questões de anatomia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_ANATOMIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_ANATOMIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_ANATOMIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave] if t in TEMPLATES_ANATOMIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Quantos FATOS distintos cada template consegue explorar. O rodízio
    # simples distribuía por template, mas o material é desigual: cinco
    # templates dividem 12 nervos, enquanto dois dividem 41 epônimos.
    # Num lote grande, os de nervo esgotavam e repetiam enquanto os
    # epônimos sobravam.
    LASTRO = {
        "nervo_funcao":         len(NERVOS_CRANIANOS),
        "nervo_tipo":           len(NERVOS_CRANIANOS),
        "nervo_numero":         len(NERVOS_CRANIANOS),
        "nervo_saida":          len(NERVOS_CRANIANOS) - 1,   # sem o trigêmeo
        "nervo_parassimpatico": len(NERVOS_CRANIANOS),
        "eponimo_termo":        len(EPONIMOS),
        "termo_eponimo":        len(EPONIMOS),
    }

    questoes, tentativas, limite = [], 0, quantidade * 12
    vistos, fatos_usados = set(), set()

    # Ordem de sorteio proporcional ao material: um template com 41 fatos
    # aparece mais que um com 12, e o lote esgota os dois ao mesmo tempo.
    # A fila precisa ser INTERCALADA, não agrupada: estender com
    # [nome] * peso coloca as repetições lado a lado, e um lote pequeno
    # consome só os primeiros templates da lista, sem alcançar os de
    # maior lastro. As rodadas se alternam.
    pesos = {n: max(1, min(round(LASTRO.get(n, 10) / 12), 5))
             for n in disponiveis}
    fila = []
    for rodada in range(max(pesos.values())):
        for nome in disponiveis:
            if pesos[nome] > rodada:
                fila.append(nome)
    if not fila:
        fila = list(disponiveis)

    # A posição na fila avança a cada TENTATIVA, não a cada questão
    # aceita. Com len(questoes), o laço ficava preso na posição de um
    # template cujas questões estavam todas vetadas, até esgotar as
    # tentativas — e então o veto afrouxava e todas entravam de uma vez.
    posicao = 0
    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = fila[posicao % len(fila)]
        posicao += 1
        q = TEMPLATES_ANATOMIA[nome](rng)
        if not q:
            continue

        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        # Um mesmo FATO não deve render duas questões no lote, mesmo em
        # direções opostas: quem responde "corpúsculo de Malpighi → ?"
        # já sabe "? ← corpúsculo renal". São a mesma informação.
        #
        # A restrição afrouxa perto do limite de tentativas, porque com
        # poucos fatos disponíveis é melhor alguma repetição que lote
        # incompleto.
        fato = q.get("_fato")
        if fato and fato in fatos_usados and tentativas < limite * 0.7:
            continue

        vistos.add(q["enunciado"])
        if fato:
            fatos_usados.add(fato)
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade: int = 10, seed: int = None,
                   topico: str = None, templates: list = None):
    """Devolve (questoes, gabarito) no formato que a API espera."""
    lote = gerar_lote(quantidade, seed=seed, topico=topico, templates=templates)
    questoes, gabarito = [], []
    for q in lote:
        questoes.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": q["tem_elemento_visual"],
        })
        gabarito.append({
            "numero":           q["numero"],
            "resposta_correta": q["gabarito"],
            "explicacao":       q["explicacao"],
            "topico":           q["topico"],
            "_fato":            q.get("_fato", ""),
        })
    return questoes, gabarito


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    print("═" * 64)
    print("  GERADOR DE ANATOMIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
