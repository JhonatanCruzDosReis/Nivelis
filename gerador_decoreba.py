"""
=============================================================
  NIVELIS — Gerador de Questões Conceituais (memorização)
  Foco: ENADE — Computação
=============================================================

  Diferente dos outros geradores: aqui o Python NÃO calcula o
  gabarito — ele sorteia de uma TABELA DE FATOS.

  IMPLICAÇÃO IMPORTANTE
  ---------------------
  Nos geradores procedurais, o gabarito é correto por
  construção. Aqui, ele é tão correto quanto a tabela abaixo.
  Por isso cada fato foi conferido em fonte primária:

    • Portas TCP/UDP ....... IANA Service Name and Transport
                             Protocol Port Number Registry
    • Códigos HTTP ......... RFC 9110 (HTTP Semantics, 2022)
    • Camadas OSI .......... ISO/IEC 7498-1
    • Formas normais ....... literatura de BD (Elmasri/Navathe,
                             Date) e material acadêmico
    • Complexidades ........ literatura clássica de algoritmos

  A checagem de consistência interna está em
  teste_4_fatos.py — ela detecta duplicata contraditória,
  distrator que também é verdadeiro e resposta ambígua.

  Fatos que mudam com o tempo (versões de software, preços,
  valores de referência clínicos) foram DELIBERADAMENTE
  deixados de fora: para esses, use as rotas com IA apoiadas
  em livro indexado.

  USO:
    python gerador_decoreba.py            # 10 questões
    python gerador_decoreba.py 20 redes
=============================================================
"""

import sys
import re
import random

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "fracao", "simbolica", "codigo_numerico",
    "sequencia", "textual", "endereco_ip", "percentual", "monetaria",
}


# ══════════════════════════════════════════════════════════
#  TABELA DE FATOS — cada entrada verificada em fonte primária
# ══════════════════════════════════════════════════════════

# ── Portas padrão (fonte: IANA port registry) ──
PORTAS = [
    ("FTP (canal de controle)", 21),
    ("SSH",                     22),
    ("Telnet",                  23),
    ("SMTP",                    25),
    ("DNS",                     53),
    ("HTTP",                    80),
    ("POP3",                   110),
    ("IMAP",                   143),
    ("HTTPS",                  443),
    ("MySQL",                 3306),
    ("PostgreSQL",            5432),
    ("RDP",                   3389),
]

# ── Faixas de portas (fonte: RFC 6335) ──
FAIXAS_PORTAS = [
    ("portas bem conhecidas (system ports)",      "0 a 1023"),
    ("portas registradas (user ports)",           "1024 a 49151"),
    ("portas dinâmicas ou privadas",              "49152 a 65535"),
]

# ── Códigos HTTP (fonte: RFC 9110) ──
#
# A alternativa é "Nome — descrição", e os nomes já variam de 2
# ("OK") a 21 caracteres ("Internal Server Error"). Com as descrições
# antigas, a opção montada ia de 28 a 59 caracteres, e marcar a mais
# longa acertava as 15 questões em que a diferença era grande o
# bastante para se notar.
#
# As descrições foram reescritas para COMPENSAR o nome: nome curto
# ganha descrição mais longa e vice-versa. O fato não muda; o intervalo
# fecha em 38 a 55 caracteres, e o tamanho deixa de indicar coisa
# alguma.
HTTP_CODIGOS = [
    (200, "OK",                     "requisição processada com sucesso"),
    (201, "Created",                "novo recurso criado com sucesso"),
    (204, "No Content",             "sucesso sem corpo de resposta"),
    (301, "Moved Permanently",      "redirecionamento permanente"),
    (302, "Found",                  "redirecionamento temporário do recurso"),
    (400, "Bad Request",            "sintaxe inválida na requisição"),
    (401, "Unauthorized",           "falta de credenciais válidas"),
    (403, "Forbidden",              "servidor recusa autorizar a requisição"),
    (404, "Not Found",              "recurso não encontrado no servidor"),
    (405, "Method Not Allowed",     "método não permitido nesse recurso"),
    (409, "Conflict",               "conflito com o estado do recurso"),
    (429, "Too Many Requests",      "excesso de requisições no período"),
    (500, "Internal Server Error",  "erro interno genérico"),
    (501, "Not Implemented",        "funcionalidade não implementada"),
    (502, "Bad Gateway",            "resposta inválida do servidor upstream"),
    (503, "Service Unavailable",    "indisponível temporariamente"),
]

# ── Classes de código HTTP (fonte: RFC 9110) ──
HTTP_CLASSES = [
    ("1xx", "informativa"),
    ("2xx", "sucesso"),
    ("3xx", "redirecionamento"),
    ("4xx", "erro do cliente"),
    ("5xx", "erro do servidor"),
]

# ── Camadas OSI (fonte: ISO/IEC 7498-1) ──
OSI = [
    (1, "Física",        "transmissão de bits pelo meio físico",              "bit"),
    (2, "Enlace",        "controle de acesso ao meio e detecção de erros",    "quadro"),
    (3, "Rede",          "endereçamento lógico e roteamento entre redes",     "pacote"),
    (4, "Transporte",    "entrega fim a fim, controle de fluxo e de erros",   "segmento"),
    (5, "Sessão",        "estabelecimento e encerramento de sessões",         "dados"),
    (6, "Apresentação",  "tradução, compressão e criptografia dos dados",     "dados"),
    (7, "Aplicação",     "interface entre os aplicativos e a rede",           "dados"),
]

