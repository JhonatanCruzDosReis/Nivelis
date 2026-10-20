"""
=============================================================
  NIVELIS — Gerador Procedural: Saúde
  Foco: ENADE — Medicina, Enfermagem, Farmácia, Biomedicina
=============================================================

  Gera questões SEM IA. O Python calcula o gabarito, que é
  correto por construção.

  ESCOPO DELIBERADO
  -----------------
  Cobre apenas conteúdo cuja resposta vem de FÓRMULA ESTÁVEL:
  aritmética clínica, epidemiologia e bioestatística. Essas
  fórmulas não mudam com diretriz nem com ano.

  NÃO cobre — e isso é intencional:
    • dose padrão de fármacos específicos
    • conduta terapêutica ou diagnóstico
    • valores de referência que variam por protocolo

  Nos templates de posologia, a prescrição (mg/kg, mL, etc.)
  vem SEMPRE como dado do enunciado. A questão avalia o
  cálculo, não afirma qual dose é correta para um paciente.
  Para conteúdo clínico variável, use as rotas com IA
  apoiadas em livro indexado.

  11 TEMPLATES:

  CÁLCULOS CLÍNICOS
    1. Gotejamento (gotas/min e microgotas/min)
    2. Tempo de infusão
    3. Conversão de unidades (g/mg/mcg, L/mL)
    4. Diluição e concentração
    5. Dose por peso corporal (dose prescrita dada)
  EPIDEMIOLOGIA
    6. Prevalência e incidência
    7. Sensibilidade e especificidade (tabela 2x2)
    8. Valor preditivo positivo e negativo
  BIOESTATÍSTICA
    9. Risco relativo e redução de risco
   10. Odds ratio
   11. NNT (número necessário para tratar)

  USO:
    python gerador_saude.py            # 11 questões
    python gerador_saude.py 20 epidemiologia
=============================================================
"""

import sys
import re
import random
from math import ceil

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "fracao", "simbolica", "codigo_numerico",
    "sequencia", "textual", "endereco_ip", "percentual", "monetaria",
}


# ──────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────

def _fmt(v) -> str:
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return str(v)


def _fmt_dec(v, casas=1) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def _fmt_pct(v) -> str:
    return f"{v:.1f}%".replace(".", ",")


def _plural(n, singular, plural=None):
    if plural is None:
        plural = singular + "s"
    return singular if abs(n) == 1 else plural


def _juntar(anterior: str, seguinte: str) -> str:
    """Ajusta a inicial conforme a pontuação da parte anterior."""
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=_fmt, tipo_resposta="numerica"):
    """
    Monta a questão. Rejeita distratores IMPOSSÍVEIS por natureza.

    Também descarta os de ordem de grandeza incompatível: uma opção
    100 vezes maior que a resposta é eliminada de imediato pelo aluno,
    e a questão passa a ter quatro alternativas efetivas em vez de cinco.

    Medidas de saúde são grandezas positivas: risco, dose, volume,
    concentração e razões nunca são negativos. Um distrator negativo não
    engana ninguém e sinaliza erro no cálculo do próprio distrator.
    """
    assert tipo_resposta in TIPOS_RESPOSTA
    unicos = []
    escalar = isinstance(correta, (int, float)) and correta != 0
    for d in distratores:
        if isinstance(d, (int, float)) and d < 0:
            continue                      # grandeza negativa não existe aqui
        # A checagem NÃO se aplica à conversão de unidades: ali a
        # diferença de escala É o conteúdo da questão (1 g = 1000 mg),
        # e distratores em outra ordem de grandeza são justamente os
        # erros que se quer testar.
        if (escalar and isinstance(d, (int, float)) and d != 0
                and "conversão" not in topico.lower()
                and "unidade" not in topico.lower()):
            razao = max(abs(d), abs(correta)) / min(abs(d), abs(correta))
            if razao > 60:
                continue                  # descartável à primeira vista
        # Percentuais e taxas exigem separação ABSOLUTA mínima: 81,8% e
        # 82,1% diferem só 0,4% em termos relativos, mas quem arredondou
        # num passo intermediário erra sem ter errado o método.
        if (escalar and isinstance(d, (int, float))
                and tipo_resposta == "percentual"):
            if any(isinstance(u, (int, float)) and abs(d - u) < 1.0
                   for u in unicos + [correta]):
                continue

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
        "origem":         "gerador_saude",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
    }


# ══════════════════════════════════════════
#  CÁLCULOS CLÍNICOS
# ══════════════════════════════════════════

def gerar_gotejamento(rng):
    """
    Gotejamento: gotas/min = volume(mL) / (tempo(h) × 3).
    Microgotas/min = volume(mL) / tempo(h).
    Fórmulas aritméticas padrão, independentes de protocolo.
    """
    for _ in range(60):
        # Volume e tempo são sorteados JUNTOS: combinações como 250 mL em
        # 12 horas dão contas corretas, mas cenários que um profissional
        # estranharia. Os pares abaixo refletem prescrições usuais.
        volume, horas = rng.choice([
            (250, 1), (250, 2), (250, 3),
            (500, 2), (500, 3), (500, 4), (500, 6),
            (750, 4), (750, 6),
            (1000, 4), (1000, 6), (1000, 8), (1000, 10),
            (1500, 8), (1500, 10), (1500, 12),
            (2000, 12), (2000, 24),
        ])
        micro  = rng.random() < 0.4

        if micro:
            correta = round(volume / horas)
            unidade = "microgotas por minuto"
            formula = (f"microgotas/min = volume (mL) ÷ tempo (h), ou seja, "
                       f"{volume} ÷ {horas} = {correta}")
            distratores = [round(volume / (horas * 3)), round(volume / horas) + 5,
                           round(volume / horas) - 5, volume // (horas * 2),
                           round(volume * horas / 60)]
        else:
            correta = round(volume / (horas * 3))
            unidade = "gotas por minuto"
            formula = (f"gotas/min = volume (mL) ÷ (tempo (h) × 3), ou seja, "
                       f"{volume} ÷ ({horas} × 3) = {volume} ÷ {horas * 3} = {correta}")
            distratores = [round(volume / horas), round(volume / (horas * 3)) + 4,
                           round(volume / (horas * 3)) - 4, round(volume / (horas * 60)),
                           round(volume * 3 / horas)]

        SOLUCOES = ["soro fisiológico 0,9%", "solução glicosada 5%",
                    "Ringer lactato", "soro fisiológico"]
        sol = rng.choice(SOLUCOES)

        CENARIOS = [
            f"Foi prescrita a infusão de {volume} mL de {sol} a ser administrada "
            f"em {horas} horas.",
            f"Um paciente internado recebe prescrição de {volume} mL de {sol} "
            f"para infusão contínua em {horas} horas.",
            f"A equipe de enfermagem deve administrar {volume} mL de {sol} ao "
            f"longo de {horas} horas.",
            f"Consta na prescrição médica: {volume} mL de {sol}, infundir em "
            f"{horas} horas.",
            f"Durante o plantão, prescreveu-se {volume} mL de {sol} em {horas} "
            f"horas por via endovenosa.",
        ]
        PERGUNTAS = [
            f"Qual deve ser o gotejamento, em {unidade}?",
            f"O gotejamento a ser ajustado, em {unidade}, é de:",
            f"Determine o gotejamento em {unidade}.",
            f"Nessas condições, quantas {unidade.split(' por ')[0]} por minuto "
            f"devem ser administradas?",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Para infusão em equipo, aplica-se {formula} {unidade}."
        )

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Cálculo de gotejamento", rng)
        if q:
            return q
    raise RuntimeError("gotejamento")


