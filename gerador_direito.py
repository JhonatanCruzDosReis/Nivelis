"""
=============================================================
  NIVELIS — Gerador Procedural: Direito
  Foco: ENADE Direito, OAB (1ª fase), concursos jurídicos
=============================================================

  Gera questões SEM IA. O Python calcula ou consulta tabela
  de dispositivos legais verificados em fonte primária.

  ESCOPO DELIBERADO
  -----------------
  Cobre apenas o que tem RESPOSTA OBJETIVA NA LEI:
    • prazos processuais e prescricionais (contagem calculada)
    • competência e hierarquia normativa
    • classificação de recursos e prazos correspondentes
    • cálculo de honorários e custas (percentuais legais)

  NÃO cobre — e isso é intencional:
    • interpretação de casos concretos
    • jurisprudência controvertida
    • questões que dependem de ponderação de princípios

  Para conteúdo interpretativo, use o gerador_interpretacao
  com doutrina indexada.

  ⚠️  AVISO IMPORTANTE
  A legislação MUDA. Os prazos aqui refletem o CPC/2015 e o
  Código Civil vigentes na data de escrita. Antes de usar em
  produção, confirme que não houve alteração legislativa —
  especialmente após reformas processuais.
  Última verificação das fontes: agosto/2026.

  FONTES CONSULTADAS:
    • CPC/2015 (Lei 13.105/2015) — arts. 183, 219, 224, 335,
      994, 1.003, 1.009, 1.015, 1.020, 1.029
    • Código Civil (Lei 10.406/2002) — arts. 205, 206
    • Jurisprudência do STJ sobre reparação civil contratual
      vs. extracontratual (EREsp 1.281.594/SP)

  12 TEMPLATES:

  PROCESSO CIVIL
    1. Prazo de recurso (identificação)
    2. Prazo em dobro (Fazenda Pública, MP, Defensoria)
    3. Contagem de prazo em dias úteis (cálculo de data)
    4. Recurso cabível por tipo de decisão
  CIVIL
    5. Prazo prescricional por pretensão
    6. Prescrição — cálculo de data-limite
    7. Capacidade civil por idade
  CONSTITUCIONAL
    8. Competência legislativa (União/Estado/Município)
    9. Hierarquia e quórum normativo
  PENAL / TRABALHISTA
   10. Prazos penais (recursos e prescrição da pena)
   11. Prazos trabalhistas (CLT)
  HONORÁRIOS
   12. Honorários sucumbenciais (faixas do art. 85 do CPC)

  USO:
    python gerador_direito.py            # 12 questões
    python gerador_direito.py 20 processo_civil
=============================================================
"""

import sys
import re
import random
from datetime import date, timedelta

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "fracao", "simbolica", "codigo_numerico",
    "sequencia", "textual", "endereco_ip", "percentual", "monetaria",
}


# ══════════════════════════════════════════════════════════
#  TABELA DE DISPOSITIVOS — verificada em fonte primária
# ══════════════════════════════════════════════════════════

# ── Prazos recursais do CPC/2015 (em dias ÚTEIS) ──
# Fonte: CPC arts. 994, 1.003 §5º, 1.009, 1.015, 1.029
PRAZOS_RECURSAIS = [
    ("apelação",                        15, "art. 1.003, § 5º"),
    ("agravo de instrumento",           15, "art. 1.003, § 5º"),
    ("agravo interno",                  15, "art. 1.021"),
    ("recurso especial",                15, "art. 1.003, § 5º"),
    ("recurso extraordinário",          15, "art. 1.003, § 5º"),
    ("recurso ordinário",               15, "art. 1.003, § 5º"),
    ("embargos de divergência",         15, "art. 1.003, § 5º"),
    ("embargos de declaração",           5, "art. 1.023"),
]

# ── Outros prazos processuais (dias úteis) ──
PRAZOS_PROCESSUAIS = [
    ("contestação",                             15, "art. 335"),
    ("réplica (impugnação à contestação)",      15, "art. 351"),
    ("contrarrazões de apelação",               15, "art. 1.010, § 1º"),
    ("pagamento voluntário no cumprimento de sentença", 15, "art. 523"),
    ("impugnação ao cumprimento de sentença",   15, "art. 525"),
    ("embargos à execução",                     15, "art. 915"),
]

# ── Sujeitos com prazo em dobro (CPC art. 180, 183, 186) ──
# O terceiro campo diz se o sujeito é PLURAL. Sem ele, o enunciado saía
# "os litisconsortes com procuradores diferentes, em autos físicos foi
# intimado" — e a vírgula interna ainda partia a frase ao meio.
PRAZO_DOBRO = [
    ("a Fazenda Pública",    "art. 183", False),
    ("o Ministério Público", "art. 180", False),
    ("a Defensoria Pública", "art. 186", False),
    ("os litisconsortes com procuradores diferentes em autos físicos",
     "art. 229", True),
]

# ── Prazos prescricionais do Código Civil ──
# Fonte: CC arts. 205 e 206
PRESCRICAO_CIVIL = [
    ("a pretensão de reparação civil extracontratual",          3, "art. 206, § 3º, V"),
    ("a pretensão relativa a aluguéis de prédios urbanos",      3, "art. 206, § 3º, I"),
    ("a pretensão de ressarcimento de enriquecimento sem causa", 3, "art. 206, § 3º, IV"),
    ("a pretensão para haver juros e dividendos",               3, "art. 206, § 3º, III"),
    ("a pretensão relativa à tutela",                           4, "art. 206, § 4º"),
    ("a cobrança de dívida líquida constante de instrumento",   5, "art. 206, § 5º, I"),
    ("a pretensão de profissionais liberais quanto a honorários", 5, "art. 206, § 5º, II"),
    ("a pretensão do vencedor para haver o que despendeu em juízo", 5, "art. 206, § 5º, III"),
    ("a pretensão para haver prestações alimentares",           2, "art. 206, § 2º"),
    ("a pretensão do segurado contra o segurador",              1, "art. 206, § 1º, II"),
    ("a reparação civil decorrente de inadimplemento contratual", 10, "art. 205 (STJ, EREsp 1.281.594/SP)"),
    ("a pretensão sem prazo específico previsto em lei",        10, "art. 205"),
]

# ── Capacidade civil (CC arts. 3º, 4º, 5º) ──
# "plenamente capaz" tinha 16 caracteres contra 21 das duas categorias
# de incapacidade e 37 dos distratores — era sempre a alternativa mais
# curta, e é a resposta certa para toda idade a partir dos 18. Marcar a
# menor acertava metade destas questões.
CAPACIDADE_CIVIL = [
    ("absolutamente incapaz",             "menor de 16 anos",   "art. 3º"),
    ("relativamente incapaz",             "maior de 16 e menor de 18 anos",
     "art. 4º, I"),
    ("plenamente capaz para os atos civis", "maior de 18 anos", "art. 5º"),
]

# ── Competência legislativa (CF arts. 22, 24, 30) ──
COMPETENCIA_LEGISLATIVA = [
    ("direito civil, comercial, penal e processual",  "privativa da União",   "art. 22, I"),
    ("águas, energia, informática e telecomunicações", "privativa da União",  "art. 22, IV"),
    ("diretrizes da política nacional de transportes", "privativa da União",  "art. 22, IX"),
    ("direito tributário, financeiro e urbanístico",   "concorrente entre União, Estados e DF", "art. 24, I"),
    ("orçamento",                                      "concorrente entre União, Estados e DF", "art. 24, II"),
    ("educação, cultura, ensino e desporto",           "concorrente entre União, Estados e DF", "art. 24, IX"),
    ("assuntos de interesse local",                    "do Município",        "art. 30, I"),
]

