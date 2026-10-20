"""
=============================================================
  GERADOR DE MICROBIOLOGIA
=============================================================
  Questões de microbiologia geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Coloração de Gram — etapas, estrutura da parede,
       resultado e exceções
    ✅ Classificação bacteriana por morfologia e arranjo
    ✅ Alvos dos antimicrobianos (mecanismo, sem dose)
    ❌ Escolha de antibiótico para um caso, posologia

  VERIFICAÇÃO DAS FONTES

  Registradas em microbiologia/_fontes.md.

  USO:
      from gerador_microbiologia import gerar_lote, gerar_para_api
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

# ── Etapas da coloração de Gram ──
#
# Fontes: Kasvi; UNL/CTNE; USP/FORP; Wikipédia (Técnica de Gram);
# Tortora, Funke & Case, Microbiology.
#
# (ordem, reagente, papel)
# Cada reagente traz o ARTIGO: "o cristal violeta" mas "a safranina".
# Sem isso, o enunciado saía como "considere o safranina".
ETAPAS_GRAM = [
    (1, "cristal violeta", "o cristal violeta",
     "corante primário, que cora todas as células de roxo"),
    (2, "lugol", "o lugol",
     "mordente, que forma um complexo insolúvel com o corante dentro "
     "da célula"),
    (3, "álcool-acetona", "o álcool-acetona",
     "descolorante, na etapa crítica da técnica"),
    (4, "safranina", "a safranina",
     "contracorante, que cora de vermelho as células que perderam o "
     "corante primário"),
]

# ── Características das paredes bacterianas ──
#
# (característica, gram-positiva, gram-negativa)
# Cada característica traz o ARTIGO, porque gênero e número variam:
# "a espessura" mas "os ácidos teicoicos". Sem isso, o enunciado saía
# como "Considere a ácidos teicoicos e lipoteicoicos".
# As respostas "ausente", "presentes" e "em geral maior" tinham de 7 a
# 14 caracteres, contra até 63 dos distratores: marcar a mais curta
# acertava 47% destas questões. Cada valor passou a trazer o traço que o
# sustenta, no mesmo comprimento das alternativas erradas — sem mudar o
# fato, só a forma de enunciá-lo.
PAREDE_GRAM = [
    ("espessura da camada de peptidoglicano",
     "a espessura da camada de peptidoglicano",
     "espessa, de 20 a 80 nanômetros",
     "fina, de cerca de 8 nanômetros"),
    ("membrana externa", "a membrana externa",
     "ausente, com o peptidoglicano exposto",
     "presente, contendo lipopolissacarídeo"),
    ("ácidos teicoicos e lipoteicoicos",
     "os ácidos teicoicos e lipoteicoicos",
     "presentes, ancorados no peptidoglicano",
     "ausentes, com membrana externa no lugar"),
    ("cor ao final da coloração de Gram",
     "a cor ao final da coloração de Gram",
     "roxa ou violeta",
     "vermelha ou rosa"),
    ("presença de endotoxina", "a presença de endotoxina",
     "não possui lipopolissacarídeo",
     "o lipopolissacarídeo atua como endotoxina"),
    ("suscetibilidade aos beta-lactâmicos",
     "a suscetibilidade aos beta-lactâmicos",
     "maior, pela parede diretamente acessível",
     "menor, pela barreira da membrana externa"),
]

# ── Exceções à coloração de Gram ──
#
# (gênero, motivo, alternativa)
EXCECOES_GRAM = [
    ("Mycobacterium",
     "sua parede é rica em ácido micólico, um lipídio que impede a "
     "penetração dos corantes convencionais",
     "coloração de Ziehl-Neelsen, que as identifica como bacilos "
     "álcool-ácido resistentes"),
    ("Mycoplasma",
     "não possui parede celular, estrutura em que a técnica se baseia",
     "identificação por métodos moleculares ou por cultura em meios "
     "específicos"),
]

# ── Morfologia e arranjo bacteriano ──
#
# (gênero, gram, morfologia, arranjo, observação)
MORFOLOGIA_BACTERIANA = [
    ("Staphylococcus", "positiva", "coco", "agrupado em cachos",
     "é catalase positivo, o que o distingue do Streptococcus"),
    ("Streptococcus", "positiva", "coco", "disposto em cadeias",
     "é catalase negativo"),
    ("Neisseria", "negativa", "coco", "aos pares, como diplococo",
     "os diplococos têm faces adjacentes achatadas, com aspecto de "
     "grão de café"),
    ("Escherichia", "negativa", "bacilo", "isolado ou aos pares",
     "faz parte da microbiota intestinal normal"),
    ("Clostridium", "positiva", "bacilo", "isolado",
     "é anaeróbio estrito e forma esporos"),
    ("Bacillus", "positiva", "bacilo", "isolado ou em cadeias",
     "é aeróbio ou anaeróbio facultativo e forma esporos"),
    ("Vibrio", "negativa", "bacilo curvo", "em forma de vírgula",
     "é oxidase positivo e tem motilidade por flagelo polar único"),
]

# Clostridium fica FORA do template de morfologia e arranjo.
#
# Seu arranjo é "isolado", e a tabela traz "isolado ou aos pares"
# (Escherichia) e "isolado ou em cadeias" (Bacillus). Quem está isolado
# também satisfaz "isolado ou aos pares": o distrator não era falso, era
# mais abrangente que a resposta. Duas alternativas marcáveis.
#
# O gênero continua nos demais templates — Gram, esporulação, anaerobiose
# —, onde o que se cobra dele é específico. Aqui a característica não
# distingue.
SEM_ARRANJO_EXCLUSIVO = {"Clostridium"}

# ── Alvos dos antimicrobianos ──
#
# Mecanismo de ação, não posologia — mesmo critério adotado no gerador
# de farmacologia.
#
# (alvo, o que faz, exemplos de classe)
# O campo `classes` traz o ARTIGO junto, porque o gênero varia: "dos
# beta-lactâmicos" mas "das polimixinas". Sem isso, o enunciado saía
# como "o mecanismo de ação dos polimixinas".
ALVOS_ANTIMICROBIANOS = [
    ("parede celular",
     "inibição da síntese do peptidoglicano, levando à lise osmótica",
     "dos beta-lactâmicos e glicopeptídeos"),
    ("membrana citoplasmática",
     "desorganização da membrana, com extravasamento do conteúdo celular",
     "das polimixinas"),
    ("subunidade ribossômica 30S",
     "bloqueio da síntese proteica pela ligação à subunidade menor do "
     "ribossomo",
     "dos aminoglicosídeos e tetraciclinas"),
    ("subunidade ribossômica 50S",
     "bloqueio da síntese proteica pela ligação à subunidade maior do "
     "ribossomo",
     "dos macrolídeos, da clindamicina e do cloranfenicol"),
    ("DNA-girase e topoisomerase IV",
     "impedimento do superenovelamento do DNA bacteriano",
     "das quinolonas"),
    ("via do folato",
     "bloqueio da síntese de ácido fólico, necessário à produção de "
     "ácidos nucleicos",
     "das sulfonamidas e da trimetoprima"),
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

    Existe nos demais geradores do projeto pelo mesmo motivo: o
    fatiamento manual — d{art[1:]} — devolve o espaço junto e produz
    "d plasmócito".
    """
    s = str(sintagma or "").strip()
    # O PLURAL faltava. "os ácidos teicoicos e lipoteicoicos" é o
    # sintagma de uma das características da parede, e o enunciado saía
    # "compara as paredes celulares bacterianas quanto a os ácidos
    # teicoicos" — em vez de "quanto aos".
    CONTRACOES = {
        ("a", "a "): "à ",   ("a", "o "): "ao ",
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
    """Eleva só a primeira letra, preservando nomes próprios."""
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


# ══════════════════════════════════════════════════════════
#  TEMPLATES — COLORAÇÃO DE GRAM
# ══════════════════════════════════════════════════════════

def gerar_gram_etapa(rng):
    """Qual o papel de determinado reagente na coloração de Gram?"""
    ordem, reagente, reagente_art, papel = rng.choice(ETAPAS_GRAM)

    CENARIOS = [
        f"Na coloração de Gram, utiliza-se {reagente_art}.",
        f"A técnica de Gram emprega quatro reagentes em sequência. "
        f"Considere {reagente_art}.",
        f"Durante a execução da coloração de Gram, aplica-se "
        f"{reagente_art} sobre o esfregaço.",
        f"Um técnico de laboratório executa a coloração de Gram e "
        f"adiciona {reagente_art}.",
        f"Entre os reagentes da técnica de Gram encontra-se {reagente_art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve seu papel na técnica.",
        "Esse reagente atua como:",
        "Qual a função desse reagente?",
        "Assinale a alternativa que apresenta sua função.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = papel
    distratores = [e[3] for e in ETAPAS_GRAM if e[3] != papel]
    distratores += [
        "fixador, que adere as células à lâmina antes da coloração",
        "agente de contraste ótico, que aumenta o índice de refração",
        "conservante, que impede a proliferação bacteriana na lâmina",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(reagente_art)} é o {ordem}º reagente "
        f"da técnica e atua como "
        f"{papel}. A sequência completa é: cristal violeta, lugol, "
        f"álcool-acetona e safranina."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Microbiologia (coloração de Gram)", rng)
    if q:
        q["_fato"] = f"gram_etapa:{reagente}"
    return q


def gerar_gram_sequencia(rng):
    """Qual reagente vem antes ou depois de outro?"""
    idx = rng.randrange(len(ETAPAS_GRAM))
    ordem, reagente, reagente_art, papel = ETAPAS_GRAM[idx]

    direcao = rng.choice(["antes", "depois"])
    if direcao == "antes" and idx == 0:
        direcao = "depois"
    if direcao == "depois" and idx == len(ETAPAS_GRAM) - 1:
        direcao = "antes"
    alvo = ETAPAS_GRAM[idx - 1] if direcao == "antes" else ETAPAS_GRAM[idx + 1]

    palavra = "precede" if direcao == "antes" else "sucede"
    # Cada cenário é um ADJUNTO, não uma oração completa — a frase é
    # fechada pelo ", considere X" que vem depois. "Os reagentes seguem
    # ordem definida" já era oração, e a junção produzia emenda.
    CENARIOS = [
        "Na sequência de reagentes da coloração de Gram",
        "Ao executar a técnica de Gram na ordem correta",
        "Seguindo o protocolo padrão da coloração de Gram",
        "No protocolo padrão da coloração de Gram",
        "Na ordem estabelecida para a técnica de Gram",
        "Ao aplicar os reagentes da coloração de Gram em sequência",
    ]
    posicao = ("imediatamente anterior" if direcao == "antes"
               else "imediatamente posterior")
    COMANDOS = [
        f"Assinale a alternativa com o reagente {posicao}.",
        f"Qual é o reagente {posicao}?",
        f"Entre os reagentes listados, qual ocupa a posição {posicao}?",
        f"Assinale a alternativa que apresenta o reagente {posicao}.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)}, considere {reagente_art}. "
                 f"{rng.choice(COMANDOS)}")

    # Os reagentes da técnica têm nomes de tamanhos muito diferentes —
    # "lugol" tem 5 caracteres, "álcool-acetona" tem 14. Qualificar
    # todos com a mesma estrutura desfaz a correlação entre tamanho e
    # resposta, que fazia a estratégia "marque a mais curta" acertar 46%.
    # As qualificações precisam ter comprimento SEMELHANTE entre si.
    # "o lugol, solução de iodo" tinha 24 caracteres contra 52 do
    # distrator mais longo, e continuava sendo o menor — a estratégia
    # "marque a mais curta" ainda acertava 48%.
    QUALIFICA = {
        "cristal violeta": "o cristal violeta, primeiro corante aplicado",
        "lugol":           "o lugol, solução de iodo usada como mordente",
        "álcool-acetona":  "o álcool-acetona, empregado na descoloração",
        "safranina":       "a safranina, corante de contraste vermelho",
    }
    correta = QUALIFICA[alvo[1]]
    distratores = [QUALIFICA[e[1]] for e in ETAPAS_GRAM
                   if e[1] not in (reagente, alvo[1])]
    distratores += [
        "a fucsina de Ziehl, usada em bacilos resistentes",
        "o azul de metileno, corante de contraste azulado",
        "o verde malaquita, empregado na coloração de esporos",
    ]

    explicacao = (
        f"A ordem dos reagentes é: cristal violeta, lugol, álcool-acetona "
        f"e safranina. Portanto, o reagente {posicao} ao {reagente} é: "
        f"{correta}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Microbiologia (coloração de Gram)", rng)
    if q:
        q["_fato"] = f"gram_seq:{reagente}:{direcao}"
    return q


def gerar_parede_caracteristica(rng):
    """Como determinada característica se apresenta em cada grupo?"""
    caracteristica, carac_art, positiva, negativa = rng.choice(PAREDE_GRAM)
    grupo = rng.choice(["positiva", "negativa"])
    valor = positiva if grupo == "positiva" else negativa
    outro_valor = negativa if grupo == "positiva" else positiva

    CENARIOS = [
        f"Nas bactérias Gram-{grupo}s, avalia-se a seguinte "
        f"característica: {caracteristica}.",
        f"Considere {carac_art} nas bactérias Gram-{grupo}s.",
        f"A estrutura da parede celular difere entre os grupos "
        f"bacterianos. Analise {carac_art} nas Gram-{grupo}s.",
        f"Um estudante compara as paredes celulares bacterianas quanto "
        f"{_com_preposicao('a', carac_art)}, "
        f"examinando as Gram-{grupo}s.",
    ]
    COMANDOS = [
        "Assinale a alternativa correta.",
        "Nesse grupo, essa característica se apresenta como:",
        "Qual a descrição correta para esse grupo?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    # Os distratores precisam ser RESPOSTAS POSSÍVEIS para a pergunta
    # feita. Usar o valor de outra característica produzia coisas como
    # "qual a cor final?" com alternativa "ausente" — descartável sem
    # conhecimento nenhum.
    #
    # Cada característica tem seu próprio conjunto de respostas
    # plausíveis, do mesmo tipo semântico.
    PLAUSIVEIS = {
        "espessura da camada de peptidoglicano": [
            "intermediária, de cerca de 15 nanômetros",
            "variável, de 5 a 50 nanômetros",
            "ausente, sem peptidoglicano na parede",
        ],
        "membrana externa": [
            "presente, mas sem lipopolissacarídeo",
            "presente apenas durante a esporulação",
            "substituída por cápsula polissacarídica",
        ],
        "ácidos teicoicos e lipoteicoicos": [
            "presentes apenas nas formas esporuladas",
            "substituídos por ácidos micólicos",
            "restritos à membrana citoplasmática",
        ],
        "cor ao final da coloração de Gram": [
            "azul-esverdeada",
            "amarelo-acastanhada",
            "castanho-clara",
            "incolor",
        ],
        "presença de endotoxina": [
            "possui exotoxina proteica em vez de lipopolissacarídeo",
            "não produz nenhum tipo de toxina",
            "o ácido teicoico atua como endotoxina",
        ],
        "suscetibilidade aos beta-lactâmicos": [
            "em geral nula, por ausência de parede",
            "quase sempre igual nos dois grupos",
            "dependente apenas da presença de cápsula",
            "variável conforme o meio de cultura",
        ],
    }
    correta = valor
    distratores = [outro_valor] + PLAUSIVEIS.get(caracteristica, [])
    rng.shuffle(distratores)

    outro_grupo = "negativa" if grupo == "positiva" else "positiva"
    explicacao = (
        f"Nas bactérias Gram-{grupo}s, a {caracteristica} apresenta-se "
        f"assim: {valor}. Nas Gram-{outro_grupo}s, por contraste: "
        f"{outro_valor}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Microbiologia (parede bacteriana)", rng)
    if q:
        q["_fato"] = f"parede:{caracteristica}:{grupo}"
    return q


def gerar_gram_excecao(rng):
    """Por que determinado gênero não cora pela técnica de Gram?"""
    genero, motivo, alternativa = rng.choice(EXCECOES_GRAM)
    modo = rng.choice(["por_que", "qual_genero"])

    if modo == "por_que":
        CENARIOS = [
            f"Bactérias do gênero {genero} não são adequadamente "
            f"identificadas pela coloração de Gram.",
            f"A coloração de Gram tem limitações. Um exemplo é o gênero "
            f"{genero}.",
            f"Ao tentar corar bactérias do gênero {genero} pela técnica "
            f"de Gram, o resultado é inconclusivo.",
            f"Um laboratório não consegue classificar bactérias do gênero "
            f"{genero} pela coloração de Gram.",
            f"O gênero {genero} escapa à classificação convencional pela "
            f"técnica de Gram.",
            f"Em uma aula prática, observa-se que o gênero {genero} não "
            f"responde à coloração de Gram como esperado.",
            f"A técnica de Gram falha na identificação de bactérias do "
            f"gênero {genero}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que justifica essa limitação.",
            "Isso ocorre porque:",
            "Qual a razão dessa limitação?",
            "Assinale a alternativa que explica esse comportamento.",
            "A explicação para isso é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = motivo
        distratores = [e[1] for e in EXCECOES_GRAM if e[1] != motivo]
        distratores += [
            "seu tamanho reduzido impede a visualização em microscopia "
            "óptica convencional",
            "cresce apenas em meios anaeróbios, incompatíveis com a "
            "preparação da lâmina",
            "sua cápsula polissacarídica retém todos os corantes de "
            "forma inespecífica",
            "multiplica-se exclusivamente dentro de células hospedeiras",
        ]
    else:
        CENARIOS = [
            f"Certo gênero bacteriano não é identificado pela coloração "
            f"de Gram porque {motivo}.",
            f"A limitação da técnica de Gram diante de um gênero "
            f"específico decorre do seguinte: {motivo}.",
            f"Um gênero bacteriano escapa à coloração de Gram pela "
            f"seguinte razão: {motivo}.",
            f"A impossibilidade de classificar certo gênero pelo Gram "
            f"tem esta explicação: {motivo}.",
            f"Um estudante investiga por que determinado gênero não cora "
            f"pelo Gram e descobre que {motivo}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que o identifica.",
            "Trata-se do gênero:",
            "Esse gênero é o:",
            "Assinale a alternativa correspondente.",
            "Qual gênero apresenta essa característica?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = genero
        distratores = [e[0] for e in EXCECOES_GRAM if e[0] != genero]
        distratores += ["Staphylococcus", "Escherichia", "Clostridium",
                        "Neisseria", "Bacillus"]

    rng.shuffle(distratores)
    explicacao = (
        f"O gênero {genero} não cora adequadamente pelo Gram porque "
        f"{motivo}. A alternativa diagnóstica é: {alternativa}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Microbiologia (limitações da coloração de Gram)", rng)
    if q:
        q["_fato"] = f"excecao:{genero}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — MORFOLOGIA BACTERIANA
# ══════════════════════════════════════════════════════════

def gerar_morfologia_genero(rng):
    """Qual a morfologia e o arranjo de determinado gênero?"""
    candidatos = [m for m in MORFOLOGIA_BACTERIANA
                  if m[0] not in SEM_ARRANJO_EXCLUSIVO]
    genero, gram, morfologia, arranjo, obs = rng.choice(candidatos)

    CENARIOS = [
        f"Considere bactérias do gênero {genero}.",
        f"Um esfregaço corado revela bactérias do gênero {genero}.",
        f"Ao examinar uma cultura de {genero} ao microscópio,",
        f"Entre os gêneros bacterianos de importância clínica encontra-se "
        f"o {genero}.",
        f"Um estudante revisa as características morfológicas do "
        f"gênero {genero}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve sua morfologia e arranjo.",
        "Sua morfologia e arranjo correspondem a:",
        "observa-se a seguinte morfologia e arranjo:",
        "Qual a morfologia e o arranjo característicos?",
    ]
    cenario = rng.choice(CENARIOS)
    if cenario.rstrip().endswith(","):
        comando = "observa-se a seguinte morfologia e arranjo:"
    else:
        comando = rng.choice([x for x in COMANDOS if x[0].isupper()])
    enunciado = f"{cenario} {comando}"

    correta = f"{morfologia} {arranjo}"

    # Nenhuma alternativa pode ser mais abrangente que a correta: se a
    # resposta é "bacilo isolado", "bacilo isolado ou aos pares" também
    # estaria certa para uma bactéria isolada.
    def _formas(texto):
        return frozenset(p.strip() for p in texto.split(" ou "))

    # O filtro vale contra a correta E entre os próprios distratores:
    # "bacilo isolado" ao lado de "bacilo isolado ou aos pares" é um par
    # que se anula, mesmo quando nenhum dos dois é a resposta.
    formas_certas = _formas(correta)
    distratores, formas_vistas = [], [formas_certas]
    for m in MORFOLOGIA_BACTERIANA:
        alt = f"{m[2]} {m[3]}"
        if alt == correta:
            continue
        fa = _formas(alt)
        if any(fa < v or v < fa for v in formas_vistas):
            continue
        distratores.append(alt)
        formas_vistas.append(fa)
    distratores += [
        "espirilo em forma de saca-rolhas",
        "cocobacilo isolado ou em paliçada",
    ]
    rng.shuffle(distratores)

    explicacao = (
        f"O gênero {genero} é Gram-{gram} e apresenta-se como {morfologia} "
        f"{arranjo}. Convém lembrar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Microbiologia (morfologia bacteriana)", rng)
    if q:
        q["_fato"] = f"morfologia:{genero}"
    return q


def gerar_gram_genero(rng):
    """O gênero é Gram-positivo ou Gram-negativo?"""
    genero, gram, morfologia, arranjo, obs = rng.choice(MORFOLOGIA_BACTERIANA)

    CENARIOS = [
        f"Bactérias do gênero {genero} apresentam-se como {morfologia} "
        f"{arranjo}.",
        f"Considere a classificação do gênero {genero} pela coloração "
        f"de Gram.",
        f"Um laboratório identifica bactérias do gênero {genero} em uma "
        f"amostra clínica.",
        f"Ao classificar o gênero {genero} quanto à coloração de Gram,",
    ]
    # Nenhum comando pode terminar em "Gram:", porque as alternativas
    # começam com "Gram-positiva" — produzia "bactéria Gram:
    # Gram-positiva, retendo o cristal violeta".
    COMANDOS = [
        "Assinale a alternativa correta quanto à sua coloração de Gram.",
        "Esse gênero é classificado como:",
        "verifica-se que se trata de bactéria:",
        "Quanto à coloração de Gram, trata-se de bactéria:",
        "Assinale a alternativa que classifica esse gênero corretamente.",
    ]
    cenario = rng.choice(CENARIOS)
    if cenario.rstrip().endswith(","):
        comando = "verifica-se que se trata de bactéria:"
    else:
        comando = rng.choice([x for x in COMANDOS if x[0].isupper()])
    enunciado = f"{cenario} {comando}"

    # Mesmo problema do gram_sequencia: "Gram-positiva" tem 13
    # caracteres contra 57 do distrator mais longo. Todas as opções
    # ganham qualificação de comprimento semelhante.
    outro = "negativa" if gram == "positiva" else "positiva"
    QUALIFICA_GRAM = {
        "positiva": "Gram-positiva, retendo o cristal violeta",
        "negativa": "Gram-negativa, corando-se pela safranina",
    }
    correta = QUALIFICA_GRAM[gram]
    distratores = [
        QUALIFICA_GRAM[outro],
        "Gram-variável, conforme a fase de crescimento",
        "não corável, por ausência de parede celular",
        "álcool-ácido resistente, exigindo Ziehl-Neelsen",
        "Gram-positiva apenas na forma esporulada",
    ]

    explicacao = (
        f"O gênero {genero} é Gram-{gram}, apresentando-se como "
        f"{morfologia} {arranjo}. {obs.capitalize()}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Microbiologia (classificação bacteriana)", rng)
    if q:
        q["_fato"] = f"gram_genero:{genero}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — ALVOS DOS ANTIMICROBIANOS
# ══════════════════════════════════════════════════════════

def _irmao_ribossomal(alvo, campo):
    """
    Devolve o item 30S quando o alvo é o 50S, e vice-versa.

    Lista vazia para os demais alvos. O campo escolhe o que retornar:
    0 para o nome do alvo, 1 para a descrição do mecanismo.
    """
    if "ribossômica" not in alvo:
        return []
    return [a[campo] for a in ALVOS_ANTIMICROBIANOS
            if "ribossômica" in a[0] and a[0] != alvo]


def gerar_alvo_antimicrobiano(rng):
    """Onde determinada classe de antimicrobiano age?"""
    alvo, acao, classes = rng.choice(ALVOS_ANTIMICROBIANOS)
    modo = rng.choice(["pela_classe", "pelo_alvo"])

    if modo == "pela_classe":
        CENARIOS = [
            f"Os antimicrobianos do grupo {classes} exercem ação "
            f"antibacteriana.",
            f"Considere o mecanismo de ação {classes}.",
            f"Um paciente recebe antimicrobiano da classe {classes}.",
            f"Em uma aula de microbiologia, discute-se o mecanismo "
            f"{classes}.",
            f"O uso clínico {classes} baseia-se em um mecanismo definido.",
        ]
        COMANDOS = [
            "Assinale a alternativa que indica seu alvo bacteriano.",
            "Seu alvo é:",
            "Essa classe atua sobre:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = alvo
        distratores = _irmao_ribossomal(alvo, 0)
        distratores += [a[0] for a in ALVOS_ANTIMICROBIANOS if a[0] != alvo]
        distratores += [
            "cápsula polissacarídica",
            "flagelo bacteriano",
        ]
    else:
        CENARIOS = [
            f"Certa classe de antimicrobianos atua sobre a seguinte "
            f"estrutura bacteriana: {alvo}.",
            f"O alvo bacteriano de uma classe de antimicrobianos é: {alvo}.",
            f"Um antimicrobiano tem como sítio de ação: {alvo}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que descreve seu mecanismo.",
            "O mecanismo correspondente é:",
            "Qual o mecanismo de ação sobre esse alvo?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = acao
        # O par 30S/50S anda junto. O enunciado diz "sítio de ação:
        # subunidade ribossômica 30S", e a resposta fala em "ligação à
        # subunidade menor do RIBOSSOMO": quando o item do 50S não era
        # sorteado, a alternativa certa virava a única a repetir as
        # palavras do enunciado, e o chute pelo eco acertava todas.
        #
        # Com os dois sempre presentes, o que decide é saber que 30S é a
        # subunidade menor — que é o que a questão quer cobrar.
        distratores = _irmao_ribossomal(alvo, 1)
        distratores += [a[1] for a in ALVOS_ANTIMICROBIANOS if a[1] != acao]
        distratores += [
            "inibição da adesão bacteriana ao epitélio do hospedeiro",
            "neutralização direta das toxinas produzidas pela bactéria",
        ]

    rng.shuffle(distratores)
    explicacao = (
        f"O alvo é: {alvo}. O mecanismo consiste em {acao}. É o caso "
        f"{classes}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Microbiologia (antimicrobianos)", rng)
    if q:
        q["_fato"] = f"alvo:{alvo}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_MICROBIOLOGIA = {
    "gram_etapa":        gerar_gram_etapa,
    "gram_sequencia":    gerar_gram_sequencia,
    "parede_gram":       gerar_parede_caracteristica,
    "gram_excecao":      gerar_gram_excecao,
    "morfologia":        gerar_morfologia_genero,
    "gram_genero":       gerar_gram_genero,
    "alvo_antimicrobiano": gerar_alvo_antimicrobiano,
}

TOPICOS_MICROBIOLOGIA = {
    "coloracao_gram": [
        "gram_etapa",
        "gram_sequencia",
        "parede_gram",
        "gram_excecao",
    ],
    "classificacao": [
        "morfologia",
        "gram_genero",
    ],
    "antimicrobianos": [
        "alvo_antimicrobiano",
    ],
}

PALAVRAS_CHAVE = {
    "gram_etapa":     ["coloracao de gram", "tecnica de gram", "gram",
                       "cristal violeta", "safranina", "lugol"],
    "gram_sequencia": ["coloracao de gram", "tecnica de gram", "gram",
                       "cristal violeta", "safranina"],
    "parede_gram":    ["parede celular bacteriana", "peptidoglicano",
                       "lipopolissacarideo", "acido teicoico", "gram",
                       "gram-positiva", "gram-negativa", "endotoxina"],
    "gram_excecao":   ["mycobacterium", "mycoplasma", "ziehl-neelsen",
                       "baar", "alcool-acido resistente"],
    "morfologia":     ["morfologia bacteriana", "coco", "cocos", "bacilo",
                       "bacilos", "diplococo", "estafilococo",
                       "estreptococo", "staphylococcus", "streptococcus"],
    "gram_genero":    ["staphylococcus", "streptococcus", "escherichia",
                       "neisseria", "clostridium", "classificacao "
                       "bacteriana", "gram-positiva", "gram-negativa"],
    "alvo_antimicrobiano": ["antimicrobiano", "antimicrobianos",
                            "antibiotico", "antibioticos", "beta-lactamico",
                            "quinolona", "quinolonas", "aminoglicosideo",
                            "macrolideo", "resistencia bacteriana"],
}

CHAVES_GENERICAS = {
    "gram", "parede", "membrana", "celular", "estrutura", "alvo",
    "classificacao", "mecanismo", "acao", "bacteria", "bacterias",
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
    """Gera um lote de questões de microbiologia."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_MICROBIOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_MICROBIOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_MICROBIOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_MICROBIOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Sorteio proporcional ao material, com fila INTERCALADA — ver
    # comentário em gerador_bioquimica.gerar_lote sobre por que a fila
    # agrupada fazia lotes pequenos nunca alcançarem os templates de
    # maior lastro.
    LASTRO = {
        "gram_etapa":          len(ETAPAS_GRAM),
        "gram_sequencia":      len(ETAPAS_GRAM),
        "parede_gram":         len(PAREDE_GRAM) * 2,   # dois grupos
        "gram_excecao":        len(EXCECOES_GRAM) * 2, # dois modos
        "morfologia":          len(MORFOLOGIA_BACTERIANA),
        "gram_genero":         len(MORFOLOGIA_BACTERIANA),
        "alvo_antimicrobiano": len(ALVOS_ANTIMICROBIANOS) * 2,
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
        q = TEMPLATES_MICROBIOLOGIA[nome](rng)
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
    print("  GERADOR DE MICROBIOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
