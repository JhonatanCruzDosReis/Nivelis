"""
=============================================================
  AUDITORIA — ALTERNATIVAS QUE ENGLOBAM OUTRAS
=============================================================
  Um defeito recorrente já apareceu em cinco geradores:

    anatomia    "meato acústico interno"
                "meato acústico interno, com saída pelo forame"
    embriologia "a tuba uterina" / "a ampola da tuba uterina"
    imunologia  tipo I "menos de uma hora"
                tipo II "de minutos a horas"
    imunologia  tipo III "IgG" / tipo II "IgG e IgM"
    biocelular  ribossomo e centríolo, ambos sem membrana

  Em todos, DUAS alternativas podiam ser marcadas. A questão
  não é anulável por erro de gabarito: é anulável porque o
  enunciado não distingue as duas.

  Este arquivo procura o padrão em toda a base, por três
  critérios independentes:

    1. CONTINÊNCIA TEXTUAL — uma alternativa é subcadeia da
       outra, alinhada por palavra.
    2. CONTINÊNCIA DE CONJUNTO — a lista de itens de uma está
       contida na da outra ("IgG" dentro de "IgG e IgM").
    3. INTERSEÇÃO DE INTERVALO — duas faixas de tempo ou de
       valor se cruzam.

  O relatório separa o que é grave (a correta é um dos dois
  lados) do que é apenas ruído (dois distratores parecidos).

  USO:
      python3 auditar_sobreposicao.py
      python3 auditar_sobreposicao.py imunologia biocelular
=============================================================
"""

import importlib
import re
import sys
import unicodedata

# (rótulo, módulo)
GERADORES = [
    ("ADS",            "gerador_ads"),
    ("Administração",  "gerador_administracao"),
    ("Anatomia",       "gerador_anatomia"),
    ("Matemática básica", "gerador_basica"),
    ("Bio. celular",   "gerador_biocelular"),
    ("Bioquímica",     "gerador_bioquimica"),
    ("Conceitual",     "gerador_decoreba"),
    ("Direito",        "gerador_direito"),
    ("Embriologia",    "gerador_embriologia"),
    ("Engenharia",     "gerador_engenharia"),
    ("Farmacologia",   "gerador_farmacologia"),
    ("Fisiologia",     "gerador_fisiologia"),
    ("Genética",       "gerador_genetica"),
    ("Histologia",     "gerador_histologia"),
    ("Imunologia",     "gerador_imunologia"),
    # Interpretação fica de fora: seu gerar_lote exige a lista de trechos
    # de um livro, e as alternativas saem do texto analisado, não de uma
    # tabela de fatos — não é o alvo desta auditoria.
    ("Microbiologia",  "gerador_microbiologia"),
    ("Português",      "gerador_portugues"),
    ("Matemática",     "gerador_procedural"),
    ("Redes",          "gerador_redes"),
]

SEEDS = [1, 42, 777, 20260811, 31337, 999999, 123456, 8080]
POR_SEED = 250

# Artigos e preposições que abrem um sintagma sem mudar o referente.
ABERTURAS = ("o ", "a ", "os ", "as ", "um ", "uma ", "de ", "do ", "da ",
             "dos ", "das ", "no ", "na ", "ao ", "à ", "em ", "pelo ",
             "pela ", "seu ", "sua ")

# Pares em que a continência é o CONTEÚDO da questão, não um defeito:
# distinguir 1FN de 2FN, ou "recessiva ligada ao X" de "dominante ligada
# ao X", é exatamente o que se está cobrando.
ISENTOS = [
    (r"\b\d?fn\b", r"\b\d?fn\b"),          # formas normais
    (r"\bligad[ao] ao [xy]\b", r"\bligad[ao] ao [xy]\b"),
    (r"^tipo [ivx]+", r"^tipo [ivx]+"),    # Gell e Coombs
    (r"^camada \d", r"^camada \d"),

    # Transposição para a voz passiva: "O evento foi organizado." está
    # contido em "O evento foi organizado pelos alunos.", mas o comando
    # pede que o sentido seja MANTIDO, e a versão sem agente perde o
    # agente. A continência é o próprio conteúdo da questão.
    (r"\bfoi \w+[ao]\b", r"\bfoi \w+[ao]\b"),

    # Fila x Fila de prioridade, Pilha x Pilha dupla: o enunciado dá a
    # política de remoção, que separa uma da outra. Mesmo caso das
    # formas normais.
    (r"^(fila|pilha)\b", r"^(fila|pilha)\b"),

    # Vozes verbais: reflexiva, reflexiva recíproca e reflexiva indireta
    # são três denominações distintas da gramática, não graus da mesma.
    (r"^reflexiva\b", r"^reflexiva\b"),
]


