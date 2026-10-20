"""
=============================================================
  TESTE 12 — O SIMULADO ENTREGUE AO ALUNO
=============================================================
  Os outros testes examinam o que cada GERADOR produz. Este
  examina o que sai do montador, que é o que o aplicativo
  realmente entrega:

    1. O gabarito aponta uma letra que existe na questão.
    2. A explicação do gabarito corresponde à alternativa
       apontada — o montador renumera as questões, e é aí que
       gabarito e questão podem se desencontrar.
    3. Nenhum enunciado se repete dentro do simulado.
    4. Nenhum FATO se repete — duas redações da mesma coisa
       cansam tanto quanto a repetição literal.
    5. Nenhuma área domina o caderno além do teto.
    6. As letras do gabarito se distribuem.
    7. A composição bate com o que foi pedido.

  USO:
      python3 teste_12_simulado_gerado.py
      python3 teste_12_simulado_gerado.py medicina ads
=============================================================
"""

import re
import sys
import unicodedata
from collections import Counter

import montar_simulado_procedural as MS

LETRAS = ["A", "B", "C", "D", "E"]

# (rótulo, disciplinas, quantidade)
CADERNOS = [
    ("Medicina",         ["medicina"],    30),
    ("ADS",              ["ads"],         30),
    ("Administração",    ["administracao"], 30),
    ("Direito",          ["direito"],     30),
    ("Matemática",       ["matematica"],  30),
    ("Matemática básica", ["basica"],     30),
    ("Português",        ["portugues"],   30),
    ("Redes",            ["redes"],       30),
    ("Saúde",            ["saude"],       30),
    ("Engenharia",       ["engenharia"],  20),
    # Anatomia em 30, não em 20: é a disciplina com menos rótulos de
    # tópico (quatro), e é justamente no caderno maior que a reposição
    # pela reserva pode concentrar. Testar no tamanho fácil escondia isso.
    ("Anatomia",         ["anatomia"],    30),
    ("Misto",            ["ads", "redes", "matematica"], 40),
]

SEEDS = [1, 42, 777, 20260926, 31337]

# Teto de concentração por área dentro de um caderno.
TETO_AREA = 0.45


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def _area(topico):
    """'Redes (máscaras)' → 'redes'. O que vem antes do parêntese."""
    return _norm(str(topico).split("(")[0])


# Palavras que não carregam conteúdo e não devem contar na comparação.
VAZIAS = {
    "para", "pelo", "pela", "pelos", "pelas", "como", "esse", "essa",
    "este", "esta", "isso", "aquele", "aquela", "quando", "onde", "que",
    "com", "sem", "dos", "das", "uma", "sua", "seu", "seus", "suas",
    "mais", "menos", "entre", "sobre", "cada", "qual", "quais", "deve",
    "pode", "ocorre", "assinale", "alternativa", "correta", "considere",
}


def _radicais(texto):
    """Palavras de conteúdo, cortadas em cinco letras.

    O corte aproxima flexões: "desloca", "deslocamento" e "deslocada"
    viram todas "desloc". Sem isso, a comparação escapava por uma letra.
    """
    palavras = re.findall(r"[a-zà-ú]{4,}", _norm(texto))
    return {p[:5] for p in palavras if p not in VAZIAS}


def _vazamento_cruzado(questoes, gabarito):
    """
    Uma questão cujo ENUNCIADO contém a resposta de outra.

    Foi assim num caderno de medicina: a questão 29 abria com
    "deslocamento da curva para a esquerda, com afinidade maior da
    hemoglobina pelo oxigênio" para então pedir a causa — e a 28
    perguntava justamente o que acontece com a curva e com a afinidade.
    Quem lesse a 29 primeiro eliminava duas das cinco opções da 28.

    A comparação é por radicais, não por texto: os dois trechos diziam a
    mesma coisa com as palavras em ordem diferente ("com maior afinidade"
    contra "com afinidade maior"), e casar cadeias exatas não pegava.
    """
    problemas = []
    for q in questoes:
        g = gabarito.get(q["numero"])
        if not g:
            continue
        resposta = _radicais(q["alternativas"].get(g["resposta_correta"], ""))
        # Respostas curtas são termos soltos ("segmento", "mesoderma") e
        # aparecem em outros enunciados sem entregar nada.
        if len(resposta) < 6:
            continue
        for outra in questoes:
            if outra["numero"] == q["numero"]:
                continue
            enun = _radicais(outra["enunciado"])
            if len(resposta & enun) / len(resposta) >= 0.85:
                problemas.append(
                    f"Q{outra['numero']} enuncia a resposta da "
                    f"Q{q['numero']}")
                break
    return problemas


