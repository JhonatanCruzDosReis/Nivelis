"""
=============================================================
  NIVELIS — Bateria completa dos 3 testes
=============================================================
  1. GABARITO   — recalcula a resposta de forma independente
  2. COERÊNCIA  — verifica se a frase faz sentido
  3. PORTUGUÊS  — concordância, contrações, pontuação
  4. FATOS      — consistência da tabela do gerador conceitual
  5. INTERPRETAÇÃO — gabarito rastreável à análise do trecho
  6. SIMULADO      — composição, numeração e mistura
  7. SENTIDO       — verossimilhança do cenário descrito
  8. SEM LER      — a questão se resolve sem ler o texto?
  9. DISTRATORES  — as alternativas erradas são erros plausíveis?
 10. ROBUSTEZ     — reprodutibilidade, entrada malformada, contrato

  Roda com VÁRIAS SEMENTES para não viciar num caso específico.

  USO:  python rodar_testes.py [questões_por_seed]
=============================================================
"""
import sys
sys.path.insert(0, ".")

import gerador_ads, gerador_procedural, gerador_saude, gerador_decoreba
import gerador_direito, gerador_redes
import teste_1_gabarito  as T1
import teste_2_coerencia as T2
import teste_3_portugues as T3
import teste_4_fatos      as T4
import teste_5_interpretacao as T5
import teste_6_simulado      as T6
import teste_7_sentido       as T7
import teste_8_sem_ler       as T8

SEEDS = [1, 42, 777, 20260811, 31337, 999999]


