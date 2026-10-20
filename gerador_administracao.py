"""
=============================================================
  NIVELIS — Gerador Procedural: Administração
  Foco: ENADE Administração, concursos e provas de graduação
=============================================================

  Gera questões SEM IA. O Python calcula o resultado ou consulta
  uma tabela de fatos conferidos em fonte.

  POR QUE COMEÇA PELO LADO CALCULÁVEL
  -----------------------------------
  Uma disciplina puramente conceitual nasce rasa: cada fato é uma
  linha de tabela que alguém precisa pesquisar, e o gerador de
  engenharia de software, feito assim, comporta doze questões
  distintas — menos do que um caderno de trinta.

  Custos, finanças e contabilidade não têm esse teto: o enunciado
  sorteia parâmetros e a resposta é calculada, como em juros
  compostos. Dez dos quinze templates daqui são desse tipo, e é
  deles que vem o lastro. Os cinco conceituais entram como
  complemento, não como base.

  ESCOPO DELIBERADO
  -----------------
  Cobre o que tem RESPOSTA OBJETIVA — fórmula ou definição
  consolidada. Não cobre estudo de caso, diagnóstico
  organizacional nem escolha de estratégia para um cenário, que
  dependem de ponderação e não de gabarito único.

  DIVERGÊNCIAS QUE MOTIVARAM EXCLUSÕES
  ------------------------------------
  Registradas em administracao/_fontes.md. A principal: o ROI
  aparece na literatura brasileira com dois denominadores
  incompatíveis — o investimento (análise de balanço) e o custo
  (marketing e projetos). Ficou de fora; usam-se ROA e ROE, que
  não divergem.

  15 TEMPLATES
    calculáveis  margem de contribuição, ponto de equilíbrio,
                 markup, liquidez, rentabilidade, payback, VPL,
                 depreciação, giro de estoque, custeio
    conceituais  escolas da administração, funções administrativas,
                 estruturas organizacionais, estratégia, motivação

  USO:
      from gerador_administracao import gerar_lote, gerar_para_api
=============================================================
"""

import math
import random
import re
import sys
import unicodedata

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "percentual", "monetaria", "textual", "sequencia",
}


# ══════════════════════════════════════════════════════════
#  FORMATAÇÃO
# ══════════════════════════════════════════════════════════

def _moeda(v) -> str:
    """R$ 1.234,56 — sempre com duas casas, para as alternativas
    terem todas o mesmo formato."""
    inteiro, dec = f"{abs(float(v)):.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    sinal = "-" if float(v) < 0 else ""
    return f"R$ {sinal}{inteiro},{dec}"


def _pct(v) -> str:
    return f"{float(v):.2f}".replace(".", ",") + "%"


def _num(v) -> str:
    """Número com duas casas quando não é inteiro."""
    if abs(float(v) - round(float(v))) < 1e-9:
        return f"{int(round(float(v))):,}".replace(",", ".")
    return f"{float(v):.2f}".replace(".", ",")


def _indice(v) -> str:
    """Índice de balanço — SEMPRE com duas casas.

    Não usa _num porque um índice exato viraria "2" no meio de
    "1,50" e "0,38": a alternativa de formato diferente se denuncia
    sozinha, mesmo para quem não sabe a matéria.
    """
    return f"{float(v):.2f}".replace(".", ",")


def _contrair_de(texto: str) -> str:
    """de + o/a/os/as → do/da/dos/das.

    As ênfases das escolas já vêm com artigo ("as pessoas e os
    grupos informais"), então "em torno de {enfase}" sairia
    "em torno de as pessoas".
    """
    for artigo, contracao in (("as ", "das "), ("os ", "dos "),
                              ("a ", "da "), ("o ", "do ")):
        if texto.startswith(artigo):
            return contracao + texto[len(artigo):]
    return "de " + texto


def _unid(v) -> str:
    return f"{_num(v)} unidades"


def _vezes(v) -> str:
    return f"{_num(v)} vezes"


def _anos(v) -> str:
    n = float(v)
    return f"{_num(n)} " + ("ano" if abs(n - 1) < 1e-9 else "anos")


def _dias(v) -> str:
    n = float(v)
    return f"{_num(n)} " + ("dia" if abs(n - 1) < 1e-9 else "dias")


def _normalizar(txt: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(txt) or "")
    sem = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem.lower().strip()


def _juntar(anterior: str, seguinte: str) -> str:
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=_num, tipo_resposta="numerica", fato=None):
    """
    Junta gabarito e quatro distratores, embaralha e devolve a questão.

    Os distratores passam por dois filtros que hoje são padrão do
    projeto, por terem custado caro em outras disciplinas:

      • valor repetido — duas alternativas com o mesmo texto depois de
        formatadas anulam a questão;
      • continência — alternativa que contém outra ("presente" dentro
        de "presente, mas sem lipopolissacarídeo") deixa duas
        marcáveis.
    """
    assert tipo_resposta in TIPOS_RESPOSTA

    txt_correta = formatador(correta)

    def _contido(a, b):
        na, nb = _normalizar(a), _normalizar(b)
        if na == nb or len(na) < 5:
            return False
        return re.search(r"(^|\s)" + re.escape(na) + r"($|\s|,)", nb) is not None

    # O PRIMEIRO distrator de cada template é o erro clássico da
    # matéria e entra sempre; os demais são sorteados. Antes valia
    # `unicos[:4]`, que pegava os quatro primeiros da lista — o quinto
    # e o sexto quase nunca apareciam, e o template ficava preso a um
    # conjunto fixo de alternativas. Foi assim que o markup passou a
    # ter a resposta certa como maior valor em 84% das questões: os
    # distratores que passavam do preço correto estavam no fim da fila.
    candidatos = list(distratores)
    obrigatorio = candidatos[:1]
    resto = candidatos[1:]
    rng.shuffle(resto)

    unicos, textos = [], [txt_correta]
    for d in obrigatorio + resto:
        t = formatador(d)
        if t in textos:
            continue
        if any(_contido(t, o) or _contido(o, t) for o in textos):
            continue
        unicos.append(d)
        textos.append(t)

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
        "origem":         "gerador_administracao",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
        "_fato":          fato or f"{topico}:{txt_correta}",
    }


def _cap(txt: str) -> str:
    """Maiúscula só na primeira letra.

    str.capitalize() rebaixa o resto da string: "margem líquida (ROE)"
    virava "(roe)", e "de Fayol" virava "de fayol".
    """
    txt = str(txt)
    return txt[:1].upper() + txt[1:] if txt else txt


# Empresas que FABRICAM. Os templates que falam em "produziu N
# unidades" e em custo fixo de produção sorteiam só daqui — uma
# transportadora que produziu 500 unidades não é cenário de prova.
INDUSTRIAS = [
    "uma indústria de embalagens", "uma fábrica de móveis",
    "uma confecção", "uma gráfica", "uma metalúrgica",
    "uma fábrica de componentes eletrônicos",
    "uma indústria de alimentos",
]

COMERCIO_E_SERVICOS = [
    "uma rede de farmácias", "uma distribuidora de alimentos",
    "uma empresa de software", "uma transportadora",
    "uma loja de materiais de construção",
]


def _empresa(rng) -> str:
    return rng.choice(INDUSTRIAS + COMERCIO_E_SERVICOS)


def _industria(rng) -> str:
    return rng.choice(INDUSTRIAS)


def _revendedor(rng) -> str:
    """Quem COMPRA para revender: tem CMV e custo de aquisição."""
    return rng.choice([
        "uma rede de farmácias", "uma distribuidora de alimentos",
        "uma loja de materiais de construção",
        "uma rede de lojas de departamento",
        "um atacadista de bebidas", "uma livraria",
    ])


def _produto(rng) -> str:
    """Sem particípio: o cenário já diz "é vendida por", e "cada peça
    vendida é vendida por" saía redundante."""
    return rng.choice([
        "cada unidade", "cada peça", "cada item do catálogo",
        "cada caixa", "cada lote",
    ])


# ══════════════════════════════════════════════════════════
#  TEMPLATES CALCULÁVEIS — CUSTOS
# ══════════════════════════════════════════════════════════