def _sem_acento(t):
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _norm(texto):
    # O artigo sai ANTES de tirar o acento. Na ordem inversa, "nó
    # atrioventricular" virava "no atrioventricular", o "no " era lido
    # como preposição e sobrava "atrioventricular" — contido em
    # "fascículo atrioventricular". Alarme falso nascido da normalização.
    t = str(texto).lower()
    for ab in ABERTURAS:
        if t.startswith(ab):
            t = t[len(ab):]
            break
    t = _sem_acento(t)
    # Os dois-pontos PRECISAM sobreviver: trocados por espaço, o endereço
    # "…:e4d6::" virava prefixo alinhado de "…:e4d6:0:0:0" e toda questão
    # de IPv6 comprimido aparecia como sobreposição.
    t = re.sub(r"[^\w\s%/º²³,.:()-]", " ", t)
    return re.sub(r"\s+", " ", t).strip(" .;,")


def _isento(a, b):
    for pa, pb in ISENTOS:
        if re.search(pa, a) and re.search(pb, b):
            return True
    return False


# Conectivos que RESTRINGEM ou CONTRADIZEM o que veio antes. Quando a
# alternativa maior é a menor seguida de um deles, o acréscimo muda o
# valor de verdade — "involuntário" x "involuntário, mas modulável pela
# vontade" — e isso é distrator intencional, não ambiguidade.
#
# O que interessa de fato à auditoria é o outro caso: a maior ESPECIFICA
# a menor sem contradizê-la ("a tuba uterina" x "a ampola da tuba
# uterina"), e aí as duas podem ser marcadas.
QUALIFICADORES = re.compile(
    r"^(,\s*)?(mas|porem|contudo|todavia|embora|apenas|somente|so|exceto|"
    r"salvo|desde que|caso|se |ainda que|a menos que|nao |sem )")


def _contem_texto(a, b):
    """
    `a` é subcadeia de `b`, alinhada por palavra?

    Devolve None, "texto" (provável ambiguidade) ou "qualificado"
    (provável distrator intencional).
    """
    if a == b or len(a) < 4:
        return None
    m = re.search(r"(^|\s)" + re.escape(a) + r"($|\s|,)", b)
    if not m:
        return None
    if b.startswith(a):
        resto = b[len(a):].strip()
        if QUALIFICADORES.match(resto):
            return "qualificado"
    # A diferença pode vir na FRENTE: "consome ATP e ocorre contra o
    # gradiente" dentro de "não consome ATP e ocorre contra o gradiente".
    # A negação inverte a afirmação — é o distrator fazendo seu trabalho.
    if b.endswith(a):
        antes = b[:len(b) - len(a)].strip()
        if re.fullmatch(r"(nao|nunca|jamais|sem)", antes):
            return "qualificado"
    # Notação assintótica: "O(log n)" é subcadeia de "O(n log n)" sem que
    # uma inclua a outra em sentido algum.
    if re.search(r"\b(o|omega|theta)\s*\(", a):
        return None
    return "texto"


# A vírgula só separa itens quando NÃO está entre dígitos: em português
# "5,00 mg/L" é um número, e partir nela fazia o auditor comparar {5, 00
# mg/l} com {128, 00 mg/l} e acusar continência em toda questão de
# cálculo — dezenas de alarmes falsos.
_SEPARADOR = re.compile(r"(?<!\d),(?!\d)| e | ou |\+")