def gerar_tempo_infusao(rng):
    """Tempo de infusão a partir do volume e do gotejamento."""
    for _ in range(60):
        volume = rng.choice([250, 500, 750, 1000, 1500])
        gotas  = rng.choice([15, 20, 25, 28, 30, 33, 42, 50, 60])
        horas  = volume / (gotas * 3)
        # Faixa realista de duração: infusões muito longas para volumes
        # pequenos (250 mL em 8 h) soam artificiais na clínica.
        if not (1.0 <= horas <= 12):
            continue
        # Densidade coerente: ao menos ~60 mL/h
        if volume / horas < 55:
            continue
        correta = round(horas, 1)

        distratores = [round(volume / gotas, 1), round(horas * 2, 1),
                       round(horas / 2, 1), round(volume / (gotas * 60), 1),
                       round(horas + 1, 1)]

        CENARIOS = [
            f"Um frasco de {volume} mL está sendo infundido a {gotas} gotas por minuto.",
            f"A infusão de {volume} mL foi ajustada para {gotas} gotas por minuto.",
            f"Um paciente recebe {volume} mL de solução com gotejamento de "
            f"{gotas} gotas por minuto.",
            f"O equipo foi regulado em {gotas} gotas por minuto para infundir "
            f"{volume} mL.",
        ]
        PERGUNTAS = [
            "Em quantas horas a infusão será concluída?",
            "Qual é o tempo total de infusão, em horas?",
            "Determine o tempo de infusão em horas.",
            "O tempo necessário para infundir todo o volume é de:",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Isolando o tempo na fórmula do gotejamento: tempo (h) = volume ÷ "
            f"(gotas/min × 3) = {volume} ÷ ({gotas} × 3) = {volume} ÷ {gotas*3} "
            f"= {_fmt_dec(correta)} horas."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Cálculo de infusão", rng, formatador=lambda v: _fmt_dec(v))
        if q:
            return q
    raise RuntimeError("tempo_infusao")


def gerar_conversao_unidades(rng):
    """Conversão entre unidades de massa e volume — fatores fixos do SI."""
    for _ in range(60):
        modo = rng.choice(["g_mg", "mg_mcg", "l_ml", "mg_g"])

        if modo == "g_mg":
            v = rng.choice([0.25, 0.5, 1.5, 2.5, 0.125, 3.5])
            correta = v * 1000
            enun_base = f"Uma prescrição indica {_fmt_dec(v, 3).rstrip('0').rstrip(',')} g de um medicamento."
            pergunta = "Esse valor corresponde a quantos miligramas?"
            explicacao = (f"Como 1 g equivale a 1.000 mg, multiplica-se por 1.000: "
                          f"{_fmt_dec(v, 3).rstrip('0').rstrip(',')} × 1.000 = "
                          f"{_fmt_dec(correta, 1).rstrip('0').rstrip(',')} mg.")
            distratores = [v * 100, v * 10000, v / 1000, v * 500]
        elif modo == "mg_mcg":
            v = rng.choice([0.5, 0.25, 1.5, 2, 5, 0.75])
            correta = v * 1000
            enun_base = f"Um frasco contém {_fmt_dec(v, 2).rstrip('0').rstrip(',')} mg de princípio ativo."
            pergunta = "Quantos microgramas há nesse frasco?"
            explicacao = (f"Como 1 mg equivale a 1.000 mcg, multiplica-se por 1.000: "
                          f"{_fmt_dec(v, 2).rstrip('0').rstrip(',')} × 1.000 = "
                          f"{_fmt_dec(correta, 1).rstrip('0').rstrip(',')} mcg.")
            distratores = [v * 100, v * 10000, v / 1000, v * 60]
        elif modo == "l_ml":
            v = rng.choice([0.25, 0.5, 1.5, 2, 0.75, 3])
            correta = v * 1000
            enun_base = f"Foi prescrita a administração de {_fmt_dec(v, 2).rstrip('0').rstrip(',')} L de solução."
            pergunta = "Esse volume equivale a quantos mililitros?"
            explicacao = (f"Como 1 L equivale a 1.000 mL, multiplica-se por 1.000: "
                          f"{_fmt_dec(v, 2).rstrip('0').rstrip(',')} × 1.000 = "
                          f"{_fmt_dec(correta, 1).rstrip('0').rstrip(',')} mL.")
            distratores = [v * 100, v * 10000, v / 1000, v * 250]
        else:
            v = rng.choice([250, 500, 750, 1500, 2500])
            correta = v / 1000
            enun_base = f"Um comprimido contém {v} mg de determinada substância."
            pergunta = "Essa massa corresponde a quantos gramas?"
            explicacao = (f"Como 1.000 mg equivalem a 1 g, divide-se por 1.000: "
                          f"{v} ÷ 1.000 = {_fmt_dec(correta, 3).rstrip('0').rstrip(',')} g.")
            distratores = [v / 100, v / 10000, v * 1000, v / 500]

        ABERTURAS = [
            enun_base,
            enun_base.replace("Uma prescrição indica", "Consta na prescrição")
                     .replace("Um frasco contém", "A bula informa que o frasco contém")
                     .replace("Foi prescrita a administração de", "A prescrição solicita")
                     .replace("Um comprimido contém", "Cada comprimido apresenta"),
        ]
        enunciado = f"{rng.choice(ABERTURAS)} {pergunta}"

        fmt = lambda x: _fmt_dec(x, 3).rstrip("0").rstrip(",")
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Conversão de unidades", rng, formatador=fmt)
        if q:
            return q
    raise RuntimeError("conversao_unidades")


def gerar_diluicao(rng):
    """
    Volume a aspirar dada a concentração do frasco e a dose prescrita.
    A dose prescrita é DADO do enunciado — o template não afirma
    qual dose é adequada, apenas calcula o volume correspondente.
    """
    for _ in range(60):
        conc_mg = rng.choice([100, 250, 500, 1000])
        conc_ml = rng.choice([2, 5, 10])
        dose    = rng.choice([50, 100, 125, 200, 250, 400, 500])
        if dose > conc_mg:
            continue
        correta = round(dose * conc_ml / conc_mg, 2)
        if correta < 0.1 or correta > conc_ml:
            continue

        distratores = [
            # Erros que o profissional realmente comete na diluição:
            round(dose / conc_mg, 2),                  # esqueceu o volume
            round(correta * 2, 2),                     # dobrou por engano
            round(correta / 2, 2),                     # dividiu a mais
            round(dose * conc_ml / (conc_mg * 2), 2),  # errou a concentração
            round(dose / (conc_mg / conc_ml) * 2, 2),  # inverteu uma etapa
            round(correta * 10, 2),                    # casa decimal
        ]

        CENARIOS = [
            f"Um frasco-ampola contém {conc_mg} mg do fármaco diluídos em "
            f"{conc_ml} mL. A prescrição solicita {dose} mg.",
            f"Dispõe-se de uma ampola com {conc_mg} mg em {conc_ml} mL de "
            f"solução. Foi prescrita a dose de {dose} mg.",
            f"A apresentação disponível é de {conc_mg} mg por {conc_ml} mL. "
            f"A prescrição indica {dose} mg para administração.",
            f"Após a diluição, a solução ficou com {conc_mg} mg em {conc_ml} mL. "
            f"Deve-se administrar {dose} mg conforme prescrição.",
        ]
        PERGUNTAS = [
            "Qual volume, em mL, deve ser aspirado?",
            "O volume a ser administrado, em mL, é de:",
            "Determine o volume em mL a ser aspirado da ampola.",
            "Quantos mililitros correspondem à dose prescrita?",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Aplicando regra de três entre concentração e dose: se {conc_mg} mg "
            f"estão em {conc_ml} mL, então {dose} mg estão em "
            f"({dose} × {conc_ml}) ÷ {conc_mg} = {_fmt_dec(correta, 2)} mL."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Diluição e concentração", rng,
                    formatador=lambda v: _fmt_dec(v, 2))
        if q:
            return q
    raise RuntimeError("diluicao")


def gerar_dose_peso(rng):
    """
    Dose total a partir de mg/kg PRESCRITO e peso do paciente.
    A posologia vem do enunciado; o template não recomenda dose.
    """
    for _ in range(60):
        mg_kg = rng.choice([2, 5, 10, 15, 20, 25, 7.5, 12.5])
        peso  = rng.choice([8, 12, 18, 25, 30, 45, 60, 72, 85])
        fracionar = rng.random() < 0.4
        doses_dia = rng.choice([2, 3, 4]) if fracionar else 1

        total = mg_kg * peso
        correta = round(total / doses_dia, 1)

        distratores = [
            # Cada distrator reproduz um erro que o profissional cometeria:
            round(total, 1),                        # esqueceu de dividir pelas tomadas
            round(total * doses_dia, 1),            # multiplicou em vez de dividir
            round(total / (doses_dia + 1), 1),      # errou o número de tomadas
            round(total / max(1, doses_dia - 1), 1),# idem, para menos
            round(mg_kg * doses_dia, 1),            # ignorou o peso
            round(total / 2, 1),                    # dividiu por 2 por hábito
        ]

        mgkg_txt = _fmt_dec(mg_kg, 1).rstrip("0").rstrip(",")
        if fracionar:
            cen = (f"Foi prescrito um medicamento na posologia de {mgkg_txt} mg/kg "
                   f"por dia, dividida em {doses_dia} administrações iguais, para "
                   f"um paciente de {peso} kg.")
            per = rng.choice([
                "Qual é a dose de cada administração, em mg?",
                "A dose por administração, em mg, é de:",
                "Determine a quantidade em mg de cada dose.",
            ])
            explicacao = (
                f"A dose diária é {mgkg_txt} mg/kg × {peso} kg = "
                f"{_fmt_dec(total, 1).rstrip('0').rstrip(',')} mg. Dividindo em "
                f"{doses_dia} administrações: {_fmt_dec(total, 1).rstrip('0').rstrip(',')} ÷ "
                f"{doses_dia} = {_fmt_dec(correta, 1)} mg por dose."
            )
        else:
            cen = (f"A prescrição indica {mgkg_txt} mg/kg em dose única para um "
                   f"paciente com {peso} kg.")
            per = rng.choice([
                "Qual é a dose total a ser administrada, em mg?",
                "A dose total, em mg, corresponde a:",
                "Determine a dose total em mg.",
            ])
            explicacao = (
                f"Multiplicando a posologia prescrita pelo peso: {mgkg_txt} mg/kg × "
                f"{peso} kg = {_fmt_dec(correta, 1)} mg."
            )

        enunciado = f"{cen} {_juntar(cen, per)}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Cálculo de dose", rng, formatador=lambda v: _fmt_dec(v, 1))
        if q:
            return q
    raise RuntimeError("dose_peso")


