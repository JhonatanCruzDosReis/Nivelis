"""
=============================================================
  TESTE 4 — CONSISTÊNCIA DA TABELA DE FATOS
=============================================================
  Exclusivo do gerador_decoreba, cujo gabarito NÃO é calculado
  e sim consultado. Este teste não valida se um fato é
  verdadeiro no mundo (isso exige fonte externa e revisão
  humana) — ele valida a CONSISTÊNCIA INTERNA da tabela e das
  questões geradas a partir dela.

  CHECAGENS:
    1. Chave duplicada com valores diferentes
       (ex.: SSH aparecendo como 22 e como 23)
    2. Valor ambíguo entre chaves
       (ex.: duas portas iguais para serviços diferentes)
    3. Distrator que também é verdadeiro para a pergunta
       (ex.: perguntar complexidade do Merge Sort e ter
        O(n log n) em duas alternativas por caminhos distintos)
    4. Gabarito ausente ou repetido entre as alternativas
    5. Explicação que não menciona a resposta correta
    6. Cobertura: todo fato da tabela é alcançável

  USO: python teste_4_fatos.py [quantidade]
=============================================================
"""

import sys
import re
from collections import Counter, defaultdict

sys.path.insert(0, ".")


def checar_tabelas(mod) -> list:
    """Consistência interna das tabelas de fatos declaradas no módulo."""
    problemas = []

    # 1 e 2 — PORTAS: serviço único e porta única
    servicos = [s for s, _ in mod.PORTAS]
    portas   = [p for _, p in mod.PORTAS]
    for s, n in Counter(servicos).items():
        if n > 1:
            problemas.append(("porta_servico_duplicado", f"'{s}' aparece {n}x"))
    for p, n in Counter(portas).items():
        if n > 1:
            iguais = [s for s, pp in mod.PORTAS if pp == p]
            problemas.append(("porta_valor_ambiguo",
                              f"porta {p} atribuída a {iguais}"))

    # HTTP: código único, nome único
    codigos = [c for c, _, _ in mod.HTTP_CODIGOS]
    nomes   = [n for _, n, _ in mod.HTTP_CODIGOS]
    descs   = [d for _, _, d in mod.HTTP_CODIGOS]
    for c, n in Counter(codigos).items():
        if n > 1:
            problemas.append(("http_codigo_duplicado", f"código {c} aparece {n}x"))
    for nm, n in Counter(nomes).items():
        if n > 1:
            problemas.append(("http_nome_duplicado", f"'{nm}' aparece {n}x"))
    for d, n in Counter(descs).items():
        if n > 1:
            problemas.append(("http_descricao_ambigua", f"'{d}' aparece {n}x"))

    # OSI: número 1..7 sem repetição, nomes únicos
    nums = [n for n, _, _, _ in mod.OSI]
    if sorted(nums) != list(range(1, 8)):
        problemas.append(("osi_numeracao", f"níveis: {sorted(nums)} (esperado 1..7)"))
    for nm, n in Counter(n for _, n, _, _ in mod.OSI).items():
        if n > 1:
            problemas.append(("osi_nome_duplicado", f"'{nm}' aparece {n}x"))
    for f, n in Counter(f for _, _, f, _ in mod.OSI).items():
        if n > 1:
            problemas.append(("osi_funcao_ambigua", f"'{f}' aparece {n}x"))

    # Protocolo → camada: coerente com a tabela OSI
    mapa_osi = {n: nm for n, nm, _, _ in mod.OSI}
    for proto, num, nome in mod.PROTOCOLO_CAMADA:
        if mapa_osi.get(num) != nome:
            problemas.append(("protocolo_camada_incoerente",
                              f"{proto}: nível {num} deveria ser "
                              f"'{mapa_osi.get(num)}', consta '{nome}'"))

    # ACID / formas normais / estruturas: descrição única
    # ACID tem 3 campos (nome, artigo, descrição) — normaliza para (chave, valor)
    acid_pares = [(n, d) for n, _, d in mod.ACID]
    for nome_tab, tabela in [("ACID", acid_pares),
                             ("FORMAS_NORMAIS", mod.FORMAS_NORMAIS),
                             ("ESTRUTURAS", mod.ESTRUTURAS),
                             ("PERCURSOS", mod.PERCURSOS),
                             ("PARADIGMAS", mod.PARADIGMAS),
                             ("PILARES_OO", mod.PILARES_OO),
                             ("SCRUM", mod.SCRUM)]:
        chaves = [k for k, _ in tabela]
        vals   = [v for _, v in tabela]
        for k, n in Counter(chaves).items():
            if n > 1:
                problemas.append((f"{nome_tab.lower()}_chave_duplicada", f"'{k}' {n}x"))
        for v, n in Counter(vals).items():
            if n > 1:
                problemas.append((f"{nome_tab.lower()}_valor_ambiguo", f"'{v[:45]}' {n}x"))

    # SQL: um comando não pode estar em duas categorias
    onde = defaultdict(list)
    for sigla, _, comandos in mod.SQL_CATEGORIAS:
        for c in comandos:
            onde[c].append(sigla)
    for cmd, cats in onde.items():
        if len(cats) > 1:
            problemas.append(("sql_comando_ambiguo", f"{cmd} em {cats}"))

    # Complexidades: (algoritmo, caso) deve ser único
    chaves = [(a, c) for a, c, _ in mod.COMPLEXIDADES]
    for k, n in Counter(chaves).items():
        if n > 1:
            problemas.append(("complexidade_duplicada", f"{k} aparece {n}x"))

    return problemas


