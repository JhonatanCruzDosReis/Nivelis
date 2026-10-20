"""
=============================================================
  NIVELIS — Montador de Simulados Procedurais
=============================================================

  Monta um simulado COMPLETO combinando os geradores em
  Python, sem chamar IA no momento da geração.

  MISTURA PADRÃO
  --------------
    40%  procedural  — cálculo e simulação (ADS, matemática, saúde)
    30%  conceitual  — memorização (portas, HTTP, ACID, complexidades)
    30%  interpretação — sobre trechos de livros indexados

  A proporção é ajustável por parâmetro. Quando algum gerador
  não tem material disponível (ex.: livro sem trechos), sua
  fatia é redistribuída entre os demais em vez de o simulado
  vir incompleto.

  PONDERAÇÃO POR PROVA REAL (opcional)
  ------------------------------------
  Se houver provas na coleção 'provas_analisadas' da mesma
  área, a distribuição DENTRO da fatia procedural segue a
  frequência com que cada assunto foi cobrado. Assim o
  simulado espelha o que a banca realmente pede.

  USO (como biblioteca):
    from montar_simulado_procedural import montar
    simulado = montar(trechos=..., disciplinas=["ads"], quantidade=30)
=============================================================
"""

import random
from collections import Counter

# Proporção padrão entre as três fontes
MISTURA_PADRAO = {
    "procedural":    0.40,
    "conceitual":    0.30,
    "interpretacao": 0.30,
}


# ══════════════════════════════════════════════════════════════════
#  COMPATIBILIDADE ENTRE DISCIPLINA E ÁREAS CONCEITUAIS
#
#  A fatia conceitual (memorização) é hoje inteiramente de computação:
#  portas, HTTP, OSI, ACID, formas normais, SQL, Scrum, complexidades.
#
#  Sem este filtro, pedir um simulado de MATEMÁTICA trazia questão sobre
#  a porta do PostgreSQL — decoreba de TI num simulado de combinatória.
#
#  Quando não há área conceitual compatível com a disciplina pedida, a
#  fatia é redistribuída entre as demais fontes em vez de ser preenchida
#  com conteúdo fora do assunto.
# ══════════════════════════════════════════════════════════════════

# Quais áreas do gerador conceitual combinam com cada disciplina.
#
# Disciplina AUSENTE deste mapa recebe lista vazia por padrão — o que
# está correto, mas ficava implícito. Todas as disciplinas do projeto
# estão declaradas aqui, para que o comportamento seja explícito e a
# próxima disciplina não dependa de um acidente do `.get`.
CONCEITUAL_POR_DISCIPLINA = {
    # ── computação: o gerador conceitual tem material ──
    #
    # "redes" NÃO entra por padrão em ADS: é uma disciplina separada no
    # sistema, e quem pede um simulado de ADS não espera 18% de
    # endereçamento IP e modelo OSI.
    #
    # Para incluir, basta pedir as duas disciplinas:
    #   disciplinas=ads,redes
    # ou sobrescrever a fatia conceitual:
    #   conceitual=redes,algoritmos
    "ads":           ["banco_dados", "algoritmos", "eng_software"],
    "redes":         ["redes"],          # portas, OSI, HTTP
    "engenharia":    ["eng_software", "algoritmos"],

    # ── as demais não têm área conceitual correspondente ──
    "administracao": [],
    "matematica":    [],
    "basica":        [],
    "portugues":     [],
    "saude":         [],
    # "medicina" também sai daqui: este dicionário é indexado por DISCIPLINA,
    # e medicina é grupo — nunca chega a ser consultado. (A leitura é
    # `.get(d, [])`, então tanto faz para a execução; sai por coerência.)
    "direito":       [],
    "fisiologia":    [],
    "anatomia":      [],
    "farmacologia":  [],
    "imunologia":    [],
    "bioquimica":    [],
    "microbiologia": [],
    "histologia":    [],
    "embriologia":   [],
    "genetica":      [],
    "biocelular":    [],
}


LETRAS = ["A", "B", "C", "D", "E"]


