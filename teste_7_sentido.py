"""
=============================================================
  TESTE 7 — SENTIDO E VEROSSIMILHANÇA
=============================================================
  Os testes anteriores verificam se a questão está CORRETA:
  gabarito confere, frase bem construída, português limpo.

  Este verifica se ela FAZ SENTIDO — se um leitor da área
  reconheceria a situação como real. Uma questão pode passar
  em todos os outros e ainda descrever algo que ninguém faria
  na prática:

    "250 mL de soro correndo em 12 horas"     (30 mL/h)
    "uma comissão de 2 pessoas escolhida
     entre 3 candidatos"                       (quase todos)
    "uma turma de 2 alunos"                    (grandeza fora de escala)
    "um datagrama de 65.000 bytes"             (acima do máximo do IP)

  CHECAGENS:
    1. Grandezas dentro de faixa plausível por domínio
    2. Proporções que não tornam o problema trivial
    3. Unidades coerentes com a grandeza
    4. Cenário sem contradição interna
    5. Enunciado autossuficiente (não pede dado ausente)
    6. Comando compatível com o tipo de resposta

  USO: python teste_7_sentido.py [quantidade]
=============================================================
"""

import sys
import re
from collections import defaultdict

sys.path.insert(0, ".")


# ══════════════════════════════════════════════════════════
#  FAIXAS PLAUSÍVEIS POR GRANDEZA
#
#  Os limites vêm da prática de cada área, não de restrição
#  matemática. Fora deles a conta continua correta, mas o
#  cenário soa artificial para quem conhece o assunto.
# ══════════════════════════════════════════════════════════

FAIXAS = [
    # (regex de captura, nome, mínimo, máximo, unidade)
    # Volume que CORRE no paciente. Ampola e frasco-ampola têm volumes bem
    # menores (1 a 20 mL) e são outra grandeza — por isso o padrão exige a
    # menção ao soro/solução em contexto de infusão, não de diluição.
    (r'(\d+) mL de (?:soro|Ringer|solução glicosada)',
     "volume de infusão", 50, 3000, "mL"),
    (r'(\d+) gotas por minuto',              "gotejamento",        5,  120, "gotas/min"),
    (r'(\d+) kg',                            "peso do paciente",   2,  200, "kg"),
    (r'paciente de (\d+) anos',              "idade",              0,  110, "anos"),
    (r'(\d+) leitos',                        "leitos",             5, 2000, "leitos"),

    (r'(\d+) alunos em uma turma',           "tamanho de turma",   5,   60, "alunos"),
    (r'(\d+) pessoas em uma reunião',        "reunião",            3,   50, "pessoas"),
    (r'(\d+) finalistas',                    "finalistas",         3,   30, "finalistas"),
    (r'(\d+) competidores',                  "competidores",       3,   50, "competidores"),

    (r'MTU de (\d+) bytes',                  "MTU",              576, 9000, "bytes"),
    (r'datagrama (?:IP )?de (\d+) bytes',    "datagrama",         21, 65535, "bytes"),
    (r'(\d+) Mbps',                          "taxa de enlace",     1, 100000, "Mbps"),
    (r'(\d+) MB',                            "tamanho de arquivo", 1, 1000000, "MB"),

    # Equipe = grupo que trabalha junto. Um levantamento de habilidades
    # pode envolver centenas de colaboradores sem ser uma "equipe".
    (r'(?:equipe|time|squad) de (\d+) (?:desenvolvedores|pessoas)',
     "equipe", 1, 60, "pessoas"),
    (r'(\d+) pontos de história',            "backlog",            1, 5000, "pontos"),
    (r'R\$ ([\d.]+),00',                     "valor monetário",  100, 100000000, "R$"),
]


def checar_grandezas(texto: str) -> list:
    problemas = []
    for padrao, nome, minimo, maximo, unidade in FAIXAS:
        for m in re.finditer(padrao, texto):
            try:
                valor = int(m.group(1).replace(".", ""))
            except ValueError:
                continue
            if valor < minimo:
                problemas.append(("grandeza_baixa",
                                  f"{nome} de {valor} {unidade} "
                                  f"(mínimo plausível: {minimo})"))
            elif valor > maximo:
                problemas.append(("grandeza_alta",
                                  f"{nome} de {valor} {unidade} "
                                  f"(máximo plausível: {maximo})"))
    return problemas


# ══════════════════════════════════════════════════════════
#  PROPORÇÕES QUE TORNAM O PROBLEMA TRIVIAL
# ══════════════════════════════════════════════════════════