def examinar(rotulo, disciplinas, quantidade, seed):
    problemas = []
    r = MS.montar(quantidade=quantidade, disciplinas=disciplinas, seed=seed)
    questoes = r["questoes"]
    gabarito = {g["numero"]: g for g in r["gabarito"]}

    if len(questoes) != quantidade:
        problemas.append(f"pediu {quantidade}, veio {len(questoes)}")

    enunciados, letras, areas = set(), Counter(), Counter()
    repetidos = Counter()

    for q in questoes:
        num = q["numero"]
        g = gabarito.get(num)
        if g is None:
            problemas.append(f"Q{num}: sem gabarito")
            continue

        letra = g["resposta_correta"]
        letras[letra] += 1

        if letra not in q["alternativas"]:
            problemas.append(f"Q{num}: gabarito {letra} não existe entre "
                             f"as alternativas")
            continue

        # A explicação nomeia a resposta. Se o montador tivesse
        # embaralhado as questões sem levar o gabarito junto, a
        # explicação de uma cairia sobre outra — e o jeito de flagrar é
        # confrontar a explicação com o texto da alternativa apontada.
        correta = _norm(q["alternativas"][letra])
        expl = _norm(g.get("explicacao", ""))
        if len(correta) >= 6 and correta not in expl:
            outras = [L for L in q["alternativas"]
                      if L != letra
                      and len(_norm(q["alternativas"][L])) >= 6
                      and _norm(q["alternativas"][L]) in expl]
            if outras:
                problemas.append(
                    f"Q{num}: a explicação descreve a alternativa "
                    f"{outras[0]}, mas o gabarito diz {letra}")

        chave = _norm(q["enunciado"])
        if chave in enunciados:
            problemas.append(f"Q{num}: enunciado repetido no caderno")
        enunciados.add(chave)

        repetidos[(g.get("topico", ""), _norm(q["alternativas"][letra]))] += 1

    problemas += _vazamento_cruzado(questoes, gabarito)

    # MESMO FATO, redação diferente. "Qual é o prazo legal, em dias
    # úteis?" e "O prazo previsto na CLT é de:" são textos distintos
    # para a mesma coisa — recurso de revista, 8 dias —, e essa
    # combinação apareceu três vezes num caderno de direito.
    #
    # O limiar é três, não dois: há templates de resposta binária, como
    # o de ocorrência de crase, em que duas frases diferentes têm
    # legitimamente a mesma resposta ("o acento grave não se aplica").
    for (topico, resposta), n in repetidos.items():
        if n >= 3:
            problemas.append(f"'{resposta[:42]}' responde {n} questões de "
                             f"{topico} — mesmo fato, redações diferentes")

    # Distribuição das letras. Num caderno de 30, uma letra com mais de
    # 45% é padrão visível — o aluno atento marca tudo nela.
    if questoes:
        mais = letras.most_common(1)[0]
        if mais[1] / len(questoes) > 0.45:
            problemas.append(f"letra {mais[0]} em {mais[1]} de "
                             f"{len(questoes)} questões")
        if len(letras) < 4:
            problemas.append(f"só {len(letras)} letras distintas no gabarito")

    # Concentração por assunto. Foi o que produziu o caderno de direito
    # com doze perguntas de prazo trabalhista.
    #
    # O tópico vem do GABARITO, não da questão: a questão entregue ao
    # aluno não carrega metadado nenhum. Ler q["topico"] dava "?" para
    # todas, o caderno parecia ter uma única área e a verificação
    # passava sem verificar nada.
    sem_topico = 0
    for g in gabarito.values():
        t = g.get("topico") or ""
        if not t:
            sem_topico += 1
        areas[_area(t) or "?"] += 1
    if sem_topico:
        problemas.append(f"{sem_topico} questões sem tópico no gabarito — "
                         f"o teto de repetição por assunto não consegue agir")

    # A verificação por ÁREA foi retirada. Ela media o texto antes do
    # parêntese, e num simulado de engenharia "Engenharia de software"
    # é 90% do caderno por definição — o alarme disparava em todo
    # caderno de disciplina única, dizendo apenas que o caderno era do
    # que foi pedido. Um teste que sempre reclama deixa de ser lido.
    #
    # O tópico exato é mais fino: "Direito do trabalho (prazos)"
    # e "Processo penal (prazos)" são áreas diferentes, mas repetir um
    # deles dez vezes cansa igual.
    #
    # O limite acompanha quantos tópicos a disciplina tem. Anatomia tem
    # quatro: exigir 30% seria exigir uma distribuição mais uniforme do
    # que a divisão exata (25%) permite variar.
    topicos = Counter(g.get("topico") or "?" for g in gabarito.values())
    if questoes and len(topicos) > 1:
        # A folga acompanha o número de tópicos. Anatomia tem quatro, e
        # o de Terminologia Anatômica cobre muito mais fatos distintos
        # que os outros três somados: quando a reposição escolhe entre
        # um fato inédito de Terminologia e um repetido de
        # Neuroanatomia, o inédito é a escolha certa — e aí a fatia de
        # Terminologia passa dos 40% sem que nada esteja errado.
        #
        # Com 15 tópicos, como em direito, o limite volta a 30% e o caso
        # que originou esta verificação (doze perguntas de prazo
        # trabalhista em trinta questões) continua sendo pego.
        limite = max(0.30, 2.0 / len(topicos))
        top, n = topicos.most_common(1)[0]
        if n / len(questoes) > limite:
            problemas.append(f"tópico '{top}' ocupa {n} de {len(questoes)} "
                             f"questões ({n / len(questoes):.0%}, "
                             f"limite {limite:.0%} para {len(topicos)} tópicos)")

    return problemas, r


