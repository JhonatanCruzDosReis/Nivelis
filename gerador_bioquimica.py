"""
=============================================================
  GERADOR DE BIOQUÍMICA
=============================================================
  Questões de bioquímica geradas proceduralmente, sem depender
  de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Vias metabólicas — local, saldo, enzimas reguladoras
    ✅ Sequência de etapas e produtos
    ✅ Cálculo de rendimento COM a contagem explicitada

  UMA DECISÃO SOBRE O RENDIMENTO DE ATP

  Há duas contagens em circulação. A CLÁSSICA atribui 3 ATP
  por NADH e 2 por FADH₂ (total de 36 a 38 por glicose). A
  ATUAL, baseada na medida da razão P/O, atribui cerca de 2,5
  e 1,5 (total de 30 a 32).

  Nenhuma é "errada" — são convenções diferentes, e provas
  usam ambas. Por isso, os templates evitam perguntar o total
  em aberto; quando o rendimento aparece, o enunciado
  explicita qual contagem adotar.

  VERIFICAÇÃO DAS FONTES

  Registradas em bioquimica/_fontes.md, incluindo uma
  divergência sobre o número de reações da glicólise (uma
  fonte diz 11; a literatura padrão diz 10 — adotado 10).

  USO:
      from gerador_bioquimica import gerar_lote, gerar_para_api
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

# ── Etapas da respiração celular ──
#
# Fontes: Khan Academy; UFLA — Temas em Fisiologia Vegetal; Biologia Net;
# Lehninger, Princípios de Bioquímica.
#
# (etapa, local, entrada, produtos por glicose, observação)
# Mesmo cuidado das vias: o artigo acompanha o nome.
ETAPAS_RESPIRACAO = [
    ("glicólise", "a glicólise", "citosol",
     "uma molécula de glicose",
     "2 ATP, 2 NADH e 2 piruvato",
     "não requer oxigênio, e o saldo de 2 ATP é líquido — produzem-se 4 "
     "e consomem-se 2 na fase de investimento"),

    ("descarboxilação oxidativa do piruvato",
     "a descarboxilação oxidativa do piruvato", "matriz mitocondrial",
     "duas moléculas de piruvato",
     "2 CO₂ e 2 NADH",
     "é catalisada pelo complexo piruvato desidrogenase e conecta a "
     "glicólise ao ciclo de Krebs"),

    ("ciclo de Krebs", "o ciclo de Krebs", "matriz mitocondrial",
     "duas moléculas de acetil-CoA",
     "4 CO₂, 6 NADH, 2 FADH₂ e 2 GTP",
     "uma glicose origina DUAS acetil-CoA, e cada volta do ciclo "
     "processa uma delas — por isso os valores aparecem dobrados na "
     "contagem por glicose"),

    ("cadeia transportadora de elétrons",
     "a cadeia transportadora de elétrons",
     "membrana interna da mitocôndria",
     "os NADH e FADH₂ produzidos nas etapas anteriores",
     "ATP por fosforilação oxidativa e água",
     "o oxigênio é o aceptor final de elétrons, formando água"),
]

# ── Enzimas reguladoras da glicólise ──
#
# (enzima, reação, papel)
ENZIMAS_GLICOLISE = [
    ("hexoquinase",
     "glicose em glicose-6-fosfato",
     "catalisa a primeira fosforilação da via"),
    ("fosfofrutoquinase-1",
     "frutose-6-fosfato em frutose-1,6-bifosfato",
     "é o principal ponto de regulação e a primeira etapa comprometida "
     "com a glicólise"),
    ("piruvato quinase",
     "fosfoenolpiruvato em piruvato",
     "catalisa a última reação da via, com produção de ATP"),
]


# ── Aminoácidos, proteínas e enzimas ──
#
# Fontes: Lehninger, Princípios de Bioquímica; Berg, Bioquímica.
#
# (nível, descrição, estabilizado por)
ESTRUTURA_PROTEICA = [
    ("primária",
     "a sequência linear de aminoácidos unidos por ligações peptídicas",
     "ligações peptídicas covalentes"),
    ("secundária",
     "o arranjo local da cadeia em hélice alfa ou folha beta pregueada",
     "pontes de hidrogênio entre átomos da cadeia principal"),
    ("terciária",
     "o dobramento tridimensional completo de uma única cadeia "
     "polipeptídica",
     # A distinção entre terciária e quaternária é DENTRO x ENTRE
     # cadeias. Redigir as duas quase iguais — 84% de similaridade —
     # transformava a questão em teste de leitura atenta. Aqui a
     # diferença aparece logo no começo da alternativa.
     "interações entre cadeias laterais DENTRO de uma mesma cadeia: "
     "pontes dissulfeto, ligações iônicas e forças hidrofóbicas"),
    ("quaternária",
     "a associação de duas ou mais cadeias polipeptídicas em um "
     "complexo funcional",
     # O estabilizador não NOMEIA a estrutura terciária: quando a
     # pergunta é sobre a terciária, este texto vira distrator e citar
     # o nome ali torna a alternativa circular.
     "interações ENTRE subunidades diferentes: pontes dissulfeto, "
     "ligações iônicas e forças hidrofóbicas"),
]

# ── Vias metabólicas e sua natureza ──
#
# (via, natureza, local, função)
# Cada via traz o ARTIGO junto, porque o gênero varia: "a
# gliconeogênese" mas "o ciclo da ureia". Sem isso, o enunciado saía
# como "analisa a ciclo da ureia".
#
# O campo `nome` é usado quando a frase já fornece o determinante; o
# campo `com_artigo`, quando a frase precisa dele.
VIAS_METABOLICAS = [
    ("glicogênese", "a glicogênese", "anabólica", "citosol",
     "síntese de glicogênio a partir de glicose"),
    ("glicogenólise", "a glicogenólise", "catabólica", "citosol",
     "degradação do glicogênio, liberando glicose-1-fosfato"),
    ("gliconeogênese", "a gliconeogênese", "anabólica",
     "citosol e mitocôndria",
     "síntese de glicose a partir de precursores não glicídicos, como "
     "lactato, glicerol e aminoácidos"),
    ("beta-oxidação", "a beta-oxidação", "catabólica",
     "matriz mitocondrial",
     "degradação de ácidos graxos, gerando acetil-CoA"),
    ("lipogênese", "a lipogênese", "anabólica", "citosol",
     "síntese de ácidos graxos a partir de acetil-CoA"),
    ("cetogênese", "a cetogênese", "catabólica",
     "matriz mitocondrial do hepatócito",
     "produção de corpos cetônicos a partir de acetil-CoA"),
    ("via das pentoses-fosfato", "a via das pentoses-fosfato",
     "anabólica", "citosol",
     "produção de NADPH e de ribose-5-fosfato para a síntese de "
     "nucleotídeos"),
    ("ciclo da ureia", "o ciclo da ureia", "anabólica",
     "citosol e mitocôndria do hepatócito",
     "eliminação do nitrogênio amínico na forma de ureia"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str, tipo_resposta=None):
    """
    `tipo_resposta` informa se a resposta é numérica ou textual.

    O teste de português só exige que a explicação termine em número
    quando a resposta é numérica — sem o metadado, ele cobrava isso de
    questões cuja resposta é "matriz mitocondrial".
    """
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
    # Sem tipo declarado, deduz pelo gabarito: se não tem dígito, é
    # textual. Assim os templates existentes não precisam ser alterados
    # um a um.
    if tipo_resposta is None:
        # Ter dígito não basta: "frutose-1,6-bifosfato" e "4 CO₂, 6 NADH"
        # são respostas TEXTUAIS que por acaso contêm números.
        #
        # Numérica de verdade é a que consiste essencialmente em um
        # valor — poucos caracteres, sem nome de substância.
        _txt = str(correta).strip()
        _so_numero = bool(re.fullmatch(r'[\d\s.,+\-]+(?:\s*\w{1,6})?', _txt))
        tipo_resposta = "numerica" if _so_numero else "textual"
    return {
        "enunciado":         enunciado,
        "alternativas":      alternativas,
        "gabarito":          gabarito,
        "explicacao":        explicacao,
        "topico":            topico,
        "tipo_resposta":     tipo_resposta,
        "tem_elemento_visual": False,
    }


def _inicial_maiuscula(t: str) -> str:
    """
    Eleva apenas a PRIMEIRA letra, preservando o resto.

    str.capitalize() rebaixa todas as demais, o que estraga nomes
    próprios: "o ciclo de Krebs" virava "O ciclo de krebs".
    """
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


def _com_preposicao(prep: str, sintagma: str) -> str:
    """
    Junta preposição e sintagma fazendo a CONTRAÇÃO quando necessário.

    Sem isso saíam construções como "chega a a descarboxilação" e
    "corresponde a o dobramento". O campo com artigo já traz "a" ou "o"
    no início, e a preposição precisa fundir-se a ele.
    """
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "):  "à ",
        ("a", "o "):  "ao ",
        ("a", "as "): "às ",
        ("a", "os "): "aos ",
        ("de", "a "): "da ",
        ("de", "o "): "do ",
        ("de", "as "): "das ",
        ("de", "os "): "dos ",
        ("em", "a "): "na ",
        ("em", "o "): "no ",
        ("em", "as "): "nas ",
        ("em", "os "): "nos ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


# ══════════════════════════════════════════════════════════
#  TEMPLATES — RESPIRAÇÃO CELULAR
# ══════════════════════════════════════════════════════════

def gerar_etapa_local(rng):
    """Onde ocorre determinada etapa da respiração celular?"""
    etapa, etapa_art, local, entrada, produtos, obs = rng.choice(ETAPAS_RESPIRACAO)

    CENARIOS = [
        f"Considere {etapa_art} no contexto da respiração celular.",
        f"{_inicial_maiuscula(etapa_art)} é uma das etapas do metabolismo energético.",
        f"Um estudante revisa a compartimentalização da respiração "
        f"celular e chega {_com_preposicao('a', etapa_art)}.",
        f"Entre as etapas da oxidação da glicose encontra-se {etapa_art}.",
        f"{_inicial_maiuscula(etapa_art)} tem como entrada {entrada}.",
    ]
    # Sem pronome: o referente é a etapa, e "o ciclo de Krebs" é
    # masculino enquanto "a glicólise" é feminino. Repetir "essa etapa"
    # resolve, porque "etapa" é sempre feminino.
    COMANDOS = [
        "Assinale a alternativa que indica onde essa etapa ocorre.",
        "Essa etapa ocorre em:",
        "Qual o compartimento celular em que essa etapa acontece?",
        "Assinale a alternativa que apresenta seu local.",
        "Em que compartimento celular essa etapa se realiza?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = local
    distratores = [e[2] for e in ETAPAS_RESPIRACAO if e[2] != local]
    distratores += [
        "espaço intermembranas da mitocôndria",
        "membrana externa da mitocôndria",
        "lúmen do retículo endoplasmático rugoso",
        "complexo de Golgi",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(etapa_art)} ocorre em: {local}. A partir de {entrada}, "
        f"origina {produtos}. "
        f"Convém lembrar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (respiração celular)", rng)
    if q:
        q["_fato"] = f"etapa:{etapa}"
    return q


def gerar_etapa_produtos(rng):
    """Quais os produtos de determinada etapa, por glicose?"""
    etapa, etapa_art, local, entrada, produtos, obs = rng.choice(ETAPAS_RESPIRACAO[:3])

    CENARIOS = [
        f"Considere {etapa_art}, que ocorre em {local}.",
        f"{_inicial_maiuscula(etapa_art)} processa {entrada}.",
        f"Ao acompanhar o destino de uma molécula de glicose, chega-se "
        f"{_com_preposicao('a', etapa_art)}.",
        f"Um estudante calcula o rendimento de cada etapa da respiração "
        f"celular e analisa {etapa_art}.",
        f"O balanço energético {_com_preposicao('de', etapa_art)} pode "
        f"ser contabilizado por "
        f"molécula de glicose.",
        f"Em uma aula de metabolismo, discute-se o rendimento "
        f"{_com_preposicao('de', etapa_art)}.",
        f"A contabilidade dos produtos {_com_preposicao('de', etapa_art)} "
        f"costuma gerar dúvidas.",
        f"Ao somar os produtos da respiração celular, considera-se "
        f"separadamente {etapa_art}.",
    ]
    COMANDOS = [
        "Considerando UMA molécula de glicose, os produtos dessa etapa são:",
        "Por molécula de glicose processada, essa etapa produz:",
        "Assinale a alternativa que apresenta seus produtos, por glicose.",
        "O saldo dessa etapa, por glicose, corresponde a:",
        "Assinale a alternativa com o rendimento correto por glicose.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = produtos
    distratores = [e[4] for e in ETAPAS_RESPIRACAO if e[4] != produtos]
    distratores += [
        "4 ATP, 4 NADH e 2 piruvato",
        "2 CO₂, 4 NADH e 1 FADH₂",
        "6 CO₂, 2 NADH e 4 ATP",
        "1 ATP, 1 NADH e 1 acetil-CoA",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(etapa_art)}, a partir de {entrada}, produz {produtos}. "
        f"Vale notar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (respiração celular)", rng)
    if q:
        q["_fato"] = f"etapa:{etapa}"
    return q


def gerar_etapa_sequencia(rng):
    """Qual etapa precede ou sucede outra?"""
    idx = rng.randrange(len(ETAPAS_RESPIRACAO))
    etapa = ETAPAS_RESPIRACAO[idx][0]
    etapa_art = ETAPAS_RESPIRACAO[idx][1]

    direcao = rng.choice(["antes", "depois"])
    if direcao == "antes" and idx == 0:
        direcao = "depois"
    if direcao == "depois" and idx == len(ETAPAS_RESPIRACAO) - 1:
        direcao = "antes"
    alvo = (ETAPAS_RESPIRACAO[idx - 1] if direcao == "antes"
            else ETAPAS_RESPIRACAO[idx + 1])

    palavra = "precede" if direcao == "antes" else "sucede"
    CENARIOS = [
        "Na sequência de etapas da respiração celular aeróbia",
        "Ao ordenar cronologicamente as etapas da oxidação da glicose",
        "No encadeamento das reações do metabolismo energético",
        "Durante o estudo da sucessão de etapas da respiração celular",
    ]
    # Os comandos evitam PRONOME, porque o referente muda de gênero:
    # "a etapa que A precede" quebra quando a etapa é "o ciclo de Krebs".
    # Repetir o substantivo custa uma palavra e elimina o problema.
    posicao = "imediatamente anterior" if direcao == "antes" else "imediatamente posterior"
    COMANDOS = [
        f"Assinale a alternativa que apresenta a etapa {posicao}.",
        f"Qual é a etapa {posicao}?",
        f"Entre as etapas listadas, qual ocupa a posição {posicao}?",
        f"Assinale a alternativa com a etapa {posicao}.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)}, considere {etapa_art}. "
                 f"{rng.choice(COMANDOS)}")

    correta = alvo[0]
    distratores = [e[0] for e in ETAPAS_RESPIRACAO
                   if e[0] not in (etapa, correta)]
    distratores += [
        "fermentação láctica",
        "via das pentoses-fosfato",
        "gliconeogênese hepática",
    ]

    explicacao = (
        f"A ordem das etapas é: glicólise → descarboxilação oxidativa do "
        f"piruvato → ciclo de Krebs → cadeia transportadora de elétrons. "
        f"Portanto, a etapa {posicao} à de {etapa} é: {correta}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Bioquímica (respiração celular)", rng)
    if q:
        q["_fato"] = f"seq:{etapa}:{direcao}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — REGULAÇÃO DA GLICÓLISE
# ══════════════════════════════════════════════════════════

def gerar_enzima_reacao(rng):
    """Qual reação determinada enzima catalisa?"""
    enzima, reacao, papel = rng.choice(ENZIMAS_GLICOLISE)

    CENARIOS = [
        f"A {enzima} é uma das enzimas reguladoras da glicólise.",
        f"Entre as três enzimas irreversíveis da glicólise encontra-se "
        f"a {enzima}.",
        f"Considere a {enzima} no contexto da via glicolítica.",
        f"Um estudante revisa o papel da {enzima} na glicólise.",
        f"A atividade da {enzima} determina o fluxo por uma das etapas "
        f"da glicólise.",
        f"Em um ensaio enzimático, mede-se a atividade da {enzima}.",
        f"A {enzima} atua em uma etapa específica da via glicolítica.",
        f"Ao mapear as reações da glicólise, identifica-se a {enzima}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta a reação que ela catalisa.",
        "Essa enzima catalisa a conversão de:",
        "Qual reação essa enzima catalisa?",
        "Assinale a alternativa com a reação correspondente.",
        "A reação catalisada por ela é a conversão de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = reacao
    distratores = [e[1] for e in ENZIMAS_GLICOLISE if e[1] != reacao]
    distratores += [
        "gliceraldeído-3-fosfato em 1,3-bifosfoglicerato",
        "piruvato em acetil-CoA",
        "oxaloacetato em citrato",
        "glicose-6-fosfato em frutose-6-fosfato",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"A {enzima} catalisa a conversão de {reacao} e {papel}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (regulação da glicólise)", rng)
    if q:
        q["_fato"] = f"enzima:{enzima}"
    return q


def gerar_ponto_regulacao(rng):
    """
    Qual a principal enzima reguladora da glicólise?

    A PFK-1 é o ponto de controle central, e o motivo — ser a primeira
    etapa comprometida com a via — é o que a prova cobra.
    """
    modo = rng.choice(["qual_enzima", "por_que"])

    if modo == "qual_enzima":
        CENARIOS = [
            "A glicólise possui três enzimas irreversíveis, mas apenas "
            "uma constitui o principal ponto de controle da via.",
            "O fluxo pela via glicolítica é regulado sobretudo em uma "
            "de suas etapas.",
            "Entre as enzimas reguladoras da glicólise, uma responde "
            "pelo controle principal do fluxo.",
            "A primeira etapa comprometida com a glicólise é catalisada "
            "por uma enzima específica.",
            "O ponto de controle central da glicólise concentra-se em "
            "uma única enzima.",
            "A velocidade da glicólise é determinada principalmente por "
            "uma de suas enzimas.",
            "Em condições de alta demanda energética, uma enzima da "
            "glicólise responde como principal reguladora.",
        ]
        COMANDOS = [
            "Assinale a alternativa que a identifica.",
            "Trata-se da:",
            "Essa enzima é a:",
            "Assinale a alternativa correspondente.",
            "Qual enzima desempenha esse papel?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "fosfofrutoquinase-1"
        distratores = [e[0] for e in ENZIMAS_GLICOLISE
                       if e[0] != "fosfofrutoquinase-1"]
        distratores += [
            "gliceraldeído-3-fosfato desidrogenase",
            "fosfoglicerato quinase",
            "enolase",
            "aldolase",
        ]
        explicacao = (
            "A fosfofrutoquinase-1 é o principal ponto de regulação da "
            "glicólise, por catalisar a primeira etapa comprometida com a "
            "via. A glicose-6-fosfato e a frutose-6-fosfato ainda podem "
            "seguir outros destinos metabólicos, mas a frutose-1,6-"
            "bifosfato só é direcionada à glicólise."
        )
    else:
        CENARIOS = [
            "A fosfofrutoquinase-1 é considerada o principal ponto de "
            "regulação da glicólise.",
            "Entre as enzimas da via glicolítica, a fosfofrutoquinase-1 "
            "ocupa posição de destaque na regulação.",
            "O controle do fluxo glicolítico concentra-se na etapa "
            "catalisada pela fosfofrutoquinase-1.",
            "A fosfofrutoquinase-1 recebe atenção especial no estudo da "
            "regulação metabólica.",
            "Livros de bioquímica destacam a fosfofrutoquinase-1 entre as "
            "enzimas da glicólise.",
            "A etapa catalisada pela fosfofrutoquinase-1 tem importância "
            "regulatória particular.",
        ]
        COMANDOS = [
            "Assinale a alternativa que justifica essa importância.",
            "A razão para isso é que:",
            "Qual a justificativa para esse papel central?",
            "Assinale a alternativa que explica esse destaque.",
            "Isso se deve ao fato de que essa enzima:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        # A resposta certa tinha 118 caracteres contra 50 a 75 dos
        # distratores. Encurtada, e os distratores ganharam extensão
        # semelhante — o tamanho não deve correlacionar com a resposta.
        correta = ("catalisa a primeira etapa comprometida com a via "
                   "glicolítica")
        distratores = [
            "é a única enzima da via que dispensa ATP como substrato",
            "catalisa a reação de maior rendimento energético da via",
            "controla a entrada de glicose no citosol da célula",
            "atua na única etapa reversível de toda a via glicolítica",
            "está presente em maior concentração que as demais enzimas",
        ]
        # A explicação TERMINA no resultado: a glicose-6-fosfato e a
        # frutose-6-fosfato ainda podem seguir outras vias, e é isso que
        # faz da PFK-1 o passo comprometido.
        explicacao = (
            "Antes da fosfofrutoquinase-1, a glicose-6-fosfato e a "
            "frutose-6-fosfato ainda podem ser desviadas para outras "
            "vias, como a das pentoses-fosfato ou a síntese de "
            "glicogênio. Por isso a PFK-1, que converte frutose-6-fosfato "
            "em frutose-1,6-bifosfato, catalisa a primeira etapa "
            "comprometida com a glicólise."
        )

    q = _montar(enunciado, correta, distratores, explicacao,
                "Bioquímica (regulação da glicólise)", rng)
    if q:
        q["_fato"] = f"regulacao:pfk1:{modo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — ESTRUTURA PROTEICA
# ══════════════════════════════════════════════════════════

def gerar_estrutura_proteica(rng):
    """Qual nível de estrutura proteica corresponde a determinada descrição?"""
    nivel, descricao, estabilizador = rng.choice(ESTRUTURA_PROTEICA)
    modo = rng.choice(["pela_descricao", "pelo_nivel"])

    if modo == "pela_descricao":
        CENARIOS = [
            f"Ao analisar uma proteína, identifica-se {descricao}.",
            f"Certo nível de organização proteica corresponde "
            f"{_com_preposicao('a', descricao)}.",
            f"Em um estudo de estrutura proteica, observa-se {descricao}.",
        ]
        COMANDOS = [
            "Esse nível de organização é a estrutura:",
            "Assinale a alternativa que o identifica.",
            "Trata-se da estrutura:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = nivel
        distratores = [e[0] for e in ESTRUTURA_PROTEICA if e[0] != nivel]
        distratores += ["supersecundária", "quinária", "de domínio isolado"]
    else:
        CENARIOS = [
            f"A estrutura {nivel} de uma proteína tem definição precisa.",
            f"Considere a estrutura {nivel} de uma proteína.",
            f"Um estudante revisa o conceito de estrutura {nivel}.",
            f"Entre os níveis de organização proteica encontra-se a "
            f"estrutura {nivel}.",
        ]
    # Nenhum comando termina em preposição: as definições são
    # sintagmas nominais com artigo ("a velocidade de dobramento"), e
    # "corresponde a: a velocidade" produz "a a".
        COMANDOS = [
            "Assinale a alternativa que a define corretamente.",
            "Ela é definida como:",
            "Qual a definição correta?",
            "Assinale a alternativa com a definição correta.",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = descricao
        distratores = [e[1] for e in ESTRUTURA_PROTEICA if e[1] != descricao]
        distratores += [
            "a proporção entre aminoácidos polares e apolares na cadeia",
            "a velocidade de dobramento da cadeia após a síntese",
        ]

    rng.shuffle(distratores)
    explicacao = (
        f"A estrutura {nivel} corresponde {_com_preposicao('a', descricao)}, "
        f"e é estabilizada "
        f"por {estabilizador}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (estrutura proteica)", rng)
    if q:
        q["_fato"] = f"estrutura:{nivel}"
    return q


def gerar_estabilizacao_proteica(rng):
    """O que estabiliza determinado nível de estrutura?"""
    nivel, descricao, estabilizador = rng.choice(ESTRUTURA_PROTEICA)

    CENARIOS = [
        f"A estrutura {nivel} de uma proteína corresponde "
        f"{_com_preposicao('a', descricao)}.",
        f"Considere a estabilização da estrutura {nivel} de uma proteína.",
        f"Cada nível de organização proteica é mantido por interações "
        f"específicas. Considere a estrutura {nivel}.",
        f"A manutenção da estrutura {nivel} depende de interações "
        f"químicas definidas.",
        f"Um experimento de desnaturação avalia o que sustenta a "
        f"estrutura {nivel} de uma proteína.",
        f"Ao estudar a organização proteica, analisa-se o que mantém a "
        f"estrutura {nivel}.",
        f"A estabilidade da estrutura {nivel} decorre de um tipo "
        f"específico de interação.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica o que a estabiliza.",
        "Ela é estabilizada por:",
        "Qual interação a mantém?",
        "Assinale a alternativa com o fator estabilizador correto.",
        "Sua estabilização decorre de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = estabilizador
    distratores = [e[2] for e in ESTRUTURA_PROTEICA if e[2] != estabilizador]
    distratores += [
        "ligações glicosídicas entre resíduos de açúcar",
        "interações eletrostáticas com íons metálicos do meio",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"A estrutura {nivel} — {descricao} — é estabilizada por "
        f"{estabilizador}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (estrutura proteica)", rng)
    if q:
        q["_fato"] = f"estrutura:{nivel}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — VIAS METABÓLICAS
# ══════════════════════════════════════════════════════════

def gerar_via_natureza(rng):
    """A via é anabólica ou catabólica?"""
    via, via_art, natureza, local, funcao = rng.choice(VIAS_METABOLICAS)

    CENARIOS = [
        f"{_inicial_maiuscula(via_art)} consiste na {funcao}.",
        f"Considere a via metabólica denominada {via}.",
        f"Um estudante classifica as vias metabólicas quanto à sua "
        f"natureza e analisa {via_art}.",
        f"Entre as vias do metabolismo intermediário encontra-se {via_art}.",
    ]
    # Sem pronome: o referente é a via, e "o ciclo da ureia" é
    # masculino. "Assinale a alternativa que A classifica" quebra ali.
    COMANDOS = [
        "Quanto à sua natureza, essa via é:",
        "Assinale a alternativa que classifica essa via corretamente.",
        "Trata-se de uma via:",
        "Quanto à natureza, classifica-se como via:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # "anabólica" tem 9 caracteres; os distratores tinham até 66. Marcar
    # sempre a alternativa mais curta acertava 68% destas questões.
    #
    # Agora toda alternativa é "classificação + o que a define", e o par
    # trocado (anabólica que degrada, catabólica que sintetiza) obriga a
    # saber qual rótulo corresponde a qual comportamento — que é
    # exatamente o que a questão cobra.
    CLASSIFICA = {
        "anabólica":  "anabólica, que sintetiza e consome energia",
        "catabólica": "catabólica, que degrada e libera energia",
    }
    TROCADA = {
        "anabólica":  "anabólica, que degrada e libera energia",
        "catabólica": "catabólica, que sintetiza e consome energia",
    }
    outra = "catabólica" if natureza == "anabólica" else "anabólica"
    correta = CLASSIFICA[natureza]
    distratores = [
        CLASSIFICA[outra],
        TROCADA[natureza],
        TROCADA[outra],
        "anfibólica, que sintetiza e degrada ao mesmo tempo",
        "anaplerótica, que repõe intermediários do ciclo",
        "fermentativa, que dispensa oxigênio",
    ]

    explicacao = (
        f"{_inicial_maiuscula(via_art)} é uma via {natureza}, pois consiste na {funcao}. "
        f"Ocorre em: {local}. "
    )
    if natureza == "anabólica":
        explicacao += "Vias anabólicas SINTETIZAM moléculas e consomem energia."
    else:
        explicacao += "Vias catabólicas DEGRADAM moléculas e liberam energia."
    q = _montar(enunciado, correta, distratores, explicacao,
                "Bioquímica (vias metabólicas)", rng)
    if q:
        q["_fato"] = f"via:{via}"
    return q


def gerar_via_funcao(rng):
    """Qual a função de determinada via metabólica?"""
    via, via_art, natureza, local, funcao = rng.choice(VIAS_METABOLICAS)

    CENARIOS = [
        f"Considere a via metabólica denominada {via}.",
        f"{_inicial_maiuscula(via_art)} é uma via {natureza} do metabolismo intermediário.",
        f"Um estudante revisa o papel {_com_preposicao('de', via_art)} "
        f"no metabolismo.",
        f"Entre as vias metabólicas do organismo encontra-se {via_art}.",
        f"{_inicial_maiuscula(via_art)} ocorre no seguinte compartimento: {local}.",
    ]
    # Mesmo cuidado: "a via" é sempre feminino, mas o nome dela pode
    # ser masculino ("o ciclo da ureia").
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função.",
        "Essa via consiste na:",
        "Qual a função dessa via?",
        "Assinale a alternativa que descreve essa via corretamente.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [v[4] for v in VIAS_METABOLICAS if v[4] != funcao]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(via_art)} consiste na {funcao}. É uma via {natureza} e ocorre "
        f"em: {local}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Bioquímica (vias metabólicas)", rng)
    if q:
        q["_fato"] = f"via:{via}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_BIOQUIMICA = {
    "etapa_local":      gerar_etapa_local,
    "etapa_produtos":   gerar_etapa_produtos,
    "etapa_sequencia":  gerar_etapa_sequencia,
    "enzima_reacao":    gerar_enzima_reacao,
    "ponto_regulacao":  gerar_ponto_regulacao,
    "estrutura_proteica": gerar_estrutura_proteica,
    "estabilizacao":      gerar_estabilizacao_proteica,
    "via_natureza":       gerar_via_natureza,
    "via_funcao":         gerar_via_funcao,
}

TOPICOS_BIOQUIMICA = {
    "respiracao_celular": [
        "etapa_local",
        "etapa_produtos",
        "etapa_sequencia",
    ],
    "glicolise": [
        "enzima_reacao",
        "ponto_regulacao",
    ],
    "proteinas": [
        "estrutura_proteica",
        "estabilizacao",
    ],
    "vias_metabolicas": [
        "via_natureza",
        "via_funcao",
    ],
}

PALAVRAS_CHAVE = {
    "etapa_local":     ["respiracao celular", "glicolise", "ciclo de krebs",
                        "cadeia respiratoria", "fosforilacao oxidativa",
                        "mitocondria", "acido citrico"],
    "etapa_produtos":  ["respiracao celular", "glicolise", "ciclo de krebs",
                        "nadh", "fadh2", "acetil-coa", "acetil coa"],
    "etapa_sequencia": ["respiracao celular", "glicolise", "ciclo de krebs",
                        "cadeia respiratoria", "metabolismo energetico"],
    "enzima_reacao":   ["glicolise", "hexoquinase", "fosfofrutoquinase",
                        "piruvato quinase", "enzimas da glicolise"],
    "ponto_regulacao": ["glicolise", "fosfofrutoquinase", "pfk-1", "pfk1",
                        "regulacao metabolica", "enzima reguladora",
                        "enzimas reguladoras"],
    "estrutura_proteica": ["estrutura proteica", "proteina", "proteinas",
                           "aminoacido", "aminoacidos", "helice alfa",
                           "folha beta", "peptidica", "polipeptidica"],
    "estabilizacao":      ["estrutura proteica", "proteina", "proteinas",
                           "ponte dissulfeto", "pontes dissulfeto",
                           "ponte de hidrogenio", "desnaturacao"],
    "via_natureza":       ["anabolismo", "catabolismo", "gliconeogenese",
                           "glicogenese", "glicogenolise", "beta-oxidacao",
                           "lipogenese", "cetogenese", "ciclo da ureia",
                           "pentoses-fosfato", "metabolismo intermediario"],
    "via_funcao":         ["gliconeogenese", "glicogenese", "glicogenolise",
                           "beta-oxidacao", "lipogenese", "cetogenese",
                           "ciclo da ureia", "pentoses-fosfato",
                           "corpos cetonicos", "metabolismo intermediario"],
}

CHAVES_GENERICAS = {
    "etapa", "etapas", "local", "produtos", "enzima", "enzimas",
    "reacao", "regulacao", "via", "vias", "metabolismo", "celula",
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
    """Gera um lote de questões de bioquímica."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_BIOQUIMICA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_BIOQUIMICA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_BIOQUIMICA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_BIOQUIMICA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Sorteio proporcional ao material — ver comentário equivalente em
    # gerador_anatomia.gerar_lote.
    LASTRO = {
        "etapa_local":     len(ETAPAS_RESPIRACAO),
        "etapa_produtos":  len(ETAPAS_RESPIRACAO) - 1,
        "etapa_sequencia": len(ETAPAS_RESPIRACAO),
        "enzima_reacao":   len(ENZIMAS_GLICOLISE),
        "ponto_regulacao": 2,          # dois modos de pergunta
        "estrutura_proteica": len(ESTRUTURA_PROTEICA),
        "estabilizacao":      len(ESTRUTURA_PROTEICA),
        "via_natureza":       len(VIAS_METABOLICAS),
        "via_funcao":         len(VIAS_METABOLICAS),
    }
    # O teto de 3 era baixo demais: com 8 vias metabólicas e 3 etapas de
    # respiração, os templates de via precisam aparecer bem mais que os
    # de etapa para que os dois esgotem juntos.
    # A fila precisa ser INTERCALADA, não agrupada. Estender com
    # [nome] * peso colocava as repetições lado a lado, e um lote de 10
    # consumia só os primeiros templates da lista — nunca chegava às
    # vias metabólicas, que têm o maior lastro.
    #
    # Aqui as rodadas se alternam: uma passagem por todos os templates,
    # depois outra pelos que ainda têm lastro, e assim por diante.
    pesos = {n: max(1, min(round(LASTRO.get(n, 3) / 2), 5))
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
        q = TEMPLATES_BIOQUIMICA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        # Um mesmo fato não rende duas questões: perguntar o local e os
        # produtos do ciclo de Krebs é perguntar duas vezes sobre a mesma
        # linha da tabela.
        # O veto de fato repetido só cede quando as tentativas estão
        # quase esgotadas. Com 0.7, ele cedia cedo demais em lotes
        # pequenos: um lote de 10 tem 120 tentativas, e o veto caía já
        # na 84ª — antes de o rodízio ter percorrido todos os fatos.
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
    print("  GERADOR DE BIOQUÍMICA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