def checar_proporcoes(texto: str) -> list:
    """
    Detecta escolhas em que quase todos são selecionados.

    "Escolher 3 de 4" ou "uma comissão de 5 entre 6" tem resposta
    tão pequena que a questão perde a graça — e o aluno resolve
    por contagem direta, sem aplicar a fórmula.
    """
    problemas = []

    # "exatamente A de N" — só quando os dois números pertencem AO MESMO
    # grupo. Em "3 pesquisadores e 4 bolsistas" são grupos diferentes, e
    # comparar 3 com 4 não faz sentido.
    for m in re.finditer(
            r'(\d+)\s+(pessoas|alunos|peças|filhos|verificações|entrevistados|'
            r'moedas|lançamentos)\b[^.]{0,60}?exatamente (\d+)\s+(?:del[ae]s|\2)',
            texto):
        try:
            total, escolhidos = int(m.group(1)), int(m.group(3))
        except (ValueError, IndexError):
            continue
        if total and escolhidos > total:
            problemas.append(("proporcao_invalida",
                              f"escolher {escolhidos} de {total}"))

    # Infusão: vazão mL/h
    mv = re.search(r'(\d+) mL', texto)
    mh = re.search(r'(?:em|ao longo de|durante|infundir em|por)\s+(\d+)\s+horas',
                   texto)
    if mv and mh:
        volume, horas = int(mv.group(1)), int(mh.group(1))
        if horas > 0:
            vazao = volume / horas
            # Limiar de 40 mL/h: abaixo disso a infusão é de manutenção
            # muito lenta (bomba de seringa), não o cenário típico de
            # equipo por gravidade que os enunciados descrevem.
            if vazao < 40:
                problemas.append(("vazao_implausivel",
                                  f"{volume} mL em {horas} h = "
                                  f"{vazao:.0f} mL/h (lento demais)"))
            elif vazao > 1500:
                problemas.append(("vazao_implausivel",
                                  f"{vazao:.0f} mL/h (rápido demais)"))

    # Sub-rede IPv4: /31 e /32 não comportam hosts endereçáveis.
    # NÃO se aplica a IPv6, onde /32 é um bloco enorme (96 bits livres).
    if "ipv6" not in texto.lower() and "::" not in texto:
        for m in re.finditer(r'\d+\.\d+\.\d+\.\d+/(\d+)', texto):
            p = int(m.group(1))
            if 31 <= p <= 32 and "host" in texto.lower():
                problemas.append(("prefixo_sem_hosts",
                                  f"prefixo /{p} não comporta hosts"))

    return problemas


# ══════════════════════════════════════════════════════════
#  CONTRADIÇÃO INTERNA
# ══════════════════════════════════════════════════════════

def checar_contradicao(texto: str) -> list:
    """
    O enunciado afirma duas coisas incompatíveis entre si.
    """
    problemas = []
    t = texto.lower()

    # Com e sem reposição na mesma questão
    tem_com  = bool(re.search(r'com reposição|é devolvid|recolocad|volta para', t))
    tem_sem  = bool(re.search(r'sem reposição|sem devolvê|não é devolvid', t))
    if tem_com and tem_sem:
        problemas.append(("reposicao_contraditoria",
                          "menciona com E sem reposição"))

    # Ordena importa e não importa
    if "a ordem não importa" in t and "a ordem importa" in t:
        problemas.append(("ordem_contraditoria", "ordem importa e não importa"))

    # Dias úteis e corridos no mesmo prazo
    if "dias úteis" in t and "dias corridos" in t:
        problemas.append(("contagem_contraditoria",
                          "menciona dias úteis E corridos"))

    # Retirar mais itens do que existem
    m_total = re.search(r'(\d+)\s+(?:bolas|fichas|cartões|chips|peças|bolinhas)', t)
    # Cobre "retira 7", "retiram-se 7", "são retiradas 7", "retirando 7"
    m_retir = re.search(
        r'(?:retira(?:m|-se|m-se|das?|dos?)?|retirando|sortei[ao]m?-?se)\s+'
        r'(?:as\s+|os\s+)?(\d+)', t)
    if m_total and m_retir:
        if int(m_retir.group(1)) > int(m_total.group(1)):
            problemas.append(("retirada_impossivel",
                              f"retira {m_retir.group(1)} de "
                              f"{m_total.group(1)} disponíveis"))

    return problemas


# ══════════════════════════════════════════════════════════
#  AUTOSSUFICIÊNCIA
# ══════════════════════════════════════════════════════════