def gerar_margem_contribuicao(rng):
    """
    Margem de contribuição unitária: preço − custo variável − despesa
    variável.

    Os distratores são os esquecimentos clássicos: deixar a comissão
    de fora, deixar o custo de fora, somar em vez de subtrair.
    """
    preco = rng.choice([40, 50, 60, 75, 80, 90, 100, 120, 150, 180, 200])
    cv = round(preco * rng.uniform(0.35, 0.60))
    dv = round(preco * rng.uniform(0.05, 0.15))
    if cv + dv >= preco or dv < 2:
        return None
    correta = preco - cv - dv

    distratores = [
        preco - cv,            # esqueceu a comissão
        preco - dv,            # esqueceu o custo variável
        cv + dv,               # somou os custos e parou aí
        preco - cv - 2 * dv,   # descontou a comissão duas vezes
        preco - (cv - dv),     # trocou o sinal da comissão
    ]

    # O cenário e a explicação precisam chamar o gasto pelo MESMO
    # nome. Antes a explicação falava sempre em "comissão", e o cenário
    # do meio dizia "despesa variável" — a justificativa comentava um
    # dado que não estava no enunciado.
    CENARIOS = [
        (f"Em {_empresa(rng)}, o preço de venda de {_produto(rng)} é "
         f"{_moeda(preco)}. O custo variável unitário é de {_moeda(cv)} "
         f"e a comissão paga ao vendedor é de {_moeda(dv)} por unidade.",
         "A comissão"),
        (f"O setor de custos de {_empresa(rng)} levantou os seguintes "
         f"dados por unidade: preço de venda de {_moeda(preco)}, custo "
         f"variável de {_moeda(cv)} e despesa variável de {_moeda(dv)}.",
         "A despesa variável"),
        (f"Uma análise de rentabilidade em {_empresa(rng)} apurou preço "
         f"de venda unitário de {_moeda(preco)}, custo variável de "
         f"{_moeda(cv)} e comissão de {_moeda(dv)} por peça.",
         "A comissão"),
    ]
    PERGUNTAS = [
        "Qual é a margem de contribuição unitária?",
        "A margem de contribuição unitária é de:",
        "Determine a margem de contribuição por unidade.",
    ]
    cen, rotulo = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"A margem de contribuição unitária é o que sobra do preço "
        f"depois de TODOS os gastos variáveis, e é ela que paga os "
        f"custos fixos. Aqui: {_moeda(preco)} − {_moeda(cv)} − "
        f"{_moeda(dv)} = {_moeda(correta)}. {rotulo} entra no cálculo "
        f"por ser gasto variável; deixá-la de fora é o erro mais comum."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (custos)", rng, _moeda, "monetaria",
                   fato=f"mc:{preco}:{cv}:{dv}")


def gerar_ponto_equilibrio(rng):
    """
    Ponto de equilíbrio contábil, financeiro ou econômico.

    Fonte: Estratégia Concursos, "Ponto de equilíbrio contábil,
    financeiro e econômico" — PEF = (CF − depreciação) / MCu;
    PEC = CF / MCu; PEE = (CF + lucro desejado) / MCu. A ordem é
    sempre PEF < PEC < PEE.

    Os distratores são os OUTROS dois pontos de equilíbrio: é a
    confusão que a questão quer separar, e as três grandezas têm a
    mesma ordem de tamanho.
    """
    mcu = rng.choice([10, 12, 15, 20, 25, 30, 40, 50])
    unidades = rng.choice([200, 300, 400, 500, 600, 800, 1000])
    cf = mcu * unidades
    dep = mcu * rng.choice([40, 50, 80, 100, 120])
    lucro = mcu * rng.choice([60, 100, 150, 200])
    if dep >= cf:
        return None

    pec = cf / mcu
    pef = (cf - dep) / mcu
    pee = (cf + lucro) / mcu

    modo = rng.choice(["contabil", "financeiro", "economico"])
    if modo == "contabil":
        correta, nome = pec, "contábil"
        conta = f"{_moeda(cf)} ÷ {_moeda(mcu)}"
    elif modo == "financeiro":
        correta, nome = pef, "financeiro"
        conta = f"({_moeda(cf)} − {_moeda(dep)}) ÷ {_moeda(mcu)}"
    else:
        correta, nome = pee, "econômico"
        conta = f"({_moeda(cf)} + {_moeda(lucro)}) ÷ {_moeda(mcu)}"

    distratores = [
        pec, pef, pee,
        (cf + dep) / mcu,          # somou a depreciação em vez de tirar
        (cf - lucro) / mcu,        # subtraiu o lucro desejado
    ]
    distratores = [d for d in distratores if abs(d - correta) > 1e-9 and d > 0]

    CENARIOS = [
        f"{_cap(_empresa(rng))} apura custos e despesas fixos "
        f"mensais de {_moeda(cf)}, dos quais {_moeda(dep)} correspondem "
        f"a depreciação. A margem de contribuição unitária é de "
        f"{_moeda(mcu)} e a diretoria estabeleceu lucro desejado de "
        f"{_moeda(lucro)} no período.",
        f"O controller de {_empresa(rng)} reuniu os dados do mês: "
        f"custos e despesas fixos de {_moeda(cf)}, incluindo "
        f"{_moeda(dep)} de depreciação; margem de contribuição unitária "
        f"de {_moeda(mcu)}; lucro desejado pelos sócios de "
        f"{_moeda(lucro)}.",
    ]
    PERGUNTAS = [
        f"Qual é o ponto de equilíbrio {nome}, em unidades?",
        f"O ponto de equilíbrio {nome} corresponde a quantas unidades?",
        f"Determine o ponto de equilíbrio {nome}.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"O ponto de equilíbrio {nome} é {conta} = {_unid(correta)}.\n\n"
        f"Os três se distinguem pelo NUMERADOR: o contábil usa os "
        f"custos fixos como estão; o financeiro desconta a depreciação, "
        f"que reduz o lucro mas não sai do caixa; o econômico acrescenta "
        f"o lucro desejado. Daí a ordem invariável: financeiro "
        f"({_unid(pef)}) < contábil ({_unid(pec)}) < econômico "
        f"({_unid(pee)})."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (custos)", rng, _unid, "numerica",
                   fato=f"pe:{modo}:{cf}:{mcu}:{dep}:{lucro}")


