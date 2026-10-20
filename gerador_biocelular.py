"""
=============================================================
  GERADOR DE BIOLOGIA CELULAR
=============================================================
  Questões de biologia celular geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Organelas, funções e particularidades
    ✅ Membrana plasmática e tipos de transporte
    ✅ Ciclo celular
    ❌ Identificação em microscopia (depende de imagem)

  VERIFICAÇÃO DAS FONTES

  Registradas em biocelular/_fontes.md, incluindo um erro:
  uma fonte universitária atribui ao retículo RUGOSO a
  síntese de esteroides — função do retículo LISO.

  USO:
      from gerador_biocelular import gerar_lote, gerar_para_api
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

# ── Organelas ──
#
# Fontes: Toda Matéria; Manual do Enem; Kenhub; Junqueira & Carneiro,
# Biologia Celular e Molecular; Alberts, Biologia Molecular da Célula.
#
# (organela, com_artigo, função, particularidade)
ORGANELAS = [
    ("núcleo", "o núcleo",
     "abrigar o DNA e comandar a transcrição gênica",
     "é delimitado por um envoltório com poros, que controlam a passagem "
     "de moléculas"),

    # A particularidade anterior era "é a única estrutura da lista que não
    # possui membrana". O CENTRÍOLO também não tem membrana, e está entre
    # os distratores: a questão nascia com duas respostas certas. A
    # ressalva "da lista" não resolvia, porque a lista é justamente o
    # conjunto de alternativas.
    #
    # A montagem no nucléolo é exclusiva do ribossomo e não ecoa o nome
    # dele — dizer "RNA ribossômico" entregaria a resposta a quem não
    # sabe o conteúdo.
    ("ribossomo", "o ribossomo",
     "realizar a síntese proteica",
     "não é delimitado por membrana e tem suas duas subunidades "
     "montadas no nucléolo"),

    ("retículo endoplasmático rugoso",
     "o retículo endoplasmático rugoso",
     "sintetizar proteínas destinadas à exportação ou à membrana",
     "tem ribossomos aderidos à face citosólica, o que lhe dá o aspecto "
     "granuloso"),

    ("retículo endoplasmático liso",
     "o retículo endoplasmático liso",
     "sintetizar lipídios e esteroides, além de participar da "
     "detoxificação",
     "armazena cálcio na célula muscular, onde recebe o nome de "
     "retículo sarcoplasmático"),

    ("complexo de Golgi", "o complexo de Golgi",
     "modificar, empacotar e endereçar as proteínas recebidas do "
     "retículo",
     "é a organela que origina os lisossomos"),

    ("lisossomo", "o lisossomo",
     "realizar a digestão intracelular",
     "contém enzimas hidrolíticas que funcionam em pH ácido"),

    ("peroxissomo", "o peroxissomo",
     "degradar o peróxido de hidrogênio por meio da catalase",
     # A redação anterior terminava em "e não deve ser confundido com o
     # lisossomo": um aviso ao leitor que, dentro do enunciado, eliminava
     # uma alternativa de graça. E o "também" não tinha antecedente.
     "realiza a beta-oxidação dos ácidos graxos de cadeia muito longa"),

    ("mitocôndria", "a mitocôndria",
     "produzir ATP pela fosforilação oxidativa",
     "possui DNA próprio, de herança materna, e é delimitada por dupla "
     "membrana"),

    ("centríolo", "o centríolo",
     "organizar o fuso mitótico durante a divisão celular",
     "está presente nas células animais e ausente na maioria das "
     "vegetais"),
]

# ── Transporte através da membrana ──
#
# (tipo, com_artigo, gasto de ATP, sentido, exemplos)
TRANSPORTES = [
    ("difusão simples", "a difusão simples", "não consome ATP",
     "a favor do gradiente de concentração",
     "a passagem de oxigênio, gás carbônico e moléculas lipossolúveis"),
    ("difusão facilitada", "a difusão facilitada", "não consome ATP",
     "a favor do gradiente de concentração",
     "a entrada de glicose pelos transportadores GLUT"),
    ("osmose", "a osmose", "não consome ATP",
     "a favor do gradiente de água",
     "a passagem de água pelas aquaporinas"),
    ("transporte ativo", "o transporte ativo", "consome ATP",
     "contra o gradiente de concentração",
     "o funcionamento da bomba de sódio e potássio"),
]

# ── Ciclo celular ──
#
# (ordem, fase, com_artigo, o que acontece)
CICLO_CELULAR = [
    (1, "G1", "a fase G1",
     "crescimento celular e intensa síntese de proteínas"),
    (2, "S", "a fase S",
     "duplicação do DNA, com formação das cromátides-irmãs"),
    (3, "G2", "a fase G2",
     "preparação final para a divisão, com checagem do DNA duplicado"),
    (4, "mitose", "a mitose",
     "divisão propriamente dita, em prófase, metáfase, anáfase e "
     "telófase"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _com_preposicao(prep: str, sintagma: str) -> str:
    """Junta preposição e sintagma fazendo a CONTRAÇÃO."""
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "): "à ", ("a", "o "): "ao ",
        ("de", "a "): "da ", ("de", "o "): "do ",
        ("em", "a "): "na ", ("em", "o "): "no ",
        ("por", "a "): "pela ", ("por", "o "): "pelo ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


def _inicial_maiuscula(t: str) -> str:
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str):
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
#  TEMPLATES — ORGANELAS
# ══════════════════════════════════════════════════════════

def gerar_funcao_por_organela(rng):
    """Qual a função de determinada organela?"""
    org, art, funcao, particular = rng.choice(ORGANELAS)

    CENARIOS = [
        f"Considere {art} no contexto do funcionamento celular.",
        # Não "do citoplasma": o NÚCLEO está na lista de organelas, e
        # dizer que ele é uma estrutura citoplasmática é erro de
        # conteúdo dentro do próprio enunciado.
        f"Entre os componentes da célula encontra-se {art}.",
        f"Um estudante revisa o papel {_com_preposicao('de', art)} na "
        f"célula.",
        f"Uma micrografia eletrônica evidencia {art}.",
        f"A compartimentalização celular inclui {art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função principal.",
        "Sua função principal é:",
        "Qual a função dessa estrutura?",
        "Assinale a alternativa que descreve corretamente sua função.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [o[2] for o in ORGANELAS if o[2] != funcao]
    rng.shuffle(distratores)

    explicacao = (
        f"A função {_com_preposicao('de', art)} é {funcao}. Convém "
        f"lembrar que {particular}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Biologia celular (organelas)", rng)
    if q:
        q["_fato"] = f"organela:{org}"
    return q


def gerar_organela_por_funcao(rng):
    """Qual organela desempenha determinada função?"""
    org, art, funcao, particular = rng.choice(ORGANELAS)

    CENARIOS = [
        f"Certa estrutura celular tem como função {funcao}.",
        f"Em uma célula, a seguinte função é desempenhada por uma "
        f"estrutura específica: {funcao}.",
        f"Um processo celular essencial consiste em {funcao}.",
        f"A célula depende de uma estrutura especializada para {funcao}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que a identifica.",
        "Trata-se do:",
        "Essa função cabe ao:",
        "Qual estrutura desempenha essa função?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = org
    distratores = [o[0] for o in ORGANELAS if o[0] != org]
    rng.shuffle(distratores)

    explicacao = (
        f"Trata-se {_com_preposicao('de', art)}, cuja função é {funcao}. "
        f"Vale notar que {particular}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Biologia celular (organelas)", rng)
    if q:
        q["_fato"] = f"organela:{org}"
    return q


def gerar_particularidade_organela(rng):
    """Qual organela tem determinada característica distintiva?"""
    org, art, funcao, particular = rng.choice(ORGANELAS)

    # As particularidades foram escritas com o gênero da ORGANELA ("é
    # delimitado por um envoltório"), então o cenário não pode
    # introduzi-las com "estrutura", que é feminino — saía "Certa
    # estrutura celular... é delimitado".
    #
    # Aqui o sintagma que antecede é neutro ou concorda com a organela.
    CENARIOS = [
        f"Um componente celular apresenta a seguinte particularidade: "
        f"{particular}.",
        f"Entre as organelas, há uma da qual se diz o seguinte: "
        f"{particular}.",
        f"Ao comparar os componentes da célula, registra-se o seguinte "
        f"sobre um deles: {particular}.",
        f"A respeito de certo componente celular, afirma-se: "
        f"{particular}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que a identifica.",
        "Trata-se do:",
        "Essa estrutura é o:",
        "Qual estrutura apresenta essa característica?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = org
    distratores = [o[0] for o in ORGANELAS if o[0] != org]
    rng.shuffle(distratores)

    explicacao = (
        f"Trata-se {_com_preposicao('de', art)}: {particular}. Sua "
        f"função principal é {funcao}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Biologia celular (organelas)", rng)
    if q:
        q["_fato"] = f"organela:{org}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — TRANSPORTE PELA MEMBRANA
# ══════════════════════════════════════════════════════════

def gerar_transporte_classificacao(rng):
    """
    O transporte é ativo ou passivo, e por quê?

    O ponto que a prova cobra é que a difusão FACILITADA usa proteína
    e ainda assim é passiva — o critério é o sentido em relação ao
    gradiente, não a presença de transportador.
    """
    tipo, art, atp, sentido, exemplos = rng.choice(TRANSPORTES)

    CENARIOS = [
        f"Considere {art} através da membrana plasmática.",
        f"Entre os mecanismos de transporte pela membrana encontra-se "
        f"{art}.",
        f"Um estudante revisa as características {_com_preposicao('de', art)}.",
        f"A membrana plasmática permite {art}.",
    ]
    # Sem pronome: o referente é o tipo de transporte, e o gênero varia
    # — "a osmose" contra "o transporte ativo". "que O caracteriza"
    # quebra num, "que A caracteriza" quebra no outro.
    COMANDOS = [
        "Quanto ao consumo de energia e ao sentido, esse mecanismo:",
        "Assinale a alternativa que caracteriza esse mecanismo.",
        "Esse mecanismo caracteriza-se por:",
        "Assinale a alternativa correta quanto a esse mecanismo.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = f"{atp} e ocorre {sentido}"
    distratores = []
    for t in TRANSPORTES:
        cand = f"{t[2]} e ocorre {t[3]}"
        if cand != correta:
            distratores.append(cand)
    # Combinações impossíveis, mas plausíveis para quem não estudou
    distratores += [
        "não consome ATP e ocorre contra o gradiente de concentração",
        "consome ATP e ocorre a favor do gradiente de concentração",
    ]

    explicacao = (
        f"{_inicial_maiuscula(art)} {atp} e ocorre {sentido}. "
        f"São exemplos: {exemplos}. "
    )
    if tipo == "difusão facilitada":
        explicacao += (
            "Convém notar que a difusão facilitada usa proteína "
            "transportadora e ainda assim é PASSIVA — o que define o "
            "transporte ativo é o sentido contrário ao gradiente, não a "
            "presença de proteína."
        )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Biologia celular (transporte pela membrana)", rng)
    if q:
        q["_fato"] = f"transporte:{tipo}"
    return q


def gerar_transporte_exemplo(rng):
    """Que tipo de transporte corresponde a determinado exemplo?"""
    tipo, art, atp, sentido, exemplos = rng.choice(TRANSPORTES)

    CENARIOS = [
        f"Considere o seguinte processo celular: {exemplos}.",
        f"Em uma célula, ocorre o seguinte: {exemplos}.",
        f"Um experimento acompanha o seguinte fenômeno de membrana: "
        f"{exemplos}.",
        f"A membrana plasmática viabiliza o seguinte processo: "
        f"{exemplos}.",
    ]
    COMANDOS = [
        "Esse processo corresponde a:",
        "Assinale a alternativa que o classifica.",
        "Trata-se de:",
        "Qual mecanismo de transporte está envolvido?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = tipo
    distratores = [t[0] for t in TRANSPORTES if t[0] != tipo]
    distratores += ["endocitose mediada por receptor", "exocitose",
                    "pinocitose"]

    explicacao = (
        f"Trata-se {_com_preposicao('de', art)}: {atp} e ocorre "
        f"{sentido}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Biologia celular (transporte pela membrana)", rng)
    if q:
        q["_fato"] = f"transporte:{tipo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — CICLO CELULAR
# ══════════════════════════════════════════════════════════

def gerar_fase_ciclo(rng):
    """O que acontece em determinada fase do ciclo celular?"""
    ordem, fase, art, evento = rng.choice(CICLO_CELULAR)
    modo = rng.choice(["fase_para_evento", "evento_para_fase"])

    if modo == "fase_para_evento":
        CENARIOS = [
            f"Considere {art} do ciclo celular.",
            f"O ciclo celular compreende etapas sucessivas. Considere "
            f"{art}.",
            f"Um estudante revisa o que ocorre "
            f"{_com_preposicao('em', art)}.",
            f"Entre as etapas do ciclo celular encontra-se {art}.",
        ]
        COMANDOS = [
            "Nessa etapa ocorre:",
            "Assinale a alternativa que descreve o que acontece nela.",
            "O evento característico dessa etapa é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = evento
        distratores = [c[3] for c in CICLO_CELULAR if c[3] != evento]
        distratores += [
            "separação das cromátides-irmãs para os polos opostos",
            "condensação inicial da cromatina em cromossomos visíveis",
        ]
    else:
        CENARIOS = [
            f"Durante o ciclo celular ocorre o seguinte evento: {evento}.",
            f"Certa etapa do ciclo celular caracteriza-se por {evento}.",
            f"Um evento do ciclo celular consiste em {evento}.",
        ]
        COMANDOS = [
            "Esse evento ocorre em:",
            "Assinale a alternativa que indica a etapa correspondente.",
            "Trata-se de qual etapa?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = fase
        distratores = [c[1] for c in CICLO_CELULAR if c[1] != fase]
        distratores += ["G0", "citocinese", "meiose I"]

    explicacao = (
        f"{_inicial_maiuscula(art)} caracteriza-se por {evento}. "
    )
    if fase == "S":
        explicacao += (
            "Convém lembrar que a duplicação do DNA ocorre na INTÉRFASE, "
            "não na mitose — quando a célula entra em mitose, o material "
            "genético já está duplicado."
        )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Biologia celular (ciclo celular)", rng)
    if q:
        q["_fato"] = f"ciclo:{fase}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_BIOCELULAR = {
    "funcao_por_organela":  gerar_funcao_por_organela,
    "organela_por_funcao":  gerar_organela_por_funcao,
    "particularidade":      gerar_particularidade_organela,
    "transporte_class":     gerar_transporte_classificacao,
    "transporte_exemplo":   gerar_transporte_exemplo,
    "fase_ciclo":           gerar_fase_ciclo,
}

TOPICOS_BIOCELULAR = {
    "organelas": [
        "funcao_por_organela",
        "organela_por_funcao",
        "particularidade",
    ],
    "membrana": [
        "transporte_class",
        "transporte_exemplo",
    ],
    "ciclo_celular": [
        "fase_ciclo",
    ],
}

PALAVRAS_CHAVE = {
    "funcao_por_organela": ["organela", "organelas", "reticulo endoplasmatico",
                            "complexo de golgi", "lisossomo", "lisossomos",
                            "peroxissomo", "mitocondria", "ribossomo",
                            "centriolo"],
    "organela_por_funcao": ["organela", "organelas", "reticulo endoplasmatico",
                            "complexo de golgi", "lisossomo", "mitocondria",
                            "citoplasma"],
    "particularidade":     ["organela", "organelas", "mitocondria",
                            "peroxissomo", "ribossomo", "catalase",
                            "dna mitocondrial"],
    "transporte_class":    ["transporte de membrana", "membrana plasmatica",
                            "difusao", "difusao facilitada", "osmose",
                            "transporte ativo", "bomba de sodio",
                            "mosaico fluido"],
    "transporte_exemplo":  ["transporte de membrana", "membrana plasmatica",
                            "difusao", "osmose", "aquaporina",
                            "bomba de sodio", "glut"],
    "fase_ciclo":          ["ciclo celular", "interfase", "mitose",
                            "duplicacao do dna", "fase s", "cromatide",
                            "divisao celular"],
}

CHAVES_GENERICAS = {
    "celula", "celulas", "membrana", "funcao", "transporte", "fase",
    "estrutura", "processo", "gradiente", "proteina", "sintese",
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
    """Gera um lote de questões de biologia celular."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_BIOCELULAR)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_BIOCELULAR]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_BIOCELULAR.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_BIOCELULAR]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # O peso reflete quantos FATOS DISTINTOS o veto reconhece.
    LASTRO_POR_FATO = {
        "funcao_por_organela": len(ORGANELAS),
        "organela_por_funcao": len(ORGANELAS),
        "particularidade":     len(ORGANELAS),
        "transporte_class":    len(TRANSPORTES),
        "transporte_exemplo":  len(TRANSPORTES),
        "fase_ciclo":          len(CICLO_CELULAR),
    }
    pesos = {n: max(1, min(round(LASTRO_POR_FATO.get(n, 4) / 4), 4))
             for n in disponiveis}
    fila = []
    for rodada in range(max(pesos.values())):
        for nome in disponiveis:
            if pesos[nome] > rodada:
                fila.append(nome)
    if not fila:
        fila = list(disponiveis)

    questoes, tentativas, limite = [], 0, quantidade * 12
    vistos, fatos_usados = set(), set()

    # A posição na fila avança a cada TENTATIVA, não a cada questão
    # aceita. Com len(questoes), o laço ficava preso na posição de um
    # template cujas questões estavam todas vetadas, até esgotar as
    # tentativas — e então o veto afrouxava e todas entravam de uma vez.
    posicao = 0
    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = fila[posicao % len(fila)]
        posicao += 1
        q = TEMPLATES_BIOCELULAR[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        fato = q.get("_fato")
        if fato and fato in fatos_usados and tentativas < limite * 0.9:
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
    print("  GERADOR DE BIOLOGIA CELULAR")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
