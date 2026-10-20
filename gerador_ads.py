"""
=============================================================
  NIVELIS — Gerador Procedural ADS / Computação
  Foco: ENADE — Componente Específico
=============================================================

  Gera questões de TI SEM IA. O Python SIMULA o algoritmo,
  executa a query, percorre a árvore — e o gabarito é o
  resultado real, não uma estimativa de modelo.

  16 TEMPLATES:

  ALGORITMOS E COMPLEXIDADE
    1. Complexidade de loops aninhados        (Big-O)
    2. Complexidade de algoritmos clássicos   (Big-O)
    3. Contagem exata de operações
    4. Comparações em ordenação
  ESTRUTURAS DE DADOS
    5. Pilha (LIFO) — simulação real
    6. Fila (FIFO) — simulação real
    7. Árvore binária de busca — percursos reais
    8. Grafos — arestas, grau, densidade
  MATEMÁTICA COMPUTACIONAL
    9. Conversão de bases
   10. Aritmética binária / complemento de dois
   11. Lógica proposicional — tabela-verdade real
   12. Conjuntos — inclusão-exclusão
  BANCO DE DADOS
   13. SQL — resultado de query (executado de verdade)
   14. Cardinalidade de JOIN
  SISTEMAS E REDES
   15. Sub-rede CIDR (calculada com ipaddress)
   16. Escalonamento de processos (FIFO/SJF)

  USO:
    python gerador_ads.py            # 16 questões
    python gerador_ads.py 30 redes
=============================================================
"""

import sys
import re
import random
import ipaddress
from math       import comb, log2, ceil
from itertools  import product

import equilibrio_numerico as _EQ


LETRAS = ["A", "B", "C", "D", "E"]


# ──────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────

def _plural(n: int, singular: str, plural: str = None) -> str:
    """
    Concorda substantivo com numeral: 1 -> singular, demais -> plural.
    Evita "1 elementos" / "1 meninos". Se `plural` não for informado,
    acrescenta 's' ao singular.
    """
    if plural is None:
        plural = singular + "s"
    return singular if abs(n) == 1 else plural


def _verbo(n: int, singular: str, plural: str) -> str:
    """Concorda verbo com numeral: 1 -> singular ('ser'), demais -> plural."""
    return singular if abs(n) == 1 else plural


def _juntar(parte_anterior: str, parte_seguinte: str) -> str:
    """
    Ajusta a inicial da parte seguinte conforme a pontuação da anterior.
    Evita "…tamanho n. assinale a alternativa" (minúscula após ponto) e
    "…de tamanho n, Qual é" (maiúscula após vírgula).
    Essencial para montagem de enunciado por partes.
    """
    if not parte_seguinte:
        return parte_seguinte
    fecha_frase = parte_anterior.rstrip().endswith((".", "!", "?", ":"))
    primeira    = parte_seguinte[0]
    resto       = parte_seguinte[1:]
    if fecha_frase:
        return primeira.upper() + resto
    return primeira.lower() + resto


def _fmt(v) -> str:
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return str(v)


# ══════════════════════════════════════════════════════════════════
#  METADADOS DE RESPOSTA
#  Cada questão declara QUE TIPO de resposta ela tem. Os testes
#  consultam esse campo em vez de tentar adivinhar pelo texto — o que
#  eliminava questões corretas por engano (falso positivo).
#
#  São campos INTERNOS: a API não os envia ao aplicativo (ver
#  gerar_para_api, que monta a resposta só com enunciado/alternativas).
#
#    numerica     → 42, 1.408          (comparação aritmética vale)
#    fracao       → 2/3, 1/6           (comparar como decimal)
#    simbolica    → O(log n), Θ(n²)    (comparar como texto)
#    sequencia    → "37, 21, 22"       (vários números, é uma lista)
#    textual      → Aceita, Rejeita    (prosa curta)
#    endereco_ip  → 255.255.255.0      (pontos não são decimais)
#    percentual   → 95,8%              (numérica com sufixo)
# ══════════════════════════════════════════════════════════════════

TIPOS_RESPOSTA = {
    "numerica",         # 42, 1.408 — vale como quantidade
    "fracao",           # 2/3, 1/6
    "simbolica",        # O(log n), Θ(n²) — notação
    "codigo_numerico",  # 1000110 (binário), 3F (hex) — dígitos que NÃO são
                        # quantidade: comparar como TEXTO, nunca como número
    "sequencia",        # "37, 21, 22" — lista de valores
    "textual",          # Aceita, Rejeita
    "endereco_ip",      # 255.255.255.0
    "percentual",       # 95,8%
    "monetaria",        # R$ 1.234,56 — numérica com símbolo de moeda
}


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=_fmt, tipo_resposta="numerica"):
    """
    Junta gabarito + 4 distratores únicos, embaralha, acha a letra.

    `tipo_resposta` descreve a natureza das alternativas (ver TIPOS_RESPOSTA).
    É metadado interno, usado pelos testes automatizados.
    """
    assert tipo_resposta in TIPOS_RESPOSTA, f"tipo inválido: {tipo_resposta}"

    unicos = []
    escalar = isinstance(correta, (int, float)) and correta != 0
    for d in distratores:
        # Percentuais exigem separação absoluta: 44,9% e 45,1% são
        # indistinguíveis para quem arredondou num passo intermediário.
        if (escalar and isinstance(d, (int, float))
                and tipo_resposta == "percentual"):
            if any(isinstance(u, (int, float)) and abs(d - u) < 1.0
                   for u in unicos + [correta]):
                continue
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
    return {
        "enunciado":      enunciado,
        "alternativas":   {L: formatador(v) for L, v in zip(LETRAS, valores)},
        "gabarito":       LETRAS[valores.index(correta)],
        "explicacao":     explicacao,
        "topico":         topico,
        "origem":         "gerador_ads",
        # ── metadados internos (não vão para o app) ──
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
    }


# ══════════════════════════════════════════
#  ALGORITMOS E COMPLEXIDADE
# ══════════════════════════════════════════

def gerar_complexidade_loops(rng):
    """Loops aninhados -> Big-O. O código é montado e a ordem é deduzida."""
    variantes = [
        (1, "O(n)",       ["for i in range(n):", "    soma += i"]),
        (2, "O(n^2)",     ["for i in range(n):", "    for j in range(n):", "        soma += 1"]),
        (3, "O(n^3)",     ["for i in range(n):", "    for j in range(n):", "        for k in range(n):", "            soma += 1"]),
        (2, "O(n^2)",     ["for i in range(n):", "    for j in range(i, n):", "        soma += 1"]),
        ("log", "O(log n)", ["i = n", "while i > 1:", "    i = i // 2"]),
        ("nlog", "O(n log n)", ["for i in range(n):", "    j = n", "    while j > 1:", "        j = j // 2"]),
    ]
    todas = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(2^n)"]

    for _ in range(50):
        _, correta, linhas = rng.choice(variantes)
        distratores = [o for o in todas if o != correta]
        rng.shuffle(distratores)

        codigo = "\n".join(linhas)
        VARIACOES = [
            f"Analise o trecho de código abaixo, onde n é o tamanho da entrada:"
            f"\n\n{codigo}\n\nQual é a complexidade de tempo assintótica desse trecho?",
            f"Em uma revisão de código, o seguinte trecho foi identificado como "
            f"gargalo (n representa o volume de dados processado):\n\n{codigo}\n\n"
            f"Qual notação assintótica descreve o tempo de execução?",
            f"Considere a rotina a seguir, aplicada a uma entrada de tamanho n:"
            f"\n\n{codigo}\n\nAssinale a alternativa que apresenta corretamente a "
            f"ordem de complexidade dessa rotina.",
            f"Um estagiário implementou o trecho abaixo e precisa documentar seu "
            f"custo computacional em função de n:\n\n{codigo}\n\nQual é a "
            f"complexidade de tempo no pior caso?",
        ]
        enunciado = rng.choice(VARIACOES)
        if correta == "O(n^2)" and "range(i, n)" in codigo:
            just = ("O laço interno executa n, n−1, ..., 1 vezes, somando "
                    "n(n+1)/2 operações — que é da ordem de n².")
        elif correta == "O(log n)":
            just = "A cada iteração o valor é dividido por 2, então o número de repetições é log₂(n)."
        elif correta == "O(n log n)":
            just = "O laço externo executa n vezes e, para cada um, o interno divide por 2 (log n vezes)."
        else:
            niveis = codigo.count("for")
            just = (f"São {niveis} laço(s) independentes, cada um percorrendo n "
                    f"elementos, resultando em n^{niveis} operações.")
        explicacao = f"{just} Portanto, a complexidade é {correta}."

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Complexidade de algoritmos", rng, formatador=str,
                    tipo_resposta="simbolica")
        if q:
            return q
    raise RuntimeError("complexidade_loops")


def gerar_complexidade_classicos(rng):
    """Complexidade de algoritmos consagrados (caso médio/pior explicitado)."""
    tabela = [
        ("busca binária em vetor ordenado",             "pior caso",  "O(log n)",
         "A cada comparação metade do espaço de busca é descartada."),
        ("busca linear em vetor não ordenado",          "pior caso",  "O(n)",
         "No pior caso é preciso percorrer todos os n elementos."),
        ("Merge Sort",                                  "pior caso",  "O(n log n)",
         "O vetor é dividido em log n níveis e cada nível custa O(n) para intercalar."),
        ("Quick Sort",                                  "pior caso",  "O(n^2)",
         "Com pivô sempre mal escolhido, as partições ficam desbalanceadas."),
        ("Quick Sort",                                  "caso médio", "O(n log n)",
         "Com partições equilibradas em média, a recursão tem profundidade log n."),
        ("Bubble Sort",                                 "pior caso",  "O(n^2)",
         "São feitas n−1 passagens, cada uma com até n−1 comparações."),
        ("Heap Sort",                                   "pior caso",  "O(n log n)",
         "Cada uma das n remoções do topo custa O(log n) para reorganizar o heap."),
        ("acesso a uma tabela hash sem colisões",       "caso médio", "O(1)",
         "A função de dispersão leva diretamente à posição do elemento."),
        ("inserção em árvore binária de busca balanceada", "pior caso", "O(log n)",
         "A altura da árvore balanceada é da ordem de log n."),
    ]
    todas = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(2^n)"]

    for _ in range(50):
        alg, caso, correta, just = rng.choice(tabela)
        distratores = [o for o in todas if o != correta]
        rng.shuffle(distratores)

        # MONTAGEM POR PARTES: cenário + pergunta. Ambas as listas usam
        # frases fechadas em si mesmas, sem concordância cruzada — o único
        # ponto de junção é {alg} e {caso}, que são substantivos neutros.
        CENARIOS = [
            "Considerando uma entrada de tamanho n,",
            "Durante a revisão técnica de um sistema, discute-se o custo de {alg}. Para uma entrada de tamanho n,",
            "Em uma disciplina de estruturas de dados, o professor analisa {alg} com n elementos de entrada.",
            "Um time de desenvolvimento precisa documentar o desempenho de {alg} para entradas de tamanho n.",
            "Ao dimensionar a infraestrutura de um serviço, a equipe avaliou {alg} sobre n registros.",
            "Em uma entrevista técnica, pediu-se a análise assintótica de {alg} para n elementos.",
            "Considerando um conjunto de dados com n itens processados por {alg},",
        ]
        PERGUNTAS = [
            "qual é a complexidade de tempo do algoritmo de {alg}, no {caso}?",
            "qual notação assintótica descreve seu tempo de execução no {caso}?",
            "assinale a alternativa que apresenta a complexidade de tempo no {caso}.",
            "qual é a ordem de crescimento do tempo de execução no {caso}?",
            "determine a complexidade temporal no {caso}.",
            "qual das alternativas expressa corretamente o custo de tempo no {caso}?",
        ]
        cen = rng.choice(CENARIOS)
        per = rng.choice(PERGUNTAS)
        # Se o cenário já cita o algoritmo, a pergunta usa forma reduzida
        if "{alg}" in cen:
            per_txt = per.format(alg="ele", caso=caso).replace(
                "do algoritmo de ele", "desse algoritmo")
            cen_txt = cen.format(alg=alg)
        else:
            per_txt = per.format(alg=alg, caso=caso)
            cen_txt = cen
        # JUNÇÃO SEGURA: se o cenário fecha com ponto, a pergunta precisa
        # começar em maiúscula; se fecha com vírgula, em minúscula.
        enunciado = f"{cen_txt} {_juntar(cen_txt, per_txt)}"
        explicacao = f"{just} Logo, a complexidade no {caso} é {correta}."

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Complexidade de algoritmos", rng, formatador=str,
                    tipo_resposta="simbolica")
        if q:
            return q
    raise RuntimeError("complexidade_classicos")