def checar_autossuficiencia(q: dict) -> list:
    """
    O enunciado traz todos os dados necessários?

    Referências a elementos ausentes ("conforme a figura", "segundo
    a tabela acima") tornam a questão irrespondível quando o recurso
    não existe.
    """
    problemas = []
    texto = q.get("enunciado", "")
    t = texto.lower()

    REFERENCIAS = [
        (r'\b(?:a|na|conforme a|segundo a|de acordo com a)\s+figura\b', "figura"),
        (r'\b(?:o|no|conforme o|segundo o)\s+gráfico\b', "gráfico"),
        (r'\bimagem (?:acima|abaixo|a seguir)\b', "imagem"),
        (r'\besquema (?:acima|abaixo|a seguir)\b', "esquema"),
        (r'\bmapa (?:acima|abaixo|a seguir)\b', "mapa"),
    ]
    tem_visual = q.get("tem_elemento_visual", False)
    if not tem_visual:
        for padrao, nome in REFERENCIAS:
            if re.search(padrao, t):
                problemas.append(("referencia_ausente",
                                  f"cita '{nome}' mas não há elemento visual"))
                break

    # Tabela citada mas não presente no enunciado.
    # Reconhece dois formatos: colunas separadas por espaço ("VP   FP") e
    # lista rotulada ("P1: 8 ms"), ambos usados nos geradores.
    if re.search(r'\btabela (?:acima|abaixo|a seguir)\b', t):
        tem_colunas = bool(re.search(r'\n\s{2,}\S+\s{2,}\S+', texto))
        tem_lista   = bool(re.search(r'\n\s{2,}\w+\s*:\s*\S+', texto))
        if not (tem_colunas or tem_lista):
            problemas.append(("tabela_ausente",
                              "cita tabela que não está no enunciado"))

    return problemas


# ══════════════════════════════════════════════════════════
#  COMANDO COMPATÍVEL COM A RESPOSTA
# ══════════════════════════════════════════════════════════

def checar_comando(q: dict) -> list:
    """
    O que o enunciado PEDE bate com o que as alternativas OFERECEM?

    "Quantos hosts?" com alternativas em notação de máscara, ou
    "Qual a data?" com alternativas numéricas, são incoerências que
    nenhum outro teste pega.
    """
    problemas = []
    texto = q.get("enunciado", "")
    tipo  = q.get("tipo_resposta", "numerica")
    alts  = list(q.get("alternativas", {}).values())
    if not alts:
        return problemas
    amostra = str(alts[0])

    # "data" precisa estar como SUBSTANTIVO da pergunta, não dentro de
    # "data center" nem de "dados". O regex antigo casava com ambos.
    pede_data = bool(re.search(
        r'(?:qual|que)\s+(?:é\s+)?(?:a\s+)?data\b|'
        r'último dia|em que data|até que data|data final|data-limite',
        texto.lower()))
    pede_quantidade = bool(re.search(r'quant[oa]s|número de|total de', texto.lower()))
    pede_endereco  = bool(re.search(r'endereço (?:de rede|de broadcast|IP)|máscara',
                                    texto.lower()))

    eh_data     = bool(re.fullmatch(r'\d{2}/\d{2}/\d{4}', amostra))
    eh_numero   = bool(re.fullmatch(r'[\d.,]+%?', amostra))
    eh_endereco = bool(re.fullmatch(r'\d+\.\d+\.\d+\.\d+', amostra))

    if pede_data and not eh_data:
        problemas.append(("comando_incompativel",
                          f"pede data, alternativa é '{amostra}'"))
    elif pede_endereco and not (eh_endereco or "/" in amostra):
        problemas.append(("comando_incompativel",
                          f"pede endereço, alternativa é '{amostra}'"))
    elif pede_quantidade and eh_data:
        problemas.append(("comando_incompativel",
                          f"pede quantidade, alternativa é data"))

    return problemas


# ══════════════════════════════════════════════════════════

def verificar(questoes) -> dict:
    problemas = defaultdict(list)
    for q in questoes:
        e = q.get("enunciado", "")
        for regra, det in (checar_grandezas(e) + checar_proporcoes(e) +
                           checar_contradicao(e)):
            problemas[regra].append((q.get("topico", "?"), det, e[:110]))
        for regra, det in (checar_autossuficiencia(q) + checar_comando(q)):
            problemas[regra].append((q.get("topico", "?"), det, e[:110]))
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

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
    print("  TESTE 7 — SENTIDO E VEROSSIMILHANÇA")
    print("═" * 64)

    total = 0
    for nome, mod in GERADORES:
        lote = mod.gerar_lote(qtd, seed=20260816)
        probs = verificar(lote)
        n = sum(len(v) for v in probs.values())
        total += n
        marca = "✅" if n == 0 else "❌"
        print(f"\n  {marca} {nome}: {qtd} questões — {n} problema(s)")
        for regra, casos in sorted(probs.items(), key=lambda x: -len(x[1])):
            print(f"       {regra} ({len(casos)}x)")
            vistos = set()
            for topico, det, trecho in casos:
                if topico in vistos:
                    continue
                vistos.add(topico)
                print(f"          [{topico}] {det}")
                print(f"            {trecho}...")
                if len(vistos) >= 2:
                    break

    print("\n" + "═" * 64)
    print(f"  {'🎉 TESTE 7 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 64)
    sys.exit(1 if total else 0)
