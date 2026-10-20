"""
=============================================================
  TESTE 9 — OS DISTRATORES SÃO ERROS PLAUSÍVEIS?
=============================================================
  Um bom distrator é o resultado de um erro que o aluno
  realmente cometeria. Um distrator ruim é um número solto:
  ninguém marca, e a questão vira de duas alternativas.

  Exemplo em combinatória — "de quantas formas 6 pessoas
  podem ocupar 3 lugares no pódio?" (resposta 120):

    BONS:  720 (usou 6!), 20 (usou C(6,3)), 216 (usou 6³)
    RUINS: 47, 3, 1000  — não vêm de erro nenhum

  CHECAGENS:
    1. Distratores derivam de erros reconhecíveis
    2. Ordem de grandeza compatível com a resposta
    3. Sem repetição de valor entre alternativas
    4. Gabarito não é sistematicamente o maior nem o menor
    5. Distância relativa suficiente (não confunde por
       arredondamento)

  USO: python teste_9_distratores.py [quantidade]
=============================================================
"""

import sys
import re
from collections import Counter, defaultdict

sys.path.insert(0, ".")


# Alternativas que PARECEM número mas são identificadores. Comparar
# grandeza entre elas não faz sentido: a porta 22 não é "150x menor"
# que a 3306, e 255.255.255.0 não é um valor na casa dos bilhões.
NAO_E_GRANDEZA = [
    (re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?$'), "endereço IPv4"),
    (re.compile(r'^\d{2}/\d{2}/\d{4}$'),                       "data"),
    (re.compile(r'^/\d{1,2}$'),                                 "prefixo CIDR"),
    (re.compile(r'^[0-9a-fA-F:]{4,}$'),                          "endereço IPv6"),
    (re.compile(r'^\d{3}$'),                                    "código HTTP / porta"),
    (re.compile(r'^\d{2,5}$'),                                  "porta ou código"),
    # Notação assintótica: O(n²) e O(n log n) são classes, não valores.
    (re.compile(r'^[ΘΩO]\s*\(.*\)$'),                           "notação assintótica"),
    (re.compile(r'^\d+\s*(?:FN|NF)$'),                           "forma normal"),
    (re.compile(r'^v?\d+(?:\.\d+)+$'),                          "versão"),
]


def _e_identificador(txt: str) -> bool:
    """
    A alternativa é um identificador, não uma quantidade?

    Distinção necessária porque as checagens de ordem de grandeza e de
    proximidade só fazem sentido entre GRANDEZAS. Entre identificadores,
    "próximo" e "distante" não significam nada: 200 e 201 são códigos
    HTTP distintos, não valores confundíveis.
    """
    s = str(txt).strip()
    return any(padrao.fullmatch(s) for padrao, _ in NAO_E_GRANDEZA)


def _valor(txt):
    """
    Converte alternativa em número, tratando formato BR.

    Retorna None quando a alternativa não É um número:
      • identificadores (IP, data, porta, código HTTP)
      • frases que apenas CONTÊM número ("tratar 34 pacientes")

    A segunda exclusão importa: cinco frases distintas podem citar o
    mesmo valor sem que isso seja defeito — em interpretação de medidas
    epidemiológicas é o caso normal.
    """
    if _e_identificador(txt):
        return None

    s0 = str(txt).strip()
    # Mais de duas palavras alfabéticas = é frase, não valor
    if len(re.findall(r'[a-zà-ÿ]{3,}', s0.lower())) > 2:
        return None
    s = str(txt).strip().replace("R$", "").replace("%", "").strip()
    s = s.replace(" ns", "").replace(" mL", "").replace(" h", "")
    if "/" in s and s.count("/") == 1:
        try:
            a, b = s.split("/")
            return float(a.strip().replace(".", "").replace(",", ".")) / \
                   float(b.strip().replace(".", "").replace(",", "."))
        except (ValueError, ZeroDivisionError):
            return None
    s = re.sub(r'[^\d,.\-]', '', s)
    if not s:
        return None
    try:
        if "," in s:
            return float(s.replace(".", "").replace(",", "."))
        if s.count(".") == 1 and len(s.split(".")[-1]) <= 2:
            return float(s)
        return float(s.replace(".", ""))
    except ValueError:
        return None


def checar_ordem_grandeza(q, fator_max=100):
    """
    Distrator com ordem de grandeza absurda não engana ninguém.

    Se a resposta é 120 e uma alternativa é 15.000, o aluno
    descarta de imediato — a questão perde uma opção efetiva.

    NÃO se aplica a probabilidades expressas em fração: 1/512 e
    126/512 diferem 126 vezes e ambas são respostas plausíveis para
    a mesma questão binomial. Ali a razão entre valores não diz nada
    sobre a qualidade do distrator.
    """
    problemas = []
    alts = q.get("alternativas", {})

    if q.get("tipo_resposta") in ("fracao", "percentual"):
        return problemas
    if sum(1 for t in alts.values() if "/" in str(t)) >= 3:
        return problemas
    valores = {L: _valor(t) for L, t in alts.items()}
    valores = {L: v for L, v in valores.items() if v is not None and v != 0}
    if len(valores) < 4:
        return problemas          # não é questão numérica

    gab = valores.get(q.get("gabarito"))
    if gab is None or gab == 0:
        return problemas

    for L, v in valores.items():
        if L == q["gabarito"]:
            continue
        razao = max(abs(v), abs(gab)) / min(abs(v), abs(gab))
        if razao > fator_max:
            problemas.append(
                (q.get("topico", "?"),
                 f"alternativa {L} = {v:g} contra gabarito {gab:g} "
                 f"({razao:.0f}x de diferença)",
                 str(q["enunciado"])[:80]))
            break
    return problemas


def checar_distancia_minima(q, minimo=0.005):
    """
    Alternativas quase idênticas confundem por arredondamento.

    Se duas opções diferem em 0,1%, o aluno que arredondou em
    passo intermediário erra sem ter errado o método.
    """
    problemas = []
    alts = q.get("alternativas", {})
    valores = [(L, _valor(t)) for L, t in alts.items()]
    valores = [(L, v) for L, v in valores if v is not None]
    if len(valores) < 4:
        return problemas

    for i, (L1, v1) in enumerate(valores):
        for L2, v2 in valores[i + 1:]:
            if v1 == v2:
                problemas.append(
                    (q.get("topico", "?"),
                     f"alternativas {L1} e {L2} têm o mesmo valor ({v1:g})",
                     str(q["enunciado"])[:80]))
                return problemas
            # Diferença de 1 ou 2 unidades em valores inteiros é o
            # distrator "off-by-one" — clássico e proposital (1023 vs
            # 1022 = esqueceu o endereço de broadcast). Só acusa quando
            # a proximidade é FRACIONÁRIA, que confunde por arredondamento.
            if float(v1).is_integer() and float(v2).is_integer():
                if abs(v1 - v2) <= 2:
                    continue

            maior = max(abs(v1), abs(v2))
            if maior > 0 and abs(v1 - v2) / maior < minimo:
                problemas.append(
                    (q.get("topico", "?"),
                     f"alternativas {L1}={v1:g} e {L2}={v2:g} diferem menos "
                     f"de {minimo:.1%}",
                     str(q["enunciado"])[:80]))
                return problemas
    return problemas


def checar_posicao_extremos(questoes, limiar=0.55):
    """
    O gabarito não pode ser sistematicamente o maior ou o menor.

    "Na dúvida, marque o valor do meio" é estratégia real; se o
    gerador põe a resposta sempre num extremo, ela vaza.
    """
    problemas = []
    maior = menor = considerados = 0
    for q in questoes:
        valores = {L: _valor(t) for L, t in q.get("alternativas", {}).items()}
        valores = {L: v for L, v in valores.items() if v is not None}
        if len(valores) < 5:
            continue
        gab = q.get("gabarito")
        if gab not in valores:
            continue
        considerados += 1
        if valores[gab] == max(valores.values()):
            maior += 1
        if valores[gab] == min(valores.values()):
            menor += 1

    if considerados >= 30:
        # Esperado ao acaso: 20% em cada extremo
        if maior / considerados > limiar:
            problemas.append(f"gabarito é o MAIOR valor em "
                             f"{maior/considerados:.0%} das questões")
        if menor / considerados > limiar:
            problemas.append(f"gabarito é o MENOR valor em "
                             f"{menor/considerados:.0%} das questões")
    return problemas


def checar_derivacao(q):
    """
    Os distratores vêm de erros reconhecíveis?

    Testa as relações que aparecem em erro real de aluno:
    dobro, metade, sem descontar 1 ou 2, fatorial em vez de
    arranjo, inversão de razão, erro de casa decimal.
    """
    alts = q.get("alternativas", {})
    valores = {L: _valor(t) for L, t in alts.items()}
    valores = {L: v for L, v in valores.items() if v is not None and v != 0}
    if len(valores) < 5:
        return None               # não avaliável

    gab_letra = q.get("gabarito")
    if gab_letra not in valores:
        return None
    g = valores[gab_letra]

    RELACOES = [
        (lambda v: abs(v - g * 2) < 0.01 * max(1, abs(g)),      "dobro"),
        (lambda v: abs(v - g / 2) < 0.01 * max(1, abs(g)),      "metade"),
        (lambda v: abs(v - (g + 1)) < 0.001,                     "off-by-one"),
        (lambda v: abs(v - (g - 1)) < 0.001,                     "off-by-one"),
        (lambda v: abs(v - (g + 2)) < 0.001,                     "off-by-two"),
        (lambda v: abs(v - (g - 2)) < 0.001,                     "off-by-two"),
        (lambda v: g > 0 and abs(v - g * 10) < 0.01 * max(1, abs(g)), "casa decimal"),
        (lambda v: g > 0 and abs(v - g / 10) < 0.01 * max(1, abs(g)), "casa decimal"),
        (lambda v: g > 0 and abs(v * g - 1) < 0.02,              "razão invertida"),
        (lambda v: 1.2 <= max(v, g) / min(v, g) <= 8,            "mesma escala"),
    ]

    derivados = 0
    for L, v in valores.items():
        if L == gab_letra:
            continue
        if any(teste(v) for teste, _ in RELACOES):
            derivados += 1
    return derivados


def verificar(questoes) -> dict:
    problemas = defaultdict(list)
    for q in questoes:
        for p in checar_ordem_grandeza(q):
            problemas["ordem_de_grandeza"].append(p)
        for p in checar_distancia_minima(q):
            problemas["valores_proximos_demais"].append(p)
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 800

    import gerador_ads, gerador_procedural, gerador_saude
    import gerador_decoreba, gerador_direito, gerador_redes

    GERADORES = [
        ("ADS / Computação",      gerador_ads),
        ("Matemática",            gerador_procedural),
        ("Saúde",                 gerador_saude),
        ("Conceitual (decoreba)", gerador_decoreba),
        ("Direito",               gerador_direito),
        ("Redes",                 gerador_redes),
    ]

    print("═" * 64)
    print("  TESTE 9 — QUALIDADE DOS DISTRATORES")
    print("═" * 64)

    total = 0
    for nome, mod in GERADORES:
        lote = mod.gerar_lote(qtd, seed=20260817)
        probs = verificar(lote)
        n = sum(len(v) for v in probs.values())

        extremos = checar_posicao_extremos(lote)
        n += len(extremos)

        # Proporção de distratores derivados de erro reconhecível
        taxas = [t for t in (checar_derivacao(q) for q in lote) if t is not None]
        media_deriv = sum(taxas) / len(taxas) if taxas else None

        total += n
        marca = "✅" if n == 0 else "❌"
        print(f"\n  {marca} {nome}: {qtd} questões — {n} problema(s)")
        if media_deriv is not None:
            pct = media_deriv / 4
            aval = "✅" if pct >= 0.75 else ("⚠ " if pct >= 0.5 else "❌")
            print(f"       {aval} distratores derivados de erro reconhecível: "
                  f"{media_deriv:.1f}/4 ({pct:.0%}) em {len(taxas)} questões numéricas")
        for e in extremos:
            print(f"       ❌ {e}")
        for regra, casos in sorted(probs.items(), key=lambda x: -len(x[1])):
            print(f"       {regra} ({len(casos)}x)")
            vistos = set()
            for topico, det, trecho in casos:
                if topico in vistos:
                    continue
                vistos.add(topico)
                print(f"          [{topico}] {det}")
                if len(vistos) >= 2:
                    break

    print("\n" + "═" * 64)
    print(f"  {'🎉 TESTE 9 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 64)
    sys.exit(1 if total else 0)
