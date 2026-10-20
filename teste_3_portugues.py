"""
=============================================================
  TESTE 3 — PORTUGUÊS (concordância, contrações, pontuação)
=============================================================

  Confere DUAS dimensões, independentes do gabarito:

  A) LÍNGUA  — concordância, contrações, pontuação, duplicações
  B) FORMA   — estrutura da questão, alternativas, explicação

  Não substitui a validar_questao (que cuida da matemática);
  este arquivo cuida do TEXTO, que a validação não olha.

  USO:
    python teste_3_portugues.py            # 2000 questões
    python teste_3_portugues.py 5000
=============================================================
"""

import re
import sys
from collections import defaultdict


# ──────────────────────────────────────────
#  A) CHECAGENS DE LÍNGUA
# ──────────────────────────────────────────

# Cada regra: (nome, regex, explicação do erro)
# As regexes são propositalmente conservadoras — é melhor deixar passar
# um erro raro do que acusar falso positivo em texto correto.

REGRAS_LINGUA = [
    # ── Contrações não feitas ──
    # Cuidado: "de a" é CORRETO antes de oração infinitiva
    # ("a probabilidade de a soma ser 7"). Só acusa quando o que vem
    # depois é claramente um substantivo comum do nosso domínio.
    ("contração_de",
     r'\bde\s+(?:o|a|os|as)\s+(?:urna|caixa|vetor|tabela|pilha|fila|arvore|'
     r'árvore|lista|grafo|processo|livro|aluno|professor|sistema|banco)\b',
     "'de o/a' deveria ser 'do/da'"),
    ("contração_em",
     r'\bem\s+(?:o|a|os|as)\s+(?:urna|caixa|vetor|tabela|pilha|fila|arvore|'
     r'árvore|lista|grafo|processo|livro|estante|prateleira)\b',
     "'em o/a' deveria ser 'no/na'"),

    # ── Concordância com numeral 1 (ERRO REAL encontrado) ──
    # Não acusa quando o "1" faz parte de expressão matemática ("v−1 arestas",
    # "n-1 vértices"), apenas quando é contagem real ("restam 1 elementos").
    ("numeral_1_substantivo_plural",
     r'(?<![-−–\d])\b1\s+(?:resultados|caras|coroas|peças|filhos|meninos|meninas|'
     r'pessoas|itens|elementos|verificações|entrevistas|aprovações|sequências|'
     r'bolas|fichas|cartões|livros|nós|folhas|arestas|vértices)\b',
     "numeral 1 com substantivo no plural"),
    ("numeral_1_verbo_plural",
     r'\b1\s+(?:\w+\s+){0,2}(?:serem|forem|estarem|ficarem|passarem|saírem|'
     r'aparecerem|ocorrerem)\b',
     "numeral 1 com verbo no plural"),
    ("exatamente_1_plural",
     r'exatamente\s+1\s+(?:deles|delas)\s+\w+(?:em|ram)\b',
     "'exatamente 1 deles/delas' com verbo no plural"),

    # ── Artigo x substantivo (excluindo "cada um/uma dos/das", correto) ──
    ("artigo_uma_masculino",
     r'(?<!cada )\buma\s+(?:livro|dado|processo|vetor|código|número|conjunto|'
     r'grafo|nó|vértice|algoritmo|sistema|servidor|arquivo)\b',
     "'uma' com substantivo masculino"),
    ("artigo_um_feminino",
     r'(?<!cada )\bum\s+(?:bola|ficha|peça|pilha|fila|árvore|tabela|linha|'
     r'coluna|consulta|máscara|rede|urna|caixa)\b',
     "'um' com substantivo feminino"),

    # ── Duplicação de palavra ──
    # Ignora números e notação matemática (ex: "n n", "2 2")
    ("palavra_duplicada",
     r'\b([a-zA-ZÀ-ÿ]{3,})\s+\1\b',
     "palavra repetida em sequência"),

    # ── Vestígios de template ──
    ("placeholder_nao_substituido",
     r'\{[a-z_]+\}',
     "placeholder {var} não substituído"),
    ("valor_none",
     r'\bNone\b|\bnan\b|\bNaN\b',
     "valor None/nan vazou para o texto"),

    # ── Pontuação (ignorando reticências matemáticas "..., ") ──
    ("pontuacao_triplicada",
     r'(?<!\.)[,;:?!]{2,}',
     "pontuação duplicada"),
    ("espaco_antes_virgula",
     r'\w\s+,(?!\s*\.\.\.)',
     "espaço antes de vírgula"),

    # ── Frase incompleta ──
    ("enunciado_sem_final",
     r'[a-zA-ZÀ-ÿ,;]\s*$',
     "não termina com pontuação final"),

    # ── Flexão de gênero não resolvida ──
    # Pega "quantos(as)", "o(a)", "candidato(a)" — o gerador conhece o
    # gênero do que está contando e deve flexionar, não deixar a escolha
    # para o leitor.
    ("genero_nao_resolvido",
     r'\b\w+\(a\)|\b\w+\(as\)|\b\w+\(os\)|\bo\(a\)\b',
     "flexão de gênero não resolvida no enunciado"),

    # ── Verbo de constatação duplicado ──
    # Pega "verificou-se que observou-se", "notou-se que constatou-se".
    ("verbo_constatacao_duplicado",
     r'\b(?:verificou|observou|notou|constatou|percebeu)-se que\s+'
     r'(?:verificou|observou|notou|constatou|percebeu)-se\b',
     "dois verbos de constatação encadeados"),

    # ── Verbo conjugado depois de preposição que pede infinitivo ──
    # Pega "consiste em baseia-se", "corresponde a organiza".
    ("verbo_apos_preposicao",
     r'\b(?:consiste em|corresponde a|resume-se a|equivale a)\s+'
     r'(?:baseia-se|organiza|descreve|expressa|permite|oculta|representa)\b',
     "verbo conjugado onde caberia infinitivo"),

    # ── Cor/adjetivo com gênero errado após substantivo masculino ──
    # Pega "cartões brancas", "chips vermelhas" — objeto masculino com
    # adjetivo no feminino (efeito de sortear cor e objeto separadamente).
    ("adjetivo_genero_objeto",
     r'\b(?:cartões|chips|livros|dados|processos|vetores|nós|arquivos)\s+'
     r'(?:brancas|vermelhas|amarelas|pretas|roxas|azuladas)',
     "adjetivo feminino após substantivo masculino"),

    # ── Artigo com gênero errado antes de termo técnico conhecido ──
    # Pega casos como "a Isolamento", "o Atomicidade".
    # Termos em inglês (Sprint Review, Product Backlog) aceitam artigo
    # masculino em português ("o Sprint Review", "o evento"). Só acusa
    # termos PORTUGUESES cujo gênero é inequívoco.
    ("artigo_genero_termo",
     r'\ba\s+(?:Isolamento|Encapsulamento|Polimorfismo)\b|'
     r'\bo\s+(?:Atomicidade|Consistência|Durabilidade|Herança|Abstração)\b',
     "artigo com gênero incorreto antes de termo técnico"),

    # ── Nome próprio com inicial minúscula indevida ──
    # Pega "bubble Sort", "merge Sort" (efeito de .lower() mal aplicado).
    # Regex sensível a maiúsculas: só casa a forma minúscula literal.
    # (as demais regras usam IGNORECASE, esta precisa da forma exata —
    #  por isso o marcador (?-i:...) desabilitando o flag localmente)
    ("nome_proprio_minusculo",
     r'(?-i:\b(?:bubble|merge|quick|heap|insertion|selection)\s+Sort\b)',
     "nome próprio com inicial minúscula"),

    # ── Artigo duplicado ──
    # "aplicado a um vetor" e "aplicada a uma entrada" são corretos
    # (preposição + artigo). Só acusa artigo REAL seguido de artigo.
    ("artigo_duplicado",
     r'\b(?:o|os|as|uma)\s+(?:o|os|as|um|uma)\s+[a-zA-ZÀ-ÿ]',
     "dois artigos seguidos"),
]