def gerar_markup(rng):
    """
    Preço de venda pelo markup.

    Fonte: Treasy, "Markup: o que é e como calcular" — índice =
    100 / [100 − (DV + DF + LP)], aplicado sobre o custo. O erro
    clássico é somar o percentual ao custo em vez de dividir.
    """
    custo = rng.choice([20, 25, 30, 40, 50, 60, 80, 100, 120])
    dv = rng.choice([8, 10, 12, 15])
    df = rng.choice([5, 8, 10, 12])
    lp = rng.choice([15, 20, 25, 30])
    soma = dv + df + lp
    if soma >= 65:
        return None

    divisor = (100 - soma) / 100
    correta = round(custo / divisor, 2)

    # Os dois últimos ficam ACIMA do preço correto de propósito. Todos
    # os erros clássicos do markup subestimam o preço, então sem eles a
    # resposta certa era o maior valor das cinco alternativas em 84%
    # das questões — acertava-se sem fazer conta nenhuma.
    divisor_duplo = max(0.22, (100 - soma - lp) / 100)
    distratores = [
        round(custo * (1 + soma / 100), 2),        # somou em vez de dividir
        round(custo / (1 - lp / 100), 2),          # só o lucro no divisor
        round(custo * (1 + lp / 100), 2),          # só o lucro, somando
        round(custo / (1 - (dv + df) / 100), 2),   # esqueceu o lucro
        round(custo * 100 / soma, 2),              # dividiu pela soma
        round(custo / divisor**2, 2),              # aplicou o markup duas vezes
        round(custo / divisor_duplo, 2),           # contou o lucro duas vezes
    ]

    CENARIOS = [
        f"{_cap(_revendedor(rng))} compra um item por {_moeda(custo)} "
        f"e precisa formar o preço de venda. As despesas variáveis "
        f"representam {dv}% do preço, as despesas fixas {df}% e o lucro "
        f"desejado é de {lp}% sobre o preço de venda.",
        f"Na formação de preço de {_revendedor(rng)}, o custo de aquisição "
        f"do produto é {_moeda(custo)}. Sobre o preço de venda incidem "
        f"{dv}% de despesas variáveis e {df}% de despesas fixas, e a "
        f"empresa quer {lp}% de lucro, também sobre o preço de venda.",
    ]
    PERGUNTAS = [
        "Pelo método do markup, qual deve ser o preço de venda?",
        "Qual é o preço de venda pelo markup?",
        "Determine o preço de venda pelo método do markup.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    # O divisor é formatado ANTES. Quando o .replace(".", ",") era
    # aplicado ao fim de um trecho inteiro, ele trocava também o ponto
    # final da frase anterior — a explicação saía com "não se soma,"
    # e as duas linhas coladas.
    div_txt = f"{divisor:.2f}".replace(".", ",")
    explicacao = (
        f"Os percentuais incidem sobre o PREÇO, não sobre o custo — por "
        f"isso se divide, e não se soma.\n\n"
        f"Markup divisor = 1 − ({dv}% + {df}% + {lp}%) = {div_txt}\n"
        f"Preço = {_moeda(custo)} ÷ {div_txt} = {_moeda(correta)}.\n\n"
        f"Somar {soma}% ao custo daria "
        f"{_moeda(custo * (1 + soma / 100))}, que não cobre as despesas: "
        f"elas são calculadas sobre o preço maior, não sobre o custo."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (formação de preço)", rng, _moeda,
                   "monetaria", fato=f"markup:{custo}:{dv}:{df}:{lp}")


def gerar_custeio(rng):
    """
    Custo unitário por absorção e por custeio variável.

    A diferença é uma só — o custo fixo rateado entra no primeiro e
    não entra no segundo —, e é isso que a questão isola.
    """
    cv = rng.choice([12, 15, 18, 20, 24, 30, 36, 40])
    q = rng.choice([500, 800, 1000, 1200, 1500, 2000])
    cf = q * rng.choice([5, 6, 8, 10, 12])

    absorcao = cv + cf / q
    variavel = cv
    modo = rng.choice(["absorcao", "variavel"])
    correta = absorcao if modo == "absorcao" else variavel
    nome = "por absorção" if modo == "absorcao" else "pelo custeio variável"

    distratores = [
        absorcao, variavel,
        cf / q,                    # só o rateio
        cv + cf,                   # somou o fixo inteiro
        cv + cf / (q / 2),         # rateou pela metade da produção
    ]
    distratores = [d for d in distratores if abs(d - correta) > 1e-9]

    CENARIOS = [
        f"{_cap(_industria(rng))} produziu {_num(q)} unidades no "
        f"mês. O custo variável unitário foi de {_moeda(cv)} e os custos "
        f"fixos de produção somaram {_moeda(cf)}.",
        f"No fechamento do mês, {_industria(rng)} registrou produção de "
        f"{_num(q)} unidades, custo variável de {_moeda(cv)} por unidade "
        f"e custos fixos de produção de {_moeda(cf)}.",
    ]
    PERGUNTAS = [
        f"Qual é o custo unitário {nome}?",
        f"O custo unitário apurado {nome} é de:",
        f"Determine o custo unitário {nome}.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    # A explicação abre pelo método PEDIDO. Quando abria sempre pela
    # absorção, a questão de custeio variável exibia primeiro um número
    # que não era a resposta — quem estuda pelo gabarito lia o errado.
    if modo == "absorcao":
        explicacao = (
            f"No custeio por ABSORÇÃO o custo fixo de produção é "
            f"rateado pela quantidade e entra no custo do produto: "
            f"{_moeda(cv)} + {_moeda(cf)} ÷ {_num(q)} = "
            f"{_moeda(absorcao)}.\n\n"
            f"No custeio VARIÁVEL o mesmo custo fixo seria tratado como "
            f"despesa do período, e o unitário ficaria em "
            f"{_moeda(variavel)}. Só a absorção é aceita para fins "
            f"societários e fiscais; o variável serve à decisão "
            f"gerencial."
        )
    else:
        explicacao = (
            f"No custeio VARIÁVEL o custo fixo é tratado como despesa "
            f"do período e NÃO entra no produto: o custo unitário é o "
            f"próprio custo variável, {_moeda(variavel)}.\n\n"
            f"Fosse por ABSORÇÃO, o fixo seria rateado pela quantidade "
            f"e o unitário subiria para {_moeda(cv)} + {_moeda(cf)} ÷ "
            f"{_num(q)} = {_moeda(absorcao)} — que é o distrator da "
            f"questão. Só a absorção é aceita para fins societários e "
            f"fiscais; o variável serve à decisão gerencial."
        )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (custos)", rng, _moeda, "monetaria",
                   fato=f"custeio:{modo}:{cv}:{cf}:{q}")


# ══════════════════════════════════════════════════════════
#  TEMPLATES CALCULÁVEIS — ANÁLISE DE BALANÇO
# ══════════════════════════════════════════════════════════

def gerar_liquidez(rng):
    """
    Índices de liquidez.

    Os distratores são os OUTROS índices calculados sobre os mesmos
    números — que é a confusão real, e mantém todas as alternativas
    na mesma ordem de grandeza.
    """
    disponivel = rng.choice([20, 30, 40, 50, 60, 80]) * 1000
    estoques = rng.choice([40, 60, 80, 100, 120]) * 1000
    outros_ac = rng.choice([30, 50, 70, 90]) * 1000
    ac = disponivel + estoques + outros_ac
    pc = rng.choice([80, 100, 120, 150, 200]) * 1000
    rlp = rng.choice([20, 40, 60]) * 1000
    pnc = rng.choice([50, 80, 100, 150]) * 1000

    indices = {
        "corrente":  (ac / pc, "ativo circulante ÷ passivo circulante"),
        "seca":      ((ac - estoques) / pc,
                      "(ativo circulante − estoques) ÷ passivo circulante"),
        "imediata":  (disponivel / pc,
                      "disponível ÷ passivo circulante"),
        "geral":     ((ac + rlp) / (pc + pnc),
                      "(ativo circulante + realizável a longo prazo) ÷ "
                      "(passivo circulante + passivo não circulante)"),
    }
    nome = rng.choice(list(indices))
    correta, formula = indices[nome]
    correta = round(correta, 2)

    distratores = [round(v, 2) for k, (v, _) in indices.items() if k != nome]
    distratores += [
        round(pc / ac, 2),                 # inverteu a razão
        round((ac + estoques) / pc, 2),    # somou o estoque em vez de tirar
    ]

    CENARIOS = [
        f"O balanço de {_empresa(rng)} apresenta: disponível "
        f"{_moeda(disponivel)}, estoques {_moeda(estoques)}, demais "
        f"contas do ativo circulante {_moeda(outros_ac)}, realizável a "
        f"longo prazo {_moeda(rlp)}, passivo circulante {_moeda(pc)} e "
        f"passivo não circulante {_moeda(pnc)}.",
        f"Na análise das demonstrações de {_empresa(rng)}, levantaram-se "
        f"os saldos: disponível de {_moeda(disponivel)}, estoques de "
        f"{_moeda(estoques)}, outras contas circulantes de "
        f"{_moeda(outros_ac)}, realizável a longo prazo de {_moeda(rlp)}, "
        f"passivo circulante de {_moeda(pc)} e passivo não circulante de "
        f"{_moeda(pnc)}.",
    ]
    PERGUNTAS = [
        f"Qual é o índice de liquidez {nome}?",
        f"O índice de liquidez {nome} é de:",
        f"Calcule a liquidez {nome}.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"Liquidez {nome} = {formula}.\n\n"
        f"O resultado é {_num(correta)}, ou seja, a empresa dispõe de "
        f"{_moeda(correta)} para cada real de obrigação considerada. "
        f"O que muda entre os índices é o que se admite como recurso: a "
        f"imediata conta só o caixa, a seca exclui o estoque por ser o "
        f"ativo de realização mais lenta, a corrente aceita todo o "
        f"circulante e a geral estende a conta ao longo prazo dos dois "
        f"lados."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (análise de balanço)", rng, _indice,
                   "numerica",
                   fato=f"liquidez:{nome}:{ac}:{pc}:{estoques}:{disponivel}")


def gerar_rentabilidade(rng):
    """
    ROA, ROE e margem líquida.

    O ROI ficou de fora: a literatura brasileira usa dois
    denominadores incompatíveis para ele — o investimento, na análise
    de balanço, e o custo, em marketing. Questão com duas respostas
    defensáveis não serve. Ver administracao/_fontes.md.
    """
    receita = rng.choice([500, 800, 1000, 1200, 1500, 2000]) * 1000
    ll = round(receita * rng.uniform(0.05, 0.18) / 1000) * 1000
    lo = ll + round(receita * rng.uniform(0.03, 0.08) / 1000) * 1000
    ativo = round(receita * rng.uniform(0.8, 2.0) / 1000) * 1000
    pl = round(ativo * rng.uniform(0.35, 0.70) / 1000) * 1000
    if min(ll, lo, ativo, pl) <= 0:
        return None

    # O terceiro campo é o artigo: "margem líquida" é feminina e
    # sairia "Determine o margem líquida" se o texto fixasse "o".
    #
    # O ROA traz o numerador NO PRÓPRIO NOME. Assaf Neto calcula o
    # retorno sobre o ativo com o lucro operacional; Matarazzo chama de
    # rentabilidade do ativo o lucro líquido sobre o ativo. As duas são
    # consagradas, as duas caem em prova, e sem dizer qual se pede a
    # questão tem duas respostas defensáveis — o mesmo motivo que
    # deixou o ROI de fora. Aqui o enunciado desempata.
    indices = {
        "retorno sobre o ativo (ROA), com base no lucro operacional":
            (lo / ativo * 100, "lucro operacional ÷ ativo total", "o"),
        "retorno sobre o patrimônio líquido (ROE)":
            (ll / pl * 100, "lucro líquido ÷ patrimônio líquido", "o"),
        "margem líquida":
            (ll / receita * 100, "lucro líquido ÷ receita líquida", "a"),
    }
    nome = rng.choice(list(indices))
    correta, formula, artigo = indices[nome]
    correta = round(correta, 2)

    distratores = [round(v, 2) for k, (v, _, _a) in indices.items()
                   if k != nome]
    distratores += [
        round(ll / ativo * 100, 2),    # cruzou lucro líquido com ativo
        round(lo / pl * 100, 2),       # cruzou lucro operacional com PL
        round(lo / receita * 100, 2),  # margem operacional no lugar
    ]

    CENARIOS = [
        f"A demonstração de resultado de {_empresa(rng)} registra "
        f"receita líquida de {_moeda(receita)}, lucro operacional de "
        f"{_moeda(lo)} e lucro líquido de {_moeda(ll)}. O balanço "
        f"aponta ativo total de {_moeda(ativo)} e patrimônio líquido de "
        f"{_moeda(pl)}.",
        f"No exercício encerrado, {_empresa(rng)} apurou receita líquida "
        f"de {_moeda(receita)}, lucro operacional de {_moeda(lo)}, lucro "
        f"líquido de {_moeda(ll)}, ativo total de {_moeda(ativo)} e "
        f"patrimônio líquido de {_moeda(pl)}.",
    ]
    PERGUNTAS = [
        f"Qual é {artigo} {nome}?",
        f"{artigo.upper()} {nome} corresponde a:",
        f"Determine {artigo} {nome}.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"{_cap(nome)} = {formula} = {_pct(correta)}.\n\n"
        f"Cada índice responde a uma pergunta diferente: o ROA mede o "
        f"que o ativo inteiro produz, independentemente de quem o "
        f"financiou; o ROE mede o que sobra para o sócio sobre o capital "
        f"dele; a margem líquida mede quanto de cada real vendido vira "
        f"lucro. Trocar o numerador entre eles é o erro que a questão "
        f"procura."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (análise de balanço)", rng, _pct,
                   "percentual",
                   fato=f"rentab:{nome[:12]}:{receita}:{ll}:{lo}:{ativo}:{pl}")


def gerar_giro_estoque(rng):
    """
    Giro de estoque e prazo médio de estocagem.

    O enunciado fixa o ano comercial de 360 dias: a literatura usa 360
    e 365, e sem dizer qual a questão teria duas respostas certas.
    """
    giro = rng.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
    estoque_medio = rng.choice([20, 30, 40, 50, 60, 80, 100]) * 1000
    cmv = giro * estoque_medio

    modo = rng.choice(["giro", "prazo"])
    if modo == "giro":
        correta = giro
        formatador, tipo = _vezes, "numerica"
        distratores = [
            round(estoque_medio / cmv, 2),      # inverteu
            round(360 / giro, 2),               # devolveu o prazo
            giro * 2, giro / 2, giro + 2,
        ]
        pergunta = "Qual é o giro do estoque no período?"
    else:
        # Os dias saem todos inteiros de propósito. 360/giro é sempre
        # exato (giro divide 360), mas 365/giro quase nunca é: deixar
        # as duas como estão punha vírgula só nos distratores, e a
        # alternativa "redonda" entregava a resposta sem contas.
        correta = round(360 / giro)
        formatador, tipo = _dias, "numerica"
        distratores = [
            giro,                               # devolveu o giro
            math.ceil(365 / giro),              # usou o ano civil
            30 * giro,                          # multiplicou em vez de dividir
            12 * giro,                          # raciocinou em meses
            round(360 / (giro + 1)),            # errou o giro por um
            round(360 / giro) * 2,
        ]
        pergunta = ("Qual é o prazo médio de estocagem, em dias, "
                    "considerando o ano comercial de 360 dias?")

    # CMV é conta de COMÉRCIO: quem revende mercadoria. Indústria
    # apura CPV, e transportadora não tem estoque de revenda nenhum —
    # o cenário sorteia só entre revendedores.
    CENARIOS = [
        f"{_cap(_revendedor(rng))} apurou custo das mercadorias "
        f"vendidas de {_moeda(cmv)} no ano e estoque médio de "
        f"{_moeda(estoque_medio)}.",
        f"No exercício, {_revendedor(rng)} registrou CMV de "
        f"{_moeda(cmv)} e manteve estoque médio de "
        f"{_moeda(estoque_medio)}.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, pergunta)}"
    explicacao = (
        f"Giro do estoque = CMV ÷ estoque médio = {_moeda(cmv)} ÷ "
        f"{_moeda(estoque_medio)} = {_vezes(giro)} no período.\n\n"
        f"O prazo médio de estocagem é o mesmo dado pelo outro lado: "
        f"360 ÷ {_num(giro)} = {_dias(round(360 / giro, 2))}. Giro alto "
        f"e prazo curto descrevem a mesma situação — o estoque se "
        f"renova depressa."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (gestão de estoques)", rng, formatador,
                   tipo, fato=f"giro:{modo}:{cmv}:{estoque_medio}")


# ══════════════════════════════════════════════════════════
#  TEMPLATES CALCULÁVEIS — INVESTIMENTOS
# ══════════════════════════════════════════════════════════

def gerar_payback(rng):
    """Payback simples com fluxo de caixa uniforme."""
    fluxo = rng.choice([20, 25, 30, 40, 50, 60, 80]) * 1000
    anos = rng.choice([2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0])
    investimento = int(fluxo * anos)
    correta = round(investimento / fluxo, 2)

    distratores = [
        round(fluxo / investimento * 100, 2),
        round(investimento / (fluxo * 2), 2),
        round(correta + 1, 2),
        round(correta - 1, 2),
        round(investimento / (fluxo / 2), 2),
    ]
    distratores = [d for d in distratores if d > 0 and abs(d - correta) > 1e-9]

    CENARIOS = [
        f"{_cap(_empresa(rng))} avalia um projeto que exige "
        f"investimento inicial de {_moeda(investimento)} e deve gerar "
        f"fluxo de caixa líquido de {_moeda(fluxo)} por ano, de forma "
        f"constante.",
        f"Um projeto apresentado à diretoria de {_empresa(rng)} requer "
        f"{_moeda(investimento)} de aporte inicial e promete entradas "
        f"líquidas anuais e uniformes de {_moeda(fluxo)}.",
    ]
    PERGUNTAS = [
        "Qual é o payback simples do projeto, em anos?",
        "O prazo de retorno simples do investimento é de:",
        "Determine o payback simples.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"Com fluxo uniforme, o payback simples é o investimento "
        f"dividido pela entrada anual: {_moeda(investimento)} ÷ "
        f"{_moeda(fluxo)} = {_anos(correta)}.\n\n"
        f"É uma medida de prazo, não de rentabilidade: ignora o valor do "
        f"dinheiro no tempo e tudo o que entra depois do retorno. Por "
        f"isso serve como filtro de risco, e não como critério único de "
        f"decisão."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (análise de investimentos)", rng, _anos,
                   "numerica", fato=f"payback:{investimento}:{fluxo}")


def gerar_vpl(rng):
    """Valor presente líquido com dois períodos."""
    taxa = rng.choice([10, 20, 25])
    i = taxa / 100
    f1 = rng.choice([50, 60, 80, 100, 120]) * 1000
    f2 = rng.choice([60, 80, 100, 150, 200]) * 1000
    vp = f1 / (1 + i) + f2 / (1 + i) ** 2
    investimento = round(vp * rng.uniform(0.6, 0.95) / 1000) * 1000
    correta = round(vp - investimento, 2)
    if correta <= 0:
        return None

    distratores = [
        round(f1 + f2 - investimento, 2),                 # não descontou
        round(f1 / (1 + i) + f2 / (1 + i) - investimento, 2),  # expoente
        round(vp, 2),                                     # esqueceu o aporte
        round(investimento - vp, 2),                      # inverteu o sinal
        round(f1 + f2, 2),                                # só somou
    ]

    CENARIOS = [
        f"{_cap(_empresa(rng))} estuda um projeto com "
        f"investimento inicial de {_moeda(investimento)}, que gerará "
        f"{_moeda(f1)} ao final do primeiro ano e {_moeda(f2)} ao final "
        f"do segundo. A taxa mínima de atratividade é de {taxa}% ao ano.",
        f"Um projeto submetido a {_empresa(rng)} exige aporte de "
        f"{_moeda(investimento)} hoje e devolve {_moeda(f1)} em um ano e "
        f"{_moeda(f2)} em dois anos, a uma taxa de desconto de {taxa}% "
        f"ao ano.",
    ]
    PERGUNTAS = [
        "Qual é o valor presente líquido do projeto?",
        "O VPL do projeto é de:",
        "Determine o valor presente líquido.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"Cada entrada volta ao presente pelo número de períodos que a "
        f"separa de hoje:\n"
        f"  {_moeda(f1)} ÷ 1,{taxa:02d} = {_moeda(f1 / (1 + i))}\n"
        f"  {_moeda(f2)} ÷ 1,{taxa:02d}² = {_moeda(f2 / (1 + i) ** 2)}\n"
        f"Somadas dão {_moeda(vp)}; descontado o aporte de "
        f"{_moeda(investimento)}, o VPL é {_moeda(correta)}.\n\n"
        f"VPL positivo significa que o projeto rende ACIMA da taxa "
        f"exigida — não que ele simplesmente dá lucro."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (análise de investimentos)", rng, _moeda,
                   "monetaria", fato=f"vpl:{investimento}:{f1}:{f2}:{taxa}")


def gerar_depreciacao(rng):
    """Depreciação linear com valor residual."""
    valor = rng.choice([40, 50, 60, 80, 100, 120, 200]) * 1000
    residual = round(valor * rng.choice([0.1, 0.15, 0.2]))
    vida = rng.choice([4, 5, 8, 10])
    correta = (valor - residual) / vida

    distratores = [
        valor / vida,                    # ignorou o residual
        (valor + residual) / vida,       # somou o residual
        (valor - residual) / (vida - 1),
        (valor - residual) / 12,         # confundiu anos com meses
        correta / 12,                    # devolveu a parcela mensal
    ]

    CENARIOS = [
        f"{_cap(_empresa(rng))} adquiriu um equipamento por "
        f"{_moeda(valor)}, com vida útil estimada em {vida} anos e valor "
        f"residual de {_moeda(residual)}.",
        f"Um veículo comprado por {_empresa(rng)} custou {_moeda(valor)}, "
        f"tem vida útil de {vida} anos e valor residual previsto de "
        f"{_moeda(residual)}.",
    ]
    PERGUNTAS = [
        "Pelo método linear, qual é a depreciação anual?",
        "A cota anual de depreciação pelo método linear é de:",
        "Determine a depreciação anual pelo método das quotas constantes.",
    ]
    cen = rng.choice(CENARIOS)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PERGUNTAS))}"
    explicacao = (
        f"Deprecia-se o que o bem PERDE, não o que ele custou: subtrai-se "
        f"o valor residual antes de dividir pela vida útil.\n\n"
        f"({_moeda(valor)} − {_moeda(residual)}) ÷ {vida} = "
        f"{_moeda(correta)} por ano."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (contabilidade)", rng, _moeda, "monetaria",
                   fato=f"deprec:{valor}:{residual}:{vida}")


