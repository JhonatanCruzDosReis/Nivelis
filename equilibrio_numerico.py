"""
Sorteia a POSIÇÃO da resposta certa entre as alternativas numéricas.

O problema que isto resolve
───────────────────────────
Distrator de questão calculada quase sempre nasce como "a resposta,
errada por um pouco": esqueceu uma parcela, dividiu em vez de
multiplicar, usou o ano civil no lugar do comercial. Uns caem abaixo
do valor certo, outros acima — e a resposta certa fica no MEIO das
cinco, questão após questão.

Medido no teste 8 depois que a estratégia de magnitude foi
acrescentada: "marque o valor do meio" acertava 100% em prazos de
processo civil, 100% em permutação circular, 98% em desempenho de
redes. Nenhuma estratégia de texto via isso — todas medem comprimento
ou vocabulário, não grandeza.

O mesmo vale para o espelho: em contagem, todo erro clássico
SUPERESTIMA o resultado, e a resposta certa era a menor das cinco em
100% das questões.

Como resolve
────────────
`escolher(correta, pool, rng)` separa o pool em valores abaixo e acima
da resposta, SORTEIA quantos vêm de cada lado e devolve os quatro
escolhidos. A posição da resposta certa passa a ser uniforme.

O primeiro distrator do pool é o erro clássico da matéria e entra
sempre — é ele que dá valor didático à questão. Os outros três é que
são sorteados por lado.

Quando o pool inteiro está de um lado só, a posição não tem como
variar: `escolher` devolve o que dá e `diagnosticar` aponta o
template, que precisa de distratores no lado que falta.
"""

import re

_NUMERO = re.compile(r'-?[\d.]+,\d+|-?\d[\d.]*')
_DATA = re.compile(r'^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$')
_FRACAO = re.compile(r'^\s*(-?\d+)\s*/\s*(\d+)\s*$')


def valor_de(x):
    """
    Grandeza comparável de uma alternativa, ou None.

    Trata os três formatos em que uma leitura ingênua mente:

      • data "15/03/2022" — o último número é o ANO, e duas datas do
        mesmo ano empatariam. Vira um ordinal aaaammdd.
      • fração "5/36" — o último número é o DENOMINADOR, e comparar
        denominadores inverte a ordem das probabilidades.
      • moeda "R$ 1.234,56" — ponto é milhar, vírgula é decimal.
    """
    if isinstance(x, (int, float)):
        return float(x)
    try:                      # Fraction, Decimal e afins
        from fractions import Fraction
        if isinstance(x, Fraction):
            return float(x)
    except Exception:
        pass

    txt = str(x).strip()

    m = _DATA.match(txt)
    if m:
        d, mes, ano = (int(g) for g in m.groups())
        return float(ano * 10000 + mes * 100 + d)

    m = _FRACAO.match(txt)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return num / den if den else None

    achados = _NUMERO.findall(txt)
    if not achados:
        return None
    try:
        return float(achados[-1].replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _seguro(chave):
    """Blinda a função de valor: distrator exótico não derruba o lote."""
    def f(x):
        try:
            return chave(x)
        except Exception:
            return None
    return f


def escolher(correta, pool, rng, n=4, fixar_primeiro=True, chave=valor_de):
    """
    Devolve n distratores com a posição da resposta certa sorteada.

    `pool` é a lista de distratores do template, na ordem em que ele
    os escreveu — o primeiro sendo o erro clássico.

    Sem valor numérico legível, embaralha e devolve: não há posição a
    equilibrar, e o comportamento continua o de antes.
    """
    pool = list(pool)
    chave = _seguro(chave)
    vc = chave(correta)
    if vc is None or len(pool) <= n:
        resto = pool[1:] if (fixar_primeiro and pool) else pool
        rng.shuffle(resto)
        return (pool[:1] + resto) if (fixar_primeiro and pool) else resto

    fixos = pool[:1] if fixar_primeiro else []
    livres = pool[1:] if fixar_primeiro else pool

    abaixo = [d for d in livres if (chave(d) is not None and chave(d) < vc)]
    acima = [d for d in livres if (chave(d) is not None and chave(d) > vc)]
    neutros = [d for d in livres
               if chave(d) is None or chave(d) == vc]
    rng.shuffle(abaixo)
    rng.shuffle(acima)
    rng.shuffle(neutros)

    faltam = n - len(fixos)
    # De quantos do lado de baixo o sorteio pode dar conta, hoje
    minimo = max(0, faltam - len(acima) - len(neutros))
    maximo = min(faltam, len(abaixo))
    if minimo > maximo:
        resto = livres[:]
        rng.shuffle(resto)
        return fixos + resto[:faltam]

    quantos_abaixo = rng.randint(minimo, maximo)
    escolhidos = abaixo[:quantos_abaixo]
    escolhidos += acima[:faltam - len(escolhidos)]
    if len(escolhidos) < faltam:
        escolhidos += neutros[:faltam - len(escolhidos)]
    if len(escolhidos) < faltam:
        sobra = [d for d in livres if d not in escolhidos]
        escolhidos += sobra[:faltam - len(escolhidos)]
    return fixos + escolhidos


def diagnosticar(gerar, tentativas=400, chave=valor_de):
    """
    Mede a posição da resposta certa em um template.

    `gerar` é uma função sem argumentos que devolve uma questão no
    formato do projeto (ou None). Devolve a contagem por posto: o
    ideal é 20% em cada um dos cinco.
    """
    postos = [0] * 5
    medidas = 0
    for _ in range(tentativas):
        q = gerar()
        if not q:
            continue
        alts = q.get("alternativas") or {}
        vals = {L: chave(t) for L, t in alts.items()}
        if len(vals) != 5 or any(v is None for v in vals.values()):
            continue
        if len(set(vals.values())) < 5:
            continue
        ordem = sorted(vals, key=lambda L: vals[L])
        postos[ordem.index(q.get("gabarito"))] += 1
        medidas += 1
    return {"postos": postos, "medidas": medidas,
            "pior": max(postos) / medidas if medidas else 0.0}