# Regras desativadas (None na explicação) não são aplicadas
REGRAS_ATIVAS = [(n, r, e) for n, r, e in REGRAS_LINGUA if e]


def _limpar_para_analise(texto: str) -> str:
    """
    Remove blocos que NÃO são prosa (código, tabelas, notação matemática),
    pois neles espaçamento e pontuação seguem outras regras.
    """
    linhas = []
    for linha in texto.split("\n"):
        s = linha.strip()
        # pula linhas de código, tabela e notação
        if (s.startswith(("for ", "while ", "if ", "SELECT", "INNER", "LEFT",
                          "contador", "soma", "i =", "j =", "|", "-", "  ")) or
            "→" in s or "|" in s or s.count("(") > 2):
            continue
        linhas.append(linha)
    limpo = "\n".join(linhas)
    # neutraliza reticências matemáticas
    limpo = re.sub(r'\.\.\.', "…", limpo)
    return limpo


def _mascarar_tecnico(texto: str) -> str:
    """
    Substitui notações técnicas por marcadores antes da análise linguística.

    Endereços IPv6 (2001:db8::1) e referências como "art. 206, § 3º" contêm
    sequências de pontuação que as regras de português interpretariam como
    erro — "::" vira "pontuação triplicada", por exemplo. Mascarar preserva
    a checagem da PROSA sem falso positivo na notação.
    """
    t = texto
    # Cobre todas as formas: 2001:db8::1, ff02::1, ::1, fe80::, e a
    # forma completa com 8 grupos.
    t = re.sub(r'(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}', "ENDERECO_IPV6", t)
    t = re.sub(r'\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?', "ENDERECO_IPV4", t)
    # A máscara do artigo NÃO pode engolir a pontuação final da frase:
    # "conforme o art. 1.003, § 5º." deve virar "conforme o ARTIGO." e não
    # "conforme o ARTIGO" — senão a frase parece truncada.
    t = re.sub(r'art\.\s*[\d.]+(?=[\s,;.)])', "ARTIGO", t)
    t = re.sub(r'§\s*\d+º?', "PARAGRAFO", t)
    return t


