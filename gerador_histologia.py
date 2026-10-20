"""
=============================================================
  GERADOR DE HISTOLOGIA
=============================================================
  Questões de histologia geradas proceduralmente, sem depender
  de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Classificação dos epitélios — critérios, tipos, locais
    ✅ Tecido muscular — os três tipos e suas diferenças
    ❌ Identificação em lâmina (depende de imagem)

  VERIFICAÇÃO DAS FONTES

  Registradas em histologia/_fontes.md, incluindo uma
  divergência: uma fonte classifica o epitélio de transição
  como pseudoestratificado — está incorreto, ele é
  estratificado.

  USO:
      from gerador_histologia import gerar_lote, gerar_para_api
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

# ── Epitélios de revestimento ──
#
# Fontes: UNIFAL-MG (Histologia Interativa); UFSC (Atlas Virtual);
# Atlas de Histologia da FMV-Lisboa; Ross & Wojciech.
#
# (nome, com_artigo, camadas, forma, locais, observação)
EPITELIOS = [
    ("pavimentoso simples", "o epitélio pavimentoso simples",
     "simples", "pavimentosa",
     ["o endotélio dos vasos sanguíneos",
      "o mesotélio das cavidades serosas",
      "os alvéolos pulmonares"],
     "sua espessura mínima favorece a troca rápida de substâncias"),

    ("cúbico simples", "o epitélio cúbico simples",
     "simples", "cúbica",
     ["os túbulos contorcidos do rim", "os folículos da tireoide",
      "os bronquíolos terminais"],
     "está associado a secreção e a transporte ativo de íons"),

    ("cilíndrico simples", "o epitélio cilíndrico simples",
     "simples", "cilíndrica",
     ["o estômago", "o intestino delgado", "o intestino grosso",
      "a vesícula biliar"],
     "reveste quase todo o tubo digestório e é especializado em absorção"),

    ("pseudoestratificado cilíndrico ciliado",
     "o epitélio pseudoestratificado cilíndrico ciliado",
     "pseudoestratificado", "cilíndrica",
     ["a traqueia", "os brônquios", "a cavidade nasal"],
     "todas as células tocam a lâmina basal, mas os núcleos ficam em "
     "alturas diferentes, o que dá aparência de estratificação"),

    ("pavimentoso estratificado não queratinizado",
     "o epitélio pavimentoso estratificado não queratinizado",
     "estratificado", "pavimentosa",
     ["o esôfago", "a vagina", "a cavidade oral"],
     "reveste superfícies úmidas sujeitas a atrito"),

    ("pavimentoso estratificado queratinizado",
     "o epitélio pavimentoso estratificado queratinizado",
     "estratificado", "pavimentosa",
     # "a pele", não "a epiderme": a epiderme É esse epitélio, e dizer
     # que ele reveste a epiderme fica circular.
     ["a pele", "a superfície da palma da mão", "a planta do pé"],
     "constitui a epiderme, cujas células superficiais perdem organelas "
     "e acumulam queratina, impedindo a perda de líquido"),

    ("cúbico estratificado", "o epitélio cúbico estratificado",
     "estratificado", "cúbica",
     ["os ductos das glândulas sudoríparas"],
     "é pouco frequente no organismo"),

    ("de transição", "o epitélio de transição",
     "estratificado", "variável",
     ["a bexiga urinária", "o ureter", "a pelve renal"],
     "também chamado urotélio, muda de forma conforme a distensão: as "
     "células superficiais são cúbicas com a bexiga vazia e pavimentosas "
     "com a bexiga cheia"),
]

# ── Tecido muscular ──
#
# (tipo, com_artigo, estriação, núcleos, posição, controle, particular)
MUSCULOS = [
    ("esquelético", "o músculo esquelético",
     "presente", "vários por fibra", "periférica", "voluntário",
     "suas fibras são cilíndricas e longas, formadas pela fusão de "
     "mioblastos"),
    ("cardíaco", "o músculo cardíaco",
     "presente", "um ou dois", "central", "involuntário",
     "possui discos intercalares, estruturas exclusivas desse tecido, "
     "que acoplam eletricamente as células"),
    ("liso", "o músculo liso",
     "ausente", "um", "central", "involuntário",
     "suas células são fusiformes e não apresentam estriação "
     "transversal"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _com_preposicao(prep: str, sintagma: str) -> str:
    """
    Junta preposição e sintagma fazendo a CONTRAÇÃO.

    Existe nos demais geradores do projeto pelo mesmo motivo: o
    fatiamento manual devolve o espaço junto e produz "d epitélio".
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
#  TEMPLATES — EPITÉLIOS
# ══════════════════════════════════════════════════════════