def _normalizar(txt: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", str(txt) or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def calcular_distribuicao(quantidade: int, mistura: dict,
                          disponibilidade: dict) -> dict:
    """
    Converte a proporção em número de questões por fonte.

    `disponibilidade` diz quais fontes podem gerar (ex.: interpretação só
    funciona se houver trechos). Fontes indisponíveis têm sua fatia
    redistribuída proporcionalmente entre as demais — o simulado sai
    completo, com a composição possível.
    """
    ativas = {k: v for k, v in mistura.items() if disponibilidade.get(k)}
    if not ativas:
        raise ValueError("Nenhuma fonte de questões disponível.")

    soma = sum(ativas.values())
    ativas = {k: v / soma for k, v in ativas.items()}

    dist = {k: int(quantidade * p) for k, p in ativas.items()}

    # Sobras da divisão inteira vão para as fontes de maior peso
    resto = quantidade - sum(dist.values())
    for k in sorted(ativas, key=lambda x: -ativas[x]):
        if resto <= 0:
            break
        dist[k] += 1
        resto -= 1

    return {k: v for k, v in dist.items() if v > 0}


# ══════════════════════════════════════════════════════════
#  GRUPOS DE DISCIPLINAS
# ══════════════════════════════════════════════════════════
#
#  Atalhos para o app não precisar montar listas longas na
#  tela. Pedir "medicina" equivale a pedir as dez disciplinas
#  do ciclo básico.
#
#  Um grupo também resolve o problema de LASTRO: cada
#  disciplina de medicina tem entre 33 e 140 fatos, mas as
#  dez juntas somam bem mais — e o simulado deixa de repetir.

GRUPOS_DISCIPLINA = {
    "medicina": [
        "anatomia", "fisiologia", "bioquimica", "biocelular",
        "histologia", "embriologia", "genetica", "imunologia",
        "microbiologia", "farmacologia",
    ],
    "medicina_basico": [
        "anatomia", "fisiologia", "bioquimica", "biocelular",
        "histologia", "embriologia", "genetica",
    ],
    "computacao": ["ads", "redes", "engenharia"],
    "concursos": ["administracao", "direito", "portugues"],
    # "matematica" ESTAVA DE FORA do enem, e isso é conteúdo de prova
    # perdido: os dois geradores não se sobrepõem em nada. "basica" traz
    # porcentagem, juros, equações, pitágoras e área; "matematica" traz
    # combinatória, probabilidade, PA, PG e binômio — que caem no ENEM
    # todo ano e não chegavam ao usuário de jeito nenhum.
    "enem": ["basica", "matematica", "portugues"],
    # "fundamental" continua sem: combinatória e PG não são desse nível.
    "fundamental": ["basica", "portugues"],
}

# ── Lastro: fatos DISTINTOS que o veto de repetição reconhece ──
#
# Medido SIMULANDO o veto: gera-se um fluxo longo de questões e conta-se
# quantas entrariam antes de todas as seguintes esbarrarem em um fato já
# usado. Contar chaves distintas não serve — o montador rejeita por
# qualquer uma das duas chaves, a marcada pelo gerador e a derivada de
# tópico mais resposta, e a capacidade real é menor que os dois números.
#
# Foi o próprio teste 12 que pegou o erro: farmacologia estava anunciada
# com 132 e, num caderno de 60, repetia 25 vezes. A capacidade dela é 35.
#
# Seis disciplinas têm menos fatos do que um caderno de 30 questões.
# Não há ajuste de teto que resolva isso: pedir 30 de engenharia, que
# tem doze fatos, é pedir repetição. Daí o `maximo_sugerido` no retorno,
# para o aplicativo limitar o que oferece em vez de entregar um caderno
# que se repete sem avisar.
#
# Números a reconferir quando uma tabela crescer.
LASTRO_DISCIPLINA = {
    "engenharia":    12,
    # administração: o lastro vem do lado calculável. Os cinco
    # tópicos conceituais somam 80 fatos; os seis com conta
    # somam o resto. Ver administracao/_fontes.md.
    "administracao": 5862,
    "embriologia":   15,
    "biocelular":    17,
    "histologia":    19,
    "imunologia":    19,
    "bioquimica":    25,
    "genetica":      30,
    "farmacologia":  35,
    "microbiologia": 36,
    "anatomia":      65,
    "portugues":     76,
    "conceitual":    77,
    "fisiologia":   125,
    "basica":       886,
    "matematica":   964,
    "direito":     1531,
    "saude":       1862,
    "redes":       2220,
    "ads":         2398,
}

# Quantos fatos gastar, no máximo, em um caderno. Metade deixa margem
# para uma segunda prova da mesma disciplina sem reencontro imediato.
FRACAO_POR_CADERNO = 0.5


def capacidade(disciplinas, areas_conceituais=None) -> int:
    """
    Quantas questões distintas o material pedido sustenta.

    Soma o lastro das disciplinas (grupos já expandidos). Disciplina
    desconhecida não entra na conta — o número devolvido é um piso, não
    uma promessa.
    """
    total = sum(LASTRO_DISCIPLINA.get(d, 0) for d in disciplinas)
    if areas_conceituais:
        total += LASTRO_DISCIPLINA.get("conceitual", 0)
    return total


