"""
=============================================================
  TESTE 8 — A QUESTÃO SE RESOLVE SEM LER O TEXTO?
=============================================================
  Os testes anteriores verificam se a questão está CORRETA e
  se FAZ SENTIDO. Este verifica se ela MEDE ALGUMA COISA.

  Uma questão de interpretação falha no seu propósito quando
  o aluno acerta por pistas formais em vez de leitura:

    • quatro alternativas absurdas e uma razoável
    • a certa é a única moderada ("pode", "em alguns casos")
      e as erradas são categóricas ("sempre", "nunca", "único")
    • a certa é a mais longa ou a mais curta
    • as erradas se contradizem entre si, denunciando a certa
    • a certa é a única que retoma o vocabulário do comando

  A heurística implementada aqui é a de um aluno esperto que
  NÃO leu o texto. Se ela acerta acima do acaso (20%), a
  questão tem vazamento formal.

  USO: python teste_8_sem_ler.py [quantidade]
=============================================================
"""

import importlib
import sys
import re
from collections import Counter, defaultdict

sys.path.insert(0, ".")


# ══════════════════════════════════════════════════════════
#  MARCADORES QUE DENUNCIAM A ALTERNATIVA
# ══════════════════════════════════════════════════════════

# Termos absolutos: raros numa afirmação verdadeira de texto acadêmico,
# comuns em distrator mal construído
ABSOLUTOS = re.compile(
    r'\b(?:sempre|nunca|jamais|todos?|todas?|nenhum[ao]?|únic[ao]|'
    r'exclusivamente|apenas|somente|qualquer|impossível|garantid[ao]|'
    r'obrigatoriamente|necessariamente|invariavelmente|a todo custo|'
    r'independentemente|irrelevante|dispensável|desnecessári[ao])\b',
    re.IGNORECASE)

# Termos moderados: típicos da afirmação correta em texto acadêmico
MODERADOS = re.compile(
    r'\b(?:pode|podem|geralmente|frequentemente|em geral|tende|tendem|'
    r'costuma|costumam|alguns?|algumas?|parcialmente|relativamente|'
    r'sugere|indica|contribui|favorece|dificulta)\b',
    re.IGNORECASE)


def _palavras(txt):
    return {p for p in re.findall(r'[a-zà-ÿ]{5,}', str(txt).lower())}


def _radicais(txt):
    return {p[:6] for p in _palavras(txt)}


# ══════════════════════════════════════════════════════════
#  ESTRATÉGIAS DE CHUTE
# ══════════════════════════════════════════════════════════

def chute_evita_absolutos(alts: dict):
    """
    Elimina alternativas com termos absolutos.

    Estratégia clássica de prova: "sempre" e "nunca" costumam
    marcar o distrator. Se sobra UMA, o aluno acerta sem ler.
    """
    sobrando = [L for L, t in alts.items() if not ABSOLUTOS.search(str(t))]
    return sobrando[0] if len(sobrando) == 1 else None


def chute_moderada(alts: dict):
    """A única alternativa com linguagem moderada."""
    com = [L for L, t in alts.items() if MODERADOS.search(str(t))]
    return com[0] if len(com) == 1 else None


def chute_mais_longa(alts: dict, margem: float = 1.5):
    """A alternativa destacadamente mais longa."""
    tam = {L: len(str(t)) for L, t in alts.items()}
    maior = max(tam, key=tam.get)
    outros = [v for L, v in tam.items() if L != maior]
    if outros and tam[maior] / (sum(outros) / len(outros)) >= margem:
        return maior
    return None


def chute_mais_curta(alts: dict, margem: float = 0.6):
    """A alternativa destacadamente mais curta."""
    tam = {L: len(str(t)) for L, t in alts.items()}
    menor = min(tam, key=tam.get)
    outros = [v for L, v in tam.items() if L != menor]
    if outros and tam[menor] / (sum(outros) / len(outros)) <= margem:
        return menor
    return None


def chute_positiva_entre_negativas(alts: dict):
    """
    A única alternativa afirmativa quando as demais negam.

    Distratores construídos por negação da tese produzem esse
    padrão: quatro "não é / não deve" e uma afirmativa.
    """
    NEG = re.compile(r'\b(?:não|nunca|jamais|nem|sem)\b', re.IGNORECASE)
    positivas = [L for L, t in alts.items() if not NEG.search(str(t))]
    return positivas[0] if len(positivas) == 1 else None