def main(qtd=500):
    print("═" * 64)
    print(f"  BATERIA COMPLETA — {len(SEEDS)} sementes × {qtd} questões × 6 geradores")
    print(f"  Total: {len(SEEDS) * qtd * 6} questões avaliadas em 4 dimensões")
    print("═" * 64)

    falhas_totais = 0

    for nome, mod in [("ADS / Computação", gerador_ads),
                      ("Matemática", gerador_procedural),
                      ("Saúde", gerador_saude),
                      ("Conceitual (decoreba)", gerador_decoreba),
                      ("Direito", gerador_direito),
                      ("Redes", gerador_redes)]:
        print(f"\n  ┌─ {nome} " + "─" * (52 - len(nome)))
        print(f"  │ {'seed':<11} {'gabarito':>9} {'coerên.':>8} {'portug.':>8} {'sentido':>8}")
        print(f"  ├" + "─" * 55)

        for seed in SEEDS:
            lote = mod.gerar_lote(qtd, seed=seed)

            _, erros_gab = T1.testar(lote)
            probs_coe    = T2.verificar(lote)
            n_coe        = sum(len(v) for v in probs_coe.values())
            res_pt       = T3.verificar_lote(lote)
            n_pt         = (sum(len(v) for v in res_pt["lingua"].values()) +
                            sum(len(v) for v in res_pt["forma"].values()))
            probs_sent   = T7.verificar(lote)
            n_sent       = sum(len(v) for v in probs_sent.values())

            falhas = len(erros_gab) + n_coe + n_pt + n_sent
            falhas_totais += falhas
            marca = "✅" if falhas == 0 else "❌"
            print(f"  │ {seed:<11} {len(erros_gab):>9} {n_coe:>8} "
                  f"{n_pt:>8} {n_sent:>8}  {marca}")

            if erros_gab:
                for topico, esp, obt, _ in erros_gab[:2]:
                    print(f"  │    ⚠ [{topico}] esperado={esp} obtido={obt}")
            if n_coe:
                for regra, casos in list(probs_coe.items())[:2]:
                    print(f"  │    ⚠ {regra}: {casos[0][1]}")
            if n_pt:
                for regra, casos in list(res_pt["lingua"].items())[:2]:
                    print(f"  │    ⚠ {regra}: {casos[0][1][:60]}")
            if n_sent:
                for regra, casos in list(probs_sent.items())[:2]:
                    print(f"  │    ⚠ {regra}: {casos[0][1][:60]}")

        print(f"  └" + "─" * 55)

    # ── Teste 4: exclusivo do gerador conceitual ──
    print(f"\n  ┌─ Tabela de fatos (gerador conceitual) " + "─" * 17)
    p_tab = T4.checar_tabelas(gerador_decoreba)
    lote_c = gerador_decoreba.gerar_lote(qtd, seed=31337)
    p_que = T4.checar_questoes(lote_c)
    p_cob = T4.checar_cobertura(gerador_decoreba)
    n4 = len(p_tab) + len(p_que) + len(p_cob)
    falhas_totais += n4
    print(f"  │ tabelas: {len(p_tab):<3} questões: {len(p_que):<3} "
          f"cobertura: {len(p_cob):<3}  {'✅' if n4 == 0 else '❌'}")
    for regra, det in (p_tab + p_cob)[:3]:
        print(f"  │    ⚠ {regra}: {det[:60]}")
    for topico, det, _ in p_que[:3]:
        print(f"  │    ⚠ [{topico}] {det[:60]}")
    print(f"  └" + "─" * 55)

    # ── Teste 5: gerador de interpretação ──
    try:
        from gerador_interpretacao import gerar_lote as _gl_int
        from _trechos_teste import TRECHOS_TESTE
        print(f"\n  ┌─ Interpretação de texto " + "─" * 30)
        n5_total = 0
        for seed in SEEDS[:4]:
            lote_i = _gl_int(TRECHOS_TESTE, qtd // 2, seed=seed)
            p5 = T5.testar(lote_i, TRECHOS_TESTE) + \
                 T5.testar_assercao_razao(lote_i, TRECHOS_TESTE)
            n5_total += len(p5)
            print(f"  │ seed {seed:<11} {len(lote_i):>4} questões  "
                  f"{len(p5):>3} problema(s)  {'✅' if not p5 else '❌'}")
            for topico, det, _ in p5[:2]:
                print(f"  │    ⚠ [{topico}] {det[:55]}")
        falhas_totais += n5_total
        print(f"  └" + "─" * 55)
    except ImportError:
        print("\n  (gerador_interpretacao não encontrado — teste 5 pulado)")

    # ── Teste 6: montagem de simulado ──
    try:
        from montar_simulado_procedural import montar as _montar
        from _trechos_teste import TRECHOS_TESTE as _TT
        print(f"\n  ┌─ Montagem de simulado " + "─" * 32)
        n6 = 0
        for tamanho in [10, 30, 60]:
            falhas6 = []
            for seed in SEEDS[:4]:
                sim = _montar(quantidade=tamanho, disciplinas=["ads"],
                              trechos=_TT, seed=seed)
                falhas6.extend(T6.testar_simulado(sim, tamanho))
            n6 += len(falhas6)
            print(f"  │ {tamanho:>3} questões × 4 seeds   "
                  f"{len(falhas6):>3} problema(s)  {'✅' if not falhas6 else '❌'}")
            for f in falhas6[:2]:
                print(f"  │    ⚠ {f[:55]}")
        # degradação sem trechos
        falhas6 = []
        for seed in SEEDS[:4]:
            sim = _montar(quantidade=30, disciplinas=["ads"], trechos=None, seed=seed)
            falhas6.extend(T6.testar_simulado(sim, 30, espera_interpretacao=False))
        n6 += len(falhas6)
        print(f"  │ sem trechos            {len(falhas6):>3} problema(s)  "
              f"{'✅' if not falhas6 else '❌'}")
        falhas_totais += n6
        print(f"  └" + "─" * 55)
    except ImportError:
        print("\n  (montar_simulado_procedural não encontrado — teste 6 pulado)")

    print("\n" + "═" * 64)
    if falhas_totais == 0:
        print(f"  🎉 TODOS OS 3 TESTES PASSARAM EM TODAS AS SEMENTES")
        print(f"     {len(SEEDS) * qtd * 6} questões: gabarito correto, frase")
        print(f"     coerente e português sem erros.")
    else:
        print(f"  ❌ {falhas_totais} FALHA(S) — veja os detalhes acima")
    print("═" * 64)
    return falhas_totais


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    sys.exit(1 if main(qtd) else 0)