# ══════════════════════════════════════════════════════════
#  BASE DE FATOS — CONTEÚDO CONCEITUAL
# ══════════════════════════════════════════════════════════

# ── Escolas da administração ──
#
# Fontes: Chiavenato, Introdução à Teoria Geral da Administração;
# Maximiano, Teoria Geral da Administração.
#
# (escola, autor, ênfase, contribuição)
#
# `autor` é None quando a escola não tem um nome incontroverso — é o
# caso da teoria da contingência, resultado de pesquisas independentes
# de Chandler, Burns e Stalker, Lawrence e Lorsch e Joan Woodward.
# Perguntar "quem formulou" ali teria mais de uma resposta defensável,
# então essas entradas só aparecem nas perguntas de ênfase.
ESCOLAS = [
    ("administração científica", "Frederick Taylor",
     "a tarefa executada no chão de fábrica",
     "o estudo de tempos e movimentos e a seleção científica do "
     "trabalhador"),
    # A ênfase da clássica NÃO diz "estrutura". Na tabela de
    # Chiavenato, clássica E burocracia estão as duas sob "ênfase na
    # estrutura" — com "estrutura" entre as alternativas, a questão
    # sobre a burocracia ganhava uma segunda resposta defensável.
    ("teoria clássica", "Henri Fayol",
     "as funções do administrador e os princípios gerais de gestão",
     "as funções administrativas e os catorze princípios gerais"),
    ("teoria das relações humanas", "Elton Mayo",
     "as pessoas e os grupos informais",
     "a experiência de Hawthorne, que mostrou o peso dos fatores "
     "sociais sobre a produtividade"),
    ("teoria da burocracia", "Max Weber",
     "as normas e a racionalidade formal",
     "a autoridade legal, a impessoalidade e a hierarquia definida em "
     "regulamento"),
    ("teoria comportamental", "Herbert Simon",
     "o processo de tomada de decisão",
     "a racionalidade limitada — decide-se com a informação que se tem, "
     "não com a que existe"),
    ("teoria geral dos sistemas", "Ludwig von Bertalanffy",
     "a organização como sistema aberto",
     "o ciclo de entradas, processamento, saídas e retroalimentação"),
    ("teoria da contingência", None,
     "a adequação da estrutura ao ambiente",
     "a constatação de que não há uma forma única de administrar: a "
     "estrutura eficaz depende do ambiente e da tecnologia"),
]

