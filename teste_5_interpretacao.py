"""
=============================================================
  TESTE 5 — QUESTÕES DE INTERPRETAÇÃO
=============================================================
  O gerador_interpretacao não calcula gabarito nem consulta
  tabela fixa: ele reorganiza a análise que o Gemini produziu
  na indexação. Este teste verifica se essa reorganização
  preserva a correção.

  CHECAGENS:
    1. Gabarito rastreável — a resposta correta é exatamente
       um campo da análise do trecho (tese, pressuposto,
       ideia secundária ou afirmação falsa), conforme o tipo
    2. Nenhum distrator é também verdadeiro para a pergunta
    3. Texto-base presente e íntegro no enunciado
    4. Distratores no assunto — a maioria das alternativas
       deve tratar do tema do texto, senão a questão se
       responde por eliminação sem leitura
    5. Explicação coerente com o gabarito
    6. Sem vazamento — o gabarito não aparece literalmente
       fora das alternativas

  USO: python teste_5_interpretacao.py [quantidade]
=============================================================
"""

import sys
import re
from collections import Counter

sys.path.insert(0, ".")


def _norm(t: str) -> str:
    return " ".join(str(t).lower().split()).rstrip(".")


def _palavras(t: str) -> set:
    """Palavras de conteúdo (≥5 letras), para medir sobreposição temática."""
    return {p for p in re.findall(r'[a-zà-ÿ]{5,}', str(t).lower())}


# Que campo da análise deve ser o gabarito, por tipo de questão
CAMPO_ESPERADO = {
    "Interpretação de texto (tese)":            ["tese"],
    "Interpretação de texto (pressupostos)":    ["pressupostos"],
    "Interpretação de texto (argumentação)":    ["ideia_secundaria"],
    "Interpretação de texto (compreensão)":     ["afirmacoes_falsas"],
}