def maximo_sugerido(disciplinas, areas_conceituais=None) -> int:
    """Tamanho de caderno que o material sustenta com folga."""
    return max(5, int(capacidade(disciplinas, areas_conceituais)
                      * FRACAO_POR_CADERNO))


def expandir_grupos(disciplinas, geradores):
    """
    Troca nomes de GRUPO pelas disciplinas que ele reúne.

    Mantém o que já for disciplina individual, e descarta do grupo o
    que não estiver carregado — assim um gerador ausente não derruba
    o pedido inteiro.
    """
    saida, vistos = [], set()
    for d in (disciplinas or []):
        alvos = GRUPOS_DISCIPLINA.get(d, [d])
        for a in alvos:
            if a in vistos:
                continue
            if a in geradores or a == d:
                vistos.add(a)
                saida.append(a)
    return saida



def pesos_por_prova(provas: list, topicos_gerador: dict) -> dict:
    """
    Deriva o peso de cada área a partir da frequência com que ela aparece
    nas provas analisadas.

    `provas` é a lista de documentos de 'provas_analisadas'.
    `topicos_gerador` é o mapa TOPICOS_* do gerador (área → templates).

    Retorna {area: peso}. Áreas não citadas nas provas recebem peso mínimo,
    para não sumirem do simulado.
    """
    if not provas:
        return {}

    # Junta o vocabulário de todos os temas cobrados
    vocabulario = []
    for p in provas:
        for t in p.get("topicos", []):
            vocabulario.append(_normalizar(t.get("tema", "")))
            vocabulario.append(_normalizar(t.get("subtopico", "")))
    texto = " ".join(vocabulario)

    contagem = {}
    for area, templates in topicos_gerador.items():
        # Conta quantas vezes o nome da área (e de seus templates) aparece
        n = texto.count(_normalizar(area).replace("_", " "))
        for tpl in templates:
            n += texto.count(_normalizar(tpl).replace("_", " "))
        contagem[area] = n

    total = sum(contagem.values())
    if total == 0:
        return {}

    # Peso mínimo de 5% para nenhuma área ficar de fora
    minimo = 0.05
    pesos = {a: max(n / total, minimo) for a, n in contagem.items()}
    soma = sum(pesos.values())
    return {a: p / soma for a, p in pesos.items()}


def _dividir_por_area(quantidade: int, pesos: dict, rng) -> dict:
    """Distribui N questões entre áreas conforme os pesos."""
    if not pesos:
        return {}
    areas = list(pesos.keys())
    dist = {a: int(quantidade * pesos[a]) for a in areas}
    resto = quantidade - sum(dist.values())
    ordem = sorted(areas, key=lambda a: -pesos[a])
    i = 0
    while resto > 0:
        dist[ordem[i % len(ordem)]] += 1
        resto -= 1
        i += 1
    return {a: n for a, n in dist.items() if n > 0}