# ── Funções administrativas (PODC) ──
#
# Fonte: Chiavenato, a partir de Fayol. Fayol descrevia cinco funções
# (prever, organizar, comandar, coordenar, controlar); a formulação
# corrente reúne comandar e coordenar em dirigir.
FUNCOES = [
    ("planejar", "definir objetivos e o caminho para alcançá-los",
     "é a primeira função e condiciona as demais: sem objetivo definido "
     "não há como organizar recursos nem medir resultado"),
    ("organizar", "distribuir recursos, tarefas e autoridade",
     "é aqui que se desenha a estrutura, se agrupam as atividades e se "
     "define quem responde por quê"),
    ("dirigir", "conduzir e coordenar as pessoas para executar o planejado",
     "reúne o comandar e o coordenar de Fayol, e é a função que lida "
     "diretamente com o comportamento humano"),
    ("controlar", "comparar o resultado obtido com o planejado e corrigir",
     "fecha o ciclo e o realimenta: o desvio detectado volta ao "
     "planejamento"),
]

# Situação de trabalho → função exercida. Cada caso traz no texto o
# verbo que decide: fixar meta (planejar), repartir atribuição
# (organizar), atuar sobre pessoas (dirigir), confrontar realizado com
# previsto (controlar).
FUNCOES_CASOS = [
    ("a diretoria define que a meta de vendas do próximo exercício "
     "será de 12% acima da do ano corrente", "planejar"),
    ("a equipe elabora o orçamento do semestre e estabelece os prazos "
     "de cada etapa do projeto", "planejar"),
    ("antes de iniciar a obra, a empresa levanta os cenários possíveis "
     "e escolhe o curso de ação que seguirá", "planejar"),
    ("o gerente divide o departamento em três células e atribui a cada "
     "uma delas um responsável e um conjunto de tarefas", "organizar"),
    ("a empresa elabora o organograma e o manual que descreve a "
     "quem cada cargo se reporta", "organizar"),
    ("a chefia redistribui os equipamentos e o pessoal entre os "
     "setores para acomodar a nova linha de produto", "organizar"),
    ("o supervisor orienta os funcionários recém-admitidos e resolve "
     "um conflito surgido entre dois deles", "dirigir"),
    ("a liderança comunica a mudança à equipe, esclarece as dúvidas e "
     "motiva o grupo a aderir a ela", "dirigir"),
    ("o gerente conversa em particular com um funcionário desmotivado "
     "para entender o que houve e reengajá-lo no trabalho", "dirigir"),
    ("ao fim do mês, a área confronta o realizado com o orçado e "
     "aponta os desvios encontrados", "controlar"),
    ("a auditoria interna verifica se os procedimentos executados "
     "seguiram o que estava previsto e determina a correção",
     "controlar"),
    ("o painel de indicadores acusa produção 8% abaixo da meta e a "
     "gerência aciona as medidas corretivas", "controlar"),
]

# ── Estruturas organizacionais ──
ESTRUTURAS = [
    ("funcional", "agrupa as pessoas por especialidade — produção, "
     "vendas, finanças",
     "favorece a especialização técnica, mas dificulta a coordenação "
     "entre áreas"),
    ("divisional", "agrupa por produto, cliente ou região geográfica",
     "aproxima a decisão do mercado, ao custo de duplicar funções em "
     "cada divisão"),
    ("matricial", "cruza a especialidade funcional com a gestão por "
     "projeto",
     "o subordinado responde a dois chefes, o que quebra a unidade de "
     "comando e exige negociação constante"),
    ("em rede", "mantém um núcleo enxuto e terceiriza as demais "
     "atividades",
     "ganha flexibilidade e perde controle direto sobre o que foi "
     "terceirizado"),
    # O ponto fraco não repete o vocabulário do enunciado de
    # propósito: com "assessoria" e "linha" nos dois lados, a
    # alternativa certa se destacava sem que se soubesse a matéria.
    ("linha-staff", "acrescenta aos órgãos executivos um corpo "
     "consultivo, sem poder de mando, que os apoia tecnicamente",
     "quem aconselha não decide, e o desgaste sobre até onde vai a "
     "recomendação e onde começa a ordem é permanente"),
    ("por processos", "organiza o trabalho pelo fluxo que entrega "
     "valor ao cliente, e não por departamento",
     "exige redesenhar a operação inteira e enfraquece a carreira "
     "técnica dentro de cada especialidade"),
]

# ── Estratégia ──
#
# Fontes: Porter, Estratégia Competitiva e Vantagem Competitiva;
# Kaplan e Norton, A Estratégia em Ação (Balanced Scorecard).
SWOT = [
    ("forças", "interno", "favorável"),
    ("fraquezas", "interno", "desfavorável"),
    ("oportunidades", "externo", "favorável"),
    ("ameaças", "externo", "desfavorável"),
]

CINCO_FORCAS = [
    "a rivalidade entre os concorrentes existentes",
    "a ameaça de novos entrantes",
    "a ameaça de produtos substitutos",
    "o poder de barganha dos fornecedores",
    "o poder de barganha dos compradores",
]

# Situação concreta → força que ela representa → por quê.
# Cada situação aponta para UMA força só: o que a distingue está
# escrito no próprio enunciado (mesmo setor ou outro, quem dita o
# preço, o que impede a entrada).
FORCAS_CENARIOS = [
    ("muitas empresas de porte semelhante disputam o mesmo cliente e "
     "respondem umas às outras com cortes sucessivos de preço",
     "a rivalidade entre os concorrentes existentes",
     "a disputa se dá entre empresas que já atuam no setor"),
    ("o setor praticamente não cresce, e cada empresa só amplia sua "
     "participação tirando-a de um concorrente já instalado",
     "a rivalidade entre os concorrentes existentes",
     "mercado estagnado transforma ganho de um em perda de outro, "
     "dentro do mesmo setor"),
    ("o capital exigido para começar a operar é baixo, não há "
     "exigência de licença e a tecnologia é de domínio público",
     "a ameaça de novos entrantes",
     "barreiras de entrada baixas deixam o setor aberto a quem ainda "
     "não está nele"),
    ("expira a patente que dava exclusividade sobre o produto, e "
     "qualquer fabricante passa a poder produzi-lo",
     "a ameaça de novos entrantes",
     "a barreira legal que protegia o setor deixa de existir"),
    ("um serviço de outro setor passa a atender à mesma necessidade "
     "do cliente, por preço menor e sem usar a mesma tecnologia",
     "a ameaça de produtos substitutos",
     "o substituto vem de FORA do setor e satisfaz a mesma "
     "necessidade por outro meio"),
    ("os clientes começam a resolver por conta própria, com uma "
     "solução caseira, aquilo que antes contratavam do setor",
     "a ameaça de produtos substitutos",
     "a necessidade passa a ser atendida por alternativa externa ao "
     "setor"),
    ("um único fabricante no mundo produz o componente essencial e "
     "impõe reajustes sem abrir negociação",
     "o poder de barganha dos fornecedores",
     "quem vende o insumo é concentrado e dita as condições"),
    ("o insumo é altamente especializado e trocar de fornecedor "
     "exigiria requalificar toda a linha de produção",
     "o poder de barganha dos fornecedores",
     "o custo de mudança prende a empresa a quem a abastece"),
    ("três grandes redes varejistas concentram quase toda a revenda "
     "do produto e exigem desconto e prazo maior a cada contrato",
     "o poder de barganha dos compradores",
     "quem compra é concentrado e impõe as condições da venda"),
    ("o produto é padronizado, o cliente compara preços com "
     "facilidade e troca de marca sem custo algum",
     "o poder de barganha dos compradores",
     "sem diferenciação nem custo de troca, a decisão fica com quem "
     "compra"),
]