# ══════════════════════════════════════════
#  EPIDEMIOLOGIA
# ══════════════════════════════════════════

def gerar_prevalencia_incidencia(rng):
    """Prevalência e incidência — definições formais, cálculo direto."""
    for _ in range(60):
        modo = rng.choice(["prevalencia", "incidencia"])
        pop  = rng.choice([2000, 5000, 8000, 10000, 20000, 50000])

        if modo == "prevalencia":
            casos = rng.randint(int(pop * 0.005), int(pop * 0.08))
            correta = round(casos / pop * 100000)
            CEN = [
                f"Em um município com {_fmt(pop)} habitantes, foram registrados "
                f"{_fmt(casos)} casos existentes de determinada doença crônica em "
                f"um mesmo momento.",
                f"Um inquérito de saúde identificou {_fmt(casos)} pessoas vivendo "
                f"com certa condição, em uma população de {_fmt(pop)} habitantes.",
                f"Levantamento realizado em uma cidade de {_fmt(pop)} habitantes "
                f"contabilizou {_fmt(casos)} casos existentes de um agravo.",
            ]
            PER = [
                "Qual é a prevalência da doença por 100.000 habitantes?",
                "A prevalência, expressa por 100.000 habitantes, é de:",
                "Determine a prevalência por 100.000 habitantes.",
            ]
            explicacao = (
                f"A prevalência considera os casos existentes dividido pela "
                f"população, multiplicado pela base: ({_fmt(casos)} ÷ {_fmt(pop)}) "
                f"× 100.000 = {_fmt(correta)} por 100.000 habitantes."
            )
            distratores = [round(casos / pop * 10000), round(casos / pop * 1000),
                           round(pop / casos), casos, round(casos / pop * 1000000)]
        else:
            expostos = rng.choice([500, 1000, 2500, 4000])
            novos = rng.randint(int(expostos * 0.01), int(expostos * 0.12))
            correta = round(novos / expostos * 1000, 1)
            CEN = [
                f"Uma coorte de {_fmt(expostos)} pessoas sadias foi acompanhada "
                f"por um ano, período em que surgiram {novos} casos novos da doença.",
                f"Durante 12 meses de seguimento de {_fmt(expostos)} indivíduos "
                f"inicialmente sem a doença, registraram-se {novos} casos novos.",
                f"Um estudo acompanhou {_fmt(expostos)} pessoas livres do agravo "
                f"e observou {novos} casos novos ao longo do período.",
            ]
            PER = [
                "Qual é a incidência acumulada por 1.000 pessoas no período?",
                "A incidência acumulada, por 1.000 pessoas, corresponde a:",
                "Determine a incidência acumulada por 1.000 pessoas.",
            ]
            explicacao = (
                f"A incidência acumulada usa os casos NOVOS sobre a população em "
                f"risco no início: ({novos} ÷ {_fmt(expostos)}) × 1.000 = "
                f"{_fmt_dec(correta)} por 1.000 pessoas."
            )
            distratores = [round(novos / expostos * 100, 1),
                           round(novos / expostos * 10000, 1),
                           round(expostos / novos, 1), float(novos),
                           round(novos / expostos * 100000, 1)]

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        fmt = (_fmt if modo == "prevalencia" else (lambda v: _fmt_dec(v)))
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (medidas de frequência)", rng, formatador=fmt)
        if q:
            return q
    raise RuntimeError("prevalencia_incidencia")