# ── Protocolo → camada OSI (consenso da literatura) ──
PROTOCOLO_CAMADA = [
    ("IP",       3, "Rede"),
    ("ICMP",     3, "Rede"),
    ("TCP",      4, "Transporte"),
    ("UDP",      4, "Transporte"),
    ("HTTP",     7, "Aplicação"),
    ("SMTP",     7, "Aplicação"),
    ("DNS",      7, "Aplicação"),
    ("FTP",      7, "Aplicação"),
    ("Ethernet", 2, "Enlace"),
]

# ── Formas normais (fonte: literatura de BD) ──
FORMAS_NORMAIS = [
    ("1FN", "eliminar atributos multivalorados e compostos, garantindo valores atômicos"),
    ("2FN", "estar na 1FN e eliminar dependências funcionais parciais da chave primária"),
    ("3FN", "estar na 2FN e eliminar dependências funcionais transitivas entre atributos não chave"),
]

# ── Propriedades ACID (fonte: literatura de BD) ──
# (nome, artigo definido, descrição) — o artigo acompanha o termo para
# evitar "a Isolamento". Atomicidade/Consistência/Durabilidade são
# femininos; Isolamento é masculino.
ACID = [
    ("Atomicidade",  "a", "a transação é executada integralmente ou não é executada"),
    ("Consistência", "a", "a transação leva o banco de um estado válido a outro estado válido"),
    ("Isolamento",   "o", "transações concorrentes não interferem umas nas outras"),
    ("Durabilidade", "a", "os efeitos de uma transação confirmada persistem mesmo após falhas"),
]

# ── Comandos SQL por categoria (consenso da literatura) ──
SQL_CATEGORIAS = [
    ("DDL", "Linguagem de Definição de Dados",  ["CREATE", "ALTER", "DROP", "TRUNCATE"]),
    ("DML", "Linguagem de Manipulação de Dados", ["INSERT", "UPDATE", "DELETE", "SELECT"]),
    ("DCL", "Linguagem de Controle de Dados",   ["GRANT", "REVOKE"]),
    ("DTL", "Linguagem de Transação de Dados",  ["COMMIT", "ROLLBACK", "SAVEPOINT"]),
]

# ── Complexidades de algoritmos clássicos (literatura de algoritmos) ──
COMPLEXIDADES = [
    ("Busca binária em vetor ordenado",        "pior caso",  "O(log n)"),
    ("Busca linear em vetor não ordenado",     "pior caso",  "O(n)"),
    ("Merge Sort",                             "pior caso",  "O(n log n)"),
    ("Heap Sort",                              "pior caso",  "O(n log n)"),
    ("Quick Sort",                             "caso médio", "O(n log n)"),
    ("Quick Sort",                             "pior caso",  "O(n²)"),
    ("Bubble Sort",                            "pior caso",  "O(n²)"),
    ("Insertion Sort",                         "pior caso",  "O(n²)"),
    ("Selection Sort",                         "pior caso",  "O(n²)"),
    ("Acesso a elemento de vetor por índice",  "pior caso",  "O(1)"),
    ("Busca em tabela hash sem colisões",      "caso médio", "O(1)"),
]

# ── Estruturas de dados: política de acesso ──
ESTRUTURAS = [
    ("Pilha",              "LIFO — o último elemento inserido é o primeiro a sair"),
    ("Fila",               "FIFO — o primeiro elemento inserido é o primeiro a sair"),
    ("Fila de prioridade", "o elemento de maior prioridade é retirado primeiro"),
    ("Lista ligada",       "os elementos são encadeados por ponteiros, sem posições contíguas"),
]

# ── Percursos em árvore binária ──
PERCURSOS = [
    ("pré-ordem", "raiz, subárvore esquerda, subárvore direita"),
    ("em ordem",  "subárvore esquerda, raiz, subárvore direita"),
    ("pós-ordem", "subárvore esquerda, subárvore direita, raiz"),
]

# ── Paradigmas de programação ──
# As descrições ficam em INFINITIVO para encaixarem depois de "consiste em".
# Com verbo conjugado ("baseia-se em funções puras") saía "que consiste em
# baseia-se em funções puras".
PARADIGMAS = [
    ("Programação orientada a objetos", "organizar o sistema em objetos que reúnem estado e comportamento"),
    ("Programação funcional",           "estruturar o programa com funções puras, evitando estado mutável"),
    ("Programação imperativa",          "descrever a computação como uma sequência de comandos que alteram o estado"),
    ("Programação lógica",              "expressar a computação como fatos e regras avaliados por inferência"),
]

# ── Pilares da orientação a objetos ──
PILARES_OO = [
    ("Encapsulamento", "ocultar os detalhes internos e expor apenas uma interface controlada"),
    ("Herança",        "permitir que uma classe reaproveite atributos e métodos de outra"),
    ("Polimorfismo",   "permitir que uma mesma operação se comporte de formas diferentes conforme o objeto"),
    ("Abstração",      "representar apenas as características essenciais, omitindo detalhes irrelevantes"),
]