BSC = [
    ("financeira", "como a empresa é vista pelos acionistas"),
    ("clientes", "como a empresa é vista por quem compra dela"),
    # A pergunta-chave não usa a palavra "processos": era o único
    # termo que reaparecia na alternativa certa, e entregava o item.
    ("processos internos",
     "em que a empresa precisa ser excelente para entregar o que "
     "promete ao cliente"),
    ("aprendizado e crescimento",
     "como sustentar a capacidade de mudar e melhorar"),
]

GENERICAS = [
    ("liderança em custo", "ser o produtor de menor custo do setor, "
     "atendendo a um mercado amplo"),
    ("diferenciação", "oferecer algo percebido como único no setor, "
     "atendendo a um mercado amplo"),
    ("enfoque", "concentrar-se em um segmento estreito, por custo ou "
     "por diferenciação"),
]

# ── Motivação ──
#
# Fontes: Maslow, Motivation and Personality; Herzberg, The Motivation
# to Work; McGregor, The Human Side of Enterprise; Vroom, Work and
# Motivation.
TEORIAS_MOTIVACAO = [
    # A tese não repete "necessidades": o nome da teoria já traz a
    # palavra no enunciado, e ela reaparecia só na alternativa certa.
    ("hierarquia das necessidades", "Abraham Maslow",
     "o que motiva se organiza em cinco níveis, e um nível só passa a "
     "motivar depois que o anterior está razoavelmente satisfeito"),
    ("teoria dos dois fatores", "Frederick Herzberg",
     "os fatores higiênicos evitam a insatisfação mas não motivam; só "
     "os motivacionais, ligados ao conteúdo do trabalho, motivam"),
    ("teorias X e Y", "Douglas McGregor",
     "a teoria X supõe aversão ao trabalho e exige controle; a teoria Y "
     "supõe iniciativa e favorece a delegação"),
    ("teoria da expectância", "Victor Vroom",
     "a motivação depende de o esforço levar ao desempenho, o desempenho "
     "à recompensa, e a recompensa ter valor para a pessoa"),
]

NIVEIS_MASLOW = [
    (1, "fisiológicas", "fome, sede, sono e abrigo"),
    (2, "de segurança", "estabilidade no emprego e proteção contra riscos"),
    (3, "sociais", "pertencer a um grupo, amizade e aceitação"),
    (4, "de estima", "reconhecimento, status e respeito dos pares"),
    (5, "de autorrealização", "usar o próprio potencial por inteiro"),
]


# ══════════════════════════════════════════════════════════
#  TEMPLATES CONCEITUAIS
# ══════════════════════════════════════════════════════════

def gerar_escolas(rng):
    """Escola da administração: autor, ênfase ou contribuição."""
    modo = rng.choice(["autor", "enfase", "escola_por_enfase"])

    # A chave do fato é por MODO, não por escola: saber quem formulou a
    # teoria clássica não é saber qual é a ênfase dela. Só os dois
    # sentidos da ênfase (escola→ênfase e ênfase→escola) dividem chave,
    # porque aí é a mesma informação lida de trás para frente.
    if modo == "autor":
        candidatos = [e for e in ESCOLAS if e[1]]
        escola, autor, enfase, contrib = rng.choice(candidatos)
        chave = f"escola:autor:{escola}"
        correta = autor
        distratores = [e[1] for e in ESCOLAS if e[1] and e[1] != autor]
        distratores += ["Peter Drucker", "Chester Barnard", "Mary Parker Follett"]
        CEN = [
            f"Em uma revisão das escolas da administração, chega-se "
            f"à {escola}.",
            f"O estudo da evolução do pensamento administrativo inclui "
            f"a {escola}.",
        ]
        PER = ["Quem a formulou?",
               "Assinale a alternativa com seu principal formulador.",
               "Seu autor é:"]
    elif modo == "enfase":
        escola, autor, enfase, contrib = rng.choice(ESCOLAS)
        chave = f"escola:enfase:{escola}"
        correta = enfase
        distratores = [e[2] for e in ESCOLAS if e[2] != enfase]
        CEN = [
            f"As escolas da administração se distinguem pelo objeto que "
            f"colocam no centro. Considere a {escola}.",
            f"Ao comparar as correntes do pensamento administrativo, "
            f"examina-se a {escola}.",
        ]
        PER = ["Qual é a sua ênfase?",
               "Assinale a alternativa que indica sua ênfase.",
               "Sua ênfase recai sobre:"]
    else:
        escola, autor, enfase, contrib = rng.choice(ESCOLAS)
        chave = f"escola:enfase:{escola}"   # mesmo fato, sentido inverso
        correta = escola
        distratores = [e[0] for e in ESCOLAS if e[0] != escola]
        CEN = [
            f"Uma corrente do pensamento administrativo tem como ênfase "
            f"{enfase}.",
            f"Determinada escola da administração organiza-se em torno "
            f"{_contrair_de(enfase)}.",
        ]
        PER = ["Assinale a alternativa que a identifica.",
               "Trata-se da:",
               "Essa corrente é a:"]

    cen = rng.choice(CEN)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
    explicacao = (
        f"A {escola}"
        + (f", de {autor}," if autor else ",")
        + f" tem como ênfase {enfase}. Sua contribuição central é "
        f"{contrib}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (teorias da administração)", rng, str,
                   "textual", fato=chave)


def gerar_funcoes(rng):
    """
    As quatro funções administrativas.

    A tabela tem quatro linhas e nada a fazer quanto a isso: o PODC é
    o que é. O modo "caso" é o que dá material — reconhecer a função
    em uma situação de trabalho é conhecimento distinto de recitar a
    definição, e é assim que a banca costuma cobrar.
    """
    modo = rng.choice(["nome", "definicao", "caso", "caso"])

    if modo == "caso":
        situacao, funcao = rng.choice(FUNCOES_CASOS)
        definicao = next(f[1] for f in FUNCOES if f[0] == funcao)
        comentario = next(f[2] for f in FUNCOES if f[0] == funcao)
        correta = funcao
        distratores = [f[0] for f in FUNCOES if f[0] != funcao]
        distratores += ["coordenar", "supervisionar", "avaliar"]
        # O enunciado fixa "as quatro funções do processo
        # administrativo": sem isso, "coordenar" — que é função na
        # lista original de Fayol — seria defensável como resposta.
        CEN = [
            f"Em uma organização, {situacao}. Considere as quatro "
            f"funções do processo administrativo.",
            f"Observe a seguinte situação de trabalho: {situacao}. "
            f"O processo administrativo compreende quatro funções.",
        ]
        PER = ["Assinale a que está sendo exercida.",
               "A função em questão é a de:",
               "Trata-se do exercício da função de:"]
        formatador = str
        chave = f"funcao:caso:{situacao[:40]}"
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        explicacao = (
            f"A situação descreve a função de {funcao}: {definicao}. "
            f"{_cap(comentario)}.\n\n"
            f"As quatro funções formam um ciclo — planejar, organizar, "
            f"dirigir e controlar —, e o controle realimenta o "
            f"planejamento."
        )
        return _montar(enunciado, correta, distratores, explicacao,
                       "Administração (processo administrativo)", rng,
                       formatador, "textual", fato=chave)

    funcao, definicao, comentario = rng.choice(FUNCOES)
    # Os dois sentidos são o mesmo fato: quem sabe a definição de
    # "dirigir" responde às duas. Chave única de propósito.
    chave = f"funcao:{funcao}"
    inverso = modo == "nome"

    if inverso:
        correta = funcao
        distratores = [f[0] for f in FUNCOES if f[0] != funcao]
        distratores += ["coordenar", "supervisionar", "avaliar"]
        CEN = [
            f"Entre as funções administrativas, uma consiste em "
            f"{definicao}.",
            f"O ciclo administrativo reúne quatro funções. Uma delas "
            f"consiste em {definicao}.",
        ]
        PER = ["Assinale a alternativa que a nomeia.",
               "Trata-se da função de:",
               "Essa função é a de:"]
        formatador = str
    else:
        correta = definicao
        distratores = [f[1] for f in FUNCOES if f[1] != definicao]
        distratores += [
            "registrar as operações para fins contábeis e fiscais",
            "negociar preços e condições com fornecedores externos",
        ]
        CEN = [
            f"O ciclo administrativo é descrito por quatro funções. "
            f"Considere a função de {funcao}.",
            f"Em uma aula sobre o processo administrativo, discute-se a "
            f"função de {funcao}.",
        ]
        PER = ["Em que ela consiste?",
               "Assinale a alternativa que a define.",
               "Essa função consiste em:"]
        formatador = str

    cen = rng.choice(CEN)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
    explicacao = (
        f"A função de {funcao} consiste em {definicao}. {_cap(comentario)}.\n\n"
        f"As quatro funções formam um ciclo — planejar, organizar, "
        f"dirigir e controlar —, e o controle realimenta o planejamento."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (processo administrativo)", rng,
                   formatador, "textual", fato=chave)