def gerar_sensibilidade_especificidade(rng):
    """Tabela 2x2: sensibilidade e especificidade — definições formais."""
    for _ in range(60):
        vp = rng.randint(40, 200)
        fn = rng.randint(5, 40)
        vn = rng.randint(200, 800)
        fp = rng.randint(10, 90)

        sens = round(vp / (vp + fn) * 100, 1)
        espec = round(vn / (vn + fp) * 100, 1)
        pede_sens = rng.random() < 0.5
        correta = sens if pede_sens else espec

        tabela = (
            f"                      Doente    Não doente\n"
            f"  Teste positivo      {vp:<9} {fp}\n"
            f"  Teste negativo      {fn:<9} {vn}"
        )
        CEN = [
            f"Um teste diagnóstico foi avaliado em relação a um padrão-ouro, "
            f"com os seguintes resultados:",
            f"A validação de um exame produziu a tabela de contingência abaixo, "
            f"comparando-o ao padrão-ouro:",
            f"Os resultados da aplicação de um teste em uma amostra, confrontados "
            f"com o diagnóstico de referência, foram:",
        ]
        if pede_sens:
            PER = ["Qual é a sensibilidade do teste?",
                   "A sensibilidade do exame corresponde a:",
                   "Determine a sensibilidade do teste."]
            explicacao = (
                f"A sensibilidade é a proporção de doentes corretamente "
                f"identificados: VP ÷ (VP + FN) = {vp} ÷ ({vp} + {fn}) = "
                f"{vp} ÷ {vp+fn}, o que equivale a {_fmt_pct(sens)}."
            )
            distratores = [espec, round(vp / (vp + fp) * 100, 1),
                           round(vn / (vn + fn) * 100, 1),
                           round(fn / (vp + fn) * 100, 1)]
        else:
            PER = ["Qual é a especificidade do teste?",
                   "A especificidade do exame corresponde a:",
                   "Determine a especificidade do teste."]
            explicacao = (
                f"A especificidade é a proporção de não doentes corretamente "
                f"identificados: VN ÷ (VN + FP) = {vn} ÷ ({vn} + {fp}) = "
                f"{vn} ÷ {vn+fp}, o que equivale a {_fmt_pct(espec)}."
            )
            distratores = [sens, round(vn / (vn + fn) * 100, 1),
                           round(vp / (vp + fp) * 100, 1),
                           round(fp / (vn + fp) * 100, 1)]

        enunciado = f"{rng.choice(CEN)}\n\n{tabela}\n\n{rng.choice(PER)}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (testes diagnósticos)", rng,
                    formatador=_fmt_pct, tipo_resposta="percentual")
        if q:
            return q
    raise RuntimeError("sensibilidade_especificidade")


def gerar_valor_preditivo(rng):
    """VPP e VPN a partir da tabela 2x2."""
    for _ in range(60):
        vp = rng.randint(50, 250)
        fp = rng.randint(15, 120)
        fn = rng.randint(5, 50)
        vn = rng.randint(250, 900)

        vpp = round(vp / (vp + fp) * 100, 1)
        vpn = round(vn / (vn + fn) * 100, 1)
        pede_vpp = rng.random() < 0.5
        correta = vpp if pede_vpp else vpn

        tabela = (
            f"                      Doente    Não doente\n"
            f"  Teste positivo      {vp:<9} {fp}\n"
            f"  Teste negativo      {fn:<9} {vn}"
        )
        CEN = [
            "Após a aplicação de um teste em uma população, obteve-se:",
            "Um rastreamento populacional gerou a seguinte distribuição de resultados:",
            "A tabela abaixo resume o desempenho de um teste aplicado a uma amostra:",
        ]
        if pede_vpp:
            PER = ["Qual é o valor preditivo positivo (VPP)?",
                   "O valor preditivo positivo corresponde a:",
                   "Determine o VPP do teste."]
            explicacao = (
                f"O valor preditivo positivo indica, entre os testes positivos, "
                f"quantos realmente têm a doença: VP ÷ (VP + FP) = {vp} ÷ "
                f"({vp} + {fp}) = {vp} ÷ {vp+fp}, o que equivale a {_fmt_pct(vpp)}."
            )
            distratores = [vpn, round(vp / (vp + fn) * 100, 1),
                           round(fp / (vp + fp) * 100, 1),
                           round(vn / (vn + fp) * 100, 1)]
        else:
            PER = ["Qual é o valor preditivo negativo (VPN)?",
                   "O valor preditivo negativo corresponde a:",
                   "Determine o VPN do teste."]
            explicacao = (
                f"O valor preditivo negativo indica, entre os testes negativos, "
                f"quantos realmente não têm a doença: VN ÷ (VN + FN) = {vn} ÷ "
                f"({vn} + {fn}) = {vn} ÷ {vn+fn}, o que equivale a {_fmt_pct(vpn)}."
            )
            distratores = [vpp, round(vn / (vn + fp) * 100, 1),
                           round(fn / (vn + fn) * 100, 1),
                           round(vp / (vp + fp) * 100, 1)]

        enunciado = f"{rng.choice(CEN)}\n\n{tabela}\n\n{rng.choice(PER)}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (valores preditivos)", rng,
                    formatador=_fmt_pct, tipo_resposta="percentual")
        if q:
            return q
    raise RuntimeError("valor_preditivo")


# ══════════════════════════════════════════
#  BIOESTATÍSTICA
# ══════════════════════════════════════════

