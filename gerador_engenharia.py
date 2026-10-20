"""
=============================================================
  GERADOR DE ENGENHARIA DE SOFTWARE
=============================================================
  Questões geradas proceduralmente a partir de fatos
  verificados em fonte — não de um livro específico.

  ESCOPO:
    ✅ Princípios SOLID
    ✅ Pilares da orientação a objetos
    ✅ Categorias de padrões de projeto (GoF)
    ❌ Escolha de arquitetura para um caso concreto

  VERIFICAÇÃO DAS FONTES

  Registradas em engenharia/_fontes.md, incluindo uma
  divergência de data sobre o princípio de Liskov — 1987 na
  palestra, 1994 na formulação formal. Os templates não
  cobram a data por isso.

  USO:
      from gerador_engenharia import gerar_lote, gerar_para_api
=============================================================
"""

import random
import re
import unicodedata

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


# ══════════════════════════════════════════════════════════
#  BASE DE FATOS
# ══════════════════════════════════════════════════════════

# ── Princípios SOLID ──
#
# Fontes: freeCodeCamp; Estratégia Concursos (TSE-TI); Campus Code;
# Itaú Tech; Martin, Clean Architecture.
#
# (sigla, nome, com_artigo, enunciado, violação típica, armadilha)
SOLID = [
    ("S", "responsabilidade única", "o princípio da responsabilidade única",
     "uma classe deve ter um, e somente um, motivo para mudar",
     "uma classe que persiste dados, envia notificações e formata "
     "relatórios ao mesmo tempo",
     "o critério é o MOTIVO PARA MUDAR, não a quantidade de métodos: "
     "uma classe com vários métodos pode respeitar o princípio"),

    ("O", "aberto-fechado", "o princípio aberto-fechado",
     "entidades de software devem estar abertas para extensão e "
     "fechadas para modificação",
     "um cálculo que exige acrescentar um novo caso ao encadeamento de "
     "condicionais a cada tipo novo",
     "a extensão se faz por herança ou composição, sem editar o código "
     "já existente e testado"),

    ("L", "substituição de Liskov", "o princípio da substituição de Liskov",
     "uma classe derivada deve poder substituir sua classe base sem "
     "quebrar o comportamento do programa",
     "uma subclasse que lança exceção em um método herdado que a base "
     "executava normalmente",
     "violar esse princípio costuma levar a verificações de tipo em "
     "tempo de execução, o que por sua vez viola o aberto-fechado"),

    ("I", "segregação de interface", "o princípio da segregação de interface",
     "clientes não devem ser forçados a depender de métodos que não "
     "utilizam",
     "uma interface ampla que obriga toda classe implementadora a "
     "definir métodos irrelevantes para ela",
     "é preferível ter várias interfaces específicas a uma única "
     "interface genérica"),

    ("D", "inversão de dependência", "o princípio da inversão de dependência",
     "módulos de alto nível não devem depender de módulos de baixo "
     "nível; ambos devem depender de abstrações",
     "uma regra de negócio que instancia diretamente a classe concreta "
     "do banco de dados",
     "não se confunde com injeção de dependência: o princípio é o alvo, "
     "a injeção é uma técnica para alcançá-lo"),
]