def gerar_estruturas(rng):
    """
    Estruturas organizacionais: característica ou limitação.

    Chave por modo: reconhecer a estrutura pelo desenho e saber onde
    ela falha são duas coisas — quem acerta uma não acerta a outra de
    graça.
    """
    nome, caracteristica, limitacao = rng.choice(ESTRUTURAS)
    modo = rng.choice(["por_caracteristica", "limitacao"])
    chave = f"estrutura:{'def' if modo == 'por_caracteristica' else 'fraco'}:{nome}"

    if modo == "por_caracteristica":
        correta = nome
        distratores = [e[0] for e in ESTRUTURAS if e[0] != nome]
        distratores += ["por comitês", "circular", "colegiada"]
        # Os dois cenários são femininos: "Determinado desenho
        # organizacional" puxava "que o identifica", e o comando é
        # compartilhado.
        CEN = [
            f"Uma estrutura organizacional {caracteristica}.",
            f"Determinada forma de organização {caracteristica}.",
        ]
        PER = ["Assinale a alternativa que a identifica.",
               "Trata-se da estrutura:",
               "Esse desenho corresponde à estrutura:"]
        formatador = str
    else:
        correta = limitacao
        distratores = [e[2] for e in ESTRUTURAS if e[2] != limitacao]
        distratores += [
            "elimina a necessidade de coordenação entre as áreas e "
            "dispensa qualquer instância de integração",
            "impede a especialização técnica dos profissionais e "
            "obriga cada um a dominar todas as atividades",
        ]
        CEN = [
            f"Considere a estrutura organizacional {nome}, que "
            f"{caracteristica}.",
            f"Em um projeto de reorganização, avalia-se a estrutura "
            f"{nome}, que {caracteristica}.",
        ]
        PER = ["Qual é a sua principal limitação?",
               "Assinale a alternativa que aponta seu ponto fraco.",
               "Sua principal desvantagem é que:"]
        formatador = str

    cen = rng.choice(CEN)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
    explicacao = (
        f"A estrutura {nome} {caracteristica}. Em contrapartida, "
        f"{limitacao}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (estrutura organizacional)", rng,
                   formatador, "textual", fato=chave)


def gerar_estrategia(rng):
    """SWOT, cinco forças de Porter, BSC e estratégias genéricas."""
    modo = rng.choice(["swot", "porter", "bsc", "genericas"])

    if modo == "swot":
        termo, origem, sinal = rng.choice(SWOT)
        correta = f"{origem}, de natureza {sinal}"
        distratores = [f"{o}, de natureza {s}"
                       for t, o, s in SWOT if t != termo]
        distratores += ["interno, mas só mensurável no longo prazo",
                        "externo, mas controlável pela empresa"]
        CEN = [
            f"Na análise SWOT, classifica-se cada elemento quanto à "
            f"origem e ao efeito. Considere as {termo}.",
            f"Uma equipe de planejamento aplica a matriz SWOT e chega às "
            f"{termo}.",
        ]
        # Concordância: os quatro termos da SWOT são femininos
        # plurais ("as oportunidades"), e o comando tratava-os como
        # "esse elemento" / "que o classifica".
        PER = ["Como elas se classificam?",
               "Assinale a alternativa que as classifica corretamente.",
               "Trata-se de fator:"]
        explicacao = (
            f"Na SWOT, as {termo} são um fator de origem {origem} e "
            f"efeito {sinal}.\n\n"
            f"O eixo de origem separa o que está dentro da empresa — "
            f"forças e fraquezas, sobre as quais ela age diretamente — "
            f"do que está fora: oportunidades e ameaças, que ela pode no "
            f"máximo antecipar."
        )
        fato = f"swot:{termo}"
        topico = "Administração (planejamento estratégico)"
    elif modo == "porter":
        # Aqui NÃO se pergunta "qual é uma das cinco forças": as cinco
        # são todas corretas, e a questão ficaria sem resposta única.
        # Pergunta-se qual força uma situação concreta representa.
        situacao, correta, porque = rng.choice(FORCAS_CENARIOS)
        distratores = [f for f in CINCO_FORCAS if f != correta]
        CEN = [
            f"Na análise competitiva de um setor pelo modelo das cinco "
            f"forças de Porter, observa-se a seguinte situação: "
            f"{situacao}.",
            f"Um setor é avaliado pelo modelo das cinco forças de "
            f"Porter. Constata-se que {situacao}.",
        ]
        PER = ["Assinale a alternativa que identifica a força em questão.",
               "A força competitiva em questão é:",
               "Qual das forças do modelo essa situação descreve?"]
        explicacao = (
            f"A situação descreve {correta}: {porque}.\n\n"
            f"As cinco forças são a rivalidade entre os concorrentes "
            f"existentes, a ameaça de novos entrantes, a ameaça de "
            f"produtos substitutos, o poder de barganha dos "
            f"fornecedores e o poder de barganha dos compradores. "
            f"Todas descrevem a ESTRUTURA do setor, e não o desempenho "
            f"de uma empresa dentro dele."
        )
        fato = f"porter:{situacao[:40]}"
        topico = "Administração (planejamento estratégico)"
    elif modo == "bsc":
        perspectiva, pergunta_chave = rng.choice(BSC)
        correta = perspectiva
        distratores = [p for p, _ in BSC if p != perspectiva]
        distratores += ["concorrência", "sustentabilidade", "governança"]
        CEN = [
            f"O Balanced Scorecard organiza os indicadores em quatro "
            f"perspectivas. Uma delas responde: {pergunta_chave}.",
            f"Ao montar o painel estratégico pelo BSC, uma das "
            f"perspectivas trata de {pergunta_chave}.",
        ]
        PER = ["Assinale a alternativa que a nomeia.",
               "Trata-se da perspectiva:",
               "Essa perspectiva é a:"]
        explicacao = (
            f"A perspectiva {perspectiva} do Balanced Scorecard responde "
            f"a: {pergunta_chave}.\n\n"
            f"As quatro se encadeiam de baixo para cima — aprendizado e "
            f"crescimento sustentam os processos internos, que entregam "
            f"valor aos clientes, que produzem o resultado financeiro."
        )
        fato = f"bsc:{perspectiva}"
        topico = "Administração (planejamento estratégico)"
    else:
        nome, definicao = rng.choice(GENERICAS)
        correta = definicao
        distratores = [d for n, d in GENERICAS if n != nome]
        distratores += [
            "crescer por aquisição de concorrentes diretos",
            "manter preço e produto iguais aos da média do setor",
            "distribuir o investimento igualmente entre todos os "
            "segmentos",
        ]
        CEN = [
            f"Porter descreve três estratégias competitivas genéricas. "
            f"Considere a {nome}.",
            f"Na escolha do posicionamento competitivo, avalia-se a "
            f"estratégia de {nome}.",
        ]
        PER = ["Em que ela consiste?",
               "Assinale a alternativa que a define.",
               "Essa estratégia consiste em:"]
        explicacao = (
            f"A estratégia de {nome} consiste em {definicao}.\n\n"
            f"As três genéricas combinam duas decisões: a fonte da "
            f"vantagem — custo ou diferenciação — e a amplitude do "
            f"mercado. O enfoque é a escolha de atuar em alvo estreito, "
            f"por qualquer das duas fontes."
        )
        fato = f"generica:{nome}"
        topico = "Administração (planejamento estratégico)"

    cen = rng.choice(CEN)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
    return _montar(enunciado, correta, distratores, explicacao, topico,
                   rng, str, "textual", fato=fato)


def gerar_motivacao(rng):
    """Teorias da motivação e a hierarquia de Maslow."""
    modo = rng.choice(["autor", "tese", "maslow"])

    if modo == "maslow":
        nivel, nome, exemplos = rng.choice(NIVEIS_MASLOW)
        submodo = rng.choice(["por_exemplo", "ordem"])
        if submodo == "por_exemplo":
            correta = nome
            distratores = [n for _, n, _ in NIVEIS_MASLOW if n != nome]
            distratores += ["de reciprocidade", "de conformidade"]
            CEN = [
                f"Na hierarquia de Maslow, um dos níveis reúne "
                f"{exemplos}.",
                f"Ao classificar as necessidades segundo Maslow, "
                f"um dos níveis é o que abrange {exemplos}.",
            ]
            PER = ["Assinale a alternativa que nomeia esse nível.",
                   "Trata-se das necessidades:",
                   "Esse nível corresponde às necessidades:"]
        else:
            correta = f"{nivel}º nível, de baixo para cima"
            distratores = [f"{n}º nível, de baixo para cima"
                           for n, _, _ in NIVEIS_MASLOW if n != nivel]
            CEN = [
                f"Na pirâmide de Maslow, as necessidades {nome} ocupam "
                f"uma posição definida.",
                f"Considere a posição das necessidades {nome} na "
                f"hierarquia proposta por Maslow.",
            ]
            PER = ["Qual posição elas ocupam?",
                   "Assinale a alternativa que indica sua posição.",
                   "Elas correspondem ao:"]
        explicacao = (
            f"As necessidades {nome} ocupam o {nivel}º nível da "
            f"hierarquia de Maslow e abrangem {exemplos}.\n\n"
            f"A ordem, de baixo para cima, é: fisiológicas, de "
            f"segurança, sociais, de estima e de autorrealização. Um "
            f"nível só passa a motivar quando o anterior está "
            f"razoavelmente atendido."
        )
        fato = f"maslow:{submodo}:{nome}"
    else:
        teoria, autor, tese = rng.choice(TEORIAS_MOTIVACAO)
        if modo == "autor":
            correta = autor
            distratores = [t[1] for t in TEORIAS_MOTIVACAO if t[1] != autor]
            distratores += ["David McClelland", "Clayton Alderfer",
                            "Edwin Locke"]
            CEN = [
                f"Entre as teorias da motivação encontra-se a {teoria}.",
                f"Em uma revisão sobre motivação no trabalho, discute-se "
                f"a {teoria}.",
            ]
            PER = ["Quem a formulou?",
                   "Assinale a alternativa com seu autor.",
                   "Seu autor é:"]
        else:
            correta = tese
            distratores = [t[2] for t in TEORIAS_MOTIVACAO if t[2] != tese]
            distratores += [
                "a motivação decorre exclusivamente da remuneração "
                "recebida pelo trabalhador",
            ]
            CEN = [
                f"Considere a {teoria}, no estudo da motivação no "
                f"trabalho.",
                f"Em uma formação sobre gestão de pessoas, apresenta-se "
                f"a {teoria}.",
            ]
            PER = ["Qual é a sua tese central?",
                   "Assinale a alternativa que resume seu argumento.",
                   "Essa teoria sustenta que:"]
        explicacao = (
            f"A {teoria}, de {autor}, sustenta que {tese}."
        )
        fato = f"motivacao:{modo}:{teoria}"

    cen = rng.choice(CEN)
    enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
    return _montar(enunciado, correta, distratores, explicacao,
                   "Administração (gestão de pessoas)", rng, str, "textual",
                   fato=fato)