def gerar_risco_relativo(rng):
    """Risco relativo e redução relativa de risco — fórmulas formais."""
    for _ in range(60):
        n_exp   = rng.choice([100, 200, 250, 400, 500])
        n_naoexp = rng.choice([100, 200, 250, 400, 500])
        casos_exp = rng.randint(int(n_exp * 0.10), int(n_exp * 0.45))
        casos_nao = rng.randint(int(n_naoexp * 0.03), int(n_naoexp * 0.20))

        risco_exp = casos_exp / n_exp
        risco_nao = casos_nao / n_naoexp
        if risco_nao == 0:
            continue
        rr = round(risco_exp / risco_nao, 2)
        if rr < 0.2 or rr > 8:
            continue

        pede_rr = rng.random() < 0.6
        if pede_rr:
            correta = rr
            PER = ["Qual é o risco relativo (RR) de adoecer entre os expostos?",
                   "O risco relativo corresponde a:",
                   "Determine o risco relativo."]
            explicacao = (
                f"O risco nos expostos é {casos_exp}/{n_exp} = "
                f"{_fmt_dec(risco_exp, 3)} e nos não expostos é "
                f"{casos_nao}/{n_naoexp} = {_fmt_dec(risco_nao, 3)}. O risco "
                f"relativo é a razão entre eles: {_fmt_dec(risco_exp, 3)} ÷ "
                f"{_fmt_dec(risco_nao, 3)} = {_fmt_dec(rr, 2)}."
            )
            # Distratores devem ser ERROS PLAUSÍVEIS, não valores impossíveis.
            # Risco relativo é uma razão entre dois riscos: nunca é negativo.
            # A subtração de riscos (que pode dar negativo) foi trocada pelo
            # seu valor absoluto, que é o risco atribuível — erro real de quem
            # confunde as duas medidas.
            candidatos = [
                round(risco_nao / risco_exp, 2),        # inverteu a razão
                round(rr + 0.5, 2),
                round(abs(rr - 0.3), 2),
                round(abs(risco_exp - risco_nao), 2),   # calculou a diferença
                round(rr * 2, 2),
                round(risco_exp * 100 / (risco_nao * 100), 2),
            ]
            distratores = [d for d in candidatos if d > 0]
            fmt = lambda v: _fmt_dec(v, 2)
            tipo = "numerica"
        else:
            rar = round(abs(risco_exp - risco_nao) * 100, 1)
            correta = rar
            PER = ["Qual é o risco atribuível (diferença de riscos), em pontos percentuais?",
                   "A diferença absoluta de riscos, em pontos percentuais, é de:",
                   "Determine o risco atribuível em pontos percentuais."]
            explicacao = (
                f"O risco nos expostos é {_fmt_pct(risco_exp*100)} e nos não "
                f"expostos, {_fmt_pct(risco_nao*100)}. A diferença absoluta "
                f"entre eles é {_fmt_pct(rar)}."
            )
            candidatos = [round(risco_exp * 100, 1), round(risco_nao * 100, 1),
                          round(rar * 2, 1), round(rr * 10, 1),
                          round(rar + 5, 1), round(abs(rar - 3), 1)]
            distratores = [d for d in candidatos if d > 0]
            fmt = _fmt_pct
            tipo = "percentual"

        tabela = (
            f"                     Adoeceram   Total\n"
            f"  Expostos           {casos_exp:<11} {n_exp}\n"
            f"  Não expostos       {casos_nao:<11} {n_naoexp}"
        )
        CEN = [
            "Um estudo de coorte acompanhou dois grupos e obteve os seguintes dados:",
            "A tabela a seguir resume os resultados de um estudo prospectivo:",
            "Pesquisadores compararam expostos e não expostos a um fator, obtendo:",
        ]
        enunciado = f"{rng.choice(CEN)}\n\n{tabela}\n\n{rng.choice(PER)}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Bioestatística (medidas de associação)", rng,
                    formatador=fmt, tipo_resposta=tipo)
        if q:
            return q
    raise RuntimeError("risco_relativo")


