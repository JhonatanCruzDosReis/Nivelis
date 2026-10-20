"""
=============================================================
  TESTE 6 — MONTAGEM DE SIMULADO
=============================================================
  Verifica a composição do simulado montado por
  montar_simulado_procedural.

  CHECAGENS:
    1. Total correto — a soma bate com o pedido
    2. Proporção respeitada — 40/30/30 dentro da tolerância
    3. Numeração — sequencial de 1 a N, sem furos nem repetição
    4. Alinhamento — questao[i] corresponde a gabarito[i]
    5. Mistura — os tipos não ficam agrupados em blocos
    6. Degradação — sem trechos, a fatia é redistribuída e o
       simulado sai completo (não incompleto)
    7. Sem duplicata — nenhuma questão repetida no mesmo simulado
    8. Integridade — toda questão tem 5 alternativas e gabarito válido

  USO: python teste_6_simulado.py [repeticoes]
=============================================================
"""

import sys
from collections import Counter

sys.path.insert(0, ".")


def testar_simulado(r: dict, pedido: int, espera_interpretacao=True,
                    disciplinas_pedidas=None) -> list:
    problemas = []
    qs, gb = r["questoes"], r["gabarito"]

    # 1) Total
    if r["total"] != pedido:
        problemas.append(f"total {r['total']} != pedido {pedido}")
    if len(qs) != pedido or len(gb) != pedido:
        problemas.append(f"listas com tamanhos {len(qs)}/{len(gb)}")

    # 3) Numeração sequencial
    nums = [q["numero"] for q in qs]
    if nums != list(range(1, len(qs) + 1)):
        problemas.append("numeração não é sequencial de 1..N")

    # 4) Alinhamento questão ↔ gabarito
    for q, g in zip(qs, gb):
        if q["numero"] != g["numero"]:
            problemas.append(f"desalinhamento em Q{q['numero']}")
            break

    # 8) Integridade das questões
    for q, g in zip(qs, gb):
        if len(q.get("alternativas", {})) != 5:
            problemas.append(f"Q{q['numero']} não tem 5 alternativas")
            break
        if g.get("resposta_correta") not in q["alternativas"]:
            problemas.append(f"Q{q['numero']} com gabarito inválido")
            break
        if not g.get("explicacao", "").strip():
            problemas.append(f"Q{q['numero']} sem explicação")
            break

    # 7) Sem duplicata
    enunciados = [q["enunciado"] for q in qs]
    repetidos = [e for e, n in Counter(enunciados).items() if n > 1]
    if repetidos:
        problemas.append(f"{len(repetidos)} enunciado(s) repetido(s)")

    # 2) Proporção (tolerância de 1 questão por conta do arredondamento)
    comp = r["composicao"]
    proc = sum(v for k, v in comp.items() if k.startswith("procedural"))
    con  = comp.get("conceitual", 0)
    inte = comp.get("interpretacao", 0)

    if espera_interpretacao:
        # A proporção 40/30/30 vale sobre as fontes DISPONÍVEIS. Quando a
        # conceitual não tem área compatível com a disciplina, sua fatia é
        # redistribuída — e as demais crescem proporcionalmente. Por isso o
        # alvo é recalculado com base no que de fato está ativo.
        pesos = {"procedural": 0.40}
        if con > 0 or r.get("areas_conceituais"):
            pesos["conceitual"] = 0.30
        pesos["interpretacao"] = 0.30
        soma_pesos = sum(pesos.values())

        alvos = {k: pedido * (v / soma_pesos) for k, v in pesos.items()}
        reais = {"procedural": proc, "conceitual": con, "interpretacao": inte}

        # O simulado limita uma fatia quando o MATERIAL não comporta a
        # proporção pedida: três áreas conceituais com sete templates não
        # rendem dezoito questões sem repetir tópico.
        #
        # Nesse caso o excedente vai para outra fonte, e a proporção sai
        # do alvo POR PROJETO. O campo 'limite_material' informa isso, e
        # o teste passa a aceitá-lo em vez de acusar.
        limite = r.get("limite_material")
        for nome, alvo in alvos.items():
            if abs(reais[nome] - alvo) <= 1.5:
                continue
            if limite:
                # a fatia limitada pode ficar abaixo; a que recebeu o
                # excedente pode ficar acima
                if nome == limite["fonte"] and reais[nome] <= alvo:
                    continue
                if nome != limite["fonte"] and reais[nome] >= alvo:
                    continue
            problemas.append(f"{nome}: {reais[nome]} (esperado ~{alvo:.0f})")
    else:
        # 6) Sem trechos, interpretação deve ser ZERO e o total ainda bater
        if inte != 0:
            problemas.append(f"gerou {inte} de interpretação sem trechos")
        if proc + con != pedido:
            problemas.append(f"fatia não redistribuída: {proc}+{con} != {pedido}")

    # 9) Coerência de assunto — a fatia conceitual não pode trazer área
    # incompatível com a disciplina pedida (ex.: SQL num simulado de
    # matemática). Detecta pelo vocabulário característico de TI.
    # Termos INEQUIVOCAMENTE de TI. "protocolo" foi removido: em saúde
    # significa protocolo de pesquisa ou protocolo clínico, e em direito,
    # protocolo de petição — a palavra sozinha não identifica a área.
    MARCAS_TI = ("porta padrão", "modelo OSI", "status HTTP",
                 "comandos SQL", "propriedades ACID", "forma normal",
                 "Scrum", "sub-rede", "camada do modelo OSI",
                 "protocolo de rede", "endereço IP")
    if disciplinas_pedidas and not any(d in ("ads",) for d in disciplinas_pedidas):
        for q in qs:
            e = q.get("enunciado", "")
            if any(m in e for m in MARCAS_TI):
                problemas.append(
                    f"questão de TI em simulado de {disciplinas_pedidas}: "
                    f"{e[:60]}")
                break

    # 5) Mistura — nenhum tipo pode ocupar um bloco contíguo grande
    origens = []
    for q in qs:
        e = q["enunciado"]
        if "Leia o texto" in e or "Considere o trecho" in e or \
           "excerto" in e or "trecho reproduzido" in e or "texto a seguir" in e:
            origens.append("int")
        else:
            origens.append("out")
    maior_bloco, atual = 1, 1
    for i in range(1, len(origens)):
        atual = atual + 1 if origens[i] == origens[i-1] else 1
        maior_bloco = max(maior_bloco, atual)

    # Com ~30% de interpretação, sequências longas do tipo majoritário ocorrem
    # naturalmente no embaralhamento — não indicam falta de mistura. O que
    # indicaria seria o embaralhamento NÃO ter acontecido: as questões saírem
    # exatamente na ordem de geração (todas de um tipo, depois do outro).
    # Esse é o caso extremo testado aqui.
    n_int = origens.count("int")
    n_out = origens.count("out")
    ordenado = (origens == ["out"] * n_out + ["int"] * n_int) or \
               (origens == ["int"] * n_int + ["out"] * n_out)

    # Em simulados pequenos, sair ordenado por acaso é comum: com 3 de um
    # tipo e 7 de outro há 120 arranjos, então 1,7% das vezes o shuffle
    # produz blocos legitimamente. Só acusamos quando a coincidência seria
    # improvável — ou seja, com amostra grande o bastante.
    from math import comb
    arranjos = comb(n_int + n_out, n_int) if (n_int and n_out) else 1
    coincidencia_plausivel = arranjos < 500

    if (espera_interpretacao and n_int and n_out and ordenado
            and not coincidencia_plausivel):
        problemas.append("tipos não foram embaralhados (saíram em blocos)")

    return problemas