# ══════════════════════════════════════════════════════════
#  CATÁLOGO
# ══════════════════════════════════════════════════════════

TEMPLATES_ADMINISTRACAO = {
    "margem_contribuicao": gerar_margem_contribuicao,
    "ponto_equilibrio":    gerar_ponto_equilibrio,
    "markup":              gerar_markup,
    "custeio":             gerar_custeio,
    "liquidez":            gerar_liquidez,
    "rentabilidade":       gerar_rentabilidade,
    "giro_estoque":        gerar_giro_estoque,
    "payback":             gerar_payback,
    "vpl":                 gerar_vpl,
    "depreciacao":         gerar_depreciacao,
    "escolas":             gerar_escolas,
    "funcoes":             gerar_funcoes,
    "estruturas":          gerar_estruturas,
    "estrategia":          gerar_estrategia,
    "motivacao":           gerar_motivacao,
}

TOPICOS_ADMINISTRACAO = {
    "custos":       ["margem_contribuicao", "ponto_equilibrio", "custeio"],
    "precos":       ["markup"],
    "contabilidade": ["liquidez", "rentabilidade", "depreciacao"],
    "financas":     ["payback", "vpl", "rentabilidade"],
    "estoques":     ["giro_estoque"],
    "teorias":      ["escolas", "funcoes"],
    "organizacao":  ["estruturas", "funcoes"],
    "estrategia":   ["estrategia"],
    "pessoas":      ["motivacao"],
}

# (chave, rótulo legível, nível, área) — para o app montar os botões
CATALOGO = [
    ("margem_contribuicao", "Margem de contribuição",   "superior", "custos"),
    ("ponto_equilibrio",    "Ponto de equilíbrio",      "superior", "custos"),
    ("custeio",             "Custeio por absorção e variável",
                                                        "superior", "custos"),
    ("markup",              "Markup e formação de preço", "superior",
                                                                    "preços"),
    ("liquidez",            "Índices de liquidez",      "superior",
                                                        "contabilidade"),
    ("rentabilidade",       "Rentabilidade (ROA, ROE, margem)", "superior",
                                                        "contabilidade"),
    ("depreciacao",         "Depreciação",              "superior",
                                                        "contabilidade"),
    ("giro_estoque",        "Giro e prazo de estoque",  "superior",
                                                        "estoques"),
    ("payback",             "Payback simples",          "superior",
                                                        "investimentos"),
    ("vpl",                 "Valor presente líquido",   "superior",
                                                        "investimentos"),
    ("escolas",             "Escolas da administração", "superior",
                                                        "teorias"),
    ("funcoes",             "Funções administrativas",  "superior",
                                                        "teorias"),
    ("estruturas",          "Estruturas organizacionais", "superior",
                                                        "organização"),
    ("estrategia",          "Planejamento estratégico", "superior",
                                                        "estratégia"),
    ("motivacao",           "Motivação e liderança",    "superior",
                                                        "pessoas"),
]


def listar_topicos(nivel: str = None):
    """Catálogo para o app montar os botões de 'gerar questão de X'."""
    return [
        {"chave": ch, "rotulo": rot, "nivel": niv, "area": area}
        for ch, rot, niv, area in CATALOGO
        if nivel is None or niv == nivel
    ]


PALAVRAS_CHAVE = {
    "margem_contribuicao": ["margem de contribuicao", "custo variavel",
                            "preco de venda"],
    "ponto_equilibrio":    ["ponto de equilibrio", "break even",
                            "custo fixo", "margem de contribuicao"],
    "markup":              ["markup", "formacao de preco", "preco de venda"],
    "custeio":             ["custeio por absorcao", "custeio variavel",
                            "custo unitario", "rateio"],
    "liquidez":            ["liquidez", "liquidez corrente", "liquidez seca",
                            "analise de balanco"],
    "rentabilidade":       ["rentabilidade", "roe", "roa", "margem liquida",
                            "retorno sobre o ativo"],
    "giro_estoque":        ["giro de estoque", "prazo medio de estocagem",
                            "cmv", "estoque medio"],
    "payback":             ["payback", "prazo de retorno",
                            "analise de investimento"],
    "vpl":                 ["valor presente liquido", "vpl", "fluxo de caixa",
                            "taxa minima de atratividade"],
    "depreciacao":         ["depreciacao", "vida util", "valor residual",
                            "quotas constantes"],
    "escolas":             ["taylor", "fayol", "escolas da administracao",
                            "teoria geral da administracao", "burocracia"],
    "funcoes":             ["funcoes administrativas", "planejar organizar",
                            "processo administrativo", "podc"],
    "estruturas":          ["estrutura organizacional", "matricial",
                            "departamentalizacao", "organograma"],
    "estrategia":          ["swot", "cinco forcas", "porter", "bsc",
                            "balanced scorecard", "planejamento estrategico"],
    "motivacao":           ["maslow", "herzberg", "mcgregor", "vroom",
                            "motivacao", "gestao de pessoas"],
}


def templates_para_topicos(termos):
    """Casa palavras-chave de um índice com os templates daqui."""
    alvo = {_normalizar(t) for t in termos or []}
    escolhidos = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        if any(any(c in a or a in c for a in alvo) for c in chaves):
            escolhidos.append(nome)
    return escolhidos


# ══════════════════════════════════════════════════════════
#  LOTE
# ══════════════════════════════════════════════════════════

def gerar_lote(quantidade: int = 10, seed: int = None,
               topico: str = None, templates: list = None):
    """
    Gera um lote, sem repetir enunciado nem fato.

    A fila avança a cada TENTATIVA, não a cada questão aceita — se
    avançasse só nas aceitas, um template que falhasse o veto travaria
    a rotação e o lote sairia desequilibrado.
    """
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_ADMINISTRACAO)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_ADMINISTRACAO]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico)
        por_area = {_normalizar(k): v for k, v in TOPICOS_ADMINISTRACAO.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_ADMINISTRACAO]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados
    if not disponiveis:
        return []

    rng.shuffle(disponiveis)

    # Teto POR TEMPLATE, não por área: "custos" abriga margem, ponto de
    # equilíbrio e custeio, e contar por área deixaria seis questões de
    # custos passarem.
    teto = math.ceil(quantidade / len(disponiveis)) + 1

    questoes, vistos, fatos = [], set(), set()
    por_template = {n: 0 for n in disponiveis}
    posicao = 0
    limite = max(quantidade * 40, 400)

    for tentativa in range(limite):
        if len(questoes) >= quantidade:
            break
        nome = disponiveis[posicao % len(disponiveis)]
        posicao += 1

        if por_template[nome] >= teto and tentativa < limite * 0.75:
            continue
        try:
            q = TEMPLATES_ADMINISTRACAO[nome](rng)
        except Exception:
            continue
        if not q:
            continue
        if q["enunciado"] in vistos:
            continue
        if q.get("_fato") in fatos and tentativa < limite * 0.9:
            continue

        vistos.add(q["enunciado"])
        fatos.add(q.get("_fato"))
        por_template[nome] += 1
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade: int = 10, seed: int = None,
                   topico: str = None, templates: list = None):
    """Formato que a API espera. Metadados internos ficam de fora."""
    lote = gerar_lote(quantidade, seed=seed, topico=topico,
                      templates=templates)
    questoes, gabarito = [], []
    for q in lote:
        questoes.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": False,
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    alvo = sys.argv[2] if len(sys.argv) > 2 else None
    print("═" * 66)
    print("  GERADOR DE ADMINISTRAÇÃO")
    print("═" * 66)
    for q in gerar_lote(n, seed=2026, topico=alvo):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}\n")
        for L, t in q["alternativas"].items():
            print(f"      {L}) {t}{'  ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("\n" + "═" * 66)