# ── Quórum de aprovação (CF) ──
# Os três quóruns eram enunciados em formatos diferentes — 52
# caracteres para a emenda contra 16 da lei complementar. A emenda é a
# resposta em um terço dos sorteios, e marcar a alternativa mais longa
# acertava 47% destas questões. Agora os três (e os distratores) seguem
# a mesma fórmula: proporção + turnos + âmbito.
QUORUM_NORMATIVO = [
    ("emenda constitucional",
     "três quintos dos votos, em dois turnos, em cada Casa", "art. 60, § 2º"),
    ("lei complementar",
     "maioria absoluta dos membros de cada Casa",            "art. 69"),
    ("lei ordinária",
     "maioria simples dos presentes em cada Casa",           "art. 47"),
]

# ── Prazos recursais no processo penal (CPP, dias CORRIDOS) ──
PRAZOS_PENAIS = [
    ("apelação no processo penal",              5, "art. 593 do CPP"),
    ("recurso em sentido estrito",              5, "art. 586 do CPP"),
    ("embargos de declaração no processo penal", 2, "art. 619 do CPP"),
    ("razões de apelação",                      8, "art. 600 do CPP"),
    ("resposta à acusação",                    10, "art. 396 do CPP"),
]

# ── Prazos trabalhistas (CLT, dias úteis após a Lei 13.467/2017) ──
PRAZOS_TRABALHISTAS = [
    ("recurso ordinário trabalhista",   8, "art. 895 da CLT"),
    ("agravo de petição",               8, "art. 897 da CLT"),
    ("recurso de revista",              8, "art. 896 da CLT"),
    ("embargos de declaração na Justiça do Trabalho", 5, "art. 897-A da CLT"),
]

# ── Honorários sucumbenciais (CPC art. 85, § 2º e § 3º) ──
# Faixas aplicáveis quando a Fazenda Pública é parte
FAIXAS_HONORARIOS = [
    (0,        200,  10, 20),   # até 200 salários mínimos
    (200,      2000,  8, 10),
    (2000,    20000,  5,  8),
    (20000,  100000,  3,  5),
    (100000, 10**9,   1,  3),
]


# ──────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────

def _dias_uteis(v) -> str:
    """"8 dias úteis" em vez de "8".

    Com alternativas numéricas cruas, "8" tinha um caractere e "30"
    tinha dois: a mais curta era a certa em 57% das questões. Garantir
    dois distratores de um algarismo resolvia a pista de comprimento,
    mas prendia o prazo certo entre dois valores menores, e ele virava
    o valor do meio em 83%. Escrevendo a unidade, as cinco alternativas
    ficam do mesmo tamanho e as duas pistas somem juntas.
    """
    n = int(v)
    return f"{n} dia útil" if n == 1 else f"{n} dias úteis"


def _fmt(v) -> str:
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return str(v)


def _prazos_falsos(prazo, base, rng, n=4):
    """
    Escolhe `n` prazos falsos sem deixar o correto isolado no tamanho.

    O prazo trabalhista é 8 na maioria dos atos, e os distratores fixos
    eram 10, 15, 20 e 30: a resposta certa era a ÚNICA de um algarismo,
    e marcar a mais curta acertava 56% das questões. Garantindo dois
    distratores com o mesmo número de dígitos, a pista some — foi o que
    sempre salvou o gerador de prazos do processo civil, cujo conjunto
    fixo já incluía o 2 e o 8.

    A ordem importa: _montar usa os quatro PRIMEIROS da lista.
    """
    digitos = len(str(prazo))
    pool = sorted({p for p in base if p != prazo})
    iguais = [p for p in pool if len(str(p)) == digitos]
    demais = [p for p in pool if len(str(p)) != digitos]
    rng.shuffle(iguais)
    rng.shuffle(demais)

    # UM distrator com o mesmo número de dígitos já basta: "mais curta"
    # precisa de uma alternativa isoladamente mais curta, e com dois
    # números de um algarismo não há isolada. Exigir DOIS, como antes,
    # travava o prazo certo (8, quase sempre) com exatamente dois
    # distratores abaixo — e ele virava o valor do meio em 83% das
    # questões. Com um só garantido, a POSIÇÃO volta a variar.
    escolhidos = iguais[:1]
    resto = [p for p in (iguais[1:] + demais) if p not in escolhidos]
    abaixo = [p for p in resto if p < prazo]
    acima = [p for p in resto if p > prazo]
    rng.shuffle(abaixo)
    rng.shuffle(acima)
    faltam = n - len(escolhidos)
    minimo = max(0, faltam - len(acima))
    maximo = min(faltam, len(abaixo))
    if minimo <= maximo:
        q_abaixo = rng.randint(minimo, maximo)
        escolhidos += abaixo[:q_abaixo] + acima[:faltam - q_abaixo]
    else:
        escolhidos += resto[:faltam]
    escolhidos = escolhidos[:n]
    rng.shuffle(escolhidos)
    return escolhidos


def _intimado(sujeito: str, plural: bool) -> str:
    """Concorda o particípio com o sujeito em gênero e número."""
    if plural:
        return "foram intimados"
    return "foi intimada" if sujeito.startswith("a ") else "foi intimado"


def _plural(n, singular, plural=None):
    if plural is None:
        plural = singular + "s"
    return singular if abs(n) == 1 else plural


def _juntar(anterior: str, seguinte: str) -> str:
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=_fmt, tipo_resposta="numerica"):
    assert tipo_resposta in TIPOS_RESPOSTA
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
    return {
        "enunciado":      enunciado,
        "alternativas":   {L: formatador(v) for L, v in zip(LETRAS, valores)},
        "gabarito":       LETRAS[valores.index(correta)],
        "explicacao":     explicacao,
        "topico":         topico,
        "origem":         "gerador_direito",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
    }


# ══════════════════════════════════════════
#  PROCESSO CIVIL
# ══════════════════════════════════════════

def gerar_prazo_recursal(rng):
    """Prazo de um recurso específico no CPC/2015."""
    for _ in range(50):
        recurso, prazo, artigo = rng.choice(PRAZOS_RECURSAIS + PRAZOS_PROCESSUAIS)
        outros = sorted({p for _, p, _ in PRAZOS_RECURSAIS + PRAZOS_PROCESSUAIS
                         if p != prazo} | {2, 8, 10, 20, 30})
        rng.shuffle(outros)

        CENARIOS = [
            f"Publicada a decisão, a parte pretende interpor {recurso}.",
            f"Intimado da decisão, o advogado precisa protocolar {recurso}.",
            f"Após a intimação, a parte tem prazo legal para apresentar {recurso}.",
            f"No curso de processo cível regido pelo CPC/2015, cabe {recurso}.",
        ]
        PERGUNTAS = [
            "Qual é o prazo legal, em dias úteis?",
            "O prazo previsto no CPC, em dias úteis, é de:",
            "Determine o prazo em dias úteis.",
            "Nessas condições, de quantos dias úteis é o prazo?",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Segundo o CPC/2015 ({artigo}), o prazo para {recurso} é de "
            f"{prazo} {_plural(prazo, 'dia útil', 'dias úteis')}."
        )
        q = _montar(enunciado, prazo, outros, explicacao,
                    "Processo civil (prazos)", rng)
        if q:
            return q
    raise RuntimeError("prazo_recursal")