def checar_questoes(questoes) -> list:
    """Consistência das questões geradas a partir das tabelas."""
    problemas = []
    for q in questoes:
        alts = q["alternativas"]
        gab  = q["gabarito"]
        expl = q["explicacao"]

        if gab not in alts:
            problemas.append((q["topico"], "gabarito fora das alternativas", ""))
            continue

        valores = [str(v).strip() for v in alts.values()]
        if len(set(valores)) != len(valores):
            repetidos = [v for v, n in Counter(valores).items() if n > 1]
            problemas.append((q["topico"], f"alternativas repetidas: {repetidos}", ""))

        # A explicação deve conter a resposta correta (ou parte significativa)
        resposta = str(alts[gab]).strip()
        nucleo = resposta.split("—")[0].strip() if "—" in resposta else resposta
        if len(nucleo) > 3 and nucleo.lower() not in expl.lower():
            problemas.append((q["topico"],
                              f"explicação não menciona a resposta '{nucleo[:40]}'",
                              expl[:70]))

        # Nenhuma alternativa pode aparecer também no enunciado como se fosse dado
        # (isso entregaria a resposta)
        if nucleo.lower() in q["enunciado"].lower() and len(nucleo) > 6:
            problemas.append((q["topico"],
                              f"resposta '{nucleo[:35]}' aparece no enunciado", ""))

        # O CONTEXTO (parte antes da pergunta) não pode citar o próprio termo
        # perguntado. Ex.: "sendo a camada Física o nível 1... a camada Física
        # corresponde a qual nível?" — o aluno lê a resposta no enunciado.
        enun = q["enunciado"]
        m_termo = re.search(r'camada (?:de )?([A-ZÀ-Ý]\w+)', enun)
        if m_termo:
            termo = m_termo.group(1)
            # tudo que vem antes da pergunta propriamente dita
            corte = min([enun.find(p) for p in
                         ("Qual", "A camada", "Que nível", "Em qual", "Trata-se")
                         if enun.find(p) > 0] or [len(enun)])
            contexto = enun[:corte]
            if termo in contexto and re.search(r'qual nível|número da camada|'
                                               r'Que nível', enun):
                problemas.append((q["topico"],
                                  f"contexto cita '{termo}', que é a resposta", ""))
    return problemas


def checar_cobertura(mod, n_amostra=4000) -> list:
    """Todo fato da tabela deve ser alcançável pela geração."""
    problemas = []
    lote = mod.gerar_lote(n_amostra, seed=4242)
    texto = " ".join(q["enunciado"] + " " + str(q["alternativas"]) for q in lote)

    nao_vistos = []
    for servico, porta in mod.PORTAS:
        if servico not in texto:
            nao_vistos.append(f"porta:{servico}")
    for cod, nome, _ in mod.HTTP_CODIGOS:
        if str(cod) not in texto and nome not in texto:
            nao_vistos.append(f"http:{cod}")
    for _, nome, _, _ in mod.OSI:
        if nome not in texto:
            nao_vistos.append(f"osi:{nome}")

    if nao_vistos:
        problemas.append(("fato_inalcancavel",
                          f"{len(nao_vistos)} fato(s) nunca gerados: "
                          f"{nao_vistos[:6]}"))
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    import gerador_decoreba as mod

    print("═" * 62)
    print("  TESTE 4 — CONSISTÊNCIA DA TABELA DE FATOS")
    print("═" * 62)

    total = 0

    print("\n  ── 4a) Consistência interna das tabelas ──\n")
    p1 = checar_tabelas(mod)
    total += len(p1)
    if p1:
        for regra, det in p1:
            print(f"     ❌ {regra}: {det}")
    else:
        print("     ✅ Nenhuma duplicata, ambiguidade ou incoerência")

    print(f"\n  ── 4b) Questões geradas ({qtd}) ──\n")
    lote = mod.gerar_lote(qtd, seed=31337)
    p2 = checar_questoes(lote)
    total += len(p2)
    if p2:
        vistos = set()
        for topico, det, ctx in p2:
            chave = (topico, det[:30])
            if chave in vistos: continue
            vistos.add(chave)
            print(f"     ❌ [{topico}] {det}")
            if ctx: print(f"          {ctx}")
            if len(vistos) >= 8: break
        print(f"     (total: {len(p2)} ocorrências)")
    else:
        print("     ✅ Gabaritos válidos, sem alternativa repetida,")
        print("        explicações mencionam a resposta")

    print("\n  ── 4c) Cobertura da tabela ──\n")
    p3 = checar_cobertura(mod)
    total += len(p3)
    if p3:
        for regra, det in p3:
            print(f"     ❌ {regra}: {det}")
    else:
        print("     ✅ Todos os fatos são alcançáveis pela geração")

    print("\n" + "═" * 62)
    print(f"  {'🎉 TESTE 4 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 62)
    sys.exit(1 if total else 0)