# ── Metodologias ágeis: papéis e artefatos do Scrum (Scrum Guide) ──
SCRUM = [
    ("Product Owner",     "responsável por maximizar o valor do produto e gerenciar o Product Backlog"),
    ("Scrum Master",      "responsável por promover e apoiar o Scrum, removendo impedimentos"),
    ("Product Backlog",   "lista ordenada de tudo que é necessário no produto"),
    ("Sprint Backlog",    "conjunto de itens selecionados para a Sprint, mais o plano para entregá-los"),
    ("Sprint Review",     "evento ao final da Sprint para inspecionar o incremento e adaptar o backlog"),
    ("Sprint Retrospective", "evento para inspecionar o processo e planejar melhorias na próxima Sprint"),
]


# ──────────────────────────────────────────
#  MONTAGEM
# ──────────────────────────────────────────

def _juntar(anterior: str, seguinte: str) -> str:
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=str, tipo_resposta="textual", fato=None):
    assert tipo_resposta in TIPOS_RESPOSTA
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
    return {
        "enunciado":      enunciado,
        "alternativas":   {L: formatador(v) for L, v in zip(LETRAS, valores)},
        "gabarito":       LETRAS[valores.index(correta)],
        "explicacao":     explicacao,
        "topico":         topico,
        "origem":         "gerador_decoreba",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
        # A chave do FATO é a linha da tabela, não a resposta.
        #
        # Quase todo template daqui é bidirecional: sorteia entre pedir o
        # nome a partir da definição e a definição a partir do nome. São
        # a mesma coisa sabida, com respostas diferentes — e sem esta
        # chave o simulado aceitava as duas, porque o veto de repetição
        # do montador só via tópico e resposta. Um caderno de engenharia
        # saiu com nove questões de Scrum, quatro delas pares invertidos.
        "_fato":          fato or f"{topico}:{correta}",
    }


# ══════════════════════════════════════════
#  REDES E PROTOCOLOS
# ══════════════════════════════════════════