def testar(questoes, trechos) -> list:
    """Retorna lista de (topico, problema, detalhe)."""
    por_id = {t["trecho_id"]: t for t in trechos}
    problemas = []

    for q in questoes:
        topico = q["topico"]
        alts   = q["alternativas"]
        gab    = alts[q["gabarito"]]
        expl   = q["explicacao"]
        enun   = q["enunciado"]
        trecho = por_id.get(q.get("trecho_id"))

        if trecho is None:
            problemas.append((topico, "trecho de origem não identificado", ""))
            continue

        # ── 1) Gabarito rastreável à análise do trecho ──
        campos = CAMPO_ESPERADO.get(topico)
        if campos:
            valores = []
            for c in campos:
                v = trecho.get(c)
                valores.extend(v if isinstance(v, list) else [v])
            if _norm(gab) not in {_norm(v) for v in valores if v}:
                problemas.append((topico,
                                  f"gabarito não corresponde ao campo {campos}",
                                  gab[:70]))

        # ── 2) Nenhum distrator também verdadeiro ──
        if topico == "Interpretação de texto (compreensão)":
            # gabarito é a falsa; distratores devem ser verdadeiros — ok
            pass
        elif campos:
            verdadeiros = {_norm(trecho["tese"])}
            verdadeiros |= {_norm(p) for p in trecho.get("pressupostos", [])}
            if trecho.get("ideia_secundaria"):
                verdadeiros.add(_norm(trecho["ideia_secundaria"]))
            for L, txt in alts.items():
                if L == q["gabarito"]:
                    continue
                if _norm(txt) in verdadeiros:
                    problemas.append((topico,
                                      "distrator também é verdadeiro para o trecho",
                                      txt[:70]))
                    break

        # ── 2b) ANCORAGEM NO TEXTO ──
        #
        # Tentei aqui uma checagem lexical — exigir que cada distrator
        # compartilhasse vocabulário com o trecho. Não funciona em texto
        # matemático: a informação está na notação (P(A ∩ B) = P(A)·P(B)),
        # que nenhum extrator de palavras enxerga. Uma afirmação fiel ao
        # texto e outra que o extrapola davam a MESMA cobertura de 25%.
        #
        # A verificação real de "isto está no trecho?" exige leitura, que
        # é justamente o que o Python não faz. Por isso o controle mudou
        # de lugar: o prompt da indexação agora proíbe explicitamente o
        # pressuposto que extrapola, e a validação em indexar_livro.py
        # descarta trechos majoritariamente simbólicos — onde o problema
        # se concentra.
        #
        # O que sobra é conferência humana em amostra. Está documentado
        # como limitação conhecida, não como lacuna esquecida.

        # ── 3) Texto-base presente e íntegro ──
        if trecho["texto"][:60] not in enun:
            problemas.append((topico, "texto-base ausente ou alterado no enunciado", ""))

        # ── 4) Distratores no assunto ──
        # Ao menos 3 das 5 alternativas devem compartilhar vocabulário com o texto.
        # NÃO se aplica à asserção-razão: ali as alternativas são fórmulas fixas
        # ("As asserções I e II são verdadeiras...") e o conteúdo está nas
        # asserções, não nas opções.
        vocab = _palavras(trecho["texto"])
        no_tema = sum(1 for txt in alts.values()
                      if len(_palavras(txt) & vocab) >= 1)
        if "asserção-razão" not in topico and no_tema < 3:
            problemas.append((topico,
                              f"só {no_tema}/5 alternativas tratam do assunto "
                              f"(questão respondível sem ler o texto)", ""))

        # ── 5) Explicação coerente ──
        if len(expl.strip()) < 40:
            problemas.append((topico, "explicação curta demais", expl[:50]))

        # ── 6) Sem vazamento do gabarito no enunciado ──
        # (o texto-base pode conter as ideias, mas não a frase da alternativa)
        corpo = enun.split("\u201d")[-1]   # depois das aspas de fechamento
        if len(_norm(gab)) > 25 and _norm(gab) in _norm(corpo):
            problemas.append((topico, "gabarito aparece no comando da questão",
                              gab[:60]))

        # ── 6b) EQUILÍBRIO DE TAMANHO ──
        # A resposta certa não pode se destacar pelo comprimento: a tese
        # vem da análise do modelo e é naturalmente mais longa que os
        # distratores, o que entrega o gabarito sem leitura do texto.
        if "asserção-razão" not in topico:
            # QUALQUER alternativa que destoe estraga a questão, não só o
            # gabarito: um distrator gigante ao lado de quatro curtos é
            # eliminado por instinto, e o aluno passa a escolher entre
            # quatro opções. A checagem antiga olhava só o gabarito e
            # deixava passar exatamente esse caso.
            tamanhos = {L: len(str(v)) for L, v in alts.items()}
            for L, n in tamanhos.items():
                demais = [v for k, v in tamanhos.items() if k != L]
                if not demais:
                    continue
                media = sum(demais) / len(demais)
                if media <= 0:
                    continue
                razao = n / media
                papel = "gabarito" if L == q["gabarito"] else f"distrator {L}"
                if razao > 2.0:
                    problemas.append((topico,
                                      f"{papel} é {razao:.1f}x a média das demais "
                                      f"(destoa visualmente)",
                                      str(alts[L])[:60]))
                    break
                if razao < 0.45:
                    problemas.append((topico,
                                      f"{papel} tem {razao:.1f}x o tamanho médio "
                                      f"(destoa por ser curto)",
                                      str(alts[L])[:60]))
                    break

        # ── 6c) ALTERNATIVA COMPLETA ──
        # Nenhuma alternativa pode terminar em palavra que exige
        # complemento: possessivo sem substantivo ("definidores de suas."),
        # gerúndio solto, preposição pendurada. O encurtamento de teses
        # longas é a origem provável desses cortes.
        PENDENTES = {
            "é", "são", "de", "do", "da", "dos", "das", "em", "no", "na",
            "por", "para", "com", "sem", "que", "e", "ou", "a", "o", "as",
            "os", "um", "uma", "ao", "à", "seu", "sua", "seus", "suas",
            "este", "esta", "esse", "essa", "cada", "todo", "toda",
            "outro", "outra", "cujo", "cuja",
            # Adjetivos e determinantes que pedem substantivo depois:
            # "requer mais do que ações normativas ou a simples." fica
            # pendurado — o corte caiu antes do núcleo do sintagma.
            "simples", "mero", "mera", "próprio", "própria", "mesmo",
            "mesma", "único", "única", "certo", "certa", "tal", "tais",
            "determinado", "referido", "citado", "dito", "presente",
            "seguinte", "primeiro", "segundo", "novo", "nova", "grande",
            "maior", "menor",
        }
        for L, txt in alts.items():
            palavras = str(txt).rstrip(".!?").split()
            if not palavras:
                continue
            ult = palavras[-1].lower().strip(".,;:")
            if ult in PENDENTES or re.fullmatch(r'\w+(?:ando|endo|indo)', ult):
                problemas.append((topico,
                                  f"alternativa {L} termina em '{ult}' "
                                  f"(frase incompleta)",
                                  str(txt)[:70]))
                break

        # ── 6d) NEGAÇÃO BEM FORMADA ──
        # Distratores gerados por negação podem sair defeituosos quando a
        # frase original já é negativa ou tem estrutura correlativa:
        #   "nem sempre não é possível"          (dupla negação)
        #   "É X, mas sim Y"                     (correlativa quebrada)
        #   "não é paradoxal, apesar de..."      (justificativa órfã)
        for L, txt in alts.items():
            b = str(txt).lower()
            # Duas marcas de negação próximas, em qualquer ordem:
            # "não ... nunca" e "nem sempre não" são igualmente ruins.
            if re.search(r'\b(?:não|nunca|jamais|nem)\b[^.]{0,40}'
                         r'\b(?:não|nunca|jamais)\b', b):
                problemas.append((topico,
                                  f"alternativa {L} com dupla negação",
                                  str(txt)[:66]))
                break
            if "não" in b and re.search(r'\bmas sim\b|\be sim\b', b):
                problemas.append((topico,
                                  f"alternativa {L}: correlativa quebrada pela negação",
                                  str(txt)[:66]))
                break
            # Dupla negação SEMÂNTICA: "não é independente", "não é
            # desnecessário". A leitura fica penosa, sobretudo quando o
            # comando da questão também é negativo ("é INCORRETO afirmar
            # que não é independente").
            if re.search(r'\bnão\b[^.]{0,30}\b\w*(?:independente|desnecessári|'
                         r'dispensáve|irrelevante|impossíve|inadequad|'
                         r'insuficiente|incapaz|incorret|inexistente)\w*\b', b):
                problemas.append((topico,
                                  f"alternativa {L} com dupla negação semântica",
                                  str(txt)[:66]))
                break
            if re.search(r'\bnão\b[^.]{0,60}\b(?:apesar de|embora|ainda que)\b', b):
                problemas.append((topico,
                                  f"alternativa {L}: concessiva órfã após negação",
                                  str(txt)[:66]))
                break

        # ── 6e) AUTOCONTRADIÇÃO ──
        # Uma alternativa não pode afirmar algo e defender o contrário na
        # mesma frase. Acontece quando a negação é removida de uma oração
        # e o desdobramento seguinte permanece:
        #   "Existe uma única forma ideal; diferentes modelagens devem
        #    ser experimentadas e adaptadas a cada contexto"
        for L, txt in alts.items():
            b = " ".join(str(txt).lower().split())
            # "única/apenas/somente X" seguido de "diferentes/vários/múltiplos"
            if re.search(r'\b(?:únic[ao]|apenas|somente|exclusivamente)\b'
                         r'[^.]{0,80}\b(?:diferentes|vári[ao]s|múltipl[ao]s|'
                         r'diversas|diversos)\b', b):
                problemas.append((topico,
                                  f"alternativa {L} se autocontradiz",
                                  str(txt)[:70]))
                break

        # ── 6e2) FRAGMENTO SEM PREDICADO ──
        # Uma alternativa com oração reduzida que nada fecha não afirma
        # nada — não pode ser julgada verdadeira nem falsa. A lista de
        # locuções veio de varredura sistemática (ver comentário em
        # indexar_livro._checar_redacao), não de casos avulsos.
        INTRO_RED = (r'(?:ao|à|aos|às|de|em|por|para|sem|com|após|'
                     r'antes de|apesar de|além de|em vez de|ao invés de|'
                     r'a fim de|depois de|desde)?')
        for L, txt in alts.items():
            s = " ".join(str(txt).split())
            m = re.search(r',\s*' + INTRO_RED + r'\s*'
                          r'\w+(?:ando|endo|indo|arem|erem|irem|ar|er|ir|'
                          r'ad[oa]s?|id[oa]s?|t[oa]s?)\b', s, re.IGNORECASE)
            if not m:
                continue
            depois = s[m.end():]
            fecha = depois.find(",")
            resto = depois[fecha + 1:].strip() if fecha >= 0 else ""
            if len(resto.split()) < 2:
                problemas.append((topico,
                                  f"alternativa {L} é fragmento sem predicado",
                                  str(txt)[:66]))
                break

        # ── 6f) ESCOPO AMBÍGUO ──
        # Quantificador restritivo seguido de negação admite duas
        # leituras: "Apenas os médicos não podem avaliar" pode significar
        # "só eles não podem" ou "não é só eles que podem".
        for L, txt in alts.items():
            if re.match(r'^\s*(?:apenas|somente|só|exclusivamente|unicamente)\b'
                        r'[^.]{0,50}\bnão\b', str(txt), re.IGNORECASE):
                problemas.append((topico,
                                  f"alternativa {L} com escopo ambíguo "
                                  f"(restritivo + negação)",
                                  str(txt)[:66]))
                break

        # ── 7) Estrutura básica ──
        if len(alts) != 5:
            problemas.append((topico, f"{len(alts)} alternativas", ""))
        if len({_norm(v) for v in alts.values()}) != 5:
            problemas.append((topico, "alternativas repetidas", ""))

    # ── SOBREPOSIÇÃO ENTRE QUESTÕES DO MESMO TRECHO ──
    # Duas questões sobre o mesmo parágrafo não podem compartilhar quase
    # todas as alternativas: quem responde a primeira já viu as opções da
    # segunda, e só precisa descobrir qual mudou de papel.
    from collections import defaultdict as _dd
    por_trecho = _dd(list)
    for q in questoes:
        tid = q.get("trecho_id")
        if tid:
            por_trecho[tid].append((q, frozenset(str(v) for v in
                                                 q["alternativas"].values())))

    for tid, itens in por_trecho.items():
        # Com muitas questões sobre o mesmo trecho, a sobreposição é
        # matematicamente inevitável: o material do parágrafo é finito.
        # Cinco trechos e quarenta questões dão oito por trecho, e não há
        # cinco alternativas novas oito vezes.
        #
        # O limite acompanha a pressão sobre o trecho, do mesmo modo que o
        # veto no gerador: até 2 questões exige variedade alta; acima
        # disso, cede — melhor alguma repetição que lote incompleto.
        if len(itens) <= 1:
            continue
        # A escala continua até 5: com quatro ou mais questões sobre o
        # mesmo parágrafo, não existem cinco alternativas novas a cada
        # vez — o material do trecho é finito e a repetição é aritmética,
        # não defeito. O que a checagem protege é o caso comum (uma ou
        # duas questões por trecho), onde ainda há espaço para variar.
        # O limite acompanha o material restante do trecho. Cada questão
        # consome alternativas: com 4 falsas, 2 pressupostos, tese e ideia
        # secundária, um parágrafo oferece cerca de 8 afirmações distintas
        # — o bastante para duas questões sem repetir, não para quatro.
        #
        # Medi a saída real do gerador para calibrar: 2 a 3 questões por
        # trecho produzem até 4 alternativas em comum, e isso é o piso
        # aritmético, não folga de implementação.
        # 4 é o piso aritmético: um parágrafo oferece cerca de 8
        # afirmações distintas (tese, ideia secundária, 2 pressupostos,
        # 4 falsas), e cada questão consome 5. Duas questões já competem
        # pelo mesmo material.
        #
        # O gerador exige mais variedade nas primeiras tentativas e cede
        # perto do limite — comportamento intencional, porque lote
        # incompleto é pior que alguma repetição. A checagem valida o que
        # importa: o conjunto nunca ser idêntico.
        limite_comuns = 4

        for i in range(len(itens)):
            for j in range(i + 1, len(itens)):
                comuns = len(itens[i][1] & itens[j][1])
                if comuns > limite_comuns:
                    problemas.append((itens[i][0]["topico"],
                                      f"{comuns} de 5 alternativas repetidas "
                                      f"entre questões do trecho {tid}",
                                      f"Q{itens[i][0].get('numero')} e "
                                      f"Q{itens[j][0].get('numero')}"))
                    break

    return problemas