def chute_vocabulario_do_comando(enunciado: str, alts: dict):
    """
    A alternativa que mais retoma as palavras do COMANDO.

    Se o comando pergunta pela "tese" e uma alternativa é a única
    que ecoa os termos da pergunta, ela se destaca sem leitura.
    """
    # O comando é a última linha do enunciado
    comando = str(enunciado).strip().split("\n")[-1]
    rad_cmd = _radicais(comando)
    if len(rad_cmd) < 3:
        return None

    scores = {L: len(rad_cmd & _radicais(t)) for L, t in alts.items()}
    ordenado = sorted(scores.items(), key=lambda x: -x[1])
    # Destaca-se se tem ao menos 2 radicais a mais que o segundo
    if len(ordenado) >= 2 and ordenado[0][1] >= ordenado[1][1] + 2:
        return ordenado[0][0]
    return None


def chute_odd_one_out(alts: dict):
    """
    A alternativa que trata de assunto diferente das outras.

    Quando quatro distratores vêm do mesmo molde e a correta vem de
    outro lugar, ela se destaca por contraste temático — o aluno marca
    "a diferente" sem ler o texto.

    A comparação é de cada alternativa contra o VOCABULÁRIO AGREGADO
    das demais, não par a par: com frases curtas e termos variados, a
    comparação par a par dá zero para várias ao mesmo tempo e não
    distingue nada.
    """
    letras = list(alts)
    if len(letras) < 5:
        return None

    rads = {L: _radicais(t) for L, t in alts.items()}
    if any(not r for r in rads.values()):
        return None

    sobreposicao = {}
    for L in letras:
        agregado = set()
        for X in letras:
            if X != L:
                agregado |= rads[X]
        sobreposicao[L] = len(rads[L] & agregado) / len(rads[L])

    ordenado = sorted(sobreposicao.items(), key=lambda x: x[1])
    isolada, valor = ordenado[0]
    segundo_valor = ordenado[1][1]

    # Isolada de verdade: quase nada em comum com o resto, enquanto a
    # próxima menos conectada ainda compartilha vocabulário relevante
    if valor <= 0.15 and segundo_valor >= 0.30:
        return isolada
    return None


def chute_elimina_destoante(alts: dict, margem: float = 2.0):
    """
    Elimina a alternativa visualmente destoante e chuta entre as demais.

    Não é uma estratégia de acerto direto — mede se a questão perde uma
    opção efetiva. Se sobra exatamente uma após eliminar a destoante e as
    absolutas, o aluno acerta sem ler.
    """
    tam = {L: len(str(t)) for L, t in alts.items()}
    restantes = []
    for L, n in tam.items():
        demais = [v for k, v in tam.items() if k != L]
        media = sum(demais) / len(demais) if demais else 0
        if media > 0 and (n / media > margem or n / media < 0.45):
            continue          # destoa: eliminada
        if ABSOLUTOS.search(str(alts[L])):
            continue          # termo absoluto: eliminada
        restantes.append(L)
    return restantes[0] if len(restantes) == 1 else None


# Uma definição só de "valor da alternativa", compartilhada com o
# equilibrio_numerico: se o teste medir a grandeza de um jeito e o
# gerador equilibrar de outro, a correção não aparece na medição.
from equilibrio_numerico import valor_de as _valor


def _valores(alts: dict):
    """Os cinco valores, ou None se o conjunto não for comparável."""
    vals = {L: _valor(t) for L, t in alts.items()}
    if any(v is None for v in vals.values()):
        return None
    if len(set(vals.values())) < len(vals):
        return None       # empate: não dá para falar em maior nem menor
    return vals


def chute_maior_valor(alts: dict):
    """
    A alternativa de MAIOR valor numérico.

    Foi assim que o markup de administração vazou: todo erro clássico
    daquela conta produz um preço MENOR que o correto, então a resposta
    certa era a maior das cinco em 84% das questões. Nenhuma estratégia
    de texto pega isso — elas medem comprimento, não magnitude.
    """
    vals = _valores(alts)
    if not vals:
        return None
    return max(vals, key=lambda L: vals[L])


def chute_menor_valor(alts: dict):
    """A alternativa de MENOR valor numérico — o vazamento espelhado."""
    vals = _valores(alts)
    if not vals:
        return None
    return min(vals, key=lambda L: vals[L])