def conferir_maximos():
    """
    O `maximo_sugerido` promete um caderno sem assunto repetido. Aqui
    a promessa é cobrada: monta-se um caderno EXATAMENTE do tamanho
    anunciado e exige-se `fatos_repetidos` igual a zero.

    Sem isto, o número seria só uma estimativa publicada na API — e uma
    estimativa errada é pior do que nenhuma, porque o aplicativo passa
    a confiar nela para dimensionar a tela.
    """
    from montar_simulado_procedural import (
        LASTRO_DISCIPLINA, expandir_grupos, maximo_sugerido, montar)

    carregados = {k: True for k in LASTRO_DISCIPLINA}
    problemas = []
    print("\n  ┌─ Máximo sugerido por disciplina ──────────────────────")
    for disc in sorted(LASTRO_DISCIPLINA):
        if disc == "conceitual":
            continue
        expandidas = expandir_grupos([disc], carregados)
        maximo = min(maximo_sugerido(expandidas), 60)
        repetidos = []
        for seed in (1, 42, 777):
            try:
                r = montar(quantidade=maximo, disciplinas=[disc], seed=seed)
            except Exception as e:                       # noqa: BLE001
                problemas.append(f"{disc}: exceção {type(e).__name__}: {e}")
                break
            repetidos.append(r["fatos_repetidos"])
            if len(r["questoes"]) != maximo:
                problemas.append(f"{disc}: pediu {maximo}, veio "
                                 f"{len(r['questoes'])}")
        if any(repetidos):
            problemas.append(f"{disc}: máximo anunciado é {maximo}, mas "
                             f"o caderno repetiu assunto {max(repetidos)} "
                             f"vezes")
        marca = "❌" if any(repetidos) else "· "
        print(f"  │ {marca} {disc:<16} {maximo:>3} questões, "
              f"{max(repetidos or [0])} fato(s) repetido(s)")
    print("  └────────────────────────────────────────────────")
    return problemas


def main():
    alvos = [a.lower() for a in sys.argv[1:]]
    escolhidos = [c for c in CADERNOS
                  if not alvos or any(a in c[0].lower()
                                      or any(a in d for d in c[1])
                                      for a in alvos)]

    print("═" * 64)
    print("  TESTE 12 — O SIMULADO ENTREGUE AO ALUNO")
    print("═" * 64)

    total = 0
    for rotulo, disciplinas, quantidade in escolhidos:
        falhas, exemplo = [], None
        for seed in SEEDS:
            try:
                probs, r = examinar(rotulo, disciplinas, quantidade, seed)
            except Exception as e:                      # noqa: BLE001
                probs, r = [f"exceção {type(e).__name__}: {e}"], None
            if exemplo is None:
                exemplo = r
            falhas += [(seed, p) for p in probs]

        total += len(falhas)
        marca = "❌" if falhas else "✅"
        comp = (exemplo or {}).get("composicao", {})
        print(f"\n  {marca} {rotulo:<18} {quantidade:>3} questões × "
              f"{len(SEEDS)} sementes")
        if comp:
            resumo = ", ".join(f"{k.split(':')[-1]} {v}"
                               for k, v in sorted(comp.items()))
            print(f"      composição: {resumo}")
        for seed, p in falhas[:8]:
            print(f"      ├─ seed {seed}: {p}")
        if len(falhas) > 8:
            print(f"      └─ (+{len(falhas) - 8} outras)")

    if not alvos:
        for p in conferir_maximos():
            total += 1
            print(f"      ❌ {p}")

    print("\n" + "═" * 64)
    print(f"  {'🎉 TESTE 12 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 64)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
