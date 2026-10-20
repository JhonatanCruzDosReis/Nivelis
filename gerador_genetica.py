"""
=============================================================
  GERADOR DE GENÉTICA
=============================================================
  Questões de genética médica geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO:
    ✅ Padrões de herança monogênica e suas marcas
    ✅ Cálculo de probabilidade em cruzamentos
    ✅ Doenças associadas a cada padrão
    ❌ Aconselhamento genético para caso concreto
    ❌ Interpretação de heredograma em imagem

  VERIFICAÇÃO DAS FONTES

  Registradas em genetica/_fontes.md. A principal é o Manual
  MSD (edição para profissionais), cruzada com material
  universitário da USP e da PUC-Goiás.

  USO:
      from gerador_genetica import gerar_lote, gerar_para_api
=============================================================
"""

import random
import re
import unicodedata
from fractions import Fraction

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


# ══════════════════════════════════════════════════════════
#  BASE DE FATOS
# ══════════════════════════════════════════════════════════

# ── Padrões de herança ──
#
# Fontes: Manual MSD (profissional); PUC-Goiás; USP/ICB;
# Thompson & Thompson, Genética Médica.
#
# (padrão, com_artigo, marca no heredograma, sexos, exemplos, armadilha)
PADROES = [
    ("autossômica dominante", "a herança autossômica dominante",
     "o fenótipo aparece em todas as gerações, em transmissão vertical, "
     "e todo afetado costuma ter ao menos um genitor afetado",
     "afeta homens e mulheres na mesma proporção",
     ["polidactilia", "acondroplasia", "doença de Huntington",
      "neurofibromatose tipo 1", "síndrome de Marfan",
      "hipercolesterolemia familiar", "doença renal policística do "
      "adulto", "esclerose tuberosa"],
     "só se distingue da dominante ligada ao X pela presença de "
     "transmissão de homem para homem"),

    ("autossômica recessiva", "a herança autossômica recessiva",
     "o fenótipo pode pular gerações, e os afetados costumam ter pais "
     "não afetados, ambos heterozigotos",
     "afeta homens e mulheres na mesma proporção",
     ["fibrose cística", "anemia falciforme", "fenilcetonúria",
      "albinismo oculocutâneo", "talassemia", "galactosemia",
      "doença de Tay-Sachs", "atrofia muscular espinhal"],
     "a consanguinidade entre os genitores aumenta a chance de "
     "ocorrência"),

    ("recessiva ligada ao X", "a herança recessiva ligada ao X",
     "quase todos os afetados são homens, e as mulheres heterozigotas "
     "são portadoras fenotipicamente normais",
     "predomina largamente no sexo masculino",
     ["hemofilia A", "hemofilia B", "daltonismo",
      "distrofia muscular de Duchenne",
      "deficiência de glicose-6-fosfato desidrogenase",
      "síndrome de Hunter"],
     "não existe transmissão de homem para homem, pois o pai transmite "
     "apenas o cromossomo Y aos filhos"),

    ("dominante ligada ao X", "a herança dominante ligada ao X",
     "o homem afetado transmite a característica a todas as filhas e a "
     "nenhum filho",
     "afeta mais mulheres, que possuem dois cromossomos X",
     ["raquitismo hipofosfatêmico", "síndrome de Rett",
      "incontinência pigmentar"],
     "é difícil distinguir da autossômica dominante sem um heredograma "
     "amplo, e a chave está na ausência de transmissão homem a homem"),

    ("holândrica", "a herança holândrica, restrita ao Y",
     "somente homens são afetados, e o pai afetado transmite a "
     "característica a todos os filhos do sexo masculino",
     "ocorre exclusivamente no sexo masculino",
     ["hipertricose auricular"],
     "os genes envolvidos situam-se na porção do cromossomo Y sem "
     "homologia com o X"),
]