# ── Pilares da orientação a objetos ──
#
# (pilar, com_artigo, definição, exemplo, armadilha)
PILARES_POO = [
    ("abstração", "a abstração",
     "representar no código apenas os aspectos relevantes de uma "
     "entidade, ocultando o que não interessa ao problema",
     "modelar um cliente bancário com CPF e saldo, sem incluir cor "
     "favorita",
     "a abstração decide O QUE representar; o encapsulamento decide o "
     "que expor"),

    ("encapsulamento", "o encapsulamento",
     "esconder o estado interno do objeto e expor apenas operações "
     "controladas de acesso",
     "declarar o saldo como privado e permitir alteração somente por "
     "métodos de depósito e saque",
     "não se resume a usar atributos privados: o ponto é controlar como "
     "o estado muda"),

    ("herança", "a herança",
     "permitir que uma classe reaproveite atributos e comportamentos de "
     "outra, estabelecendo relação do tipo \"é um\"",
     "uma classe ContaPoupanca que estende ContaBancaria",
     "estabelece relação \"é um\", enquanto a composição estabelece "
     "\"tem um\" — e a recomendação clássica é preferir composição"),

    ("polimorfismo", "o polimorfismo",
     "permitir que uma mesma operação produza comportamentos diferentes "
     "conforme o tipo do objeto",
     "chamar calcularJuros em contas de tipos distintos e obter "
     "resultados próprios de cada tipo",
     "depende de uma interface ou classe base comum, e é o que viabiliza "
     "o princípio aberto-fechado"),
]

# ── Categorias de padrões GoF ──
#
# Fonte: Gamma, Helm, Johnson e Vlissides — Design Patterns (1994).
#
# (categoria, com_artigo, o que resolve, exemplos)
CATEGORIAS_GOF = [
    ("criacional", "os padrões criacionais",
     "como os objetos são criados, isolando o cliente do processo de "
     "instanciação",
     ["Singleton", "Factory Method", "Builder", "Prototype",
      "Abstract Factory"]),

    ("estrutural", "os padrões estruturais",
     "como classes e objetos se compõem para formar estruturas maiores",
     ["Adapter", "Decorator", "Facade", "Proxy", "Composite", "Bridge"]),

    ("comportamental", "os padrões comportamentais",
     "como os objetos se comunicam e distribuem responsabilidades entre si",
     ["Observer", "Strategy", "Command", "Template Method", "Iterator",
      "State"]),
]


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _com_preposicao(prep: str, sintagma: str) -> str:
    """Junta preposição e sintagma fazendo a CONTRAÇÃO."""
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "): "à ", ("a", "o "): "ao ", ("a", "os "): "aos ",
        ("de", "a "): "da ", ("de", "o "): "do ", ("de", "os "): "dos ",
        ("em", "a "): "na ", ("em", "o "): "no ", ("em", "os "): "nos ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


def _inicial_maiuscula(t: str) -> str:
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str):
    unicos = []
    for d in distratores:
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
    alternativas = {L: formatador(v) for L, v in zip(LETRAS, valores)}
    if len(set(alternativas.values())) < 5:
        return None
    gabarito = next(L for L, v in zip(LETRAS, valores) if v == correta)
    return {
        "enunciado":         enunciado,
        "alternativas":      alternativas,
        "gabarito":          gabarito,
        "explicacao":        explicacao,
        "topico":            topico,
        "tem_elemento_visual": False,
    }


# ══════════════════════════════════════════════════════════
#  TEMPLATES — SOLID
# ══════════════════════════════════════════════════════════

