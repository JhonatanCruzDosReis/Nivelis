"""
=============================================================
  GERADOR DE MATEMÁTICA BÁSICA
=============================================================
  Fundamental, médio e ENEM.

  DIFERENÇA EM RELAÇÃO AO gerador_procedural.py

  Aquele cobre combinatória e probabilidade em nível
  superior. Este cobre a base — porcentagem, regra de três,
  equações, juros, geometria — para alunos da rede pública.

  CATÁLOGO POR TÓPICO

  Cada template tem RÓTULO legível e NÍVEL declarado, para o
  app montar botões do tipo "gerar questão de equação do
  segundo grau". Ver CATALOGO no final do arquivo.

  As respostas são CALCULADAS, nunca tabeladas.

  USO:
      from gerador_basica import gerar_lote, gerar_para_api
      gerar_lote(5, templates=["equacao_2grau"])
=============================================================
"""

import random
import re
import unicodedata
from fractions import Fraction

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _num(v) -> str:
    """Formata número no padrão brasileiro."""
    if isinstance(v, Fraction):
        v = v.numerator if v.denominator == 1 else float(v)
    if isinstance(v, float) and abs(v - round(v)) < 1e-9:
        v = int(round(v))
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _real(v) -> str:
    """Formata valor monetário."""
    return "R$ " + f"{float(v):,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _pct(v) -> str:
    """Formata porcentagem."""
    return _num(v) + "%"


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


NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela",
         "Heitor", "Isabela", "João", "Larissa", "Marcos", "Natália",
         "Otávio", "Paula", "Rafael", "Sofia", "Tiago", "Vanessa", "Wesley"]


# ══════════════════════════════════════════════════════════
#  ARITMÉTICA E PROPORÇÃO
# ══════════════════════════════════════════════════════════

def gerar_porcentagem(rng):
    """Porcentagem de um valor — nível fundamental."""
    base = rng.choice([80, 120, 150, 200, 240, 300, 360, 450, 500, 800])
    taxa = rng.choice([5, 10, 12, 15, 20, 25, 30, 40, 45])
    resultado = base * taxa / 100

    # Cenários que CONTAM pessoas ou objetos exigem resultado inteiro:
    # "202,5 alunos" não existe. Se a combinação não fecha, o template
    # devolve None e o lote re-sorteia.
    inteiro = float(resultado).is_integer()

    nome = rng.choice(NOMES)
    # A situação vem DENTRO do cenário, não colada na frente: uma
    # abertura genérica não conversa com o corpo do problema e deixa
    # o enunciado maior sem ficar melhor.
    CENARIOS = [
        f"Em uma promoção de fim de estação, uma loja de bairro "
        f"reduziu o preço de várias peças. Um produto que custava "
        f"{_real(base)} recebeu {taxa}% de desconto.",
        f"{nome} começou a organizar as finanças este ano e definiu "
        f"uma meta: separar parte do salário todo mês. Recebendo "
        f"{_real(base)} mensais, decidiu guardar {taxa}% desse valor.",
        f"A direção de uma escola levantou a participação dos "
        f"estudantes nas atividades do contraturno. Dos {base} alunos "
        f"matriculados, {taxa}% frequentam o grêmio estudantil.",
        f"Durante um período de estiagem, a companhia de abastecimento "
        f"passou a divulgar o nível dos reservatórios. Um deles, com "
        f"capacidade para {base} litros, encontra-se {taxa}% cheio.",
    ]
    # Se o resultado não é inteiro, ficam de fora os cenários que
    # contam unidades indivisíveis.
    if not inteiro:
        CENARIOS = [x for x in CENARIOS if "alunos" not in x]
    cenario = rng.choice(CENARIOS)
    if "desconto" in cenario:
        pergunta = "O valor do desconto é de:"
        formatador = _real
    elif "guarda" in cenario:
        pergunta = "O valor guardado por mês é de:"
        formatador = _real
    elif "alunos" in cenario:
        pergunta = "O número de alunos que participam do grêmio é:"
        formatador = _num
    else:
        pergunta = "A quantidade de água no reservatório é de:"
        formatador = lambda v: _num(v) + " litros"

    enunciado = f"{cenario} {pergunta}"
    correta = resultado
    distratores = [
        base - resultado,          # confundiu parte com o restante
        base * taxa / 1000,        # errou a vírgula
        base * taxa / 10,
        base + resultado,
        resultado * 2,
        taxa,
    ]
    distratores = [d for d in distratores if d != correta]

    # Num cenário que CONTA pessoas, nem o gabarito nem os distratores
    # podem ser fracionários: "22,50 alunos" denuncia a alternativa
    # falsa de imediato, e o aluno acerta sem calcular.
    if "alunos" in cenario:
        distratores = [d for d in distratores if float(d).is_integer()]

    explicacao = (
        f"Para calcular {taxa}% de {_num(base)}, multiplica-se o valor "
        f"pela taxa dividida por 100: {_num(base)} × {taxa}/100 = "
        f"{_num(base)} × {_num(taxa/100)} = {_num(resultado)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (porcentagem)", rng, formatador)
    if q:
        q["_grupo"] = "porcentagem"
    return q


