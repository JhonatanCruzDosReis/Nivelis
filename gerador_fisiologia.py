"""
=============================================================
  GERADOR DE FISIOLOGIA
=============================================================
  Questões de fisiologia médica geradas proceduralmente, sem
  depender de livro nem de chamada a modelo.

  ESCOPO — o que este gerador faz e o que não faz:

    ✅ Relações de causa e efeito com direção estabelecida
       ("se a arteríola aferente contrai, o que acontece com
       a TFG?")
    ✅ Cálculo com fórmula consagrada (débito cardíaco,
       pressão arterial média, clearance)
    ✅ Classificação e mecanismo

    ❌ Conduta clínica, dose, diagnóstico
    ❌ Interpretação de exame aplicada a caso

  A separação não é por dificuldade: é porque um template
  errado gera centenas de questões erradas com a mesma
  confiança das certas, e em conduta clínica o custo disso
  não é o aluno perder ponto.

  VERIFICAÇÃO DAS FONTES

  Cada bloco de fatos foi confirmado em fonte de REFERÊNCIA
  (manual médico, material universitário, tratado) — nunca em
  site de questões ou fórum. Na primeira verificação, uma
  fonte desse tipo afirmava o INVERSO do correto sobre a
  curva de dissociação da hemoglobina. As fontes estão
  registradas em fisiologia/_fontes.md.

  USO:
      from gerador_fisiologia import gerar_lote, gerar_para_api
      questoes = gerar_lote(20, seed=42)
=============================================================
"""

import random
import re
import unicodedata

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


# ══════════════════════════════════════════════════════════
#  BASE DE FATOS — cada tabela cita a fonte
# ══════════════════════════════════════════════════════════

# ── Curva de dissociação da oxi-hemoglobina ──
#
# Fontes: Manual MSD (profissional), "Curva de dissociação da
# oxi-hemoglobina"; UFRGS/LACVET, "O papel do 2,3-DPG no metabolismo
# das hemácias"; Guyton & Hall, Tratado de Fisiologia Médica.
#
# REGRA: direita = MENOR afinidade = mais liberação de O₂ nos tecidos.
# É contraintuitivo, e por isso mesmo cobrado.
FATORES_CURVA_HB = [
    # (fator, direção, afinidade, contexto onde ocorre)
    ("aumento da concentração de íons hidrogênio (acidose)",
     "direita", "menor", "no músculo em exercício, que produz ácido láctico"),
    ("queda do pH sanguíneo",
     "direita", "menor", "na acidose metabólica"),
    ("aumento da pressão parcial de dióxido de carbono",
     "direita", "menor", "nos tecidos com metabolismo elevado"),
    ("elevação da temperatura corporal",
     "direita", "menor", "na febre e no exercício intenso"),
    ("aumento do 2,3-difosfoglicerato nos eritrócitos",
     "direita", "menor", "na adaptação à altitude e na anemia crônica"),
    ("alcalose",
     "esquerda", "maior", "após administração de bicarbonato de sódio"),
    ("elevação do pH sanguíneo",
     "esquerda", "maior", "na hiperventilação"),
    ("redução da pressão parcial de dióxido de carbono",
     "esquerda", "maior", "na alcalose respiratória"),
    ("hipotermia",
     "esquerda", "maior", "na parada cardiorrespiratória com resfriamento"),
    ("redução do 2,3-difosfoglicerato",
     "esquerda", "maior", "no sangue estocado para transfusão"),
    ("presença de monóxido de carbono",
     "esquerda", "maior", "na intoxicação por CO"),
]

# ── Regulação da taxa de filtração glomerular ──
#
# Fontes: UFSM (Fisiologia Renal); UFF/webquest; UFRJ/LASSBio;
# Silverthorn, Fisiologia Humana, 7ª ed., Artmed 2017.
#
# REGRA: aferente e eferente têm efeitos INVERTIDOS sobre a TFG.
FATORES_TFG = [
    # (alteração, efeito na TFG, mecanismo)
    ("vasodilatação da arteríola aferente", "aumenta",
     "mais sangue chega ao glomérulo, elevando a pressão hidrostática capilar"),
    ("vasoconstrição da arteríola aferente", "diminui",
     "menos sangue chega ao glomérulo, reduzindo a pressão hidrostática capilar"),
    ("vasoconstrição da arteríola eferente", "aumenta",
     "o sangue encontra resistência para deixar o glomérulo, elevando a "
     "pressão hidrostática capilar"),
    ("vasodilatação da arteríola eferente", "diminui",
     "o sangue deixa o glomérulo com facilidade, reduzindo a pressão "
     "hidrostática capilar"),
    ("aumento da pressão oncótica do plasma", "diminui",
     "a força que se opõe à filtração torna-se maior"),
    ("queda da concentração plasmática de albumina", "aumenta",
     "a pressão oncótica que se opõe à filtração diminui"),
    ("obstrução ureteral com elevação da pressão na cápsula de Bowman", "diminui",
     "a contrapressão na cápsula reduz o gradiente efetivo de filtração"),
]


# ── Sistema renina-angiotensina-aldosterona ──
#
# Fontes: Guyton & Hall, Tratado de Fisiologia Médica (13ª ed.);
# Acta Médica Portuguesa 2010;23(4):677-688.
#
# A ordem das etapas é o que a prova cobra, junto com o local de cada uma.
ETAPAS_SRAA = [
    # (ordem, evento, local)
    (1, "secreção de renina", "células justaglomerulares do rim"),
    (2, "conversão de angiotensinogênio em angiotensina I", "plasma"),
    (3, "conversão de angiotensina I em angiotensina II",
        "endotélio dos capilares pulmonares, pela ECA"),
    (4, "secreção de aldosterona", "córtex da glândula suprarrenal"),
    (5, "reabsorção de sódio e água", "néfron distal e ducto coletor"),
]

# Situações clínicas que ativam ou inibem o SRAA, com o mecanismo.
# Aqui a questão exige APLICAR o mecanismo, não recitar a seta.
SITUACOES_SRAA = [
    ("hemorragia de grande volume", "ativa",
     "a queda do volume circulante reduz a perfusão renal, estimulando as "
     "células justaglomerulares"),
    ("desidratação por diarreia prolongada", "ativa",
     "a perda de líquido reduz o volume circulante e a perfusão renal"),
    ("dieta com restrição intensa de sódio", "ativa",
     "a menor oferta de sódio à mácula densa estimula a liberação de renina"),
    ("estenose da artéria renal", "ativa",
     "a redução do fluxo para o rim é interpretada como hipovolemia, "
     "mesmo com volemia sistêmica normal"),
    ("infusão intravenosa de grande volume de salina", "inibe",
     "a expansão do volume circulante aumenta a perfusão renal e reduz o "
     "estímulo à secreção de renina"),
    ("dieta com alto teor de sódio", "inibe",
     "a maior oferta de sódio à mácula densa reduz a liberação de renina"),
]