def gerar_epitelio_por_local(rng):
    """
    Qual epitélio reveste determinada estrutura?

    É o formato mais cobrado: o aluno precisa associar estrutura e
    epitélio, não recitar a classificação.
    """
    nome, art, camadas, forma, locais, obs = rng.choice(EPITELIOS)
    local = rng.choice(locais)

    CENARIOS = [
        f"Considere o revestimento epitelial do seguinte local: {local}.",
        f"Uma lâmina histológica corresponde ao seguinte órgão ou "
        f"estrutura: {local}.",
        f"Em uma aula prática de histologia, examina-se o epitélio de "
        f"revestimento do seguinte local: {local}.",
        f"O revestimento epitelial {_com_preposicao('de', local)} tem "
        f"características "
        f"próprias.",
        f"Ao estudar o epitélio que reveste {local},",
    ]
    COMANDOS = [
        "Assinale a alternativa que o identifica.",
        "Trata-se do epitélio:",
        "Esse local é revestido por epitélio:",
        "Qual epitélio reveste essa estrutura?",
    ]
    cenario = rng.choice(CENARIOS)
    if cenario.rstrip().endswith(","):
        comando = "identifica-se o epitélio:"
    else:
        comando = rng.choice(COMANDOS)
    enunciado = f"{cenario} {comando}"

    correta = nome
    distratores = [e[0] for e in EPITELIOS if e[0] != nome]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(art)} reveste: {local}. Trata-se de "
        f"epitélio {camadas}, com células de forma {forma}. "
        f"Convém lembrar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Histologia (epitélios de revestimento)", rng)
    if q:
        q["_fato"] = f"epitelio:{nome}"
    return q


def gerar_local_por_epitelio(rng):
    """Caminho inverso: onde se encontra determinado epitélio?"""
    nome, art, camadas, forma, locais, obs = rng.choice(EPITELIOS)
    local = rng.choice(locais)

    CENARIOS = [
        f"Considere {art}.",
        f"Entre os epitélios de revestimento encontra-se {art}.",
        f"Um estudante revisa as características {_com_preposicao('de', art)}.",
        f"Uma lâmina apresenta {art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que indica onde ele se encontra.",
        "Esse epitélio reveste:",
        "Em que estrutura ele é encontrado?",
        "Assinale a alternativa com um local em que ele ocorre.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = local
    # Locais de OUTROS epitélios servem de distrator
    distratores = []
    for e in EPITELIOS:
        if e[0] == nome:
            continue
        distratores.extend(e[4])
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(art)} reveste: {local}. É um epitélio "
        f"{camadas}, e {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Histologia (epitélios de revestimento)", rng)
    if q:
        q["_fato"] = f"epitelio:{nome}"
    return q