def gerar_solid_enunciado(rng):
    """Qual o enunciado de determinado princípio SOLID?"""
    sigla, nome, art, enunciado_p, violacao, armadilha = rng.choice(SOLID)

    CENARIOS = [
        f"Considere {art}, dos princípios SOLID.",
        f"Entre os princípios SOLID encontra-se {art}.",
        f"Um estudante revisa {art}.",
        f"A letra {sigla} da sigla SOLID corresponde {_com_preposicao('a', art)}.",
        f"Em uma revisão de código, aplica-se {art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta seu enunciado.",
        "Esse princípio estabelece que:",
        "Qual o enunciado desse princípio?",
        "Assinale a alternativa com a formulação correta.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = enunciado_p
    distratores = [s[3] for s in SOLID if s[3] != enunciado_p]
    distratores += [
        "toda classe deve implementar ao menos uma interface, para "
        "garantir testabilidade",
        "o acoplamento entre módulos deve ser eliminado por completo",
    ]

    explicacao = (
        f"{_inicial_maiuscula(art)}, representado pela letra {sigla}, "
        f"estabelece que {enunciado_p}. Uma violação típica é "
        f"{violacao}. Convém notar que {armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (SOLID)", rng)
    if q:
        q["_fato"] = f"solid:{sigla}"
    return q


def gerar_solid_por_violacao(rng):
    """
    Dada uma violação concreta, qual princípio foi ferido?

    É o formato que a prova cobra: reconhecer o problema no código, não
    recitar a sigla.
    """
    sigla, nome, art, enunciado_p, violacao, armadilha = rng.choice(SOLID)

    CENARIOS = [
        f"Durante a revisão de um sistema, identifica-se {violacao}.",
        f"Um code review aponta o seguinte problema: {violacao}.",
        f"A análise de um projeto revela {violacao}.",
        f"Em uma auditoria de código, encontra-se {violacao}.",
        f"O seguinte trecho de arquitetura chama atenção: {violacao}.",
    ]
    COMANDOS = [
        "Que princípio SOLID está sendo violado?",
        "Assinale a alternativa que indica o princípio ferido.",
        "Esse problema viola o princípio:",
        "Assinale a alternativa com o princípio desrespeitado.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = nome
    distratores = [s[1] for s in SOLID if s[1] != nome]
    distratores += ["menor privilégio", "coesão temporal"]

    explicacao = (
        f"A situação viola {art} ({sigla}), segundo o qual "
        f"{enunciado_p}. Convém notar que {armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (SOLID)", rng)
    if q:
        q["_fato"] = f"solid:{sigla}"
    return q


def gerar_solid_sigla(rng):
    """A que letra da sigla corresponde determinado princípio?"""
    sigla, nome, art, enunciado_p, violacao, armadilha = rng.choice(SOLID)
    modo = rng.choice(["letra_para_nome", "nome_para_letra"])

    if modo == "letra_para_nome":
        CENARIOS = [
            f"A sigla SOLID reúne cinco princípios de projeto orientado a "
            f"objetos. Considere a letra {sigla}.",
            f"Na sigla SOLID, a letra {sigla} identifica um princípio "
            f"específico.",
            f"Um estudante decora a sigla SOLID e chega à letra {sigla}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que a identifica.",
            "Essa letra corresponde ao princípio:",
            "Que princípio essa letra representa?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = nome
        distratores = [s[1] for s in SOLID if s[1] != nome]
        distratores += ["menor privilégio", "coesão funcional",
                        "ocultamento de informação"]
    else:
        CENARIOS = [
            f"Considere o princípio da {nome}, dos princípios SOLID.",
            f"Entre os cinco princípios SOLID está o da {nome}.",
            f"Um estudante associa cada princípio SOLID à sua letra e "
            f"chega ao da {nome}.",
        ]
        COMANDOS = [
            "Esse princípio corresponde à letra:",
            "Assinale a alternativa com a letra correspondente.",
            "Que letra da sigla o representa?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = sigla
        distratores = [s[0] for s in SOLID if s[0] != sigla]

    explicacao = (
        f"A letra {sigla} corresponde ao princípio da {nome}: "
        f"{enunciado_p}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (SOLID)", rng)
    if q:
        q["_fato"] = f"solid:{sigla}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — ORIENTAÇÃO A OBJETOS
# ══════════════════════════════════════════════════════════

def gerar_pilar_definicao(rng):
    """Qual pilar da orientação a objetos corresponde a certa definição?"""
    pilar, art, definicao, exemplo, armadilha = rng.choice(PILARES_POO)
    modo = rng.choice(["pela_definicao", "pelo_nome"])

    if modo == "pela_definicao":
        CENARIOS = [
            f"Um dos pilares da orientação a objetos consiste em "
            f"{definicao}.",
            f"Certo pilar da programação orientada a objetos é definido "
            f"como {definicao}.",
            f"Em projeto orientado a objetos, um princípio fundamental "
            f"consiste em {definicao}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que o identifica.",
            "Trata-se de:",
            "Esse pilar é:",
            "Que pilar corresponde a essa definição?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        # Os nomes dos pilares vão de 7 a 14 caracteres, e os
        # distratores inventados eram menores ainda. A estratégia
        # "marque a mais longa" acertava 48%.
        QUALIFICA_PILAR = {
        "abstração":      "abstração de dados",
        "encapsulamento": "encapsulamento de estado",
        "herança":        "herança entre classes",
        "polimorfismo":   "polimorfismo de subtipo",
    }
        correta = QUALIFICA_PILAR[pilar]
        distratores = [v for k, v in QUALIFICA_PILAR.items() if k != pilar]
        distratores += ["modularidade de pacotes", "coesão funcional",
                        "acoplamento aferente"]
    else:
        CENARIOS = [
            f"Considere {art}, um dos pilares da orientação a objetos.",
            f"Entre os quatro pilares da orientação a objetos encontra-se "
            f"{art}.",
            f"Um estudante revisa o conceito {_com_preposicao('de', art)}.",
        ]
        COMANDOS = [
            "Assinale a alternativa que o define corretamente.",
            "Esse pilar consiste em:",
            "Qual a definição correta?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = definicao
        distratores = [p[2] for p in PILARES_POO if p[2] != definicao]
        distratores += [
            "dividir o sistema em módulos independentes e substituíveis",
            "medir o grau de interdependência entre as classes",
        ]

    explicacao = (
        f"{_inicial_maiuscula(art)} consiste em {definicao}. Um exemplo é "
        f"{exemplo}. Convém notar que {armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (orientação a objetos)", rng)
    if q:
        q["_fato"] = f"pilar:{pilar}"
    return q


def gerar_pilar_por_exemplo(rng):
    """Dado um exemplo de código, qual pilar está em jogo?"""
    pilar, art, definicao, exemplo, armadilha = rng.choice(PILARES_POO)

    CENARIOS = [
        f"Em um sistema bancário, adota-se a seguinte prática: {exemplo}.",
        f"O projeto de uma aplicação inclui a seguinte decisão: {exemplo}.",
        f"Ao modelar um domínio, o desenvolvedor opta por {exemplo}.",
        f"Uma revisão de código encontra a seguinte construção: {exemplo}.",
    ]
    COMANDOS = [
        "Essa decisão ilustra qual pilar da orientação a objetos?",
        "Assinale a alternativa com o pilar correspondente.",
        "Trata-se de aplicação do pilar:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    QUALIFICA_PILAR = {
        "abstração":      "abstração de dados",
        "encapsulamento": "encapsulamento de estado",
        "herança":        "herança entre classes",
        "polimorfismo":   "polimorfismo de subtipo",
    }
    correta = QUALIFICA_PILAR[pilar]
    distratores = [v for k, v in QUALIFICA_PILAR.items() if k != pilar]
    distratores += ["modularidade de pacotes", "coesão funcional",
                    "reflexão em tempo de execução"]

    explicacao = (
        f"A prática ilustra {art}: {definicao}. Convém notar que "
        f"{armadilha}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (orientação a objetos)", rng)
    if q:
        q["_fato"] = f"pilar:{pilar}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — PADRÕES DE PROJETO
# ══════════════════════════════════════════════════════════

def gerar_categoria_gof(rng):
    """A que categoria GoF pertence determinado padrão?"""
    categoria, art, resolve, exemplos = rng.choice(CATEGORIAS_GOF)
    padrao = rng.choice(exemplos)

    CENARIOS = [
        f"Considere o padrão de projeto {padrao}, do catálogo GoF.",
        f"Entre os padrões descritos por Gamma, Helm, Johnson e "
        f"Vlissides encontra-se o {padrao}.",
        f"Um projeto adota o padrão {padrao}.",
        f"Um estudante classifica os padrões GoF e chega ao {padrao}.",
    ]
    COMANDOS = [
        "Esse padrão pertence à categoria:",
        "Assinale a alternativa com sua categoria.",
        "A que categoria ele pertence?",
        "Assinale a alternativa que o classifica corretamente.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = categoria
    distratores = [c[0] for c in CATEGORIAS_GOF if c[0] != categoria]
    distratores += ["arquitetural", "de concorrência", "de persistência"]

    explicacao = (
        f"O padrão {padrao} é {categoria}. Os padrões dessa categoria "
        f"tratam de {resolve}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (padrões de projeto)", rng)
    if q:
        q["_fato"] = f"gof:{categoria}"
    return q


def gerar_proposito_gof(rng):
    """O que cada categoria de padrão resolve?"""
    categoria, art, resolve, exemplos = rng.choice(CATEGORIAS_GOF)

    # Só três categorias, então a variação depende dos cenários: com
    # três cenários e três comandos, o template rendia 27 enunciados.
    CENARIOS = [
        f"O catálogo GoF divide os padrões em três categorias. Considere "
        f"{art}.",
        f"Entre as categorias de padrões de projeto encontram-se "
        f"{art}.",
        f"Um estudante revisa o propósito {_com_preposicao('de', art)}.",
        f"Ao classificar os padrões de projeto por finalidade, chega-se "
        f"{_com_preposicao('a', art)}.",
        f"Uma disciplina de engenharia de software aborda {art}.",
        f"O livro de Gamma e colegas agrupa parte dos padrões como "
        f"{art}.",
        f"Em uma revisão de arquitetura, discutem-se {art}.",
        f"A classificação clássica dos padrões de projeto inclui "
        f"{art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta o que eles resolvem.",
        "Esses padrões tratam de:",
        "Qual o propósito dessa categoria?",
        "Assinale a alternativa com a finalidade correta.",
        "A finalidade dessa categoria é tratar de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = resolve
    distratores = [c[2] for c in CATEGORIAS_GOF if c[2] != resolve]
    distratores += [
        "como o sistema é dividido em camadas de implantação",
        "como as exceções são propagadas entre os módulos",
        "como o desempenho é medido em tempo de execução",
    ]

    lista = ", ".join(exemplos[:3])
    explicacao = (
        f"{_inicial_maiuscula(art)} tratam de {resolve}. São exemplos: "
        f"{lista}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Engenharia de software (padrões de projeto)", rng)
    if q:
        q["_fato"] = f"gof:{categoria}"
    return q


# ══════════════════════════════════════════════════════════
#  REGISTRO
# ══════════════════════════════════════════════════════════

TEMPLATES_ENGENHARIA = {
    "solid_enunciado":    gerar_solid_enunciado,
    "solid_violacao":     gerar_solid_por_violacao,
    "solid_sigla":        gerar_solid_sigla,
    "pilar_definicao":    gerar_pilar_definicao,
    "pilar_exemplo":      gerar_pilar_por_exemplo,
    "categoria_gof":      gerar_categoria_gof,
    "proposito_gof":      gerar_proposito_gof,
}

TOPICOS_ENGENHARIA = {
    "solid": [
        "solid_enunciado",
        "solid_violacao",
        "solid_sigla",
    ],
    "orientacao_objetos": [
        "pilar_definicao",
        "pilar_exemplo",
    ],
    "padroes": [
        "categoria_gof",
        "proposito_gof",
    ],
}

PALAVRAS_CHAVE = {
    "solid_enunciado":  ["solid", "principios solid", "responsabilidade unica",
                         "aberto-fechado", "liskov", "segregacao de interface",
                         "inversao de dependencia", "clean code"],
    "solid_violacao":   ["solid", "principios solid", "code smell",
                         "refatoracao", "clean code", "liskov"],
    "solid_sigla":      ["solid", "principios solid", "clean code"],
    "pilar_definicao":  ["orientacao a objetos", "poo", "encapsulamento",
                         "heranca", "polimorfismo", "abstracao",
                         "programacao orientada a objetos"],
    "pilar_exemplo":    ["orientacao a objetos", "poo", "encapsulamento",
                         "heranca", "polimorfismo", "abstracao"],
    "categoria_gof":    ["padrao de projeto", "padroes de projeto",
                         "design pattern", "design patterns", "gof",
                         "singleton", "factory", "observer", "strategy",
                         "decorator", "adapter"],
    "proposito_gof":    ["padrao de projeto", "padroes de projeto",
                         "design pattern", "design patterns", "gof",
                         "padroes criacionais", "padroes estruturais",
                         "padroes comportamentais"],
}

CHAVES_GENERICAS = {
    "principio", "principios", "classe", "classes", "objeto", "objetos",
    "interface", "interfaces", "metodo", "metodos", "padrao", "padroes",
    "categoria", "codigo", "software",
}


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def templates_para_topicos(topicos):
    """Quais templates casam com os tópicos de um livro?"""
    texto = " " + " ".join(_normalizar(t) for t in (topicos or [])) + " "
    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        for chave in chaves:
            cn = _normalizar(chave)
            if cn in CHAVES_GENERICAS:
                continue
            if re.search(r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])',
                         texto):
                achados.append(nome)
                break
    return achados


def gerar_lote(quantidade: int = 10, seed: int = None,
               topico: str = None, templates: list = None):
    """Gera um lote de questões de engenharia de software."""
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_ENGENHARIA)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_ENGENHARIA]
        if pedidos:
            disponiveis = pedidos
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_ENGENHARIA.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_ENGENHARIA]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    LASTRO_POR_FATO = {
        "solid_enunciado": len(SOLID),
        "solid_violacao":  len(SOLID),
        "solid_sigla":     len(SOLID),
        "pilar_definicao": len(PILARES_POO),
        "pilar_exemplo":   len(PILARES_POO),
        "categoria_gof":   len(CATEGORIAS_GOF),
        "proposito_gof":   len(CATEGORIAS_GOF),
    }
    pesos = {n: max(1, min(round(LASTRO_POR_FATO.get(n, 3) / 3), 4))
             for n in disponiveis}
    fila = []
    for rodada in range(max(pesos.values())):
        for nome in disponiveis:
            if pesos[nome] > rodada:
                fila.append(nome)
    if not fila:
        fila = list(disponiveis)

    # A posição avança a cada TENTATIVA, não a cada questão aceita —
    # ver comentário equivalente nos demais geradores.
    posicao = 0
    questoes, tentativas, limite = [], 0, quantidade * 12
    vistos, fatos_usados = set(), set()

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = fila[posicao % len(fila)]
        posicao += 1
        q = TEMPLATES_ENGENHARIA[nome](rng)
        if not q:
            continue
        if q["enunciado"] in vistos and tentativas < limite * 0.8:
            continue

        fato = q.get("_fato")
        if fato and fato in fatos_usados and tentativas < limite * 0.9:
            continue

        vistos.add(q["enunciado"])
        if fato:
            fatos_usados.add(fato)
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade: int = 10, seed: int = None,
                   topico: str = None, templates: list = None):
    """Devolve (questoes, gabarito) no formato que a API espera."""
    lote = gerar_lote(quantidade, seed=seed, topico=topico, templates=templates)
    questoes, gabarito = [], []
    for q in lote:
        questoes.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": q["tem_elemento_visual"],
        })
        gabarito.append({
            "numero":           q["numero"],
            "resposta_correta": q["gabarito"],
            "explicacao":       q["explicacao"],
            "topico":           q["topico"],
            "_fato":            q.get("_fato", ""),
        })
    return questoes, gabarito


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    print("═" * 64)
    print("  GERADOR DE ENGENHARIA DE SOFTWARE")
    print("═" * 64)
    for q in gerar_lote(n, seed=2026):
        print(f"\n{q['numero']}. [{q['topico']}]")
        print(f"   {q['enunciado']}")
        for L, t in q["alternativas"].items():
            print(f"     {L}) {t}")
        print(f"   GABARITO: {q['gabarito']}")
        print(f"   {q['explicacao']}")
