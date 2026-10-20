"""
=============================================================
  TESTE 2 — COERÊNCIA / SENTIDO DA FRASE
=============================================================
  Verifica se o enunciado FAZ SENTIDO como texto, não só se
  está gramaticalmente correto.

  O risco principal da montagem por partes é a CONTAMINAÇÃO:
  sortear o contexto "linha de produção" e a pergunta
  "quantos meninos" — cada peça correta, a junção absurda.

  CHECAGENS:
    1. Contaminação léxica — mistura de campos semânticos
       incompatíveis no mesmo enunciado
    2. Referência órfã — pronome ou "esses N" sem antecedente
    3. Coerência numérica — números da pergunta existem no contexto
    4. Pergunta presente — o enunciado realmente pergunta algo
    5. Contexto presente — não é só uma pergunta solta
    6. Continuidade — não há emenda quebrada entre as partes

  USO: python teste_2_coerencia.py [quantidade]
=============================================================
"""
import sys, re
from collections import defaultdict

sys.path.insert(0, ".")


# ── 1) CAMPOS SEMÂNTICOS MUTUAMENTE EXCLUSIVOS ──
# Cada grupo reúne palavras de um mesmo cenário. Se um enunciado
# contém palavras de DOIS grupos do mesmo conjunto, houve contaminação.
CAMPOS_EXCLUSIVOS = [
    # binomial: cenários que não podem se misturar
    {
        "moeda":     {"moeda", "caras", "coroas"},
        "dado_par":  {"resultados pares", "resultado par"},
        "testes":    {"verificações", "verificação"},
        "pesquisa":  {"entrevista", "entrevistados", "favorável", "favoráveis"},
        "familia":   {"filhos", "meninos", "menino"},
        "producao":  {"peças", "peça aprovada", "linha de produção"},
    },
    # urna / probabilidade: objetos não se misturam
    {
        "bolas":    {"bolas", "bolinhas"},
        "fichas":   {"fichas"},
        "cartoes":  {"cartões"},
    },
    # contagem: contextos de pódio
    {
        "corrida":  {"100 metros", "corrida"},
        "xadrez":   {"xadrez"},
        "natacao":  {"natação"},
        "esports":  {"e-sports"},
    },
    # estruturas de dados: pilha vs fila
    {
        "pilha": {"empilha", "desempilha", "lifo", "topo da pilha"},
        "fila":  {"insere(", "remove(", "fifo", "frente da fila"},
    },
    # banco de dados: tabelas diferentes
    {
        "funcionarios": {"funcionarios", "salario", "departamento"},
        "pedidos":      {"clientes", "pedidos", "cliente_id"},
    },
]


def checar_contaminacao(texto: str) -> list:
    t = texto.lower()
    achados = []
    for conjunto in CAMPOS_EXCLUSIVOS:
        presentes = []
        for nome, palavras in conjunto.items():
            if any(p in t for p in palavras):
                presentes.append(nome)
        if len(presentes) > 1:
            achados.append(("contaminacao_lexica",
                            f"mistura de cenários: {' + '.join(presentes)}"))
    return achados


# ── 2) REFERÊNCIA ÓRFÃ ──
def checar_referencia(texto: str) -> list:
    achados = []
    t = texto.lower()
    # "deles/delas" precisa de um plural antes
    for m in re.finditer(r'\b(deles|delas|esses|essas|esse grupo)\b', t):
        antes = t[:m.start()]
        # antecedente pode ser "N palavras" OU um plural qualquer
        # ("todos os anagramas ... em quantos deles")
        if not re.search(r'\b\d+\s+\w+(?:s|es|ns|ões)\b', antes) and \
           not re.search(r'\b\w+(?:s|es|ões)\b\s', antes):
            achados.append(("referencia_orfa",
                            f"'{m.group(1)}' sem antecedente plural claro"))
            break
    # "essa/esse" logo no início não tem a que se referir
    if re.match(r'^\s*(?:nessa|nesse|dessa|desse|essa|esse)\b', t):
        achados.append(("referencia_inicial", "enunciado começa com referência"))
    return achados