# Efeitos da angiotensina II e da aldosterona — separados de propósito,
# porque confundi-los é erro frequente.
EFEITOS_SRAA = [
    ("angiotensina II", "vasoconstrição arteriolar sistêmica", True),
    ("angiotensina II", "constrição preferencial da arteríola eferente", True),
    ("angiotensina II", "estímulo à secreção de aldosterona", True),
    ("angiotensina II", "estímulo à sede e à secreção de ADH", True),
    ("aldosterona", "aumento da reabsorção de sódio no néfron distal", True),
    ("aldosterona", "aumento da secreção de potássio na urina", True),
    ("aldosterona", "aumento da secreção de hidrogênio na urina", True),
]


# ── Potencial de ação ──
#
# Fontes: Silverthorn, Fisiologia Humana; mkfisiologia.com (Profa. Mirian
# Ayumi Kurauti, UEM); Wikipédia (Potencial de ação). As três concordam.
FASES_PA = [
    # (ordem, fase, íon, movimento, mecanismo)
    (1, "despolarização", "sódio", "influxo",
     "abertura dos canais de sódio dependentes de voltagem"),
    (2, "repolarização", "potássio", "efluxo",
     "inativação dos canais de sódio e abertura dos canais de potássio"),
    (3, "hiperpolarização", "potássio", "efluxo residual",
     "fechamento lento dos canais de potássio, que deixam sair mais íons "
     "do que o necessário"),
    (4, "retorno ao potencial de repouso", "sódio e potássio", "transporte ativo",
     "ação da bomba de sódio e potássio, que restaura os gradientes"),
]

# Períodos refratários — a distinção é frequentemente cobrada
REFRATARIOS = [
    ("absoluto",
     "nenhum estímulo, por mais intenso que seja, é capaz de gerar novo "
     "potencial de ação",
     "os canais de sódio dependentes de voltagem estão com a comporta de "
     "inativação fechada"),
    ("relativo",
     "um novo potencial de ação pode ser gerado, desde que o estímulo seja "
     "mais intenso que o habitual",
     "parte dos canais de sódio já retornou ao estado fechado, mas os canais "
     "de potássio ainda abertos opõem-se à despolarização"),
]