def checar_lingua(texto: str) -> list:
    """Retorna lista de (regra, trecho_problemático, explicação)."""
    texto = _mascarar_tecnico(texto)
    texto = _limpar_para_analise(texto)
    achados = []
    for nome, regex, expl in REGRAS_ATIVAS:
        for m in re.finditer(regex, texto, re.IGNORECASE):
            trecho = texto[max(0, m.start()-25):m.end()+25].replace("\n", " ")
            achados.append((nome, trecho.strip(), expl))
    return achados


# ──────────────────────────────────────────
#  B) CHECAGENS DE FORMA
# ──────────────────────────────────────────

def checar_forma(q: dict) -> list:
    """
    Confere a estrutura da questão (independente da matemática).
    Consulta o metadado tipo_resposta para aplicar só as regras cabíveis.
    """
    problemas = []
    tipo = q.get("tipo_resposta", "numerica")
    enun = q.get("enunciado") or ""
    alts = q.get("alternativas") or {}
    gab  = q.get("gabarito") or ""
    expl = q.get("explicacao") or ""

    if len(alts) != 5:
        problemas.append(("alternativas_qtd", f"{len(alts)} alternativas (esperado 5)"))
    if set(alts.keys()) != {"A", "B", "C", "D", "E"}:
        problemas.append(("alternativas_letras", f"letras: {sorted(alts.keys())}"))
    if gab not in alts:
        problemas.append(("gabarito_invalido", f"gabarito '{gab}' fora das alternativas"))
    if len(set(str(v).strip() for v in alts.values())) != len(alts):
        problemas.append(("alternativas_repetidas", "há alternativas com mesmo texto"))
    if any(not str(v).strip() for v in alts.values()):
        problemas.append(("alternativa_vazia", "alternativa em branco"))

    if len(enun) < 40:
        problemas.append(("enunciado_curto", f"{len(enun)} caracteres"))
    if len(expl) < 30:
        problemas.append(("explicacao_curta", f"{len(expl)} caracteres"))

    # O enunciado precisa fazer uma pergunta ou pedido
    if not re.search(r'\?|:\s*$|[Dd]etermine|[Cc]alcule|[Aa]ssinale|[Qq]uantas|[Qq]uantos|[Ii]ndique',
                     enun):
        problemas.append(("sem_pergunta", "enunciado não formula pergunta clara"))

    # A explicação deve terminar PERTO do resultado. Aceita "= 45 comparações"
    # (número + unidade), mas acusa se os últimos termos não têm número algum.
    # A explicação só precisa terminar perto do resultado quando a resposta
    # é NUMÉRICA. Para O(log n), "Aceita" ou 255.255.255.0 a regra não vale —
    # e o metadado diz isso diretamente, sem precisar adivinhar pelo texto.
    numerica = tipo in ("numerica", "fracao", "percentual")
    nums_expl = re.findall(r'\d+(?:[.,]\d+)?', expl)
    if nums_expl and len(nums_expl) > 2 and numerica:
        # Amplia a janela para 8 palavras: uma explicação bem escrita costuma
        # fechar com "restam 1.022 endereços atribuíveis a hosts" — o número
        # está no fim, mas seguido da unidade e do complemento.
        cauda = " ".join(expl.rstrip(" .").split()[-8:])
        if not re.search(r'\d', cauda):
            problemas.append(("explicacao_nao_termina_resultado",
                              f"últimas palavras sem número: '{cauda}'"))
    return problemas