def _equilibrar_gabarito(questoes, gabaritos, rng):
    """
    Espalha a letra do gabarito pelo caderno.

    Cada gerador sorteia a posição da resposta por conta própria, o que
    dá uma distribuição uniforme NA MÉDIA. Num caderno específico, não:
    em 60 simulados de 30 questões, dois saíram com a letra E correta
    treze e quatorze vezes. É azar, não defeito — mas é azar que o aluno
    percebe e explora, e prova séria não deixa a sorte decidir isso.

    Aqui cada questão recebe uma letra-alvo de um conjunto equilibrado,
    e as alternativas são ROTACIONADAS até que a correta caia nela. A
    rotação preserva a ordem relativa das opções, então nada mais muda —
    nem o conteúdo, nem a explicação, que se refere ao texto e não à
    letra.
    """
    if not questoes:
        return

    # Distribuição EQUILIBRADA, não exata. Seis de cada letra num
    # caderno de 30 é um padrão em si: quem conta as marcações sabe, nas
    # últimas questões, quais letras já se esgotaram. O teto por letra
    # deixa folga suficiente para o caderno parecer sorteado e apertado
    # o bastante para nenhuma letra dominar.
    # Parte-se da divisão exata e aplicam-se algumas transferências de
    # uma letra para outra. Preencher por sorteio com teto não serve:
    # o teto acaba sendo atingido em todo caderno, e "sempre existe uma
    # letra com exatamente sete" é tão previsível quanto "sempre seis de
    # cada". Com as transferências, a folga é que varia.
    n = len(questoes)
    base, resto = divmod(n, len(LETRAS))
    contas = {L: base for L in LETRAS}
    for L in rng.sample(LETRAS, resto):
        contas[L] += 1

    for _ in range(max(1, n // 10)):
        doador = rng.choice([L for L in LETRAS if contas[L] > max(0, base - 2)]
                            or LETRAS)
        recebe = rng.choice([L for L in LETRAS
                             if L != doador and contas[L] < base + 2] or [doador])
        if doador != recebe and contas[doador] > 0:
            contas[doador] -= 1
            contas[recebe] += 1

    alvos = [L for L, k in contas.items() for _ in range(k)]
    rng.shuffle(alvos)

    for q, g, alvo in zip(questoes, gabaritos, alvos):
        alts = q.get("alternativas") or {}
        atual = g.get("resposta_correta")
        letras = [L for L in LETRAS if L in alts]
        if atual not in letras or alvo not in letras:
            continue

        giro = (letras.index(alvo) - letras.index(atual)) % len(letras)
        if giro == 0:
            continue
        valores = [alts[L] for L in letras]
        valores = valores[-giro:] + valores[:-giro]
        q["alternativas"] = dict(zip(letras, valores))
        g["resposta_correta"] = alvo


def montar(quantidade: int = 30,
           disciplinas: list = None,
           trechos: list = None,
           provas: list = None,
           mistura: dict = None,
           seed: int = None,
           geradores: dict = None,
           areas_conceituais: list = None) -> dict:
    """
    Monta o simulado completo.

    quantidade        — total de questões
    disciplinas       — geradores procedurais a usar (ex.: ["ads", "saude"])
    trechos           — trechos analisados de livros (fatia de interpretação)
    provas            — documentos de 'provas_analisadas' para ponderar áreas
    mistura           — proporção entre as fontes (padrão: 40/30/30)
    geradores         — injeção de dependência; se None, importa os módulos
    areas_conceituais — sobrescreve o filtro automático da fatia conceitual.
                        Por padrão, só entram áreas compatíveis com as
                        disciplinas pedidas (ver CONCEITUAL_POR_DISCIPLINA).

    Retorna dict com 'questoes', 'gabarito' e 'composicao'.
    """
    rng = random.Random(seed)
    mistura = mistura or MISTURA_PADRAO

    if geradores is None:
        # O catálogo é carregado disciplina a disciplina, e o que faltar
        # simplesmente não entra. Antes eram sete imports fixos num
        # bloco só, e as disciplinas acrescentadas depois não existiam
        # para o simulado.
        _CATALOGO = [
            ("ads",           "gerador_ads"),
            ("administracao", "gerador_administracao"),
            ("matematica",    "gerador_procedural"),
            ("basica",        "gerador_basica"),
            ("portugues",     "gerador_portugues"),
            ("saude",         "gerador_saude"),
            # "medicina" NÃO entra aqui: nunca existiu um gerador_medicina.py.
            # Medicina é um GRUPO (ver GRUPOS_DISCIPLINA), expandido nas dez
            # disciplinas do ciclo básico antes de qualquer filtro. A linha
            # antiga apontava para um módulo inexistente, o import falhava e
            # era engolido pelo `except ImportError` — custo zero em execução,
            # mas quem lesse o catálogo acreditaria que existe um gerador de
            # medicina para manter.
            ("fisiologia",    "gerador_fisiologia"),
            ("anatomia",      "gerador_anatomia"),
            ("farmacologia",  "gerador_farmacologia"),
            ("imunologia",    "gerador_imunologia"),
            ("bioquimica",    "gerador_bioquimica"),
            ("microbiologia", "gerador_microbiologia"),
            ("histologia",    "gerador_histologia"),
            ("embriologia",   "gerador_embriologia"),
            ("genetica",      "gerador_genetica"),
            ("biocelular",    "gerador_biocelular"),
            ("engenharia",    "gerador_engenharia"),
            ("direito",       "gerador_direito"),
            ("redes",         "gerador_redes"),
            ("conceitual",    "gerador_decoreba"),
            ("interpretacao", "gerador_interpretacao"),
        ]
        geradores = {}
        for _chave, _modulo in _CATALOGO:
            try:
                geradores[_chave] = __import__(_modulo)
            except ImportError:
                pass

    disciplinas = disciplinas or ["ads"]

    # Expande grupos ANTES da validação: "medicina" vira as dez
    # disciplinas do ciclo básico.
    disciplinas = expandir_grupos(disciplinas, geradores)

    # Disciplina pedida que NÃO existe precisa ser sinalizada. Antes o
    # filtro descartava em silêncio e caía no padrão "ads" — pedir um
    # simulado de fisiologia devolvia questões de ADS sem aviso.
    _pedidas = list(disciplinas)
    disciplinas = [d for d in disciplinas
                   if d in geradores and d != "conceitual"]
    _ausentes = [d for d in _pedidas
                 if d not in geradores and d != "conceitual"]
    if _ausentes and not disciplinas:
        raise ValueError(
            f"Disciplina(s) indisponível(is): {', '.join(_ausentes)}. "
            f"Disponíveis: {sorted(k for k in geradores if k != 'interpretacao')}"
        )
    if not disciplinas:
        disciplinas = ["ads"]

    # ── Quais áreas conceituais combinam com as disciplinas pedidas ──
    if areas_conceituais is None:
        areas_conceituais = []
        for d in disciplinas:
            for area in CONCEITUAL_POR_DISCIPLINA.get(d, []):
                if area not in areas_conceituais:
                    areas_conceituais.append(area)
    # valida contra o que o gerador realmente oferece
    if "conceitual" in geradores:
        validas = set(geradores["conceitual"].TOPICOS_DECOREBA)
        areas_conceituais = [a for a in areas_conceituais if a in validas]

    disponibilidade = {
        "procedural":    bool(disciplinas),
        "conceitual":    "conceitual" in geradores and bool(areas_conceituais),
        "interpretacao": bool(trechos) and len(trechos) >= 3,
    }
    # Quantas questões com a MESMA assinatura o simulado tolera. Num
    # simulado de 10, duas do mesmo tipo passam; cinco não.
    from collections import Counter
    assinaturas = Counter()
    TETO_ASSINATURA = max(2, quantidade // 6)

    dist = calcular_distribuicao(quantidade, mistura, disponibilidade)

    # A fatia conceitual não pode exceder o MATERIAL DISPONÍVEL. Com
    # três áreas e sete templates, pedir doze questões forçava tópico
    # repetido — e o aluno percebe.
    #
    # O excedente volta para a fatia procedural, que tem lastro maior.
    if dist.get("conceitual") and "conceitual" in geradores:
        _tops = geradores["conceitual"].TOPICOS_DECOREBA
        _teto = sum(len(_tops.get(a, [])) for a in areas_conceituais)
        if _teto and dist["conceitual"] > _teto:
            _sobra = dist["conceitual"] - _teto
            dist["conceitual"] = _teto
            dist["procedural"] = dist.get("procedural", 0) + _sobra
            _teto_aplicado = {
                "fonte": "conceitual",
                "pedido": _teto + _sobra,
                "disponivel": _teto,
                "motivo": (f"as áreas {areas_conceituais} somam apenas "
                           f"{_teto} templates; o excedente foi para a "
                           f"fatia procedural para não repetir tópico"),
            }
        else:
            _teto_aplicado = None
    else:
        _teto_aplicado = None

    questoes, gabaritos = [], []
    composicao = {}
    vistos = set()      # enunciados já incluídos, para não repetir
    # Questões recusadas SÓ pelo teto de assinatura. Não têm defeito
    # nenhum — são boas questões que chegaram depois da cota do tópico.
    # Ficam de reserva para o caso de o caderno não fechar sem elas.
    reserva = []

    def _chave(q):
        """Identidade da questão: enunciado normalizado."""
        return " ".join(str(q.get("enunciado", "")).lower().split())

    # Fatos já usados. O enunciado sozinho não basta: "Qual é o prazo
    # legal, em dias úteis?" e "O prazo previsto na CLT é de:" são
    # textos diferentes para o mesmo fato — recurso de revista, 8 dias —
    # e apareceram três vezes no mesmo caderno de direito. O mesmo com
    # "a PDU da camada de transporte é o segmento", perguntado duas
    # vezes em redes.
    fatos = set()
    respostas = Counter()

    def _fato_de(q, g):
        """
        Identidade do CONTEÚDO da questão, não do texto.

        Sete geradores não marcam `_fato` nos seus templates. Para
        esses, a chave é derivada: tópico mais o texto da resposta
        certa. Duas questões de "Direito do trabalho (prazos)" cuja
        resposta é "8" são, para quem responde, a mesma questão — ainda
        que uma pergunte "qual é o prazo legal" e a outra "o prazo
        previsto na CLT é de".
        """
        marcado = g.get("_fato")
        if marcado:
            # Caixa e acento não distinguem fato nenhum, e dois geradores
            # que cobrem o mesmo assunto escrevem a chave cada um do seu
            # jeito: "pilar:abstração" no de engenharia, "pilar:Abstração"
            # no conceitual. São a mesma questão para quem responde.
            return "m|" + _normalizar(str(marcado))
        letra = g.get("resposta_correta")
        resposta = (q.get("alternativas") or {}).get(letra, "")
        return f"{g.get('topico', '')}|{str(resposta)[:60]}"

    def _acumular(qs, gb, rotulo, limite=None):
        """
        Adiciona as questões, descartando as que já estão no simulado.

        Cada gerador é chamado sem saber o que os outros produziram, e com
        pouco material (poucos trechos, ou uma área com poucos templates) a
        mesma questão pode sair duas vezes. Aqui ela é filtrada.

        `limite` corta o excedente: como a reposição pede a mais para
        compensar descartes, sem isso o simulado passaria do tamanho pedido.

        Retorna quantas foram efetivamente aceitas.
        """
        aceitas = 0
        for q, g in zip(qs, gb):
            if limite is not None and aceitas >= limite:
                break
            k = _chave(q)
            if k in vistos:
                continue
            # Fato repetido vai para a reserva em vez de ser descartado:
            # se o material acabar, é melhor um fato repetido do que um
            # caderno menor do que o pedido.
            # As DUAS chaves são consultadas, a marcada e a derivada.
            # Um gerador marca o fato e outro não, então a mesma coisa
            # sabida podia entrar duas vezes com chaves diferentes: a
            # porta 25 do SMTP veio do gerador de redes (marcada
            # "porta:SMTP") e do conceitual (derivada do tópico mais a
            # resposta) no mesmo caderno.
            _f = _fato_de(q, g)
            _fd = _fato_de(q, dict(g, _fato=""))
            if _f in fatos or _fd in fatos:
                reserva.append((q, g, str(g.get("topico", ""))[:44], rotulo))
                continue

            # Mesmo com fatos distintos, a mesma RESPOSTA repetida no
            # mesmo assunto cansa: três questões de crase respondidas
            # com "o acento grave é obrigatório" são três frases
            # diferentes, mas o aluno lê a mesma coisa três vezes e
            # percebe o padrão. Duas passam; a terceira espera na
            # reserva.
            _resp = _fd
            if respostas[_resp] >= 2:
                reserva.append((q, g, str(g.get("topico", ""))[:44], rotulo))
                continue

            # TETO POR TEMPLATE, atravessando as várias chamadas.
            #
            # O veto interno do gerador vale dentro de UMA chamada. Mas o
            # simulado divide a cota por área e chama várias vezes; sem
            # este controle, "redes" saía sorteada três vezes seguidas e
            # o lote vinha com cinco questões de sub-rede em seis.
            #
            # A assinatura combina o tópico com a forma da pergunta, que
            # é o que o aluno percebe como repetição.
            # A assinatura é o TÓPICO, não a pergunta: um único template
            # de sub-rede produz "broadcast", "máscara" e "hosts", que
            # são perguntas diferentes mas o mesmo assunto — e é o
            # assunto que o aluno percebe como repetido.
            _assin = str(g.get("topico", ""))[:44]
            if _assin and assinaturas[_assin] >= TETO_ASSINATURA:
                reserva.append((q, g, _assin, rotulo))
                continue
            if _assin:
                assinaturas[_assin] += 1

            vistos.add(k)
            fatos.add(_f)
            fatos.add(_fd)
            respostas[_resp] += 1
            n = len(questoes) + 1
            q["numero"], g["numero"] = n, n
            questoes.append(q)
            gabaritos.append(g)
            aceitas += 1
        if aceitas:
            composicao[rotulo] = composicao.get(rotulo, 0) + aceitas
        return aceitas


    def _acumular_com_reposicao(gerar_fn, alvo, rotulo, max_tentativas=6):
        """
        Chama o gerador repetidamente até atingir `alvo` questões únicas.

        Pede um pouco a mais a cada rodada, já contando com descartes. Se o
        material se esgotar (poucos trechos, por exemplo), para e devolve o
        que conseguiu — o chamador redistribui a diferença.
        """
        obtidas = 0
        for tentativa in range(max_tentativas):
            faltam = alvo - obtidas
            if faltam <= 0:
                break
            pedido = faltam + min(faltam, 4) * (tentativa > 0)
            qs, gb = gerar_fn(pedido)
            n = _acumular(qs, gb, rotulo, limite=faltam)
            if n == 0 and tentativa > 0:
                break       # gerador esgotou o material disponível
            obtidas += n
        return obtidas

    # ── Fatia procedural ──
    n_proc = dist.get("procedural", 0)
    if n_proc:
        por_disc = _dividir_por_area(n_proc, {d: 1 / len(disciplinas)
                                              for d in disciplinas}, rng)
        for disc, n in por_disc.items():
            mod = geradores[disc]
            mapa = (getattr(mod, "TOPICOS_ADS", None)
                    or getattr(mod, "TOPICOS_SAUDE", None)
                    or getattr(mod, "TOPICOS_DIREITO", None)
                    or getattr(mod, "TOPICOS_REDES", None)
                    or getattr(mod, "TOPICOS", {}))
            pesos = pesos_por_prova(provas or [], mapa)

            # TETO DE CONCENTRAÇÃO: nenhuma área pode passar de 40% da
            # fatia, por mais que as provas analisadas a favoreçam.
            #
            # Sem isso, uma coleção de provas com muitas menções a redes
            # fazia o simulado de ADS sair com metade das questões de
            # endereçamento IP — fiel às provas, mas ruim para o aluno.
            if pesos:
                _total = sum(pesos.values()) or 1
                _teto = 0.40
                _excedentes = {a: p for a, p in pesos.items()
                               if p / _total > _teto}
                if _excedentes and len(pesos) > 1:
                    for a in _excedentes:
                        pesos[a] = _total * _teto
                    # redistribui o que sobrou entre as demais
                    _resto = [a for a in pesos if a not in _excedentes]
                    if _resto:
                        _sobra = _total - sum(pesos.values())
                        if _sobra > 0:
                            for a in _resto:
                                pesos[a] += _sobra / len(_resto)

            if pesos:
                por_area = _dividir_por_area(n, pesos, rng)
                for area, na in por_area.items():
                    _acumular_com_reposicao(
                        lambda k, m=mod, a=area: m.gerar_para_api(
                            quantidade=k, topico=a, seed=rng.randint(0, 10**6)),
                        na, f"procedural:{disc}")
            else:
                _acumular_com_reposicao(
                    lambda k, m=mod: m.gerar_para_api(
                        quantidade=k, seed=rng.randint(0, 10**6)),
                    n, f"procedural:{disc}")

    # ── Fatia conceitual ──
    n_con = dist.get("conceitual", 0)
    if n_con:
        mod = geradores["conceitual"]
        # Pondera apenas dentro das áreas compatíveis
        topicos_filtrados = {a: mod.TOPICOS_DECOREBA[a] for a in areas_conceituais}
        pesos = pesos_por_prova(provas or [], topicos_filtrados)
        if pesos:
            for area, na in _dividir_por_area(n_con, pesos, rng).items():
                _acumular_com_reposicao(
                    lambda k, a=area: mod.gerar_para_api(
                        quantidade=k, topico=a, seed=rng.randint(0, 10**6)),
                    na, "conceitual")
        else:
            # Sem provas para ponderar: distribui igualmente entre as áreas
            por_area = _dividir_por_area(
                n_con, {a: 1 / len(areas_conceituais) for a in areas_conceituais}, rng)
            for area, na in por_area.items():
                _acumular_com_reposicao(
                    lambda k, a=area: mod.gerar_para_api(
                        quantidade=k, topico=a, seed=rng.randint(0, 10**6)),
                    na, "conceitual")

    # ── Fatia de interpretação ──
    n_int = dist.get("interpretacao", 0)
    if n_int:
        _acumular_com_reposicao(
            lambda k: geradores["interpretacao"].gerar_para_api(
                trechos, quantidade=k, seed=rng.randint(0, 10**6)),
            n_int, "interpretacao")

    # ── Completa o que faltou ──
    # Se alguma fonte esgotou o material (ex.: poucos trechos), as demais
    # cobrem a diferença para o simulado sair com o tamanho pedido.
    faltam = quantidade - len(questoes)
    if faltam > 0:
        for disc in disciplinas:
            if faltam <= 0:
                break
            mod = geradores[disc]
            n = _acumular_com_reposicao(
                lambda k, m=mod: m.gerar_para_api(
                    quantidade=k, seed=rng.randint(0, 10**6)),
                faltam, f"procedural:{disc}")
            faltam -= n
        if faltam > 0 and areas_conceituais:
            area = areas_conceituais[0]
            n = _acumular_com_reposicao(
                lambda k: geradores["conceitual"].gerar_para_api(
                    quantidade=k, topico=area, seed=rng.randint(0, 10**6)),
                faltam, "conceitual")
            faltam -= n

    # ── Relaxa o teto de assinatura, se ainda faltar ──
    #
    # TETO_ASSINATURA limita quantas questões do mesmo tópico entram, e
    # isso vale enquanto houver de onde tirar outras. Numa disciplina com
    # POUCOS rótulos de tópico, porém, o teto vira um limite absoluto:
    # anatomia tem quatro tópicos e, num caderno de 20 (teto 3), parava
    # em 12 questões — o simulado saía menor do que o pedido em toda
    # semente, em silêncio.
    #
    # Aqui as recusadas voltam, começando pelos tópicos menos usados, de
    # modo que a concentração cresça de forma espalhada e não em bloco.
    reaproveitados = 0
    faltam = quantidade - len(questoes)
    if faltam > 0 and reserva:
        # A escolha é REVISTA a cada questão aceita, não ordenada uma
        # vez só. Ordenar antes e percorrer a lista fazia o desempate
        # inicial valer até o fim: com anatomia, que tem quatro tópicos,
        # as oito questões de reposição vinham quase todas do mesmo, e o
        # caderno de 20 saía com onze de Terminologia Anatômica.
        #
        # Escolhendo sempre da assinatura menos usada no momento, a
        # reposição se distribui.
        pendentes = list(reserva)
        while faltam > 0 and pendentes:
            # Primeiro as de fato inédito; entre elas, as do assunto
            # menos usado. Só quando não houver mais nenhuma inédita é
            # que um fato se repete — e aí é isso ou devolver o caderno
            # incompleto.
            pendentes.sort(key=lambda r: (
                _fato_de(r[0], r[1]) in fatos
                or _fato_de(r[0], dict(r[1], _fato="")) in fatos,
                # A reposição também evita insistir na mesma RESPOSTA:
                # sem este critério, o caderno de português fechava com
                # três "o acento grave é obrigatório" porque a sexta
                # questão de crase vinha da reserva, onde o limite de
                # duas não era consultado.
                respostas[_fato_de(r[0], dict(r[1], _fato=""))] >= 2,
                assinaturas[r[2]]))
            q, g, _assin, rotulo = pendentes.pop(0)
            k = _chave(q)
            if k in vistos:
                continue
            if (_fato_de(q, g) in fatos
                    or _fato_de(q, dict(g, _fato="")) in fatos):
                reaproveitados += 1
            vistos.add(k)
            fatos.add(_fato_de(q, g))
            fatos.add(_fato_de(q, dict(g, _fato="")))
            respostas[_fato_de(q, dict(g, _fato=""))] += 1
            assinaturas[_assin] += 1
            questoes.append(q)
            gabaritos.append(g)
            composicao[rotulo] = composicao.get(rotulo, 0) + 1
            faltam -= 1

    # Embaralha para os tipos não ficarem agrupados, renumerando em seguida
    indices = list(range(len(questoes)))
    rng.shuffle(indices)
    questoes = [questoes[i] for i in indices]
    gabaritos = [gabaritos[i] for i in indices]
    for n, (q, g) in enumerate(zip(questoes, gabaritos), start=1):
        q["numero"], g["numero"] = n, n

    # Quando o material acaba, a reserva devolve questões cujo fato já
    # está no caderno. É melhor do que entregar menos questões do que o
    # aluno pediu, mas precisa ficar REGISTRADO: engenharia de software
    # tem 29 fatos em três templates, e um caderno de 30 inevitavelmente
    # repete. Em silêncio, isso parecia defeito do gerador; declarado, é
    # o que é — falta de lastro na disciplina.
    # Campo PRÓPRIO, e não outra entrada em limite_material: aquele
    # guarda um motivo só, já ocupado pelo teto da fatia conceitual em
    # ADS e engenharia — as duas disciplinas em que a falta de lastro
    # aparece. Somado ali, o aviso mais importante seria justamente o
    # que nunca apareceria.
    fatos_repetidos = reaproveitados

    _equilibrar_gabarito(questoes, gabaritos, rng)

    # O _fato é de uso interno do montador. Sai antes de devolver, para
    # não ir parar no documento de gabarito gravado no banco.
    for g in gabaritos:
        g.pop("_fato", None)

    return {
        "questoes":   questoes,
        "gabarito":   gabaritos,
        "total":      len(questoes),
        "limite_material": _teto_aplicado,
        "fatos_repetidos": fatos_repetidos,
        "maximo_sugerido": maximo_sugerido(disciplinas, areas_conceituais),
        "composicao": composicao,
        "areas_conceituais": areas_conceituais,
        "ponderado_por_prova": bool(provas),
    }
