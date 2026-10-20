"""
=============================================================
  GERADOR DE EMBRIOLOGIA
=============================================================
  Questões de embriologia geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Folhetos germinativos e seus derivados
    ✅ Cronologia do desenvolvimento
    ✅ Origem dupla e outras armadilhas clássicas
    ❌ Malformações e conduta pré-natal

  VERIFICAÇÃO DAS FONTES

  Registradas em embriologia/_fontes.md, incluindo uma
  imprecisão: uma fonte afirma que a blástula já contém o
  ectoderma. Na embriologia médica, os três folhetos derivam
  do EPIBLASTO durante a gastrulação.

  USO:
      from gerador_embriologia import gerar_lote, gerar_para_api
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

# ── Folhetos germinativos ──
#
# Fontes: Moore, Embriologia Clínica; Wikipédia (Folheto embrionário);
# Biologia Net; Toda Matéria.
#
# (folheto, com_artigo, posição, derivados, observação)
FOLHETOS = [
    ("ectoderma", "o ectoderma", "o mais externo",
     ["o sistema nervoso central e periférico",
      "a epiderme e seus anexos, como pelos e unhas",
      "o esmalte dentário",
      "a adeno-hipófise e a neuro-hipófise",
      "o cristalino e a retina",
      "o epitélio da boca e do ânus"],
     "a crista neural, derivada dele, origina os melanócitos, a medula "
     "da suprarrenal e os gânglios nervosos"),

    ("mesoderma", "o mesoderma", "o intermediário",
     ["a musculatura esquelética, lisa e cardíaca",
      "o coração, os vasos sanguíneos e o sangue",
      "os ossos e as cartilagens",
      "a derme e o tecido conjuntivo",
      "os rins e os ureteres",
      "as gônadas e os ductos genitais",
      "o córtex da glândula suprarrenal",
      "o baço",
      "a pleura, o pericárdio e o peritônio"],
     "é o último folheto a se formar, situado entre os outros dois"),

    ("endoderma", "o endoderma", "o mais interno",
     ["o revestimento epitelial do tubo digestório, exceto boca e ânus",
      "o fígado e o pâncreas",
      "o revestimento epitelial da traqueia, dos brônquios e dos alvéolos",
      "a tireoide, as paratireoides e o timo",
      "o revestimento da bexiga e da uretra",
      "as tonsilas"],
     "origina o revestimento EPITELIAL do trato respiratório; o estroma "
     "e a musculatura vêm do mesoderma"),
]

# ── Estruturas de origem dupla ou contraintuitiva ──
#
# (estrutura, origem, por_que, armadilha)
ORIGENS_ESPECIAIS = [
    ("o córtex da glândula suprarrenal", "mesoderma",
     "deriva do epitélio celômico",
     "a suprarrenal tem origem DUPLA: o córtex é mesodérmico e a "
     "medula vem da crista neural"),
    ("a medula da glândula suprarrenal", "ectoderma",
     "deriva da crista neural, cujas células migram para o interior "
     "da glândula",
     "a suprarrenal tem origem DUPLA: o córtex é mesodérmico e a "
     "medula vem da crista neural"),
    ("o revestimento epitelial dos alvéolos pulmonares", "endoderma",
     "o broto respiratório surge do intestino anterior",
     "todo o revestimento epitelial do trato respiratório é "
     "endodérmico, apesar de o sistema parecer mesodérmico"),
    ("o esmalte dentário", "ectoderma",
     "origina-se do órgão do esmalte, de natureza epitelial",
     "é o único tecido dentário de origem ectodérmica — dentina, "
     "cemento e polpa vêm da crista neural"),
    ("o epitélio da cavidade oral", "ectoderma",
     "forma-se a partir do estomodeu, uma invaginação ectodérmica",
     "boca e ânus são ectodérmicos, embora o restante do tubo "
     "digestório seja endodérmico"),
    ("os melanócitos da epiderme", "ectoderma",
     "derivam da crista neural, e não da camada basal da epiderme",
     "apesar de residirem na epiderme, os melanócitos têm origem "
     "na crista neural"),
]

# ── Cronologia do desenvolvimento ──
#
# (ordem, evento, momento, local)
CRONOLOGIA = [
    (1, "a fecundação", "no dia zero", "a ampola da tuba uterina"),
    (2, "a clivagem", "entre o primeiro e o terceiro dia", "a tuba uterina"),
    (3, "a formação da mórula", "por volta do quarto dia",
     "a entrada do útero"),
    (4, "a formação do blastocisto", "por volta do quinto dia",
     "a cavidade uterina"),
    (5, "o início da implantação", "entre o sexto e o sétimo dia",
     "o endométrio"),
    (6, "a gastrulação", "na terceira semana", "o disco embrionário"),
    (7, "a neurulação", "entre a terceira e a quarta semana",
     "o disco embrionário"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _com_preposicao(prep: str, sintagma: str) -> str:
    """Junta preposição e sintagma fazendo a CONTRAÇÃO."""
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "): "à ", ("a", "o "): "ao ",
        ("a", "as "): "às ", ("a", "os "): "aos ",
        ("de", "a "): "da ", ("de", "o "): "do ",
        ("de", "as "): "das ", ("de", "os "): "dos ",
        ("em", "a "): "na ", ("em", "o "): "no ",
        ("em", "as "): "nas ", ("em", "os "): "nos ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


def _inicial_maiuscula(t: str) -> str:
    """Eleva só a primeira letra, preservando o resto."""
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
#  TEMPLATES — FOLHETOS GERMINATIVOS
# ══════════════════════════════════════════════════════════

def gerar_derivado_por_folheto(rng):
    """Qual estrutura deriva de determinado folheto?"""
    folheto, art, posicao, derivados, obs = rng.choice(FOLHETOS)
    derivado = rng.choice(derivados)

    CENARIOS = [
        f"Considere {art}, {posicao} dos folhetos germinativos.",
        f"Durante a organogênese, {art} dá origem a diversas estruturas.",
        f"Um estudante revisa os derivados {_com_preposicao('de', art)}.",
        f"Entre os três folhetos germinativos, {art} é "
        f"{posicao}.",
        f"A diferenciação {_com_preposicao('de', art)} origina tecidos "
        f"e órgãos específicos.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta uma estrutura derivada "
        "desse folheto.",
        "Qual estrutura deriva desse folheto?",
        "Uma de suas derivações é:",
        "Assinale a alternativa com um de seus derivados.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = derivado
    distratores = []
    for f in FOLHETOS:
        if f[0] == folheto:
            continue
        distratores.extend(f[3])
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(derivado)} deriva {_com_preposicao('de', art)}, "
        f"{posicao} dos folhetos germinativos. Convém lembrar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Embriologia (folhetos germinativos)", rng)
    if q:
        q["_fato"] = f"folheto:{folheto}"
    return q


def gerar_folheto_por_derivado(rng):
    """De qual folheto deriva determinada estrutura?"""
    folheto, art, posicao, derivados, obs = rng.choice(FOLHETOS)
    derivado = rng.choice(derivados)

    CENARIOS = [
        f"Considere a origem embriológica da seguinte estrutura: "
        f"{derivado}.",
        f"Durante a organogênese, forma-se a seguinte estrutura: "
        f"{derivado}.",
        f"Um estudante investiga de que folheto germinativo provém "
        f"a seguinte estrutura: {derivado}.",
        f"A seguinte estrutura tem origem em um dos folhetos "
        f"germinativos: {derivado}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica seu folheto de origem.",
        "Essa estrutura deriva do:",
        "Qual folheto germinativo a origina?",
        "Assinale a alternativa com o folheto correspondente.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = folheto
    distratores = [f[0] for f in FOLHETOS if f[0] != folheto]
    distratores += ["trofoblasto", "epiblasto residual",
                    "mesênquima extraembrionário", "âmnio"]

    explicacao = (
        f"{_inicial_maiuscula(derivado)} deriva "
        f"{_com_preposicao('de', art)}, {posicao} dos folhetos. "
        f"Vale notar que {obs}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Embriologia (folhetos germinativos)", rng)
    if q:
        q["_fato"] = f"folheto:{folheto}"
    return q


def gerar_origem_especial(rng):
    """
    Estruturas cuja origem embriológica contraria a intuição.

    A suprarrenal, com córtex mesodérmico e medula ectodérmica, é o
    exemplo mais cobrado.
    """
    estrutura, origem, por_que, armadilha = rng.choice(ORIGENS_ESPECIAIS)

    CENARIOS = [
        f"Considere a origem embriológica da seguinte estrutura: "
        f"{estrutura}.",
        f"Um estudante se surpreende ao estudar a origem embriológica "
        f"da seguinte estrutura: {estrutura}.",
        f"Entre as estruturas cuja origem embriológica costuma gerar "
        f"dúvida está a seguinte: {estrutura}.",
        f"A origem embriológica da seguinte estrutura é cobrada com "
        f"frequência: {estrutura}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica seu folheto de origem.",
        "Essa estrutura deriva do:",
        "Qual folheto germinativo a origina?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = origem
    distratores = [f[0] for f in FOLHETOS if f[0] != origem]
    distratores += ["trofoblasto", "mesênquima extraembrionário",
                    "saco vitelínico", "âmnio"]

    explicacao = (
        f"{_inicial_maiuscula(estrutura)} deriva do {origem}, pois "
        f"{por_que}. Convém lembrar que {armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Embriologia (origens embriológicas)", rng)
    if q:
        # O veto inclui a RESPOSTA: três estruturas distintas podem ter
        # a mesma origem (ectoderma), e três questões seguidas com o
        # mesmo gabarito parecem repetidas ao aluno.
        q["_fato"] = f"especial:{estrutura}|{origem}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — CRONOLOGIA
# ══════════════════════════════════════════════════════════

def gerar_cronologia_momento(rng):
    """Quando ocorre determinado evento do desenvolvimento?"""
    ordem, evento, momento, local = rng.choice(CRONOLOGIA)

    CENARIOS = [
        f"Considere o seguinte evento do desenvolvimento embrionário: "
        f"{evento}.",
        f"No desenvolvimento humano inicial ocorre o seguinte evento: "
        f"{evento}.",
        f"Um estudante revisa a cronologia do desenvolvimento e chega "
        f"ao seguinte evento: {evento}.",
        f"Entre os marcos do desenvolvimento embrionário está o "
        f"seguinte: {evento}.",
    ]
    COMANDOS = [
        "Esse evento ocorre:",
        "Assinale a alternativa que indica quando esse evento ocorre.",
        "Em que momento esse evento se dá?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # Os momentos podem SE SOBREPOR: "na terceira semana" está contido
    # em "entre a terceira e a quarta semana". Quem marca o intervalo
    # não está errado, e a questão fica ambígua.
    #
    # A comparação extrai os ordinais de cada expressão e descarta o
    # distrator cujo intervalo intersecta o da resposta certa.
    ORDINAIS = {
        "primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4,
        "quinto": 5, "sexto": 6, "sétimo": 7, "oitavo": 8,
        "terceira": 3, "quarta": 4, "quinta": 5, "sexta": 6,
        "décima segunda": 12,
    }

    def _intervalo(texto):
        """Ordinais mencionados, com a unidade (dia ou semana)."""
        t = texto.lower()
        unidade = "semana" if "semana" in t else "dia"
        nums = [v for k, v in ORDINAIS.items()
                if re.search(r'(?<![a-zà-ÿ])' + k + r'(?![a-zà-ÿ])', t)]
        if "zero" in t:
            nums.append(0)
        return (unidade, min(nums), max(nums)) if nums else None

    def _intersecta(a, b):
        ia, ib = _intervalo(a), _intervalo(b)
        if not ia or not ib or ia[0] != ib[0]:
            return False
        return ia[1] <= ib[2] and ib[1] <= ia[2]

    # A verificação vale entre TODAS as alternativas, não só contra o
    # gabarito: com "por volta do quinto dia" como resposta, os
    # distratores "na terceira semana" e "entre a terceira e a quarta
    # semana" entravam juntos e se sobrepunham entre si.
    correta = momento
    candidatos = [c[2] for c in CRONOLOGIA if c[2] != momento]
    candidatos += ["na décima segunda semana", "no segundo trimestre"]

    distratores = []
    for cand in candidatos:
        if _intersecta(cand, correta):
            continue
        if any(_intersecta(cand, d) for d in distratores):
            continue
        distratores.append(cand)

    explicacao = (
        f"{_inicial_maiuscula(evento)} ocorre {momento}, "
        f"{_com_preposicao('em', local)}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Embriologia (cronologia do desenvolvimento)", rng)
    if q:
        q["_fato"] = f"crono:{evento}"
    return q


def gerar_cronologia_local(rng):
    """Onde ocorre determinado evento?"""
    ordem, evento, momento, local = rng.choice(CRONOLOGIA)

    CENARIOS = [
        f"Considere o seguinte evento do desenvolvimento: {evento}, "
        f"que ocorre {momento}.",
        f"Um estudante localiza anatomicamente o seguinte evento: "
        f"{evento}.",
        f"No desenvolvimento humano inicial, {evento} tem local "
        f"definido.",
        f"Entre os eventos do desenvolvimento inicial encontra-se "
        f"{evento}.",
    ]
    # Nenhum comando termina em preposição solta: os locais trazem
    # artigo ("a ampola"), e "ocorre em: a ampola" fica quebrado.
    # Sem pronome: o referente é o evento, e o gênero varia — "a
    # fecundação" contra "o início da implantação". "onde ELE acontece"
    # quebra num, "onde ELA acontece" quebra no outro.
    COMANDOS = [
        "Assinale a alternativa que indica onde esse evento acontece.",
        "Esse evento tem como local:",
        "Qual o local desse evento?",
        "Assinale a alternativa com o local correto.",
        "O local correspondente é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # Um distrator que CONTÉM a resposta certa, ou está contido nela,
    # torna a questão ambígua: "a tuba uterina" não é errado quando a
    # resposta é "a ampola da tuba uterina" — a ampola fica na tuba.
    #
    # O filtro vale para qualquer par com essa relação, não só este.
    def _sobrepoe(a, b):
        na = a.lower().removeprefix("a ").removeprefix("o ")
        nb = b.lower().removeprefix("a ").removeprefix("o ")
        return na in nb or nb in na

    # A sobreposição precisa ser verificada entre TODAS as alternativas,
    # não só contra a resposta certa: com "a entrada do útero" como
    # gabarito, os distratores "a tuba uterina" e "a ampola da tuba
    # uterina" entravam juntos e se sobrepunham entre si.
    correta = local
    candidatos = [c[3] for c in CRONOLOGIA if c[3] != local]
    candidatos += ["o colo uterino", "a cavidade peritoneal",
                   "o miométrio", "o ovário"]

    distratores = []
    for cand in candidatos:
        if _sobrepoe(cand, correta):
            continue
        if any(_sobrepoe(cand, d) for d in distratores):
            continue
        distratores.append(cand)

    explicacao = (
        f"{_inicial_maiuscula(evento)} ocorre "
        f"{_com_preposicao('em', local)}, {momento}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Embriologia (cronologia do desenvolvimento)", rng)
    if q:
        q["_fato"] = f"crono:{evento}"
    return q


def gerar_periodo_teratogenico(rng):
    """
    Período embrionário versus fetal, e a janela de sensibilidade a
    teratógenos.

    É o ponto de maior relevância clínica da disciplina.
    """
    modo = rng.choice(["janela", "delimitacao"])

    if modo == "janela":
        CENARIOS = [
            "A exposição a agentes teratogênicos não produz o mesmo "
            "efeito em qualquer momento da gestação.",
            "O risco de malformação estrutural varia conforme o momento "
            "da exposição a um teratógeno.",
            "Uma gestante pergunta em que fase da gestação a exposição "
            "a determinado agente traria maior risco de malformação.",
            "A suscetibilidade do embrião a agentes teratogênicos não é "
            "constante ao longo da gestação.",
            "Ao orientar uma gestante sobre o uso de medicamentos, "
            "considera-se a fase de maior vulnerabilidade do embrião.",
            "A janela de maior risco teratogênico coincide com uma fase "
            "específica do desenvolvimento.",
            "Um estudante revisa em que período a exposição a "
            "teratógenos causa mais malformações estruturais.",
            "O momento da exposição a um agente teratogênico determina "
            "a gravidade do dano estrutural.",
        ]
        # Os comandos e as alternativas precisam concordar em REGÊNCIA.
        # Os distratores foram escritos como sintagmas nominais puros
        # ("as duas primeiras semanas"), então o comando que exige
        # preposição a traz explicitamente.
        # NENHUM comando exige preposição, porque as alternativas
        # misturam sintagmas nominais ("as duas primeiras semanas") e
        # sintagmas preposicionados ("da terceira à oitava semana") —
        # os intervalos são naturalmente expressos com "de...a".
        #
        # Comandos terminados em "é:" ou em pergunta aceitam os dois.
        COMANDOS = [
            "O período de maior sensibilidade é:",
            "Assinale a alternativa que indica esse período.",
            "Qual o período de maior risco de malformação estrutural?",
            "Assinale a alternativa com o período correspondente.",
            "Esse período de maior risco é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "da terceira à oitava semana, durante a organogênese"
        distratores = [
            "as duas primeiras semanas, antes da implantação",
            "da nona semana ao final da gestação, no período fetal",
            "o terceiro trimestre, quando o crescimento é mais rápido",
            "o momento do parto, pela exposição direta",
            "todo o período gestacional, com risco constante",
        ]
        explicacao = (
            "O período de maior sensibilidade a teratógenos vai da "
            "TERCEIRA à OITAVA semana, quando ocorre a organogênese. "
            "Antes disso, nas duas primeiras semanas, vigora a lei do "
            "tudo ou nada: ou o dano é reparado, ou o embrião não "
            "sobrevive. Depois da oitava semana, no período fetal, os "
            "órgãos já estão formados, e o risco passa a ser de "
            "alterações funcionais e de crescimento, não de malformação "
            "estrutural."
        )
    else:
        alvo = rng.choice(["embrionário", "fetal"])
        CENARIOS = [
            f"O desenvolvimento pré-natal divide-se em períodos com "
            f"características próprias. Considere o período {alvo}.",
            f"Um estudante revisa a delimitação do período {alvo}.",
            f"Entre os períodos do desenvolvimento pré-natal está o "
            f"período {alvo}.",
            f"O período {alvo} tem delimitação temporal precisa.",
            f"Ao datar uma gestação, é preciso saber quando começa e "
            f"termina o período {alvo}.",
            f"Uma prova de embriologia cobra a delimitação do período "
            f"{alvo}.",
            f"O período {alvo} do desenvolvimento humano ocupa um "
            f"intervalo definido da gestação.",
        ]
        COMANDOS = [
            "Esse período compreende:",
            "Assinale a alternativa que o delimita corretamente.",
            "Qual sua delimitação temporal?",
            "Assinale a alternativa com a delimitação correta.",
            "Sua delimitação é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        if alvo == "embrionário":
            correta = "da terceira à oitava semana"
            explicacao = (
                "O período EMBRIONÁRIO vai da terceira à oitava semana e "
                "corresponde à organogênese — é quando os órgãos se "
                "formam, e por isso é o de maior sensibilidade a "
                "teratógenos. O período FETAL começa na nona semana e "
                "caracteriza-se por crescimento e maturação."
            )
        else:
            correta = "da nona semana até o nascimento"
            explicacao = (
                "O período FETAL vai da nona semana até o nascimento e "
                "caracteriza-se por crescimento e maturação dos órgãos "
                "já formados. O período EMBRIONÁRIO, da terceira à "
                "oitava semana, é o da organogênese."
            )
        distratores = [
            "da terceira à oitava semana",
            "da nona semana até o nascimento",
            "das duas primeiras semanas após a fecundação",
            "do segundo ao sexto mês de gestação",
            "das últimas quatro semanas de gestação",
        ]
        distratores = [d for d in distratores if d != correta]

    q = _montar(enunciado, correta, distratores, explicacao,
                "Embriologia (períodos do desenvolvimento)", rng)
    if q:
        q["_fato"] = f"periodo:{modo}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_EMBRIOLOGIA = {
    "derivado_por_folheto": gerar_derivado_por_folheto,
    "folheto_por_derivado": gerar_folheto_por_derivado,
    "origem_especial":      gerar_origem_especial,
    "crono_momento":        gerar_cronologia_momento,
    "crono_local":          gerar_cronologia_local,
    "periodo_teratogenico": gerar_periodo_teratogenico,
}

TOPICOS_EMBRIOLOGIA = {
    "folhetos": [
        "derivado_por_folheto",
        "folheto_por_derivado",
        "origem_especial",
    ],
    "desenvolvimento": [
        "crono_momento",
        "crono_local",
        "periodo_teratogenico",
    ],
}

PALAVRAS_CHAVE = {
    "derivado_por_folheto": ["folheto germinativo", "folhetos germinativos",
                             "folheto embrionario", "ectoderma", "mesoderma",
                             "endoderma", "ectoderme", "mesoderme",
                             "endoderme", "organogenese"],
    "folheto_por_derivado": ["folheto germinativo", "folhetos germinativos",
                             "ectoderma", "mesoderma", "endoderma",
                             "organogenese", "derivados embrionarios"],
    "origem_especial":      ["crista neural", "suprarrenal", "adrenal",
                             "ectoderma", "mesoderma", "endoderma",
                             "origem embriologica"],
    "crono_momento":        ["gastrulacao", "clivagem", "blastocisto",
                             "morula", "implantacao", "neurulacao",
                             "fecundacao", "desenvolvimento embrionario"],
    "crono_local":          ["gastrulacao", "clivagem", "blastocisto",
                             "implantacao", "tuba uterina", "endometrio",
                             "fecundacao"],
    "periodo_teratogenico": ["teratogeno", "teratogenos", "teratogenico",
                             "periodo embrionario", "periodo fetal",
                             "organogenese", "malformacao"],
}

CHAVES_GENERICAS = {
    "folheto", "folhetos", "estrutura", "origem", "periodo", "evento",
    "local", "desenvolvimento", "embriao", "celula", "celulas",
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
    """Gera um lote de questões de embriologia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_EMBRIOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_EMBRIOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_EMBRIOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_EMBRIOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Fila INTERCALADA, proporcional ao material.
    LASTRO = {
        "derivado_por_folheto": sum(len(f[3]) for f in FOLHETOS),
        "folheto_por_derivado": sum(len(f[3]) for f in FOLHETOS),
        "origem_especial":      len(ORIGENS_ESPECIAIS),
        "crono_momento":        len(CRONOLOGIA),
        "crono_local":          len(CRONOLOGIA),
        "periodo_teratogenico": 3,      # janela + dois períodos
    }
    # O divisor 6 achatava os pesos: com 21 derivados e 7 eventos de
    # cronologia, os dois templates de folheto ficavam com peso 4 e os
    # de cronologia com 1, mas o veto de fato é por FOLHETO (só três) —
    # então eles esgotam rápido. O peso reflete quantos FATOS DISTINTOS
    # o veto reconhece, não quantas variações o template produz.
    LASTRO_POR_FATO = {
        "derivado_por_folheto": len(FOLHETOS),          # veto por folheto
        "folheto_por_derivado": len(FOLHETOS),
        "origem_especial":      len(ORIGENS_ESPECIAIS),
        "crono_momento":        len(CRONOLOGIA),
        "crono_local":          len(CRONOLOGIA),
        "periodo_teratogenico": 2,                      # veto por modo
    }
    pesos = {n: max(1, min(round(LASTRO_POR_FATO.get(n, 3) / 3), 4))
             for n in disponiveis}
    fila = []
    for rodada in range(max(pesos.values())):
        for nome in disponiveis:
            if pesos[nome] > rodada:
                fila.append(nome)
    if not fila:
        fila = list(disponiveis)

    from collections import Counter
    questoes, tentativas, limite = [], 0, quantidade * 12
    vistos, fatos_usados = set(), set()
    respostas = Counter()

    # A posição na fila avança a cada TENTATIVA, não a cada questão
    # aceita. Com len(questoes), o laço ficava preso na posição de um
    # template cujas questões estavam todas vetadas, até esgotar as
    # tentativas — e então o veto afrouxava e todas entravam de uma vez.
    posicao = 0
    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = fila[posicao % len(fila)]
        posicao += 1
        q = TEMPLATES_EMBRIOLOGIA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        fato = q.get("_fato")
        if fato and fato in fatos_usados and tentativas < limite * 0.9:
            continue

        # Veto por RESPOSTA, além do veto por fato. Três estruturas
        # distintas podem ter a mesma origem embriológica, e três
        # questões seguidas com gabarito "ectoderma" parecem repetidas
        # ainda que os fatos sejam diferentes.
        #
        # O teto é 2: duas questões com a mesma resposta num lote de
        # dez é tolerável; três já chama atenção.
        gab_txt = q["alternativas"].get(q.get("gabarito"), "")
        if (gab_txt and respostas[gab_txt] >= 2
                and tentativas < limite * 0.85):
            continue

        vistos.add(q["enunciado"])
        if fato:
            fatos_usados.add(fato)
        if gab_txt:
            respostas[gab_txt] += 1
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
    print("  GERADOR DE EMBRIOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