def gerar_porta_padrao(rng):
    """Porta padrão de um serviço (fonte: registro IANA)."""
    for _ in range(50):
        servico, porta = rng.choice(PORTAS)
        outras = [p for s, p in PORTAS if p != porta]
        rng.shuffle(outras)

        CEN = [
            f"Ao configurar um firewall, um administrador precisa liberar o "
            f"tráfego do serviço {servico}.",
            f"Durante a análise de um servidor, identificou-se a necessidade de "
            f"verificar o serviço {servico}.",
            f"Um técnico documenta as portas utilizadas pelos serviços de rede "
            f"da empresa, entre eles o {servico}.",
            f"Na configuração de um servidor, é preciso informar a porta padrão "
            f"do serviço {servico}.",
        ]
        PER = [
            f"Qual é a porta padrão registrada para o {servico}?",
            f"A porta padrão desse serviço é:",
            f"Qual porta deve ser considerada como padrão para esse serviço?",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        explicacao = (
            f"Segundo o registro de portas e nomes de serviços mantido pela "
            f"IANA, a porta padrão associada ao {servico} é a {porta}."
        )
        q = _montar(enunciado, porta, outras, explicacao,
                    "Redes (portas e serviços)", rng, tipo_resposta="numerica",
                    fato=f"porta:{servico}")
        if q:
            return q
    raise RuntimeError("porta_padrao")


def gerar_camada_osi(rng):
    """Camada OSI, sua função ou sua PDU (fonte: ISO/IEC 7498-1)."""
    for _ in range(50):
        modo = rng.choice(["funcao", "numero", "pdu", "protocolo"])

        if modo == "funcao":
            num, nome, funcao, _ = rng.choice(OSI)
            correta = nome
            distratores = [n for _, n, _, _ in OSI if n != nome]
            CEN = ["No modelo de referência OSI, uma das camadas é responsável "
                   f"por {funcao}.",
                   f"Entre as sete camadas do modelo OSI, uma tem como função {funcao}.",
                   f"O modelo OSI atribui a uma de suas camadas a responsabilidade "
                   f"de {funcao}."]
            PER = ["Trata-se da camada:", "Qual é essa camada?",
                   "Essa descrição corresponde à camada:"]
            explicacao = (f"No modelo OSI, a camada {nome} (nível {num}) é a "
                          f"responsável por {funcao}.")
        elif modo == "numero":
            num, nome, funcao, _ = rng.choice(OSI)
            correta = num
            distratores = [n for n, _, _, _ in OSI if n != num]

            # O contexto NÃO pode citar a camada perguntada como exemplo — se
            # a pergunta for sobre a Física e o texto disser "sendo a Física o
            # nível 1", o enunciado entrega a resposta.
            CEN = [
                "No modelo de referência OSI, as camadas são numeradas da mais "
                "próxima do meio físico até a mais próxima do usuário.",
                "O modelo OSI organiza a comunicação de rede em sete camadas "
                "hierárquicas, numeradas de 1 a 7.",
                "A pilha de protocolos do modelo OSI é dividida em sete níveis, "
                "cada um com responsabilidades próprias.",
            ]
            # "camada Física", não "camada de Física" — o nome é adjetivo.
            # Já "camada de Rede/Transporte/Sessão" pede a preposição.
            artigo = "" if nome in ("Física", "Aplicação") else "de "
            PER = [f"Qual é o número da camada {artigo}{nome}?",
                   f"A camada {artigo}{nome} corresponde a qual nível?",
                   f"Que nível ocupa a camada {artigo}{nome}?"]
            explicacao = (f"Na numeração do modelo OSI, a camada {artigo}{nome} "
                          f"ocupa o nível {num}.")
            return _montar(f"{rng.choice(CEN)} {rng.choice(PER)}", correta,
                           distratores, explicacao, "Redes (modelo OSI)", rng,
                           tipo_resposta="numerica", fato=f"osi:{nome}")
        elif modo == "pdu":
            candidatos = [(n, nm, p) for n, nm, _, p in OSI if p != "dados"]
            num, nome, pdu = rng.choice(candidatos)
            correta = pdu
            distratores = [p for _, _, _, p in OSI if p != pdu] + ["byte", "octeto"]
            CEN = [f"Cada camada do modelo OSI manipula uma unidade de dados "
                   f"de protocolo (PDU) específica."]
            artigo = "" if nome in ("Física", "Aplicação") else "de "
            PER = [f"Qual é a PDU tratada pela camada {artigo}{nome}?",
                   f"A unidade de dados da camada {artigo}{nome} é denominada:"]
            explicacao = (f"A unidade de dados de protocolo (PDU) da camada "
                          f"{artigo}{nome} é o {pdu}.")
        else:
            proto, num, nome = rng.choice(PROTOCOLO_CAMADA)
            correta = nome
            distratores = [n for _, n, _, _ in OSI if n != nome]
            CEN = [f"Os protocolos de rede são classificados conforme a camada "
                   f"do modelo OSI em que atuam.",
                   f"Ao estudar a pilha de protocolos, é comum associar cada "
                   f"protocolo à camada OSI correspondente."]
            PER = [f"Em qual camada do modelo OSI o protocolo {proto} atua?",
                   f"O protocolo {proto} pertence a qual camada?"]
            artigo = "" if nome in ("Física", "Aplicação") else "de "
            explicacao = (f"O protocolo {proto} atua na camada {artigo}{nome} "
                          f"(nível {num}) do modelo OSI.")

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (modelo OSI)", rng, fato=f"osi:{nome}")
        if q:
            return q
    raise RuntimeError("camada_osi")


def gerar_codigo_http(rng):
    """Significado de código HTTP (fonte: RFC 9110)."""
    for _ in range(50):
        modo = rng.choice(["codigo_para_nome", "nome_para_codigo", "classe"])

        if modo == "codigo_para_nome":
            cod, nome, desc = rng.choice(HTTP_CODIGOS)
            correta = f"{nome} — {desc}"
            distratores = [f"{n} — {d}" for c, n, d in HTTP_CODIGOS if c != cod]
            CEN = [f"Ao consumir uma API REST, um desenvolvedor recebeu a "
                   f"resposta com código de status {cod}.",
                   f"O log de um servidor web registrou diversas respostas com "
                   f"status HTTP {cod}.",
                   f"Durante o teste de uma requisição, o servidor retornou o "
                   f"código {cod}."]
            PER = ["Segundo a especificação HTTP, esse código indica:",
                   "Qual é o significado desse código de status?",
                   "Esse status corresponde a:"]
            explicacao = (f"Conforme a RFC 9110, que define a semântica do HTTP, "
                          f"o código {cod} corresponde a {nome}, indicando "
                          f"{desc}.")
        elif modo == "nome_para_codigo":
            cod, nome, desc = rng.choice(HTTP_CODIGOS)
            correta = cod
            distratores = [c for c, _, _ in HTTP_CODIGOS if c != cod]
            CEN = [f"Uma API deve responder adequadamente quando ocorre a "
                   f"seguinte situação: {desc}.",
                   f"Ao projetar um serviço web, define-se o status a retornar "
                   f"quando há {desc}."]
            PER = ["Qual código de status HTTP deve ser utilizado?",
                   "O código apropriado para essa situação é:"]
            explicacao = (f"Pela RFC 9110, a situação descrita corresponde ao "
                          f"código {cod} ({nome}).")
            cen = rng.choice(CEN)
            enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
            q = _montar(enunciado, correta, distratores, explicacao,
                        "Web (códigos HTTP)", rng, tipo_resposta="numerica",
                        fato=f"http:{cod}")
            if q:
                return q
            continue
        else:
            classe, sentido = rng.choice(HTTP_CLASSES)
            cod = f"classe {classe}"
            correta = sentido
            distratores = [s for c, s in HTTP_CLASSES if c != classe]
            CEN = [f"Os códigos de status HTTP são agrupados em famílias "
                   f"identificadas pelo primeiro dígito.",
                   f"A especificação HTTP organiza os códigos de status em "
                   f"cinco classes."]
            PER = [f"A classe {classe} indica respostas do tipo:",
                   f"Códigos da faixa {classe} representam:"]
            explicacao = (f"Segundo a RFC 9110, os códigos da classe {classe} "
                          f"indicam {sentido}.")

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Web (códigos HTTP)", rng, fato=f"http:{cod}")
        if q:
            return q
    raise RuntimeError("codigo_http")


# ══════════════════════════════════════════
#  BANCO DE DADOS
# ══════════════════════════════════════════

def gerar_forma_normal(rng):
    """Definição das formas normais (literatura de BD)."""
    for _ in range(50):
        fn, criterio = rng.choice(FORMAS_NORMAIS)
        correta = criterio
        distratores = [c for f, c in FORMAS_NORMAIS if f != fn] + [
            "estar na 3FN e eliminar dependências multivaloradas",
            "garantir que toda dependência funcional tenha uma superchave como determinante",
        ]
        CEN = [
            "A normalização de bancos de dados relacionais é aplicada em etapas "
            "sucessivas para reduzir redundância e anomalias.",
            "No projeto de um banco relacional, as formas normais são aplicadas "
            "progressivamente sobre as relações.",
            "Ao normalizar um esquema relacional, cada forma normal impõe uma "
            "exigência adicional sobre a anterior.",
            "Durante a modelagem do banco, a equipe aplica as formas normais em sequência.",
            "Um DBA revisa o esquema legado para verificar em qual forma normal ele se encontra.",
            "Ao eliminar redundâncias de uma tabela, o analista avança pelas formas normais.",
            "O projeto lógico do banco exige justificar a forma normal atingida por cada tabela.",
        ]
        PER = [f"Para que uma relação esteja na {fn}, é necessário:",
               f"O critério que define a {fn} é:",
               f"Uma tabela atende à {fn} quando se consegue:"]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        explicacao = (f"A {fn} exige {criterio}.")
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Banco de dados (normalização)", rng, fato=f"fn:{fn}")
        if q:
            return q
    raise RuntimeError("forma_normal")


def gerar_acid(rng):
    """Propriedades ACID de transações."""
    for _ in range(50):
        prop, art, desc = rng.choice(ACID)
        inverso = rng.random() < 0.5
        if inverso:
            correta = prop
            distratores = [p for p, _, _ in ACID if p != prop] + ["Concorrência", "Persistência"]
            PER = [f"A propriedade que garante que {desc} é:",
                   f"Qual propriedade ACID assegura que {desc}?"]
            explicacao = (f"Entre as propriedades ACID, {art} {prop} é quem garante "
                          f"que {desc}.")
        else:
            correta = desc
            distratores = [d for p, _, d in ACID if p != prop]
            PER = [f"A propriedade de {prop} garante que:",
                   f"O que assegura {art} {prop} em uma transação?"]
            explicacao = (f"A propriedade de {prop} garante que {desc}.")

        CEN = [
            "Os sistemas gerenciadores de bancos de dados relacionais garantem "
            "quatro propriedades no processamento de transações, conhecidas "
            "pelo acrônimo ACID.",
            "O controle de transações em um SGBD apoia-se nas propriedades ACID.",
            "Em bancos de dados transacionais, o acrônimo ACID resume quatro "
            "garantias fundamentais.",
            "Durante a auditoria de um sistema bancário, a equipe revisou como o SGBD assegura as propriedades ACID.",
            "Um analista precisa justificar a escolha de um banco relacional destacando as garantias ACID.",
            "Ao projetar o módulo de pagamentos, a equipe mapeou quais propriedades ACID sustentam cada requisito.",
            "Em uma revisão de arquitetura, discutiu-se qual propriedade ACID responde por determinada garantia.",
            "O documento de requisitos não funcionais cita as propriedades ACID como critério de escolha do banco.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Banco de dados (transações)", rng, fato=f"acid:{prop}")
        if q:
            return q
    raise RuntimeError("acid")


def gerar_sql_categoria(rng):
    """Classificação de comandos SQL em DDL, DML, DCL e DTL."""
    for _ in range(50):
        sigla, nome, comandos = rng.choice(SQL_CATEGORIAS)
        cmd = rng.choice(comandos)
        # garante que o comando pertence a UMA categoria só
        outras_cats = [(s, n) for s, n, cs in SQL_CATEGORIAS
                       if s != sigla and cmd not in cs]
        if len(outras_cats) < 3:
            continue

        modo = rng.choice(["comando_para_cat", "cat_para_nome"])
        if modo == "comando_para_cat":
            correta = sigla
            distratores = [s for s, _ in outras_cats] + ["DQL"]
            CEN = [f"Os comandos da linguagem SQL são agrupados em subconjuntos "
                   f"conforme sua finalidade.",
                   f"A SQL divide seus comandos em categorias de acordo com a "
                   f"operação que realizam."]
            PER = [f"O comando {cmd} pertence a qual subconjunto da SQL?",
                   f"Em qual categoria da SQL se enquadra o comando {cmd}?"]
            explicacao = (f"O comando {cmd} faz parte da {sigla} "
                          f"({nome}).")
        else:
            correta = nome
            distratores = [n for _, n in outras_cats] + ["Linguagem de Consulta de Dados"]
            CEN = ["Os comandos SQL são agrupados em subconjuntos identificados "
                   "por siglas de três letras."]
            PER = [f"A sigla {sigla} corresponde a:",
                   f"O subconjunto {sigla} da SQL é denominado:"]
            explicacao = (f"A sigla {sigla} designa a {nome}, que reúne comandos "
                          f"como {', '.join(comandos[:3])}.")

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Banco de dados (SQL)", rng, fato=f"sql:{sigla}")
        if q:
            return q
    raise RuntimeError("sql_categoria")


# ══════════════════════════════════════════
#  ALGORITMOS E ESTRUTURAS
# ══════════════════════════════════════════

def gerar_complexidade_decoreba(rng):
    """Complexidade de algoritmos clássicos (memorização)."""
    TODAS = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(2^n)", "O(n!)"]
    for _ in range(50):
        alg, caso, correta = rng.choice(COMPLEXIDADES)
        distratores = [o for o in TODAS if o != correta]
        rng.shuffle(distratores)

        CEN = [
            f"Ao estudar o desempenho de algoritmos clássicos, é fundamental "
            f"conhecer sua ordem de complexidade.",
            f"A análise assintótica permite comparar algoritmos independentemente "
            f"do hardware utilizado.",
            f"Em uma revisão de algoritmos fundamentais, discute-se o custo "
            f"computacional de cada um.",
        ]
        # Não usar .lower() no nome: "Bubble Sort" é nome próprio e viraria
        # "bubble Sort". As frases foram redigidas para aceitar a inicial maiúscula.
        PER = [f"Qual é a complexidade de tempo do algoritmo {alg}, no {caso}, "
               f"para uma entrada de tamanho n?",
               f"No {caso}, o algoritmo {alg} apresenta complexidade de tempo:",
               f"A complexidade de tempo do algoritmo {alg}, no {caso}, é:"]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (f"A literatura de algoritmos estabelece que {alg} tem "
                      f"complexidade {correta} no {caso}.")
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Algoritmos (complexidade)", rng, tipo_resposta="simbolica",
                    fato=f"complexidade:{alg}:{caso}")
        if q:
            return q
    raise RuntimeError("complexidade_decoreba")