def gerar_odds_ratio(rng):
    """Odds ratio de estudo caso-controle — fórmula formal (ad/bc)."""
    for _ in range(60):
        a = rng.randint(30, 150)   # casos expostos
        b = rng.randint(20, 120)   # controles expostos
        c = rng.randint(15, 100)   # casos não expostos
        d = rng.randint(40, 200)   # controles não expostos

        if b * c == 0:
            continue
        odds = round((a * d) / (b * c), 2)
        if odds < 0.2 or odds > 10:
            continue

        tabela = (
            f"                     Casos     Controles\n"
            f"  Expostos           {a:<9} {b}\n"
            f"  Não expostos       {c:<9} {d}"
        )
        CEN = [
            "Um estudo caso-controle investigou a associação entre um fator e "
            "determinado desfecho:",
            "A tabela abaixo apresenta os dados de um estudo caso-controle:",
            "Pesquisadores compararam casos e controles quanto à exposição a um "
            "fator, obtendo:",
        ]
        PER = [
            "Qual é a razão de chances (odds ratio) dessa associação?",
            "A razão de chances corresponde a:",
            "Determine o odds ratio.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen}\n\n{tabela}\n\n{rng.choice(PER)}"
        explicacao = (
            f"A razão de chances é obtida por (a × d) ÷ (b × c), em que a e d são "
            f"a diagonal principal: ({a} × {d}) ÷ ({b} × {c}) = {a*d} ÷ {b*c} = "
            f"{_fmt_dec(odds, 2)}."
        )
        distratores = [round((b * c) / (a * d), 2), round((a * c) / (b * d), 2),
                       round(odds + 0.7, 2), round(odds / 2, 2),
                       round((a * b) / (c * d), 2)]

        q = _montar(enunciado, odds, distratores, explicacao,
                    "Bioestatística (odds ratio)", rng,
                    formatador=lambda v: _fmt_dec(v, 2))
        if q:
            return q
    raise RuntimeError("odds_ratio")


def gerar_nnt(rng):
    """NNT = 1 / redução absoluta de risco — definição formal."""
    for _ in range(60):
        n_trat = rng.choice([200, 250, 400, 500])
        n_ctrl = rng.choice([200, 250, 400, 500])
        ev_trat = rng.randint(int(n_trat * 0.03), int(n_trat * 0.18))
        ev_ctrl = rng.randint(int(n_ctrl * 0.12), int(n_ctrl * 0.35))

        r_trat = ev_trat / n_trat
        r_ctrl = ev_ctrl / n_ctrl
        rar = r_ctrl - r_trat
        if rar <= 0.01:
            continue
        correta = ceil(1 / rar)

        tabela = (
            f"                     Eventos   Total\n"
            f"  Grupo tratamento   {ev_trat:<9} {n_trat}\n"
            f"  Grupo controle     {ev_ctrl:<9} {n_ctrl}"
        )
        CEN = [
            "Um ensaio clínico randomizado comparou tratamento e controle:",
            "Os resultados de um ensaio clínico estão resumidos abaixo:",
            "A tabela a seguir apresenta os desfechos observados em um ensaio "
            "clínico controlado:",
        ]
        PER = [
            "Qual é o número necessário para tratar (NNT), arredondado para cima?",
            "O NNT, arredondado para o inteiro superior, é de:",
            "Determine o número necessário para tratar.",
        ]
        enunciado = f"{rng.choice(CEN)}\n\n{tabela}\n\n{rng.choice(PER)}"
        explicacao = (
            f"O risco no controle é {_fmt_pct(r_ctrl*100)} e no tratamento, "
            f"{_fmt_pct(r_trat*100)}. A redução absoluta de risco é "
            f"{_fmt_pct(rar*100)}. O NNT é o inverso dessa redução: 1 ÷ "
            f"{_fmt_dec(rar, 4)}, que arredondado para cima resulta em {correta}."
        )
        distratores = [correta + 1, correta - 1, ceil(1 / r_ctrl),
                       ceil(1 / r_trat) if r_trat > 0 else correta + 5,
                       correta * 2]

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Bioestatística (NNT)", rng)
        if q:
            return q
    raise RuntimeError("nnt")


# ══════════════════════════════════════════
#  RACIOCÍNIO CLÍNICO E EPIDEMIOLÓGICO
#
#  Os templates acima medem a CONTA. Estes medem a INTERPRETAÇÃO:
#  o que o resultado significa, qual medida se aplica, que erro o
#  desenho do estudo introduz. A resposta continua determinística —
#  decorre da definição formal —, mas exige entender o conceito.
# ══════════════════════════════════════════

def gerar_interpretacao_medida(rng):
    """
    O que o valor calculado SIGNIFICA.

    Um RR de 2,5 não é "risco de 2,5%": é 150% de aumento relativo.
    Confundir a leitura é erro comum e clinicamente relevante.
    """
    for _ in range(60):
        medida = rng.choice(["rr", "or", "nnt", "sens", "vpp"])

        if medida == "rr":
            valor = rng.choice([0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0])
            if valor > 1:
                pct = round((valor - 1) * 100)
                correta = (f"os expostos têm risco {pct}% maior de apresentar "
                           f"o desfecho do que os não expostos")
            elif valor < 1:
                pct = round((1 - valor) * 100)
                correta = (f"a exposição associa-se a redução de {pct}% no "
                           f"risco do desfecho")
            else:
                correta = ("não há associação entre a exposição e o desfecho")

            distratores = [
                f"o risco absoluto entre os expostos é de {valor}%",
                f"{round(valor * 100)}% dos expostos apresentarão o desfecho",
                "a exposição causa o desfecho em todos os casos analisados",
                "o resultado indica ausência de significância estatística",
            ]
            contexto = (f"Um estudo de coorte encontrou risco relativo (RR) "
                        f"igual a {_fmt_dec(valor, 1)}.")
            fundamento = (
                f"O risco relativo é uma razão, não um percentual absoluto. "
                f"Um RR de {_fmt_dec(valor, 1)} significa que o risco nos "
                f"expostos é {_fmt_dec(valor, 1)} vez(es) o risco nos não "
                f"expostos"
                + (f", ou seja, {round((valor-1)*100)}% maior." if valor > 1
                   else (f", ou seja, {round((1-valor)*100)}% menor." if valor < 1
                         else " — valores iguais indicam ausência de associação."))
            )

        elif medida == "or":
            valor = rng.choice([0.5, 1.0, 2.0, 3.0, 4.0])
            if valor > 1:
                correta = ("a chance de exposição entre os casos é maior do "
                           "que entre os controles")
            elif valor < 1:
                correta = ("a chance de exposição entre os casos é menor do "
                           "que entre os controles, sugerindo fator protetor")
            else:
                correta = "as chances de exposição são iguais nos dois grupos"

            distratores = [
                "a chance de exposição entre os casos é menor do que entre os "
                "controles, sugerindo fator protetor" if valor >= 1 else
                "a chance de exposição entre os casos é maior do que entre os "
                "controles",
                f"{round(valor * 100)}% dos casos foram expostos ao fator",
                "o estudo demonstra relação causal entre exposição e doença",
                "a prevalência da doença é de " + _fmt_dec(valor, 1) + "%",
            ]
            contexto = (f"Um estudo caso-controle obteve razão de chances (OR) "
                        f"de {_fmt_dec(valor, 1)}.")
            fundamento = (
                f"A razão de chances compara a CHANCE de exposição entre casos "
                f"e controles. OR de {_fmt_dec(valor, 1)} indica que essa "
                f"chance é {'maior' if valor > 1 else ('menor' if valor < 1 else 'igual')}"
                f" entre os casos. Estudo caso-controle não permite estimar "
                f"prevalência nem estabelecer causalidade isoladamente."
            )

        elif medida == "nnt":
            valor = rng.randint(4, 50)
            correta = (f"é preciso tratar {valor} pacientes para evitar um "
                       f"desfecho adverso")
            distratores = [
                f"{valor}% dos pacientes tratados terão benefício",
                f"o tratamento falha em {valor} de cada 100 pacientes",
                f"{valor} pacientes apresentaram o desfecho no grupo tratado",
                f"o tratamento reduz o risco em {valor}%",
            ]
            contexto = (f"Um ensaio clínico randomizado resultou em NNT "
                        f"(número necessário para tratar) igual a {valor}.")
            fundamento = (
                f"O NNT indica quantos pacientes precisam receber a "
                f"intervenção para que UM desfecho adverso seja evitado. NNT "
                f"de {valor} significa tratar {valor} pessoas para prevenir um "
                f"evento. Quanto MENOR o NNT, maior o benefício da intervenção."
            )

        elif medida == "sens":
            valor = rng.choice([70, 80, 90, 95, 99])
            correta = (f"o teste identifica corretamente {valor}% das pessoas "
                       f"que realmente têm a doença")
            distratores = [
                f"{valor}% dos testes positivos correspondem a doentes reais",
                f"o teste erra em {valor}% dos casos analisados",
                f"{valor}% das pessoas testadas estão doentes",
                f"o teste tem {valor}% de chance de estar disponível na rede",
            ]
            contexto = f"Um teste diagnóstico apresenta sensibilidade de {valor}%."
            fundamento = (
                f"A sensibilidade é a capacidade de detectar quem TEM a "
                f"doença: entre os doentes, {valor}% terão resultado positivo. "
                f"A proporção de doentes entre os positivos é o valor preditivo "
                f"positivo, medida distinta que depende da prevalência."
            )

        else:  # vpp
            valor = rng.choice([30, 50, 70, 85, 95])
            correta = (f"entre as pessoas com resultado positivo, {valor}% "
                       f"realmente têm a doença")
            distratores = [
                f"entre os doentes, {valor}% terão resultado positivo",
                f"o teste acerta {valor}% de todos os diagnósticos",
                f"{valor}% da população testada está doente",
                f"a especificidade do teste é de {valor}%",
            ]
            contexto = (f"Em determinada população, um teste apresenta valor "
                        f"preditivo positivo (VPP) de {valor}%.")
            fundamento = (
                f"O VPP responde à pergunta do paciente: 'meu teste deu "
                f"positivo, qual a chance de eu estar doente?'. Com VPP de "
                f"{valor}%, essa é a proporção de doentes entre os positivos. "
                f"Diferentemente da sensibilidade, o VPP VARIA com a "
                f"prevalência da doença na população."
            )

        PER = [
            "A interpretação correta desse resultado é que:",
            "Esse valor significa que:",
            "Assinale a interpretação correta.",
        ]
        enunciado = f"{contexto} {rng.choice(PER)}"
        q = _montar(enunciado, correta, distratores, fundamento,
                    "Epidemiologia (interpretação)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("interpretacao_medida")


def gerar_medida_adequada(rng):
    """
    Qual medida epidemiológica se aplica a cada desenho de estudo.

    Erro clássico: calcular risco relativo em caso-controle, onde a
    incidência não é observável.
    """
    DESENHOS = [
        ("um estudo de coorte prospectivo",
         "risco relativo",
         "a coorte acompanha os grupos ao longo do tempo, permitindo observar "
         "a incidência e, portanto, calcular riscos"),
        ("um estudo caso-controle",
         "razão de chances (odds ratio)",
         "no caso-controle os grupos são definidos pelo desfecho, de modo que "
         "a incidência não é observável — só a razão de chances é estimável"),
        ("um estudo transversal (de prevalência)",
         "razão de prevalências",
         "o estudo transversal mede exposição e desfecho no mesmo momento, "
         "captando prevalência e não incidência"),
    ]

    # O ENSAIO CLÍNICO RANDOMIZADO saiu deste template.
    #
    # Ele estava com "redução absoluta de risco e NNT" como resposta, e
    # "risco relativo" entre os distratores — mas o ensaio é uma coorte
    # experimental, e o risco relativo é calculado nele rotineiramente.
    # A alternativa dita errada não era errada.
    #
    # Os três desenhos observacionais que ficam têm medidas que não se
    # confundem: coorte mede incidência e dá RR; caso-controle parte do
    # desfecho e só permite OR; transversal capta prevalência. O ensaio
    # continua nos templates de NNT e de redução absoluta de risco, onde
    # é o desenho próprio da pergunta.
    for _ in range(50):
        desenho, correta, motivo = rng.choice(DESENHOS)
        # Com três desenhos, sobram só dois distratores da tabela —
        # menos do que as quatro alternativas exigem. Os demais são
        # medidas reais da epidemiologia que não correspondem a nenhum
        # destes desenhos.
        distratores = [c for _, c, _ in DESENHOS if c != correta]
        distratores += [
            "coeficiente de mortalidade proporcional",
            "número necessário para tratar (NNT)",
            "razão de verossimilhança positiva",
            "risco atribuível populacional",
        ]

        CEN = [
            f"Pesquisadores conduziram {desenho} para investigar a associação "
            f"entre uma exposição e determinado desfecho.",
            f"Um grupo de pesquisa delineou {desenho} sobre a relação entre "
            f"fator e doença.",
            f"O protocolo aprovado descreve {desenho}.",
        ]
        PER = [
            "Qual medida de associação é adequada a esse desenho?",
            "A medida que deve ser calculada é:",
            "Assinale a medida de associação apropriada.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Em {desenho}, a medida adequada é {correta}, porque {motivo}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (desenhos de estudo)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("medida_adequada")


def gerar_vies_estudo(rng):
    """
    Identificação de viés a partir da descrição do estudo.

    Cada situação corresponde a um viés específico e reconhecível.
    """
    VIESES = [
        ("os pesquisadores perguntaram às mães de crianças com malformação "
         "sobre exposições durante a gestação, e elas se recordaram com muito "
         "mais detalhe do que as mães do grupo controle",
         "viés de memória (recall bias)",
         "a diferença sistemática na recordação entre casos e controles "
         "distorce a medida de exposição"),
        ("30% dos participantes abandonaram o acompanhamento, e a perda foi "
         "maior no grupo exposto",
         "viés de perda de seguimento (attrition bias)",
         "as perdas desiguais entre os grupos comprometem a comparabilidade"),
        ("os voluntários que aceitaram participar tinham escolaridade e renda "
         "muito superiores às da população-alvo",
         "viés de seleção",
         "a amostra deixa de representar a população que se pretendia estudar"),
        ("o avaliador do desfecho sabia qual paciente recebeu a intervenção "
         "e qual recebeu placebo",
         "viés de aferição (detecção)",
         "o conhecimento da alocação pode influenciar a classificação do "
         "desfecho — daí a importância do cegamento"),
        ("havia associação entre consumo de café e câncer de pulmão, mas "
         "os consumidores de café fumavam muito mais",
         "confundimento",
         "o tabagismo se associa tanto à exposição quanto ao desfecho, "
         "distorcendo a associação observada"),
    ]
    for _ in range(50):
        situacao, correta, motivo = rng.choice(VIESES)
        distratores = [c for _, c, _ in VIESES if c != correta]
        distratores.append("erro aleatório de amostragem")

        # Os cenários usam verbos de constatação; as situações são redigidas
        # como ORAÇÕES SUBORDINADAS ("havia X", "30% abandonaram"), sem verbo
        # de constatação próprio — senão sai "verificou-se que observou-se".
        CEN = [
            f"Ao revisar a metodologia de um estudo, notou-se que {situacao}.",
            f"Um parecerista observou que, no estudo submetido, {situacao}.",
            f"Durante a análise crítica de um artigo, constatou-se que "
            f"{situacao}.",
            f"A leitura do relatório de pesquisa revelou que {situacao}.",
        ]
        PER = [
            "Qual problema metodológico está caracterizado?",
            "Trata-se de:",
            "Assinale o viés identificado.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"A situação descrita caracteriza {correta}, pois {motivo}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (validade)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("vies_estudo")


def gerar_escolha_teste(rng):
    """
    Rastreamento vs. confirmação: sensibilidade ou especificidade?

    Regra clínica: rastrear pede alta sensibilidade (não perder doente);
    confirmar pede alta especificidade (não rotular sadio como doente).
    """
    SITUACOES = [
        ("rastrear uma doença grave e tratável em população assintomática",
         "alta sensibilidade",
         "no rastreamento o custo de deixar de identificar um doente é alto; "
         "os falsos positivos são depois esclarecidos por teste confirmatório"),
        ("confirmar o diagnóstico antes de iniciar tratamento com efeitos "
         "adversos importantes",
         "alta especificidade",
         "aqui o custo de tratar quem não tem a doença é elevado, exigindo "
         "poucos falsos positivos"),
        ("excluir uma condição de urgência em pronto-socorro",
         "alta sensibilidade",
         "para descartar com segurança, o teste precisa raramente deixar "
         "passar um caso verdadeiro"),
        ("selecionar doadores em banco de sangue",
         "alta sensibilidade",
         "deixar passar uma bolsa contaminada tem consequências graves, o que "
         "justifica priorizar a detecção"),
    ]
    for _ in range(50):
        situacao, correta, motivo = rng.choice(SITUACOES)
        distratores = [
            "alta especificidade" if correta == "alta sensibilidade"
            else "alta sensibilidade",
            "alto valor preditivo negativo, independentemente da prevalência",
            "baixo custo por exame, como critério principal",
            "elevada razão de verossimilhança negativa",
        ]

        CEN = [
            f"Um serviço de saúde precisa escolher um teste para {situacao}.",
            f"O gestor avalia qual exame adotar para {situacao}.",
            f"Ao definir o protocolo para {situacao}, discute-se a escolha do "
            f"teste.",
        ]
        PER = [
            "Qual característica deve ser priorizada?",
            "A propriedade mais importante do teste é:",
            "Deve-se privilegiar um teste com:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Para {situacao}, prioriza-se {correta}, porque {motivo}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Epidemiologia (testes diagnósticos)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("escolha_teste")


def gerar_via_administracao(rng):
    """
    Escolha da via de administração conforme a situação clínica.

    Conteúdo de farmacologia básica, com resposta objetiva.
    """
    SITUACOES = [
        ("é necessário efeito imediato em situação de emergência",
         "endovenosa",
         "a via endovenosa dispensa a fase de absorção, resultando em "
         "biodisponibilidade de 100% e início de ação imediato"),
        ("o paciente está consciente, estável e o fármaco tem boa absorção "
         "digestiva",
         "oral",
         "é a via mais segura, econômica e cômoda quando não há urgência nem "
         "prejuízo à absorção"),
        ("o paciente apresenta vômitos incoercíveis e precisa de medicação "
         "sistêmica",
         "endovenosa",
         "a via oral fica inviabilizada pela êmese, e a absorção não pode ser "
         "garantida"),
        ("deseja-se liberação lenta e prolongada a partir de um depósito",
         "intramuscular",
         "a musculatura é bem vascularizada e permite formulações de depósito "
         "com liberação gradual"),
        # A situação dizia apenas "sofre intenso metabolismo de primeira
        # passagem". A via ENDOVENOSA — que está entre os distratores —
        # também escapa por completo do fígado, e a retal, em parte:
        # três alternativas defensáveis. O acréscimo "sem acesso venoso"
        # deixa uma só.
        ("o fármaco sofre intenso metabolismo de primeira passagem "
         "hepática e não há acesso venoso disponível",
         "sublingual",
         "a absorção pela mucosa sublingual cai diretamente na circulação "
         "sistêmica, evitando a passagem inicial pelo fígado — e, sem "
         "acesso venoso, é a via que resta para contorná-la"),
    ]
    for _ in range(50):
        situacao, correta, motivo = rng.choice(SITUACOES)
        distratores = list({c for _, c, _ in SITUACOES if c != correta})
        distratores += ["retal", "inalatória", "transdérmica"]
        rng.shuffle(distratores)

        CEN = [
            f"Em determinado atendimento, {situacao}.",
            f"A equipe avalia a prescrição considerando que {situacao}.",
            f"Diante de um quadro em que {situacao},",
        ]
        PER = [
            "Qual via de administração é a mais adequada?",
            "a via de escolha é:",
            "Assinale a via de administração indicada.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        explicacao = (
            f"Quando {situacao}, a via de escolha é a {correta}, porque "
            f"{motivo}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Farmacologia (vias de administração)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("via_administracao")


# ──────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────

TEMPLATES_SAUDE = {
    "gotejamento":              gerar_gotejamento,
    "tempo_infusao":            gerar_tempo_infusao,
    "conversao_unidades":       gerar_conversao_unidades,
    "diluicao":                 gerar_diluicao,
    "dose_peso":                gerar_dose_peso,
    "prevalencia_incidencia":   gerar_prevalencia_incidencia,
    "sensibilidade":            gerar_sensibilidade_especificidade,
    "valor_preditivo":          gerar_valor_preditivo,
    "risco_relativo":           gerar_risco_relativo,
    "odds_ratio":               gerar_odds_ratio,
    "nnt":                      gerar_nnt,
    # ── Raciocínio clínico e epidemiológico ──
    "interpretacao_medida":     gerar_interpretacao_medida,
    "medida_adequada":          gerar_medida_adequada,
    "vies_estudo":              gerar_vies_estudo,
    "escolha_teste":            gerar_escolha_teste,
    "via_administracao":        gerar_via_administracao,
}

TOPICOS_SAUDE = {
    "calculo_clinico":  ["gotejamento", "tempo_infusao", "conversao_unidades",
                         "diluicao", "dose_peso"],
    "epidemiologia":    ["prevalencia_incidencia", "sensibilidade", "valor_preditivo",
                         "medida_adequada", "vies_estudo", "escolha_teste"],
    "bioestatistica":   ["risco_relativo", "odds_ratio", "nnt",
                         "interpretacao_medida"],
    "farmacologia":     ["via_administracao", "dose_peso", "conversao_unidades"],
}

PALAVRAS_CHAVE = {
    "gotejamento":            ["gotejamento", "infusao", "soro", "equipo",
                               "administracao de medicamento", "calculo de medicacao",
                               "enfermagem"],
    "tempo_infusao":          ["infusao", "gotejamento", "equipo", "tempo de infusao"],
    "conversao_unidades":     ["unidade", "conversao", "sistema internacional",
                               "grama", "miligrama", "farmacologia", "posologia"],
    "diluicao":               ["diluicao", "concentracao", "solucao", "ampola",
                               "regra de tres", "farmacologia", "preparo de medicamento"],
    "dose_peso":              ["dose", "posologia", "peso corporal", "mg/kg",
                               "farmacologia", "calculo de dose", "pediatria"],
    "prevalencia_incidencia": ["prevalencia", "incidencia", "epidemiologia",
                               "medidas de frequencia", "saude coletiva",
                               "vigilancia", "morbidade"],
    "sensibilidade":          ["sensibilidade", "especificidade", "teste diagnostico",
                               "rastreamento", "epidemiologia", "acuracia",
                               "padrao-ouro"],
    "valor_preditivo":        ["valor preditivo", "vpp", "vpn", "teste diagnostico",
                               "rastreamento", "epidemiologia"],
    "risco_relativo":         ["risco relativo", "coorte", "medidas de associacao",
                               "epidemiologia", "bioestatistica", "risco atribuivel"],
    "odds_ratio":             ["odds ratio", "razao de chances", "caso-controle",
                               "medidas de associacao", "bioestatistica"],
    "nnt":                    ["nnt", "numero necessario para tratar", "ensaio clinico",
                               "medicina baseada em evidencias", "bioestatistica",
                               "reducao de risco"],
    "interpretacao_medida":   ["interpretacao", "risco relativo", "odds ratio",
                               "medidas de associacao", "epidemiologia",
                               "medicina baseada em evidencias"],
    "medida_adequada":        ["desenho de estudo", "coorte", "caso-controle",
                               "transversal", "ensaio clinico", "epidemiologia",
                               "metodologia"],
    "vies_estudo":            ["vies", "confundimento", "validade", "metodologia",
                               "epidemiologia", "erro sistematico"],
    "escolha_teste":          ["rastreamento", "triagem", "teste diagnostico",
                               "sensibilidade", "especificidade", "epidemiologia"],
    "via_administracao":      ["via de administracao", "farmacologia", "endovenosa",
                               "oral", "biodisponibilidade", "primeira passagem"],
}


# Termos que também ocorrem em estatística e administração.
CHAVES_GENERICAS = {
    "dose", "unidade", "conversao", "solucao", "concentracao",
    "prevalencia", "incidencia", "sensibilidade", "especificidade",
    "risco relativo", "metodologia", "validade", "vies", "amostra",
    "peso corporal", "via de administracao", "desenho de estudo",
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

def gerar_lote(quantidade=11, topico=None, templates=None, seed=None):
    rng = random.Random(seed)
    if templates:
        nomes = [n for n in templates if n in TEMPLATES_SAUDE]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
    elif topico:
        nomes = TOPICOS_SAUDE.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS_SAUDE)}")
    else:
        nomes = list(TEMPLATES_SAUDE)

    funcoes = [TEMPLATES_SAUDE[n] for n in nomes]
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

    IMPORTANTE: monta o payload campo a campo, de propósito. Os metadados
    internos (tipo_resposta, resposta_bruta) NÃO são incluídos — servem
    apenas aos testes automatizados.
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
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    topico = sys.argv[2] if len(sys.argv) > 2 else None
    for q in gerar_lote(qtd, topico):
        print("─" * 66)
        print(f"Q{q['numero']} [{q['topico']}]\n")
        print(q["enunciado"], "\n")
        for L, t in q["alternativas"].items():
            print(f"   {L}) {t}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("─" * 66)
    print(f"\n{qtd} questões | Custo: R$ 0,00 | Gabaritos calculados.\n")