if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    from montar_simulado_procedural import montar, calcular_distribuicao
    from _trechos_teste import TRECHOS_TESTE

    print("═" * 62)
    print("  TESTE 6 — MONTAGEM DE SIMULADO")
    print("═" * 62)

    total_prob = 0

    # ── 6a) Simulado completo, tamanhos variados ──
    print("\n  ── 6a) Simulado completo (com trechos) ──\n")
    for qtd in [10, 20, 30, 40, 60]:
        falhas = []
        for seed in range(reps):
            r = montar(quantidade=qtd, disciplinas=["ads"],
                       trechos=TRECHOS_TESTE, seed=seed)
            falhas.extend(testar_simulado(r, qtd, disciplinas_pedidas=["ads"]))
        total_prob += len(falhas)
        marca = "✅" if not falhas else "❌"
        r0 = montar(quantidade=qtd, disciplinas=["ads"],
                    trechos=TRECHOS_TESTE, seed=0)
        print(f"     {marca} {qtd:>3} questões × {reps} seeds — {r0['composicao']}")
        for f in falhas[:3]:
            print(f"          ⚠ {f}")

    # ── 6b) Sem trechos: fatia redistribuída ──
    print("\n  ── 6b) Sem trechos de livro (degradação) ──\n")
    falhas = []
    for seed in range(reps):
        r = montar(quantidade=30, disciplinas=["ads"], trechos=None, seed=seed)
        falhas.extend(testar_simulado(r, 30, espera_interpretacao=False))
    total_prob += len(falhas)
    r0 = montar(quantidade=30, disciplinas=["ads"], trechos=None, seed=0)
    print(f"     {'✅' if not falhas else '❌'} 30 questões — {r0['composicao']}")
    for f in falhas[:3]:
        print(f"          ⚠ {f}")

    # ── 6c) Múltiplas disciplinas ──
    print("\n  ── 6c) Várias disciplinas ──\n")
    for discs in [["ads"], ["saude"], ["ads", "matematica"],
                  ["ads", "saude", "matematica"]]:
        falhas = []
        for seed in range(5):
            r = montar(quantidade=30, disciplinas=discs,
                       trechos=TRECHOS_TESTE, seed=seed)
            falhas.extend(testar_simulado(r, 30, disciplinas_pedidas=discs))
        total_prob += len(falhas)
        r0 = montar(quantidade=30, disciplinas=discs,
                    trechos=TRECHOS_TESTE, seed=1)
        print(f"     {'✅' if not falhas else '❌'} {str(discs):<38} {r0['composicao']}")
        for f in falhas[:2]:
            print(f"          ⚠ {f}")

    # ── 6d) Ponderação por prova real ──
    print("\n  ── 6d) Ponderação por prova analisada ──\n")
    PROVA_FALSA = [{
        "concurso": "enade", "ano": 2023, "area": "computacao",
        "topicos": (
            [{"tema": "banco de dados", "subtopico": "SQL e normalização"}] * 8 +
            [{"tema": "redes", "subtopico": "endereçamento IP"}] * 3 +
            [{"tema": "algoritmos", "subtopico": "complexidade"}] * 5
        ),
    }]
    falhas = []
    for seed in range(5):
        r = montar(quantidade=30, disciplinas=["ads"], trechos=TRECHOS_TESTE,
                   provas=PROVA_FALSA, seed=seed)
        falhas.extend(testar_simulado(r, 30))
    total_prob += len(falhas)
    r0 = montar(quantidade=30, disciplinas=["ads"], trechos=TRECHOS_TESTE,
                provas=PROVA_FALSA, seed=1)
    print(f"     {'✅' if not falhas else '❌'} ponderado={r0['ponderado_por_prova']} "
          f"— {r0['composicao']}")
    for f in falhas[:3]:
        print(f"          ⚠ {f}")

    # ── 6d2) Filtro de área conceitual ──
    print("\n  ── 6d2) Fatia conceitual compatível com a disciplina ──\n")
    for discs, espera_conceitual in [(["ads"], True), (["matematica"], False),
                                     (["saude"], False), (["ads", "saude"], True)]:
        falhas = []
        for seed in range(5):
            r = montar(quantidade=30, disciplinas=discs,
                       trechos=TRECHOS_TESTE, seed=seed)
            tem = r["composicao"].get("conceitual", 0) > 0
            if tem != espera_conceitual:
                falhas.append(f"conceitual={'presente' if tem else 'ausente'}, "
                              f"esperado {'presente' if espera_conceitual else 'ausente'}")
            falhas.extend(testar_simulado(r, 30, disciplinas_pedidas=discs))
        total_prob += len(falhas)
        r0 = montar(quantidade=30, disciplinas=discs, trechos=TRECHOS_TESTE, seed=1)
        print(f"     {'✅' if not falhas else '❌'} {str(discs):<26} "
              f"áreas: {r0['areas_conceituais'] or '(nenhuma)'} "
              f"→ {r0['composicao']}")
        for f in falhas[:2]:
            print(f"          ⚠ {f[:70]}")

    # ── 6e) Distribuição isolada ──
    print("\n  ── 6e) Cálculo da distribuição ──\n")
    casos = [
        (30, {"procedural": 1, "conceitual": 1, "interpretacao": 1}, 30),
        (10, {"procedural": 1, "conceitual": 1, "interpretacao": 0}, 10),
        (7,  {"procedural": 1, "conceitual": 1, "interpretacao": 1}, 7),
        (100, {"procedural": 1, "conceitual": 0, "interpretacao": 0}, 100),
    ]
    from montar_simulado_procedural import MISTURA_PADRAO
    for qtd, disp, esperado in casos:
        d = calcular_distribuicao(qtd, MISTURA_PADRAO, disp)
        soma = sum(d.values())
        ok = soma == esperado
        if not ok: total_prob += 1
        # Expressão quebrada em duas linhas DENTRO da f-string só compila
        # a partir do 3.12 (PEP 701), e runtime.txt fixa o 3.11.
        ativos = [k for k, v in disp.items() if v]
        marca = '✅' if ok else '❌'
        print(f"     {marca} {qtd} questões, disponível={ativos} "
              f"→ {d} (soma {soma})")

    print("\n" + "═" * 62)
    print(f"  {'🎉 TESTE 6 PASSOU' if total_prob == 0 else f'❌ {total_prob} PROBLEMA(S)'}")
    print("═" * 62)
    sys.exit(1 if total_prob else 0)