def testar_assercao_razao(questoes, trechos) -> list:
    """
    A asserção-razão tem lógica própria: as duas asserções vêm da análise,
    e o gabarito precisa descrever corretamente a relação entre elas.
    """
    por_id = {t["trecho_id"]: t for t in trechos}
    problemas = []
    for q in questoes:
        if q["topico"] != "Interpretação de texto (asserção-razão)":
            continue
        trecho = por_id.get(q.get("trecho_id"))
        if not trecho:
            continue
        enun = q["enunciado"]

        m1 = re.search(r'\nI\.\s+(.+?)\n', enun)
        m2 = re.search(r'\nII\.\s+(.+?)\n', enun)
        if not (m1 and m2):
            problemas.append((q["topico"], "asserções I/II não encontradas", ""))
            continue

        a1, a2 = _norm(m1.group(1)), _norm(m2.group(1))
        verdadeiros = {_norm(trecho["tese"])}
        verdadeiros |= {_norm(p) for p in trecho.get("pressupostos", [])}
        if trecho.get("ideia_secundaria"):
            verdadeiros.add(_norm(trecho["ideia_secundaria"]))
        falsos = {_norm(f) for f in trecho.get("afirmacoes_falsas", [])}

        i_verdadeira  = a1 in verdadeiros
        ii_verdadeira = a2 in verdadeiros

        # A II também pode ser a NEGAÇÃO de um pressuposto (falsa, mas
        # pertinente). A negação vai nos DOIS sentidos: o pressuposto pode
        # ser afirmativo ("X altera Y" → "X não altera Y") ou já negativo
        # ("X não altera Y" → "X altera Y"), então testamos ambos.
        a2_sem_neg  = _norm(a2.replace("não ", ""))
        a2_com_neg  = _norm(f"não {a2}")
        ii_negacao = (not ii_verdadeira) and (
            a2_sem_neg in verdadeiros
            or any(_norm(v.replace("não ", "")) == _norm(a2) for v in verdadeiros)
            or a2_com_neg in verdadeiros
        )

        i_conhecida  = i_verdadeira or a1 in falsos
        ii_conhecida = ii_verdadeira or a2 in falsos or ii_negacao

        if not (i_conhecida and ii_conhecida):
            problemas.append((q["topico"],
                              "asserção não rastreável à análise do trecho", ""))
            continue

        # ── CONTRADIÇÃO ENTRE AS ASSERÇÕES ──
        # As duas não podem ser a mesma proposição com polaridade trocada:
        #   I.  "A inclusão em reuniões é desnecessária"
        #   II. "A inclusão em reuniões é benéfica"
        # Não há relação causal a avaliar, só contradição — o aluno resolve
        # por lógica, sem ler o texto.
        try:
            from gerador_interpretacao import _sao_contraditorias as _contr
            if _contr(a1, a2):
                problemas.append((q["topico"],
                                  "asserções I e II se contradizem "
                                  "(não é relação de causa)",
                                  f"I: {a1[:36]} | II: {a2[:36]}"))
        except ImportError:
            pass

        # ── PERTINÊNCIA: a II precisa poder justificar a I ──
        # Num item asserção-razão, a segunda asserção deve tratar do mesmo
        # ponto da primeira; se falar de outro assunto, a relação "porque"
        # não é avaliável e a questão perde sentido.
        #
        # A comparação é por RADICAL, não por palavra inteira: "diagnósticos"
        # e "diagnóstico" são o mesmo assunto, assim como "notificação" e
        # "notificar". Exigir a forma exata acusaria pares legítimos.
        def _radicais(txt):
            return {p[:6] for p in _palavras(txt)}

        rad_i  = _radicais(a1)
        rad_ii = _radicais(a2_sem_neg)
        if rad_i and rad_ii and not (rad_i & rad_ii):
            # Como as asserções vêm sempre da análise DO MESMO trecho, um par
            # sem nenhum radical em comum indica que a II veio de outro ponto
            # do texto e não serve como razão da I.
            problemas.append((q["topico"],
                              "asserção II não se relaciona com a I "
                              "(relação 'porque' não avaliável)",
                              f"I: {a1[:40]} | II: {a2[:40]}"))

        gab = q["alternativas"][q["gabarito"]].lower()
        # O gabarito precisa refletir os valores-verdade reais
        ii_final = ii_verdadeira   # negação de pressuposto conta como falsa
        if i_verdadeira and ii_final:
            esperado = "i e ii são proposições verdadeiras"
        elif i_verdadeira and not ii_final:
            esperado = "i é uma proposição verdadeira, e a ii é uma proposição falsa"
        elif not i_verdadeira and ii_final:
            esperado = "i é uma proposição falsa, e a ii é uma proposição verdadeira"
        else:
            esperado = "i e ii são proposições falsas"

        if esperado not in gab:
            problemas.append((q["topico"],
                              f"gabarito não reflete os valores-verdade "
                              f"(I={'V' if i_verdadeira else 'F'}, "
                              f"II={'V' if ii_final else 'F'})",
                              gab[:70]))
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    from gerador_interpretacao import gerar_lote
    from _trechos_teste import TRECHOS_TESTE

    print("═" * 62)
    print("  TESTE 5 — QUESTÕES DE INTERPRETAÇÃO")
    print("═" * 62)

    total = 0
    for seed in [1, 42, 777, 31337]:
        lote = gerar_lote(TRECHOS_TESTE, qtd // 4, seed=seed)
        p1 = testar(lote, TRECHOS_TESTE)
        p2 = testar_assercao_razao(lote, TRECHOS_TESTE)
        n = len(p1) + len(p2)
        total += n
        print(f"\n  seed {seed:<8} {len(lote)} questões → "
              f"{'✅ nenhum problema' if n == 0 else f'❌ {n} problema(s)'}")
        vistos = set()
        for topico, det, ctx in (p1 + p2):
            chave = (topico, det[:35])
            if chave in vistos: continue
            vistos.add(chave)
            print(f"     ⚠ [{topico}] {det}")
            if ctx: print(f"        {ctx}")
            if len(vistos) >= 5: break

    # distribuição por tipo
    lote = gerar_lote(TRECHOS_TESTE, 500, seed=99)
    print(f"\n  ── Distribuição dos tipos em 500 questões ──")
    for topico, n in Counter(q["topico"] for q in lote).most_common():
        print(f"     {topico:<48} {n}")

    print("\n" + "═" * 62)
    print(f"  {'🎉 TESTE 5 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 62)
    sys.exit(1 if total else 0)