def _itens(texto):
    """
    Conjunto de itens de uma enumeração curta.

    Enumerações de NÚMEROS ficam de fora. O teste de conjunto existe
    para "IgG" dentro de "IgG e IgM"; aplicado a raízes de equação, ele
    comparava {-5, 3} com {-5, -3} e — como o filtro de tamanho descartava
    o item de um só caractere — enxergava continência onde havia apenas
    dois pares distintos de raízes.
    """
    if re.fullmatch(r"[\d.,%/\s-]+[a-z/²³ºµ]*", texto):
        return frozenset()
    partes = [p.strip() for p in _SEPARADOR.split(texto)]
    if not partes:
        return frozenset()
    # Descartar item por tamanho MUTILA o conjunto: "presente, mas
    # desprovida de lipopolissacarídeo" perdia o segundo item e virava
    # {presente}, subconjunto de qualquer coisa que comece por "presente".
    # Se algum item não couber na janela, o texto não é enumeração.
    if any(len(p) > 28 for p in partes):
        return frozenset()
    if all(re.fullmatch(r"-?[\d.,]+", p) for p in partes):
        return frozenset()
    return frozenset(partes)


def _contem_conjunto(a, b):
    # O qualificador vale aqui também: "involuntário" x "involuntário,
    # mas modulável pela vontade" escapava do teste de texto e reaparecia
    # como continência de conjunto.
    for x, y in ((a, b), (b, a)):
        if y.startswith(x) and QUALIFICADORES.match(y[len(x):].strip()):
            return False
    ia, ib = _itens(a), _itens(b)
    if not ia or not ib or ia == ib:
        return False
    # Só vale para enumerações mesmo: pelo menos um dos lados tem 2+ itens
    # e o outro é subconjunto próprio.
    if max(len(ia), len(ib)) < 2:
        return False
    return ia < ib or ib < ia


# ── Intervalos ────────────────────────────────────────────
NUM_EXTENSO = {
    "uma": 1, "um": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "doze": 12, "quinze": 15, "vinte": 20, "vinte e quatro": 24,
    "trinta": 30, "quarenta e oito": 48, "setenta e duas": 72,
}
UNIDADE_EM_HORAS = {
    "minuto": 1 / 60, "minutos": 1 / 60,
    "hora": 1.0, "horas": 1.0,
    "dia": 24.0, "dias": 24.0,
    "semana": 168.0, "semanas": 168.0,
    "mes": 720.0, "meses": 720.0,
}


def _valor(txt):
    txt = txt.strip()
    if txt.isdigit():
        return float(txt)
    return NUM_EXTENSO.get(txt)


def _intervalo_horas(texto):
    """Extrai (início, fim) em horas de expressões de tempo."""
    unid = None
    for u in UNIDADE_EM_HORAS:
        if re.search(r"\b" + u + r"\b", texto):
            unid = UNIDADE_EM_HORAS[u]
            break
    if unid is None:
        return None

    m = re.search(r"\bde ([\w ]+?) a ([\w ]+?)\b", texto)
    if m:
        a, b = _valor(m.group(1)), _valor(m.group(2))
        if a is not None and b is not None:
            return (a * unid, b * unid)

    m = re.search(r"\bentre (?:o|a|as|os)? ?([\w ]+?) e (?:o|a|as|os)? ?"
                  r"([\w ]+?)\b", texto)
    if m:
        a, b = _valor(m.group(1)), _valor(m.group(2))
        if a is not None and b is not None:
            return (a * unid, b * unid)

    m = re.search(r"\bmenos de ([\w]+)\b", texto)
    if m and _valor(m.group(1)) is not None:
        return (0.0, _valor(m.group(1)) * unid)

    m = re.search(r"\b(?:mais de|apos|acima de) ([\w]+)\b", texto)
    if m and _valor(m.group(1)) is not None:
        return (_valor(m.group(1)) * unid, 1e9)

    return None


def _intersecta(a, b):
    return a[0] < b[1] and b[0] < a[1]