def gerar_estrutura_politica(rng):
    """Política de acesso de estruturas de dados e percursos em árvore."""
    for _ in range(50):
        modo = rng.choice(["estrutura", "percurso"])

        if modo == "estrutura":
            nome, desc = rng.choice(ESTRUTURAS)
            _chave_ed = f"estrutura:{nome}"
            inverso = rng.random() < 0.5
            if inverso:
                correta = nome
                distratores = [n for n, _ in ESTRUTURAS if n != nome] + ["Árvore binária", "Grafo"]
                PER = [f"A estrutura de dados cuja política é '{desc}' é:",
                       f"Qual estrutura de dados adota a seguinte política: {desc}?"]
            else:
                correta = desc
                distratores = [d for n, d in ESTRUTURAS if n != nome]
                PER = [f"A política de acesso de uma {nome.lower()} é:",
                       f"Qual descrição corresponde ao funcionamento de uma {nome.lower()}?"]
            explicacao = (f"A estrutura {nome} caracteriza-se por: {desc}.")
            CEN = ["As estruturas de dados lineares diferenciam-se pela política "
                   "de inserção e remoção de elementos.",
                   "Cada estrutura de dados define uma ordem específica para "
                   "acesso aos seus elementos.""Ao dimensionar a estrutura de dados de um módulo, o desenvolvedor considera a política de acesso.",
                   "Em uma prova de algoritmos, pede-se identificar a estrutura pela sua política de remoção.",
                   "Durante a implementação de um buffer, discutiu-se qual estrutura atende ao requisito.",
                   "A escolha entre estruturas lineares depende da ordem em que os elementos saem.",
                   ]
        else:
            nome, ordem = rng.choice(PERCURSOS)
            _chave_ed = f"percurso:{nome}"
            inverso = rng.random() < 0.5
            if inverso:
                correta = nome
                distratores = [n for n, _ in PERCURSOS if n != nome] + [
                    "em largura", "por nível"]
                PER = [f"O percurso que visita os nós na ordem '{ordem}' é chamado:",
                       f"Qual percurso segue a sequência {ordem}?"]
            else:
                correta = ordem
                distratores = [o for n, o in PERCURSOS if o != ordem] + [
                    "raiz, subárvore direita, subárvore esquerda"]
                PER = [f"No percurso {nome}, a ordem de visita dos nós é:",
                       f"O percurso {nome} visita os nós na seguinte ordem:"]
            explicacao = (f"No percurso {nome} de uma árvore binária, a ordem de "
                          f"visita é: {ordem}.")
            CEN = ["Os percursos em profundidade de árvores binárias diferem "
                   "pela posição em que a raiz é visitada.",
                   "Existem três percursos clássicos em profundidade para "
                   "árvores binárias."]

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Estruturas de dados (conceitos)", rng, fato=_chave_ed)
        if q:
            return q
    raise RuntimeError("estrutura_politica")