def gerar_contagem_operacoes(rng):
    """Quantas vezes a instrução executa — contado por simulação real."""
    for _ in range(50):
        n = rng.choice([5, 6, 8, 10, 12])
        tipo = rng.choice(["triangular", "duplo", "passo2"])

        if tipo == "triangular":
            correta = sum(1 for i in range(n) for j in range(i, n))
            codigo = (f"for i in range(0, {n}):\n"
                      f"    for j in range(i, {n}):\n"
                      f"        contador += 1")
            just = (f"O laço interno executa {n}, {n-1}, ..., 1 vezes. "
                    f"A soma é {n}×({n}+1)/2 = {correta}.")
            distratores = [n * n, n * (n - 1), correta - n, correta + n, n * (n + 1)]
        elif tipo == "duplo":
            correta = sum(1 for i in range(n) for j in range(n))
            codigo = (f"for i in range(0, {n}):\n"
                      f"    for j in range(0, {n}):\n"
                      f"        contador += 1")
            just = f"Cada um dos {n} valores de i combina com {n} valores de j: {n}×{n} = {correta}."
            distratores = [n, 2 * n, n * (n - 1), n * (n + 1) // 2, n ** 3]
        else:
            correta = sum(1 for i in range(0, n, 2) for j in range(n))
            passos_i = len(range(0, n, 2))
            codigo = (f"for i in range(0, {n}, 2):\n"
                      f"    for j in range(0, {n}):\n"
                      f"        contador += 1")
            just = (f"O laço externo dá {passos_i} passos (de 2 em 2) e o "
                    f"interno {n}: {passos_i}×{n} = {correta}.")
            distratores = [n * n, n, passos_i, correta * 2, correta // 2 if correta > 1 else correta + 3]

        VARIACOES = [
            f"Considere o trecho de código a seguir:\n\n{codigo}\n\nQuantas vezes a "
            f"instrução 'contador += 1' será executada?",
            f"Um desenvolvedor escreveu o seguinte trecho para instrumentar um "
            f"módulo:\n\n{codigo}\n\nAo final da execução, qual será o valor de "
            f"'contador', supondo que ele foi inicializado com zero?",
            f"Analise o algoritmo abaixo:\n\n{codigo}\n\nDeterminando o custo exato "
            f"do trecho, quantas vezes a operação interna é executada?",
            f"Durante a análise de desempenho de um sistema, foi isolado o seguinte "
            f"laço:\n\n{codigo}\n\nQuantas execuções da instrução mais interna "
            f"ocorrem no total?",
        ]
        enunciado = rng.choice(VARIACOES)
        q = _montar(enunciado, correta, distratores,
                    f"{just} Total: {correta} execuções.",
                    "Análise de algoritmos", rng)
        if q:
            return q
    raise RuntimeError("contagem_operacoes")


def gerar_ordenacao_comparacoes(rng):
    """Bubble sort: comparações = n(n-1)/2 — verificado por simulação."""
    for _ in range(50):
        n = rng.choice([5, 6, 7, 8, 10])

        # simula o bubble sort padrão contando comparações
        comparacoes = 0
        v = list(range(n))
        for i in range(len(v)):
            for j in range(len(v) - i - 1):
                comparacoes += 1
        correta = comparacoes

        distratores = [n * n, n * (n - 1), n, n - 1, n * (n + 1) // 2]
        CONTEXTOS = [
            f"O algoritmo Bubble Sort, em sua versão sem otimização de parada "
            f"antecipada, é aplicado a um vetor de {n} elementos. Quantas comparações "
            f"entre elementos serão realizadas?",
            f"Um sistema de relatórios ordena uma lista de {n} registros utilizando "
            f"Bubble Sort sem parada antecipada. Quantas comparações entre pares de "
            f"registros o algoritmo executa?",
            f"Durante uma aula de algoritmos, um aluno implementa o Bubble Sort "
            f"clássico (com dois laços aninhados e sem flag de troca) para ordenar "
            f"{n} números. Quantas comparações serão feitas na execução?",
            f"Considere a implementação tradicional do Bubble Sort, que percorre o "
            f"vetor repetidamente até o fim, sem interromper quando já está ordenado. "
            f"Aplicando-a a {n} elementos, qual é o número total de comparações?",
            f"Um vetor com {n} posições é ordenado por Bubble Sort na versão que "
            f"sempre completa todas as passagens. Determine quantas comparações "
            f"entre elementos ocorrem.",
        ]
        enunciado = rng.choice(CONTEXTOS)
        explicacao = (
            f"São {n}−1 passagens; na passagem i há {n}−i−1 comparações. "
            f"O total é {n}×({n}−1)/2 = {correta} comparações."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Algoritmos de ordenação", rng)
        if q:
            return q
    raise RuntimeError("ordenacao_comparacoes")


# ══════════════════════════════════════════
#  ESTRUTURAS DE DADOS
# ══════════════════════════════════════════

def gerar_pilha(rng):
    """Simula uma pilha DE VERDADE e pergunta o resultado."""
    for _ in range(50):
        n_ops = rng.randint(7, 10)
        valores = rng.sample(range(10, 90), n_ops)

        ops, pilha, desempilhados = [], [], []
        vi = 0
        for _ in range(n_ops):
            if len(pilha) >= 2 and rng.random() < 0.4:
                ops.append("desempilha()")
                desempilhados.append(pilha.pop())
            else:
                v = valores[vi]; vi += 1
                ops.append(f"empilha({v})")
                pilha.append(v)

        if not pilha or len(desempilhados) < 2:
            continue

        pergunta = rng.choice(["topo", "tamanho", "ultimo_removido"])
        if pergunta == "topo":
            correta = pilha[-1]
            texto_q = "qual valor estará no topo da pilha ao final?"
            just = (f"Seguindo as operações, a pilha final tem seus elementos "
                    f"empilhados na ordem de inserção. Como o acesso é LIFO, o "
                    f"topo é o valor {correta}.")
            distratores = [pilha[0], desempilhados[-1], len(pilha),
                           pilha[-2] if len(pilha) > 1 else correta + 1, valores[0]]
        elif pergunta == "tamanho":
            correta = len(pilha)
            texto_q = "quantos elementos restarão na pilha ao final?"
            n_ins = n_ops - ops.count('desempilha()')
            n_rem = ops.count('desempilha()')
            just = (f"Houve {n_ins} {_plural(n_ins, 'inserção', 'inserções')} e "
                    f"{n_rem} {_plural(n_rem, 'remoção', 'remoções')}. A diferença "
                    f"entre elas indica que "
                    f"{_verbo(correta, 'resta', 'restam')} {correta} "
                    f"{_plural(correta, 'elemento')}.")
            distratores = [n_ops, len(desempilhados), correta + 1, correta - 1, n_ops - 1]
        else:
            correta = desempilhados[-1]
            texto_q = "qual foi o último valor removido da pilha?"
            just = (f"Cada desempilha() retira o elemento do topo naquele "
                    f"momento. A última remoção retirou o valor {correta}.")
            distratores = [desempilhados[0], pilha[-1], pilha[0], valores[0], correta + 1]

        seq = " → ".join(ops)
        enunciado = (
            f"Uma pilha (estrutura LIFO) inicialmente vazia recebe a "
            f"seguinte sequência de operações:\n\n{seq}\n\n"
            f"Considerando essa sequência, {texto_q}"
        )
        q = _montar(enunciado, correta, distratores, just,
                    "Estruturas de dados (pilha)", rng)
        if q:
            return q
    raise RuntimeError("pilha")


def gerar_fila(rng):
    """Simula uma fila DE VERDADE (FIFO)."""
    for _ in range(50):
        n_ops = rng.randint(7, 10)
        valores = rng.sample(range(10, 90), n_ops)

        ops, fila, removidos = [], [], []
        vi = 0
        for _ in range(n_ops):
            if len(fila) >= 2 and rng.random() < 0.4:
                ops.append("remove()")
                removidos.append(fila.pop(0))
            else:
                v = valores[vi]; vi += 1
                ops.append(f"insere({v})")
                fila.append(v)

        if not fila or len(removidos) < 2:
            continue

        pergunta = rng.choice(["frente", "tamanho"])
        if pergunta == "frente":
            correta = fila[0]
            texto_q = "qual valor estará na frente da fila ao final?"
            just = (f"Como o atendimento é FIFO, cada remove() retira sempre o "
                    f"elemento mais antigo. Ao final, na frente da fila está o "
                    f"valor {correta}.")
            distratores = [fila[-1], removidos[-1], removidos[0], len(fila), valores[0]]
        else:
            correta = len(fila)
            texto_q = "quantos elementos restarão na fila ao final?"
            n_ins = n_ops - len(removidos)
            n_rem = len(removidos)
            just = (f"Foram {n_ins} {_plural(n_ins, 'inserção', 'inserções')} contra "
                    f"{n_rem} {_plural(n_rem, 'remoção', 'remoções')}, de modo que "
                    f"{_verbo(correta, 'permanece', 'permanecem')} na fila exatamente "
                    f"{correta} {_plural(correta, 'elemento')}.")
            distratores = [n_ops, len(removidos), correta + 1, correta - 1, n_ops - 1]

        seq = " → ".join(ops)
        enunciado = (
            f"Uma fila (estrutura FIFO) inicialmente vazia recebe a "
            f"seguinte sequência de operações:\n\n{seq}\n\n"
            f"Considerando essa sequência, {texto_q}"
        )
        q = _montar(enunciado, correta, distratores, just,
                    "Estruturas de dados (fila)", rng)
        if q:
            return q
    raise RuntimeError("fila")


def _abertura_arvore(rng, vals):
    """Abertura variada para questões de árvore binária de busca."""
    lista = ", ".join(map(str, vals))
    ABERTURAS = [
        f"Os valores a seguir são inseridos, nesta ordem, em uma árvore "
        f"binária de busca inicialmente vazia:\n\n{lista}\n\nApós as inserções,",
        f"Uma árvore binária de busca vazia recebe as seguintes chaves, na "
        f"ordem apresentada:\n\n{lista}\n\nConcluídas as inserções,",
        f"Um índice de banco de dados é construído como árvore binária de "
        f"busca a partir das chaves abaixo, inseridas nesta sequência:"
        f"\n\n{lista}\n\nCom a árvore montada,",
        f"Em uma aula de estruturas de dados, os alunos inserem os números "
        f"abaixo, um a um e nesta ordem, em uma árvore binária de busca "
        f"inicialmente vazia:\n\n{lista}\n\nAo final do processo,",
        f"Considere a inserção sucessiva das chaves a seguir em uma árvore "
        f"binária de busca sem balanceamento:\n\n{lista}\n\nTerminadas as "
        f"inserções,",
        f"Um programa insere, na ordem indicada, os valores abaixo em uma "
        f"árvore binária de busca vazia:\n\n{lista}\n\nApós a execução,",
    ]
    return rng.choice(ABERTURAS)


def gerar_arvore_bst(rng):
    """Constrói uma BST DE VERDADE e pergunta percurso/altura."""
    class No:
        __slots__ = ("v", "esq", "dir")
        def __init__(self, v): self.v, self.esq, self.dir = v, None, None

    def inserir(raiz, v):
        if raiz is None: return No(v)
        if v < raiz.v: raiz.esq = inserir(raiz.esq, v)
        else:          raiz.dir = inserir(raiz.dir, v)
        return raiz

    def pre(n):  return ([n.v] + pre(n.esq) + pre(n.dir)) if n else []
    def ino(n):  return (ino(n.esq) + [n.v] + ino(n.dir)) if n else []
    def pos(n):  return (pos(n.esq) + pos(n.dir) + [n.v]) if n else []
    def alt(n):  return 0 if n is None else 1 + max(alt(n.esq), alt(n.dir))

    for _ in range(50):
        # MELHORIA 4: mais valores possíveis e tamanhos variados
        vals = rng.sample(range(5, 199), rng.randint(6, 9))
        raiz = None
        for v in vals: raiz = inserir(raiz, v)

        tipo = rng.choice(["pre", "pos", "altura", "folhas"])
        fmt = lambda x: ", ".join(map(str, x)) if isinstance(x, list) else str(x)

        if tipo == "pre":
            correta = pre(raiz)
            pergunta = "qual é a sequência do percurso em PRÉ-ORDEM (raiz, esquerda, direita)?"
            just = (f"Pré-ordem visita a raiz antes das subárvores. "
                    f"Resultado: {fmt(correta)}.")
            distratores = [ino(raiz), pos(raiz), vals, list(reversed(pre(raiz)))]
        elif tipo == "pos":
            correta = pos(raiz)
            pergunta = "qual é a sequência do percurso em PÓS-ORDEM (esquerda, direita, raiz)?"
            just = (f"Pós-ordem visita a raiz por último. Resultado: {fmt(correta)}.")
            distratores = [ino(raiz), pre(raiz), vals, list(reversed(pos(raiz)))]
        elif tipo == "altura":
            correta = alt(raiz)
            pergunta = "qual é a altura da árvore resultante (contando o número de níveis)?"
            just = (f"Percorrendo a árvore da raiz até a folha mais distante, "
                    f"contam-se os níveis. A altura é {correta}.")
            distratores = [correta + 1, correta - 1, len(vals), correta + 2, len(vals) - 1]
        else:
            correta = sum(1 for n in _todos_nos(raiz) if n.esq is None and n.dir is None)
            pergunta = "quantos nós folha (sem filhos) a árvore resultante possui?"
            just = (f"Analisando a árvore construída, os nós que não possuem "
                    f"filho esquerdo nem direito totalizam {correta}.")
            distratores = [correta + 1, correta - 1, len(vals), alt(raiz), len(vals) - correta]

        if tipo in ("pre", "pos"):
            correta_f = fmt(correta)
            distratores_f = [fmt(d) for d in distratores]
            _ab = _abertura_arvore(rng, vals)
            enunciado = f"{_ab} {_juntar(_ab, pergunta)}"
            q = _montar(enunciado, correta_f, distratores_f, just,
                        "Estruturas de dados (árvore)", rng, formatador=str,
                        tipo_resposta="sequencia")
        else:
            _ab = _abertura_arvore(rng, vals)
            enunciado = f"{_ab} {_juntar(_ab, pergunta)}"
            q = _montar(enunciado, correta, distratores, just,
                        "Estruturas de dados (árvore)", rng)
        if q:
            return q
    raise RuntimeError("arvore_bst")


def _todos_nos(n):
    if n is None: return []
    return [n] + _todos_nos(n.esq) + _todos_nos(n.dir)


def gerar_grafos(rng):
    """Propriedades de grafos — todas calculadas."""
    for _ in range(50):
        n = rng.randint(5, 14)      # MELHORIA 4: faixa ampliada
        tipo = rng.choice(["max_arestas", "arvore", "completo_grau", "dirigido"])

        if tipo == "max_arestas":
            correta = comb(n, 2)
            enunciado = rng.choice([
                f"Qual é o número máximo de arestas que um grafo simples não "
                f"direcionado com {n} vértices pode ter?",
                f"Um grafo simples não direcionado possui {n} vértices. Quantas "
                f"arestas ele terá se todos os pares de vértices estiverem ligados?",
                f"Em uma rede modelada como grafo simples não direcionado com {n} "
                f"nós, qual é a quantidade máxima de conexões possíveis?",
                f"Considerando um grafo simples e não direcionado de {n} vértices, "
                f"determine o número máximo de arestas que ele admite.",
                f"Um sistema de recomendação representa {n} usuários como vértices "
                f"de um grafo simples não direcionado. No cenário de conectividade "
                f"total, quantas arestas existiriam?",
            ])
            just = (f"Cada par de vértices distintos forma no máximo uma aresta: "
                    f"C({n},2) = {n}×{n-1}/2 = {correta}.")
            distratores = [n * (n - 1), n * n, n, 2 * n, comb(n, 2) + n]
        elif tipo == "arvore":
            correta = n - 1
            enunciado = rng.choice([
                f"Uma árvore é um grafo conexo e acíclico. Quantas arestas possui "
                f"uma árvore com {n} vértices?",
                f"Em teoria dos grafos, quantas arestas tem uma árvore de {n} vértices?",
                f"A hierarquia de diretórios de um sistema de arquivos é modelada "
                f"como uma árvore com {n} nós. Quantas ligações pai-filho existem?",
                f"Um grafo conexo e sem ciclos possui {n} vértices. Qual é o número "
                f"de arestas desse grafo?",
                f"Uma rede em topologia de árvore conecta {n} equipamentos sem formar "
                f"ciclos. Quantos enlaces são necessários?",
            ])
            just = (f"Toda árvore com v vértices tem exatamente v−1 arestas. "
                    f"Para {n} vértices: {n}−1 = {correta} "
                    f"{_plural(correta, 'aresta')}.")
            distratores = [n, n + 1, comb(n, 2), 2 * n - 1, n - 2]
        elif tipo == "completo_grau":
            correta = n - 1
            enunciado = rng.choice([
                f"Em um grafo completo K{n}, qual é o grau de cada vértice?",
                f"Considere o grafo completo K{n}. Qual o número de arestas incidentes "
                f"a um vértice qualquer?",
                f"Num grafo completo com {n} vértices, a quantos outros vértices cada "
                f"vértice está diretamente conectado?",
                f"Em uma malha totalmente conectada de {n} dispositivos, qual é o grau "
                f"de cada nó do grafo correspondente?",
            ])
            just = (f"Num grafo completo, cada vértice se liga a todos os outros "
                    f"{n}−1 vértices. Grau = {correta}.")
            distratores = [n, comb(n, 2), 2 * (n - 1), n + 1, n - 2]
        else:
            correta = n * (n - 1)
            enunciado = rng.choice([
                f"Qual é o número máximo de arcos em um grafo DIRECIONADO simples "
                f"com {n} vértices, sem laços?",
                f"Um dígrafo simples de {n} vértices não admite laços. Quantos arcos "
                f"ele pode ter no máximo?",
                f"Modelando {n} páginas web como um grafo direcionado simples (sem "
                f"autorreferência), qual é o número máximo de links possíveis?",
                f"Considerando um grafo orientado simples com {n} vértices e sem "
                f"laços, determine a quantidade máxima de arcos.",
            ])
            just = (f"Cada par ordenado de vértices distintos admite um arco: "
                    f"{n}×({n}−1) = {correta}.")
            distratores = [comb(n, 2), n * n, n, 2 * n, correta // 2]

        q = _montar(enunciado, correta, distratores, just,
                    "Teoria dos grafos", rng)
        if q:
            return q
    raise RuntimeError("grafos")


# ══════════════════════════════════════════
#  MATEMÁTICA COMPUTACIONAL
# ══════════════════════════════════════════

def gerar_conversao_bases(rng):
    """Conversão entre bases — calculada."""
    for _ in range(50):
        modo = rng.choice(["dec_bin", "bin_dec", "dec_hex", "hex_dec"])
        n = rng.randint(20, 250)

        if modo == "dec_bin":
            correta = bin(n)[2:]
            enunciado = f"Qual é a representação do número decimal {n} na base 2 (binário)?"
            just = f"Dividindo {n} sucessivamente por 2 e lendo os restos de baixo para cima: {correta}."
            distratores = [bin(n + 1)[2:], bin(n - 1)[2:], oct(n)[2:], bin(n * 2)[2:], hex(n)[2:].upper()]
        elif modo == "bin_dec":
            b = bin(n)[2:]
            correta = str(n)
            enunciado = f"O número binário {b} corresponde a qual valor na base decimal?"
            pesos = " + ".join(f"{d}×2^{len(b)-1-i}" for i, d in enumerate(b) if d == "1")
            just = f"Somando os pesos das posições com bit 1: {pesos} = {n}."
            distratores = [str(n + 1), str(n - 1), str(int(b)), str(n * 2), str(len(b))]
        elif modo == "dec_hex":
            correta = hex(n)[2:].upper()
            enunciado = f"Qual é a representação do número decimal {n} na base 16 (hexadecimal)?"
            just = f"Dividindo {n} por 16 sucessivamente e convertendo os restos: {correta}."
            distratores = [hex(n + 1)[2:].upper(), hex(n - 1)[2:].upper(), bin(n)[2:], oct(n)[2:], str(n)]
        else:
            h = hex(n)[2:].upper()
            correta = str(n)
            enunciado = f"O número hexadecimal {h} corresponde a qual valor na base decimal?"
            just = f"Cada dígito hexadecimal vale 16 elevado à sua posição. Resultado: {n}."
            distratores = [str(n + 1), str(n - 1), str(n * 16), str(int(h, 8)) if all(c in "01234567" for c in h) else str(n + 16), str(n // 2)]

        q = _montar(enunciado, correta, distratores, just,
                    "Sistemas de numeração", rng, formatador=str,
                    tipo_resposta="codigo_numerico")
        if q:
            return q
    raise RuntimeError("conversao_bases")


def gerar_binario_operacoes(rng):
    """Soma binária e complemento de dois — calculados."""
    for _ in range(50):
        modo = rng.choice(["soma", "complemento", "bits_necessarios"])

        if modo == "soma":
            a, b = rng.randint(5, 60), rng.randint(5, 60)
            correta = bin(a + b)[2:]
            enunciado = (f"Considere os números binários {bin(a)[2:]} e "
                         f"{bin(b)[2:]}. Qual é o resultado da soma, em binário?")
            just = (f"{bin(a)[2:]} = {a} e {bin(b)[2:]} = {b} em decimal. "
                    f"A soma é {a}+{b} = {a+b}, que em binário é {correta}.")
            distratores = [bin(a + b + 1)[2:], bin(a + b - 1)[2:], bin(a * b)[2:],
                           bin(abs(a - b))[2:], bin((a + b) * 2)[2:]]
        elif modo == "complemento":
            bits = 8
            v = rng.randint(1, 100)
            correta = format((1 << bits) - v, f"0{bits}b")
            enunciado = (f"Em uma representação de {bits} bits com complemento "
                         f"de dois, qual é a representação binária de −{v}?")
            just = (f"Complemento de dois de {v}: inverte-se os bits de "
                    f"{format(v, f'0{bits}b')} e soma-se 1, resultando em {correta}.")
            distratores = [format(v, f"0{bits}b"),
                           format(((1 << bits) - 1) ^ v, f"0{bits}b"),
                           format((1 << bits) - v - 1, f"0{bits}b"),
                           format((1 << bits) - v + 1, f"0{bits}b")]
        else:
            n_valores = rng.choice([16, 32, 64, 100, 256, 500, 1000])
            correta = max(1, ceil(log2(n_valores)))
            enunciado = (f"Quantos bits são necessários, no mínimo, para "
                         f"representar {n_valores} valores distintos?")
            just = (f"É preciso que 2^b ≥ {n_valores}. Como 2^{correta} = "
                    f"{2**correta} ≥ {n_valores}, são necessários {correta} bits.")
            distratores = [correta + 1, correta - 1, n_valores, correta * 2, 8]

        q = _montar(enunciado, correta, distratores, just,
                    "Aritmética computacional", rng, formatador=str,
                    tipo_resposta="codigo_numerico")
        if q:
            return q
    raise RuntimeError("binario_operacoes")


def gerar_logica_proposicional(rng):
    """Tabela-verdade calculada por força bruta real."""
    formulas = [
        ("(p ∧ q) → r",       lambda p,q,r: (not (p and q)) or r),
        ("p ∨ (q ∧ ¬r)",      lambda p,q,r: p or (q and not r)),
        ("(p → q) ∧ (q → r)", lambda p,q,r: ((not p) or q) and ((not q) or r)),
        ("¬(p ∧ q) ∨ r",      lambda p,q,r: (not (p and q)) or r),
        ("(p ↔ q) ∧ r",       lambda p,q,r: (p == q) and r),
        ("p ⊕ (q ∨ r)",       lambda p,q,r: p != (q or r)),
    ]
    for _ in range(50):
        texto, fn = rng.choice(formulas)
        linhas = list(product([True, False], repeat=3))
        correta = sum(1 for p, q, r in linhas if fn(p, q, r))
        if correta in (0, 8):
            continue

        VARIACOES = [
            f"Considere a fórmula proposicional a seguir, em que p, q e r são "
            f"variáveis booleanas:\n\n{texto}\n\nEm quantas das 8 linhas da "
            f"tabela-verdade essa fórmula assume o valor VERDADEIRO?",
            f"Um sistema de regras de negócio é modelado pela expressão lógica "
            f"abaixo, com p, q e r representando condições booleanas:\n\n{texto}\n\n"
            f"Construindo a tabela-verdade completa, em quantas combinações a "
            f"expressão resulta em VERDADEIRO?",
            f"Analise a proposição composta a seguir:\n\n{texto}\n\nSabendo que p, q "
            f"e r assumem valores verdadeiro ou falso, quantas das 8 atribuições "
            f"possíveis tornam a proposição verdadeira?",
            f"Durante a verificação formal de um módulo, obteve-se a seguinte "
            f"condição booleana:\n\n{texto}\n\nDentre todas as combinações possíveis "
            f"de p, q e r, em quantas a condição é satisfeita?",
        ]
        enunciado = rng.choice(VARIACOES)
        just = (f"Avaliando as 8 combinações possíveis de p, q e r, a fórmula "
                f"resulta em verdadeiro em {correta} delas.")
        distratores = [correta + 1, correta - 1, 8 - correta, 4, 8]

        q = _montar(enunciado, correta, distratores, just,
                    "Lógica proposicional", rng)
        if q:
            return q
    raise RuntimeError("logica_proposicional")


def gerar_conjuntos(rng):
    """Inclusão-exclusão — calculado."""
    for _ in range(50):
        inter = rng.randint(4, 35)      # MELHORIA 4
        so_a  = rng.randint(8, 70)
        so_b  = rng.randint(8, 70)
        a, b  = so_a + inter, so_b + inter
        total_uniao = so_a + so_b + inter

        tipo = rng.choice(["uniao", "so_um", "nenhum"])
        ling = rng.choice([
            ("Java", "Python"), ("SQL", "NoSQL"), ("front-end", "back-end"),
            ("React", "Angular"), ("Docker", "Kubernetes"), ("C#", "Go"),
            ("testes automatizados", "integração contínua"),
            ("análise de dados", "aprendizado de máquina"),
        ])

        if tipo == "uniao":
            correta = total_uniao
            pergunta = f"quantos desenvolvedores conhecem {ling[0]} OU {ling[1]}?"
            just = (f"Pelo princípio da inclusão-exclusão: |A ∪ B| = {a} + {b} − "
                    f"{inter} = {correta}.")
            distratores = [a + b, a + b + inter, inter, a, b]
        elif tipo == "so_um":
            correta = so_a + so_b
            pergunta = f"quantos conhecem exatamente UMA das duas tecnologias?"
            just = (f"Quem conhece só {ling[0]}: {a}−{inter} = {so_a}. Só "
                    f"{ling[1]}: {b}−{inter} = {so_b}. Total: {correta}.")
            distratores = [total_uniao, a + b, inter, so_a, so_b]
        else:
            # A folga era de 5 a 25, então a resposta ("quantos ficam de
            # fora") caía em um algarismo quase metade das vezes,
            # enquanto os distratores — união, equipe, equipe menos a —
            # têm dois ou três. A resposta certa era a alternativa mais
            # curta. De 11 para cima, todas ficam no mesmo porte.
            equipe = total_uniao + rng.randint(11, 60)
            correta = equipe - total_uniao
            pergunta = (f"se a equipe tem {equipe} desenvolvedores no total, "
                        f"quantos não conhecem nenhuma das duas?")
            just = (f"|A ∪ B| = {a} + {b} − {inter} = {total_uniao}. "
                    f"Fora da união: {equipe} − {total_uniao} = {correta}.")
            distratores = [total_uniao, equipe - a, equipe - b, inter, equipe]

        CENARIOS_CONJ = [
            f"Em uma equipe de desenvolvimento, {a} pessoas conhecem {ling[0]}, "
            f"{b} conhecem {ling[1]} e {inter} conhecem ambas as tecnologias.",
            f"Uma pesquisa interna revelou que {a} profissionais dominam {ling[0]}, "
            f"{b} dominam {ling[1]} e {inter} dominam as duas.",
            f"O levantamento de competências de uma empresa registrou {a} pessoas "
            f"com {ling[0]}, {b} com {ling[1]} e {inter} com as duas habilidades.",
            f"Em um processo seletivo, {a} candidatos declararam conhecer {ling[0]}, "
            f"{b} declararam conhecer {ling[1]} e {inter} declararam conhecer ambas.",
            f"Uma consultoria mapeou o time de tecnologia: {a} integrantes trabalham "
            f"com {ling[0]}, {b} trabalham com {ling[1]} e {inter} atuam nas duas frentes.",
            f"Segundo o cadastro de habilidades, {a} colaboradores sabem {ling[0]}, "
            f"{b} sabem {ling[1]} e {inter} sabem as duas tecnologias.",
        ]
        LIGACOES_CONJ = ["Nessas condições,", "Com base nesses dados,",
                         "A partir dessas informações,", "Diante desse cenário,",
                         "Considerando esse levantamento,"]
        _cen = rng.choice(CENARIOS_CONJ)
        _lig = rng.choice(LIGACOES_CONJ)
        enunciado = (f"{_cen} {_juntar(_cen, _lig)} "
                     f"{_juntar(_lig, pergunta)}")
        q = _montar(enunciado, correta, distratores, just,
                    "Teoria dos conjuntos", rng)
        if q:
            return q
    raise RuntimeError("conjuntos")


# ══════════════════════════════════════════
#  BANCO DE DADOS
# ══════════════════════════════════════════

def gerar_sql_resultado(rng):
    """Monta uma tabela, EXECUTA a query mentalmente em Python, valida."""
    for _ in range(50):
        # MELHORIA 4: nomes, departamentos e salários sorteados de pools amplos
        POOL_NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elena", "Felipe", "Gabi",
                      "Heitor", "Iara", "Joao", "Karina", "Lucas", "Marina",
                      "Nadia", "Otavio", "Paula", "Rafael", "Sofia", "Tiago", "Vera"]
        POOL_DEPS = ["TI", "RH", "Vendas", "Financeiro", "Logistica", "Juridico"]
        n = rng.randint(5, 8)
        nomes = rng.sample(POOL_NOMES, n)
        # garante que "TI" apareça ao menos uma vez (a query de AVG usa TI)
        deps = ["TI"] + [rng.choice(POOL_DEPS) for _ in range(n - 1)]
        rng.shuffle(deps)
        if "TI" not in deps:
            deps[0] = "TI"
        sals = [rng.randrange(2200, 9800, 100) for _ in range(n)]
        linhas = list(zip(nomes, deps, sals))

        tipo = rng.choice(["where", "count_group", "avg", "max_where"])
        limite = rng.choice([3000, 4000, 5000])

        if tipo == "where":
            correta = sum(1 for _, _, s in linhas if s > limite)
            query = f"SELECT nome FROM funcionarios WHERE salario > {limite};"
            pergunta = "Quantas linhas essa consulta retorna?"
            just = (f"Salários acima de {limite}: "
                    f"{[s for _,_,s in linhas if s > limite]}. "
                    f"Total: {correta} linha(s).")
            distratores = [len(linhas), correta + 1, correta - 1,
                           len(linhas) - correta, 0]
        elif tipo == "count_group":
            dep_alvo = rng.choice(list(set(deps[:n])))
            correta = sum(1 for _, d, _ in linhas if d == dep_alvo)
            query = (f"SELECT departamento, COUNT(*) FROM funcionarios "
                     f"GROUP BY departamento;")
            pergunta = f"Qual valor de COUNT(*) é retornado para o departamento '{dep_alvo}'?"
            just = (f"Registros com departamento '{dep_alvo}': {correta}.")
            distratores = [len(linhas), correta + 1, correta - 1,
                           len(set(d for _, d, _ in linhas)), 0]
        elif tipo == "avg":
            dep_alvo = "TI"
            sal_ti = [s for _, d, s in linhas if d == dep_alvo]
            if not sal_ti: continue
            correta = round(sum(sal_ti) / len(sal_ti))
            query = (f"SELECT AVG(salario) FROM funcionarios "
                     f"WHERE departamento = '{dep_alvo}';")
            pergunta = "Qual é o valor retornado (arredondado)?"
            just = (f"Salários de {dep_alvo}: {sal_ti}. Média: "
                    f"{sum(sal_ti)}/{len(sal_ti)} = {correta}.")
            distratores = [sum(sal_ti), max(sal_ti), min(sal_ti),
                           round(sum(s for _,_,s in linhas)/len(linhas)), len(sal_ti)]
        else:
            correta = max((s for _, _, s in linhas if s > limite), default=0)
            if correta == 0: continue
            query = f"SELECT MAX(salario) FROM funcionarios WHERE salario > {limite};"
            pergunta = "Qual é o valor retornado?"
            just = (f"Entre os salários acima de {limite}, o maior é {correta}.")
            distratores = [max(s for _,_,s in linhas), min(s for _,_,s in linhas),
                           limite, sum(s for _,_,s in linhas), correta - 100]

        tabela = "\n".join(f"  {nm:<8} | {dp:<8} | {sl}" for nm, dp, sl in linhas)
        cabecalho = ("  nome     | departamento | salario\n"
                     "  ---------|--------------|--------")
        VARIACOES = [
            f"Considere a tabela 'funcionarios' abaixo:\n\n{cabecalho}\n{tabela}\n\n"
            f"Sobre essa tabela, executa-se a consulta:\n\n{query}\n\n{pergunta}",
            f"O setor de RH mantém a tabela 'funcionarios' com os dados a seguir:"
            f"\n\n{cabecalho}\n{tabela}\n\nUm relatório é gerado a partir da consulta:"
            f"\n\n{query}\n\n{pergunta}",
            f"Analise o conteúdo da tabela 'funcionarios':\n\n{cabecalho}\n{tabela}\n\n"
            f"Um desenvolvedor executa o seguinte comando SQL:\n\n{query}\n\n{pergunta}",
            f"Um banco de dados corporativo armazena os registros abaixo na tabela "
            f"'funcionarios':\n\n{cabecalho}\n{tabela}\n\nConsiderando a consulta:"
            f"\n\n{query}\n\n{pergunta}",
        ]
        enunciado = rng.choice(VARIACOES)
        q = _montar(enunciado, correta, distratores, just, "SQL e banco de dados", rng)
        if q:
            return q
    raise RuntimeError("sql_resultado")


def gerar_sql_join(rng):
    """Cardinalidade de JOIN — calculada por simulação real."""
    for _ in range(50):
        n_clientes = rng.randint(4, 6)
        clientes = list(range(1, n_clientes + 1))
        # pedidos referenciam clientes (alguns clientes sem pedido)
        n_pedidos = rng.randint(5, 8)
        pedidos = [rng.choice(clientes[:n_clientes - 1]) for _ in range(n_pedidos)]

        tipo = rng.choice(["inner", "left", "sem_pedido"])
        if tipo == "inner":
            correta = len(pedidos)   # todo pedido tem cliente válido
            query = ("SELECT * FROM clientes c\n"
                     "INNER JOIN pedidos p ON c.id = p.cliente_id;")
            just = (f"Cada um dos {n_pedidos} pedidos casa com exatamente um "
                    f"cliente, então o INNER JOIN retorna {correta} linhas.")
            distratores = [n_clientes, n_clientes * n_pedidos, n_clientes + n_pedidos,
                           len(set(pedidos)), correta + 1]
        elif tipo == "left":
            sem_pedido = [c for c in clientes if c not in pedidos]
            correta = len(pedidos) + len(sem_pedido)
            query = ("SELECT * FROM clientes c\n"
                     "LEFT JOIN pedidos p ON c.id = p.cliente_id;")
            just = (f"O LEFT JOIN mantém todos os clientes: {len(pedidos)} linhas "
                    f"dos pedidos existentes mais {len(sem_pedido)} cliente(s) sem "
                    f"pedido (com NULL), totalizando {correta}.")
            distratores = [len(pedidos), n_clientes, n_clientes * n_pedidos,
                           len(set(pedidos)), correta + 1]
        else:
            correta = len([c for c in clientes if c not in pedidos])
            if correta == 0: continue
            query = ("SELECT COUNT(*) FROM clientes c\n"
                     "LEFT JOIN pedidos p ON c.id = p.cliente_id\n"
                     "WHERE p.cliente_id IS NULL;")
            just = (f"Clientes sem nenhum pedido correspondente: {correta}.")
            distratores = [n_clientes, len(pedidos), len(set(pedidos)),
                           correta + 1, 0]

        t_cli = ", ".join(str(c) for c in clientes)
        t_ped = ", ".join(str(p) for p in pedidos)
        corpo = (f"  clientes → ids: {t_cli}\n"
                 f"  pedidos  → cliente_id de cada pedido: {t_ped}")
        VARIACOES = [
            f"Considere duas tabelas de um banco relacional:\n\n{corpo}\n\n"
            f"Executa-se a consulta:\n\n{query}\n\nQuantas linhas o resultado apresenta?",
            f"Um sistema de e-commerce mantém as tabelas abaixo:\n\n{corpo}\n\n"
            f"Um analista executa a seguinte instrução SQL:\n\n{query}\n\n"
            f"Qual é a quantidade de registros retornados?",
            f"Durante uma auditoria de dados, foram levantadas as seguintes "
            f"informações:\n\n{corpo}\n\nAo rodar a consulta:\n\n{query}\n\n"
            f"quantas linhas compõem o conjunto resultado?",
            f"Observe o conteúdo de duas tabelas relacionadas:\n\n{corpo}\n\n"
            f"Considerando a consulta abaixo:\n\n{query}\n\nquantas tuplas são "
            f"retornadas?",
        ]
        enunciado = rng.choice(VARIACOES)
        q = _montar(enunciado, correta, distratores, just, "SQL e banco de dados", rng)
        if q:
            return q
    raise RuntimeError("sql_join")


# ══════════════════════════════════════════
#  SISTEMAS E REDES
# ══════════════════════════════════════════

def gerar_redes_subrede(rng):
    """Sub-rede calculada com a biblioteca ipaddress (correto por definição)."""
    for _ in range(50):
        # MELHORIA 4: espaço de parâmetros muito maior
        prefixo = rng.choice([22, 23, 24, 25, 26, 27, 28, 29, 30])
        faixa = rng.choice([
            f"192.168.{rng.randint(0, 254)}.0",
            f"10.{rng.randint(0, 254)}.{rng.randint(0, 254)}.0",
            f"172.{rng.randint(16, 31)}.{rng.randint(0, 254)}.0",
        ])
        base = f"{faixa}/{prefixo}"
        rede = ipaddress.ip_network(base, strict=False)
        CENARIOS_REDE = [
            "Considere a rede {base}.",
            "Um administrador configurou a sub-rede {base} em um roteador.",
            "O plano de endereçamento de uma filial reservou o bloco {base}.",
            "Durante a segmentação de uma rede corporativa, definiu-se o bloco {base}.",
            "Um data center aloca o intervalo {base} para um novo ambiente.",
            "A documentação de infraestrutura registra a sub-rede {base}.",
            "Em um laboratório de redes, os alunos analisam o bloco {base}.",
        ]
        cen_rede = rng.choice(CENARIOS_REDE).format(base=base)

        tipo = rng.choice(["hosts", "mascara", "broadcast"])
        if tipo == "hosts":
            correta = rede.num_addresses - 2
            pergunta = "quantos endereços IP podem ser atribuídos a hosts nessa sub-rede?"
            just = (f"O prefixo /{prefixo} deixa {32-prefixo} bits para hosts, o que "
                    f"dá {rede.num_addresses} endereços no bloco. Retirando o endereço "
                    f"de rede e o de broadcast, sobram {correta} utilizáveis.")
            distratores = [rede.num_addresses, rede.num_addresses - 1,
                           rede.num_addresses + 2, 32 - prefixo, prefixo]
            LIGACOES = ["Nessas condições,", "Diante disso,", "A partir dessa informação,",
                        "Considerando esse endereçamento,", "Com base nesse bloco,"]
            _lig = rng.choice(LIGACOES)
            q = _montar(f"{cen_rede} {_juntar(cen_rede, _lig)} "
                        f"{_juntar(_lig, pergunta)}",
                        correta, distratores, just, "Redes de computadores", rng)
        elif tipo == "mascara":
            correta = str(rede.netmask)
            pergunta = "qual é a máscara de sub-rede correspondente em notação decimal?"
            just = (f"Um prefixo /{prefixo} equivale a {prefixo} bits em 1 seguidos de "
                    f"{32-prefixo} bits em 0, que em notação decimal é {correta}.")
            outros = [24, 25, 26, 27, 28, 29, 30]
            distratores = [str(ipaddress.ip_network(f"10.0.0.0/{p}").netmask)
                           for p in outros if p != prefixo]
            LIGACOES = ["Nessas condições,", "Diante disso,", "A partir dessa informação,",
                        "Considerando esse endereçamento,", "Com base nesse bloco,"]
            _lig = rng.choice(LIGACOES)
            q = _montar(f"{cen_rede} {_juntar(cen_rede, _lig)} "
                        f"{_juntar(_lig, pergunta)}",
                        correta, distratores, just, "Redes de computadores", rng,
                        formatador=str, tipo_resposta="endereco_ip")
        else:
            correta = str(rede.broadcast_address)
            pergunta = "qual é o endereço de broadcast dessa sub-rede?"
            just = (f"A sub-rede abrange {rede.num_addresses} endereços consecutivos, "
                    f"e o último deles é reservado para broadcast: {correta}.")
            distratores = [str(rede.network_address),
                           str(list(rede.hosts())[0]),
                           str(list(rede.hosts())[-1]),
                           str(rede.broadcast_address + 1)]
            LIGACOES = ["Nessas condições,", "Diante disso,", "A partir dessa informação,",
                        "Considerando esse endereçamento,", "Com base nesse bloco,"]
            _lig = rng.choice(LIGACOES)
            q = _montar(f"{cen_rede} {_juntar(cen_rede, _lig)} "
                        f"{_juntar(_lig, pergunta)}",
                        correta, distratores, just, "Redes de computadores", rng,
                        formatador=str, tipo_resposta="endereco_ip")
        if q:
            return q
    raise RuntimeError("redes_subrede")


def gerar_escalonamento(rng):
    """Escalonamento de processos — tempos calculados por simulação."""
    for _ in range(50):
        n = rng.randint(3, 4)
        nomes = [f"P{i+1}" for i in range(n)]
        duracoes = [rng.randint(2, 9) for _ in range(n)]

        politica = rng.choice(["FIFO", "SJF"])
        if politica == "FIFO":
            ordem = list(range(n))
        else:
            ordem = sorted(range(n), key=lambda i: duracoes[i])

        # tempo de espera: soma das durações anteriores
        espera, t = {}, 0
        for i in ordem:
            espera[i] = t
            t += duracoes[i]

        total_espera = sum(espera.values())
        media = total_espera / n
        correta = round(media, 2)

        # distratores: média com a outra política, turnaround, etc
        ordem_alt = sorted(range(n), key=lambda i: duracoes[i]) if politica == "FIFO" else list(range(n))
        esp_alt, t2 = {}, 0
        for i in ordem_alt:
            esp_alt[i] = t2
            t2 += duracoes[i]
        media_alt = round(sum(esp_alt.values()) / n, 2)
        turnaround = round((total_espera + sum(duracoes)) / n, 2)

        distratores = [media_alt, turnaround, round(sum(duracoes)/n, 2),
                       float(total_espera), round(media + 1, 2)]

        tabela = "\n".join(f"  {nomes[i]}: {duracoes[i]} ms" for i in range(n))
        desc_pol = 'ordem de chegada' if politica == 'FIFO' else 'menor job primeiro'
        VARIACOES = [
            f"Considere {n} processos que chegam simultaneamente ao escalonador, "
            f"com os seguintes tempos de execução:\n\n{tabela}\n\nUtilizando a "
            f"política de escalonamento {politica} ({desc_pol}), qual é o tempo "
            f"médio de espera dos processos, em milissegundos?",
            f"Um sistema operacional recebe {n} processos no mesmo instante, com "
            f"as durações de CPU abaixo:\n\n{tabela}\n\nAplicando o algoritmo "
            f"{politica} ({desc_pol}), determine o tempo médio de espera, em ms.",
            f"Em um servidor, {n} tarefas são submetidas simultaneamente à fila de "
            f"execução:\n\n{tabela}\n\nCom a política {politica} ({desc_pol}), qual "
            f"o tempo médio que uma tarefa aguarda antes de iniciar, em milissegundos?",
            f"A tabela a seguir mostra o tempo de burst de {n} processos que chegam "
            f"juntos ao escalonador:\n\n{tabela}\n\nEscalonando por {politica} "
            f"({desc_pol}), calcule o tempo médio de espera em ms.",
        ]
        enunciado = rng.choice(VARIACOES)
        seq = " → ".join(nomes[i] for i in ordem)
        esperas_txt = ", ".join(f"{nomes[i]}={espera[i]}" for i in ordem)
        just = (f"Com {politica}, a ordem de execução é {seq}. Os tempos de "
                f"espera são {esperas_txt}, somando {total_espera}. "
                f"A média é {total_espera}/{n} = {correta} ms.")

        q = _montar(enunciado, correta, distratores, just,
                    "Sistemas operacionais", rng,
                    formatador=lambda v: f"{v:.2f}".replace(".", ","))
        if q:
            return q
    raise RuntimeError("escalonamento")


# ══════════════════════════════════════════
#  ENGENHARIA DE SOFTWARE
# ══════════════════════════════════════════

def gerar_pontos_funcao(rng):
    """
    Análise de Pontos de Função — cálculo real dos PF não ajustados.
    Pesos oficiais IFPUG para complexidade média.
    """
    PESOS = {"ALI": (7, 10, 15), "AIE": (5, 7, 10), "EE": (3, 4, 6),
             "SE": (4, 5, 7), "CE": (3, 4, 6)}
    NOMES = {"ALI": "Arquivos Lógicos Internos", "AIE": "Arquivos de Interface Externa",
             "EE": "Entradas Externas", "SE": "Saídas Externas", "CE": "Consultas Externas"}
    NIVEL = {0: "baixa", 1: "média", 2: "alta"}

    for _ in range(60):
        itens, total, linhas = {}, 0, []
        for tipo in ["ALI", "EE", "SE", "CE"]:
            qtd = rng.randint(1, 8)
            idx = rng.randint(0, 2)
            peso = PESOS[tipo][idx]
            itens[tipo] = (qtd, peso, NIVEL[idx])
            total += qtd * peso
            linhas.append(f"  {NOMES[tipo]}: {qtd} de complexidade {NIVEL[idx]} (peso {peso})")

        tabela = "\n".join(linhas)
        detalhe = " + ".join(f"{q}×{p}" for q, p, _ in itens.values())

        CENARIOS = [
            "Uma equipe realizou a contagem de pontos de função de um sistema e "
            "levantou os seguintes componentes:",
            "Durante a estimativa de um projeto, o analista identificou os "
            "componentes abaixo:",
            "O documento de requisitos de um sistema resultou na seguinte "
            "contagem de funções:",
            "Para orçar um desenvolvimento, foram catalogados estes componentes "
            "funcionais:",
        ]
        PERGUNTAS = [
            "Qual é o total de Pontos de Função Não Ajustados (PFNA)?",
            "Qual o valor dos Pontos de Função Não Ajustados desse sistema?",
            "Determine o total de PF não ajustados.",
            "A contagem de Pontos de Função Não Ajustados resulta em:",
        ]
        cen = rng.choice(CENARIOS)
        enunciado = f"{cen}\n\n{tabela}\n\n{rng.choice(PERGUNTAS)}"

        correta = total
        distratores = [
            sum(q for q, _, _ in itens.values()),
            sum(p for _, p, _ in itens.values()),
            total + 10, total - 10,
            round(total * 1.35),
        ]
        explicacao = (
            f"Os PF não ajustados somam quantidade × peso de cada componente: "
            f"{detalhe} = {correta} pontos de função."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Engenharia de software (métricas)", rng)
        if q:
            return q
    raise RuntimeError("pontos_funcao")


def gerar_cobertura_testes(rng):
    """
    Cobertura de código e complexidade ciclomática — calculadas.
    A complexidade usa a fórmula de McCabe (decisões + 1).
    """
    for _ in range(60):
        modo = rng.choice(["cobertura", "ciclomatica", "caminhos"])

        if modo == "cobertura":
            total_linhas = rng.randint(80, 400)
            cobertas = rng.randint(int(total_linhas * 0.4), total_linhas - 5)
            correta = round(cobertas / total_linhas * 100, 1)
            CEN = [
                f"Uma ferramenta de análise reportou que, de {total_linhas} linhas "
                f"executáveis de um módulo, {cobertas} foram exercitadas pelos "
                f"testes automatizados.",
                f"O relatório de cobertura de um projeto indica {cobertas} linhas "
                f"cobertas em um total de {total_linhas} linhas executáveis.",
                f"Após a execução da suíte de testes, {cobertas} das {total_linhas} "
                f"linhas de um componente foram percorridas.",
            ]
            PER = [
                "Qual é o percentual de cobertura de linhas obtido?",
                "A cobertura de código alcançada é de aproximadamente:",
                "Determine o percentual de cobertura de linhas.",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"A cobertura de linhas é a razão entre linhas exercitadas e "
                f"linhas executáveis: {cobertas}/{total_linhas} × 100 = "
                f"{correta}%."
            )
            distratores = [
                round((total_linhas - cobertas) / total_linhas * 100, 1),
                round(cobertas / total_linhas * 100 + 10, 1),
                round(cobertas / total_linhas * 100 - 10, 1),
                round(cobertas / (total_linhas + cobertas) * 100, 1),
            ]
            fmt = lambda v: f"{v:.1f}%".replace(".", ",")

        elif modo == "ciclomatica":
            n_if    = rng.randint(1, 5)
            n_while = rng.randint(0, 3)
            n_and   = rng.randint(0, 3)
            decisoes = n_if + n_while + n_and
            correta = decisoes + 1
            partes = []
            if n_if:    partes.append(f"{n_if} comando(s) if")
            if n_while: partes.append(f"{n_while} laço(s) while")
            if n_and:   partes.append(f"{n_and} operador(es) lógico(s) AND em condições")
            lista = ", ".join(partes)
            CEN = [
                f"Uma função possui {lista}, sem outros pontos de decisão.",
                f"Ao revisar um método, a equipe contabilizou {lista}.",
                f"Um analisador estático identificou em uma rotina {lista}.",
            ]
            PER = [
                "Qual é a complexidade ciclomática de McCabe dessa função?",
                "Qual o valor da complexidade ciclomática?",
                "A complexidade ciclomática dessa rotina é:",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Pela fórmula de McCabe, a complexidade ciclomática é o número "
                f"de pontos de decisão mais 1. Com {decisoes} decisões, o "
                f"resultado é {decisoes} + 1 = {correta}."
            )
            distratores = [decisoes, correta + 1, correta + 2, decisoes * 2, 1]
            fmt = _fmt

        else:
            n_if = rng.randint(2, 5)
            correta = 2 ** n_if
            CEN = [
                f"Um trecho de código contém {n_if} comandos if independentes e "
                f"sequenciais, cada um com desvio verdadeiro e falso.",
                f"Uma rotina apresenta {n_if} decisões binárias independentes em "
                f"sequência.",
                f"Um método executa {n_if} verificações condicionais independentes, "
                f"cada uma podendo seguir dois caminhos.",
            ]
            PER = [
                "Quantos caminhos de execução distintos existem nesse trecho?",
                "Qual é o número de caminhos possíveis para cobertura total?",
                "Determine a quantidade de caminhos de execução distintos.",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Cada decisão independente dobra o número de caminhos. Com "
                f"{n_if} decisões binárias: 2^{n_if} = {correta} caminhos."
            )
            distratores = [n_if, n_if * 2, n_if + 1, 2 * n_if + 1, correta // 2]
            fmt = _fmt

        tipo = "percentual" if modo == "cobertura" else "numerica"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Engenharia de software (qualidade)", rng, formatador=fmt,
                    tipo_resposta=tipo)
        if q:
            return q
    raise RuntimeError("cobertura_testes")


def gerar_metricas_projeto(rng):
    """Velocidade de sprint, esforço e prazo — aritmética de projeto real."""
    for _ in range(60):
        modo = rng.choice(["velocidade", "sprints", "esforco"])

        if modo == "velocidade":
            sprints = rng.randint(3, 6)
            pontos = [rng.randrange(15, 55) for _ in range(sprints)]
            correta = round(sum(pontos) / sprints, 1)
            lista = ", ".join(f"{p}" for p in pontos)
            CEN = [
                f"Uma equipe ágil entregou, nas últimas {sprints} sprints, os "
                f"seguintes totais de pontos de história: {lista}.",
                f"O histórico de entregas de um time nas {sprints} sprints mais "
                f"recentes foi: {lista} pontos.",
                f"Um quadro de acompanhamento registra as entregas de {sprints} "
                f"sprints consecutivas: {lista} pontos de história.",
            ]
            PER = [
                "Qual é a velocidade média da equipe, em pontos por sprint?",
                "A velocidade média do time é de aproximadamente:",
                "Determine a velocidade média por sprint.",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"A velocidade média é a soma dos pontos dividida pelo número de "
                f"sprints: {sum(pontos)}/{sprints} = {correta} pontos por sprint."
            )
            distratores = [sum(pontos), max(pontos), min(pontos),
                           round(sum(pontos) / (sprints + 1), 1), sprints]
            fmt = lambda v: (f"{v:.1f}".replace(".", ",") if isinstance(v, float) else _fmt(v))

        elif modo == "sprints":
            backlog = rng.randrange(120, 500, 10)
            veloc = rng.randrange(20, 60, 5)
            correta = ceil(backlog / veloc)
            CEN = [
                f"O backlog de um produto soma {backlog} pontos de história e a "
                f"equipe tem velocidade média de {veloc} pontos por sprint.",
                f"Um projeto possui {backlog} pontos pendentes; o time entrega em "
                f"média {veloc} pontos a cada sprint.",
                f"Restam {backlog} pontos de história no backlog de um produto, "
                f"com velocidade média de {veloc} pontos por sprint.",
            ]
            PER = [
                "Quantas sprints completas serão necessárias para concluir o backlog?",
                "Qual é o número mínimo de sprints para entregar todo o backlog?",
                "Determine quantas sprints são necessárias para finalizar o trabalho.",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Dividindo o backlog pela velocidade: {backlog}/{veloc} = "
                f"{backlog/veloc:.2f}. Como sprints são unidades inteiras, "
                f"arredonda-se para cima, resultando em {correta} sprints."
            )
            distratores = [correta - 1, correta + 1, backlog // veloc if backlog % veloc == 0 else correta + 2,
                           veloc, correta * 2]
            fmt = _fmt

        else:
            devs = rng.randint(3, 8)
            horas_dia = rng.choice([6, 8])
            dias = rng.randint(10, 30)
            correta = devs * horas_dia * dias
            CEN = [
                f"Uma equipe de {devs} desenvolvedores trabalha {horas_dia} horas "
                f"por dia durante {dias} dias úteis em um projeto.",
                f"Um projeto aloca {devs} pessoas por {dias} dias úteis, com "
                f"jornada de {horas_dia} horas diárias.",
                f"Durante {dias} dias úteis, {devs} profissionais dedicam "
                f"{horas_dia} horas diárias a um desenvolvimento.",
            ]
            PER = [
                "Qual é o esforço total do projeto, em homens-hora?",
                "O esforço total estimado, em homens-hora, é de:",
                "Determine o esforço total em homens-hora.",
            ]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"O esforço em homens-hora multiplica pessoas, jornada e dias: "
                f"{devs} × {horas_dia} × {dias} = {correta} homens-hora."
            )
            distratores = [devs * dias, horas_dia * dias, devs * horas_dia,
                           correta // 2, correta * 2]
            fmt = _fmt

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Engenharia de software (gestão)", rng, formatador=fmt)
        if q:
            return q
    raise RuntimeError("metricas_projeto")


# ══════════════════════════════════════════
#  CIÊNCIA DA COMPUTAÇÃO
# ══════════════════════════════════════════

def gerar_recorrencia(rng):
    """Teorema Mestre — resolvido pela regra formal, caso a caso."""
    CASOS = [
        (2, 2, 0, "O(n log n)", "a = 2, b = 2 e f(n) = O(n). Como n^(log_b a) = n^1 = n "
                                "coincide com f(n), aplica-se o caso 2 do Teorema Mestre"),
        (2, 2, 1, "O(n log n)", "a = 2, b = 2 e f(n) = O(n). Como n^(log_b a) = n e f(n) = n "
                                "têm a mesma ordem, aplica-se o caso 2"),
        (1, 2, 0, "O(log n)",   "a = 1, b = 2 e f(n) = O(1). Como n^(log_2 1) = n^0 = 1 "
                                "coincide com f(n), aplica-se o caso 2"),
        (4, 2, 1, "O(n^2)",     "a = 4, b = 2 e f(n) = O(n). Como n^(log_2 4) = n^2 domina "
                                "f(n) = n, aplica-se o caso 1"),
        (3, 4, 1, "O(n)",       "a = 3, b = 4 e f(n) = O(n). Como f(n) = n domina "
                                "n^(log_4 3) ≈ n^0,79, aplica-se o caso 3"),
        (8, 2, 2, "O(n^3)",     "a = 8, b = 2 e f(n) = O(n²). Como n^(log_2 8) = n³ domina "
                                "f(n), aplica-se o caso 1"),
    ]
    TODAS = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(2^n)"]

    for _ in range(60):
        a, b, exp_f, correta, just = rng.choice(CASOS)
        fn_txt = "1" if exp_f == 0 else ("n" if exp_f == 1 else f"n^{exp_f}")
        rec = f"T(n) = {a}·T(n/{b}) + O({fn_txt})"

        CEN = [
            f"A análise de um algoritmo de divisão e conquista levou à recorrência "
            f"{rec}, com T(1) = O(1).",
            f"Um algoritmo recursivo tem seu tempo descrito por {rec}.",
            f"Durante o estudo de complexidade, obteve-se a relação de recorrência "
            f"{rec}.",
            f"O custo de um procedimento recursivo satisfaz {rec}, para n > 1.",
        ]
        PER = [
            "Aplicando o Teorema Mestre, qual é a solução assintótica de T(n)?",
            "Qual é a complexidade assintótica resultante?",
            "Pelo Teorema Mestre, T(n) pertence a qual classe?",
            "A solução dessa recorrência é:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        explicacao = f"Na recorrência, {just}. Logo, T(n) = {correta}."
        distratores = [o for o in TODAS if o != correta]
        rng.shuffle(distratores)

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Análise de algoritmos (recorrências)", rng, formatador=str,
                    tipo_resposta="simbolica")
        if q:
            return q
    raise RuntimeError("recorrencia")


def gerar_hash_colisao(rng):
    """Tabela hash: posição por divisão e tratamento de colisão — simulado."""
    for _ in range(60):
        m = rng.choice([7, 11, 13, 17])
        chaves = rng.sample(range(20, 200), rng.randint(5, 8))
        modo = rng.choice(["posicao", "colisoes", "sondagem"])

        if modo == "posicao":
            chave = rng.choice(chaves)
            correta = chave % m
            CEN = [
                f"Uma tabela hash de {m} posições (índices 0 a {m-1}) utiliza a "
                f"função de dispersão h(k) = k mod {m}.",
                f"Em uma tabela hash com {m} entradas, adota-se h(k) = k mod {m} "
                f"como função de espalhamento.",
                f"Um dicionário implementado com hashing usa h(k) = k mod {m} em "
                f"uma tabela de {m} posições.",
            ]
            PER = [f"Em qual índice a chave {chave} será armazenada, supondo a "
                   f"tabela vazia?",
                   f"Qual é o índice inicial calculado para a chave {chave}?",
                   f"A chave {chave} é mapeada para qual posição?"]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (f"Aplicando a função de dispersão: h({chave}) = {chave} "
                          f"mod {m} = {correta}.")
            distratores = [(chave % m + 1) % m, (chave % m - 1) % m, chave % (m + 1),
                           chave // m, m - 1]

        elif modo == "colisoes":
            posicoes = [k % m for k in chaves]
            correta = len(posicoes) - len(set(posicoes))
            lista = ", ".join(map(str, chaves))
            CEN = [
                f"As chaves {lista} são inseridas, nesta ordem, em uma tabela hash "
                f"de {m} posições com h(k) = k mod {m}.",
                f"Um conjunto de chaves ({lista}) é mapeado por h(k) = k mod {m} em "
                f"uma tabela de {m} entradas.",
            ]
            PER = ["Quantas colisões ocorrem durante as inserções?",
                   "Qual é o número total de colisões observadas?",
                   "Determine quantas colisões acontecem."]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Calculando h(k) para cada chave e contando quantas caem em "
                f"índices já ocupados, o total de colisões é {correta}."
            )
            distratores = [correta + 1, correta + 2, len(chaves),
                           len(set(posicoes)), max(correta - 1, 0)]

        else:
            base = rng.randint(20, 150)
            ocupadas = rng.randint(1, 3)
            inicial = base % m
            correta = (inicial + ocupadas) % m
            CEN = [
                f"Uma tabela hash de {m} posições usa h(k) = k mod {m} e sondagem "
                f"linear para resolver colisões. A chave {base} colide, e as "
                f"{ocupadas} posição(ões) seguinte(s) também estão ocupadas.",
                f"Em uma tabela hash de {m} entradas com h(k) = k mod {m} e "
                f"endereçamento aberto por sondagem linear, a chave {base} encontra "
                f"sua posição inicial e as {ocupadas} seguinte(s) ocupadas.",
            ]
            PER = ["Em qual índice a chave será finalmente inserida?",
                   "Qual posição receberá a chave?",
                   "Determine o índice final de inserção."]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"A posição inicial é h({base}) = {inicial}. Com sondagem linear, "
                f"avança-se {ocupadas} posição(ões) módulo {m}, chegando ao "
                f"índice {correta}."
            )
            distratores = [inicial, (correta + 1) % m, (inicial + ocupadas + 1) % m,
                           (inicial - 1) % m, m - 1]

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Estruturas de dados (hashing)", rng)
        if q:
            return q
    raise RuntimeError("hash_colisao")


def gerar_automato(rng):
    """Autômato finito: simula a leitura da cadeia e diz se aceita."""
    for _ in range(60):
        modo = rng.choice(["paridade", "termina", "contagem"])

        tam = rng.randint(6, 10)
        cadeia = "".join(rng.choice("01") for _ in range(tam))

        if modo == "paridade":
            zeros = cadeia.count("0")
            aceita = zeros % 2 == 0
            correta = "Aceita" if aceita else "Rejeita"
            desc = "aceita cadeias com uma quantidade PAR de símbolos 0"
            explicacao = (
                f"A cadeia possui {zeros} ocorrência(s) do símbolo 0. "
                f"Como {zeros} é {'par' if aceita else 'ímpar'}, o autômato "
                f"{'aceita' if aceita else 'rejeita'} a cadeia."
            )
        elif modo == "termina":
            aceita = cadeia.endswith("01")
            correta = "Aceita" if aceita else "Rejeita"
            desc = "aceita cadeias que terminam com a subcadeia 01"
            explicacao = (
                f"Os dois últimos símbolos da cadeia são '{cadeia[-2:]}'. "
                f"Como {'coincidem' if aceita else 'não coincidem'} com 01, "
                f"o autômato {'aceita' if aceita else 'rejeita'} a entrada."
            )
        else:
            uns = cadeia.count("1")
            aceita = uns >= 3
            correta = "Aceita" if aceita else "Rejeita"
            desc = "aceita cadeias com pelo menos três símbolos 1"
            explicacao = (
                f"A cadeia contém {uns} símbolo(s) 1. Como esse total "
                f"{'atinge' if aceita else 'não atinge'} o mínimo de três, "
                f"o autômato {'aceita' if aceita else 'rejeita'} a cadeia."
            )

        CEN = [
            f"Um autômato finito determinístico sobre o alfabeto {{0, 1}} {desc}.",
            f"Considere um AFD definido sobre {{0, 1}} que {desc}.",
            f"Uma máquina de estados finitos sobre o alfabeto binário {desc}.",
        ]
        PER = [f"Qual é o resultado do processamento da cadeia {cadeia}?",
               f"Ao processar a entrada {cadeia}, o autômato:",
               f"Submetendo a cadeia {cadeia} a esse autômato, o resultado é:"]
        enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"

        distratores = ["Rejeita" if aceita else "Aceita",
                       "Entra em laço infinito",
                       "A cadeia não pertence ao alfabeto",
                       "O autômato é não determinístico para essa entrada"]

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Teoria da computação (autômatos)", rng, formatador=str,
                    tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("automato")


def gerar_memoria_cache(rng):
    """Hierarquia de memória: taxa de acerto e tempo médio — calculados."""
    for _ in range(60):
        modo = rng.choice(["hit_rate", "tempo_medio", "enderecamento"])

        if modo == "hit_rate":
            total = rng.randrange(1000, 20000, 500)
            faltas = rng.randint(int(total * 0.02), int(total * 0.25))
            acertos = total - faltas
            correta = round(acertos / total * 100, 1)
            CEN = [
                f"Durante a execução de um programa, foram realizados {total} "
                f"acessos à memória cache, dos quais {faltas} resultaram em falta "
                f"(miss).",
                f"Um profiler registrou {total} acessos à cache com {faltas} "
                f"ocorrências de miss.",
                f"A análise de desempenho de um sistema contabilizou {total} "
                f"referências à cache e {faltas} faltas.",
            ]
            PER = ["Qual é a taxa de acerto (hit rate) da cache?",
                   "A taxa de acertos obtida foi de:",
                   "Determine o hit rate da cache."]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Os acertos são {total} − {faltas} = {acertos}. A taxa de acerto "
                f"é {acertos}/{total} × 100 = {correta}%."
            )
            distratores = [round(faltas / total * 100, 1),
                           round(acertos / total * 100 + 5, 1),
                           round(acertos / total * 100 - 5, 1),
                           round(faltas / acertos * 100, 1)]
            fmt = lambda v: f"{v:.1f}%".replace(".", ",")

        elif modo == "tempo_medio":
            t_cache = rng.choice([1, 2, 4])
            t_ram = rng.choice([50, 80, 100, 120])
            hit = rng.choice([90, 92, 95, 98])
            correta = round(t_cache * (hit / 100) + t_ram * (1 - hit / 100), 2)
            CEN = [
                f"Um sistema possui cache com tempo de acesso de {t_cache} ns e "
                f"memória principal com {t_ram} ns. A taxa de acerto da cache é "
                f"de {hit}%.",
                f"Em uma arquitetura, acessar a cache custa {t_cache} ns e a RAM "
                f"custa {t_ram} ns, com hit rate de {hit}%.",
                f"A hierarquia de memória de um processador tem cache de "
                f"{t_cache} ns, memória principal de {t_ram} ns e {hit}% de acertos.",
            ]
            PER = ["Qual é o tempo médio de acesso à memória, em nanossegundos?",
                   "O tempo médio de acesso resulta em:",
                   "Determine o tempo médio de acesso em ns."]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"O tempo médio pondera acertos e faltas: "
                f"{t_cache} × {hit/100} + {t_ram} × {round(1-hit/100, 2)} = "
                f"{correta} ns."
            )
            distratores = [float(t_ram), float(t_cache),
                           round((t_cache + t_ram) / 2, 2),
                           round(t_cache * (1 - hit/100) + t_ram * (hit/100), 2)]
            fmt = lambda v: f"{v:.2f}".replace(".", ",")

        else:
            bits = rng.choice([16, 20, 24, 32])
            correta = 2 ** bits
            CEN = [
                f"Um processador utiliza barramento de endereços com {bits} bits.",
                f"Uma arquitetura define endereços de memória com {bits} bits.",
                f"O espaço de endereçamento de um sistema é definido por {bits} bits.",
            ]
            PER = ["Quantas posições de memória distintas podem ser endereçadas?",
                   "Qual é o número máximo de células endereçáveis?",
                   "Determine a quantidade de endereços possíveis."]
            enunciado = f"{rng.choice(CEN)} {rng.choice(PER)}"
            explicacao = (
                f"Com {bits} bits de endereço, o total de posições distintas é "
                f"2^{bits} = {_fmt(correta)}."
            )
            distratores = [2 ** (bits - 1), 2 ** (bits + 1), bits * 1024,
                           2 ** bits - 1, bits ** 2]
            fmt = _fmt

        tipo = ("percentual" if modo == "hit_rate"
                else "numerica")
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Arquitetura de computadores", rng, formatador=fmt,
                    tipo_resposta=tipo)
        if q:
            return q
    raise RuntimeError("memoria_cache")


# ──────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────

TEMPLATES_ADS = {
    "complexidade_loops":     gerar_complexidade_loops,
    "complexidade_classicos": gerar_complexidade_classicos,
    "contagem_operacoes":     gerar_contagem_operacoes,
    "ordenacao_comparacoes":  gerar_ordenacao_comparacoes,
    "pilha":                  gerar_pilha,
    "fila":                   gerar_fila,
    "arvore_bst":             gerar_arvore_bst,
    "grafos":                 gerar_grafos,
    "conversao_bases":        gerar_conversao_bases,
    "binario_operacoes":      gerar_binario_operacoes,
    "logica_proposicional":   gerar_logica_proposicional,
    "conjuntos":              gerar_conjuntos,
    "sql_resultado":          gerar_sql_resultado,
    "sql_join":               gerar_sql_join,
    "redes_subrede":          gerar_redes_subrede,
    "escalonamento":          gerar_escalonamento,
    # ── Engenharia de software ──
    "pontos_funcao":          gerar_pontos_funcao,
    "cobertura_testes":       gerar_cobertura_testes,
    "metricas_projeto":       gerar_metricas_projeto,
    # ── Ciência da computação ──
    "recorrencia":            gerar_recorrencia,
    "hash_colisao":           gerar_hash_colisao,
    "automato":               gerar_automato,
    "memoria_cache":          gerar_memoria_cache,
}

TOPICOS_ADS = {
    "algoritmos":       ["complexidade_loops", "complexidade_classicos",
                         "contagem_operacoes", "ordenacao_comparacoes"],
    "estruturas_dados": ["pilha", "fila", "arvore_bst", "grafos"],
    "matematica_disc":  ["conversao_bases", "binario_operacoes",
                         "logica_proposicional", "conjuntos"],
    "banco_dados":      ["sql_resultado", "sql_join"],
    "redes":            ["redes_subrede"],
    "sistemas_op":      ["escalonamento", "memoria_cache"],
    "eng_software":     ["pontos_funcao", "cobertura_testes", "metricas_projeto"],
    "teoria_computacao": ["recorrencia", "automato"],
    "arquitetura":      ["memoria_cache"],
}

# Palavras-chave para casar tópicos de LIVROS indexados com templates.
PALAVRAS_CHAVE = {
    "complexidade_loops":     ["complexidade", "assintotic", "big-o", "big o",
                               "analise de algoritmo", "notacao o"],
    "complexidade_classicos": ["complexidade", "busca binaria", "merge sort",
                               "quick sort", "heap", "hash", "algoritmo"],
    "contagem_operacoes":     ["analise de algoritmo", "custo de algoritmo",
                               "laco aninhado", "estrutura de repeticao",
                               "loop", "iteracao", "contagem de operacoes"],
    "ordenacao_comparacoes":  ["ordenacao", "sort", "bubble", "insertion",
                               "selection", "classificacao"],
    "pilha":                  ["pilha", "stack", "lifo", "estrutura de dados"],
    "fila":                   ["fila", "queue", "fifo", "estrutura de dados"],
    "arvore_bst":             ["arvore", "binaria", "bst", "percurso",
                               "pre-ordem", "in-ordem", "heap"],
    "grafos":                 ["grafo", "vertice", "aresta", "dijkstra",
                               "arvore geradora", "caminho minimo"],
    "conversao_bases":        ["base", "binario", "hexadecimal", "octal",
                               "numeracao", "conversao"],
    "binario_operacoes":      ["binario", "complemento", "aritmetica",
                               "ponto flutuante", "bit", "representacao"],
    "logica_proposicional":   ["logica", "proposicional", "tabela-verdade",
                               "tabela verdade", "booleana", "predicado"],
    "conjuntos":              ["conjunto", "inclusao", "exclusao", "relacao",
                               "matematica discreta"],
    "sql_resultado":          ["sql", "consulta", "query", "select",
                               "banco de dados", "relacional"],
    "sql_join":               ["join", "sql", "relacionamento", "chave estrangeira",
                               "banco de dados", "algebra relacional"],
    "redes_subrede":          ["rede", "ip", "sub-rede", "subrede", "cidr",
                               "mascara", "tcp", "roteamento", "endereçamento"],
    "escalonamento":          ["escalonamento", "processo", "sistema operacional",
                               "cpu", "thread", "concorrencia", "deadlock"],
    "pontos_funcao":          ["ponto de funcao", "pontos de funcao", "metrica",
                               "estimativa", "engenharia de software", "ifpug",
                               "analise de pontos"],
    "cobertura_testes":       ["teste", "cobertura", "qualidade de software",
                               "complexidade ciclomatica", "mccabe", "verificacao",
                               "validacao", "engenharia de software"],
    "metricas_projeto":       ["gerencia de projeto", "gestao de projeto", "agil",
                               "scrum", "sprint", "backlog", "velocidade",
                               "esforco", "cronograma"],
    "recorrencia":            ["recorrencia", "teorema mestre", "divisao e conquista",
                               "recursao", "analise de algoritmo", "complexidade"],
    "hash_colisao":           ["hash", "hashing", "tabela hash", "dispersao",
                               "colisao", "sondagem", "estrutura de dados"],
    "automato":               ["automato", "linguagem formal", "teoria da computacao",
                               "maquina de estados", "afd", "afn", "gramatica",
                               "expressao regular"],
    "memoria_cache":          ["cache", "memoria", "arquitetura de computadores",
                               "hierarquia de memoria", "enderecamento",
                               "barramento", "organizacao de computadores"],
}


# Chaves que aparecem em MAIS DE UMA área e, sozinhas, não identificam o
# assunto. "contagem" existe em combinatória, em algoritmos e em prazo
# processual; "arvore" em estrutura de dados e em diagrama de probabilidade.
CHAVES_GENERICAS = {
    # "base" sozinha aciona conversao_bases, mas aparece em contextos de
    # outras áreas: "base do crânio" (anatomia), "base de dados",
    # "base legal". Só "base numérica", "base binária" e afins são
    # específicas — e essas continuam listadas nas palavras-chave.
    "base", "bases",
    "contagem", "arvore", "grafo", "conjuntos", "logica", "operacoes",
    "ordenacao", "busca", "sequencia", "modelo", "processo", "analise",
    # Colidem com saúde e administração — um Caderno do Ministério da
    # Saúde casava com sub-rede por causa de "rede de atenção à saúde",
    # e com ordenação por causa de "classificação de risco".
    # Ambíguas de verdade — existem em saúde, administração, direito:
    "rede", "redes", "classificacao", "fluxo", "fluxograma", "protocolo",
    "porta", "camada", "acesso", "servico", "servicos", "gestao",
    "organizacao", "estrutura", "processo", "modelo",
    # "mascara", "host" e "endereco" ficaram FORA desta lista: em contexto
    # de computação são inequívocos, e tratá-los como ambíguos fazia um
    # livro de redes deixar de casar com o template de sub-rede.
    # Colidem com combinatória e probabilidade:
    "repeticao", "permutacao", "combinacao", "arranjo", "probabilidade",
    "evento", "espaco", "fatorial", "binomio", "pascal",
    # Colidem com outras áreas:
    "laco", "loop", "iteracao", "complexidade", "custo", "tabela",
}


def _normalizar(txt: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def templates_para_topicos(topicos: list) -> list:
    """
    Casa os tópicos de um livro indexado com os templates deste gerador.

    A comparação é por PALAVRA INTEIRA, não por substring: "ip" não pode
    casar dentro de "princípio", nem "or" dentro de "ordenação". Antes
    dessa correção, um livro de combinatória acionava geradores de rede
    porque "Princípio" contém "ip".

    Além disso, chaves de UMA palavra genérica (como "contagem", que
    aparece em combinatória, em análise de algoritmos e em prazo
    processual) só valem quando acompanhadas de outra chave do mesmo
    template — sozinhas, geram falso casamento.
    """
    texto = " " + " ".join(_normalizar(str(t)) for t in topicos) + " "

    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        especificas = 0
        genericas   = 0
        for chave in chaves:
            cn = _normalizar(chave)
            if not cn:
                continue
            # \b não funciona bem com acentos removidos + espaços; usamos
            # delimitadores explícitos de palavra.
            padrao = r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])'
            if re.search(padrao, texto):
                if cn in CHAVES_GENERICAS:
                    genericas += 1
                else:
                    especificas += 1

        # Uma chave específica basta; genéricas NÃO acionam sozinhas,
        # por mais que se acumulem. A regra anterior aceitava duas
        # genéricas, e um Caderno do Ministério da Saúde acionava o
        # gerador de portas por conter "porta de entrada do SUS" e
        # "protocolo de acolhimento" — nenhuma das duas sobre redes.
        #
        # O custo é perder algum casamento legítimo em livro de
        # vocabulário pobre; o benefício é nunca gerar questão de outra
        # área, que é o erro visível para o usuário.
        if especificas >= 1:
            achados.append(nome)

    return achados

def gerar_lote(quantidade=16, topico=None, templates=None, seed=None):
    """
    Gera questões de ADS.
      topico    → filtra por área (algoritmos, banco_dados, redes...)
      templates → lista explícita de nomes (usado pelo pipeline do livro)
    """
    rng = random.Random(seed)

    if templates:
        nomes = [n for n in templates if n in TEMPLATES_ADS]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
    elif topico:
        nomes = TOPICOS_ADS.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS_ADS)}")
    else:
        nomes = list(TEMPLATES_ADS)

    funcoes = [TEMPLATES_ADS[n] for n in nomes]
    rng.shuffle(funcoes)

    questoes = []
    # O laço anterior aceitava a PRIMEIRA questão de cada template, sem
    # filtro. Num simulado de 30, isso rendia sete questões "quantos
    # hosts nessa sub-rede", três delas com o MESMO prefixo /27 e a
    # mesma resposta.
    #
    # O veto atua em três níveis:
    #   enunciado  — nunca repete texto idêntico
    #   fato       — o par (template, resposta) não se repete
    #   tópico     — no máximo dois do mesmo assunto por lote
    #
    # Cada nível afrouxa perto do limite de tentativas, para não
    # devolver lote incompleto quando o material acaba.
    from collections import Counter
    vistos, fatos_usados = set(), set()
    topicos = Counter()
    # Teto por TEMPLATE: dividir a cota pelo número de templates
    # distribui de verdade, enquanto o teto por tópico agrupava
    # assuntos distintos sob o mesmo rótulo.
    import math
    TETO_TOPICO = math.ceil(quantidade / max(1, len(funcoes))) + 1
    tentativas, limite = 0, quantidade * 15

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        fn = funcoes[tentativas % len(funcoes)]
        try:
            q = fn(rng)
        except Exception:
            continue
        if not q:
            continue

        if q["enunciado"] in vistos and tentativas < limite * 0.9:
            continue

        # O "fato" combina o tipo de pergunta com a resposta: duas
        # questões de /27 pedindo hosts têm o mesmo fato, ainda que o
        # endereço mudе.
        fato = f"{fn.__name__}:{q['alternativas'][q['gabarito']]}"
        if fato in fatos_usados and tentativas < limite * 0.85:
            continue

        # Conta pelo TEMPLATE, não pelo tópico: tópicos agrupam
        # assuntos distintos e deixam a repetição passar.
        if topicos[fn.__name__] >= TETO_TOPICO and tentativas < limite * 0.75:
            continue

        vistos.add(q["enunciado"])
        fatos_usados.add(fato)
        topicos[fn.__name__] += 1
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade=10, topico=None, templates=None, seed=None):
    """
    Formato compatível com salvar_questoes_banco.

    IMPORTANTE: monta o payload campo a campo, de propósito. Os metadados
    internos (tipo_resposta, resposta_bruta) NÃO são incluídos — eles
    servem apenas aos testes automatizados e não devem chegar ao app.
    """
    lote = gerar_lote(quantidade, topico, templates, seed)
    questoes_limpas, gabarito_final = [], []
    for q in lote:
        questoes_limpas.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": False,
        })
        gabarito_final.append({
            "numero":           q["numero"],
            "resposta_correta": q["gabarito"],
            "explicacao":       q["explicacao"],
            # O TÓPICO vai junto. O montador de simulado usa-o para
            # limitar quantas questões do mesmo assunto entram no
            # caderno, e sem ele essa trava ficava sempre inerte — um
            # simulado de direito saía com doze perguntas de prazo
            # trabalhista, onze delas com a mesma resposta.
            #
            # Serve também ao aplicativo, que pode relatar o desempenho
            # por assunto sem precisar reabrir o gerador.
            "topico":           q.get("topico", ""),
            # O FATO — par template+resposta — vai junto pelo mesmo
            # motivo do tópico. O veto interno de cada gerador vale
            # dentro de uma chamada; o simulado faz várias, e sem esta
            # chave o mesmo fato voltava com outra redação: "recurso de
            # revista: 8 dias" apareceu três vezes no mesmo caderno.
            #
            # O montador remove o campo antes de devolver, para não
            # sujar o que é gravado no banco.
            "_fato":            q.get("_fato", ""),
        })
    return questoes_limpas, gabarito_final


if __name__ == "__main__":
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    topico = sys.argv[2] if len(sys.argv) > 2 else None
    for q in gerar_lote(qtd, topico):
        print("─" * 66)
        print(f"Q{q['numero']} [{q['topico']}]\n")
        print(q["enunciado"], "\n")
        for L, t in q["alternativas"].items():
            print(f"   {L}) {t}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("─" * 66)
    print(f"\n{qtd} questões ADS | Custo: R$ 0,00 | Gabaritos calculados.\n")