# ══════════════════════════════════════════════════════════
#  VARREDURA
# ══════════════════════════════════════════════════════════

def auditar(rotulo, modulo):
    try:
        m = importlib.import_module(modulo)
    except ImportError:
        return None

    graves, leves, vistas, total = {}, {}, set(), 0

    for seed in SEEDS:
        try:
            lote = m.gerar_lote(POR_SEED, seed=seed)
        except TypeError:
            lote = m.gerar_lote(POR_SEED)
        for q in lote or []:
            total += 1
            alts = q.get("alternativas") or {}
            gab = q.get("gabarito")
            normalizadas = {L: _norm(v) for L, v in alts.items()}
            letras = list(alts)

            for i in range(len(letras)):
                for j in range(i + 1, len(letras)):
                    La, Lb = letras[i], letras[j]
                    a, b = normalizadas[La], normalizadas[Lb]
                    if not a or not b or _isento(a, b):
                        continue

                    motivo = _contem_texto(a, b) or _contem_texto(b, a)
                    if motivo == "qualificado":
                        motivo = None      # distrator intencional
                    if motivo:
                        pass
                    elif _contem_conjunto(a, b):
                        motivo = "conjunto"
                    else:
                        ia, ib = _intervalo_horas(a), _intervalo_horas(b)
                        if ia and ib and _intersecta(ia, ib):
                            motivo = "intervalo"
                    if not motivo:
                        continue

                    chave = (q.get("topico", "?"), motivo,
                             tuple(sorted((a, b))))
                    if chave in vistas:
                        continue
                    vistas.add(chave)
                    alvo = graves if gab in (La, Lb) else leves
                    alvo[chave] = {
                        "topico": q.get("topico", "?"),
                        "motivo": motivo,
                        "a": alts[La], "b": alts[Lb],
                        "correta": alts.get(gab, ""),
                        "enunciado": q.get("enunciado", "")[:150],
                    }

    return {"rotulo": rotulo, "total": total,
            "graves": list(graves.values()), "leves": list(leves.values())}


def main():
    alvos = sys.argv[1:]
    escolhidos = [
        (r, mo) for r, mo in GERADORES
        if not alvos or any(a.lower() in mo.lower() or a.lower() in r.lower()
                            for a in alvos)
    ]

    print("═" * 64)
    print("  AUDITORIA — ALTERNATIVAS QUE ENGLOBAM OUTRAS")
    print("═" * 64)

    tg = tl = 0
    for rotulo, modulo in escolhidos:
        r = auditar(rotulo, modulo)
        if r is None:
            print(f"\n  ⏭  {rotulo}: módulo ausente")
            continue
        tg += len(r["graves"])
        tl += len(r["leves"])
        marca = "❌" if r["graves"] else ("⚠ " if r["leves"] else "✅")
        print(f"\n  {marca} {rotulo:<20} {r['total']:>5} questões  "
              f"graves: {len(r['graves']):<3} leves: {len(r['leves'])}")
        for d in r["graves"]:
            print(f"      ├─ [{d['motivo']}] {d['topico']}")
            print(f"      │   {d['enunciado']}")
            print(f"      │   A: {d['a']}")
            print(f"      │   B: {d['b']}")
            print(f"      │   correta: {d['correta']}")
        for d in r["leves"][:4]:
            print(f"      ·  [{d['motivo']}] {d['topico']}: "
                  f"{d['a']!r} ~ {d['b']!r}")
        if len(r["leves"]) > 4:
            print(f"      ·  (+{len(r['leves']) - 4} outros pares de "
                  f"distratores)")

    print("\n" + "═" * 64)
    if tg:
        print(f"  ❌ {tg} SOBREPOSIÇÃO(ÕES) ENVOLVENDO A RESPOSTA CORRETA")
    else:
        print("  🎉 NENHUMA ALTERNATIVA CORRETA DISPUTA COM OUTRA")
    print(f"     ({tl} pares de distratores parecidos, sem efeito no "
          f"gabarito)")
    print("═" * 64)
    sys.exit(1 if tg else 0)


if __name__ == "__main__":
    main()