# ══════════════════════════════════════════
#  ENGENHARIA DE SOFTWARE
# ══════════════════════════════════════════

def gerar_paradigma_oo(rng):
    """Paradigmas de programação e pilares da orientação a objetos."""
    for _ in range(50):
        usar_pilar = rng.random() < 0.55
        tabela = PILARES_OO if usar_pilar else PARADIGMAS
        rotulo = "pilar da orientação a objetos" if usar_pilar else "paradigma de programação"

        nome, desc = rng.choice(tabela)
        inverso = rng.random() < 0.5
        if inverso:
            correta = nome
            distratores = [n for n, _ in tabela if n != nome]
            if usar_pilar:
                distratores += ["Composição", "Sobrecarga"]
            else:
                distratores += ["Programação concorrente", "Programação estruturada"]
            PER = [f"O {rotulo} que consiste em {desc} é:",
                   f"Qual {rotulo} corresponde a {desc}?"]
        else:
            correta = desc
            distratores = [d for n, d in tabela if d != desc]
            # Ambos os comandos pedem infinitivo, que é a forma das descrições
            PER = [f"{nome} consiste em:",
                   f"O conceito de {nome} pode ser definido como:"]
        explicacao = f"{nome} consiste em {desc}."
        # Contextos alternativos, para variar a redação sem inventar
        # conteúdo: a tabela de paradigmas tem só 4 entradas, e sem isso
        # o template rendia apenas 16 enunciados distintos.
        #
        # Todos terminam em ponto e substituem o cenário padrão — mais
        # simples que emendar prefixo, que exigia ajustar a caixa da
        # primeira letra e produzia "projeto, A orientação a objetos".
        if usar_pilar:
            CEN = [
                "A orientação a objetos apoia-se em pilares que organizam o "
                "projeto do software.",
                "Ao revisar a modelagem de classes, a equipe retomou os "
                "pilares da orientação a objetos.",
                "Num processo seletivo para desenvolvedor, cobram-se os "
                "pilares da orientação a objetos.",
                "A documentação de arquitetura descreve como cada pilar da "
                "orientação a objetos foi aplicado.",
                "Durante o code review, discutiu-se qual pilar da orientação "
                "a objetos sustenta determinada decisão.",
            ]
        else:
            CEN = [
                "Os paradigmas de programação definem formas distintas de "
                "estruturar a solução de um problema.",
                "Ao escolher a linguagem de um novo projeto, a equipe "
                "comparou os paradigmas disponíveis.",
                "Em uma disciplina de linguagens de programação, discutem-se "
                "os diferentes paradigmas.",
                "A modernização de um sistema legado exigiu identificar o "
                "paradigma originalmente adotado.",
                "Na definição do padrão de código da equipe, avaliou-se qual "
                "paradigma orienta a solução.",
            ]

        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Engenharia de software (paradigmas)", rng,
                    fato=f"{'pilar' if usar_pilar else 'paradigma'}:{nome}")
        if q:
            return q
    raise RuntimeError("paradigma_oo")


