"""
=============================================================
  GERADOR DE IMUNOLOGIA
=============================================================
  Questões de imunologia geradas proceduralmente, sem depender
  de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Classificação de Gell e Coombs — mecanismo, mediador,
       tempo de instalação, exemplos
    ✅ Imunoglobulinas — estrutura, localização, função
    ✅ Imunidade inata versus adaptativa
    ❌ Conduta diante de reação alérgica, dose de fármaco

  VERIFICAÇÃO DAS FONTES

  Registradas em imunologia/_fontes.md. As fontes principais
  são o Manual MSD (profissional) e a Revista Portuguesa de
  Imunoalergologia, cruzadas com material universitário.

  USO:
      from gerador_imunologia import gerar_lote, gerar_para_api
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

# ── Hipersensibilidade: classificação de Gell e Coombs ──
#
# Fontes: Manual MSD (profissional); Revista Portuguesa de
# Imunoalergologia (SPAIC); microbiologybook.org (USC).
#
# (tipo, denominação, mediador, mecanismo, tempo, exemplos)
HIPERSENSIBILIDADE = [
    ("I", "imediata", "IgE",
     "ligação do antígeno à IgE fixada em mastócitos e basófilos, com "
     "liberação de histamina e outros mediadores",
     "menos de uma hora",
     ["anafilaxia", "asma alérgica", "rinite alérgica", "urticária aguda"]),

    ("II", "citotóxica", "IgG e IgM",
     "ligação do anticorpo a antígeno presente na superfície da célula, "
     "com ativação do complemento e citotoxicidade celular",
     "variável, definida pelo mecanismo e não pelo relógio",
     ["anemia hemolítica autoimune", "síndrome de Goodpasture",
      "tireoidite de Hashimoto", "reação transfusional por "
      "incompatibilidade ABO"]),

    ("III", "por imunocomplexos", "IgG",
     "formação de complexos antígeno-anticorpo circulantes que se "
     "depositam nos tecidos e ativam o complemento",
     "de duas a oito horas",
     ["doença do soro", "lúpus eritematoso sistêmico",
      "glomerulonefrite pós-estreptocócica", "vasculite leucocitoclástica"]),

    ("IV", "tardia", "linfócitos T",
     "ativação de linfócitos T e macrófagos, sem participação primária "
     "de anticorpos",
     "de 24 a 72 horas",
     ["teste tuberculínico de Mantoux", "dermatite de contato alérgica",
      "rejeição de transplante"]),
]

# ── Imunoglobulinas ──
#
# (classe, estrutura, local, função, particularidade)
# O campo `local` é um SINTAGMA NOMINAL puro, sem preposição: ele é
# encaixado em frases como "predomina em {local}", e trazer regência
# própria produzia "predomina em ligada à membrana de mastócitos".
IMUNOGLOBULINAS = [
    ("IgG", "monômero", "soro, onde corresponde a cerca de 75% do total",
     "resposta secundária, opsonização e ativação do complemento",
     "é a única classe que atravessa a placenta, conferindo imunidade "
     "passiva ao recém-nascido"),
    ("IgM", "pentâmero", "compartimento intravascular",
     "primeira classe a aparecer na resposta primária",
     "é a maior das imunoglobulinas e o ativador mais eficiente do "
     "complemento, mas não atravessa a placenta"),
    ("IgA", "dímero nas secreções",
     "secreções como saliva, lágrima, leite e superfícies mucosas",
     "defesa das superfícies mucosas",
     "é a imunoglobulina predominante no colostro"),
    ("IgE", "monômero", "membrana de mastócitos e basófilos",
     "mediação das reações alérgicas e defesa antiparasitária",
     "é a de menor concentração sérica"),
    ("IgD", "monômero", "membrana do linfócito B",
     "receptor de antígeno do linfócito B virgem",
     "atua como receptor no linfócito B que ainda não encontrou seu "
     "antígeno"),
]


# ── Células do sistema imune ──
#
# Fontes: Manual MSD (profissional), "Visão geral do sistema imunitário";
# Abbas, Imunologia Celular e Molecular.
#
# (célula, linhagem, função principal, particularidade)
# Cada célula traz o ARTIGO: "o neutrófilo" mas "a célula dendrítica".
CELULAS_IMUNES = [
    ("neutrófilo", "o neutrófilo", "inata",
     "fagocitose de bactérias e fungos",
     "é o leucócito mais abundante no sangue e o primeiro a chegar ao "
     "foco inflamatório agudo"),
    ("macrófago", "o macrófago", "inata",
     "fagocitose e apresentação de antígeno aos linfócitos T",
     "origina-se do monócito circulante ao migrar para o tecido"),
    ("célula dendrítica", "a célula dendrítica", "inata",
     "captura de antígeno e apresentação aos linfócitos T virgens",
     "é a apresentadora de antígeno mais eficiente, e faz a ponte entre "
     "imunidade inata e adaptativa"),
    ("célula natural killer", "a célula natural killer", "inata",
     "destruição de células infectadas por vírus e de células tumorais",
     "reconhece células que perderam a expressão de MHC de classe I, sem "
     "necessidade de sensibilização prévia"),
    ("eosinófilo", "o eosinófilo", "inata",
     "defesa contra helmintos e participação nas reações alérgicas",
     "seus grânulos contêm proteína básica principal, tóxica para "
     "parasitas"),
    ("basófilo", "o basófilo", "inata",
     "liberação de histamina nas reações de hipersensibilidade imediata",
     "é o leucócito menos abundante no sangue"),
    ("linfócito B", "o linfócito B", "adaptativa",
     "produção de anticorpos, após diferenciação em plasmócito",
     "matura-se na medula óssea e reconhece o antígeno em sua forma "
     "nativa"),
    ("linfócito T auxiliar", "o linfócito T auxiliar", "adaptativa",
     "coordenação da resposta imune por meio da secreção de citocinas",
     "expressa a molécula CD4 e reconhece antígeno apresentado por MHC "
     "de classe II"),
    ("linfócito T citotóxico", "o linfócito T citotóxico", "adaptativa",
     "destruição direta de células infectadas por vírus",
     "expressa a molécula CD8 e reconhece antígeno apresentado por MHC "
     "de classe I"),
    ("plasmócito", "o plasmócito", "adaptativa",
     "secreção de grandes quantidades de anticorpo",
     "é o estágio final de diferenciação do linfócito B e não expressa "
     "mais imunoglobulina de membrana"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

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
    Junta preposição e sintagma fazendo a CONTRAÇÃO.

    O fatiamento manual — d{art[1:]} — parecia equivalente, mas devolve
    o espaço junto e produz "d plasmócito". Esta função existe nos
    demais geradores do projeto pelo mesmo motivo.
    """
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
    """Eleva só a primeira letra, preservando nomes próprios."""
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