# ──────────────────────────────────────────
#  RELATÓRIO
# ──────────────────────────────────────────

def verificar_lote(questoes: list, nome_lote: str = "") -> dict:
    erros_lingua = defaultdict(list)
    erros_forma  = defaultdict(list)

    for q in questoes:
        alvo = f"{q.get('enunciado','')}\n{q.get('explicacao','')}"
        for regra, trecho, expl in checar_lingua(alvo):
            erros_lingua[regra].append((q.get("topico", "?"), trecho, expl))
        for regra, det in checar_forma(q):
            erros_forma[regra].append((q.get("topico", "?"), det))

    return {"lingua": erros_lingua, "forma": erros_forma, "total": len(questoes)}


def imprimir_relatorio(res: dict, nome: str):
    total = res["total"]
    n_ling = sum(len(v) for v in res["lingua"].values())
    n_form = sum(len(v) for v in res["forma"].values())

    print(f"\n{'═'*62}")
    print(f"  {nome} — {total} questões")
    print(f"{'═'*62}")

    if not n_ling and not n_form:
        print("  ✅ Nenhum problema de língua ou forma encontrado.")
        return 0

    if n_ling:
        print(f"\n  ── LÍNGUA: {n_ling} ocorrência(s) ──\n")
        for regra, casos in sorted(res["lingua"].items(), key=lambda x: -len(x[1])):
            print(f"  ❌ {regra} ({len(casos)}x) — {casos[0][2]}")
            vistos = set()
            for topico, trecho, _ in casos:
                if topico in vistos: continue
                vistos.add(topico)
                print(f"       [{topico}] ...{trecho}...")
                if len(vistos) >= 3: break
            print()

    if n_form:
        print(f"\n  ── FORMA: {n_form} ocorrência(s) ──\n")
        for regra, casos in sorted(res["forma"].items(), key=lambda x: -len(x[1])):
            print(f"  ❌ {regra} ({len(casos)}x)")
            for topico, det in casos[:3]:
                print(f"       [{topico}] {det}")
            print()

    return n_ling + n_form


if __name__ == "__main__":
    sys.path.insert(0, ".")
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 2000

    import gerador_ads, gerador_procedural

    total_problemas = 0
    for nome, mod in [("ADS / Computação", gerador_ads),
                      ("Matemática", gerador_procedural)]:
        lote = mod.gerar_lote(qtd, seed=20260811)
        res  = verificar_lote(lote, nome)
        total_problemas += imprimir_relatorio(res, nome)

    print(f"\n{'═'*62}")
    if total_problemas == 0:
        print(f"  🎉 {qtd*2} questões verificadas — texto e forma OK")
    else:
        print(f"  ⚠️  {total_problemas} problema(s) encontrado(s)")
    print(f"{'═'*62}\n")
    sys.exit(1 if total_problemas else 0)