# ── 3) COERÊNCIA NUMÉRICA ──
def checar_numeros(texto: str, tipo_resposta: str = "numerica") -> list:
    """
    Detecta número que aparece SÓ na pergunta final sem relação com o
    contexto — sintoma de junção errada entre partes sorteadas.

    Usa o METADADO da questão: se a resposta é um código numérico
    (binário, hex) ou textual, os "números" do enunciado costumam ser
    cadeias de símbolos, não quantidades — e a checagem não se aplica.
    """
    achados = []

    # Tipos cuja questão gira em torno de símbolos, não de quantidades
    if tipo_resposta in ("codigo_numerico", "textual", "endereco_ip"):
        return achados

    # Normas técnicas citadas (RFC 5952, ISO 27001) são identificadores, não
    # quantidades — mascarar ANTES de qualquer divisão em frases.
    texto = re.sub(r'\b(?:RFC|ISO|IEC|NBR|ITU)[\s-]*\d+', "NORMA", texto)

    # Remove blocos estruturados (tabela, código, SQL): números ali são dados
    prosa = "\n".join(
        l for l in texto.split("\n")
        if not re.match(r'^\s{2,}', l)
        and not re.search(r'\||SELECT|FROM|WHERE|GROUP BY|JOIN|→|range\(|ms\s*$', l)
    )

    partes = re.split(r'(?<=[.:])\s+(?=[A-ZÀ-Ý])', prosa)
    if len(partes) < 2:
        return achados
    contexto, pergunta = " ".join(partes[:-1]), partes[-1]

    nums_ctx = [int(x) for x in re.findall(r'\d+', contexto)]
    if not nums_ctx:
        return achados

    pergunta_limpa = re.sub(r'\^\s*\d+', "", pergunta)   # tira expoentes
    # Bases de cálculo padronizadas (por 1.000 / 100.000 habitantes em
    # epidemiologia) são convenção da métrica, não referência ao contexto.
    pergunta_limpa = re.sub(r'por\s+[\d.]+\s*(?:habitantes|pessoas|mil)',
                            "por BASE", pergunta_limpa)
    pergunta_limpa = re.sub(r'pontos percentuais', "", pergunta_limpa)
    nums_perg = {int(x) for x in re.findall(r'\d+', pergunta_limpa)}

    # Número que a própria pergunta introduz como dado ou meta
    alvo = bool(re.search(
        r'(?:ser|igual a|exatamente|vale|soma de|maior que|acima de|'
        r'tem|possui|conta com|totaliza|de|com|chave|entrada)\s+\d+',
        pergunta_limpa))

    # ÍNDICE DE POSIÇÃO em sequências: "o termo de ordem 8", "o 12º
    # termo", "a posição 20". O número é a própria incógnita da
    # pergunta, e exigi-lo no contexto não faz sentido — não há como
    # anunciar de antemão qual termo será pedido.
    if re.search(r'(?:ordem|posição|posicao)\s+\d+|\b\d+\s*[ºo°]\s+termo',
                 pergunta_limpa, re.I):
        alvo = True

    derivados = {sum(nums_ctx), max(nums_ctx), min(nums_ctx)}
    orfaos = {n for n in nums_perg - set(nums_ctx)
              if n > 5 and not alvo and n not in derivados}

    if orfaos:
        achados.append(("numero_orfao",
                        f"números só na pergunta: {sorted(orfaos)}"))
    return achados


# ── 4/5) ESTRUTURA MÍNIMA DE UMA QUESTÃO ──
def checar_estrutura_textual(texto: str) -> list:
    achados = []
    t = texto.strip()

    # Aceita também o formato "…é igual a:" (completar), comum em provas.
    tem_pergunta = bool(re.search(
        r'\?|[Dd]etermine|[Cc]alcule|[Aa]ssinale|[Ii]ndique|[Qq]uantas|[Qq]uantos|'
        r'[Qq]ual|[Dd]e quantos|[Ee]m quantas|:\s*$|é igual a|é:\s*$', t))
    if not tem_pergunta:
        achados.append(("sem_pergunta", "não há pergunta no enunciado"))

    # deve haver contexto antes da pergunta (não começa direto com "Qual...?")
    # Questões diretas ("Quantos anagramas possui a palavra X?") são
    # legítimas e curtas. Só acusa se for curto DEMAIS para fazer sentido.
    if len(t) < 35:
        achados.append(("sem_contexto", f"enunciado muito curto ({len(t)} car.)"))

    # emenda quebrada: minúscula logo após ponto final
    if re.search(r'\.\s+[a-zà-ÿ]', t):
        achados.append(("emenda_quebrada", "minúscula após ponto final"))

    # dupla pergunta (duas interrogações = provável junção errada)
    if t.count("?") > 1:
        achados.append(("duas_perguntas", "mais de uma interrogação"))

    # frase iniciada por conjunção solta
    if re.match(r'^\s*(?:e|ou|mas|porém|que|se)\b', t.lower()):
        achados.append(("inicio_conjuncao", "começa com conjunção solta"))

    return achados


def verificar(questoes):
    problemas = defaultdict(list)
    for q in questoes:
        e = q["enunciado"]
        tipo = q.get("tipo_resposta", "numerica")
        for regra, det in (checar_contaminacao(e) + checar_referencia(e) +
                           checar_numeros(e, tipo) + checar_estrutura_textual(e)):
            problemas[regra].append((q["topico"], det, e[:110]))
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    import gerador_ads, gerador_procedural

    print("═" * 62)
    print("  TESTE 2 — COERÊNCIA / SENTIDO DA FRASE")
    print("═" * 62)

    total = 0
    for nome, mod in [("ADS", gerador_ads), ("Matemática", gerador_procedural)]:
        lote = mod.gerar_lote(qtd, seed=8080)
        probs = verificar(lote)
        n = sum(len(v) for v in probs.values())
        total += n
        print(f"\n  ── {nome}: {qtd} questões ──")
        if not n:
            print("     ✅ Nenhum problema de coerência")
        else:
            for regra, casos in sorted(probs.items(), key=lambda x: -len(x[1])):
                print(f"     ❌ {regra} ({len(casos)}x)")
                vistos = set()
                for topico, det, trecho in casos:
                    if topico in vistos: continue
                    vistos.add(topico)
                    print(f"          [{topico}] {det}")
                    print(f"            {trecho}...")
                    if len(vistos) >= 2: break

    print("\n" + "═" * 62)
    print(f"  {'🎉 TESTE 2 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 62)
    sys.exit(1 if total else 0)