def gerar_desconto_acrescimo(rng):
    """Preço final após desconto ou acréscimo — nível fundamental."""
    preco = rng.choice([60, 80, 120, 150, 200, 250, 320, 400])
    taxa = rng.choice([10, 15, 20, 25, 30, 40])
    tipo = rng.choice(["desconto", "acréscimo"])
    if tipo == "desconto":
        final = preco * (1 - taxa / 100)
    else:
        final = preco * (1 + taxa / 100)

    nome = rng.choice(NOMES)
    CENARIOS = [
        f"Uma loja de departamentos anunciou reajuste de preços após "
        f"mudança no custo do fornecedor. Um produto que custava "
        f"{_real(preco)} sofreu {tipo} de {taxa}%.",
        f"{nome} pesquisou preços em três lojas antes de fechar a "
        f"compra. Na escolhida, o item sai por {_real(preco)}, com "
        f"{tipo} de {taxa}% aplicado no caixa.",
        f"O setor de compras de uma empresa revisa a tabela de preços "
        f"a cada trimestre. Uma mercadoria de {_real(preco)} recebeu "
        f"{tipo} de {taxa}% na última revisão.",
        f"Ao conferir a nota fiscal, um cliente notou que o valor "
        f"final diferia do anunciado. O produto custava "
        f"{_real(preco)} e sofreu {tipo} de {taxa}%.",
    ]
    COMANDOS_PRECO = [
        "O preço final é de:",
        "O valor a pagar é de:",
        "Qual o preço final?",
        "O preço após a operação corresponde a:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS_PRECO)}"

    correta = final
    outro = preco * (1 + taxa / 100) if tipo == "desconto" else preco * (1 - taxa / 100)
    distratores = [
        outro,                     # aplicou a operação inversa
        preco * taxa / 100,        # respondeu só o valor do desconto
        preco,                     # esqueceu de aplicar
        preco - taxa,              # subtraiu a taxa em vez do percentual
        final + taxa,
    ]
    distratores = [d for d in distratores if abs(d - correta) > 0.005]

    sinal = "−" if tipo == "desconto" else "+"
    fator = (100 - taxa) / 100 if tipo == "desconto" else (100 + taxa) / 100
    explicacao = (
        f"Um {tipo} de {taxa}% equivale a multiplicar o preço pelo fator "
        f"(100 {sinal} {taxa})/100 = {_num(fator)}. "
        f"Então: {_real(preco)} × {_num(fator)} = {_real(final)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (porcentagem)", rng, _real)
    if q:
        q["_grupo"] = "desconto"
    return q


def gerar_regra_de_tres(rng):
    """Regra de três simples e direta — nível fundamental."""
    a = rng.choice([2, 3, 4, 5, 6, 8])
    b = rng.choice([12, 15, 18, 20, 24, 30, 36, 40])
    c = rng.choice([7, 9, 10, 12, 15, 20])
    resultado = Fraction(b * c, a)
    if resultado.denominator != 1:
        return None

    resultado = int(resultado)
    nome = rng.choice(NOMES)
    CENARIOS = [
        (f"Uma escola vai distribuir material escolar aos alunos e "
         f"pediu orçamento à papelaria. Foi informada de que {a} "
         f"cadernos custam {_real(b)}. Mantida a proporção, quanto "
         f"custarão {c} cadernos do mesmo tipo?", _real),
        (f"Uma fábrica recebeu encomenda maior que a habitual e "
         f"precisa estimar a produção. Sabe-se que a máquina produz "
         f"{b} peças em {a} horas. Mantendo o mesmo ritmo, quantas "
         f"peças ela produzirá em {c} horas?",
         lambda v: _num(v) + " peças"),
        (f"{nome} trabalha com entregas e acompanha o consumo do "
         f"veículo para planejar a rota da semana. O carro percorre "
         f"{b} quilômetros com {a} litros de combustível. Com {c} "
         f"litros, quantos quilômetros percorrerá?",
         lambda v: _num(v) + " km"),
        (f"Uma cozinha comunitária vai ampliar a produção para "
         f"atender mais famílias. A receita indica que, para {a} "
         f"bolos, são necessários {b} ovos. Quantos ovos serão "
         f"necessários para {c} bolos?",
         lambda v: _num(v) + " ovos"),
    ]
    enunciado, formatador = rng.choice(CENARIOS)

    correta = resultado
    # a·c/b e a·b/c produzem valores de ordem muito menor que o
    # gabarito quando b é grande. Os distratores abaixo ficam na faixa.
    distratores = [
        b + c - a,
        resultado + a,
        resultado - a,
        resultado + b,
        Fraction(b * (c + 1), a),
        Fraction(b * (c - 1), a) if c > 1 else resultado * 2,
    ]
    distratores = [int(d) if isinstance(d, Fraction) and d.denominator == 1
                   else d for d in distratores]
    distratores = [d for d in distratores
                   if isinstance(d, int) and d > 0 and d != correta]

    explicacao = (
        f"Monta-se a proporção {a} está para {_num(b)} assim como {c} "
        f"está para x. Multiplicando em cruz: {a}·x = {_num(b)}·{c}, "
        f"logo x = {_num(b*c)}/{a} = {_num(resultado)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (regra de três)", rng, formatador)
    if q:
        q["_grupo"] = "regra_de_tres"
    return q


# ══════════════════════════════════════════════════════════
#  EQUAÇÕES
# ══════════════════════════════════════════════════════════

def gerar_equacao_1grau(rng):
    """Equação do primeiro grau — nível fundamental."""
    x = rng.choice([2, 3, 4, 5, 6, 7, 8, 10, 12, -3, -4, -5])
    a = rng.choice([2, 3, 4, 5, 6, 7])
    b = rng.choice([1, 2, 3, 5, 7, 10, 12, 15])
    c = a * x + b

    forma = rng.choice(["direta", "com_termo", "contextualizada"])
    if forma == "direta":
        enunciado = (f"Em uma atividade de revisão, o professor "
                     f"apresentou à turma uma equação do primeiro grau "
                     f"e pediu que os alunos isolassem a incógnita, "
                     f"justificando cada passo. A equação proposta foi "
                     f"{a}x + {b} = {c}. O valor de x é:")
    elif forma == "com_termo":
        d = rng.choice([2, 3, 4])
        e = (a + d) * x + b - d * x
        enunciado = (f"Um exercício de vestibular apresenta uma "
                     f"equação com a incógnita nos dois membros, o que "
                     f"exige agrupar os termos semelhantes antes de "
                     f"resolver. A equação é {a+d}x + {b} = {d}x + "
                     f"{_num(e)}. O valor de x é:")
        c = e
    else:
        nome = rng.choice(NOMES)
        enunciado = (f"Durante uma gincana de matemática, cada equipe "
                     f"recebeu uma pista para descobrir um número "
                     f"secreto. A pista da equipe de {nome} dizia: o "
                     f"número, multiplicado por {a} e somado a {b}, "
                     f"resulta em {_num(c)}. O número secreto é:")

    correta = x
    distratores = [
        c - b,               # esqueceu de dividir
        (c + b) / a if (c + b) % a == 0 else c + b,
        c / a if c % a == 0 else c - a,
        -x,
        x + 1,
        x - 1,
        b,
    ]
    distratores = [int(d) for d in distratores
                   if isinstance(d, (int, float)) and float(d).is_integer()
                   and int(d) != correta]

    explicacao = (
        f"Isola-se o termo com x. De {a}x + {b} = {_num(c)}, "
        f"passa-se {b} para o outro lado: {a}x = {_num(c)} − {b} = "
        f"{_num(c - b)}. Dividindo por {a}: x = {_num(c-b)}/{a} = {x}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (equação do 1º grau)", rng, _num)
    if q:
        q["_grupo"] = "equacao_1grau"
    return q


def gerar_equacao_2grau(rng):
    """
    Equação do segundo grau — nível médio.

    As raízes são escolhidas primeiro, e os coeficientes derivados
    delas: garante raízes inteiras e discriminante perfeito.
    """
    r1 = rng.choice([1, 2, 3, 4, 5, 6, -1, -2, -3, -4, -5])
    r2 = rng.choice([1, 2, 3, 4, 5, 6, -1, -2, -3, -4, -5])
    # x² − (r1+r2)x + r1·r2 = 0
    b = -(r1 + r2)
    cc = r1 * r2
    delta = b * b - 4 * cc

    def _termo(coef, var):
        if coef == 0:
            return ""
        sinal = " + " if coef > 0 else " − "
        val = abs(coef)
        corpo = var if val == 1 and var else f"{val}{var}"
        return f"{sinal}{corpo}"

    eq = "x²" + _termo(b, "x") + _termo(cc, "")
    eq = eq.replace("x² + ", "x² + ").strip()

    modo = rng.choice(["raizes", "soma", "produto", "delta"])
    if modo == "raizes":
        enunciado = (f"Ao estudar equações do segundo grau, a turma "
                     f"aprendeu que a soma e o produto das raízes se "
                     f"obtêm diretamente dos coeficientes, sem "
                     f"necessidade de aplicar a fórmula resolutiva. "
                     f"Considere a equação {eq} = 0. Suas raízes são:")
        correta = f"{min(r1,r2)} e {max(r1,r2)}"
        distratores = [
            f"{-min(r1,r2)} e {-max(r1,r2)}",
            f"{min(r1,r2)} e {-max(r1,r2)}",
            f"{min(r1,r2)+1} e {max(r1,r2)+1}",
            f"{min(r1,r2)-1} e {max(r1,r2)-1}",
            f"{b} e {cc}",
        ]
        explicacao = (
            f"Pela soma e produto: a soma das raízes é −b/a = "
            f"{-b}, e o produto é c/a = {cc}. Os números que somam "
            f"{-b} e multiplicam {cc} são {min(r1,r2)} e {max(r1,r2)}. "
            f"As raízes são {min(r1,r2)} e {max(r1,r2)}."
        )
        formatador = str
    elif modo == "soma":
        enunciado = (f"Uma questão de prova pede que o candidato "
                     f"relacione os coeficientes de uma equação "
                     f"quadrática às suas raízes, sem resolvê-la. "
                     f"Na equação {eq} = 0, a soma das raízes é:")
        correta = r1 + r2
        distratores = [b, cc, r1 * r2, -(r1 + r2) * 2, r1 + r2 + 1,
                       r1 + r2 - 1]
        explicacao = (
            f"A soma das raízes de ax² + bx + c = 0 é dada por −b/a. "
            f"Aqui a = 1 e b = {b}, então a soma é −({b})/1 = {r1+r2}."
        )
        formatador = _num
    elif modo == "produto":
        enunciado = (f"Em uma lista de exercícios sobre relações "
                     f"entre coeficientes e raízes, aparece a seguinte "
                     f"equação do segundo grau: {eq} = 0. "
                     f"O produto das raízes é:")
        correta = r1 * r2
        distratores = [b, -cc, r1 + r2, cc * 2, cc + 1, cc - 1]
        explicacao = (
            f"O produto das raízes de ax² + bx + c = 0 é dado por c/a. "
            f"Aqui a = 1 e c = {cc}, então o produto é {cc}/1 = {cc}."
        )
        formatador = _num
    else:
        enunciado = (f"O discriminante de uma equação do segundo grau "
                     f"informa quantas raízes reais ela possui, antes "
                     f"mesmo de resolvê-la. Considere a equação "
                     f"{eq} = 0. O valor do discriminante é:")
        correta = delta
        distratores = [b * b + 4 * cc, b * b - cc, -delta if delta else 1,
                       b * b, 4 * cc, delta + 1]
        explicacao = (
            f"O discriminante é Δ = b² − 4ac. Com a = 1, b = {b} e "
            f"c = {cc}: Δ = ({b})² − 4·1·({cc}) = {b*b} − {4*cc} = "
            f"{delta}."
        )
        formatador = _num

    distratores = [d for d in distratores if d != correta]
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (equação do 2º grau)", rng, formatador)
    if q:
        q["_grupo"] = f"equacao_2grau:{modo}"
    return q


def gerar_sistema_equacoes(rng):
    """Sistema de duas equações — nível fundamental e médio."""
    x = rng.choice([2, 3, 4, 5, 6, 7, 8])
    y = rng.choice([1, 2, 3, 4, 5, 6, 9])
    a1, b1 = rng.choice([(1, 1), (2, 1), (1, 2), (3, 1), (2, 3)])
    a2, b2 = rng.choice([(1, -1), (3, 2), (1, 3), (2, -1), (4, 1)])
    if a1 * b2 - a2 * b1 == 0:
        return None
    c1 = a1 * x + b1 * y
    c2 = a2 * x + b2 * y

    def _eq(a, b, c):
        sb = " + " if b > 0 else " − "
        vb = abs(b)
        return (f"{a if a != 1 else ''}x{sb}"
                f"{vb if vb != 1 else ''}y = {_num(c)}")

    nome = rng.choice(NOMES)
    CENARIOS = [
        f"Muitos problemas do cotidiano se traduzem em duas condições "
        f"que precisam ser satisfeitas ao mesmo tempo, o que leva a um "
        f"sistema de equações. Considere o sistema formado por "
        f"{_eq(a1,b1,c1)} e {_eq(a2,b2,c2)}.",
        f"Em uma atividade em dupla, {nome} e o colega receberam um "
        f"sistema de duas equações e duas incógnitas, com liberdade "
        f"para escolher o método de resolução. O sistema é "
        f"{_eq(a1,b1,c1)} e {_eq(a2,b2,c2)}.",
        f"Uma questão de concurso apresenta duas relações entre as "
        f"mesmas grandezas e pede o par que satisfaz ambas: "
        f"{_eq(a1,b1,c1)} e {_eq(a2,b2,c2)}.",
    ]
    COMANDOS_SIS = [
        "A solução é:",
        "O par que satisfaz as duas equações é:",
        "Qual a solução do sistema?",
        "Os valores de x e y são:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS_SIS)}"

    correta = f"x = {x} e y = {y}"
    distratores = [
        f"x = {y} e y = {x}",
        f"x = {x+1} e y = {y-1}",
        f"x = {x-1} e y = {y+1}",
        f"x = {-x} e y = {-y}",
        f"x = {x} e y = {y+2}",
        f"x = {x+2} e y = {y-2}",
        f"x = {x-2} e y = {y+3}",
        f"x = {y} e y = {-x}",
    ]
    explicacao = (
        f"Resolvendo o sistema por substituição ou adição, obtém-se "
        f"x = {x} e y = {y}. Conferindo na primeira equação: "
        f"{a1}·{x} + ({b1})·{y} = {_num(c1)} ✓. Na segunda: "
        f"{a2}·{x} + ({b2})·{y} = {_num(c2)} ✓. A solução é x = {x} e "
        f"y = {y}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (sistema de equações)", rng)
    if q:
        q["_grupo"] = "sistema"
    return q


# ══════════════════════════════════════════════════════════
#  MATEMÁTICA FINANCEIRA
# ══════════════════════════════════════════════════════════

def gerar_juros_simples(rng):
    """Juros simples — J = C·i·t. Nível fundamental e médio."""
    capital = rng.choice([500, 800, 1000, 1200, 1500, 2000, 2500, 3000])
    taxa = rng.choice([1, 2, 2.5, 3, 4, 5])
    tempo = rng.choice([4, 6, 8, 10, 12, 15, 18, 24])
    juros = capital * taxa / 100 * tempo
    montante = capital + juros

    nome = rng.choice(NOMES)
    pede_montante = rng.random() < 0.5
    CENARIOS = [
        f"{nome} recebeu um valor extra no fim do ano e decidiu "
        f"aplicá-lo em vez de gastar. Investiu {_real(capital)} em uma "
        f"modalidade que rende juros simples de {_num(taxa)}% ao mês, "
        f"pelo prazo de {tempo} meses.",
        f"Uma cooperativa de crédito oferece aos associados uma "
        f"aplicação com remuneração fixa. Um capital de "
        f"{_real(capital)} foi investido a juros simples de "
        f"{_num(taxa)}% ao mês, durante {tempo} meses.",
        f"Um pequeno comerciante precisou de capital de giro e tomou "
        f"um empréstimo de {_real(capital)}, com juros simples de "
        f"{_num(taxa)}% ao mês, a ser quitado em {tempo} meses.",
        f"Durante uma feira de educação financeira, os visitantes "
        f"simularam aplicações. Uma delas partia de {_real(capital)} "
        f"a juros simples de {_num(taxa)}% ao mês, por {tempo} meses.",
    ]
    pergunta = ("O montante ao final do período é de:" if pede_montante
                else "O total de juros pago no período é de:")
    enunciado = f"{rng.choice(CENARIOS)} {pergunta}"

    correta = montante if pede_montante else juros
    # Todos os distratores ficam na mesma ORDEM DE GRANDEZA do gabarito:
    # capital·tempo/100 gerava valor 108 vezes menor, descartável de
    # imediato — o teste 9 acusa isso.
    distratores = [
        juros if pede_montante else montante,
        capital * taxa / 100 * tempo * 2,   # dobrou o período
        capital + capital * taxa / 100,     # aplicou só um período
        (montante if pede_montante else juros) * 1.5,
        capital * taxa / 100 * (tempo + 1),
        capital * taxa / 100 * (tempo - 1) if tempo > 1 else capital * 1.1,
    ]
    # Dois distratores próximos demais confundem sem ensinar: o de juros
    # compostos (capital·(1+i)^t) caía a menos de 0,5% de outro valor da
    # lista, e o teste 9 acusa. Aqui a separação é garantida.
    distratores = [d for d in distratores if abs(d - correta) > 0.005]
    unicos = []
    for d in sorted(distratores):
        if all(abs(d - u) / max(abs(u), 1) > 0.02 for u in unicos):
            unicos.append(d)
    distratores = unicos

    explicacao = (
        f"Nos juros simples, J = C·i·t, com a taxa em forma decimal. "
        f"Aqui: J = {_num(capital)} × {_num(taxa/100)} × {tempo} = "
        f"{_real(juros)}. "
    )
    if pede_montante:
        explicacao += (f"O montante é M = C + J = {_real(capital)} + "
                       f"{_real(juros)} = {_real(montante)}.")
    else:
        explicacao += f"O total de juros é {_real(juros)}."
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (juros simples)", rng, _real)
    if q:
        q["_grupo"] = "juros_simples"
    return q


def gerar_juros_compostos(rng):
    """Juros compostos — M = C·(1+i)^t. Nível médio e ENEM."""
    capital = rng.choice([1000, 2000, 4000, 5000, 8000, 10000])
    taxa = rng.choice([10, 20, 25, 50])
    tempo = rng.choice([2, 3])
    montante = capital * (1 + taxa / 100) ** tempo
    juros = montante - capital
    simples = capital * (1 + taxa / 100 * tempo)

    nome = rng.choice(NOMES)
    CENARIOS = [
        f"Ao comparar as opções oferecidas pelo banco, {nome} optou "
        f"pela aplicação com capitalização composta, em que os juros "
        f"de cada período incidem sobre o montante acumulado. Aplicou "
        f"{_real(capital)} a {taxa}% ao ano, por {tempo} anos.",
        f"Um fundo de investimento divulga rendimento anual composto "
        f"de {taxa}%. Um cotista aplicou {_real(capital)} e manteve o "
        f"valor investido por {tempo} anos, sem resgates.",
        f"Uma família começou a poupar para a entrada de um imóvel e "
        f"escolheu um produto com juros compostos. O aporte inicial "
        f"foi de {_real(capital)}, com rendimento de {taxa}% ao ano "
        f"durante {tempo} anos.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} O montante final é de:"

    correta = montante
    # capital·(i)^t gera valor 1.331 vezes menor que o gabarito — um
    # distrator descartável de imediato, que o teste 9 acusa.
    distratores = [
        simples,                       # aplicou juros simples
        capital * (1 + taxa / 100),    # esqueceu o expoente
        juros,                         # respondeu só o rendimento
        capital + capital * taxa / 100 * tempo,
        montante * (1 + taxa / 100),   # aplicou um período a mais
        capital * (1 + taxa / 100) ** (tempo - 1),
        capital * (1 + taxa / 100) ** (tempo + 1),  # um período a mais
        montante + juros,                           # somou o juro de novo
        capital * (1 + taxa * tempo / 100) * 1.1,
    ]
    distratores = [d for d in distratores if abs(d - correta) > 0.005]

    passos = " × ".join([_num(1 + taxa/100)] * tempo)
    # A explicação TERMINA no resultado: o teste de português verifica
    # isso, e o aluno lê a última linha.
    explicacao = (
        f"Nos juros compostos, M = C·(1 + i)^t, e o que caracteriza a "
        f"capitalização composta é que os juros incidem sobre o montante "
        f"acumulado — a juros simples o resultado seria apenas "
        f"{_real(simples)}. Aqui: M = {_num(capital)} × ({passos}) = "
        f"{_num(capital)} × {_num((1+taxa/100)**tempo)} = "
        f"{_real(montante)}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (juros compostos)", rng, _real)
    if q:
        q["_grupo"] = "juros_compostos"
    return q


# ══════════════════════════════════════════════════════════
#  ESTATÍSTICA BÁSICA
# ══════════════════════════════════════════════════════════

def gerar_media_moda_mediana(rng):
    """Média, moda e mediana — nível fundamental e ENEM."""
    from collections import Counter

    # O conjunto é CONSTRUÍDO com moda única, em vez de sorteado e
    # corrigido depois. A tentativa anterior — dados[0] = dados[1] —
    # não resolvia quando os dois primeiros já eram iguais, e saíam
    # conjuntos bimodais como (2, 2, 3, 5, 6, 6, 8): tanto o 2 quanto
    # o 6 seriam moda, e a questão ficava sem resposta única.
    n = rng.choice([5, 7, 9])
    universo = [2, 3, 4, 5, 6, 7, 8, 9, 10]
    rng.shuffle(universo)

    moda = universo[0]
    repeticoes = 3 if n >= 7 else 2          # a moda aparece mais vezes
    resto = universo[1:1 + (n - repeticoes)] # os demais, todos distintos
    dados = sorted([moda] * repeticoes + resto)

    cont = Counter(dados)
    # Confere: exatamente um valor com a frequência máxima
    if list(cont.values()).count(max(cont.values())) != 1:
        return None

    medida = rng.choice(["média", "mediana", "moda"])
    if medida == "média":
        correta = Fraction(sum(dados), len(dados))
        valor_txt = _num(float(correta))
    elif medida == "mediana":
        correta = Fraction(dados[len(dados) // 2])
        valor_txt = _num(correta)
    else:
        correta = Fraction(cont.most_common(1)[0][0])
        valor_txt = _num(correta)

    lista = ", ".join(str(d) for d in dados)
    nome = rng.choice(NOMES)
    CENARIOS = [
        f"A coordenação de uma escola acompanha o desempenho dos "
        f"alunos ao longo do bimestre para definir quem precisa de "
        f"reforço. As notas de {nome} nas {n} avaliações do período "
        f"foram: {lista}.",
        f"Um professor tabulou o número de acertos da turma para "
        f"identificar os conteúdos que precisam ser revistos. Em {n} "
        f"provas aplicadas, os resultados de um aluno foram: {lista}.",
        f"Um laboratório repete a mesma medição várias vezes para "
        f"avaliar a consistência do equipamento. Nas {n} leituras "
        f"realizadas, obteve-se: {lista}.",
        f"Uma equipe esportiva analisa os números da temporada antes "
        f"de definir a escalação. O aproveitamento de um atleta nas "
        f"{n} últimas partidas foi: {lista}.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} A {medida} desses valores é:"

    correta_f = float(correta)
    outras = {
        "média": float(Fraction(sum(dados), len(dados))),
        "mediana": float(dados[len(dados)//2]),
        "moda": float(cont.most_common(1)[0][0]),
    }
    distratores = [v for k, v in outras.items() if abs(v - correta_f) > 0.005]
    distratores += [float(max(dados)), float(min(dados)),
                    float(max(dados) - min(dados)),
                    round(correta_f + 1, 2)]
    distratores = [d for d in distratores if abs(d - correta_f) > 0.005]

    if medida == "média":
        detalhe = (f"soma-se tudo e divide-se pela quantidade: "
                   f"({' + '.join(str(d) for d in dados)}) / {n} = "
                   f"{sum(dados)}/{n} = {valor_txt}")
    elif medida == "mediana":
        detalhe = (f"ordenam-se os valores e toma-se o do meio. Com {n} "
                   f"valores, o do meio é o {n//2 + 1}º: {valor_txt}")
    else:
        detalhe = (f"identifica-se o valor mais frequente. Aqui, o "
                   f"{cont.most_common(1)[0][0]} aparece "
                   f"{cont.most_common(1)[0][1]} vezes: {valor_txt}")
    explicacao = f"Para calcular a {medida}, {detalhe}."

    q = _montar(enunciado, correta_f, distratores, explicacao,
                "Matemática básica (estatística)", rng, _num)
    if q:
        q["_grupo"] = f"estatistica:{medida}"
    return q


# ══════════════════════════════════════════════════════════
#  GEOMETRIA
# ══════════════════════════════════════════════════════════

def gerar_pitagoras(rng):
    """Teorema de Pitágoras — nível fundamental."""
    TERNOS = [(3,4,5), (6,8,10), (5,12,13), (9,12,15), (8,15,17),
              (12,16,20), (7,24,25), (20,21,29), (10,24,26)]
    a, b, c = rng.choice(TERNOS)
    pede = rng.choice(["hipotenusa", "cateto"])

    nome = rng.choice(NOMES)
    if pede == "hipotenusa":
        CENARIOS = [
            f"Uma marcenaria produz peças triangulares para reforçar "
            f"estruturas de madeira. Cada peça tem forma de triângulo "
            f"retângulo, com catetos medindo {a} cm e {b} cm.",
            f"A prefeitura vai construir uma rampa de acessibilidade "
            f"na entrada de um posto de saúde. O projeto forma um "
            f"triângulo retângulo cujos catetos medem {a} m e {b} m.",
            f"{nome} precisou trocar uma lâmpada do lado externo da "
            f"casa e apoiou a escada na parede, formando um triângulo "
            f"retângulo de catetos {a} m e {b} m.",
            f"Um terreno em declive foi dividido por uma cerca "
            f"diagonal, formando um triângulo retângulo de catetos "
            f"{a} m e {b} m.",
        ]
        pergunta = "A medida da hipotenusa é:"
        correta = c
        # |b − a| pode dar 1, valor absurdo diante de uma hipotenusa
        # de 29 — descartável de imediato. Substituído por erros reais.
        distratores = [a + b, c - 1, c + 1, (a + b) // 2,
                       c + 2, (a * a + b * b) // 10,
                       c - 2, a + b - 1, max(a, b) + 1]
        detalhe = (f"h² = {a}² + {b}² = {a*a} + {b*b} = {c*c}, logo "
                   f"h = √{c*c} = {c}")
    else:
        CENARIOS = [
            f"Uma peça metálica em forma de triângulo retângulo será "
            f"cortada a partir de uma chapa. O projeto indica "
            f"hipotenusa de {c} cm e um dos catetos com {a} cm.",
            f"Um poste foi fixado ao solo por um cabo de sustentação "
            f"esticado, formando um triângulo retângulo. O cabo, que é "
            f"a hipotenusa, mede {c} m, e a distância do ponto de "
            f"fixação até a base do poste é {a} m.",
            f"Ao projetar uma cobertura, o engenheiro calculou que a "
            f"estrutura formaria um triângulo retângulo com hipotenusa "
            f"de {c} m e um cateto de {a} m.",
        ]
        pergunta = "A medida do outro cateto é:"
        correta = b
        distratores = [c - a, c + a, b - 1, b + 1, (c + a) // 2]
        detalhe = (f"{a}² + x² = {c}², então x² = {c*c} − {a*a} = "
                   f"{c*c - a*a}, logo x = √{c*c-a*a} = {b}")

    # A unidade precisa vir do cenário SORTEADO, não de CENARIOS[0] —
    # que é sempre o primeiro da lista e tem "cm", produzindo
    # "catetos de 20 m" com alternativas em "cm".
    cenario = rng.choice(CENARIOS)
    unidade = "cm" if " cm" in cenario else "m"
    enunciado = f"{cenario} {pergunta}"
    distratores = [d for d in distratores if d > 0 and d != correta]

    explicacao = (
        f"Pelo teorema de Pitágoras, o quadrado da hipotenusa é igual à "
        f"soma dos quadrados dos catetos. Aqui: {detalhe}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (geometria)", rng,
                lambda v: f"{_num(v)} {unidade}")
    if q:
        q["_grupo"] = f"pitagoras:{pede}"
    return q


def gerar_area_figura(rng):
    """Área de figuras planas — nível fundamental."""
    figura = rng.choice(["retângulo", "triângulo", "quadrado", "círculo"])
    if figura == "retângulo":
        b, h = rng.choice([(6,4),(8,5),(10,7),(12,9),(15,8),(20,6)])
        area = b * h
        cenario = rng.choice([
            f"Uma família comprou um terreno retangular para "
            f"construir e precisa saber a área total antes de "
            f"contratar o projeto. O lote mede {b} metros de "
            f"comprimento por {h} metros de largura.",
            f"A direção de uma escola vai trocar o piso de uma sala "
            f"retangular e pediu orçamento à loja de materiais. A sala "
            f"mede {b} metros por {h} metros.",
            f"Uma empresa de paisagismo foi contratada para cobrir "
            f"com grama um jardim retangular de {b} metros por "
            f"{h} metros.",
            f"A prefeitura vai instalar piso emborrachado em uma "
            f"quadra poliesportiva que mede {b} metros de comprimento "
            f"por {h} metros de largura.",
        ])
        formula = f"área = base × altura = {b} × {h} = {area}"
        distratores = [2*(b+h), b+h, b*h//2, b*h*2, (b+h)//2,
                       b*h + b + h, (b+1)*h, b*(h+1)]
    elif figura == "triângulo":
        b, h = rng.choice([(6,4),(8,6),(10,8),(12,5),(14,6),(20,7)])
        area = b * h // 2
        cenario = rng.choice([
            f"Em uma aula de geometria, os alunos recortaram figuras "
            f"em cartolina para comparar áreas. Um dos triângulos "
            f"recortados tem base de {b} cm e altura de {h} cm.",
            f"Uma fábrica de embalagens produz peças triangulares "
            f"usadas como reforço nas caixas. Cada peça tem {b} cm de "
            f"base e {h} cm de altura.",
            f"Ao projetar um mosaico, um artesão calculou a área de "
            f"cada peça antes de encomendar o material. As peças "
            f"triangulares têm base de {b} cm e altura de {h} cm.",
        ])
        formula = f"área = (base × altura)/2 = ({b} × {h})/2 = {area}"
        distratores = [b*h, b+h, 2*(b+h), b*h//4, area+b]
    elif figura == "quadrado":
        lado = rng.choice([4, 5, 6, 7, 8, 9, 11, 12])
        area = lado * lado
        cenario = rng.choice([
            f"Um condomínio vai instalar um deque de madeira em uma "
            f"área quadrada do jardim, com {lado} metros de lado.",
            f"Uma sala quadrada de {lado} metros de lado será "
            f"revestida com piso vinílico, vendido por metro "
            f"quadrado.",
            f"Um galpão possui piso quadrado medindo {lado} metros em "
            f"cada lado, e a empresa precisa calcular quanto de "
            f"impermeabilizante comprar.",
        ])
        formula = f"área = lado² = {lado}² = {area}"
        distratores = [4*lado, 2*lado, lado*lado//2, area+lado, lado]
    else:
        raio = rng.choice([2, 3, 4, 5, 6, 10])
        area = raio * raio
        cenario = rng.choice([
            f"A prefeitura vai revitalizar uma praça circular do "
            f"centro e precisa estimar a área a ser gramada. A praça "
            f"tem raio de {raio} metros. Adote π = 3.",
            f"Um projeto de jardinagem prevê um canteiro circular no "
            f"pátio da escola, com {raio} metros de raio. "
            f"Adote π = 3.",
            f"Um clube vai recapear a pista circular de caminhada, "
            f"que tem raio de {raio} metros. Adote π = 3.",
        ])
        area = 3 * raio * raio
        formula = f"área = π·r² = 3 × {raio}² = 3 × {raio*raio} = {area}"
        distratores = [2*3*raio, 3*raio, raio*raio, area*2, area//2]

    # Uma pergunta só fazia cinco questões do template parecerem
    # idênticas, ainda que a figura mudasse.
    COMANDOS = [
        "Sua área é de:",
        "A área dessa figura é de:",
        "Qual a área correspondente?",
        "Determine a área.",
        "A área ocupada corresponde a:",
        "Calcule a área.",
    ]
    enunciado = f"{cenario} {rng.choice(COMANDOS)}"
    unidade = "m²" if "metros" in cenario else "cm²"
    correta = area
    distratores = [d for d in distratores if d > 0 and d != correta]

    explicacao = f"A área do {figura} é calculada assim: {formula}."
    q = _montar(enunciado, correta, distratores, explicacao,
                "Matemática básica (geometria)", rng,
                lambda v: f"{_num(v)} {unidade}")
    if q:
        q["_grupo"] = f"area:{figura}"
    return q


# ══════════════════════════════════════════════════════════
#  CATÁLOGO POR TÓPICO
# ══════════════════════════════════════════════════════════
#
#  Cada template tem RÓTULO legível e NÍVEL declarado, para o
#  app montar botões do tipo "gerar questão de equação do
#  segundo grau" sem precisar traduzir nomes internos.
#
#  Consumido pela rota GET /procedural/topicos.
#

TEMPLATES_BASICA = {
    "porcentagem":       gerar_porcentagem,
    "desconto":          gerar_desconto_acrescimo,
    "regra_de_tres":     gerar_regra_de_tres,
    "equacao_1grau":     gerar_equacao_1grau,
    "equacao_2grau":     gerar_equacao_2grau,
    "sistema":           gerar_sistema_equacoes,
    "juros_simples":     gerar_juros_simples,
    "juros_compostos":   gerar_juros_compostos,
    "estatistica":       gerar_media_moda_mediana,
    "pitagoras":         gerar_pitagoras,
    "area":              gerar_area_figura,
}

# (chave, rótulo legível, nível, área)
CATALOGO = [
    ("porcentagem",     "Porcentagem",                "fundamental", "aritmética"),
    ("desconto",        "Desconto e acréscimo",       "fundamental", "aritmética"),
    ("regra_de_tres",   "Regra de três",              "fundamental", "aritmética"),
    ("equacao_1grau",   "Equação do 1º grau",         "fundamental", "álgebra"),
    ("equacao_2grau",   "Equação do 2º grau",         "médio",       "álgebra"),
    ("sistema",         "Sistema de equações",        "fundamental", "álgebra"),
    ("juros_simples",   "Juros simples",              "fundamental", "financeira"),
    ("juros_compostos", "Juros compostos",            "médio",       "financeira"),
    ("estatistica",     "Média, moda e mediana",      "fundamental", "estatística"),
    ("pitagoras",       "Teorema de Pitágoras",       "fundamental", "geometria"),
    ("area",            "Área de figuras planas",     "fundamental", "geometria"),
]

NIVEIS = ["fundamental", "médio"]

TOPICOS_BASICA = {}
for _ch, _rot, _niv, _area in CATALOGO:
    TOPICOS_BASICA.setdefault(_area, []).append(_ch)
for _niv in NIVEIS:
    TOPICOS_BASICA[_niv] = [c[0] for c in CATALOGO if c[2] == _niv]


def listar_topicos(nivel: str = None):
    """
    Devolve o catálogo para o app montar os botões.

    Cada item traz a chave interna, o rótulo legível, o nível e a área.
    Se `nivel` for informado, filtra por ele.
    """
    itens = [
        {"chave": ch, "rotulo": rot, "nivel": niv, "area": area}
        for ch, rot, niv, area in CATALOGO
        if nivel is None or niv == nivel
    ]
    return itens


PALAVRAS_CHAVE = {
    "porcentagem":     ["porcentagem", "percentual", "porcento", "desconto"],
    "desconto":        ["desconto", "acrescimo", "aumento", "porcentagem",
                        "preco final"],
    "regra_de_tres":   ["regra de tres", "proporcao", "grandezas "
                        "proporcionais", "razao"],
    "equacao_1grau":   ["equacao do primeiro grau", "equacao do 1 grau",
                        "equacao linear", "incognita"],
    "equacao_2grau":   ["equacao do segundo grau", "equacao do 2 grau",
                        "bhaskara", "discriminante", "delta",
                        "equacao quadratica", "soma e produto"],
    "sistema":         ["sistema de equacoes", "sistema linear",
                        "substituicao", "adicao"],
    "juros_simples":   ["juros simples", "matematica financeira", "montante",
                        "capital"],
    "juros_compostos": ["juros compostos", "matematica financeira",
                        "capitalizacao", "montante"],
    "estatistica":     ["media", "moda", "mediana", "estatistica",
                        "medidas de tendencia central"],
    "pitagoras":       ["pitagoras", "teorema de pitagoras", "triangulo "
                        "retangulo", "hipotenusa", "cateto"],
    "area":            ["area", "figuras planas", "perimetro", "geometria "
                        "plana", "retangulo", "triangulo", "circulo"],
}

CHAVES_GENERICAS = {"equacao", "grau", "valor", "numero", "total", "medida"}


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
               topico: str = None, templates: list = None,
               nivel: str = None):
    """
    Gera um lote de questões de matemática básica.

    `templates` aceita a chave de UM tópico — é o que permite o botão
    "gerar questão de equação do segundo grau" no app.
    `nivel` filtra por fundamental ou médio.
    """
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_BASICA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_BASICA]
        if pedidos:
            disponiveis = pedidos
    if nivel:
        n = _normalizar(nivel)
        por_nivel = [c[0] for c in CATALOGO if _normalizar(c[2]) == n]
        if por_nivel:
            disponiveis = [t for t in disponiveis if t in por_nivel]
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_BASICA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave] if t in TEMPLATES_BASICA]
        elif chave in TEMPLATES_BASICA:
            disponiveis = [chave]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    from collections import Counter

    posicao = 0
    questoes, tentativas, limite = [], 0, quantidade * 15
    vistos, fatos_usados = set(), set()
    topicos = Counter()

    # Teto por TEMPLATE, não por tópico: "geometria" agrupa área e
    # Pitágoras, então um teto de tópico permitia seis questões de área
    # seguidas. Dividir a cota pelo número de templates disponíveis
    # distribui de verdade.
    #
    # Com UM único template pedido (botão de tópico no app), não há
    # teto: o aluno pediu dez questões daquele assunto.
    import math
    TETO = (math.ceil(quantidade / len(disponiveis)) + 1
            if len(disponiveis) > 1 else quantidade)

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = disponiveis[posicao % len(disponiveis)]
        posicao += 1
        try:
            q = TEMPLATES_BASICA[nome](rng)
        except Exception:
            continue
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        # O campo é "_grupo", não "_fato". Aqui ele nomeia o TIPO de
        # exercício — "porcentagem", "juros_simples" — e serve para
        # espaçar exercícios do mesmo tipo dentro do lote, com escape
        # quando o material acaba.
        #
        # Chamava-se "_fato", e o montador de simulado lê esse nome como
        # identidade de conteúdo: duas contas de porcentagem com números
        # diferentes eram tratadas como a mesma questão e uma delas
        # caía. Numa disciplina inteira de cálculo, isso derrubava quase
        # tudo para a reserva.
        fato = q.get("_grupo")
        if (fato and fato in fatos_usados and len(disponiveis) > 1
                and tentativas < limite * 0.9):
            continue

        # A contagem é pelo TEMPLATE que gerou a questão, não pelo
        # tópico — "geometria" abriga área e Pitágoras, e contar por
        # tópico deixava seis questões de área passarem.
        if topicos[nome] >= TETO and tentativas < limite * 0.75:
            continue

        vistos.add(q["enunciado"])
        if fato:
            fatos_usados.add(fato)
        topicos[nome] += 1
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade: int = 10, seed: int = None,
                   topico: str = None, templates: list = None,
                   nivel: str = None):
    """Devolve (questoes, gabarito) no formato que a API espera."""
    lote = gerar_lote(quantidade, seed=seed, topico=topico,
                      templates=templates, nivel=nivel)
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
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    print("═" * 64)
    print("  GERADOR DE MATEMÁTICA BÁSICA")
    print("═" * 64)
    if not alvo:
        print("\n  TÓPICOS DISPONÍVEIS:\n")
        for it in listar_topicos():
            print(f"    {it['chave']:<18} {it['rotulo']:<26} "
                  f"{it['nivel']:<12} {it['area']}")
        print("\n  Uso: python gerador_basica.py <chave>")
    else:
        for q in gerar_lote(4, seed=2026, templates=[alvo]):
            print(f"\n{q['numero']}. {q['enunciado']}")
            for L, t in q["alternativas"].items():
                print(f"     {L}) {t}")
            print(f"   GABARITO: {q['gabarito']}")
            print(f"   {q['explicacao']}")