# Propriedades da condução — comparação entre os dois tipos de axônio
CONDUCAO = [
    ("axônio mielinizado", "saltatória",
     "o impulso salta entre os nódulos de Ranvier", "mais rápida"),
    ("axônio amielínico", "contínua",
     "a despolarização percorre toda a extensão da membrana", "mais lenta"),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _frase(t) -> str:
    """Capitaliza a primeira letra e garante ponto final."""
    s = " ".join(str(t).split())
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return s if s[-1] in ".!?" else s + "."


def _fmt(v) -> str:
    """Formata número no padrão brasileiro."""
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return f"{int(round(v)):,}".replace(",", ".")
        return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{v:,}".replace(",", ".")


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str):
    """
    Monta a questão com cinco alternativas embaralhadas.

    Rejeita o item se não houver quatro distratores distintos: alternativa
    repetida reduz a questão a quatro opções efetivas.
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
    return {
        "enunciado":         enunciado,
        "alternativas":      alternativas,
        "gabarito":          gabarito,
        "explicacao":        explicacao,
        "topico":            topico,
        "tem_elemento_visual": False,
    }


# ══════════════════════════════════════════════════════════
#  TEMPLATES — HEMATOLOGIA / RESPIRATÓRIO
# ══════════════════════════════════════════════════════════

def gerar_curva_hb_direcao(rng):
    """
    Dado um fator, para que lado a curva se desloca?

    A relação é contraintuitiva — desvio à direita significa MENOR
    afinidade — e por isso é das mais cobradas.
    """
    fator, direcao, afinidade, contexto = rng.choice(FATORES_CURVA_HB)

    CENARIOS = [
        f"Durante a avaliação de um paciente, observa-se {fator}.",
        f"Um estudo de fisiologia respiratória analisa o efeito do "
        f"seguinte fator sobre o transporte de oxigênio: {fator}.",
        f"Considere a situação em que ocorre {fator}, o que se verifica "
        f"{contexto}.",
        f"Na análise do transporte de oxigênio pelo sangue, avalia-se o "
        f"efeito de {fator}.",
    ]
    PERGUNTAS = [
        "Sobre a curva de dissociação da oxi-hemoglobina, é correto afirmar que:",
        "Em relação à curva de dissociação da oxi-hemoglobina, assinale a "
        "alternativa correta.",
        "Qual o efeito esperado sobre a curva de dissociação da "
        "oxi-hemoglobina?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(PERGUNTAS)}"

    oposta = "esquerda" if direcao == "direita" else "direita"
    afin_oposta = "maior" if afinidade == "menor" else "menor"

    correta = (f"a curva desloca-se para a {direcao}, com {afinidade} "
               f"afinidade da hemoglobina pelo oxigênio")
    distratores = [
        f"a curva desloca-se para a {oposta}, com {afin_oposta} afinidade "
        f"da hemoglobina pelo oxigênio",
        # Erro clássico: acertar a direção e inverter a afinidade
        f"a curva desloca-se para a {direcao}, com {afin_oposta} afinidade "
        f"da hemoglobina pelo oxigênio",
        f"a curva desloca-se para a {oposta}, com {afinidade} afinidade "
        f"da hemoglobina pelo oxigênio",
        "a curva não sofre deslocamento, pois a afinidade da hemoglobina "
        "pelo oxigênio é fixa",
        "a curva torna-se linear, perdendo o formato sigmoide característico",
    ]

    entrega = ("facilitando" if afinidade == "menor" else "dificultando")
    explicacao = (
        f"{_frase(fator)} desloca a curva para a {direcao}. Deslocamento "
        f"à {direcao} significa {afinidade} afinidade da hemoglobina pelo "
        f"oxigênio, {entrega} sua liberação nos tecidos. "
        f"A relação é contraintuitiva e por isso costuma ser cobrada: "
        f"direita não significa 'mais oxigênio ligado', e sim mais oxigênio "
        f"entregue."
    )
    # A chave é a DIREÇÃO, e é a mesma nos dois templates da curva.
    #
    # Um deles pergunta para que lado a curva vai, dado o fator; o outro
    # dá o lado e pede o fator — e, para dar, escreve no enunciado que
    # "a curva se desloca para a esquerda, situação em que a afinidade
    # torna-se maior". Esse enunciado é exatamente a resposta do
    # primeiro. Num caderno de medicina as duas caíram juntas, e a
    # questão 29 eliminava duas das cinco alternativas da 28.
    #
    # Com a chave compartilhada, cada direção entra uma vez só.
    q = _montar(enunciado, correta, distratores, explicacao,
                "Fisiologia respiratória (transporte de gases)", rng)
    if q:
        q["_fato"] = f"curva_hb_direcao:{fator[:24]}"
    return q


def gerar_curva_hb_fator(rng):
    """Qual fator produz determinado deslocamento?"""
    direcao = rng.choice(["direita", "esquerda"])
    mesma = [f for f in FATORES_CURVA_HB if f[1] == direcao]
    outra = [f for f in FATORES_CURVA_HB if f[1] != direcao]
    if len(mesma) < 1 or len(outra) < 4:
        return None

    correto = rng.choice(mesma)
    rng.shuffle(outra)

    # O enunciado incorpora o CONTEXTO do fator sorteado. Sem isso, o
    # texto dependia apenas da direção — duas variações possíveis —, e
    # o template rendia 4 enunciados distintos no total.
    #
    # E NÃO diz a afinidade. Dois cenários diziam ("para a esquerda, com
    # afinidade maior da hemoglobina pelo oxigênio"), e o outro template
    # da curva pergunta exatamente esse par: dada a acidose, para que
    # lado a curva vai e o que acontece com a afinidade. Caídas no mesmo
    # caderno, uma respondia a outra — a questão 29 de um simulado de
    # medicina eliminava duas das cinco alternativas da 28.
    #
    # A direção sozinha não entrega nada: continua sendo preciso saber
    # qual fator a produz, que é o que se pergunta aqui.
    CENARIOS = [
        f"A curva de dissociação da oxi-hemoglobina pode deslocar-se para "
        f"a {direcao}, o que altera a entrega de oxigênio aos tecidos.",
        f"Em determinadas condições, observa-se deslocamento da curva de "
        f"dissociação da oxi-hemoglobina para a {direcao} — situação "
        f"verificada, por exemplo, {correto[3]}.",
        f"Um paciente apresenta deslocamento da curva de dissociação da "
        f"oxi-hemoglobina para a {direcao}.",
        f"Durante a análise gasométrica, identifica-se padrão compatível "
        f"com deslocamento da curva de dissociação para a {direcao}, "
        f"condição observada {correto[3]}.",
        f"O deslocamento da curva de dissociação da oxi-hemoglobina para "
        f"a {direcao} é achado frequente na prática clínica.",
    ]
    PERGUNTAS = [
        "Assinale a alternativa que apresenta um fator responsável por "
        "esse deslocamento.",
        "Qual dos fatores abaixo produz esse deslocamento?",
        "Entre os fatores listados, qual determina esse comportamento da "
        "curva?",
        "Assinale a alternativa que indica uma causa desse deslocamento.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(PERGUNTAS)}"

    correta = correto[0]
    distratores = [f[0] for f in outra[:5]]

    explicacao = (
        f"{_frase(correto[0])} desloca a curva para a {direcao}, reduzindo "
        f"a afinidade da hemoglobina pelo oxigênio."
        if direcao == "direita" else
        f"{_frase(correto[0])} desloca a curva para a {direcao}, aumentando "
        f"a afinidade da hemoglobina pelo oxigênio."
    )
    explicacao += (" As demais alternativas produzem deslocamento no "
                   "sentido oposto.")
    q = _montar(enunciado, correta, distratores, explicacao,
                "Fisiologia respiratória (transporte de gases)", rng)
    if q:
        q["_fato"] = f"curva_hb_fator:{correto[0][:24]}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — RENAL
# ══════════════════════════════════════════════════════════

def gerar_tfg_efeito(rng):
    """
    Dada uma alteração hemodinâmica, o que acontece com a TFG?

    Aferente e eferente agem em direções OPOSTAS — é o ponto que a
    prova cobra, e o erro mais comum é tratá-las como equivalentes.
    """
    alteracao, efeito, mecanismo = rng.choice(FATORES_TFG)

    CENARIOS = [
        f"Em um estudo de hemodinâmica renal, induz-se {alteracao}.",
        f"Considere um néfron no qual ocorre {alteracao}.",
        f"Durante a investigação da função renal, observa-se {alteracao}.",
        f"A avaliação da função glomerular identifica {alteracao}.",
    ]
    # O comando determina o MODO VERBAL das alternativas. Misturar os
    # dois produzia "é correto afirmar que a TFG aumente" — o comando
    # pede indicativo, a alternativa veio no subjuntivo.
    #
    # Cada pergunta carrega o modo que exige, e as alternativas são
    # construídas de acordo.
    PERGUNTAS = [
        ("Quanto à taxa de filtração glomerular, espera-se que ela:",
         "subjuntivo"),
        ("O efeito esperado sobre a taxa de filtração glomerular é que ela:",
         "subjuntivo"),
        ("Sobre a taxa de filtração glomerular, é correto afirmar que ela:",
         "indicativo"),
        ("Nessa condição, a taxa de filtração glomerular:",
         "indicativo"),
    ]
    pergunta, modo = rng.choice(PERGUNTAS)
    enunciado = f"{rng.choice(CENARIOS)} {pergunta}"

    # "aumenta" e "diminui" têm sete letras; os distratores chegavam a
    # 73. As duas alternativas plausíveis eram sempre as duas mais
    # curtas, e o chute pela mais curta virava cara ou coroa entre elas —
    # 65% de acerto sem ler o enunciado.
    #
    # Agora as cinco opções têm a mesma forma (direção + consequência) e
    # comprimento parecido, com um distrator mais curto e outro mais
    # longo que a resposta, para que o tamanho não aponte nada.
    if modo == "subjuntivo":
        verbo, oposto = ("aumente", "diminua") if efeito == "aumenta" \
            else ("diminua", "aumente")
        FORMA = {
            "aumente": "aumente, elevando o volume de filtrado",
            "diminua": "diminua, reduzindo o volume de filtrado",
        }
        neutros = [
            "permaneça inalterada, apesar da hemodinâmica",
            "cesse por completo, com anúria imediata",
            "oscile sem direção previsível",
        ]
    else:
        verbo, oposto = ("aumenta", "diminui") if efeito == "aumenta" \
            else ("diminui", "aumenta")
        FORMA = {
            "aumenta": "aumenta, elevando o volume de filtrado",
            "diminui": "diminui, reduzindo o volume de filtrado",
        }
        neutros = [
            "permanece inalterada, apesar da hemodinâmica",
            "cessa por completo, com anúria imediata",
            "oscila sem direção previsível",
        ]
    condicional = f"{verbo} apenas se a pressão sistêmica subir"

    correta = FORMA[verbo]
    distratores = [FORMA[oposto]] + neutros + [condicional]

    # "faz a taxa de filtração glomerular diminui" — o verbo depois de
    # "fazer" vai no infinitivo, não no modo da alternativa.
    infinitivo = "aumentar" if verbo.startswith("aumen") else "diminuir"
    explicacao = (
        f"{_frase(alteracao)} faz a taxa de filtração glomerular "
        f"{infinitivo}: {mecanismo}. "
    )
    if "aferente" in alteracao or "eferente" in alteracao:
        explicacao += (
            "Vale lembrar que as duas arteríolas têm efeitos INVERTIDOS: "
            "constringir a aferente reduz a filtração, enquanto constringir "
            "a eferente a aumenta."
        )
    # O sujeito já está no comando ("...espera-se que ELA:"), então a
    # alternativa começa direto pelo verbo.
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia renal (filtração glomerular)", rng)


def gerar_tfg_causa(rng):
    """Qual alteração produz determinado efeito sobre a TFG?"""
    efeito = rng.choice(["aumenta", "diminui"])
    mesmas = [f for f in FATORES_TFG if f[1] == efeito]
    outras = [f for f in FATORES_TFG if f[1] != efeito]
    if not mesmas or len(outras) < 3:
        return None

    correta_t = rng.choice(mesmas)
    rng.shuffle(outras)

    verbo = "elevação" if efeito == "aumenta" else "redução"

    # Sem cenários variados, o enunciado dependia só do efeito — duas
    # possibilidades — e o template gerava 2 questões distintas.
    CENARIOS = [
        f"Um paciente apresenta {verbo} da taxa de filtração glomerular, "
        f"sem alteração da pressão arterial sistêmica.",
        f"A monitorização da função renal revela {verbo} da taxa de "
        f"filtração glomerular em um paciente estável.",
        f"Em um modelo experimental, registra-se {verbo} da taxa de "
        f"filtração glomerular com pressão arterial mantida constante.",
        f"Durante a investigação de uma alteração renal, observa-se "
        f"{verbo} da taxa de filtração glomerular.",
        f"Um estudo de hemodinâmica renal documenta {verbo} da taxa de "
        f"filtração glomerular sem variação do débito cardíaco.",
    ]
    PERGUNTAS = [
        "Assinale a alternativa que apresenta uma causa compatível com "
        "esse achado.",
        "Qual das alterações abaixo explica esse achado?",
        "Entre as condições listadas, qual justifica esse resultado?",
        "Assinale a alternativa que indica uma causa possível.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(PERGUNTAS)}"

    correta = correta_t[0]
    distratores = [o[0] for o in outras[:3]]
    # Completa com distratores que não constam da tabela
    distratores += [
        "aumento do número de néfrons funcionantes por regeneração tubular",
        "elevação isolada da temperatura corporal",
    ]

    explicacao = (
        f"{_frase(correta_t[0])} {efeito} a taxa de filtração glomerular, "
        f"porque {correta_t[2]}. As demais alternativas produzem efeito "
        f"contrário ou não alteram a filtração."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia renal (filtração glomerular)", rng)


# ══════════════════════════════════════════════════════════
#  TEMPLATES — CARDIOVASCULAR (cálculo)
# ══════════════════════════════════════════════════════════

def gerar_debito_cardiaco(rng):
    """
    Débito cardíaco = frequência cardíaca × volume sistólico.

    Fórmula consagrada, sem controvérsia. Os distratores reproduzem
    erros de conta reais: somar em vez de multiplicar, esquecer a
    conversão de mL para L, dividir na ordem trocada.
    """
    fc = rng.choice([60, 65, 70, 72, 75, 80, 85, 90, 100, 110])
    vs = rng.choice([50, 55, 60, 65, 70, 75, 80])       # mL

    dc_ml = fc * vs
    dc_l = dc_ml / 1000

    CENARIOS = [
        f"Um paciente em repouso apresenta frequência cardíaca de {fc} "
        f"batimentos por minuto e volume sistólico de {vs} mL.",
        f"Na avaliação hemodinâmica, registra-se frequência cardíaca de "
        f"{fc} bpm e volume sistólico de {vs} mL.",
        f"Um estudo de fisiologia cardiovascular mede, em um voluntário, "
        f"frequência cardíaca de {fc} bpm e volume sistólico de {vs} mL.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)} Com base nesses dados, o débito "
                 f"cardíaco é de aproximadamente:")

    correta = round(dc_l, 2)

    # Os distratores precisam ser VEROSSÍMEIS como débito cardíaco.
    # "6.600 L/min" (esquecer a conversão) e "0,17 L/min" (dividir
    # invertido) são descartados sem cálculo: o primeiro é mil vezes o
    # débito humano, o segundo é incompatível com a vida.
    #
    # Um distrator que ninguém marca não é distrator — a questão perde
    # uma opção efetiva.
    candidatos = [
        round(dc_l * 1.5, 2),                # errou o volume sistólico
        round(dc_l / 1.5, 2),
        round(dc_l * 2, 2),                  # dobrou
        round(dc_l / 2, 2),                  # dividiu por engano
        round((fc + vs) / 20, 2),            # somou e ajustou a escala
        round(dc_l + 1.0, 2),
        round(dc_l - 1.0, 2),
        round(dc_l * 1.2, 2),
        round(dc_l * 0.8, 2),
    ]
    # Débito cardíaco humano em repouso fica entre 3 e 8 L/min; sob
    # esforço chega a 25. Fora de 0,5 a 30 não engana ninguém.
    distratores = [d for d in candidatos
                   if 0.5 <= d <= 30 and abs(d - correta) > 0.05]

    explicacao = (
        f"O débito cardíaco é o produto da frequência cardíaca pelo volume "
        f"sistólico, e a conversão de mL para L é onde o cálculo costuma "
        f"escorregar: {fc} bpm × {vs} mL = {_fmt(dc_ml)} mL/min, ou seja, "
        f"{_fmt(correta)} L/min."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (débito cardíaco)", rng,
                   formatador=lambda v: f"{_fmt(v)} L/min")


def gerar_pressao_arterial_media(rng):
    """
    PAM = pressão diastólica + (pressão de pulso ÷ 3)

    A fórmula usa um TERÇO da pressão de pulso porque a diástole ocupa
    cerca de dois terços do ciclo cardíaco em repouso. O erro comum é
    calcular a média aritmética simples.
    """
    pas = rng.choice([100, 110, 120, 130, 140, 150, 160])
    pad = rng.choice([60, 65, 70, 75, 80, 85, 90])
    if pas - pad < 20:
        pad = pas - rng.choice([30, 40, 50])
    pp = pas - pad
    pam = pad + pp / 3

    CENARIOS = [
        f"Um paciente apresenta pressão arterial de {pas}/{pad} mmHg.",
        f"Na consulta de rotina, afere-se pressão arterial de {pas} x {pad} mmHg.",
        f"O monitor registra pressão arterial sistólica de {pas} mmHg e "
        f"diastólica de {pad} mmHg.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)} A pressão arterial média é de "
                 f"aproximadamente:")

    correta = round(pam, 1)

    # A média aritmética simples e "diastólica + metade da pressão de
    # pulso" dão o MESMO valor — são a mesma conta escrita de duas
    # formas. Manter as duas deixava só três distratores distintos, e o
    # template não gerava nunca.
    distratores = [
        round((pas + pad) / 2, 1),        # média simples (= pad + pp/2)
        round(pas - pp / 3, 1),           # subtraiu da sistólica
        round(pp, 1),                     # respondeu a pressão de pulso
        round(pad + pp * 2 / 3, 1),       # usou dois terços da PP
        round(pad, 1),                    # respondeu só a diastólica
        round(pad + pp / 4, 1),           # usou um quarto
    ]
    vistos, unicos = set(), []
    for d in distratores:
        if abs(d - correta) > 0.05 and d not in vistos:
            vistos.add(d)
            unicos.append(d)
    distratores = unicos

    explicacao = (
        f"Usa-se um terço da pressão de pulso, e não a média simples, "
        f"porque em repouso a diástole ocupa cerca de dois terços do "
        f"ciclo cardíaco. Assim: PP = {pas} − {pad} = {pp} mmHg; "
        f"PAM = {pad} + {pp}/3 = {_fmt(correta)} mmHg."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (pressão arterial)", rng,
                   formatador=lambda v: f"{_fmt(v)} mmHg")


# ══════════════════════════════════════════════════════════
#  TEMPLATES — APLICAÇÃO A SITUAÇÃO
# ══════════════════════════════════════════════════════════

def gerar_sraa_situacao(rng):
    """
    Dada uma situação, o SRAA é ativado ou inibido — e por quê?

    Diferente dos templates de direção: aqui o aluno precisa APLICAR o
    mecanismo a um cenário, não recitar uma seta. A estenose de artéria
    renal é o caso mais instrutivo: ativa o sistema mesmo com volemia
    sistêmica normal.
    """
    situacao, resposta, mecanismo = rng.choice(SITUACOES_SRAA)

    CENARIOS = [
        f"Um paciente apresenta {situacao}.",
        f"Considere um indivíduo submetido a {situacao}.",
        f"Durante a avaliação clínica, identifica-se {situacao}.",
        f"Um estudo de fisiologia cardiovascular analisa o efeito de "
        f"{situacao} sobre o controle da pressão arterial.",
    ]
    # Todos os comandos deste template pedem SUBJUNTIVO, porque as
    # alternativas são construídas com "seja ativado" / "haja aumento".
    # O comando "é correto afirmar que" pede indicativo e produzia
    # "é correto afirmar que o sistema seja ativado" — foi removido.
    PERGUNTAS = [
        "Quanto ao sistema renina-angiotensina-aldosterona, espera-se que:",
        "Sobre a atividade do sistema renina-angiotensina-aldosterona "
        "nessa condição, espera-se que:",
        "O comportamento esperado do sistema renina-angiotensina-aldosterona "
        "é que:",
        "Em relação ao sistema renina-angiotensina-aldosterona, é esperado que:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(PERGUNTAS)}"

    if resposta == "ativa":
        correta = ("o sistema seja ativado, com aumento da secreção de "
                   "renina e, consequentemente, de aldosterona")
        oposta = ("o sistema seja inibido, com redução da secreção de "
                  "renina e de aldosterona")
    else:
        correta = ("o sistema seja inibido, com redução da secreção de "
                   "renina e de aldosterona")
        oposta = ("o sistema seja ativado, com aumento da secreção de "
                  "renina e, consequentemente, de aldosterona")

    distratores = [
        oposta,
        "o sistema permaneça inalterado, pois responde apenas a variações "
        "da concentração plasmática de sódio",
        "haja aumento da renina sem alteração da aldosterona, já que os "
        "dois hormônios são regulados de forma independente",
        "haja aumento da aldosterona sem participação da renina, por ação "
        "direta sobre a suprarrenal",
        "o sistema seja ativado apenas se houver simultânea queda da "
        "concentração de potássio",
    ]

    explicacao = (
        f"{_frase(situacao)} {resposta} o sistema renina-angiotensina-"
        f"aldosterona, porque {mecanismo}. A renina converte o "
        f"angiotensinogênio em angiotensina I; a ECA, no endotélio "
        f"pulmonar, produz angiotensina II, que estimula a secreção de "
        f"aldosterona pelo córtex da suprarrenal."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (SRAA)", rng)


def gerar_sraa_sequencia(rng):
    """
    Qual evento vem imediatamente antes ou depois de outro na via?

    Testa a ordem da cascata, que é onde o aluno erra ao decorar os
    nomes sem a sequência.
    """
    idx = rng.randrange(len(ETAPAS_SRAA))
    ordem, evento, local = ETAPAS_SRAA[idx]

    direcao = rng.choice(["antes", "depois"])
    if direcao == "antes" and idx == 0:
        direcao = "depois"
    if direcao == "depois" and idx == len(ETAPAS_SRAA) - 1:
        direcao = "antes"

    alvo = ETAPAS_SRAA[idx - 1] if direcao == "antes" else ETAPAS_SRAA[idx + 1]

    palavra = "precede imediatamente" if direcao == "antes" else "sucede imediatamente"

    # Sem variação de cenário e comando, o template rendia 8 enunciados
    # (5 etapas × 2 direções, descontadas as bordas).
    CENARIOS = [
        "Na cascata do sistema renina-angiotensina-aldosterona",
        "Na sequência de ativação do sistema renina-angiotensina-aldosterona",
        "No encadeamento de eventos do sistema renina-angiotensina-aldosterona",
        "Ao estudar a ordem das etapas do sistema renina-angiotensina-aldosterona",
        "Durante a revisão da cascata hormonal que regula a pressão arterial",
    ]
    COMANDOS = [
        f"Assinale a alternativa que apresenta o evento que a {palavra}.",
        f"Qual evento {palavra} essa etapa?",
        f"Entre os eventos listados, qual {palavra} a etapa citada?",
        f"Assinale a alternativa que indica o evento que a {palavra}.",
    ]
    enunciado = (f"{rng.choice(CENARIOS)}, considere a etapa de {evento}. "
                 f"{rng.choice(COMANDOS)}")

    correta = alvo[1]
    distratores = [e[1] for e in ETAPAS_SRAA if e[1] not in (evento, correta)]
    distratores += [
        "liberação de peptídeo natriurético atrial pelos átrios",
        "secreção de hormônio antidiurético pela neuro-hipófise",
    ]

    explicacao = (
        f"A sequência é: secreção de renina pelas células "
        f"justaglomerulares → conversão de angiotensinogênio em "
        f"angiotensina I → conversão em angiotensina II pela ECA no "
        f"endotélio pulmonar → secreção de aldosterona pelo córtex da "
        f"suprarrenal → reabsorção de sódio e água no néfron distal. "
        f"Portanto, {correta} {'precede' if direcao == 'antes' else 'sucede'} "
        f"a etapa de {evento}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (SRAA)", rng)


def gerar_sraa_local(rng):
    """Onde ocorre cada etapa da via?"""
    ordem, evento, local = rng.choice(ETAPAS_SRAA)

    CENARIOS = [
        f"No sistema renina-angiotensina-aldosterona, a etapa de {evento}",
        f"Na cascata que regula a pressão arterial, o evento de {evento}",
        f"Durante a ativação do sistema renina-angiotensina-aldosterona, "
        f"a etapa de {evento}",
        f"Ao estudar a regulação hormonal da volemia, a etapa de {evento}",
    ]
    COMANDOS = [
        "ocorre em que local?",
        "acontece em qual estrutura?",
        "tem lugar em que sítio anatômico?",
        "é realizada onde?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
    correta = local
    distratores = [e[2] for e in ETAPAS_SRAA if e[2] != local]
    distratores += [
        "hepatócitos do lobo direito do fígado",
        "medula da glândula suprarrenal",
        "túbulo contorcido proximal",
    ]

    explicacao = f"{_frase(evento)} ocorre em: {local}. "
    if "pulmon" in local:
        explicacao += (
            "É um ponto cobrado com frequência: o rim produz a renina, "
            "mas a conversão de angiotensina I em II acontece "
            "predominantemente no endotélio pulmonar."
        )
    elif "córtex" in local:
        explicacao += (
            "A aldosterona é produzida no CÓRTEX da suprarrenal, na zona "
            "glomerulosa — não na medula, que secreta catecolaminas."
        )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (SRAA)", rng)


def gerar_sraa_efeito_hormonio(rng):
    """
    Qual efeito pertence à angiotensina II e qual à aldosterona?

    Confundir os dois é erro frequente — a angiotensina II age no vaso,
    a aldosterona no túbulo.
    """
    hormonio = rng.choice(["angiotensina II", "aldosterona"])
    proprios = [e[1] for e in EFEITOS_SRAA if e[0] == hormonio]
    alheios = [e[1] for e in EFEITOS_SRAA if e[0] != hormonio]
    if not proprios or len(alheios) < 3:
        return None

    correta = rng.choice(proprios)
    rng.shuffle(alheios)

    CENARIOS = [
        f"Entre os efeitos do sistema renina-angiotensina-aldosterona, "
        f"alguns são atribuíveis especificamente à {hormonio}.",
        f"A {hormonio} exerce efeitos próprios dentro da cascata do "
        f"sistema renina-angiotensina-aldosterona.",
        f"Na regulação da pressão arterial e da volemia, a {hormonio} "
        f"desempenha funções específicas.",
        f"Um estudante precisa distinguir os efeitos da {hormonio} dos "
        f"efeitos dos demais componentes do sistema.",
        f"A ação da {hormonio} sobre os alvos periféricos é distinta da "
        f"dos outros mediadores da cascata.",
    ]
    COMANDOS = [
        f"Assinale a alternativa que apresenta um efeito da {hormonio}.",
        f"Qual das ações abaixo é atribuível à {hormonio}?",
        f"Entre os efeitos listados, qual corresponde à {hormonio}?",
        f"Assinale a alternativa que indica uma ação da {hormonio}.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    distratores = alheios[:3] + [
        "aumento da excreção renal de sódio e água",
        "redução da resistência vascular periférica",
    ]

    outro = "aldosterona" if hormonio == "angiotensina II" else "angiotensina II"
    explicacao = (
        f"{_frase(correta)} é efeito da {hormonio}. "
        f"Convém separar os dois hormônios: a angiotensina II age "
        f"principalmente sobre o VASO (vasoconstrição, constrição da "
        f"arteríola eferente) e estimula a suprarrenal; a aldosterona age "
        f"sobre o TÚBULO renal (reabsorção de sódio, secreção de potássio "
        f"e hidrogênio). Os distratores incluem efeitos da {outro} e ações "
        f"opostas às do sistema."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Fisiologia cardiovascular (SRAA)", rng)


# ══════════════════════════════════════════════════════════
#  TEMPLATES — NEUROFISIOLOGIA
# ══════════════════════════════════════════════════════════

def gerar_pa_fase_ion(rng):
    """
    Qual íon e em que direção se move em cada fase do potencial de ação?

    O erro clássico é atribuir a repolarização à bomba de sódio e
    potássio — ela restaura os gradientes DEPOIS, não gera o potencial.
    """
    ordem, fase, ion, movimento, mecanismo = rng.choice(FASES_PA[:3])

    CENARIOS = [
        f"Durante o registro eletrofisiológico de um neurônio, observa-se "
        f"a fase de {fase} do potencial de ação.",
        f"Ao analisar o traçado de um potencial de ação, identifica-se a "
        f"fase de {fase}.",
        f"Um experimento de neurofisiologia acompanha a fase de {fase} do "
        f"potencial de ação em um axônio isolado.",
        f"Considere a fase de {fase} de um potencial de ação neuronal.",
    ]
    COMANDOS = [
        "O movimento iônico responsável por essa fase é:",
        "Assinale a alternativa que indica o evento iônico dessa fase.",
        "Qual movimento iônico caracteriza essa fase?",
        "Essa fase decorre de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = f"{movimento} de {ion}"
    distratores = []
    for _, f2, i2, m2, _ in FASES_PA:
        cand = f"{m2} de {i2}"
        if cand == correta:
            continue
        # A hiperpolarização É um efluxo de potássio — o que a distingue
        # da repolarização é ser residual. Oferecer "efluxo de potássio"
        # como distrator dela dá duas alternativas verdadeiras.
        if fase == "hiperpolarização" and cand == "efluxo de potássio":
            continue
        distratores.append(cand)
    # Os extras traziam a explicação do mecanismo junto ("pelos canais
    # dependentes de voltagem") e chegavam a 57 caracteres, contra 16 de
    # "influxo de sódio". A resposta certa era quase sempre a mais curta.
    # Agora todos têm a forma "movimento de íon", e os erros são de
    # direção ou de íon — que é o que a questão precisa separar.
    distratores += [
        "influxo de cálcio",
        "efluxo de cloreto",
        "influxo de potássio",
        "efluxo de sódio",
        "transporte ativo de cálcio",
    ]

    explicacao = (
        f"A fase de {fase} decorre do {movimento} de {ion}, por "
        f"{mecanismo}. Convém lembrar que a bomba de sódio e potássio não "
        f"gera o potencial de ação — ela restaura os gradientes depois que "
        f"ele termina."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Neurofisiologia (potencial de ação)", rng)


def gerar_pa_sequencia(rng):
    """Qual fase vem antes ou depois de outra?"""
    idx = rng.randrange(len(FASES_PA))
    ordem, fase, _, _, _ = FASES_PA[idx]

    direcao = rng.choice(["antes", "depois"])
    if direcao == "antes" and idx == 0:
        direcao = "depois"
    if direcao == "depois" and idx == len(FASES_PA) - 1:
        direcao = "antes"
    alvo = FASES_PA[idx - 1] if direcao == "antes" else FASES_PA[idx + 1]

    palavra = "precede" if direcao == "antes" else "sucede"
    CENARIOS = [
        "Na sequência de eventos de um potencial de ação neuronal",
        "Ao descrever as fases do potencial de ação em ordem cronológica",
        "No traçado de um potencial de ação registrado experimentalmente",
        "Durante o estudo da sucessão de fases do potencial de ação",
    ]
    COMANDOS = [
        f"Assinale a alternativa que apresenta a fase que a {palavra} "
        f"imediatamente.",
        f"Qual fase {palavra} imediatamente essa etapa?",
        f"Entre as fases listadas, qual {palavra} imediatamente a citada?",
    ]
    enunciado = (f"{rng.choice(CENARIOS)}, considere a fase de {fase}. "
                 f"{rng.choice(COMANDOS)}")

    correta = alvo[1]
    distratores = [f[1] for f in FASES_PA if f[1] not in (fase, correta)]
    # Os extras eram eventos sinápticos descritos por extenso, de até 58
    # caracteres, enquanto as fases têm nomes de uma palavra. A resposta
    # era quase sempre a mais curta da lista.
    #
    # Agora os extras também são NOMES de fase — dois reais mas de outro
    # fenômeno (o potencial de ação cardíaco, o potencial pós-sináptico)
    # e um inexistente. Mesmo formato, mesmo tamanho.
    distratores += [
        "platô",
        "pré-potencial",
        "diástole elétrica",
        "pós-despolarização",
    ]

    explicacao = (
        f"A ordem das fases é: despolarização → repolarização → "
        f"hiperpolarização → retorno ao potencial de repouso. Portanto, "
        f"{correta} {palavra} a fase de {fase}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Neurofisiologia (potencial de ação)", rng)


def gerar_periodo_refratario(rng):
    """
    Distinguir período refratário absoluto de relativo.

    A diferença prática — se um estímulo mais forte consegue ou não
    gerar novo potencial — é o que a prova cobra.
    """
    tipo, definicao, mecanismo = rng.choice(REFRATARIOS)
    outro = [r for r in REFRATARIOS if r[0] != tipo][0]

    modo = rng.choice(["pela_definicao", "pelo_nome"])

    if modo == "pela_definicao":
        CENARIOS = [
            f"Durante determinado intervalo após um potencial de ação, "
            f"{definicao}.",
            f"Em uma etapa do ciclo de excitabilidade neuronal, {definicao}.",
            f"Um experimento demonstra que, em certo momento após o "
            f"potencial de ação, {definicao}.",
        ]
        COMANDOS = [
            "Esse intervalo corresponde ao período refratário:",
            "Assinale a alternativa que o classifica.",
            "Trata-se do período refratário:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = tipo
        # Os distratores eram sintagmas "de ..." com até 22 caracteres,
        # contra 8 de "absoluto" e "relativo": a resposta certa era
        # sempre a mais curta. Agora todas as opções são adjetivos que
        # encaixam na mesma moldura ("período refratário ___"), com
        # comprimento equivalente.
        distratores = [
            outro[0],
            "parcial",
            "tardio",
            "residual",
            "isoelétrico",
        ]
        explicacao = (
            f"Trata-se do período refratário {tipo}, no qual {definicao}. "
            f"A causa é que {mecanismo}. No período refratário {outro[0]}, "
            f"por sua vez, {outro[1]}."
        )
    else:
        # Todos os cenários terminam em PONTO. Um deles terminava em
        # vírgula, e a junção com o comando produzia "...a um potencial
        # de ação, Sobre esse período, é correto afirmar que:" — vírgula
        # seguida de maiúscula.
        CENARIOS = [
            f"Considere o período refratário {tipo} de um neurônio.",
            f"Um estudo de excitabilidade neuronal analisa o período "
            f"refratário {tipo}.",
            f"Após um potencial de ação, o neurônio atravessa o período "
            f"refratário {tipo}.",
            f"Durante a avaliação da excitabilidade de um axônio, examina-se "
            f"o período refratário {tipo}.",
        ]
        COMANDOS = [
            "É correto afirmar que, nesse intervalo:",
            "Assinale a alternativa correta sobre esse intervalo.",
            "Sobre esse período, é correto afirmar que:",
            "Nesse intervalo:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = definicao

        # Os distratores precisam ter a MESMA modalidade da resposta certa.
        # A definição do período relativo usa "pode ser gerado"; se os
        # distratores forem todos categóricos, o aluno marca a única
        # moderada sem saber o conteúdo — a estratégia acertava metade
        # das vezes.
        distratores = [
            outro[1],
            "a membrana pode conduzir sinais elétricos, embora com "
            "amplitude reduzida de forma permanente",
            "a velocidade de condução do axônio pode aumentar de forma "
            "transitória",
            "o potencial de repouso pode tornar-se positivo por alguns "
            "milissegundos",
            "a bomba de sódio e potássio pode interromper temporariamente "
            "seu funcionamento",
        ]
        explicacao = (
            f"No período refratário {tipo}, {definicao}, porque {mecanismo}."
        )

    return _montar(enunciado, correta, distratores, explicacao,
                   "Neurofisiologia (excitabilidade)", rng)


def gerar_conducao_axonio(rng):
    """Condução saltatória versus contínua."""
    tipo, nome, descricao, velocidade = rng.choice(CONDUCAO)
    outro = [c for c in CONDUCAO if c[0] != tipo][0]

    CENARIOS = [
        f"Compare a propagação do impulso nervoso em um {tipo}.",
        f"Um estudo de neurofisiologia analisa a condução do impulso em "
        f"um {tipo}.",
        f"Considere a propagação do potencial de ação ao longo de um {tipo}.",
        f"Durante a avaliação da velocidade de condução nervosa, examina-se "
        f"um {tipo}.",
        f"Um exame de eletroneuromiografia avalia a condução em um {tipo}.",
        f"Na comparação entre fibras nervosas, analisa-se um {tipo}.",
        f"O estudo da velocidade de condução do impulso nervoso examina "
        f"um {tipo}.",
        f"Ao investigar como o potencial de ação se propaga, considera-se "
        f"um {tipo}.",
    ]
    COMANDOS = [
        "É correto afirmar que a condução nesse axônio é:",
        "Assinale a alternativa que caracteriza corretamente essa condução.",
        "A condução do impulso nesse axônio é:",
        "Sobre a condução nessa fibra, é correto afirmar que ela é:",
        "Qual alternativa descreve corretamente essa condução?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = f"{nome} e {velocidade} que no {outro[0]}"
    # Os quatro primeiros distratores combinam nome e velocidade de forma
    # errada — mesmo formato da resposta certa. Os dois últimos usavam
    # "apenas" e "não afeta", termos absolutos que uma estratégia de
    # eliminação identifica; foram reescritos sem eles.
    distratores = [
        f"{outro[1]} e {outro[3]} que no {tipo}",
        f"{nome} e {outro[3]} que no {outro[0]}",
        f"{outro[1]} e {velocidade} que no {tipo}",
        f"{nome} e de velocidade semelhante à do {outro[0]}",
        f"{outro[1]} e de velocidade semelhante à do {tipo}",
    ]

    explicacao = (
        f"No {tipo}, a condução é {nome}: {descricao}. Por isso é "
        f"{velocidade} que no {outro[0]}, onde a condução é {outro[1]}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Neurofisiologia (condução nervosa)", rng)


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_FISIOLOGIA = {
    "curva_hb_direcao":  gerar_curva_hb_direcao,
    "curva_hb_fator":    gerar_curva_hb_fator,
    "tfg_efeito":        gerar_tfg_efeito,
    "tfg_causa":         gerar_tfg_causa,
    "debito_cardiaco":   gerar_debito_cardiaco,
    "pressao_media":     gerar_pressao_arterial_media,
    "sraa_situacao":     gerar_sraa_situacao,
    "sraa_sequencia":    gerar_sraa_sequencia,
    "sraa_local":        gerar_sraa_local,
    "sraa_efeito":       gerar_sraa_efeito_hormonio,
    "pa_fase_ion":       gerar_pa_fase_ion,
    "pa_sequencia":      gerar_pa_sequencia,
    "periodo_refratario": gerar_periodo_refratario,
    "conducao_axonio":   gerar_conducao_axonio,
}

# Agrupamento dos templates por assunto. A API usa esta estrutura para
# listar o que existe e para filtrar por área — mesmo formato dos demais
# geradores do projeto.
TOPICOS_FISIOLOGIA = {
    "respiratorio": [
        "curva_hb_direcao",
        "curva_hb_fator",
    ],
    "renal": [
        "tfg_efeito",
        "tfg_causa",
    ],
    "cardiovascular": [
        "debito_cardiaco",
        "pressao_media",
    ],
    "neurofisiologia": [
        "pa_fase_ion",
        "pa_sequencia",
        "periodo_refratario",
        "conducao_axonio",
    ],
    "endocrino_cardiovascular": [
        "sraa_situacao",
        "sraa_sequencia",
        "sraa_local",
        "sraa_efeito",
    ],
}


# Palavras que identificam este gerador nos tópicos de um livro
PALAVRAS_CHAVE = {
    "curva_hb_direcao":  ["hemoglobina", "oxi-hemoglobina", "efeito bohr",
                          "transporte de oxigenio", "dissociacao"],
    "curva_hb_fator":    ["hemoglobina", "oxi-hemoglobina", "efeito bohr",
                          "2,3-dpg", "difosfoglicerato"],
    "tfg_efeito":        ["filtracao glomerular", "tfg", "arteriola aferente",
                          "arteriola eferente", "glomerulo", "nefron"],
    "tfg_causa":         ["filtracao glomerular", "tfg", "glomerulo",
                          "starling", "macula densa"],
    "debito_cardiaco":   ["debito cardiaco", "volume sistolico",
                          "frequencia cardiaca"],
    "pressao_media":     ["pressao arterial", "pressao arterial media",
                          "pressao de pulso"],
    "sraa_situacao":     ["renina", "angiotensina", "aldosterona", "sraa",
                          "eca", "justaglomerular"],
    "sraa_sequencia":    ["renina", "angiotensina", "aldosterona", "sraa",
                          "angiotensinogenio"],
    "sraa_local":        ["renina", "angiotensina", "aldosterona",
                          "suprarrenal", "adrenal"],
    "sraa_efeito":       ["renina", "angiotensina", "aldosterona",
                          "mineralocorticoide"],
    "pa_fase_ion":       ["potencial de acao", "despolarizacao",
                          "repolarizacao", "hiperpolarizacao", "axonio"],
    "pa_sequencia":      ["potencial de acao", "despolarizacao",
                          "repolarizacao", "neuronio"],
    "periodo_refratario": ["periodo refratario", "excitabilidade",
                           "potencial de acao", "limiar"],
    "conducao_axonio":   ["conducao saltatoria", "mielina", "ranvier",
                          "axonio", "conducao nervosa", "bainha"],
}

# Termos que existem fora da fisiologia e não devem acionar o gerador
CHAVES_GENERICAS = {
    "curva", "fator", "pressao", "volume", "frequencia", "transporte",
    "filtracao", "efeito", "media", "sistema", "funcao",
}


def _normalizar(t: str) -> str:
    """Remove acento e caixa, para comparar tópicos de livro."""
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def templates_para_topicos(topicos):
    """
    Quais templates casam com os tópicos de um livro?

    Exige ao menos uma palavra ESPECÍFICA — genéricas como "pressão" e
    "volume" existem em qualquer área e sozinhas não identificam
    fisiologia.
    """
    texto = " " + " ".join(_normalizar(t) for t in (topicos or [])) + " "
    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        especificas = 0
        for chave in chaves:
            cn = _normalizar(chave)
            if cn in CHAVES_GENERICAS:
                continue
            if re.search(r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])',
                         texto):
                especificas += 1
        if especificas >= 1:
            achados.append(nome)
    return achados


def gerar_lote(quantidade: int = 10, seed: int = None,
               topico: str = None, templates: list = None):
    """
    Gera um lote de questões de fisiologia.

    Percorre os templates em rodízio para distribuir os assuntos, e
    tenta várias vezes cada um: alguns rejeitam o sorteio quando os
    distratores colidem.
    """
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_FISIOLOGIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_FISIOLOGIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        # A área pedida pode ser uma CHAVE de TOPICOS_FISIOLOGIA
        # ("renal", "cardiovascular") ou um texto livre a ser casado por
        # palavra-chave. A chave tem precedência: sem isso, pedir
        # topico="renal" devolvia questões de respiratório, porque
        # "renal" não consta das palavras-chave de nenhum template.
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_FISIOLOGIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_FISIOLOGIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    questoes, tentativas, limite = [], 0, quantidade * 12
    vistos = set()
    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = disponiveis[len(questoes) % len(disponiveis)]
        q = TEMPLATES_FISIOLOGIA[nome](rng)
        if not q:
            continue
        # Não repete enunciado idêntico dentro do mesmo lote
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue
        vistos.add(q["enunciado"])
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade: int = 10, seed: int = None,
                   topico: str = None, templates: list = None):
    """
    Devolve (questoes, gabarito) no formato que a API espera.

    Campos internos — tópico, explicação — ficam no gabarito, não na
    questão, para não vazarem ao aluno.
    """
    lote = gerar_lote(quantidade, seed=seed, topico=topico,
                      templates=templates)
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
    print("  GERADOR DE FISIOLOGIA")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