def gerar_criterio_classificacao(rng):
    """
    Qual critério define o nome do epitélio?

    A regra de que a camada SUPERFICIAL nomeia o epitélio estratificado
    é o que a prova cobra com mais frequência.
    """
    modo = rng.choice(["camada_superficial", "criterios", "pseudo"])

    if modo == "camada_superficial":
        CENARIOS = [
            "Um epitélio estratificado apresenta células basais cúbicas "
            "e células superficiais pavimentosas.",
            "Em uma lâmina, observa-se epitélio com várias camadas: as "
            "células profundas são cilíndricas e as superficiais, "
            "pavimentosas.",
            "Certo epitélio estratificado tem células de formatos "
            "diferentes conforme a profundidade da camada.",
            "Ao examinar um epitélio com múltiplas camadas, verifica-se "
            "que as células mudam de forma da base para a superfície.",
            "Um estudante hesita ao classificar um epitélio cujas "
            "camadas têm células de formatos distintos.",
            "Num corte histológico, o epitélio mostra células cúbicas "
            "junto à lâmina basal e achatadas na superfície livre.",
            "A classificação de um epitélio com várias camadas de "
            "formatos diferentes segue uma convenção definida.",
        ]
        COMANDOS = [
            "Assinale a alternativa que indica como ele é classificado.",
            "Sua classificação segue:",
            "Qual critério determina o nome desse epitélio?",
            "Assinale a alternativa com o critério aplicável.",
            "O nome desse epitélio é definido por:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = ("a forma das células da camada superficial")
        distratores = [
            "a forma das células da camada basal",
            "a forma predominante entre todas as camadas",
            "o número total de camadas celulares",
            "a espessura da lâmina basal",
            "a forma das células da camada intermediária",
        ]
        explicacao = (
            "Num epitélio estratificado, é sempre a forma das células da "
            "camada SUPERFICIAL que determina o nome. No exemplo dado, "
            "as células superficiais são pavimentosas, então o epitélio "
            "é classificado como pavimentoso estratificado."
        )
    elif modo == "criterios":
        CENARIOS = [
            "A classificação dos epitélios de revestimento obedece a "
            "critérios definidos.",
            "Ao nomear um epitélio de revestimento, o histologista "
            "considera parâmetros específicos.",
            "A denominação de um epitélio de revestimento combina dois "
            "parâmetros.",
            "Todo epitélio de revestimento recebe um nome composto, "
            "derivado de dois critérios.",
            "Um estudante revisa como se nomeiam os epitélios de "
            "revestimento.",
            "A nomenclatura dos epitélios de revestimento não é "
            "arbitrária: segue parâmetros estabelecidos.",
        ]
        COMANDOS = [
            "Assinale a alternativa que os apresenta.",
            "Esses critérios são:",
            "Quais são esses parâmetros?",
            "Assinale a alternativa com os dois critérios corretos.",
            "Os parâmetros considerados são:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "o número de camadas celulares e a forma das células"
        distratores = [
            "a origem embrionária e a função predominante",
            "a espessura da lâmina basal e o tipo de junção intercelular",
            "a presença de cílios e a capacidade de secreção",
            "o grau de vascularização e a taxa de renovação celular",
            "a coloração pela hematoxilina e a densidade nuclear",
        ]
        explicacao = (
            "A classificação combina o NÚMERO DE CAMADAS — simples, "
            "estratificado ou pseudoestratificado — e a FORMA DAS "
            "CÉLULAS — pavimentosa, cúbica ou cilíndrica. Nos "
            "estratificados, é a forma da camada superficial que conta."
        )
    else:
        CENARIOS = [
            "Um epitélio apresenta núcleos em alturas diferentes, o que "
            "sugere várias camadas. Ao exame cuidadoso, verifica-se que "
            "todas as células tocam a lâmina basal.",
            "Certo epitélio parece estratificado, mas todas as suas "
            "células estão apoiadas na lâmina basal.",
            "Em uma lâmina da traqueia, observa-se epitélio cujos "
            "núcleos ocupam níveis distintos, embora nenhuma célula "
            "esteja separada da lâmina basal.",
            "A aparência de múltiplas camadas em certo epitélio decorre "
            "apenas do desalinhamento dos núcleos.",
            "Um epitélio das vias respiratórias dá impressão de ter "
            "várias camadas, mas todas as células alcançam a lâmina "
            "basal.",
            "Ao examinar o epidídimo, identifica-se epitélio com núcleos "
            "em alturas variadas e todas as células apoiadas na lâmina "
            "basal.",
        ]
        COMANDOS = [
            "Esse epitélio é classificado como:",
            "Assinale a alternativa que o classifica corretamente.",
            "Trata-se de epitélio:",
            "Assinale a alternativa com a classificação correta.",
            "Sua classificação é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "pseudoestratificado"
        # "estratificado" e "estratificado com metaplasia" na mesma
        # questão: dois distratores em que um engloba o outro. Nenhum é
        # a resposta aqui, mas o par se elimina sozinho — quem percebe
        # que os dois não podem estar certos descarta ambos de graça.
        distratores = [
            "estratificado",
            "simples com projeções apicais",
            "de transição",
            "colunar com metaplasia",
            "simples com invaginações basais",
        ]
        explicacao = (
            "Trata-se de epitélio PSEUDOESTRATIFICADO. Ele parece ter "
            "várias camadas porque os núcleos ocupam alturas diferentes, "
            "mas todas as células tocam a lâmina basal — ou seja, é um "
            "epitélio simples. O exemplo clássico é o "
            "pseudoestratificado cilíndrico ciliado da traqueia."
        )

    q = _montar(enunciado, correta, distratores, explicacao,
                "Histologia (classificação dos epitélios)", rng)
    if q:
        q["_fato"] = f"criterio:{modo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — TECIDO MUSCULAR
# ══════════════════════════════════════════════════════════

def gerar_musculo_caracteristica(rng):
    """
    Como determinada característica se apresenta em cada tipo muscular?

    O ponto central é que o cardíaco combina traços dos outros dois:
    estriado como o esquelético, involuntário como o liso.
    """
    tipo, art, estriacao, nucleos, posicao, controle, particular = \
        rng.choice(MUSCULOS)

    # Cada característica traz o ARTIGO e a forma com preposição,
    # porque o gênero varia: "a estriação" mas "o tipo de controle".
    # Encaixar "a" em todas produzia "avalia-se A tipo de controle".
    CARACTERISTICAS = [
        ("estriação transversal", "a estriação transversal",
         "à estriação transversal", estriacao,
         ["presente", "ausente"]),
        ("número de núcleos por célula", "o número de núcleos por célula",
         "ao número de núcleos por célula", nucleos,
         ["vários por fibra", "um ou dois", "um"]),
        ("posição do núcleo", "a posição do núcleo",
         "à posição do núcleo", posicao,
         ["periférica", "central"]),
        ("tipo de controle", "o tipo de controle",
         "ao tipo de controle", controle,
         ["voluntário", "involuntário"]),
    ]
    (caracteristica, carac_art, carac_prep,
     valor, universo) = rng.choice(CARACTERISTICAS)

    # O cenário e o comando não devem repetir a característica. Antes
    # saía "quanto à seguinte característica: posição do núcleo.
    # Assinale a alternativa correta quanto à posição do núcleo".
    #
    # Cenários que JÁ nomeiam a característica recebem comandos curtos;
    # os que não nomeiam recebem comandos que a explicitam. A crase e o
    # gênero vêm do próprio campo (carac_art, carac_prep).
    CENARIOS_COM_CARAC = [
        f"Considere {art} quanto à seguinte característica: "
        f"{caracteristica}.",
        f"Ao comparar os tipos de tecido muscular, avalia-se "
        f"{carac_art} {_com_preposicao('em', art)}.",
        f"Um estudante analisa {carac_art} {_com_preposicao('em', art)}.",
        f"Uma prova de histologia cobra {carac_art} "
        f"{_com_preposicao('em', art)}.",
    ]
    COMANDOS_CURTOS = [
        "Nesse tecido, essa característica apresenta-se como:",
        "Assinale a alternativa correta.",
        "A descrição correta é:",
        "Assinale a alternativa que a descreve corretamente.",
    ]
    CENARIOS_SEM_CARAC = [
        f"Uma lâmina de tecido muscular corresponde "
        f"{_com_preposicao('a', art)}.",
        f"Um corte histológico revela {art}.",
        f"O material examinado corresponde {_com_preposicao('a', art)}.",
    ]
    COMANDOS_COM_CARAC = [
        f"Nesse tecido, {carac_art} apresenta-se como:",
        f"Assinale a alternativa correta quanto {carac_prep}.",
        f"Quanto {carac_prep}, a descrição correta é:",
        f"{_inicial_maiuscula(carac_art)} nesse tecido corresponde a:",
    ]

    if rng.random() < 0.5:
        enunciado = (f"{rng.choice(CENARIOS_COM_CARAC)} "
                     f"{rng.choice(COMANDOS_CURTOS)}")
    else:
        enunciado = (f"{rng.choice(CENARIOS_SEM_CARAC)} "
                     f"{rng.choice(COMANDOS_COM_CARAC)}")

    # Os distratores precisam ser respostas POSSÍVEIS para a
    # característica perguntada. Antes vinham das outras linhas da
    # tabela, e perguntar sobre estriação com alternativa "voluntário"
    # permitia descartar sem saber nada de histologia.
    #
    # Cada característica tem seu próprio conjunto de opções plausíveis.
    PLAUSIVEIS = {
        "estriação transversal": [
            "presente apenas nas extremidades da fibra",
            "presente somente após coloração especial",
            "substituída por estriação longitudinal",
        ],
        "número de núcleos por célula": [
            "nenhum, pois a célula é anucleada",
            "número variável, de dez a vinte por célula",
            "dois em toda a extensão da fibra",
        ],
        "posição do núcleo": [
            "junto ao disco intercalar",
            "deslocada para a extremidade da fibra",
            "variável ao longo do ciclo contrátil",
        ],
        "tipo de controle": [
            "voluntário apenas durante o esforço máximo",
            "involuntário, mas modulável pela vontade",
            "reflexo, sem participação do sistema nervoso",
        ],
    }
    correta = valor
    distratores = [u for u in universo if u != valor]
    distratores += PLAUSIVEIS.get(caracteristica, [])
    vistos, unicos = set(), []
    for d in distratores:
        if d != correta and d not in vistos:
            vistos.add(d)
            unicos.append(d)

    explicacao = (
        f"{_inicial_maiuscula(art)} apresenta {carac_art}: {valor}. "
        f"Convém lembrar que {particular}."
    )
    if tipo == "cardíaco":
        explicacao += (" O músculo cardíaco combina traços dos outros "
                       "dois: é ESTRIADO como o esquelético e "
                       "INVOLUNTÁRIO como o liso.")
    q = _montar(enunciado, correta, unicos, explicacao,
                "Histologia (tecido muscular)", rng)
    if q:
        # O veto é pela CARACTERÍSTICA, não pelo par com o músculo:
        # "posição do núcleo no esquelético" e "posição do núcleo no
        # cardíaco" são a mesma pergunta repetida.
        q["_fato"] = f"musculo_carac:{caracteristica}"
        # Grupo secundário: permite ao gerar_lote espalhar os músculos
        # em vez de concentrar três questões no cardíaco.
        q["_grupo"] = f"musculo:{tipo}"
    return q


def gerar_musculo_identificacao(rng):
    """Dado um conjunto de características, qual tipo muscular é?"""
    tipo, art, estriacao, nucleos, posicao, controle, particular = \
        rng.choice(MUSCULOS)

    # "um núcleo(s)" não é português. Os valores do campo já trazem a
    # forma correta; basta não acrescentar o substantivo.
    NUCLEO_TEXTO = {
        "vários por fibra": "vários núcleos por fibra",
        "um ou dois":       "um ou dois núcleos",
        "um":               "um único núcleo",
    }
    descricao = (f"estriação {estriacao}, {NUCLEO_TEXTO.get(nucleos, nucleos)} "
                 f"em posição {posicao} e controle {controle}")
    CENARIOS = [
        f"Um tecido muscular apresenta as seguintes características: "
        f"{descricao}.",
        f"A análise de uma lâmina revela tecido muscular com "
        f"{descricao}.",
        f"Certo tipo de tecido muscular caracteriza-se por {descricao}.",
        f"Em um corte histológico, o tecido muscular mostra "
        f"{descricao}.",
        f"Um estudante descreve um tecido muscular assim: {descricao}.",
        f"O laudo de uma biópsia muscular registra {descricao}.",
        f"As características observadas em uma amostra muscular são: "
        f"{descricao}.",
    ]
    COMANDOS = [
        "Trata-se de músculo:",
        "Assinale a alternativa que o identifica.",
        "Esse tecido corresponde ao músculo:",
        "Assinale a alternativa com o tipo correspondente.",
        "Que tipo de músculo é esse?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = tipo
    distratores = [m[0] for m in MUSCULOS if m[0] != tipo]
    # "esquelético cardiomodificado" saiu: contém "esquelético", que é
    # resposta em um terço dos sorteios, e alternativa que engloba a
    # correta é alternativa marcável.
    #
    # "mioepitelial" entra no lugar — termo real (as células
    # mioepiteliais das glândulas são contráteis), errado como tipo de
    # tecido muscular e sem parentesco textual com nenhuma das respostas.
    distratores += ["estriado visceral", "misto de transição",
                    "mioepitelial"]

    explicacao = (
        f"Trata-se {_com_preposicao('de', art)}: {descricao}. "
        f"{_inicial_maiuscula(particular)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Histologia (tecido muscular)", rng)
    if q:
        q["_fato"] = f"musculo_id:{tipo}"
        q["_grupo"] = f"musculo:{tipo}"
    return q


def gerar_discos_intercalares(rng):
    """
    Estrutura exclusiva de um tipo muscular.

    Os discos intercalares são a marca do cardíaco, e a questão cobra
    justamente essa exclusividade.
    """
    modo = rng.choice(["qual_tecido", "qual_estrutura"])

    if modo == "qual_tecido":
        CENARIOS = [
            "Os discos intercalares são estruturas juncionais que "
            "acoplam eletricamente células musculares adjacentes.",
            "Certa estrutura permite que células musculares se contraiam "
            "de forma sincronizada, funcionando como sincício.",
            "Em uma lâmina, identificam-se discos intercalares entre as "
            "células musculares.",
            "Uma amostra muscular exibe faixas escuras transversais que "
            "unem células adjacentes de ponta a ponta.",
            "A presença de discos intercalares é registrada no laudo de "
            "uma biópsia muscular.",
            "Certas células musculares comunicam-se por junções que "
            "permitem a passagem direta de íons entre elas.",
        ]
        COMANDOS = [
            "Essa estrutura é exclusiva do músculo:",
            "Assinale a alternativa que indica o tecido correspondente.",
            "Trata-se de tecido muscular:",
            "Assinale a alternativa com o tipo muscular correspondente.",
            "Esse achado indica músculo:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "cardíaco"
        # Mesma limpeza: "liso" convivia com "liso visceral" e "liso
        # multiunitário", e "esquelético" com "estriado esquelético
        # apenas". Os subtipos saíram; entraram termos reais que não se
        # contêm.
        distratores = ["esquelético", "liso", "estriado visceral",
                       "mioepitelial", "misto de transição"]
        explicacao = (
            "Os discos intercalares são EXCLUSIVOS do músculo cardíaco. "
            "Contêm desmossomos, que dão adesão mecânica, e junções "
            "comunicantes, que acoplam eletricamente as células e "
            "permitem contração sincronizada."
        )
    else:
        CENARIOS = [
            "O músculo cardíaco possui uma estrutura juncional que não "
            "existe nos demais tipos musculares.",
            "Entre as características do músculo cardíaco está uma "
            "estrutura que o distingue dos outros tecidos musculares.",
            "Uma estrutura própria do tecido muscular cardíaco permite a "
            "contração sincronizada de suas células.",
            "O acoplamento elétrico entre células do músculo cardíaco "
            "depende de uma estrutura específica.",
            "Ao microscópio, o músculo cardíaco exibe faixas escuras "
            "transversais ausentes nos demais tecidos musculares.",
            "Um estudante procura a estrutura que distingue o músculo "
            "cardíaco do esquelético ao microscópio óptico.",
        ]
        COMANDOS = [
            "Assinale a alternativa que a nomeia.",
            "Trata-se de:",
            "Que estrutura é essa?",
            "Assinale a alternativa com o nome correto.",
            "Essa estrutura é denominada:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "discos intercalares"
        distratores = ["túbulos T", "tríades sarcoplasmáticas",
                       "placas motoras", "corpos densos",
                       "junções mioneurais"]
        explicacao = (
            "São os DISCOS INTERCALARES, exclusivos do músculo cardíaco. "
            "Contêm desmossomos, para adesão mecânica, e junções "
            "comunicantes, que acoplam eletricamente as células."
        )

    q = _montar(enunciado, correta, distratores, explicacao,
                "Histologia (tecido muscular)", rng)
    if q:
        q["_fato"] = f"discos:{modo}"
        # Este template é SEMPRE sobre o músculo cardíaco, então entra
        # no mesmo grupo dos demais — sem isso, escapava do teto e o
        # lote voltava a ter três questões sobre o cardíaco.
        q["_grupo"] = "musculo:cardíaco"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_HISTOLOGIA = {
    "epitelio_por_local":  gerar_epitelio_por_local,
    "local_por_epitelio":  gerar_local_por_epitelio,
    "criterio_class":      gerar_criterio_classificacao,
    "musculo_caract":      gerar_musculo_caracteristica,
    "musculo_id":          gerar_musculo_identificacao,
    "discos_intercalares": gerar_discos_intercalares,
}

TOPICOS_HISTOLOGIA = {
    "epitelios": [
        "epitelio_por_local",
        "local_por_epitelio",
        "criterio_class",
    ],
    "muscular": [
        "musculo_caract",
        "musculo_id",
        "discos_intercalares",
    ],
}

PALAVRAS_CHAVE = {
    "epitelio_por_local": ["epitelio", "epitelios", "tecido epitelial",
                           "epitelio de revestimento", "pavimentoso",
                           "estratificado", "pseudoestratificado",
                           "urotelio"],
    "local_por_epitelio": ["epitelio", "epitelios", "tecido epitelial",
                           "epitelio de revestimento", "pavimentoso",
                           "cilindrico simples"],
    "criterio_class":     ["epitelio", "epitelios", "tecido epitelial",
                           "classificacao dos epitelios", "lamina basal",
                           "pseudoestratificado"],
    "musculo_caract":     ["tecido muscular", "musculo esqueletico",
                           "musculo cardiaco", "musculo liso",
                           "fibra muscular", "estriacao"],
    "musculo_id":         ["tecido muscular", "musculo esqueletico",
                           "musculo cardiaco", "musculo liso",
                           "fibra muscular"],
    "discos_intercalares": ["disco intercalar", "discos intercalares",
                            "musculo cardiaco", "tecido muscular",
                            "juncao comunicante", "desmossomo"],
}

CHAVES_GENERICAS = {
    "tecido", "tecidos", "celula", "celulas", "estrutura", "camada",
    "camadas", "forma", "local", "revestimento", "musculo",
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
    """Gera um lote de questões de histologia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_HISTOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_HISTOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_HISTOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_HISTOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Fila INTERCALADA, proporcional ao material — ver comentário em
    # gerador_bioquimica.gerar_lote sobre por que a fila agrupada fazia
    # lotes pequenos nunca alcançarem os templates de maior lastro.
    LASTRO = {
        "epitelio_por_local":  len(EPITELIOS),
        "local_por_epitelio":  len(EPITELIOS),
        "criterio_class":      3,          # três modos de pergunta
        "musculo_caract":      len(MUSCULOS) * 4,   # quatro características
        "musculo_id":          len(MUSCULOS),
        "discos_intercalares": 2,          # dois modos
    }
    pesos = {n: max(1, min(round(LASTRO.get(n, 4) / 4), 4))
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
    grupos = Counter()

    # Quantas questões do mesmo GRUPO o lote tolera. O veto por fato
    # impede repetir a mesma pergunta, mas não impede que três
    # perguntas diferentes recaiam todas sobre o músculo cardíaco —
    # o que deixa o lote repetitivo aos olhos do aluno.
    TETO_POR_GRUPO = max(2, quantidade // 4)

    # A posição na fila depende de len(questoes), que NÃO avança quando
    # a questão é rejeitada. Se o template daquela posição só produz
    # questões vetadas, o laço fica preso ali até esgotar as tentativas
    # — e então o veto afrouxa e todas entram de uma vez.
    #
    # Avançar a posição a cada TENTATIVA, e não a cada questão aceita,
    # faz o rodízio seguir para o próximo template quando um emperra.
    posicao = 0
    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = fila[posicao % len(fila)]
        posicao += 1
        q = TEMPLATES_HISTOLOGIA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        fato = q.get("_fato")
        if fato and fato in fatos_usados and tentativas < limite * 0.9:
            continue

        # O teto por grupo é FIRME até quase esgotar as tentativas.
        # Com 0.85, ele cedia cedo demais e o lote voltava a concentrar
        # quatro questões no mesmo músculo.
        grupo = q.get("_grupo")
        if (grupo and grupos[grupo] >= TETO_POR_GRUPO
                and tentativas < limite * 0.95):
            continue

        vistos.add(q["enunciado"])
        if fato:
            fatos_usados.add(fato)
        if grupo:
            grupos[grupo] += 1
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
    print("  GERADOR DE HISTOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