# ══════════════════════════════════════════════════════════
#  TEMPLATES — HIPERSENSIBILIDADE
# ══════════════════════════════════════════════════════════

def gerar_hs_por_exemplo(rng):
    """
    Dado um quadro clínico, a que tipo de hipersensibilidade corresponde?

    É o formato mais cobrado: o aluno precisa reconhecer o mecanismo por
    trás da manifestação, não recitar a tabela.
    """
    tipo, denom, mediador, mecanismo, tempo, exemplos = rng.choice(HIPERSENSIBILIDADE)
    exemplo = rng.choice(exemplos)

    CENARIOS = [
        f"Um paciente apresenta quadro compatível com {exemplo}.",
        f"A investigação de {exemplo} identifica mecanismo imunológico "
        f"subjacente.",
        f"Considere a fisiopatologia de {exemplo}.",
        f"Em uma aula de imunologia, discute-se o mecanismo de {exemplo}.",
        f"Entre as manifestações de hipersensibilidade encontra-se "
        f"{exemplo}.",
    ]
    COMANDOS = [
        "Segundo a classificação de Gell e Coombs, trata-se de "
        "hipersensibilidade do tipo:",
        "Assinale a alternativa que indica o tipo de hipersensibilidade "
        "envolvido.",
        "Esse quadro corresponde a hipersensibilidade do tipo:",
        "Qual o tipo de hipersensibilidade, segundo Gell e Coombs?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = f"tipo {tipo} ({denom})"
    distratores = [f"tipo {h[0]} ({h[1]})" for h in HIPERSENSIBILIDADE
                   if h[0] != tipo]
    distratores += [
        "tipo V (estimulatória por autoanticorpo)",
        "reação idiossincrásica, sem mecanismo imunológico",
    ]

    explicacao = (
        f"{exemplo.capitalize()} é hipersensibilidade do tipo {tipo} "
        f"({denom}), mediada por {mediador}. O mecanismo envolve "
        f"{mecanismo}, e a reação se instala em {tempo}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (hipersensibilidade)", rng)
    if q:
        q["_fato"] = f"hs:{tipo}"
    return q


def gerar_hs_mediador(rng):
    """Qual o mediador de determinado tipo de hipersensibilidade?"""
    tipo, denom, mediador, mecanismo, tempo, exemplos = rng.choice(HIPERSENSIBILIDADE)

    CENARIOS = [
        f"A hipersensibilidade do tipo {tipo}, segundo a classificação "
        f"de Gell e Coombs, é também denominada {denom}.",
        f"Considere as reações de hipersensibilidade do tipo {tipo}.",
        f"Entre os quatro tipos de hipersensibilidade descritos por Gell "
        f"e Coombs, o tipo {tipo} apresenta mecanismo próprio.",
        f"Um estudante revisa as características da hipersensibilidade "
        f"do tipo {tipo}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica seu mediador imunológico.",
        "Seu mediador é:",
        "Qual o mediador dessa reação?",
        "Assinale a alternativa que apresenta o mediador envolvido.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = mediador

    # Os mediadores da tabela se SOBREPÕEM como conjuntos: o tipo II é
    # "IgG e IgM" e o tipo III é "IgG". Postas lado a lado, quem sabe que
    # o tipo III envolve IgG pode marcar qualquer uma das duas — e boa
    # parte da literatura de fato atribui IgG e IgM ao tipo III. Duas
    # alternativas defensáveis é questão anulável.
    #
    # Aqui nenhuma alternativa pode conter ou estar contida em outra:
    # o filtro vale contra a correta E entre os próprios distratores,
    # porque _montar sorteia quatro quaisquer da lista.
    def _isotipos(texto):
        return frozenset(re.findall(r"Ig[ADEGM]", texto))

    def _contem(a, b):
        return bool(a) and bool(b) and (a <= b or b <= a)

    candidatos = [h[2] for h in HIPERSENSIBILIDADE if h[2] != mediador]
    candidatos += [
        "IgA secretora",
        "sistema complemento isoladamente, sem participação de anticorpos",
        "linfócitos B de memória",
    ]
    rng.shuffle(candidatos)

    conjunto_correto = _isotipos(mediador)
    distratores, conjuntos = [], []
    for cand in candidatos:
        conj = _isotipos(cand)
        if _contem(conj, conjunto_correto):
            continue
        if any(_contem(conj, c) for c in conjuntos):
            continue
        distratores.append(cand)
        conjuntos.append(conj)

    explicacao = (
        f"A hipersensibilidade do tipo {tipo} ({denom}) é mediada por "
        f"{mediador}. "
    )
    if tipo == "IV":
        explicacao += ("É a ÚNICA mediada por células — os tipos I, II e "
                       "III dependem de anticorpos.")
    else:
        explicacao += ("Os tipos I, II e III são mediados por anticorpos; "
                       "apenas o tipo IV é mediado por células T.")
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (hipersensibilidade)", rng)
    if q:
        q["_fato"] = f"hs:{tipo}"
    return q


def gerar_hs_tempo(rng):
    """
    Em quanto tempo a reação se instala?

    Só os tipos I, III e IV entram: são os que a literatura define por
    janela temporal precisa — imediata, de duas a oito horas, e tardia.
    O tipo II é caracterizado pelo MECANISMO, não pelo relógio, e sua
    faixa se sobrepunha às demais, tornando a questão ambígua.
    """
    candidatos = [h for h in HIPERSENSIBILIDADE if h[0] != "II"]
    tipo, denom, mediador, mecanismo, tempo, exemplos = rng.choice(candidatos)

    # Restringir o template a três tipos reduziu a combinatória de 48
    # para 36 enunciados. Mais cenários e comandos compensam.
    CENARIOS = [
        f"A hipersensibilidade do tipo {tipo} ({denom}) tem tempo de "
        f"instalação característico.",
        f"O intervalo entre a exposição ao antígeno e a manifestação "
        f"clínica varia conforme o tipo de hipersensibilidade. Considere "
        f"o tipo {tipo}.",
        f"Um paciente sensibilizado é reexposto ao antígeno e desenvolve "
        f"reação de hipersensibilidade do tipo {tipo}.",
        f"Ao caracterizar a hipersensibilidade do tipo {tipo}, avalia-se "
        f"seu tempo de instalação.",
        f"Na anamnese, o intervalo entre a exposição e o início dos "
        f"sintomas ajuda a classificar a reação. Considere uma "
        f"hipersensibilidade do tipo {tipo} ({denom}).",
        f"Um serviço de emergência registra o tempo decorrido entre a "
        f"exposição ao antígeno e a chegada do paciente. Trata-se de "
        f"hipersensibilidade do tipo {tipo}.",
        f"A classificação de Gell e Coombs associa cada tipo de "
        f"hipersensibilidade a uma janela temporal própria. Considere o "
        f"tipo {tipo} ({denom}).",
        f"Ao investigar uma reação adversa, o médico considera o tempo "
        f"decorrido desde a exposição. A hipótese é de hipersensibilidade "
        f"do tipo {tipo}.",
    ]
    COMANDOS = [
        "A reação se instala em:",
        "Assinale a alternativa que indica esse intervalo.",
        "O tempo esperado até a manifestação é de:",
        "Assinale a alternativa com a janela temporal correta.",
        "O intervalo característico é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = tempo
    distratores = [h[4] for h in candidatos if h[4] != tempo]
    distratores += [
        "de sete a dez dias",
        "de duas a quatro semanas",
        "de oito a doze horas",
        "de quatro a seis dias",
    ]

    explicacao = (
        f"A hipersensibilidade do tipo {tipo} ({denom}) instala-se em "
        f"{tempo}, porque depende de {mecanismo}. "
    )
    if tipo == "I":
        explicacao += ("É a mais rápida das quatro, por depender de "
                       "mediadores já pré-formados nos mastócitos.")
    elif tipo == "IV":
        explicacao += ("É a mais lenta, por depender do recrutamento e da "
                       "ativação de linfócitos T — daí o nome 'tardia'.")
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (hipersensibilidade)", rng)
    if q:
        q["_fato"] = f"hs:{tipo}"
    return q


def gerar_hs_mecanismo(rng):
    """
    Qual o mecanismo de determinado tipo?

    Aqui a distinção entre II e III é o ponto: no tipo II o antígeno está
    FIXO na superfície celular; no tipo III os complexos são CIRCULANTES.
    """
    tipo, denom, mediador, mecanismo, tempo, exemplos = rng.choice(HIPERSENSIBILIDADE)

    CENARIOS = [
        f"Considere o mecanismo imunopatológico da hipersensibilidade "
        f"do tipo {tipo}.",
        f"A hipersensibilidade do tipo {tipo} ({denom}) tem mecanismo "
        f"distinto dos demais tipos.",
        f"Em uma revisão de imunologia, analisa-se o mecanismo da "
        f"hipersensibilidade do tipo {tipo}.",
        f"O dano tecidual na hipersensibilidade do tipo {tipo} decorre "
        f"de um mecanismo característico.",
    ]
    COMANDOS = [
        "Assinale a alternativa que o descreve corretamente.",
        "Esse mecanismo consiste em:",
        "Qual o mecanismo envolvido?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = mecanismo
    distratores = [h[3] for h in HIPERSENSIBILIDADE if h[3] != mecanismo]
    distratores += [
        "destruição direta da célula-alvo por toxinas bacterianas, sem "
        "participação do sistema imune",
        "produção de autoanticorpos que estimulam receptores celulares, "
        "aumentando sua função",
    ]

    explicacao = f"Na hipersensibilidade do tipo {tipo} ({denom}), ocorre {mecanismo}. "
    if tipo in ("II", "III"):
        explicacao += (
            "A distinção entre os tipos II e III está em ONDE o antígeno "
            "se encontra: no tipo II o anticorpo se liga a antígeno fixo "
            "na superfície da célula; no tipo III os complexos "
            "antígeno-anticorpo circulam e depois se depositam nos tecidos."
        )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (hipersensibilidade)", rng)
    if q:
        q["_fato"] = f"hs:{tipo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — IMUNOGLOBULINAS
# ══════════════════════════════════════════════════════════

def gerar_ig_funcao(rng):
    """Qual a função principal de determinada imunoglobulina?"""
    classe, estrutura, local, funcao, particular = rng.choice(IMUNOGLOBULINAS)

    CENARIOS = [
        f"Considere a imunoglobulina {classe}.",
        f"Entre as classes de imunoglobulinas encontra-se a {classe}.",
        f"Um estudante revisa as características da {classe}.",
        f"A {classe} apresenta estrutura de {estrutura}.",
        f"Na avaliação do perfil de imunoglobulinas de um paciente, "
        f"analisa-se a {classe}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função principal.",
        "Sua função principal é:",
        "Qual a função dessa imunoglobulina?",
        "Assinale a alternativa que descreve corretamente sua função.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [i[3] for i in IMUNOGLOBULINAS if i[3] != funcao]
    distratores += [
        "transporte de antígenos até os linfonodos regionais",
        "neutralização direta de toxinas no compartimento intracelular",
    ]

    explicacao = (
        f"A {classe} tem como função principal a {funcao}. Predomina no "
        f"seguinte compartimento: {local}. Além disso, {particular}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (imunoglobulinas)", rng)
    if q:
        q["_fato"] = f"ig:{classe}"
    return q


def gerar_ig_local(rng):
    """Onde predomina determinada imunoglobulina?"""
    classe, estrutura, local, funcao, particular = rng.choice(IMUNOGLOBULINAS)

    CENARIOS = [
        f"A distribuição das imunoglobulinas pelo organismo não é "
        f"uniforme. Considere a {classe}.",
        f"Ao analisar onde cada classe de imunoglobulina se concentra, "
        f"examina-se a {classe}.",
        f"A {classe} tem localização preferencial no organismo.",
        f"Um exame laboratorial investiga a distribuição da {classe}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica onde predomina.",
        "Sua localização predominante é:",
        "Essa imunoglobulina predomina em:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = local
    distratores = [i[2] for i in IMUNOGLOBULINAS if i[2] != local]

    # Os dois extras antigos tinham 38 e 39 caracteres e eram SEMPRE
    # falsos, enquanto "membrana do linfócito B" (23) e "compartimento
    # intravascular" (27) são respostas certas em dois quintos dos
    # sorteios: bastava marcar a mais curta para acertar quase metade.
    #
    # A lista agora cobre a faixa inteira — de 23 a 50 caracteres — dos
    # dois lados, e só dois extras entram por questão, para que os
    # outros locais de imunoglobulina continuem sendo o distrator
    # dominante, que é o pedagogicamente útil.
    EXTRAS = [
        "citosol dos plasmócitos",
        "líquido cefalorraquidiano",
        "citoplasma dos linfócitos T auxiliares",
        "matriz extracelular do tecido conjuntivo",
        "grânulos dos eosinófilos e neutrófilos circulantes",
    ]
    distratores += rng.sample(EXTRAS, 2)

    explicacao = (
        f"A {classe} predomina no seguinte compartimento: {local}. Ali "
        f"exerce sua função de {funcao}. Convém lembrar que {particular}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (imunoglobulinas)", rng)
    if q:
        q["_fato"] = f"ig:{classe}"
    return q


def gerar_ig_particularidade(rng):
    """
    Qual imunoglobulina tem determinada característica?

    As particularidades — atravessar a placenta, ser pentâmero, ser a
    primeira da resposta primária — são o que a prova mais cobra.

    A IgD fica de fora: sua característica ("receptor do linfócito B
    virgem") também vale para a IgM de membrana, e a questão ficaria
    ambígua.
    """
    candidatos = [i for i in IMUNOGLOBULINAS if i[0] != "IgD"]
    classe, estrutura, local, funcao, particular = rng.choice(candidatos)

    CENARIOS = [
        f"Certa classe de imunoglobulina tem a seguinte particularidade: "
        f"{particular}.",
        f"Entre as imunoglobulinas, uma delas apresenta esta "
        f"característica distintiva: {particular}.",
        f"Ao comparar as classes de imunoglobulinas, observa-se que uma "
        f"delas tem a seguinte propriedade: {particular}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que a identifica.",
        "Trata-se da:",
        "Essa imunoglobulina é a:",
        "Qual classe apresenta essa característica?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = classe
    distratores = [i[0] for i in IMUNOGLOBULINAS if i[0] != classe]

    explicacao = (
        f"Trata-se da {classe}: {particular}. Sua função principal é a "
        f"{funcao}, e predomina no seguinte compartimento: {local}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (imunoglobulinas)", rng)
    if q:
        q["_fato"] = f"ig:{classe}"
    return q


def gerar_ig_estrutura(rng):
    """Qual a estrutura de determinada imunoglobulina?"""
    classe, estrutura, local, funcao, particular = rng.choice(IMUNOGLOBULINAS)

    # Todos os cenários terminam em PONTO e todos os comandos são orações
    # completas. A variante anterior misturava um cenário terminado em
    # vírgula com comandos em maiúscula, e a junção produzia sujeito
    # duplicado: "Ao caracterizar a IgD... sua estrutura corresponde a".
    #
    # O verbo "predominar" pede preposição contraída com artigo, e o
    # campo `local` é sintagma nominal puro — daí o "no" explícito.
    CENARIOS = [
        f"As imunoglobulinas diferem quanto à organização estrutural. "
        f"Considere a {classe}.",
        f"A {classe} predomina no seguinte compartimento: {local}.",
        f"Um estudo de imunoquímica analisa a organização estrutural "
        f"da {classe}.",
        f"Ao caracterizar a {classe} quanto à sua estrutura molecular, "
        f"observa-se um padrão definido.",
        f"A estrutura molecular da {classe} distingue-a das demais "
        f"classes de imunoglobulina.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve sua estrutura.",
        "Sua estrutura é a de um:",
        "Qual a estrutura dessa imunoglobulina?",
        "Sua organização estrutural corresponde a um:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = estrutura
    distratores = [i[1] for i in IMUNOGLOBULINAS if i[1] != estrutura]
    distratores += [
        "tetrâmero estabilizado por cadeia J",
        "trímero associado a componente secretor",
    ]

    explicacao = (
        f"A {classe} apresenta estrutura de {estrutura}. {particular.capitalize()}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (imunoglobulinas)", rng)
    if q:
        q["_fato"] = f"ig:{classe}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — CÉLULAS DO SISTEMA IMUNE
# ══════════════════════════════════════════════════════════

def gerar_celula_funcao(rng):
    """Qual a função principal de determinada célula imune?"""
    celula, celula_art, linhagem, funcao, particular = rng.choice(CELULAS_IMUNES)

    CENARIOS = [
        f"Considere {celula_art} no contexto da resposta imune.",
        f"Entre as células do sistema imune encontra-se {celula_art}.",
        f"Um estudante revisa o papel {_com_preposicao('de', celula_art)} "
        f"na defesa do organismo.",
        f"{_inicial_maiuscula(celula_art)} integra a imunidade {linhagem}.",
        f"Ao analisar um infiltrado inflamatório, identifica-se {celula_art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função principal.",
        "Sua função principal é:",
        "Qual a função dessa célula?",
        "Assinale a alternativa que descreve corretamente sua função.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [x[3] for x in CELULAS_IMUNES if x[3] != funcao]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(celula_art)} pertence à imunidade {linhagem} e tem como função "
        f"principal a {funcao}. Convém lembrar que {particular}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Imunologia (células do sistema imune)", rng)
    if q:
        q["_fato"] = f"celula:{celula}"
    return q


def gerar_celula_linhagem(rng):
    """A célula pertence à imunidade inata ou adaptativa?"""
    celula, celula_art, linhagem, funcao, particular = rng.choice(CELULAS_IMUNES)

    CENARIOS = [
        f"O sistema imune divide-se em componentes inato e adaptativo. "
        f"Considere {celula_art}.",
        f"Ao classificar as células de defesa quanto à sua linhagem "
        f"funcional, examina-se {celula_art}.",
        f"{_inicial_maiuscula(celula_art)} exerce a função de {funcao}.",
        f"Em uma revisão de imunologia, discute-se o papel "
        f"{_com_preposicao('de', celula_art)}.",
    ]
    COMANDOS = [
        "Essa célula pertence à imunidade:",
        "Assinale a alternativa que indica sua linhagem.",
        "Quanto à sua classificação funcional, trata-se de célula da "
        "imunidade:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # A resposta da tabela é uma palavra — "inata" ou "adaptativa" — e os
    # distratores eram frases explicativas de até 60 caracteres. Quem
    # marcasse sempre a alternativa mais curta acertava 70% das vezes,
    # sem ler nada.
    #
    # Agora as cinco opções têm a mesma forma: linhagem + as duas
    # propriedades que a definem (velocidade/especificidade e memória).
    # O erro dos distratores está no CONTEÚDO — inata com memória,
    # adaptativa inespecífica —, não no tamanho.
    # Os comprimentos são escalonados de propósito: "inata" tem cinco
    # letras e "adaptativa", dez, então qualificações idênticas deixariam
    # a resposta certa sistematicamente mais curta quando a linhagem
    # fosse inata. As qualificações compensam a diferença, e as duas
    # respostas possíveis (38 e 36 caracteres) ficam no MEIO da faixa dos
    # distratores (31 a 43) — nem a mais curta, nem a mais longa.
    QUALIFICA = {
        "inata":      "inata, de ação imediata e inespecífica",
        "adaptativa": "adaptativa, específica e com memória",
    }
    ESPELHO = {
        "inata":      "inata, específica e com memória",
        "adaptativa": "adaptativa, de ação imediata e inespecífica",
    }
    correta = QUALIFICA[linhagem]
    outra = "adaptativa" if linhagem == "inata" else "inata"
    distratores = [
        QUALIFICA[outra],
        ESPELHO["inata"],
        ESPELHO["adaptativa"],
        "passiva, transferida por anticorpos",
        "humoral, mediada só por anticorpos",
    ]

    explicacao = (
        f"{_inicial_maiuscula(celula_art)} pertence à imunidade {linhagem}, pois sua função é a "
        f"{funcao}. "
    )
    if linhagem == "inata":
        explicacao += ("A imunidade inata age de forma rápida e "
                       "inespecífica, sem gerar memória imunológica.")
    else:
        explicacao += ("A imunidade adaptativa é específica para o "
                       "antígeno e gera memória imunológica.")
    q = _montar(enunciado, correta, distratores, explicacao,
                "Imunologia (imunidade inata e adaptativa)", rng)
    if q:
        q["_fato"] = f"celula:{celula}"
    return q


def gerar_celula_particularidade(rng):
    """Qual célula tem determinada característica distintiva?"""
    celula, celula_art, linhagem, funcao, particular = rng.choice(CELULAS_IMUNES)

    CENARIOS = [
        f"Certa célula do sistema imune tem a seguinte característica: "
        f"{particular}.",
        f"Entre as células de defesa, uma delas apresenta esta "
        f"propriedade distintiva: {particular}.",
        f"Ao comparar as células do sistema imune, observa-se que uma "
        f"delas tem a seguinte particularidade: {particular}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que a identifica.",
        "Trata-se do:",
        "Essa célula é o:",
        "Qual célula apresenta essa característica?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = celula
    distratores = [x[0] for x in CELULAS_IMUNES if x[0] != celula]
    rng.shuffle(distratores)

    explicacao = (
        f"Trata-se {_com_preposicao('de', celula_art)}: {particular}. "
        f"Pertence à imunidade "
        f"{linhagem} e sua função principal é a {funcao}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Imunologia (células do sistema imune)", rng)
    if q:
        q["_fato"] = f"celula:{celula}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_IMUNOLOGIA = {
    "hs_por_exemplo":     gerar_hs_por_exemplo,
    "hs_mediador":        gerar_hs_mediador,
    "hs_tempo":           gerar_hs_tempo,
    "hs_mecanismo":       gerar_hs_mecanismo,
    "ig_funcao":          gerar_ig_funcao,
    "ig_local":           gerar_ig_local,
    "ig_particularidade": gerar_ig_particularidade,
    "ig_estrutura":       gerar_ig_estrutura,
    "celula_funcao":      gerar_celula_funcao,
    "celula_linhagem":    gerar_celula_linhagem,
    "celula_particular":  gerar_celula_particularidade,
}

TOPICOS_IMUNOLOGIA = {
    "hipersensibilidade": [
        "hs_por_exemplo",
        "hs_mediador",
        "hs_tempo",
        "hs_mecanismo",
    ],
    "imunoglobulinas": [
        "ig_funcao",
        "ig_local",
        "ig_particularidade",
        "ig_estrutura",
    ],
    "celulas": [
        "celula_funcao",
        "celula_linhagem",
        "celula_particular",
    ],
}

# Singular e plural: o casamento é por palavra inteira, e o índice de um
# livro costuma usar o plural.
PALAVRAS_CHAVE = {
    "hs_por_exemplo":     ["hipersensibilidade", "gell e coombs",
                           "gell-coombs", "anafilaxia", "alergia",
                           "reacao alergica", "imunocomplexo",
                           "imunocomplexos"],
    "hs_mediador":        ["hipersensibilidade", "gell e coombs",
                           "gell-coombs", "imunocomplexo", "imunocomplexos"],
    "hs_tempo":           ["hipersensibilidade", "gell e coombs",
                           "hipersensibilidade tardia",
                           "hipersensibilidade imediata"],
    "hs_mecanismo":       ["hipersensibilidade", "gell e coombs",
                           "imunocomplexo", "imunocomplexos", "citotoxica"],
    "ig_funcao":          ["imunoglobulina", "imunoglobulinas", "anticorpo",
                           "anticorpos", "iga", "igg", "igm", "ige", "igd"],
    "ig_local":           ["imunoglobulina", "imunoglobulinas", "anticorpo",
                           "anticorpos", "iga", "igg", "igm"],
    "ig_particularidade": ["imunoglobulina", "imunoglobulinas", "anticorpo",
                           "anticorpos", "imunidade passiva", "colostro"],
    "ig_estrutura":       ["imunoglobulina", "imunoglobulinas",
                           "estrutura do anticorpo", "pentamero", "dimero"],
    "celula_funcao":      ["linfocito", "linfocitos", "macrofago",
                           "macrofagos", "neutrofilo", "neutrofilos",
                           "celula dendritica", "natural killer",
                           "plasmocito", "eosinofilo", "basofilo"],
    "celula_linhagem":    ["imunidade inata", "imunidade adaptativa",
                           "resposta inata", "resposta adaptativa",
                           "linfocito", "linfocitos"],
    "celula_particular":  ["linfocito", "linfocitos", "macrofago",
                           "neutrofilo", "celula dendritica",
                           "natural killer", "plasmocito", "cd4", "cd8",
                           "mhc"],
}

CHAVES_GENERICAS = {
    "resposta", "mecanismo", "funcao", "estrutura", "tempo", "tipo",
    "celula", "celulas", "sistema", "reacao", "mediador",
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
    """Gera um lote de questões de imunologia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_IMUNOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_IMUNOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_IMUNOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_IMUNOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Quantos fatos distintos cada template explora. O rodízio simples
    # distribuía por template, mas o material é desigual: quatro
    # templates dividem 4 tipos de hipersensibilidade, enquanto três
    # dividem 10 células. Sem peso, os de hipersensibilidade esgotavam e
    # repetiam enquanto as células sobravam.
    LASTRO = {
        "hs_por_exemplo":     len(HIPERSENSIBILIDADE),
        "hs_mediador":        len(HIPERSENSIBILIDADE),
        "hs_tempo":           len(HIPERSENSIBILIDADE),
        "hs_mecanismo":       len(HIPERSENSIBILIDADE),
        "ig_funcao":          len(IMUNOGLOBULINAS),
        "ig_local":           len(IMUNOGLOBULINAS),
        "ig_particularidade": len(IMUNOGLOBULINAS) - 1,   # sem a IgD
        "ig_estrutura":       len(IMUNOGLOBULINAS),
        "celula_funcao":      len(CELULAS_IMUNES),
        "celula_linhagem":    len(CELULAS_IMUNES),
        "celula_particular":  len(CELULAS_IMUNES),
    }
    # Ver comentário equivalente em gerador_bioquimica.gerar_lote: a
    # fila é intercalada, não agrupada.
    pesos = {n: max(1, min(round(LASTRO.get(n, 5) / 4), 4))
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
        q = TEMPLATES_IMUNOLOGIA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        # Um mesmo fato não rende duas questões no lote: perguntar o
        # mediador e o tempo do tipo I é perguntar duas vezes sobre o
        # mesmo item da tabela.
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
    print("  GERADOR DE IMUNOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