def gerar_scrum(rng):
    """Papéis, artefatos e eventos do Scrum."""
    for _ in range(50):
        nome, desc = rng.choice(SCRUM)
        inverso = rng.random() < 0.5
        if inverso:
            correta = nome
            distratores = [n for n, _ in SCRUM if n != nome]
            PER = [f"No Scrum, {'o papel' if 'Owner' in nome or 'Master' in nome else 'o elemento'} "
                   f"responsável por/descrito como '{desc}' é:",
                   f"Qual elemento do Scrum corresponde a: {desc}?"]
        else:
            correta = desc
            distratores = [d for n, d in SCRUM if d != desc]
            PER = [f"No Scrum, o que caracteriza o {nome}?",
                   f"O {nome} é definido como:"]
        explicacao = f"No Scrum, o {nome} é {desc}."
        CEN = [
            "O Scrum define papéis, artefatos e eventos com responsabilidades "
            "bem delimitadas.",
            "A estrutura do Scrum organiza o trabalho em papéis, artefatos e "
            "eventos específicos.",
            "Durante a adoção de métodos ágeis, a equipe estuda os papéis e eventos do Scrum.",
            "Em uma certificação ágil, cobra-se o domínio dos elementos do framework Scrum.",
            "Ao estruturar o time, o gestor define quem responde por cada responsabilidade no Scrum.",
            "A retrospectiva do time revisitou o propósito de cada cerimônia do Scrum.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {_juntar(cen, rng.choice(PER))}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Engenharia de software (ágil)", rng, fato=f"scrum:{nome}")
        if q:
            return q
    raise RuntimeError("scrum")


# ──────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────

TEMPLATES_DECOREBA = {
    "porta_padrao":          gerar_porta_padrao,
    "camada_osi":            gerar_camada_osi,
    "codigo_http":           gerar_codigo_http,
    "forma_normal":          gerar_forma_normal,
    "acid":                  gerar_acid,
    "sql_categoria":         gerar_sql_categoria,
    "complexidade_conceito": gerar_complexidade_decoreba,
    "estrutura_politica":    gerar_estrutura_politica,
    "paradigma_oo":          gerar_paradigma_oo,
    "scrum":                 gerar_scrum,
}

TOPICOS_DECOREBA = {
    "redes":         ["porta_padrao", "camada_osi", "codigo_http"],
    "banco_dados":   ["forma_normal", "acid", "sql_categoria"],
    "algoritmos":    ["complexidade_conceito", "estrutura_politica"],
    "eng_software":  ["paradigma_oo", "scrum"],
}