# ── Cruzamentos monogênicos ──
#
# (genótipos, descendência, comentário)
CRUZAMENTOS = [
    ("Aa × Aa", {"AA": Fraction(1, 4), "Aa": Fraction(1, 2),
                 "aa": Fraction(1, 4)},
     "ocorre entre dois portadores e é típico da herança autossômica "
     "recessiva"),
    ("Aa × aa", {"Aa": Fraction(1, 2), "aa": Fraction(1, 2)},
     "envolve um afetado heterozigoto e um homozigoto recessivo"),
    ("AA × aa", {"Aa": Fraction(1, 1)},
     "gera descendência inteiramente heterozigota"),
    ("AA × Aa", {"AA": Fraction(1, 2), "Aa": Fraction(1, 2)},
     "não produz nenhum descendente homozigoto recessivo"),
    ("AA × AA", {"AA": Fraction(1, 1)},
     "gera descendência inteiramente homozigota dominante"),
    ("aa × aa", {"aa": Fraction(1, 1)},
     "gera descendência inteiramente homozigota recessiva"),
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
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


def _inicial_maiuscula(t: str) -> str:
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


def _pct(f: Fraction) -> str:
    """Formata fração como porcentagem, no padrão brasileiro."""
    v = float(f) * 100
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}%"
    return f"{v:.1f}".replace(".", ",") + "%"


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
    # O teste de português só exige número no fim da explicação quando
    # a resposta é NUMÉRICA. "trissomia do cromossomo 18" tem dígito
    # mas é textual — daí a checagem pelo formato, não pela presença
    # de algarismo.
    _txt = str(correta).strip()
    _so_numero = bool(re.fullmatch(r'[\d\s.,%+\-/]+', _txt))
    return {
        "enunciado":         enunciado,
        "alternativas":      alternativas,
        "gabarito":          gabarito,
        "explicacao":        explicacao,
        "topico":            topico,
        "tipo_resposta":     "numerica" if _so_numero else "textual",
        "tem_elemento_visual": False,
    }


# ══════════════════════════════════════════════════════════
#  TEMPLATES — PADRÕES DE HERANÇA
# ══════════════════════════════════════════════════════════