def chute_valor_do_meio(alts: dict):
    """
    A alternativa MEDIANA em valor.

    O oposto dos dois anteriores: quando todos os distratores são erros
    que ora superestimam ora subestimam, a resposta certa fica presa no
    meio e nunca nos extremos. Eliminar as duas pontas leva o acaso de
    20% para 33%.
    """
    vals = _valores(alts)
    if not vals:
        return None
    ordenado = sorted(vals, key=lambda L: vals[L])
    return ordenado[len(ordenado) // 2]


ESTRATEGIAS = [
    ("maior_valor",           lambda e, a: chute_maior_valor(a)),
    ("menor_valor",           lambda e, a: chute_menor_valor(a)),
    ("valor_do_meio",         lambda e, a: chute_valor_do_meio(a)),
    ("elimina_destoante",     lambda e, a: chute_elimina_destoante(a)),
    ("evita_absolutos",       lambda e, a: chute_evita_absolutos(a)),
    ("unica_moderada",        lambda e, a: chute_moderada(a)),
    ("mais_longa",            lambda e, a: chute_mais_longa(a)),
    ("mais_curta",            lambda e, a: chute_mais_curta(a)),
    ("unica_positiva",        lambda e, a: chute_positiva_entre_negativas(a)),
    ("ecoa_o_comando",        chute_vocabulario_do_comando),
    ("assunto_isolado",       lambda e, a: chute_odd_one_out(a)),
]


# ══════════════════════════════════════════════════════════

def avaliar(questoes) -> dict:
    """
    Roda cada estratégia sobre o lote e mede a taxa de acerto.

    O acaso é 20% (1 em 5). Uma estratégia que acerta acima disso
    de forma consistente indica vazamento formal.
    """
    resultado = {}
    for nome, fn in ESTRATEGIAS:
        tentou = acertou = 0
        exemplos = []
        for q in questoes:
            palpite = fn(q.get("enunciado", ""), q.get("alternativas", {}))
            if palpite is None:
                continue
            tentou += 1
            if palpite == q.get("gabarito"):
                acertou += 1
                if len(exemplos) < 2:
                    exemplos.append(q)
        if tentou:
            resultado[nome] = {
                "tentou": tentou,
                "acertou": acertou,
                "taxa": acertou / tentou,
                "cobertura": tentou / max(1, len(questoes)),
                "exemplos": exemplos,
            }
    return resultado


def imprimir(nome_gerador, questoes, limiar=0.45):
    """
    Limiar de 45%: acima do acaso (20%) com folga para variação
    amostral. Uma estratégia que acerta metade das vezes está
    lendo uma pista real, não sorteando.
    """
    res = avaliar(questoes)
    problemas = 0

    print(f"\n  ┌─ {nome_gerador} ({len(questoes)} questões)")
    if not res:
        print("  │   nenhuma estratégia encontrou padrão explorável  ✅")
        print("  └────────────────────────────────────────────────")
        return 0

    for nome, d in sorted(res.items(), key=lambda x: -x[1]["taxa"]):
        # Só conta como falha se a estratégia se aplica a uma fração
        # relevante do lote — acertar 1 de 1 não prova nada
        relevante = d["cobertura"] >= 0.10 and d["tentou"] >= 5
        falha = relevante and d["taxa"] >= limiar

        # Exceção à cobertura: uma estratégia que NUNCA erra, mesmo
        # aplicando-se a poucas questões, encontrou um vazamento real,
        # não uma tendência estatística. Acertar 15 de 15 por acaso tem
        # probabilidade de 0,2^15.
        #
        # Foi assim que o eco passou despercebido: só dois dos doze
        # nervos cranianos saem por uma abertura que leva o nome deles
        # ("nervo hipoglosso" → "canal do hipoglosso"), então a
        # cobertura ficava em 3% e o alarme era rebaixado a aviso —
        # embora quem marcasse a alternativa que repete a palavra do
        # enunciado acertasse todas.
        if d["tentou"] >= 15 and d["taxa"] >= 0.90:
            falha = True
        if falha:
            problemas += 1
        marca = "❌" if falha else ("· " if d["taxa"] < limiar else "⚠ ")
        print(f"  │ {marca} {nome:<20} acertou {d['acertou']:>3}/{d['tentou']:<3} "
              f"({d['taxa']:>5.1%})  aplicou-se a {d['cobertura']:>5.1%}")
        if falha and d["exemplos"]:
            q = d["exemplos"][0]
            cmd = str(q["enunciado"]).strip().split("\n")[-1]
            print(f"  │      exemplo: {cmd[:62]}")
            for L, t in q["alternativas"].items():
                m = " ←" if L == q["gabarito"] else "  "
                print(f"  │        {L}) {str(t)[:58]}{m}")
    print("  └────────────────────────────────────────────────")
    return problemas


def checar_distribuicao_gabarito(questoes, nome=""):
    """
    A letra do gabarito e o CONTEÚDO da opção correta precisam variar.

    Dois vieses distintos:
      1. Letra — se o gabarito é B em 60% das vezes, chutar B compensa.
      2. Conteúdo — na asserção-razão, se apenas 2 das 5 opções
         possíveis chegam a ser corretas, o aluno elimina três de
         antemão. Foi o que aconteceu quando o filtro de tamanho
         descartava a opção mais curta.
    """
    problemas = []
    if len(questoes) < 30:
        return problemas

    letras = Counter(q.get("gabarito") for q in questoes)
    for L, n in letras.items():
        taxa = n / len(questoes)
        if taxa > 0.35:
            problemas.append(f"letra {L} é gabarito em {taxa:.0%} das questões")

    # Conteúdo da correta, para formatos de opções fixas
    conteudos = Counter(str(q["alternativas"][q["gabarito"]])[:40]
                        for q in questoes)
    total_opcoes = len(set(
        str(v)[:40] for q in questoes for v in q["alternativas"].values()))
    if total_opcoes <= 6 and len(conteudos) < total_opcoes - 1:
        problemas.append(
            f"apenas {len(conteudos)} de {total_opcoes} opções chegam a ser "
            f"gabarito (as demais são elimináveis de antemão)")
    return problemas


# Todos os geradores procedurais entram: o vazamento formal não é
# privilégio da interpretação de texto. Nas rodadas anteriores o teste
# pegou eco do comando em genética, português e engenharia, e correlação
# de comprimento em engenharia — defeitos que nenhum outro teste vê.
GERADORES_PROCEDURAIS = [
    ("ADS / Computação",  "gerador_ads"),
    ("Administração",     "gerador_administracao"),
    ("Anatomia",          "gerador_anatomia"),
    ("Matemática básica", "gerador_basica"),
    ("Bio. celular",      "gerador_biocelular"),
    ("Bioquímica",        "gerador_bioquimica"),
    ("Conceitual",        "gerador_decoreba"),
    ("Direito",           "gerador_direito"),
    ("Embriologia",       "gerador_embriologia"),
    ("Engenharia",        "gerador_engenharia"),
    ("Farmacologia",      "gerador_farmacologia"),
    ("Fisiologia",        "gerador_fisiologia"),
    ("Genética",          "gerador_genetica"),
    ("Histologia",        "gerador_histologia"),
    ("Imunologia",        "gerador_imunologia"),
    ("Microbiologia",     "gerador_microbiologia"),
    ("Português",         "gerador_portugues"),
    ("Matemática",        "gerador_procedural"),
    ("Redes",             "gerador_redes"),
]


def _examinar(nome, questoes, detalhar_topicos=True):
    """Roda as estratégias no lote inteiro e depois tópico a tópico."""
    if not questoes:
        print(f"\n  ⏭  {nome}: nenhuma questão gerada")
        return 0

    problemas = imprimir(nome, questoes)

    for p in checar_distribuicao_gabarito(questoes, nome):
        problemas += 1
        print(f"  │ ❌ [{nome}] {p}")

    if detalhar_topicos:
        # O lote inteiro dilui: uma pista que domina um tópico pequeno
        # some na média de 1000 questões. Só se detalha o que falhou ou
        # o que tem amostra suficiente.
        por_tipo = defaultdict(list)
        for q in questoes:
            por_tipo[q.get("topico", "?")].append(q)
        for topico, qs in sorted(por_tipo.items()):
            if len(qs) >= 40:
                problemas += imprimir(f"  → {topico}", qs)
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    alvos = [a.lower() for a in sys.argv[2:]]

    print("═" * 64)
    print("  TESTE 8 — A QUESTÃO SE RESOLVE SEM LER O TEXTO?")
    print("═" * 64)
    print("\n  Cada estratégia simula um aluno que NÃO leu o texto.")
    print("  Acaso = 20%. Acima de 45% indica pista formal.")

    total = 0

    # Interpretação, que é onde o risco se concentra
    if not alvos or any("interp" in a for a in alvos):
        import gerador_interpretacao as GI
        from _trechos_teste import TRECHOS_TESTE
        lote = GI.gerar_lote(TRECHOS_TESTE, qtd, seed=20260817)
        total += _examinar("Interpretação de texto", lote)

    for rotulo, modulo in GERADORES_PROCEDURAIS:
        if alvos and not any(a in modulo.lower() or a in rotulo.lower()
                             for a in alvos):
            continue
        try:
            m = importlib.import_module(modulo)
        except ImportError:
            print(f"\n  ⏭  {rotulo}: módulo ausente")
            continue
        # Várias sementes: uma só pode mascarar a pista por sorte de
        # sorteio, sobretudo nos geradores de lastro pequeno.
        lote = []
        for seed in (20260817, 4242, 99):
            lote += m.gerar_lote(qtd, seed=seed) or []
        total += _examinar(rotulo, lote)

    print("\n" + "═" * 64)
    print(f"  {'🎉 TESTE 8 PASSOU' if total == 0 else f'❌ {total} VAZAMENTO(S) FORMAL(IS)'}")
    print("═" * 64)
    sys.exit(1 if total else 0)
