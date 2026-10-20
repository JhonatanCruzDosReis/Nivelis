"""
=============================================================
  GERADOR DE FARMACOLOGIA
=============================================================
  Questões de farmacologia geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO — e por que ele é o que é:

    ✅ Mecanismo de ação e classificação de receptor
    ✅ Superfamílias de receptores e velocidade de resposta
    ✅ Conceitos de farmacocinética
    ✅ Cálculo aritmético COM os valores dados no enunciado

    ❌ DOSE, posologia, ajuste renal, dose pediátrica

  A exclusão da dose não é por dificuldade. Um template com
  dose errada produz centenas de questões com aquela dose, e
  dose é o tipo de coisa que o estudante memoriza sem
  questionar. Mecanismo de ação é verificável em fonte e não
  carrega esse risco.

  Onde há cálculo, o enunciado FORNECE a posologia e o aluno
  faz a conta — o gerador não afirma qual é a dose correta de
  nada.

  VERIFICAÇÃO DAS FONTES

  Registradas em farmacologia/_fontes.md.

  USO:
      from gerador_farmacologia import gerar_lote, gerar_para_api
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

# ── Receptores adrenérgicos ──
#
# Fontes: UNESP Marília (Farmacologia do SNA); Sanarmed; Wikipédia
# (Receptores adrenérgicos); Rang & Dale, Farmacologia.
#
# (receptor, proteína G, local, efeito, observação)
RECEPTORES_ADRENERGICOS = [
    ("α1", "Gq",
     "musculatura lisa vascular",
     "vasoconstrição, com aumento da resistência periférica",
     "também promove midríase, por contração do músculo radial da íris"),
    ("α2", "Gi",
     "terminal nervoso pré-sináptico",
     "inibição da liberação de noradrenalina, por retroalimentação negativa",
     "seu agonista REDUZ o tônus simpático, ao contrário do que o nome sugere"),
    ("β1", "Gs",
     "coração",
     "aumento da frequência e da contratilidade cardíacas",
     "no rim, estimula a liberação de renina"),
    ("β2", "Gs",
     "musculatura lisa brônquica",
     "broncodilatação",
     "também relaxa o útero e promove vasodilatação no músculo esquelético"),
    ("β3", "Gs",
     "tecido adiposo",
     "lipólise",
     "na bexiga, relaxa o músculo detrusor"),
]

# ── Fármacos por alvo — CLASSIFICAÇÃO, sem dose ──
#
# (fármaco, tipo, receptor, seletividade)
FARMACOS_ADRENERGICOS = [
    ("fenilefrina",  "agonista",    "α1", "seletivo"),
    ("clonidina",    "agonista",    "α2", "seletivo"),
    ("dobutamina",   "agonista",    "β1", "seletivo"),
    ("salbutamol",   "agonista",    "β2", "seletivo"),
    ("isoprenalina", "agonista",    "β",  "não seletivo"),
    ("prazosina",    "antagonista", "α1", "seletivo"),
    ("atenolol",     "antagonista", "β1", "seletivo"),
    ("metoprolol",   "antagonista", "β1", "seletivo"),
    ("propranolol",  "antagonista", "β",  "não seletivo"),
]

# ── Superfamílias de receptores ──
#
# Fonte: Rang & Dale, Farmacologia.
#
# (tipo, mecanismo, velocidade, exemplos)
# Cada superfamília traz também a forma PLURAL, usada quando a frase
# diz "os receptores {plural}". Sem isso, saía "os receptores nuclear".
SUPERFAMILIAS = [
    ("canal iônico controlado por ligante",
     "o próprio receptor forma um poro na membrana, que se abre com a "
     "ligação do agonista",
     "milissegundos",
     "receptor nicotínico de acetilcolina e receptor GABA-A",
     "canais iônicos controlados por ligante"),
    ("acoplado a proteína G",
     "a ligação ativa uma proteína G, que desencadeia a produção de um "
     "segundo mensageiro",
     "segundos",
     "receptores muscarínicos, adrenérgicos e opioides",
     "acoplados a proteína G"),
    ("ligado a enzima",
     "o receptor possui domínio catalítico intracelular, com atividade "
     "de tirosina-quinase",
     "minutos",
     "receptor de insulina e receptores de fatores de crescimento",
     "ligados a enzima"),
    ("nuclear",
     "o receptor está no interior da célula e, ao ser ativado, altera a "
     "transcrição gênica",
     "horas",
     "receptores de glicocorticoides, de hormônios tireoidianos e de "
     "esteroides sexuais",
     "nucleares"),
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


def _com_preposicao(prep: str, sintagma: str) -> str:
    """
    Junta preposição e sintagma fazendo a CONTRAÇÃO quando necessário.

    Os campos com artigo ("a meia-vida", "o efeito de primeira
    passagem") são inseridos em frases que já trazem preposição, e sem
    a contração saía "a determinação de a meia-vida".
    """
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "): "à ", ("a", "o "): "ao ",
        ("de", "a "): "da ", ("de", "o "): "do ",
        ("em", "a "): "na ", ("em", "o "): "no ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


# ══════════════════════════════════════════════════════════
#  TEMPLATES — RECEPTORES ADRENÉRGICOS
# ══════════════════════════════════════════════════════════

def gerar_receptor_efeito(rng):
    """Qual o efeito da ativação de determinado receptor adrenérgico?"""
    rec, prot, local, efeito, obs = rng.choice(RECEPTORES_ADRENERGICOS)

    CENARIOS = [
        f"Em um experimento de farmacologia, ativa-se seletivamente o "
        f"receptor adrenérgico {rec}.",
        f"Considere a estimulação do receptor adrenérgico {rec} em "
        f"{local}.",
        f"Um agonista seletivo liga-se ao receptor adrenérgico {rec}.",
        f"A estimulação simpática ativa o receptor adrenérgico {rec} "
        f"presente em {local}.",
        f"Durante o estudo da transmissão adrenérgica, avalia-se a "
        f"ativação do receptor {rec}.",
    ]
    COMANDOS = [
        "O efeito esperado é:",
        "Assinale a alternativa que apresenta o efeito resultante.",
        "Qual o efeito dessa ativação?",
        "Assinale a alternativa que descreve o efeito produzido.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = efeito
    distratores = [r[3] for r in RECEPTORES_ADRENERGICOS if r[3] != efeito]
    distratores += [
        "aumento da secreção de bile pelos hepatócitos",
        "redução da filtração glomerular por vasodilatação da eferente",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"O receptor adrenérgico {rec}, acoplado à proteína {prot} e "
        f"localizado em {local}, produz {efeito}. Vale notar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacologia do sistema nervoso autônomo", rng)
    if q:
        q["_fato"] = f"receptor:{rec}"
    return q


def gerar_receptor_local(rng):
    """Onde predomina determinado receptor adrenérgico?"""
    rec, prot, local, efeito, obs = rng.choice(RECEPTORES_ADRENERGICOS)

    CENARIOS = [
        f"O receptor adrenérgico {rec} distribui-se de forma desigual "
        f"pelos tecidos.",
        f"Ao estudar a distribuição dos adrenoceptores, considera-se o "
        f"receptor {rec}.",
        f"O receptor adrenérgico {rec} é acoplado à proteína {prot}.",
        f"Um estudante revisa a localização predominante do receptor "
        f"adrenérgico {rec}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica seu local de predomínio.",
        "Qual o tecido em que predomina?",
        "Sua localização predominante é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = local
    distratores = [r[2] for r in RECEPTORES_ADRENERGICOS if r[2] != local]
    distratores += [
        "epitélio do túbulo contorcido proximal",
        "membrana pós-sináptica da junção neuromuscular esquelética",
        "células principais do estômago",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"O receptor adrenérgico {rec} predomina em {local}, onde sua "
        f"ativação produz {efeito}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacologia do sistema nervoso autônomo", rng)
    if q:
        q["_fato"] = f"receptor:{rec}"
    return q


def gerar_farmaco_alvo(rng):
    """Em qual receptor o fármaco age, e como?"""
    farmaco, tipo, rec, selet = rng.choice(FARMACOS_ADRENERGICOS)

    CENARIOS = [
        f"O fármaco {farmaco} atua sobre a transmissão adrenérgica.",
        f"Um paciente recebe {farmaco} como parte de seu tratamento.",
        f"Considere o mecanismo de ação do fármaco {farmaco}.",
        f"Em uma aula de farmacologia do sistema nervoso autônomo, "
        f"estuda-se o fármaco {farmaco}.",
        f"O fármaco {farmaco} pertence ao grupo dos que modulam a "
        f"transmissão adrenérgica.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve corretamente seu mecanismo "
        "de ação.",
        "Seu mecanismo de ação é:",
        "Qual o mecanismo de ação desse fármaco?",
        "Assinale a alternativa que apresenta sua ação farmacológica.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    def _descrever(t, r, s):
        return f"{t} {s} de receptores {r}"

    correta = _descrever(tipo, rec, selet)
    distratores = []
    for f2, t2, r2, s2 in FARMACOS_ADRENERGICOS:
        d = _descrever(t2, r2, s2)
        if d != correta:
            distratores.append(d)
    # Inverter o tipo mantendo o receptor é o erro mais comum
    inverso = "antagonista" if tipo == "agonista" else "agonista"
    distratores.insert(0, _descrever(inverso, rec, selet))
    rng.shuffle(distratores)

    explicacao = (
        f"O fármaco {farmaco} é {correta}. "
    )
    if tipo == "agonista":
        explicacao += "Como agonista, ativa o receptor e reproduz o efeito da catecolamina."
    else:
        explicacao += "Como antagonista, ocupa o receptor sem ativá-lo, bloqueando o efeito da catecolamina."
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacologia do sistema nervoso autônomo", rng)
    if q:
        q["_fato"] = f"farmaco:{farmaco}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — SUPERFAMÍLIAS DE RECEPTORES
# ══════════════════════════════════════════════════════════

def gerar_superfamilia_mecanismo(rng):
    """Como funciona determinada superfamília de receptores?"""
    tipo, mecanismo, velocidade, exemplos, plural = rng.choice(SUPERFAMILIAS)

    CENARIOS = [
        f"Os receptores farmacológicos organizam-se em superfamílias. "
        f"Considere os receptores do tipo {tipo}.",
        f"Um estudante revisa as características dos receptores {plural}.",
        f"Entre as superfamílias de receptores encontram-se os "
        f"{plural}.",
        f"A classificação dos receptores farmacológicos inclui o grupo "
        f"dos receptores {plural}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve corretamente seu mecanismo.",
        "Seu mecanismo de transdução de sinal é:",
        "Qual o mecanismo desses receptores?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = mecanismo
    distratores = [s[1] for s in SUPERFAMILIAS if s[1] != mecanismo]
    # Os distratores inventados seguem o mesmo padrão das respostas
    # reais: afirmação direta, sem "em geral" nem "geralmente". Quando só
    # a correta trazia hedge, a estratégia "marque a moderada" tinha
    # vantagem.
    distratores += [
        "o receptor é degradado após a ligação, liberando o segundo "
        "mensageiro no citoplasma",
        "a ligação do agonista provoca fusão do receptor com a membrana "
        "mitocondrial",
        "o receptor transloca-se para a membrana nuclear e ativa a "
        "polimerase do RNA",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"Nos receptores {plural}, {mecanismo}. A resposta ocorre em "
        f"{velocidade}, e são exemplos os {exemplos}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacologia geral (receptores)", rng)
    if q:
        q["_fato"] = f"superfamilia:{tipo}"
    return q


def gerar_superfamilia_velocidade(rng):
    """Qual superfamília responde em determinada escala de tempo?"""
    tipo, mecanismo, velocidade, exemplos, plural = rng.choice(SUPERFAMILIAS)

    # O espaço é pequeno por natureza — quatro superfamílias —, então a
    # variação depende dos cenários. Com três, o template rendia 36
    # enunciados distintos.
    CENARIOS = [
        f"A velocidade de resposta de um receptor depende de seu "
        f"mecanismo de transdução. Certa superfamília responde em "
        f"{velocidade}.",
        f"Em um experimento, observa-se que determinado receptor produz "
        f"resposta na escala de {velocidade}.",
        f"O tempo entre a ligação do agonista e o efeito celular é de "
        f"aproximadamente {velocidade} em certa superfamília de receptores.",
        f"Um ensaio farmacológico registra latência de {velocidade} entre "
        f"a exposição ao agonista e a resposta mensurável.",
        f"A comparação entre superfamílias de receptores mostra que uma "
        f"delas responde em {velocidade}.",
        f"Ao caracterizar um receptor recém-descrito, verifica-se que sua "
        f"resposta se instala em {velocidade}.",
        f"Certa classe de receptores produz efeito celular na escala de "
        f"{velocidade} após a ligação do ligante.",
        f"Um estudante compara a cinética de resposta das superfamílias "
        f"de receptores e identifica uma que responde em {velocidade}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que identifica essa superfamília.",
        "Trata-se de receptores do tipo:",
        "Qual superfamília apresenta esse comportamento?",
        "Assinale a alternativa que a nomeia corretamente.",
        "Essa superfamília corresponde aos receptores do tipo:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = tipo
    distratores = [s[0] for s in SUPERFAMILIAS if s[0] != tipo]
    distratores += [
        "receptor de membrana acoplado a canal de cálcio dependente de voltagem",
        "receptor citoplasmático acoplado a proteína quinase C",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"São os receptores {tipo}: {mecanismo}, e por isso a resposta "
        f"ocorre em {velocidade}. A velocidade acompanha o mecanismo — "
        f"canal iônico é o mais rápido, receptor nuclear o mais lento, "
        f"porque este depende de transcrição gênica e síntese proteica."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacologia geral (receptores)", rng)
    if q:
        q["_fato"] = f"superfamilia:{tipo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — FARMACOCINÉTICA
# ══════════════════════════════════════════════════════════

# (conceito, definição, observação)
# Cada conceito traz o ARTIGO, porque o gênero varia: "a
# biodisponibilidade" mas "o efeito de primeira passagem". Sem isso,
# saía "a determinação do seu meia-vida".
CONCEITOS_FC = [
    ("biodisponibilidade", "a biodisponibilidade",
     "a fração da dose administrada que alcança a circulação sistêmica "
     "de forma inalterada",
     "por definição, é de 100% para a via intravenosa"),
    ("efeito de primeira passagem", "o efeito de primeira passagem",
     "a metabolização do fármaco pelo fígado antes de alcançar a "
     "circulação sistêmica",
     "afeta a via oral e é contornado pelas vias sublingual e retal"),
    ("meia-vida de eliminação", "a meia-vida de eliminação",
     "o tempo necessário para que a concentração plasmática se reduza à "
     "metade",
     "após cerca de cinco meias-vidas, considera-se o fármaco eliminado"),
    ("volume de distribuição", "o volume de distribuição",
     "o volume teórico em que a dose administrada precisaria se dissolver "
     "para atingir a concentração plasmática observada",
     "valores elevados indicam distribuição ampla nos tecidos"),
    ("clearance", "o clearance",
     "o volume de plasma completamente depurado do fármaco por unidade "
     "de tempo",
     "determina a dose de manutenção necessária"),
    ("ligação a proteínas plasmáticas", "a ligação a proteínas plasmáticas",
     "a fração do fármaco que circula ligada à albumina e não exerce "
     "efeito farmacológico",
     "apenas a fração livre é farmacologicamente ativa"),
]


def gerar_conceito_fc(rng):
    """Definição de um conceito de farmacocinética."""
    conceito, conceito_art, definicao, obs = rng.choice(CONCEITOS_FC)
    modo = rng.choice(["pelo_nome", "pela_definicao"])

    if modo == "pelo_nome":
        CENARIOS = [
            f"Em farmacocinética, o termo \"{conceito}\" descreve uma "
            f"propriedade do fármaco no organismo.",
            f"Um estudante revisa o conceito de {conceito}.",
            f"Entre os parâmetros farmacocinéticos encontra-se "
            f"{conceito_art}.",
            f"A avaliação de um novo fármaco inclui a determinação "
            f"{_com_preposicao('de', conceito_art)} desse fármaco.",
        ]
    # Sem pronome: o referente é o conceito, e o gênero varia — "a
    # meia-vida" contra "o clearance". "que O define" quebra num,
    # "que A define" quebra no outro.
        COMANDOS = [
    # "corresponde a:" + "o volume teórico..." produzia "a o". As
    # definições são sintagmas nominais com artigo, então o comando
    # não pode terminar em preposição.
            "Assinale a alternativa que define esse parâmetro.",
            "Esse parâmetro é definido como:",
            "Qual a definição correta?",
            "Assinale a alternativa com a definição correta.",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = definicao
        distratores = [c[2] for c in CONCEITOS_FC if c[2] != definicao]
        distratores += [
            "a velocidade com que o fármaco atravessa a barreira "
            "hematoencefálica",
            "a concentração mínima capaz de produzir efeito tóxico",
        ]
    else:
        CENARIOS = [
            f"Certo parâmetro farmacocinético corresponde "
            f"{_com_preposicao('a', definicao)}.",
            f"Em farmacocinética, define-se como {definicao}.",
            f"Ao caracterizar um fármaco, mede-se {definicao}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que nomeia esse parâmetro.",
            "Trata-se de:",
            "Esse parâmetro é denominado:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = conceito
        distratores = [c[0] for c in CONCEITOS_FC if c[0] != conceito]
        distratores += [
            "índice terapêutico",
            "concentração inibitória mínima",
            "potência relativa",
        ]

    rng.shuffle(distratores)
    # _frase() acrescenta ponto final, o que quebrava a frase no meio:
    # "Clearance. é o volume de plasma...". Aqui só a maiúscula inicial
    # é necessária.
    conceito_cap = conceito[0].upper() + conceito[1:]
    explicacao = (
        f"{conceito_cap} é {definicao}. Convém lembrar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Farmacocinética", rng)
    if q:
        q["_fato"] = f"fc:{conceito}"
    return q


def gerar_meia_vida(rng):
    """
    Cálculo de eliminação por meias-vidas.

    O enunciado FORNECE a meia-vida — o gerador não afirma qual é a
    meia-vida real de fármaco nenhum. O aluno faz a aritmética.
    """
    meia_vida = rng.choice([2, 3, 4, 6, 8, 12])
    n_meias = rng.choice([2, 3, 4, 5])
    conc_inicial = rng.choice([80, 100, 120, 160, 200, 240])

    tempo = meia_vida * n_meias
    restante = conc_inicial / (2 ** n_meias)

    CENARIOS = [
        f"Um fármaco hipotético apresenta meia-vida de eliminação de "
        f"{meia_vida} horas. Sua concentração plasmática inicial é de "
        f"{conc_inicial} mg/L.",
        f"Após a administração de um fármaco com meia-vida de "
        f"{meia_vida} horas, mede-se concentração plasmática de "
        f"{conc_inicial} mg/L.",
        f"Considere um fármaco cuja meia-vida de eliminação é de "
        f"{meia_vida} horas, com concentração plasmática inicial de "
        f"{conc_inicial} mg/L.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)} Decorridas {tempo} horas, a "
                 f"concentração plasmática esperada é de:")

    correta = round(restante, 2)
    candidatos = [
        round(conc_inicial / (2 * n_meias), 2),      # dividiu por 2n
        round(conc_inicial - (conc_inicial / n_meias), 2),
        round(conc_inicial / (2 ** (n_meias - 1)), 2),   # errou uma meia-vida
        round(conc_inicial / (2 ** (n_meias + 1)), 2),
        round(conc_inicial / n_meias, 2),
        round(conc_inicial / 2, 2),
    ]
    distratores = [d for d in candidatos if d > 0 and abs(d - correta) > 0.01]

    # A explicação TERMINA no resultado. O comentário sobre o erro
    # comum vem antes, porque o aluno lê a última linha.
    explicacao = (
        f"O decaimento é exponencial, não linear — dividir a "
        f"concentração pelo número de meias-vidas é o erro mais comum. "
        f"Em {tempo} horas transcorrem {n_meias} meias-vidas de "
        f"{meia_vida} horas cada, e a cada uma a concentração cai pela "
        f"metade: {conc_inicial} → " +
        " → ".join(str(round(conc_inicial / (2 ** i), 2))
                   for i in range(1, n_meias + 1)) +
        f" mg/L."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Farmacocinética (cálculo)", rng,
                formatador=lambda v: (f"{v:,.2f}".replace(",", "§")
                                      .replace(".", ",").replace("§", ".")
                                      + " mg/L"))
    if q:
        q["_fato"] = f"meiavida:{meia_vida}:{n_meias}:{conc_inicial}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_FARMACOLOGIA = {
    "receptor_efeito":         gerar_receptor_efeito,
    "receptor_local":          gerar_receptor_local,
    "farmaco_alvo":            gerar_farmaco_alvo,
    "superfamilia_mecanismo":  gerar_superfamilia_mecanismo,
    "superfamilia_velocidade": gerar_superfamilia_velocidade,
    "conceito_fc":             gerar_conceito_fc,
    "meia_vida":               gerar_meia_vida,
}

TOPICOS_FARMACOLOGIA = {
    "autonomo": [
        "receptor_efeito",
        "receptor_local",
        "farmaco_alvo",
    ],
    "receptores": [
        "superfamilia_mecanismo",
        "superfamilia_velocidade",
    ],
    "farmacocinetica": [
        "conceito_fc",
        "meia_vida",
    ],
}

# Singular E plural: o casamento é por palavra inteira, e o índice de um
# livro costuma usar o plural ("Receptores adrenérgicos"). Mesmo cuidado
# já foi necessário no gerador de anatomia.
PALAVRAS_CHAVE = {
    "receptor_efeito":         ["receptor adrenergico",
                                "receptores adrenergicos",
                                "adrenoceptor", "adrenoceptores",
                                "sistema nervoso autonomo", "simpatico",
                                "catecolamina", "catecolaminas",
                                "noradrenalina", "adrenalina"],
    "receptor_local":          ["receptor adrenergico",
                                "receptores adrenergicos",
                                "adrenoceptor", "adrenoceptores",
                                "simpatico", "catecolamina",
                                "catecolaminas"],
    "farmaco_alvo":            ["betabloqueador", "betabloqueadores",
                                "beta-bloqueador", "beta-bloqueadores",
                                "agonista adrenergico",
                                "agonistas adrenergicos",
                                "antagonista adrenergico",
                                "antagonistas adrenergicos",
                                "propranolol", "atenolol", "salbutamol",
                                "clonidina", "adrenergico", "adrenergicos",
                                "simpaticomimetico", "simpaticomimeticos"],
    "superfamilia_mecanismo":  ["superfamilia de receptores",
                                "superfamilias de receptores",
                                "proteina g", "receptor ionotropico",
                                "receptores ionotropicos",
                                "receptor metabotropico",
                                "receptores metabotropicos",
                                "tirosina quinase", "receptor nuclear",
                                "receptores nucleares"],
    "superfamilia_velocidade": ["superfamilia de receptores",
                                "superfamilias de receptores", "proteina g",
                                "transducao de sinal", "segundo mensageiro",
                                "segundos mensageiros"],
    "conceito_fc":             ["farmacocinetica", "biodisponibilidade",
                                "primeira passagem", "meia-vida",
                                "meia vida", "clearance", "depuracao",
                                "volume de distribuicao"],
    "meia_vida":               ["farmacocinetica", "meia-vida", "meia vida",
                                "eliminacao", "depuracao", "clearance"],
}

CHAVES_GENERICAS = {
    "receptor", "receptores", "farmaco", "farmacos", "mecanismo",
    "acao", "efeito", "sistema", "velocidade", "concentracao",
    "distribuicao", "ligacao",
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
    """Gera um lote de questões de farmacologia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_FARMACOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_FARMACOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_FARMACOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_FARMACOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Quantos fatos distintos cada template explora, para o sorteio ser
    # proporcional ao material — ver comentário equivalente em
    # gerador_anatomia.gerar_lote.
    LASTRO = {
        "receptor_efeito":         len(RECEPTORES_ADRENERGICOS),
        "receptor_local":          len(RECEPTORES_ADRENERGICOS),
        "farmaco_alvo":            len(FARMACOS_ADRENERGICOS),
        "superfamilia_mecanismo":  len(SUPERFAMILIAS),
        "superfamilia_velocidade": len(SUPERFAMILIAS),
        "conceito_fc":             len(CONCEITOS_FC),
        # O lastro do meia_vida é combinatório (144 variações), mas usar
        # esse número o fazia dominar a fila: 3 das 10 questões de um
        # lote eram cálculo de meia-vida. O peso reflete o número de
        # CONCEITOS que o template explora, não de variações numéricas.
        "meia_vida":               len(CONCEITOS_FC),
    }
    # Ver comentário equivalente em gerador_bioquimica.gerar_lote: a
    # fila é intercalada, não agrupada, para que um lote pequeno percorra
    # todos os templates antes de repetir qualquer um.
    pesos = {n: max(1, min(round(LASTRO.get(n, 6) / 5), 6))
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
        q = TEMPLATES_FARMACOLOGIA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        # Um mesmo fato não rende duas questões no lote: perguntar o
        # efeito e o local do receptor β2 é perguntar duas vezes a mesma
        # coisa.
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
    print("  GERADOR DE FARMACOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