def gerar_padrao_por_marca(rng):
    """
    Dada a marca observada numa família, qual o padrão de herança?

    É o formato mais cobrado: o aluno lê a descrição do heredograma e
    deduz o padrão, sem precisar da imagem.
    """
    padrao, art, marca, sexos, exemplos, armadilha = rng.choice(PADROES)

    CENARIOS = [
        f"Em uma família, observa-se o seguinte padrão: {marca}.",
        f"O estudo de um heredograma revela que {marca}.",
        f"Ao analisar a distribuição de uma característica em várias "
        f"gerações, verifica-se que {marca}.",
        f"Uma anomalia genética distribui-se assim numa família: {marca}.",
        f"O aconselhamento genético de uma família registra que {marca}.",
    ]
    COMANDOS = [
        "Esse padrão corresponde à herança:",
        "Assinale a alternativa que identifica o padrão de herança.",
        "Trata-se de herança:",
        "Assinale a alternativa com o padrão correspondente.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = padrao
    distratores = [p[0] for p in PADROES if p[0] != padrao]
    distratores += ["mitocondrial", "poligênica multifatorial",
                    "por imprinting genômico"]

    explicacao = (
        f"Trata-se de {padrao}: {marca}. Além disso, {sexos}. "
        f"Convém lembrar que {armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (padrões de herança)", rng)
    if q:
        q["_fato"] = f"padrao:{padrao}"
    return q


def gerar_marca_por_padrao(rng):
    """Qual a marca característica de determinado padrão?"""
    padrao, art, marca, sexos, exemplos, armadilha = rng.choice(PADROES)

    CENARIOS = [
        f"Considere {art}.",
        f"Entre os padrões de herança monogênica encontra-se {art}.",
        f"Um estudante revisa as características {_com_preposicao('de', art)}.",
        f"O aconselhamento genético exige reconhecer {art} em um "
        f"heredograma.",
    ]
    COMANDOS = [
        "Assinale a alternativa que descreve sua marca no heredograma.",
        "Sua característica distintiva é que:",
        "Como esse padrão se manifesta em um heredograma?",
        "Assinale a alternativa com a descrição correta.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = marca
    distratores = [p[2] for p in PADROES if p[2] != marca]
    distratores += [
        "o fenótipo é transmitido exclusivamente pela linhagem materna, "
        "a todos os descendentes",
        "a expressão depende da soma de vários genes e de fatores "
        "ambientais",
    ]

    explicacao = (
        f"{_inicial_maiuscula(art)} caracteriza-se assim: {marca}. "
        f"Quanto à distribuição por sexo, {sexos}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (padrões de herança)", rng)
    if q:
        q["_fato"] = f"padrao:{padrao}"
    return q


def gerar_doenca_por_padrao(rng):
    """Qual doença segue determinado padrão de herança?"""
    padrao, art, marca, sexos, exemplos, armadilha = rng.choice(PADROES)
    exemplo = rng.choice(exemplos)

    modo = rng.choice(["padrao_para_doenca", "doenca_para_padrao"])

    if modo == "padrao_para_doenca":
        CENARIOS = [
            f"Considere as doenças que seguem {art}.",
            f"Um estudante lista exemplos de condições com {art}.",
            f"Entre as doenças monogênicas, algumas seguem {art}.",
        ]
        COMANDOS = [
            "Assinale a alternativa com um exemplo desse padrão.",
            "Qual das condições abaixo segue esse padrão?",
            "Um exemplo é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = exemplo
        distratores = []
        for p in PADROES:
            if p[0] == padrao:
                continue
            distratores.extend(p[4])
        rng.shuffle(distratores)
    else:
        CENARIOS = [
            f"Considere o padrão de herança da seguinte condição: "
            f"{exemplo}.",
            f"Um paciente recebe o diagnóstico da seguinte condição: "
            f"{exemplo}.",
            f"O aconselhamento genético de uma família aborda a seguinte "
            f"condição: {exemplo}.",
        ]
        COMANDOS = [
            "Assinale a alternativa com seu padrão de herança.",
            "Essa condição segue herança:",
            "Qual o padrão de herança dessa condição?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = padrao
        distratores = [p[0] for p in PADROES if p[0] != padrao]
        distratores += ["mitocondrial", "poligênica multifatorial"]

    explicacao = (
        f"{_inicial_maiuscula(exemplo)} segue {padrao}, em que {marca}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Genética (doenças monogênicas)", rng)
    if q:
        q["_fato"] = f"doenca:{padrao}"
    return q


def gerar_exclusao_ligado_x(rng):
    """
    A regra de ouro: transmissão homem para homem exclui ligação ao X.

    É o critério que separa autossômica dominante de dominante ligada
    ao X, e cai com frequência.
    """
    modo = rng.choice(["qual_conclusao", "por_que"])

    if modo == "qual_conclusao":
        CENARIOS = [
            "Em um heredograma, observa-se um homem afetado cujo filho, "
            "também do sexo masculino, apresenta a mesma condição.",
            "A análise de uma família revela transmissão da "
            "característica de pai para filho homem.",
            "Um heredograma mostra que a anomalia passou de um homem "
            "afetado para seu filho do sexo masculino.",
            "Numa genealogia, o pai afetado teve um filho homem também "
            "afetado.",
            "Duas gerações consecutivas de homens da mesma linhagem "
            "apresentam a característica, de pai para filho.",
            "O estudo genealógico documenta um homem afetado cujo "
            "descendente masculino direto também o é.",
            "Uma família apresenta a condição em avô, pai e filho, "
            "todos do sexo masculino.",
        ]
        COMANDOS = [
            "Esse achado permite EXCLUIR a herança:",
            "Assinale a alternativa com o padrão que fica excluído.",
            "Que padrão de herança esse achado descarta?",
            "Assinale a alternativa que esse achado elimina.",
            "Esse achado torna impossível a herança:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "ligada ao cromossomo X"
        distratores = [
            "autossômica dominante",
            "autossômica recessiva",
            "poligênica multifatorial",
            "com penetrância incompleta",
            "com expressividade variável",
        ]
        explicacao = (
            "A transmissão de HOMEM PARA HOMEM exclui a herança ligada "
            "ao cromossomo X. O pai transmite ao filho do sexo masculino "
            "apenas o cromossomo Y — o X vai para as filhas. Portanto, "
            "uma característica ligada ao X jamais passa de pai para "
            "filho homem. É o critério que separa a herança autossômica "
            "dominante da dominante ligada ao X."
        )
    else:
        # O enunciado NÃO pode repetir o vocabulário do gabarito: com
        # "pai", "filho do sexo masculino" e "cromossomo" no texto, a
        # estratégia "marque a alternativa que ecoa o comando" acertava
        # 100% das vezes.
        #
        # Aqui o cenário usa termos genéricos — "genitor", "descendente
        # masculino" — e o gabarito, os termos técnicos.
        CENARIOS = [
            "Certo achado em heredograma permite descartar de imediato "
            "a hipótese de ligação ao X.",
            "Uma observação genealógica basta para eliminar a "
            "possibilidade de o gene estar no X.",
            "Há um critério simples que afasta a hipótese de ligação ao "
            "X na análise de uma genealogia.",
            "Um geneticista descarta a ligação ao X apenas com base na "
            "distribuição da característica entre gerações.",
        ]
        COMANDOS = [
            "Assinale a alternativa que apresenta esse critério.",
            "Esse critério consiste em observar:",
            "Qual achado permite essa exclusão?",
            "Assinale a alternativa com o achado correspondente.",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        # A correta tinha 83 caracteres e o distrator mais longo, 67:
        # marcar a maior acertava 100% das vezes. Enxugada para 54, fica
        # no meio da faixa dos distratores (48 a 63).
        correta = ("a transmissão de um homem afetado para seu "
                   "filho homem")
        distratores = [
            "a ocorrência da característica em mulheres de todas as "
            "gerações",
            "o predomínio de indivíduos afetados no sexo masculino",
            "a presença de consanguinidade entre os genitores",
            "o aparecimento da característica em gerações alternadas",
            "a transmissão de uma mulher afetada a todos os "
            "descendentes",
        ]
        explicacao = (
            "O critério é a transmissão de um homem afetado para seu "
            "filho do sexo masculino. O pai transmite ao filho homem "
            "apenas o cromossomo Y — o X paterno vai para as filhas. "
            "Logo, uma característica ligada ao X jamais passa de pai "
            "para filho homem, e observar essa transmissão exclui a "
            "hipótese."
        )

    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (análise de heredograma)", rng)
    if q:
        q["_fato"] = f"exclusao:{modo}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — PROBABILIDADE
# ══════════════════════════════════════════════════════════

def gerar_probabilidade_cruzamento(rng):
    """
    Probabilidade de determinado genótipo ou fenótipo na descendência.

    Os distratores reproduzem erros reais: somar em vez de multiplicar,
    confundir portador com afetado, esquecer que o heterozigoto conta.
    """
    cruzamento, descendencia, comentario = rng.choice(CRUZAMENTOS)
    alvo = rng.choice(list(descendencia))

    CENARIOS = [
        f"Um casal apresenta o seguinte cruzamento genotípico: "
        f"{cruzamento}.",
        f"Considere o cruzamento {cruzamento} para um gene autossômico.",
        f"Em um cruzamento monogênico, os genitores têm genótipos "
        f"{cruzamento}.",
        f"O aconselhamento genético de um casal parte do cruzamento "
        f"{cruzamento}.",
        f"Um quadro de Punnett é construído para o cruzamento "
        f"{cruzamento}.",
        f"Dois indivíduos com genótipos {cruzamento} têm descendência.",
        f"Ao analisar a segregação de um gene autossômico, considera-se "
        f"o cruzamento {cruzamento}.",
        f"Um estudante monta o quadro de Punnett para {cruzamento}.",
    ]
    COMANDOS = [
        f"A probabilidade de um descendente apresentar o genótipo "
        f"{alvo} é de:",
        f"Qual a probabilidade de descendente com genótipo {alvo}?",
        f"A chance de um filho ter genótipo {alvo} corresponde a:",
        f"Espera-se que a proporção de descendentes {alvo} seja de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = descendencia[alvo]
    # Erros reais: trocar por outra proporção da mesma tabela, dobrar,
    # somar as duas metades, ou responder o complementar
    candidatos = [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4),
                  Fraction(1, 1), Fraction(1, 8), Fraction(2, 3),
                  Fraction(1, 3), Fraction(0, 1)]
    distratores = [c for c in candidatos if c != correta]

    detalhe = ", ".join(f"{g}: {_pct(p)}" for g, p in descendencia.items())
    explicacao = (
        f"No cruzamento {cruzamento}, a descendência esperada é — "
        f"{detalhe}. Portanto, a probabilidade de {alvo} é de "
        # Termina no RESULTADO, não no comentário: o teste de português
        # verifica isso, e o aluno lê a última linha.
        f"Esse cruzamento {comentario}, e a probabilidade de {alvo} é "
        f"de {_pct(correta)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (probabilidade)", rng, formatador=_pct)
    if q:
        q["_fato"] = f"prob:{cruzamento}:{alvo}"
    return q


def gerar_probabilidade_afetado(rng):
    """
    Probabilidade de filho afetado, considerando o padrão de herança.

    Cobre o caso mais frequente na clínica: casal de portadores em
    herança autossômica recessiva, e mulher portadora em herança
    recessiva ligada ao X.
    """
    caso = rng.choice(["ar_portadores", "ad_heterozigoto", "xr_portadora"])

    if caso == "ar_portadores":
        CENARIOS = [
            "Um casal saudável já teve um filho com fibrose cística, "
            "que é doença autossômica recessiva.",
            "Ambos os membros de um casal são portadores heterozigotos "
            "de uma doença autossômica recessiva.",
            "Um casal descobre, em teste genético, que ambos carregam "
            "um alelo recessivo para a mesma doença.",
            "Dois primos em primeiro grau, ambos heterozigotos para a "
            "mesma doença autossômica recessiva, planejam ter filhos.",
            "O rastreamento pré-concepcional identifica ambos os "
            "parceiros como portadores da mesma mutação recessiva.",
            "Um casal com histórico familiar de anemia falciforme "
            "descobre que ambos têm o traço falciforme.",
        ]
        COMANDOS = [
            "A cada nova gestação, a probabilidade de filho afetado é de:",
            "A chance de a próxima criança ser afetada é de:",
            "Para cada gestação, o risco de filho afetado corresponde a:",
        ]
        correta = Fraction(1, 4)
        explicacao = (
            "Ambos os genitores são heterozigotos (Aa × Aa). A "
            "descendência esperada é 25% AA, 50% Aa e 25% aa. Como "
            "cada gestação é um evento independente, o risco NÃO muda "
            "por causa dos filhos anteriores: permanece em 25%."
        )
    elif caso == "ad_heterozigoto":
        CENARIOS = [
            "Um homem com acondroplasia, doença autossômica dominante, "
            "é heterozigoto e tem parceira sem a condição.",
            "Uma mulher heterozigota para doença de Huntington, de "
            "herança autossômica dominante, planeja engravidar de um "
            "homem não afetado.",
            "Um paciente heterozigoto para uma doença autossômica "
            "dominante tem parceiro homozigoto normal.",
            "Um homem com neurofibromatose tipo 1, em heterozigose, "
            "planeja ter filhos com mulher não afetada.",
            "Uma paciente heterozigota para condição autossômica "
            "dominante busca aconselhamento genético.",
        ]
        COMANDOS = [
            "A probabilidade de filho afetado é de:",
            "A chance de transmitir a condição a cada filho é de:",
            "Para cada gestação, o risco de filho afetado é de:",
        ]
        correta = Fraction(1, 2)
        explicacao = (
            "O cruzamento é Aa × aa. Metade dos descendentes recebe o "
            "alelo dominante e será afetada: 50% Aa e 50% aa. Na herança "
            "autossômica dominante, basta uma cópia para manifestar a "
            "condição."
        )
    else:
        CENARIOS = [
            "Uma mulher portadora de hemofilia A, doença recessiva "
            "ligada ao X, tem parceiro não afetado.",
            "Uma mulher heterozigota para daltonismo, de herança "
            "recessiva ligada ao X, planeja engravidar de um homem sem "
            "a condição.",
            "Uma portadora de distrofia muscular de Duchenne tem "
            "parceiro sem a doença.",
            "Uma mulher cujo irmão tem hemofilia descobre-se portadora "
            "e planeja engravidar de homem não afetado.",
            "O teste genético confirma que uma gestante é heterozigota "
            "para condição recessiva ligada ao X.",
        ]
        COMANDOS = [
            "Considerando apenas os filhos do sexo MASCULINO, a "
            "probabilidade de um deles ser afetado é de:",
            "Entre os filhos do sexo MASCULINO, a chance de afetado é de:",
            "A probabilidade de um filho HOMEM ser afetado é de:",
        ]
        correta = Fraction(1, 2)
        explicacao = (
            "A mãe é portadora (X^A X^a) e o pai é normal (X^A Y). Cada "
            "filho do sexo masculino recebe o Y do pai e um dos dois X "
            "da mãe — metade recebe o X com o alelo alterado e será "
            "afetado. Considerando TODOS os filhos, o risco é de 25%, "
            "porque metade das gestações resulta em menina."
        )

    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
    candidatos = [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4),
                  Fraction(1, 1), Fraction(1, 8), Fraction(1, 3),
                  Fraction(2, 3), Fraction(0, 1)]
    distratores = [c for c in candidatos if c != correta]

    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (probabilidade)", rng, formatador=_pct)
    if q:
        # Dois dos três casos têm resposta 50%. Sem a resposta na
        # chave, o lote trazia três questões com o mesmo gabarito.
        q["_fato"] = f"prob_afetado:{caso}|{_pct(correta)}"
    return q


# ══════════════════════════════════════════════════════════
#  ANEUPLOIDIAS
# ══════════════════════════════════════════════════════════
#
#  Fontes: Prepara Enem; Nav Dasa; InfoEscola; Osler Medicina;
#  Thompson & Thompson, Genética Médica.
#
#  ⚠️ Cri-du-chat NÃO entra aqui: é deleção, alteração
#  estrutural, e uma das fontes consultadas a classificava
#  erradamente como monossomia.
#
#  (síndrome, alteração, cariótipo, sexo, sinais, observação)
ANEUPLOIDIAS = [
    ("síndrome de Down", "trissomia do cromossomo 21",
     "47,XX,+21 ou 47,XY,+21", "ambos os sexos",
     "hipotonia, prega palmar única, fácies característica e "
     "deficiência intelectual de grau variável",
     "é a trissomia autossômica mais frequente entre nascidos vivos, "
     "cerca de 1 para 700, com associação forte à idade materna "
     "avançada"),

    ("síndrome de Edwards", "trissomia do cromossomo 18",
     "47,XX,+18 ou 47,XY,+18", "ambos os sexos",
     "baixo peso ao nascer, mãos cerradas com sobreposição de dedos e "
     "cardiopatia",
     "é compatível com o nascimento, mas a sobrevida costuma ser "
     "inferior a um ano"),

    ("síndrome de Patau", "trissomia do cromossomo 13",
     "47,XX,+13 ou 47,XY,+13", "ambos os sexos",
     "holoprosencefalia, fenda labiopalatina, microftalmia e "
     "polidactilia",
     "é a terceira trissomia autossômica compatível com nascimento "
     "vivo, e a mais rara delas"),

    ("síndrome de Turner", "monossomia do cromossomo X",
     "45,X", "apenas o sexo feminino",
     "baixa estatura, pescoço alado, disgenesia gonadal e "
     "infertilidade",
     "é a ÚNICA monossomia viável em seres humanos"),

    ("síndrome de Klinefelter", "trissomia dos cromossomos sexuais",
     "47,XXY", "apenas o sexo masculino",
     "estatura acima da média, testículos pequenos, infertilidade e "
     "ginecomastia em parte dos casos",
     "o número de autossomos é normal; o excesso está nos "
     "cromossomos sexuais"),

    ("síndrome do triplo X", "trissomia do cromossomo X",
     "47,XXX", "apenas o sexo feminino",
     "manifestações discretas, por vezes apenas estatura elevada",
     "muitas portadoras não recebem diagnóstico ao longo da vida"),

    ("síndrome do duplo Y", "trissomia dos cromossomos sexuais",
     "47,XYY", "apenas o sexo masculino",
     "estatura elevada e, em parte dos casos, dificuldades de "
     "aprendizagem",
     "a fertilidade costuma ser preservada"),
]


def gerar_aneuploidia(rng):
    """Identificar a alteração cromossômica — nível médio e ENEM."""
    sind, alt, cario, sexo, sinais, obs = rng.choice(ANEUPLOIDIAS)
    modo = rng.choice(["pela_sindrome", "pelo_cariotipo", "pelo_sexo"])

    if modo == "pela_sindrome":
        CENARIOS = [
            f"Um exame de cariótipo é solicitado para investigar "
            f"suspeita de {sind}.",
            f"O aconselhamento genético de uma família aborda a "
            f"{sind}.",
            f"Um recém-nascido é encaminhado à genética com hipótese "
            f"diagnóstica de {sind}.",
        ]
        COMANDOS = [
            "Essa condição decorre de:",
            "Assinale a alternativa com a alteração cromossômica "
            "correspondente.",
            "Qual a alteração cromossômica envolvida?",
        ]
        correta = alt
        distratores = [a[1] for a in ANEUPLOIDIAS if a[1] != alt]
        distratores += ["deleção do braço curto do cromossomo 5",
                        "translocação recíproca equilibrada"]
    elif modo == "pelo_cariotipo":
        CENARIOS = [
            f"O resultado de um cariótipo com bandeamento G indica: "
            f"{cario}.",
            f"Um laudo citogenético registra o seguinte cariótipo: "
            f"{cario}.",
            f"A análise cromossômica de um paciente revelou o "
            f"cariótipo {cario}.",
        ]
        COMANDOS = [
            "Esse achado corresponde à:",
            "Assinale a alternativa que identifica a síndrome.",
            "Trata-se de qual condição?",
        ]
        correta = sind
        distratores = [a[0] for a in ANEUPLOIDIAS if a[0] != sind]
        distratores += ["síndrome de Cri-du-chat", "síndrome do X frágil"]
    else:
        CENARIOS = [
            f"Considere a {sind}, decorrente de {alt}.",
            f"Um estudante revisa as características da {sind}.",
            f"A {sind} tem apresentação clínica característica.",
        ]
        COMANDOS = [
            "Essa condição acomete:",
            "Assinale a alternativa que indica o sexo afetado.",
            "Quanto ao sexo dos afetados, essa síndrome atinge:",
        ]
        correta = sexo
        distratores = ["ambos os sexos", "apenas o sexo feminino",
                       "apenas o sexo masculino"]
        distratores = [d for d in distratores if d != correta]
        distratores += ["preferencialmente o sexo masculino, sem "
                        "exclusividade",
                        "preferencialmente o sexo feminino, sem "
                        "exclusividade"]

    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
    explicacao = (
        f"A {sind} decorre de {alt}, com cariótipo {cario}, e acomete "
        f"{sexo}. Entre os sinais: {sinais}. Convém notar que {obs}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Genética (aneuploidias)", rng)
    if q:
        q["_fato"] = f"aneuploidia:{sind}:{modo}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_GENETICA = {
    "padrao_por_marca":    gerar_padrao_por_marca,
    "marca_por_padrao":    gerar_marca_por_padrao,
    "doenca_por_padrao":   gerar_doenca_por_padrao,
    "exclusao_ligado_x":   gerar_exclusao_ligado_x,
    "prob_cruzamento":     gerar_probabilidade_cruzamento,
    "prob_afetado":        gerar_probabilidade_afetado,
    "aneuploidia":         gerar_aneuploidia,
}

TOPICOS_GENETICA = {
    "heranca": [
        "padrao_por_marca",
        "marca_por_padrao",
        "doenca_por_padrao",
        "exclusao_ligado_x",
    ],
    "probabilidade": [
        "prob_cruzamento",
        "prob_afetado",
    ],
    "citogenetica": [
        "aneuploidia",
    ],
}

PALAVRAS_CHAVE = {
    "padrao_por_marca":  ["padrao de heranca", "padroes de heranca",
                          "heredograma", "heredogramas", "autossomica",
                          "ligada ao x", "holandrica", "genealogia"],
    "marca_por_padrao":  ["padrao de heranca", "padroes de heranca",
                          "heredograma", "autossomica", "ligada ao x"],
    "doenca_por_padrao": ["doenca monogenica", "doencas monogenicas",
                          "fibrose cistica", "anemia falciforme",
                          "hemofilia", "daltonismo", "acondroplasia",
                          "huntington", "fenilcetonuria"],
    "exclusao_ligado_x": ["heredograma", "heredogramas", "ligada ao x",
                          "cromossomo x", "cromossomo y", "genealogia"],
    "prob_cruzamento":   ["quadro de punnett", "punnett", "cruzamento",
                          "genotipo", "heterozigoto", "homozigoto",
                          "segregacao", "mendel"],
    "aneuploidia":       ["aneuploidia", "aneuploidias", "trissomia",
                         "monossomia", "cariotipo", "sindrome de down",
                         "turner", "klinefelter", "patau", "edwards",
                         "citogenetica", "alteracao cromossomica"],
    "prob_afetado":      ["aconselhamento genetico", "risco de recorrencia",
                          "portador", "portadora", "heterozigoto",
                          "probabilidade genetica"],
}

CHAVES_GENERICAS = {
    "heranca", "padrao", "padroes", "gene", "genes", "alelo", "alelos",
    "probabilidade", "risco", "doenca", "doencas", "cromossomo",
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
    """Gera um lote de questões de genética."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_GENETICA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_GENETICA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_GENETICA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_GENETICA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # O peso reflete quantos FATOS DISTINTOS o veto de repetição
    # reconhece, não quantas variações o template produz — ver
    # comentário equivalente em gerador_embriologia.gerar_lote.
    LASTRO_POR_FATO = {
        "padrao_por_marca":  len(PADROES),
        "marca_por_padrao":  len(PADROES),
        "doenca_por_padrao": len(PADROES),
        "exclusao_ligado_x": 2,
        "prob_cruzamento":   sum(len(c[1]) for c in CRUZAMENTOS),
        "prob_afetado":      3,
        "aneuploidia":       len(ANEUPLOIDIAS) * 3,   # três modos
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
        q = TEMPLATES_GENETICA[nome](rng)
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
    print("  GERADOR DE GENÉTICA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