PALAVRAS_CHAVE = {
    "porta_padrao":          ["porta", "protocolo", "servico de rede", "firewall",
                              "tcp", "udp", "redes"],
    "camada_osi":            ["osi", "camada", "modelo de referencia", "pilha de protocolos",
                              "redes", "tcp/ip"],
    "codigo_http":           ["http", "status", "codigo de resposta", "rest",
                              "api", "web"],
    "forma_normal":          ["normalizacao", "forma normal", "1fn", "2fn", "3fn",
                              "dependencia funcional", "banco de dados"],
    "acid":                  ["acid", "transacao", "atomicidade", "isolamento",
                              "durabilidade", "banco de dados", "sgbd"],
    "sql_categoria":         ["sql", "ddl", "dml", "dcl", "comando", "banco de dados"],
    "complexidade_conceito": ["complexidade", "big-o", "assintotic", "analise de algoritmo",
                              "ordenacao", "busca"],
    "estrutura_politica":    ["pilha", "fila", "lifo", "fifo", "arvore", "percurso",
                              "estrutura de dados"],
    "paradigma_oo":          ["orientacao a objetos", "paradigma", "encapsulamento",
                              "heranca", "polimorfismo", "abstracao", "programacao"],
    "scrum":                 ["scrum", "agil", "sprint", "product owner", "backlog",
                              "metodologia", "gerencia de projeto"],
}


# Siglas e termos curtos que colidem com outras áreas.
CHAVES_GENERICAS = {
    "porta", "camada", "status", "comando", "complexidade", "pilha",
    "fila", "arvore", "percurso", "paradigma", "agil", "sprint",
    "normalizacao", "transacao", "protocolo", "cabimento",
    # "porta de entrada do SUS", "protocolo de acolhimento", "fila de
    # espera" — todas existem fora de TI, e duas genéricas juntas
    # bastavam para acionar o gerador.
    "rede", "redes", "acesso", "servico", "servicos", "fluxo",
    "classificacao", "modelo", "estrutura", "processo", "gestao",
    "camada", "protocolo", "porta",
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

def gerar_lote(quantidade=10, topico=None, templates=None, seed=None):
    rng = random.Random(seed)
    if templates:
        nomes = [n for n in templates if n in TEMPLATES_DECOREBA]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
    elif topico:
        nomes = TOPICOS_DECOREBA.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS_DECOREBA)}")
    else:
        nomes = list(TEMPLATES_DECOREBA)

    funcoes = [TEMPLATES_DECOREBA[n] for n in nomes]
    rng.shuffle(funcoes)

    # O laço anterior aceitava a PRIMEIRA questão de cada template, sem
    # filtro: pedir 12 questões com 10 templates devolvia dois tópicos
    # repetidos, e às vezes o mesmo enunciado.
    #
    # Agora rejeita enunciado repetido e tópico já usado, afrouxando
    # perto do limite de tentativas — melhor alguma repetição que lote
    # incompleto.
    questoes = []
    vistos, fatos_usados, topicos_usados = set(), set(), set()
    tentativas, limite = 0, quantidade * 12

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        q = funcoes[tentativas % len(funcoes)](rng)
        if not q:
            continue

        if q["enunciado"] in vistos and tentativas < limite * 0.9:
            continue

        # ── veto pelo FATO, não só pelo enunciado ──
        #
        # Comparar enunciado deixava passar a mesma informação reescrita:
        # "cada forma normal impõe uma exigência..." e "as formas normais
        # são aplicadas progressivamente..." são textos diferentes com a
        # mesma resposta, e o usuário respondia duas vezes a mesma coisa.
        #
        # Medindo num lote de 60, treze fatos saíam repetidos assim; numa
        # sessão de 15, um. Os outros geradores já vetavam pelo fato — este
        # era o único que não.
        #
        # Afrouxa a 85% das tentativas, antes do afrouxamento do enunciado:
        # lote completo com alguma repetição ainda é melhor que lote curto.
        fato_q = q.get("_fato") or f'{q.get("topico","")}:{q.get("gabarito","")}'
        if fato_q in fatos_usados and tentativas < limite * 0.85:
            continue

        topico_q = q.get("topico", "")
        if (topico_q and topico_q in topicos_usados
                and tentativas < limite * 0.7):
            continue

        vistos.add(q["enunciado"])
        fatos_usados.add(fato_q)
        if topico_q:
            topicos_usados.add(topico_q)
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade=10, topico=None, templates=None, seed=None):
    """
    Formato compatível com salvar_questoes_banco.
    Metadados internos (tipo_resposta, resposta_bruta) NÃO são incluídos.
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
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    topico = sys.argv[2] if len(sys.argv) > 2 else None
    for q in gerar_lote(qtd, topico):
        print("─" * 66)
        print(f"Q{q['numero']} [{q['topico']}]\n")
        print(q["enunciado"], "\n")
        for L, t in q["alternativas"].items():
            print(f"   {L}) {t}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("─" * 66)
    print(f"\n{qtd} questões conceituais | Fatos verificados em fonte primária.\n")