def gerar_prazo_dobro(rng):
    """Prazo em dobro para Fazenda Pública, MP e Defensoria."""
    for _ in range(50):
        sujeito, art_dobro, plural = rng.choice(PRAZO_DOBRO)
        ato, prazo, artigo = rng.choice(PRAZOS_RECURSAIS + PRAZOS_PROCESSUAIS)
        correta = prazo * 2

        distratores = [prazo, prazo * 3, correta + 5, correta - 5, prazo + 5,
                       correta + 10, max(1, correta - 10), prazo * 4]

        CENARIOS = [
            f"Em processo cível, {sujeito} {_intimado(sujeito, plural)} "
            f"para apresentar {ato}.",
            f"O CPC/2015 confere prazo diferenciado a determinados sujeitos "
            f"processuais. Quando {sujeito} "
            f"{'precisam' if plural else 'precisa'} apresentar {ato},",
            f"Considere que {sujeito} "
            f"{'figuram como partes' if plural else 'figura como parte'} "
            f"em processo "
            f"cível e {'devem' if plural else 'deve'} apresentar {ato}.",
        ]
        PERGUNTAS = [
            "Qual é o prazo aplicável, em dias úteis?",
            "o prazo aplicável, em dias úteis, é de:",
            "Determine o prazo em dias úteis.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"O prazo comum para {ato} é de {prazo} "
            f"{_plural(prazo, 'dia útil', 'dias úteis')} ({artigo}). Como "
            f"{sujeito} {'gozam' if plural else 'goza'} de prazo em dobro "
            f"({art_dobro} do CPC), o prazo "
            f"passa a ser de {correta} dias úteis."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (prazos diferenciados)", rng)
        if q:
            return q
    raise RuntimeError("prazo_dobro")


def gerar_contagem_prazo(rng):
    """
    Contagem de prazo em dias úteis a partir de uma data.
    O Python percorre o calendário dia a dia — resultado sempre correto.
    """
    for _ in range(60):
        ato, prazo, artigo = rng.choice(PRAZOS_RECURSAIS + PRAZOS_PROCESSUAIS)
        # Data-base num dia útil qualquer de um ano recente
        base = date(2025, rng.randint(2, 11), rng.randint(1, 25))
        while base.weekday() >= 5:            # cai em fim de semana
            base += timedelta(days=1)

        # CPC art. 224: exclui o dia do começo, inclui o do vencimento.
        # Art. 219: contam-se apenas os dias úteis.
        contados, atual = 0, base
        while contados < prazo:
            atual += timedelta(days=1)
            if atual.weekday() < 5:
                contados += 1
        correta = atual.strftime("%d/%m/%Y")

        # Distratores: erros típicos de contagem
        d_corridos = base + timedelta(days=prazo)
        d_inclui_inicio = atual - timedelta(days=1)
        while d_inclui_inicio.weekday() >= 5:
            d_inclui_inicio -= timedelta(days=1)
        d_a_mais = atual + timedelta(days=1)
        while d_a_mais.weekday() >= 5:
            d_a_mais += timedelta(days=1)
        d_dobro = base + timedelta(days=prazo * 2)

        d_dois_antes = d_inclui_inicio - timedelta(days=3)
        while d_dois_antes.weekday() >= 5:
            d_dois_antes -= timedelta(days=1)
        d_metade = base + timedelta(days=max(1, prazo // 2))
        distratores = [d.strftime("%d/%m/%Y") for d in
                       (d_corridos, d_inclui_inicio, d_a_mais, d_dobro,
                        d_dois_antes, d_metade)]

        CENARIOS = [
            f"A intimação para {ato} ocorreu em {base.strftime('%d/%m/%Y')}, "
            f"{'uma' if base.weekday() in (1,2,5) else 'uma'} "
            f"{['segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira'][base.weekday()]}.",
            f"Publicada a decisão em {base.strftime('%d/%m/%Y')}, iniciou-se o "
            f"prazo para {ato}.",
        ]
        PERGUNTAS = [
            f"Considerando que o prazo é de {prazo} dias úteis e que não houve "
            f"feriado no período, qual é a data final?",
            f"Sabendo que o prazo é de {prazo} dias úteis e desconsiderando "
            f"feriados, o último dia para a prática do ato é:",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {rng.choice(PERGUNTAS)}"
        explicacao = (
            f"Pelo art. 224 do CPC, exclui-se o dia do começo e inclui-se o do "
            f"vencimento; pelo art. 219, contam-se apenas dias úteis. Contando "
            f"{prazo} dias úteis a partir de {base.strftime('%d/%m/%Y')}, "
            f"o prazo termina em {correta}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (contagem de prazos)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("contagem_prazo")


def gerar_recurso_cabivel(rng):
    """Qual recurso cabe contra cada tipo de decisão."""
    CABIMENTO = [
        ("sentença", "apelação", "art. 1.009"),
        ("decisão interlocutória que versa sobre tutela provisória",
         "agravo de instrumento", "art. 1.015, I"),
        ("decisão interlocutória sobre mérito do processo",
         "agravo de instrumento", "art. 1.015, II"),
        ("decisão monocrática do relator", "agravo interno", "art. 1.021"),
        ("acórdão com omissão, contradição ou obscuridade",
         "embargos de declaração", "art. 1.022"),
        ("acórdão que contraria lei federal",
         "recurso especial", "art. 105, III, da CF"),
        ("acórdão que contraria dispositivo da Constituição",
         "recurso extraordinário", "art. 102, III, da CF"),
    ]
    for _ in range(50):
        decisao, recurso, fundamento = rng.choice(CABIMENTO)
        distratores = [r for _, r, _ in CABIMENTO if r != recurso]
        distratores += ["mandado de segurança", "reclamação constitucional"]
        rng.shuffle(distratores)

        CENARIOS = [
            f"Em processo cível, foi proferida {decisao}.",
            f"O juízo proferiu {decisao} no curso do processo.",
            f"A parte pretende impugnar {decisao}.",
        ]
        PERGUNTAS = [
            "Qual é o recurso cabível?",
            "O recurso adequado para impugná-la é:",
            "Assinale o recurso previsto no CPC para essa hipótese.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Contra {decisao} cabe {recurso}, conforme {fundamento}."
        )
        q = _montar(enunciado, recurso, distratores, explicacao,
                    "Processo civil (recursos)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("recurso_cabivel")


# ══════════════════════════════════════════
#  DIREITO CIVIL
# ══════════════════════════════════════════

def gerar_prazo_prescricional(rng):
    """Prazo prescricional de uma pretensão específica."""
    for _ in range(50):
        pretensao, prazo, artigo = rng.choice(PRESCRICAO_CIVIL)
        outros = sorted({p for _, p, _ in PRESCRICAO_CIVIL if p != prazo}
                        | {6, 8, 15, 20})
        rng.shuffle(outros)

        # "No caso de a pretensão..." fica pesado; usa-se a forma contraída
        sem_artigo = pretensao
        for art in ("a pretensão ", "a cobrança ", "a reparação "):
            if pretensao.startswith(art):
                sem_artigo = pretensao[2:]
                break

        CENARIOS = [
            f"Considere {pretensao}, prevista no Código Civil.",
            f"O Código Civil fixa prazos prescricionais distintos conforme a "
            f"natureza da pretensão. No caso da {sem_artigo},",
            f"Discute-se em juízo {pretensao}.",
            f"Uma ação judicial tem por objeto {pretensao}.",
        ]
        PERGUNTAS = [
            "Qual é o prazo prescricional, em anos?",
            "o prazo prescricional é de quantos anos?",
            "Determine o prazo prescricional em anos.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Conforme o {artigo} do Código Civil, {pretensao} prescreve em "
            f"{prazo} {_plural(prazo, 'ano')}."
        )
        q = _montar(enunciado, prazo, outros, explicacao,
                    "Direito civil (prescrição)", rng)
        if q:
            return q
    raise RuntimeError("prazo_prescricional")


def gerar_calculo_prescricao(rng):
    """Data-limite para ajuizar, dado o marco inicial e a pretensão."""
    for _ in range(50):
        pretensao, prazo, artigo = rng.choice(PRESCRICAO_CIVIL)
        if prazo > 10:
            continue
        inicio = date(rng.randint(2015, 2022), rng.randint(1, 12), rng.randint(1, 28))
        fim = date(inicio.year + prazo, inicio.month, inicio.day)
        correta = fim.strftime("%d/%m/%Y")

        distratores = [
            date(inicio.year + prazo + 1, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(inicio.year + prazo - 1, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(inicio.year + prazo * 2, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            inicio.strftime("%d/%m/%Y"),
            date(inicio.year + 10, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(inicio.year + max(1, prazo - 2), inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(inicio.year + prazo + 3, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(inicio.year + 1, inicio.month, inicio.day).strftime("%d/%m/%Y"),
        ]

        # As entradas de PRESCRICAO_CIVIL já começam com "a pretensão..." ou
        # "a cobrança...", então o cenário NÃO pode acrescentar outro artigo:
        # "deu origem a a pretensão" era o resultado.
        sem_artigo = pretensao
        for art in ("a pretensão ", "a cobrança ", "a reparação "):
            if pretensao.startswith(art):
                sem_artigo = pretensao[2:]      # remove só o "a "
                break

        CENARIOS = [
            f"{pretensao.capitalize()} nasceu em {inicio.strftime('%d/%m/%Y')}.",
            f"Em {inicio.strftime('%d/%m/%Y')} ocorreu o fato que deu origem "
            f"à {sem_artigo}.",
            f"O direito referente à {sem_artigo} foi violado em "
            f"{inicio.strftime('%d/%m/%Y')}.",
        ]
        PERGUNTAS = [
            "Desconsiderando causas de suspensão ou interrupção, até que data a "
            "ação poderia ser ajuizada?",
            "Sem causas suspensivas ou interruptivas, qual é o termo final do "
            "prazo prescricional?",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {rng.choice(PERGUNTAS)}"
        explicacao = (
            f"Pelo {artigo} do Código Civil, {pretensao} prescreve em {prazo} "
            f"{_plural(prazo, 'ano')}. Contados de "
            f"{inicio.strftime('%d/%m/%Y')}, o prazo se encerra em {correta}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Direito civil (prescrição)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("calculo_prescricao")


def gerar_capacidade_civil(rng):
    """Capacidade civil conforme a idade."""
    for _ in range(50):
        idade = rng.randint(5, 25)
        if idade < 16:
            correta, faixa, artigo = CAPACIDADE_CIVIL[0]
        elif idade < 18:
            correta, faixa, artigo = CAPACIDADE_CIVIL[1]
        else:
            correta, faixa, artigo = CAPACIDADE_CIVIL[2]

        distratores = [c for c, _, _ in CAPACIDADE_CIVIL if c != correta]
        distratores += ["emancipado por concessão dos pais",
                        "incapaz por falta de discernimento"]

        CENARIOS = [
            f"Uma pessoa com {idade} anos de idade pretende praticar ato "
            f"da vida civil.",
            f"Considere uma pessoa de {idade} anos, sem qualquer causa de "
            f"emancipação ou de incapacidade por outro motivo.",
            f"Para fins de direito civil, analisa-se a situação de alguém "
            f"com {idade} anos completos.",
        ]
        PERGUNTAS = [
            "Segundo o Código Civil, essa pessoa é:",
            "Qual é a sua condição quanto à capacidade civil?",
            "No regime do Código Civil, ela é considerada:",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"O Código Civil ({artigo}) classifica como {correta} quem é "
            f"{faixa}. Com {idade} anos, a pessoa se enquadra nessa categoria."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Direito civil (capacidade)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("capacidade_civil")


# ══════════════════════════════════════════
#  DIREITO CONSTITUCIONAL
# ══════════════════════════════════════════

def gerar_competencia_legislativa(rng):
    """Competência legislativa: União, Estados ou Municípios."""
    for _ in range(50):
        materia, competencia, artigo = rng.choice(COMPETENCIA_LEGISLATIVA)
        distratores = list({c for _, c, _ in COMPETENCIA_LEGISLATIVA
                            if c != competencia})
        distratores += ["comum a todos os entes federativos",
                        "exclusiva do Distrito Federal",
                        "suplementar dos Municípios"]
        rng.shuffle(distratores)

        CENARIOS = [
            f"A Constituição Federal reparte a competência legislativa entre "
            f"os entes da Federação. Quanto à matéria de {materia},",
            f"Discute-se qual ente federativo pode legislar sobre {materia}.",
            f"Um projeto de lei trata de {materia}.",
        ]
        PERGUNTAS = [
            "a competência legislativa é:",
            "Qual é a natureza da competência legislativa?",
            "Segundo a Constituição, a competência para legislar é:",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Conforme o {artigo} da Constituição Federal, a competência para "
            f"legislar sobre {materia} é {competencia}."
        )
        q = _montar(enunciado, competencia, distratores, explicacao,
                    "Direito constitucional (competências)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("competencia_legislativa")


def gerar_quorum(rng):
    """Quórum de aprovação de espécies normativas."""
    for _ in range(50):
        especie, quorum, artigo = rng.choice(QUORUM_NORMATIVO)
        distratores = [q for _, q, _ in QUORUM_NORMATIVO if q != quorum]
        distratores += ["dois terços dos votos, em turno único, em cada Casa",
                        "unanimidade dos membros presentes em cada Casa",
                        "quatro quintos dos votos, em dois turnos"]
        rng.shuffle(distratores)

        CENARIOS = [
            f"Tramita no Congresso Nacional proposta de {especie}.",
            f"Para que seja aprovada uma {especie},",
            f"A Constituição estabelece quóruns distintos conforme a espécie "
            f"normativa. No caso de {especie},",
        ]
        PERGUNTAS = [
            "qual é o quórum exigido para aprovação?",
            "o quórum constitucionalmente exigido é de:",
            "Determine o quórum de aprovação.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Segundo o {artigo} da Constituição Federal, a aprovação de "
            f"{especie} exige {quorum}."
        )
        q = _montar(enunciado, quorum, distratores, explicacao,
                    "Direito constitucional (processo legislativo)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("quorum")


# ══════════════════════════════════════════
#  PENAL E TRABALHISTA
# ══════════════════════════════════════════

def gerar_prazo_penal(rng):
    """Prazos do processo penal (contados em dias CORRIDOS)."""
    for _ in range(50):
        ato, prazo, artigo = rng.choice(PRAZOS_PENAIS)
        outros = _prazos_falsos(
            prazo,
            {p for _, p, _ in PRAZOS_PENAIS} | {2, 3, 5, 8, 15, 20, 30},
            rng)

        CENARIOS = [
            f"Em processo penal, a parte pretende apresentar {ato}.",
            f"Intimada da decisão em processo criminal, a defesa deve "
            f"protocolar {ato}.",
            f"No rito do Código de Processo Penal, cabe {ato}.",
        ]
        PERGUNTAS = [
            "Qual é o prazo legal, em dias?",
            "O prazo previsto no CPP é de quantos dias?",
            "Determine o prazo em dias.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"O prazo para {ato} é de {prazo} {_plural(prazo, 'dia')}, "
            f"conforme o {artigo}. Diferentemente do processo civil, os prazos "
            f"penais são contados em dias corridos."
        )
        q = _montar(enunciado, prazo, outros, explicacao,
                    "Processo penal (prazos)", rng)
        if q:
            return q
    raise RuntimeError("prazo_penal")


def gerar_prazo_trabalhista(rng):
    """Prazos da Justiça do Trabalho (dias úteis após a Lei 13.467/2017)."""
    for _ in range(50):
        ato, prazo, artigo = rng.choice(PRAZOS_TRABALHISTAS)
        outros = _prazos_falsos(
            prazo,
            {p for _, p, _ in PRAZOS_TRABALHISTAS} | {2, 3, 5, 10, 15, 20, 30},
            rng)

        CENARIOS = [
            f"Em reclamação trabalhista, a parte pretende interpor {ato}.",
            f"Publicada a sentença na Justiça do Trabalho, cabe {ato}.",
            f"No processo do trabalho, a parte deve apresentar {ato}.",
        ]
        PERGUNTAS = [
            "Qual é o prazo legal, em dias úteis?",
            "O prazo previsto na CLT, em dias úteis, é de:",
            "Determine o prazo em dias úteis.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Conforme o {artigo}, o prazo para {ato} é de {prazo} dias úteis. "
            f"A contagem em dias úteis foi adotada pela Reforma Trabalhista "
            f"(Lei 13.467/2017)."
        )
        q = _montar(enunciado, prazo, outros, explicacao,
                    "Direito do trabalho (prazos)", rng, _dias_uteis)
        if q:
            return q
    raise RuntimeError("prazo_trabalhista")


# ══════════════════════════════════════════
#  HONORÁRIOS
# ══════════════════════════════════════════

def gerar_honorarios(rng):
    """
    Honorários sucumbenciais: percentual mínimo e máximo sobre o valor
    da condenação (CPC art. 85, § 2º, para causas em geral).
    """
    for _ in range(50):
        valor = rng.randrange(10_000, 900_000, 5_000)
        pct = rng.choice([10, 12, 15, 18, 20])
        correta = round(valor * pct / 100, 2)

        distratores = [
            round(valor * (pct + 5) / 100, 2),
            round(valor * (pct - 5) / 100, 2),
            round(valor * pct / 1000, 2),
            round(valor / pct, 2),
            round(valor * pct / 10, 2),
            round(valor * (pct + 10) / 100, 2),
            round(valor * max(1, pct - 8) / 100, 2),
            round(valor * pct / 200, 2),      # aplicou metade do percentual
        ]

        CENARIOS = [
            f"Julgado procedente o pedido, o réu foi condenado a pagar "
            f"R$ {_fmt(valor)},00. O juiz fixou honorários sucumbenciais em "
            f"{pct}% sobre o valor da condenação.",
            f"Em sentença que condenou a parte ré ao pagamento de "
            f"R$ {_fmt(valor)},00, os honorários advocatícios foram arbitrados "
            f"em {pct}% do valor condenatório.",
            f"A condenação totalizou R$ {_fmt(valor)},00 e o magistrado "
            f"estabeleceu honorários de sucumbência de {pct}%.",
        ]
        PERGUNTAS = [
            "Qual é o valor dos honorários, em reais?",
            "Os honorários advocatícios correspondem a que valor?",
            "Determine o valor dos honorários sucumbenciais.",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"O art. 85, § 2º, do CPC prevê honorários entre 10% e 20% sobre "
            f"o valor da condenação. Aplicando {pct}% sobre "
            f"R$ {_fmt(valor)},00: {valor} × {pct/100} = "
            f"R$ {_fmt(int(correta))},00."
        )
        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (honorários)", rng, formatador=fmt,
                    tipo_resposta="monetaria")
        if q:
            return q
    raise RuntimeError("honorarios")


# ══════════════════════════════════════════
#  APLICAÇÃO DE REGRA A CASO CONCRETO
#
#  Diferentemente dos templates de prazo, aqui a resposta não está
#  numa tabela: exige ENCADEAR regras. O aluno precisa identificar
#  qual dispositivo incide, aplicá-lo à situação e concluir.
# ══════════════════════════════════════════

def gerar_efeito_recurso(rng):
    """
    Efeitos dos recursos: interrupção vs. suspensão de prazo.

    Distinção clássica: embargos de declaração INTERROMPEM (o prazo
    recomeça do zero), enquanto a suspensão apenas pausa. Errar isso
    custa a perda do prazo na prática.
    """
    from datetime import date as _d, timedelta as _td
    for _ in range(60):
        base = _d(2025, rng.randint(2, 10), rng.randint(1, 25))
        while base.weekday() >= 5:
            base += _td(days=1)

        dias_corridos = rng.randint(2, 8)   # dias úteis já decorridos
        atual = base
        cont = 0
        while cont < dias_corridos:
            atual += _td(days=1)
            if atual.weekday() < 5:
                cont += 1
        data_ed = atual

        # Julgados os ED, o prazo da apelação RECOMEÇA integralmente
        julgamento = data_ed + _td(days=rng.randint(10, 30))
        while julgamento.weekday() >= 5:
            julgamento += _td(days=1)

        cont, fim = 0, julgamento
        while cont < 15:
            fim += _td(days=1)
            if fim.weekday() < 5:
                cont += 1
        correta = fim.strftime("%d/%m/%Y")

        # Distratores: tratar como SUSPENSÃO (só o saldo) e outros erros
        saldo = 15 - dias_corridos
        cont, d_suspensao = 0, julgamento
        while cont < saldo:
            d_suspensao += _td(days=1)
            if d_suspensao.weekday() < 5:
                cont += 1

        distratores = [
            d_suspensao.strftime("%d/%m/%Y"),          # tratou como suspensão
            (julgamento + _td(days=15)).strftime("%d/%m/%Y"),  # dias corridos
            julgamento.strftime("%d/%m/%Y"),           # começou no próprio dia
            (fim + _td(days=7)).strftime("%d/%m/%Y"),
            base.strftime("%d/%m/%Y"),
        ]

        enunciado = (
            f"Publicada a sentença em {base.strftime('%d/%m/%Y')}, a parte "
            f"deixou transcorrer {dias_corridos} dias úteis e, em "
            f"{data_ed.strftime('%d/%m/%Y')}, opôs embargos de declaração. "
            f"Os embargos foram julgados e a decisão publicada em "
            f"{julgamento.strftime('%d/%m/%Y')}. Desconsiderando feriados, "
            f"qual é o último dia para interpor apelação?"
        )
        explicacao = (
            f"Os embargos de declaração INTERROMPEM o prazo dos demais "
            f"recursos (art. 1.026 do CPC) — não o suspendem. Interrompido, o "
            f"prazo recomeça integralmente da publicação da decisão dos "
            f"embargos, desprezando os {dias_corridos} dias já decorridos. "
            f"Contando 15 dias úteis a partir de "
            f"{julgamento.strftime('%d/%m/%Y')}, o termo final é {correta}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (efeitos dos recursos)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("efeito_recurso")


def gerar_competencia_valor(rng):
    """
    Competência do Juizado Especial pelo valor da causa.

    Exige combinar: teto de 40 salários mínimos (Lei 9.099/95), valor do
    salário vigente e a natureza da parte — pessoa jurídica de direito
    público não pode figurar no polo passivo do JEC comum.
    """
    SALARIO = 1518   # valor de referência informado no próprio enunciado
    for _ in range(60):
        teto = 40 * SALARIO
        acima = rng.random() < 0.5
        valor = (rng.randrange(teto + 1000, teto * 2, 500) if acima
                 else rng.randrange(5000, teto - 1000, 500))

        if acima:
            correta = "Justiça Comum estadual, por exceder o teto do Juizado Especial"
        else:
            correta = "Juizado Especial Cível, por estar dentro do teto de 40 salários mínimos"

        distratores = [
            "Juizado Especial Cível, por estar dentro do teto de 40 salários mínimos"
            if acima else
            "Justiça Comum estadual, por exceder o teto do Juizado Especial",
            "Justiça Federal, independentemente do valor da causa",
            "Juizado Especial da Fazenda Pública, em razão do valor",
            "Vara Empresarial, por se tratar de matéria patrimonial",
        ]

        CEN = [
            f"Uma ação de cobrança entre particulares tem valor da causa de "
            f"R$ {_fmt(valor)},00. Considere o salário mínimo de "
            f"R$ {_fmt(SALARIO)},00.",
            f"O autor pretende ajuizar demanda no valor de R$ {_fmt(valor)},00 "
            f"contra outro particular, sendo o salário mínimo de "
            f"R$ {_fmt(SALARIO)},00.",
        ]
        PER = ["Qual é o órgão competente?",
               "A competência é da:",
               "Determine o juízo competente."]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"O art. 3º, I, da Lei 9.099/95 fixa a competência do Juizado "
            f"Especial Cível em causas de até 40 salários mínimos. Com salário "
            f"de R$ {_fmt(SALARIO)},00, o teto é 40 × {_fmt(SALARIO)} = "
            f"R$ {_fmt(teto)},00. Como a causa vale R$ {_fmt(valor)},00, valor "
            f"{'superior' if acima else 'inferior'} ao teto, a competência é "
            f"{'da Justiça Comum estadual' if acima else 'do Juizado Especial Cível'}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (competência)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("competencia_valor")


def gerar_termo_inicial(rng):
    """
    Termo inicial do prazo conforme a modalidade de citação/intimação.

    O CPC fixa marcos distintos (art. 231): correio conta da juntada do
    AR, oficial de justiça da juntada do mandado, edital do fim do prazo
    do edital, e o Diário da publicação. Confundir custa o prazo.
    """
    MODALIDADES = [
        ("citação pelo correio",
         "a data de juntada aos autos do aviso de recebimento", "art. 231, I"),
        ("citação por oficial de justiça",
         "a data de juntada aos autos do mandado cumprido",     "art. 231, II"),
        ("citação por edital",
         "o dia útil seguinte ao fim do prazo do edital",       "art. 231, IV"),
        ("intimação pelo Diário da Justiça",
         "a data da publicação",                                 "art. 231, VII"),
        ("citação por meio eletrônico",
         "o dia útil seguinte à consulta ao teor da citação",   "art. 231, V"),
    ]
    for _ in range(50):
        modalidade, marco, artigo = rng.choice(MODALIDADES)
        distratores = [m for _, m, _ in MODALIDADES if m != marco]
        distratores.append("a data em que o ato foi determinado pelo juiz")

        CEN = [
            # Era "o réu foi citado por meio de {modalidade}", e a lista
            # de modalidades mistura citações e intimações: saía "citado
            # por meio de intimação pelo Diário da Justiça", que confunde
            # dois atos distintos, e "citado por meio de citação por meio
            # eletrônico". "Comunicada" cobre os dois casos.
            f"Em processo cível, a parte foi comunicada por {modalidade}.",
            f"Realizou-se a {modalidade} no curso do processo.",
            f"A comunicação processual ocorreu por {modalidade}.",
        ]
        PER = [
            "A partir de que marco se inicia a contagem do prazo?",
            "O termo inicial do prazo é:",
            "Segundo o CPC, o prazo começa a correr de:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Conforme o {artigo} do CPC, na {modalidade} o prazo tem como "
            f"termo inicial {marco}."
        )
        q = _montar(enunciado, marco, distratores, explicacao,
                    "Processo civil (termo inicial)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("termo_inicial")


def gerar_prescricao_interrompida(rng):
    """
    Prescrição com causa interruptiva: o prazo RECOMEÇA do zero.

    Diferente da suspensão, em que o prazo é apenas pausado e depois
    retomado de onde parou (CC arts. 197-204).
    """
    for _ in range(60):
        pretensao, prazo, artigo = rng.choice(PRESCRICAO_CIVIL)
        if prazo > 10 or prazo < 2:
            continue

        inicio = date(rng.randint(2015, 2020), rng.randint(1, 12), rng.randint(1, 28))
        anos_ate_interrupcao = rng.randint(1, prazo - 1)
        interrupcao = date(inicio.year + anos_ate_interrupcao,
                           inicio.month, inicio.day)
        # Interrompida, a prescrição recomeça integralmente
        fim = date(interrupcao.year + prazo, interrupcao.month, interrupcao.day)
        correta = fim.strftime("%d/%m/%Y")

        # Distrator principal: tratar como SUSPENSÃO (só o saldo)
        saldo = prazo - anos_ate_interrupcao
        d_suspensao = date(interrupcao.year + saldo, interrupcao.month, interrupcao.day)

        distratores = [
            d_suspensao.strftime("%d/%m/%Y"),
            date(inicio.year + prazo, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(fim.year + 1, fim.month, fim.day).strftime("%d/%m/%Y"),
            interrupcao.strftime("%d/%m/%Y"),
            date(inicio.year + prazo * 2, inicio.month, inicio.day).strftime("%d/%m/%Y"),
            date(fim.year + 3, fim.month, fim.day).strftime("%d/%m/%Y"),
            date(fim.year + 2, fim.month, fim.day).strftime("%d/%m/%Y"),
            date(interrupcao.year + prazo * 2, interrupcao.month,
                 interrupcao.day).strftime("%d/%m/%Y"),
        ]

        ATOS = [
            "o devedor reconheceu inequivocamente a dívida",
            "houve protesto judicial regularmente promovido",
            "o credor obteve despacho que ordenou a citação",
        ]
        ato = rng.choice(ATOS)

        # As entradas da tabela já começam por "a pretensão...", e o
        # enunciado acrescentava outro "A pretensão referente à" na
        # frente: saía "A pretensão referente à pretensão sem prazo
        # específico previsto em lei". O sujeito é a própria entrada.
        sujeito = pretensao[0].upper() + pretensao[1:]
        enunciado = (
            f"{sujeito} nasceu em "
            f"{inicio.strftime('%d/%m/%Y')}. Em "
            f"{interrupcao.strftime('%d/%m/%Y')}, {ato}, o que interrompeu a "
            f"prescrição. Até que data a ação pode ser ajuizada?"
        )
        explicacao = (
            f"A prescrição dessa pretensão é de {prazo} {_plural(prazo, 'ano')} "
            f"({artigo} do CC). Interrompida em "
            f"{interrupcao.strftime('%d/%m/%Y')}, ela recomeça a correr por "
            f"INTEIRO a partir dessa data (art. 202, parágrafo único, do CC) — "
            f"não se aproveita o tempo anterior, ao contrário do que ocorre na "
            f"suspensão. Assim, o novo termo final é {correta}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Direito civil (prescrição)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("prescricao_interrompida")


def gerar_cabimento_concreto(rng):
    """
    Cabimento de agravo de instrumento: o rol do art. 1.015 é TAXATIVO.

    A pergunta não é "o que é agravo", e sim se AQUELA decisão específica
    comporta agravo ou se a matéria fica para a preliminar de apelação.
    """
    CASOS_AGRAVO = [
        # ── Cabe agravo: hipóteses do rol taxativo do art. 1.015 ──
        ("indeferiu o pedido de tutela de urgência",        True,  "art. 1.015, I"),
        ("concedeu tutela de evidência",                    True,  "art. 1.015, I"),
        ("revogou tutela provisória antes concedida",       True,  "art. 1.015, I"),
        ("decidiu sobre o mérito do processo",              True,  "art. 1.015, II"),
        ("rejeitou a alegação de convenção de arbitragem",  True,  "art. 1.015, III"),
        ("decidiu sobre incidente de desconsideração da personalidade jurídica",
                                                            True,  "art. 1.015, IV"),
        ("rejeitou o pedido de gratuidade da justiça",      True,  "art. 1.015, V"),
        ("revogou a gratuidade antes deferida",             True,  "art. 1.015, V"),
        ("determinou a exibição ou posse de documento",     True,  "art. 1.015, VI"),
        ("excluiu litisconsorte do processo",               True,  "art. 1.015, VII"),
        ("rejeitou o pedido de limitação do litisconsórcio", True, "art. 1.015, VIII"),
        ("admitiu ou não a intervenção de terceiros",       True,  "art. 1.015, IX"),
        ("decidiu sobre a concessão, modificação ou revogação do efeito suspensivo aos embargos à execução",
                                                            True,  "art. 1.015, X"),
        ("determinou a redistribuição do ônus da prova",    True,  "art. 1.015, XI"),
        ("versou sobre liquidação de sentença",             True,  "art. 1.015, parágrafo único"),
        ("foi proferida na fase de cumprimento de sentença", True, "art. 1.015, parágrafo único"),

        # ── NÃO cabe: matéria fora do rol, vai em preliminar de apelação ──
        ("rejeitou a alegação de incompetência absoluta",   False, "art. 1.015 (rol taxativo)"),
        ("indeferiu a produção de prova pericial",          False, "art. 1.015 (rol taxativo)"),
        ("indeferiu pedido de adiamento de audiência",      False, "art. 1.015 (rol taxativo)"),
        ("determinou a produção de prova testemunhal",      False, "art. 1.015 (rol taxativo)"),
        ("indeferiu o pedido de segredo de justiça",        False, "art. 1.015 (rol taxativo)"),
        ("rejeitou a impugnação ao valor da causa",         False, "art. 1.015 (rol taxativo)"),
        ("indeferiu o pedido de perícia complementar",      False, "art. 1.015 (rol taxativo)"),
        ("designou nova data para audiência de instrução",  False, "art. 1.015 (rol taxativo)"),
    ]
    for _ in range(50):
        decisao, cabe, fundamento = rng.choice(CASOS_AGRAVO)
        if cabe:
            correta = "Cabe agravo de instrumento, por estar previsto no rol legal."
        else:
            correta = ("Não cabe agravo de instrumento; a questão deve ser "
                       "suscitada em preliminar de apelação.")

        distratores = [
            ("Não cabe agravo de instrumento; a questão deve ser suscitada em "
             "preliminar de apelação.") if cabe else
            "Cabe agravo de instrumento, por estar previsto no rol legal.",
            "Cabe apelação imediata contra a decisão interlocutória.",
            "Cabe mandado de segurança, por inexistir recurso próprio.",
            "Cabe agravo retido, a ser reiterado nas razões de apelação.",
        ]

        CENARIOS = [
            f"No curso do processo de conhecimento, o juízo proferiu decisão "
            f"interlocutória que {decisao}. A parte prejudicada pretende "
            f"impugná-la de imediato.",
            f"Durante a instrução, o magistrado proferiu decisão que "
            f"{decisao}. O advogado da parte vencida avalia como recorrer.",
            f"Foi publicada decisão interlocutória que {decisao}. "
            f"A parte quer levar a questão ao tribunal desde já.",
            f"Em processo cível, o juízo {decisao}. A parte prejudicada "
            f"consulta seu advogado sobre a via recursal cabível.",
        ]
        PERGUNTAS = [
            "Assinale a alternativa correta.",
            "Sobre o cabimento recursal, assinale a alternativa correta.",
            "Qual é a orientação correta quanto ao recurso?",
            "Assinale a alternativa que indica o tratamento correto.",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(PERGUNTAS)}"
        if cabe:
            explicacao = (
                f"O rol do art. 1.015 do CPC é taxativo, e a decisão que "
                f"{decisao} está expressamente prevista ({fundamento}). Logo, "
                f"cabe agravo de instrumento."
            )
        else:
            explicacao = (
                f"A decisão que {decisao} não consta do rol taxativo do "
                f"art. 1.015 do CPC. Nessa hipótese, não há preclusão imediata: "
                f"a matéria deve ser suscitada em preliminar de apelação ou nas "
                f"contrarrazões (art. 1.009, § 1º). O agravo retido foi extinto "
                f"pelo CPC/2015."
            )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Processo civil (cabimento recursal)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("cabimento_concreto")


# ──────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────

TEMPLATES_DIREITO = {
    "prazo_recursal":          gerar_prazo_recursal,
    "prazo_dobro":             gerar_prazo_dobro,
    "contagem_prazo":          gerar_contagem_prazo,
    "recurso_cabivel":         gerar_recurso_cabivel,
    "prazo_prescricional":     gerar_prazo_prescricional,
    "calculo_prescricao":      gerar_calculo_prescricao,
    "capacidade_civil":        gerar_capacidade_civil,
    "competencia_legislativa": gerar_competencia_legislativa,
    "quorum":                  gerar_quorum,
    "prazo_penal":             gerar_prazo_penal,
    "prazo_trabalhista":       gerar_prazo_trabalhista,
    "honorarios":              gerar_honorarios,
    # ── Aplicação de regra a caso concreto ──
    "efeito_recurso":          gerar_efeito_recurso,
    "competencia_valor":       gerar_competencia_valor,
    "termo_inicial":           gerar_termo_inicial,
    "prescricao_interrompida": gerar_prescricao_interrompida,
    "cabimento_concreto":      gerar_cabimento_concreto,
}

TOPICOS_DIREITO = {
    "processo_civil":  ["prazo_recursal", "prazo_dobro", "contagem_prazo",
                        "recurso_cabivel", "honorarios", "efeito_recurso",
                        "competencia_valor", "termo_inicial",
                        "cabimento_concreto"],
    "civil":           ["prazo_prescricional", "calculo_prescricao",
                        "capacidade_civil", "prescricao_interrompida"],
    "constitucional":  ["competencia_legislativa", "quorum"],
    "penal":           ["prazo_penal"],
    "trabalho":        ["prazo_trabalhista"],
}

PALAVRAS_CHAVE = {
    "prazo_recursal":          ["prazo", "recurso", "apelacao", "agravo",
                                "processo civil", "cpc", "embargos"],
    "prazo_dobro":             ["prazo em dobro", "fazenda publica", "ministerio publico",
                                "defensoria", "prerrogativa", "processo civil"],
    "contagem_prazo":          ["contagem de prazo", "dias uteis", "prazo processual",
                                "cpc", "intimacao"],
    "recurso_cabivel":         ["recurso", "cabimento", "sentenca", "decisao interlocutoria",
                                "processo civil", "apelacao", "agravo"],
    "prazo_prescricional":     ["prescricao", "prazo prescricional", "codigo civil",
                                "pretensao", "direito civil", "decadencia"],
    "calculo_prescricao":      ["prescricao", "prazo", "codigo civil", "pretensao"],
    "capacidade_civil":        ["capacidade", "incapaz", "menor", "direito civil",
                                "pessoa natural", "emancipacao"],
    "competencia_legislativa": ["competencia", "federalismo", "uniao", "estados",
                                "municipios", "constitucional", "reparticao"],
    "quorum":                  ["quorum", "processo legislativo", "emenda constitucional",
                                "lei complementar", "constitucional"],
    "prazo_penal":             ["processo penal", "cpp", "prazo penal", "apelacao criminal",
                                "recurso em sentido estrito"],
    "prazo_trabalhista":       ["trabalhista", "clt", "justica do trabalho",
                                "recurso ordinario", "direito do trabalho"],
    "honorarios":              ["honorarios", "sucumbencia", "custas", "processo civil"],
    "efeito_recurso":          ["embargos de declaracao", "interrupcao", "suspensao",
                                "efeito dos recursos", "prazo", "processo civil"],
    "competencia_valor":       ["competencia", "juizado especial", "valor da causa",
                                "lei 9099", "processo civil"],
    "termo_inicial":           ["citacao", "intimacao", "termo inicial", "contagem",
                                "prazo", "processo civil"],
    "prescricao_interrompida": ["prescricao", "interrupcao", "suspensao",
                                "codigo civil", "causas interruptivas"],
    "cabimento_concreto":      ["agravo de instrumento", "rol taxativo", "cabimento",
                                "decisao interlocutoria", "processo civil"],
}


# "contagem", "prazo" e "competencia" aparecem fora do direito.
CHAVES_GENERICAS = {
    "prazo", "contagem", "competencia", "recurso", "processo civil",
    "intimacao", "citacao", "custas", "cabimento", "decadencia",
    "pretensao", "suspensao", "interrupcao", "valor da causa",
}


def _normalizar(txt: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def templates_para_topicos(topicos: list) -> list:
    """
    Casa os tópicos de um livro indexado com os templates deste gerador.

    A comparação é por PALAVRA INTEIRA, não por substring: "ip" não pode
    casar dentro de "princípio", nem "or" dentro de "ordenação". Antes
    dessa correção, um livro de combinatória acionava geradores de rede
    porque "Princípio" contém "ip".

    Além disso, chaves de UMA palavra genérica (como "contagem", que
    aparece em combinatória, em análise de algoritmos e em prazo
    processual) só valem quando acompanhadas de outra chave do mesmo
    template — sozinhas, geram falso casamento.
    """
    texto = " " + " ".join(_normalizar(str(t)) for t in topicos) + " "

    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        especificas = 0
        genericas   = 0
        for chave in chaves:
            cn = _normalizar(chave)
            if not cn:
                continue
            # \b não funciona bem com acentos removidos + espaços; usamos
            # delimitadores explícitos de palavra.
            padrao = r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])'
            if re.search(padrao, texto):
                if cn in CHAVES_GENERICAS:
                    genericas += 1
                else:
                    especificas += 1

        # Uma chave específica basta; genéricas NÃO acionam sozinhas,
        # por mais que se acumulem. A regra anterior aceitava duas
        # genéricas, e um Caderno do Ministério da Saúde acionava o
        # gerador de portas por conter "porta de entrada do SUS" e
        # "protocolo de acolhimento" — nenhuma das duas sobre redes.
        #
        # O custo é perder algum casamento legítimo em livro de
        # vocabulário pobre; o benefício é nunca gerar questão de outra
        # área, que é o erro visível para o usuário.
        if especificas >= 1:
            achados.append(nome)

    return achados

def gerar_lote(quantidade=12, topico=None, templates=None, seed=None):
    rng = random.Random(seed)
    if templates:
        nomes = [n for n in templates if n in TEMPLATES_DIREITO]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
    elif topico:
        nomes = TOPICOS_DIREITO.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS_DIREITO)}")
    else:
        nomes = list(TEMPLATES_DIREITO)

    funcoes = [TEMPLATES_DIREITO[n] for n in nomes]
    rng.shuffle(funcoes)

    questoes = []
    for i in range(quantidade):
        q = funcoes[i % len(funcoes)](rng)
        q["numero"] = i + 1
        questoes.append(q)
    return questoes


def gerar_para_api(quantidade=10, topico=None, templates=None, seed=None):
    """
    Formato compatível com salvar_questoes_banco.
    Metadados internos NÃO são incluídos.
    """
    lote = gerar_lote(quantidade, topico, templates, seed)
    questoes_limpas, gabarito_final = [], []
    for q in lote:
        questoes_limpas.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": False,
        })
        gabarito_final.append({
            "numero":           q["numero"],
            "resposta_correta": q["gabarito"],
            "explicacao":       q["explicacao"],
            # O TÓPICO vai junto. O montador de simulado usa-o para
            # limitar quantas questões do mesmo assunto entram no
            # caderno, e sem ele essa trava ficava sempre inerte — um
            # simulado de direito saía com doze perguntas de prazo
            # trabalhista, onze delas com a mesma resposta.
            #
            # Serve também ao aplicativo, que pode relatar o desempenho
            # por assunto sem precisar reabrir o gerador.
            "topico":           q.get("topico", ""),
            # O FATO — par template+resposta — vai junto pelo mesmo
            # motivo do tópico. O veto interno de cada gerador vale
            # dentro de uma chamada; o simulado faz várias, e sem esta
            # chave o mesmo fato voltava com outra redação: "recurso de
            # revista: 8 dias" apareceu três vezes no mesmo caderno.
            #
            # O montador remove o campo antes de devolver, para não
            # sujar o que é gravado no banco.
            "_fato":            q.get("_fato", ""),
        })
    return questoes_limpas, gabarito_final


if __name__ == "__main__":
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    topico = sys.argv[2] if len(sys.argv) > 2 else None
    for q in gerar_lote(qtd, topico):
        print("─" * 66)
        print(f"Q{q['numero']} [{q['topico']}]\n")
        print(q["enunciado"], "\n")
        for L, t in q["alternativas"].items():
            print(f"   {L}) {t}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("─" * 66)
    print(f"\n{qtd} questões | Dispositivos verificados em fonte primária.\n")
