"""
=============================================================
  GERADOR DE PORTUGUÊS
=============================================================
  Gramática, fundamental ao ENEM.

  DIFERENÇA EM RELAÇÃO AO gerador_interpretacao.py

  Aquele precisa de um TEXTO para gerar questões de
  interpretação. Este gera de REGRA — crase, concordância,
  classes de palavras, sintaxe — sem depender de livro.

  CATÁLOGO POR TÓPICO

  Cada template tem rótulo legível e nível, para o app montar
  botões do tipo "gerar questão de crase".

  Fatos verificados em portugues/_fontes.md.

  USO:
      from gerador_portugues import gerar_lote, listar_topicos
      gerar_lote(5, topico="crase")
=============================================================
"""

import random
import re
import unicodedata

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]


def _de(sintagma: str) -> str:
    """
    Antepõe "de" fazendo a contração com o artigo inicial.

    As justificativas da crase são sintagmas soltos: umas começam por
    artigo ("a palavra 'casa'..."), outras não ("palavra masculina").
    Concatenar "de" cru produzia "antes de a palavra 'casa'".
    """
    s = sintagma.lstrip()
    contracoes = (("a ", "da "), ("o ", "do "),
                  ("as ", "das "), ("os ", "dos "),
                  ("um ", "dum "), ("uma ", "duma "))
    for artigo, contraida in contracoes:
        if s.startswith(artigo):
            return contraida + s[len(artigo):]
    return "de " + s


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
#  MOLDURAS DE CONTEXTO
# ══════════════════════════════════════════════════════════
#
#  Os enunciados tinham mediana de 18 palavras, e dois terços
#  ficavam abaixo de 20. Prova de verdade dá SITUAÇÃO antes
#  da pergunta — ENEM de linguagens fica entre 60 e 150
#  palavras.
#
#  Estas molduras embrulham a frase analisada numa situação
#  plausível, sem alterar o fenômeno gramatical em exame.
#

# Três FAMÍLIAS de moldura, não uma. Com um padrão único, o aluno lia
# trinta vezes "fulano estava revisando um texto" — a variedade
# aparente sumia mesmo com aberturas diferentes.
#
#   revisao   alguém corrige ou confere um texto
#   uso       o texto aparece em circulação, sem menção a correção
#   estudo    contexto explicitamente didático
#
# A família é sorteada a cada questão, então uma prova mistura os três
# registros.

MOLDURAS_REVISAO = [
    ("Um aviso será afixado no mural da escola e passa por revisão "
     "antes da impressão. O texto submetido à coordenação é o "
     "seguinte:",
     "A coordenação, em dúvida, consultou o professor de português."),

    ("Uma empresa revisa a comunicação interna antes de enviá-la a "
     "todos os setores. O trecho em análise é:",
     "O setor de comunicação pediu parecer sobre a redação."),

    ("Ao corrigir a redação de um aluno, o professor destacou o "
     "seguinte período:",
     "A observação feita à margem pedia atenção à norma culta."),

    ("A ata de uma reunião de condomínio registrou a seguinte "
     "deliberação:",
     "Antes da assinatura, um dos presentes questionou a redação."),

    ("O edital de um concurso público apresenta, entre suas "
     "disposições, o seguinte trecho:",
     "A comissão organizadora submeteu o texto a revisão."),
]

# ── família USO: o texto simplesmente circula ──
#
# Sem menção a correção ou revisão: é o registro mais próximo do que
# ENEM e bancas costumam apresentar.
MOLDURAS_USO = [
    ("Uma reportagem sobre mobilidade urbana trazia, entre os "
     "depoimentos, a seguinte fala de um morador:",
     "O trecho foi reproduzido tal como registrado pelo repórter."),

    ("Em uma carta enviada a um jornal, o leitor escreveu:",
     "A carta foi publicada na seção de opinião."),

    ("Uma postagem em rede social sobre serviços públicos afirmava:",
     "A publicação alcançou grande circulação em poucas horas."),

    ("O narrador de um conto brasileiro contemporâneo observa:",
     "A passagem encerra o segundo capítulo da obra."),

    ("Durante uma entrevista de rádio, o convidado declarou:",
     "A transcrição foi publicada no site da emissora."),

    ("Um relatório técnico apresentado à diretoria conclui:",
     "O documento foi arquivado após a apresentação."),

    ("A legenda de uma fotografia em exposição informava:",
     "O texto acompanhava a imagem na parede da galeria."),

    ("Em um diálogo de novela, uma personagem diz à outra:",
     "A cena foi ao ar no capítulo da última semana."),
]

MOLDURAS_ESTUDO = [
    ("Durante uma aula de língua portuguesa, o professor projetou o "
     "seguinte período para análise coletiva:",
     "A turma discutiu o emprego correto do recurso em questão."),

    ("Uma apostila de preparação para concursos apresenta o seguinte "
     "exemplo:",
     "O comentário ao pé da página remete à regra aplicável."),

    ("Em um grupo de estudos, os participantes analisaram a seguinte "
     "construção:",
     "A discussão girou em torno da norma culta escrita."),

    ("Um material de revisão para o ENEM traz o seguinte período "
     "como exercício:",
     "A questão pede a aplicação da regra correspondente."),
]

FAMILIAS = {
    "revisao": MOLDURAS_REVISAO,
    "uso":     MOLDURAS_USO,
    "estudo":  MOLDURAS_ESTUDO,
}


def _emoldurar(frase, rng, tipo=None, formato="contextualizado"):
    """
    Embrulha a frase numa situação.

    `formato` decide a EXTENSÃO:
      "contextualizado"  moldura completa, para SIMULADO — o aluno
                         precisa treinar a leitura de enunciado longo
      "direto"           só a frase, para REVISÃO — quem está treinando
                         um tópico específico não quer ler três linhas
                         de contexto a cada questão

    `tipo` fixa a família; se omitido, sorteia entre as três.
    """
    if formato == "direto":
        ABERTURAS = [
            "Considere o período:",
            "Analise a construção:",
            "Observe o trecho:",
            "Leia o período:",
        ]
        return f'{rng.choice(ABERTURAS)} "{frase}"'

    familia = tipo if tipo in FAMILIAS else rng.choice(list(FAMILIAS))
    abertura, fechamento = rng.choice(FAMILIAS[familia])
    return f"{abertura}\n\n    \"{frase}\"\n\n{fechamento}"


# ══════════════════════════════════════════════════════════
#  CRASE
# ══════════════════════════════════════════════════════════
#
#  Fontes: Aprova Total; Toda Matéria; Oficina do Estudante;
#  Bechara, Moderna Gramática Portuguesa.
#
#  (frase sem acento, tem crase, regra, explicação)
FRASES_CRASE = [
    # ── obrigatória ──
    # As justificativas descrevem SEMPRE o que vem depois da lacuna,
    # porque é isso que o comando pergunta ("a lacuna antecede:"). Antes,
    # duas delas descreviam o verbo, que vem ANTES — e, pior, "verbo que
    # exige a preposição 'a'" (referir-se) e "verbo transitivo indireto
    # que exige a preposição 'a'" (assistir) enunciavam a mesma regra com
    # palavras diferentes: as duas valiam para a mesma frase.
    ("O público assistiu {} peça com atenção.", True,
     "substantivo feminino determinado exigido por verbo transitivo "
     "indireto",
     "assistir, no sentido de ver, exige a preposição 'a'"),
    ("Os alunos chegaram {}s oito horas em ponto.", True,
     "indicação de hora determinada",
     "horas determinadas sempre levam crase"),
    ("O trabalho foi entregue {}s pressas.", True,
     "locução adverbial feminina",
     "locuções adverbiais femininas levam crase: às pressas, à noite, "
     "às vezes"),
    ("Ele pediu um bife {} milanesa.", True,
     "locução 'à moda de', ainda que implícita",
     "'à milanesa' equivale a 'à moda milanesa'"),
    ("A comissão se referiu {} proposta anterior.", True,
     "substantivo feminino determinado exigido por verbo transitivo "
     "indireto",
     "referir-se exige a preposição 'a'"),
    ("Voltamos {} casa de meus avós no domingo.", True,
     # Era "a palavra 'casa' VEM determinada por complemento" — uma
     # oração, não um sintagma. Encaixada na explicação, saía "a lacuna
     # vem antes de a palavra 'casa' vem determinada por complemento".
     "a palavra 'casa' determinada por complemento",
     "'casa' só admite crase quando determinada: 'voltei a casa' sem "
     "crase, 'voltei à casa de Maria' com crase"),
    ("O documento foi elaborado {}s claras.", True,
     "locução adverbial feminina",
     "locuções adverbiais femininas levam crase"),
    ("A professora obedeceu {}s normas da escola.", True,
     "substantivo feminino plural determinado exigido por verbo "
     "transitivo indireto",
     "com plural determinado usa-se 'às', e não 'a'"),

    # ── proibida ──
    ("O menino foi {} pé até a escola.", False,
     "palavra masculina",
     "não há crase diante de palavra masculina"),
    ("Todos começaram {} estudar cedo.", False,
     "verbo no infinitivo",
     "não há crase diante de verbo, porque verbo não admite artigo"),
    ("O recado foi dado {} ela pela manhã.", False,
     "pronome pessoal",
     "não há crase diante de pronome pessoal"),
    ("A leitura me levou {} essa conclusão.", False,
     "pronome demonstrativo 'essa'",
     "não há crase diante de esse, essa, este, esta — esses pronomes "
     "não admitem artigo"),
    ("Ficaram frente {} frente no debate.", False,
     "palavras repetidas",
     "não há crase entre palavras repetidas: frente a frente, dia a dia"),
    ("Ele compareceu {} uma reunião importante.", False,
     "artigo indefinido 'uma'",
     "não há crase diante de artigo indefinido"),
    ("Não me submeto {} pessoas mal-intencionadas.", False,
     "plural com sentido genérico, com o 'a' no singular",
     "sem determinação, o 'a' fica no singular e não há crase; com "
     "determinação seria 'às pessoas'"),
    ("Esta é a colega {} quem pedi ajuda.", False,
     "pronome relativo 'quem'",
     "não há crase diante dos relativos que, quem e cuja"),
    ("O relatório se refere {} Vossa Senhoria.", False,
     "expressão de tratamento",
     "não há crase diante de expressões de tratamento"),
    # "à procura de" foi REMOVIDA: gramáticos divergem sobre a forma, e
    # questão com divergência não serve para prova. O critério aqui é o
    # mesmo das disciplinas de medicina — só entra o que as fontes
    # sustentam sem conflito.
    ("Prefiro caminhar {} andar de carro.", False,
     "verbo no infinitivo",
     "não há crase diante de verbo"),
    ("O aviso foi dirigido {} todos os presentes.", False,
     "pronome indefinido masculino",
     "não há crase diante de palavra masculina nem de pronome "
     "indefinido"),
]


def gerar_crase_ocorrencia(rng, formato="contextualizado"):
    """Há ou não crase na lacuna? — nível médio e ENEM."""
    frase, tem, regra, motivo = rng.choice(FRASES_CRASE)
    lacuna = frase.format("___")

    COMANDOS = [
        "Sobre o preenchimento da lacuna, é correto afirmar que:",
        "Assinale a alternativa correta quanto ao acento grave.",
        "Quanto ao uso da crase nesse trecho:",
        "Assinale a alternativa que resolve a dúvida corretamente.",
    ]
    enunciado = (f"{_emoldurar(lacuna, rng, formato=formato)} "
                 f"{rng.choice(COMANDOS)}")

    # A lacuna "___s" pede "às", não "à" — a alternativa precisa dizer
    # a forma exata que o aluno vai escrever.
    plural = "{}s" in frase
    forma_com = "às" if plural else "à"
    forma_sem = "as" if plural else "a"

    # As alternativas precisam MISTURAR afirmativas positivas e
    # negativas. Antes, quando havia crase, o gabarito era a única
    # positiva entre quatro negativas — e a estratégia "marque a
    # positiva" acertava 100% das vezes.
    #
    # Agora cada conjunto tem duas de cada polaridade, além do
    # facultativo.
    if tem:
        correta = f"o acento grave é obrigatório: \"{forma_com}\""
        distratores = [
            f"o acento grave não se aplica: \"{forma_sem}\"",
            "o acento grave só caberia se a frase fosse reescrita no "
            "plural",
            "o acento grave é vedado, por se tratar de palavra masculina",
            "o acento grave é vedado, por não haver preposição exigida",
            "o acento grave é facultativo, por se tratar de nome próprio",
        ]
    else:
        correta = f"o acento grave não se aplica: \"{forma_sem}\""
        distratores = [
            f"o acento grave é obrigatório: \"{forma_com}\"",
            "o acento grave seria exigido apenas no plural",
            "o acento grave é obrigatório, por exigência do verbo",
            "o acento grave é obrigatório, por ser locução adverbial "
            "feminina",
            "o acento grave é facultativo, por haver pronome possessivo",
        ]

    correcao = frase.format("à" if tem else "a")
    explicacao = (
        f"A forma correta é: \"{correcao}\" — {'com' if tem else 'sem'} "
        f"crase, porque a lacuna vem antes "
        f"{_de(regra)}. Em outras palavras: {motivo}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Português (crase)", rng)
    if q:
        q["_fato"] = f"crase:{frase[:22]}"
    return q


def gerar_crase_regra(rng, formato="contextualizado"):
    """Qual regra justifica a presença ou ausência da crase?"""
    frase, tem, regra, motivo = rng.choice(FRASES_CRASE)
    correcao = frase.format("à" if tem else "a")

    palavra = "presença" if tem else "ausência"
    # O período é exibido JÁ CORRIGIDO neste template, então não há
    # lacuna nenhuma para o aluno olhar — falar em "lacuna" mandava
    # procurar o que não estava lá.
    COMANDOS = [
        f"A {palavra} da crase se justifica porque o 'a' antecede:",
        f"O que justifica a {palavra} do acento grave é a presença de:",
        f"Assinale a alternativa que justifica a {palavra} da crase.",
    ]
    enunciado = (f"{_emoldurar(correcao, rng, formato=formato)} "
                 f"{rng.choice(COMANDOS)}")

    correta = regra
    distratores = [f[2] for f in FRASES_CRASE if f[2] != regra]
    rng.shuffle(distratores)

    explicacao = (
        f"Em \"{correcao}\", {'há' if tem else 'não há'} crase porque o "
        f"'a' antecede {regra}. Vale lembrar: {motivo}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (crase)", rng)
    if q:
        # Mesma chave do template de ocorrência, e de propósito: as duas
        # questões tratam da MESMA frase. Um caderno trazia "Esta é a
        # colega ___ quem pedi ajuda" perguntando se havia crase e, sete
        # questões depois, a mesma frase pedindo a justificativa.
        q["_fato"] = f"crase:{frase[:22]}"
    return q


# ══════════════════════════════════════════════════════════
#  CLASSES DE PALAVRAS
# ══════════════════════════════════════════════════════════
#
#  (palavra, classe, frase de contexto, o que caracteriza a classe)
CLASSES = [
    ("rapidamente", "advérbio",
     "O atleta correu rapidamente até a linha de chegada.",
     "modifica o verbo, indicando circunstância"),
    ("bonita", "adjetivo",
     "A paisagem bonita encantou os visitantes.",
     "atribui característica ao substantivo"),
    ("liberdade", "substantivo",
     "A liberdade é um direito de todos.",
     "nomeia um ser, objeto ou conceito"),
    ("correu", "verbo",
     "O menino correu para o portão.",
     "indica ação, estado ou fenômeno"),
    ("aquele", "pronome demonstrativo",
     "Aquele livro estava sobre a mesa.",
     "indica a posição do ser em relação às pessoas do discurso"),
    ("meu", "pronome possessivo",
     "Meu caderno ficou na escola.",
     "indica posse"),
    ("três", "numeral",
     "Três alunos chegaram atrasados.",
     "indica quantidade ou ordem"),
    ("mas", "conjunção",
     "Estudou bastante, mas não passou.",
     "liga orações ou termos, estabelecendo relação de sentido"),
    ("sobre", "preposição",
     "O livro está sobre a mesa.",
     "liga dois termos, estabelecendo relação de subordinação"),
    ("ah", "interjeição",
     "Ah, que surpresa agradável!",
     "exprime emoção ou sentimento súbito"),
    ("o", "artigo",
     "O professor entrou na sala.",
     "determina o substantivo, definindo-o ou indefinindo-o"),
]


def gerar_classe_palavra(rng, formato="contextualizado"):
    """A que classe pertence a palavra destacada? — fundamental."""
    palavra, classe, frase, caracteriza = rng.choice(CLASSES)
    destacada = frase.replace(palavra, palavra.upper(), 1)
    if palavra.upper() not in destacada:
        destacada = frase.replace(palavra.capitalize(),
                                  palavra.upper(), 1)

    CENARIOS = [
        f"Ao analisar morfologicamente um período, o estudante deve "
        f"identificar a que classe pertence cada palavra, observando "
        f"sua função no contexto. Considere o período abaixo, com uma "
        f"palavra em destaque:\n\n    \"{destacada}\"",
        f"Um exercício de análise morfológica apresenta o seguinte "
        f"período, com destaque para uma das palavras:"
        f"\n\n    \"{destacada}\"\n\n"
        f"A classificação depende do papel que a palavra desempenha.",
        f"Durante a correção de uma atividade, o professor pediu que a "
        f"turma classificasse a palavra destacada no período a seguir:"
        f"\n\n    \"{destacada}\"",
    ]
    COMANDOS = [
        "A palavra destacada pertence à classe:",
        "Assinale a alternativa que indica sua classe gramatical.",
        "Do ponto de vista morfológico, a palavra destacada é um:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = classe
    distratores = [c[1] for c in CLASSES if c[1] != classe]
    rng.shuffle(distratores)

    explicacao = (
        f"A palavra \"{palavra}\" é {classe}, porque {caracteriza}. "
        f"Na frase, seu papel é justamente esse."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (classes de palavras)", rng)
    if q:
        q["_fato"] = f"classe:{classe}"
    return q


# ══════════════════════════════════════════════════════════
#  CONCORDÂNCIA VERBAL
# ══════════════════════════════════════════════════════════
#
#  (frase com lacuna, forma correta, formas erradas, regra)
# Cada entrada traz VARIANTES ERRADAS DA MESMA FRASE. Antes os
# distratores eram frases de outros itens da tabela — e aí bastava
# achar a única variante da original para acertar sem saber nada.
#
# (frase errada, forma correta, variantes erradas, regra)
CONCORDANCIA = [
    ("Fazem dois anos que ele saiu da empresa.",
     "Faz dois anos que ele saiu da empresa.",
     ["Fazem-se dois anos que ele saiu da empresa.",
      "Fazem dois anos de que ele saiu da empresa.",
      "Fizeram dois anos que ele saiu da empresa.",
      "Faziam dois anos que ele saiu da empresa."],
     "o verbo 'fazer' indicando tempo decorrido é IMPESSOAL e fica "
     "sempre na terceira pessoa do singular"),

    ("Houveram muitos problemas na entrega.",
     "Houve muitos problemas na entrega.",
     ["Houveram-se muitos problemas na entrega.",
      "Haviam muitos problemas na entrega.",
      "Hão de haver muitos problemas na entrega.",
      "Houveram-nos muitos problemas na entrega."],
     "o verbo 'haver' no sentido de existir é IMPESSOAL e não vai para "
     "o plural"),

    # Saiu "A maioria dos alunos FALTARAM à prova", que estava como
    # forma errada. Com sujeito coletivo partitivo, Cegalla e Bechara
    # admitem singular e plural — a frase dada como errada estava
    # correta, o mesmo defeito do "mais de um candidato se
    # cumprimentaram". Item de concordância só serve quando a norma não
    # oferece as duas saídas.
    #
    # Nome próprio plural com artigo no plural não tem essa franquia.
    ("Os Estados Unidos é um país continental.",
     "Os Estados Unidos são um país continental.",
     ["Os Estados Unidos era um país continental.",
      "O Estados Unidos são um país continental.",
      "Os Estados Unidos foi um país continental.",
      "Os Estados Unidos sendo um país continental."],
     "nome próprio no plural precedido de artigo plural leva o verbo "
     "ao plural"),

    ("Aluga-se casas na região central.",
     "Alugam-se casas na região central.",
     ["Aluga-se as casas na região central.",
      "Alugam-se a casa na região central.",
      "Aluga-se de casas na região central.",
      "Alugam se casas na região central."],
     "na voz passiva sintética, o verbo concorda com o sujeito "
     "paciente, que aqui é 'casas', no plural"),

    ("Existe muitas razões para comemorar.",
     "Existem muitas razões para comemorar.",
     ["Existe muitas razão para comemorar.",
      "Existem muita razão para comemorar.",
      "Há de existir muitas razões para comemorar.",
      "Existiu muitas razões para comemorar."],
     "o verbo 'existir' NÃO é impessoal e concorda com o sujeito, "
     "diferentemente de 'haver'"),

    ("Devem haver soluções melhores.",
     "Deve haver soluções melhores.",
     ["Devem haverem soluções melhores.",
      "Devem existir soluções melhor.",
      "Deve haverem soluções melhores.",
      "Deviam haver soluções melhores."],
     "quando 'haver' impessoal vem em locução, o auxiliar também fica "
     "no singular"),

    # O exemplo anterior era "Mais de um candidato se cumprimentaram",
    # apresentado como ERRADO e corrigido para o singular. Mas
    # cumprimentar-se é recíproco, e a reciprocidade é exatamente a
    # exceção que a própria regra do item enunciava: a frase dada como
    # errada era a correta. Trocada por um verbo não recíproco, em que
    # a regra do singular vale sem ressalva — a exceção continua
    # ensinada na explicação.
    ("Mais de um candidato chegaram atrasados.",
     "Mais de um candidato chegou atrasado.",
     ["Mais de um candidatos chegou atrasado.",
      "Mais do que um candidato chegaram atrasados.",
      "Mais de um candidato chegaram atrasado.",
      "Mais de um candidato chegavam atrasados."],
     "a expressão 'mais de um' leva o verbo ao singular; o plural só "
     "aparece quando a ação é recíproca, como em 'mais de um se "
     "cumprimentaram'"),

    ("Vossa Excelência sois justo.",
     "Vossa Excelência é justo.",
     ["Vossa Excelência sois justos.",
      "Vossa Excelência são justo.",
      "Vossa Excelência és justo.",
      "Vossa Excelência sereis justo."],
     "pronomes de tratamento levam o verbo à TERCEIRA pessoa, ainda "
     "que se dirijam ao interlocutor"),
]


def gerar_concordancia(rng, formato="contextualizado"):
    """Corrigir a concordância verbal — nível médio e ENEM."""
    errada, certa, variantes, regra = rng.choice(CONCORDANCIA)

    COMANDOS = [
        "A forma que corrige a concordância verbal é:",
        "Assinale a alternativa que apresenta a redação correta.",
        "A frase está correta em:",
        "Assinale a alternativa adequada à norma culta.",
    ]
    enunciado = f"{_emoldurar(errada, rng, formato=formato)} {rng.choice(COMANDOS)}"

    # Todos os distratores são VARIANTES DA MESMA FRASE — inclusive a
    # original, que separa quem percebe o erro de quem não percebe.
    correta = certa
    distratores = [errada] + list(variantes)
    rng.shuffle(distratores)

    explicacao = (
        f"A forma correta é \"{certa}\", porque {regra}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (concordância verbal)", rng)
    if q:
        q["_fato"] = f"concordancia:{certa[:22]}"
    return q


# ══════════════════════════════════════════════════════════
#  FIGURAS DE LINGUAGEM
# ══════════════════════════════════════════════════════════
#
#  (figura, definição, exemplo)
FIGURAS = [
    ("metáfora", "comparação implícita, sem termo comparativo",
     "Meu coração é um balde despejado."),
    ("comparação", "aproximação explícita, com termo comparativo",
     "Ele é forte como um touro."),
    ("metonímia", "substituição de um termo por outro com o qual "
     "mantém relação de proximidade",
     "Li Machado de Assis inteiro."),
    ("hipérbole", "exagero intencional",
     "Já te disse isso um milhão de vezes."),
    ("eufemismo", "suavização de uma ideia desagradável",
     "Ele nos deixou na noite passada."),
    ("ironia", "afirmação do contrário do que se pretende dizer",
     "Que belo trabalho você fez, quebrou tudo."),
    ("personificação", "atribuição de características humanas a seres "
     "inanimados",
     "O vento sussurrava entre as folhas."),
    ("antítese", "aproximação de ideias opostas",
     "É um mar de amor e ódio."),
    ("pleonasmo", "redundância que reforça a ideia",
     "Vi com meus próprios olhos."),
    ("aliteração", "repetição de sons consonantais",
     "O rato roeu a roupa do rei de Roma."),
]


def gerar_figura_linguagem(rng, formato="contextualizado"):
    """Identificar a figura de linguagem — fundamental e ENEM."""
    figura, definicao, exemplo = rng.choice(FIGURAS)
    modo = rng.choice(["pelo_exemplo", "pela_definicao"])

    if modo == "pelo_exemplo":
        CENARIOS = [
            f"Em uma oficina de escrita criativa, os participantes "
            f"analisaram construções que fogem ao sentido literal. Um "
            f"dos trechos discutidos foi:\n\n    \"{exemplo}\"\n\n"
            f"O mediador pediu que identificassem o recurso empregado.",
            f"Uma coletânea de textos literários destaca passagens em "
            f"que o autor recorre a recursos expressivos. Entre elas:"
            f"\n\n    \"{exemplo}\"\n\n"
            f"A nota de rodapé remete ao estudo das figuras.",
            f"Ao comentar a letra de uma canção, um crítico destacou o "
            f"seguinte verso:\n\n    \"{exemplo}\"\n\n"
            f"Segundo ele, o efeito depende de um recurso específico.",
        ]
        COMANDOS = [
            "A figura de linguagem empregada é:",
            "Assinale a alternativa que a identifica.",
            "Nessa construção, há:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = figura
        distratores = [f[0] for f in FIGURAS if f[0] != figura]
    else:
        CENARIOS = [
            f"As figuras de linguagem são recursos que afastam a "
            f"expressão do sentido literal para produzir efeito "
            f"estético ou argumentativo. Uma delas consiste em "
            f"{definicao}.",
            f"Um glossário de termos literários define determinada "
            f"figura como o recurso que consiste em {definicao}.",
            f"Ao estudar os recursos expressivos da língua, o aluno "
            f"encontrou a seguinte definição: trata-se do recurso que "
            f"consiste em {definicao}.",
        ]
        COMANDOS = [
            "Trata-se de:",
            "Assinale a alternativa que a nomeia.",
            "Essa figura é a:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = figura
        distratores = [f[0] for f in FIGURAS if f[0] != figura]

    rng.shuffle(distratores)
    explicacao = (
        f"A figura é a {figura}, que consiste em {definicao}. "
        f"Um exemplo típico: \"{exemplo}\""
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (figuras de linguagem)", rng)
    if q:
        q["_fato"] = f"figura:{figura}"
    return q


# ══════════════════════════════════════════════════════════
#  REGÊNCIA VERBAL
# ══════════════════════════════════════════════════════════
#
#  Fontes: Estratégia Concursos; Toda Matéria; SESI; Bechara,
#  Moderna Gramática Portuguesa.
#
#  (verbo, sentido, regência, frase correta, frase errada, observação)
REGENCIA = [
    ("assistir", "ver, presenciar", "transitivo indireto, com \"a\"",
     "Assistimos ao documentário na íntegra.",
     "Assistimos o documentário na íntegra.",
     "no sentido de dar assistência, o mesmo verbo é transitivo direto: "
     "\"o médico assistiu o paciente\""),

    ("assistir", "dar assistência, amparar", "transitivo direto",
     "O médico assistiu o paciente durante a noite.",
     "O médico assistiu ao paciente durante a noite.",
     "no sentido de ver, o mesmo verbo é transitivo indireto: "
     "\"assistimos ao filme\""),

    ("aspirar", "almejar, pretender", "transitivo indireto, com \"a\"",
     "O funcionário aspira ao cargo de gerente.",
     "O funcionário aspira o cargo de gerente.",
     "no sentido de sorver, é transitivo direto: \"aspirou o ar puro\""),

    ("aspirar", "sorver, inalar", "transitivo direto",
     "Ela aspirou o perfume das flores.",
     "Ela aspirou ao perfume das flores.",
     "no sentido de almejar, é transitivo indireto: \"aspira ao cargo\""),

    ("visar", "ter por objetivo", "transitivo indireto, com \"a\"",
     "A campanha visa ao desenvolvimento da região.",
     "A campanha visa o desenvolvimento da região.",
     "no sentido de mirar ou de dar visto, é transitivo direto: "
     "\"visou o alvo\""),

    ("implicar", "acarretar, ter como consequência", "transitivo direto",
     "A decisão implicará mudanças no cronograma.",
     "A decisão implicará em mudanças no cronograma.",
     "no sentido de antipatizar, exige \"com\": \"implica com o vizinho\""),

    ("obedecer", "cumprir", "transitivo indireto, com \"a\"",
     "Os motoristas obedecem às normas de trânsito.",
     "Os motoristas obedecem as normas de trânsito.",
     "o mesmo vale para desobedecer: \"desobedeceu à lei\""),

    ("preferir", "escolher uma coisa em vez de outra",
     "transitivo direto e indireto, com \"a\"",
     "Prefiro caminhar a dirigir no trânsito.",
     "Prefiro mais caminhar do que dirigir no trânsito.",
     "o verbo não aceita \"do que\", \"que\" nem intensificadores como "
     "\"mais\""),

    ("chegar", "atingir um destino", "preposição \"a\", não \"em\"",
     "Cheguei à escola pontualmente.",
     "Cheguei na escola pontualmente.",
     "o mesmo vale para o verbo ir: \"fui ao mercado\""),

    ("namorar", "manter relacionamento", "transitivo direto",
     "Ela namorou aquele artista por dois anos.",
     "Ela namorou com aquele artista por dois anos.",
     "o verbo não pede preposição na norma culta"),

    ("morar", "residir", "preposição \"em\"",
     "Ele mora na Rua das Palmeiras.",
     "Ele mora à Rua das Palmeiras.",
     "morar, residir e situar-se pedem \"em\", não \"a\""),
]


def gerar_regencia_correta(rng, formato="contextualizado"):
    """Qual frase respeita a regência? — nível médio e ENEM."""
    verbo, sentido, reg, certa, errada, obs = rng.choice(REGENCIA)

    CENARIOS = [
        f"Um manual de redação oficial adverte que a regência de certos "
        f"verbos muda conforme o sentido. Entre os exemplos citados "
        f"está o verbo \"{verbo}\", empregado com o sentido de "
        f"{sentido}.",
        f"Em uma revisão de texto, o revisor apontou que o verbo "
        f"\"{verbo}\", quando significa {sentido}, exige regência "
        f"específica na norma culta.",
        f"Uma apostila de português para concursos dedica um tópico à "
        f"regência do verbo \"{verbo}\". No sentido de {sentido}, "
        f"esse verbo tem comportamento próprio.",
        f"Durante a correção de um documento oficial, discutiu-se o "
        f"emprego do verbo \"{verbo}\" com o sentido de {sentido}.",
    ]
    COMANDOS = [
        "Assinale a alternativa em que ele está corretamente empregado.",
        "A construção que respeita essa regência é:",
        "Assinale a alternativa de acordo com a norma culta.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = certa
    # Os distratores são frases erradas de OUTROS verbos, mais a versão
    # errada do próprio: assim o aluno precisa saber a regência, não
    # apenas reconhecer o verbo do enunciado.
    distratores = [errada]
    distratores += [r[4] for r in REGENCIA
                    if r[4] != errada and r[0] != verbo]
    rng.shuffle(distratores)

    explicacao = (
        f"O verbo \"{verbo}\", no sentido de {sentido}, é {reg}. "
        f"A forma correta é: \"{certa}\" Convém notar que {obs}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (regência verbal)", rng)
    if q:
        q["_fato"] = f"regencia:{verbo}:{sentido[:12]}"
    return q


def gerar_regencia_sentido(rng, formato="contextualizado"):
    """
    O mesmo verbo muda de sentido conforme a regência.

    É o ponto central do assunto: "assistir o paciente" e "assistir ao
    filme" são coisas diferentes.
    """
    duplos = {}
    for v, s, r, certa, errada, obs in REGENCIA:
        duplos.setdefault(v, []).append((s, r, certa))
    candidatos = {v: l for v, l in duplos.items() if len(l) >= 2}
    if not candidatos:
        return None

    verbo = rng.choice(list(candidatos))
    sentido, reg, frase = rng.choice(candidatos[verbo])
    outro = [x for x in candidatos[verbo] if x[0] != sentido][0]

    CENARIOS = [
        f"Certos verbos mudam de sentido conforme a regência que "
        f"adotam, o que exige atenção na leitura e na escrita. "
        f"Considere o emprego do verbo \"{verbo}\" no período abaixo:"
        f"\n\n    \"{frase}\"",
        f"Um exercício de interpretação chama atenção para o fato de "
        f"que a preposição, ou sua ausência, altera o significado do "
        f"verbo. Analise o período:\n\n    \"{frase}\"",
        f"Durante a revisão de um texto, discutiu-se qual sentido o "
        f"verbo \"{verbo}\" assume na construção abaixo, dada a "
        f"regência empregada:\n\n    \"{frase}\"",
        f"Uma apostila de português destaca que o verbo \"{verbo}\" "
        f"admite mais de uma regência, cada qual com sentido próprio. "
        f"O exemplo apresentado é:\n\n    \"{frase}\"",
    ]
    COMANDOS = [
        f"Nessa construção, o verbo \"{verbo}\" significa:",
        "O sentido do verbo na frase é:",
        "Assinale a alternativa com o sentido correto do verbo.",
        "Considerando a regência empregada, o verbo significa:",
        "Assinale a alternativa que traduz o sentido do verbo.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = sentido
    distratores = [outro[0]]
    distratores += [r[1] for r in REGENCIA if r[1] not in (sentido, outro[0])]
    rng.shuffle(distratores)

    explicacao = (
        f"Em \"{frase}\", o verbo é {reg}, e por isso significa "
        f"{sentido}. Com a outra regência, o mesmo verbo passa a "
        f"significar {outro[0]} — como em \"{outro[2]}\""
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (regência verbal)", rng)
    if q:
        q["_fato"] = f"regencia_sentido:{verbo}"
    return q


# ══════════════════════════════════════════════════════════
#  COLOCAÇÃO PRONOMINAL
# ══════════════════════════════════════════════════════════
#
#  Registradas apenas as três regras sobre as quais todas as
#  gramáticas concordam.
#
#  (frase correta, posição, motivo, frases erradas)
COLOCACAO = [
    ("Não me diga isso agora.", "próclise",
     "a palavra negativa \"não\" atrai o pronome para antes do verbo",
     ["Não diga-me isso agora.", "Não dir-me-ia isso agora.",
      "Não diga isso-me agora."]),

    ("Sempre se falou desse assunto.", "próclise",
     "o advérbio \"sempre\" atrai o pronome para antes do verbo",
     ["Sempre falou-se desse assunto.", "Sempre falar-se-ia desse "
      "assunto.", "Sempre falou desse assunto-se."]),

    ("Quem me chamou lá fora?", "próclise",
     "o pronome interrogativo \"quem\" atrai o pronome",
     ["Quem chamou-me lá fora?", "Quem chamar-me-ia lá fora?",
      "Quem chamou lá fora-me?"]),

    ("Diga-me a verdade, por favor.", "ênclise",
     "o verbo inicia a oração, e não se começa período com pronome "
     "oblíquo átono na norma culta",
     ["Me diga a verdade, por favor.", "Dir-me-ia a verdade, por favor.",
      "Diga a verdade-me, por favor."]),

    ("Entregaram-nos o relatório ontem.", "ênclise",
     "o verbo inicia a oração, sem palavra atrativa antes",
     ["Nos entregaram o relatório ontem.",
      "Entregar-nos-iam o relatório ontem.",
      "Entregaram o relatório-nos ontem."]),

    ("Dar-lhe-ei uma resposta amanhã.", "mesóclise",
     "o verbo está no futuro do presente e não há palavra atrativa",
     ["Darei-lhe uma resposta amanhã.", "Lhe darei uma resposta amanhã.",
      "Dar-ei-lhe uma resposta amanhã."]),

    ("Falar-se-ia do caso em outra ocasião.", "mesóclise",
     "o verbo está no futuro do pretérito e não há palavra atrativa",
     ["Falaria-se do caso em outra ocasião.",
      "Se falaria do caso em outra ocasião.",
      "Falar-ia-se do caso em outra ocasião."]),
]


def gerar_colocacao_pronominal(rng, formato="contextualizado"):
    """Colocação correta do pronome — nível médio e ENEM."""
    certa, posicao, motivo, erradas = rng.choice(COLOCACAO)

    # Só 7 frases na tabela, então a variação vem dos cenários: com 3
    # cenários e 3 comandos o template rendia 9 enunciados distintos.
    CENARIOS = [
        "Um manual de redação oficial estabelece que, na modalidade "
        "escrita da norma culta, a posição do pronome oblíquo átono "
        "obedece a regras precisas, determinadas pelo contexto "
        "sintático e não pela preferência do redator.",
        "Ao revisar um documento antes do envio, o assessor observou "
        "que a colocação do pronome oblíquo átono variava ao longo do "
        "texto. Consultou então o manual de redação da instituição, "
        "que trata do assunto em seção específica.",
        "Em uma aula preparatória para concursos, o professor explicou "
        "que a colocação pronominal costuma ser cobrada porque a fala "
        "cotidiana se afasta da norma escrita. Em seguida, projetou "
        "quatro construções para análise.",
        "Uma banca examinadora incluiu, na prova de língua portuguesa, "
        "uma questão sobre a posição do pronome oblíquo átono. As "
        "construções apresentadas testam o reconhecimento das palavras "
        "que atraem o pronome.",
        "O guia de estilo de um jornal determina que os textos sigam a "
        "norma culta escrita quanto à colocação pronominal, evitando "
        "construções próprias da oralidade.",
        "Ao preparar a defesa de um processo, o advogado revisou a "
        "petição atentando para a colocação dos pronomes oblíquos, "
        "cuja posição na norma culta obedece a critérios sintáticos "
        "definidos.",
        "Um curso de escrita profissional dedica um módulo à colocação "
        "pronominal, tema que costuma gerar dúvida porque a fala "
        "cotidiana se afasta bastante da modalidade escrita formal.",
        "A comissão de um concurso público elaborou questão sobre a "
        "posição do pronome oblíquo átono, verificando se o candidato "
        "reconhece os elementos que atraem o pronome para antes do "
        "verbo.",
    ]
    # Só 7 frases na tabela e 5 molduras: a variedade depende dos
    # comandos, então a lista foi ampliada.
    COMANDOS = [
        "Assinale a alternativa correta.",
        "A construção que segue a norma culta é:",
        "Assinale a alternativa em que a colocação está correta.",
        "Assinale a alternativa adequada à norma culta escrita.",
        "A única construção correta é:",
        "Assinale a alternativa em que o pronome está bem colocado.",
        "Nesse aspecto, a construção correta é:",
        "Assinale a alternativa que respeita a regra aplicável.",
        "Considerando a norma culta, a construção adequada é:",
        "A alternativa que atende à norma é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = certa
    distratores = list(erradas)
    # Completa com frases erradas de outros itens, se faltar
    for c in COLOCACAO:
        if c[0] != certa:
            distratores.extend(c[3][:1])
    rng.shuffle(distratores)

    explicacao = (
        f"A construção correta é \"{certa}\", com {posicao}, porque "
        f"{motivo}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
                "Português (colocação pronominal)", rng)
    if q:
        q["_fato"] = f"colocacao:{posicao}:{certa[:16]}"
    return q


def gerar_colocacao_nome(rng, formato="contextualizado"):
    """Como se chama a posição do pronome na frase?"""
    certa, posicao, motivo, erradas = rng.choice(COLOCACAO)

    CENARIOS = [
        f"A gramática normativa distingue três posições possíveis para "
        f"o pronome oblíquo átono em relação ao verbo, cada uma com "
        f"nome próprio. Considere o período abaixo:"
        f"\n\n    \"{certa}\"",
        f"Ao explicar a colocação pronominal, o professor projetou um "
        f"período em que o pronome ocupa posição determinada pelo "
        f"contexto sintático:\n\n    \"{certa}\"",
        f"Um material de revisão apresenta exemplos de cada tipo de "
        f"colocação pronominal. Entre eles, o seguinte período:"
        f"\n\n    \"{certa}\"",
    ]
    COMANDOS = [
        "A colocação pronominal empregada denomina-se:",
        "Assinale a alternativa que nomeia essa colocação.",
        "Trata-se de:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = posicao
    distratores = [p for p in ["próclise", "ênclise", "mesóclise"]
                   if p != posicao]
    distratores += ["apócope", "crase pronominal", "elipse do pronome"]

    explicacao = (
        f"Em \"{certa}\", a colocação é a {posicao}, porque {motivo}. "
        f"Na próclise o pronome vem antes do verbo, na ênclise vem "
        f"depois e na mesóclise vem no meio."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
                "Português (colocação pronominal)", rng)
    if q:
        q["_fato"] = f"colocacao_nome:{posicao}"
    return q


# ══════════════════════════════════════════════════════════
#  VOZES VERBAIS
# ══════════════════════════════════════════════════════════
#
#  (voz ativa, voz passiva analítica, sujeito ativo, sujeito passivo)
VOZES = [
    ("O professor corrigiu as provas.",
     "As provas foram corrigidas pelo professor.",
     "O professor", "As provas"),
    ("A prefeitura construiu a ponte.",
     "A ponte foi construída pela prefeitura.",
     "A prefeitura", "A ponte"),
    ("Os alunos organizaram o evento.",
     "O evento foi organizado pelos alunos.",
     "Os alunos", "O evento"),
    ("O júri escolheu o vencedor.",
     "O vencedor foi escolhido pelo júri.",
     "O júri", "O vencedor"),
    ("A empresa lançou o produto.",
     "O produto foi lançado pela empresa.",
     "A empresa", "O produto"),
    ("O médico examinou os pacientes.",
     "Os pacientes foram examinados pelo médico.",
     "O médico", "Os pacientes"),
]


def gerar_voz_verbal(rng, formato="contextualizado"):
    """Transposição entre voz ativa e passiva — fundamental e médio."""
    ativa, passiva, suj_at, suj_pas = rng.choice(VOZES)
    sentido = rng.choice(["ativa_para_passiva", "identificar_voz"])

    if sentido == "ativa_para_passiva":
        CENARIOS = [
            f"Ao revisar um relatório, o editor pediu que determinadas "
            f"passagens fossem reescritas de modo a destacar o "
            f"resultado da ação, e não quem a praticou. Uma das frases "
            f"marcadas foi:\n\n    \"{ativa}\"",
            f"Um exercício de reescrita propõe transformar períodos "
            f"para deslocar o foco do agente para o paciente da ação. "
            f"O período apresentado é:\n\n    \"{ativa}\"",
            f"Em uma aula sobre vozes verbais, o professor pediu à "
            f"turma que reescrevesse o seguinte período, mantendo o "
            f"sentido:\n\n    \"{ativa}\"",
        ]
        COMANDOS = [
            "A transposição para a voz passiva resulta em:",
            "Assinale a alternativa com a frase na voz passiva.",
            "Na voz passiva, essa frase fica:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        # Os distratores são VARIANTES DA MESMA FRASE. Antes vinham de
        # outros itens da tabela, e o gabarito era o único que repetia
        # os substantivos do enunciado — a estratégia "marque a que ecoa
        # o comando" acertava 100%.
        correta = passiva
        art_pas = "O" if passiva[0] == "O" else "A"
        distratores = [
            # sujeito e agente trocados
            f"{suj_at} foi {passiva.split(' foi ')[1].split(' pel')[0]} "
            f"{'pelo' if suj_pas.startswith('O') else 'pela'} "
            f"{suj_pas.split(' ', 1)[1].lower()}.",
            # ativa mantida
            ativa,
            # passiva sintética malformada
            f"{ativa.rstrip('.')}-se.",
            # sem agente
            passiva.split(" pel")[0] + ".",
            # auxiliar errado
            passiva.replace(" foi ", " está ").replace(" foram ", " estão "),
        ]
        explicacao = (
            f"Na transposição para a voz passiva, o objeto direto "
            f"\"{suj_pas.lower()}\" torna-se sujeito, e o sujeito "
            f"\"{suj_at.lower()}\" passa a agente da passiva. "
            f"O resultado é: \"{passiva}\""
        )
    else:
        usa_passiva = rng.random() < 0.5
        frase = passiva if usa_passiva else ativa
        CENARIOS = [
            f"A voz verbal indica se o sujeito pratica a ação, sofre a "
            f"ação ou ambos. Ao analisar um texto, o estudante "
            f"encontrou o seguinte período:\n\n    \"{frase}\"",
            f"Em uma atividade de análise sintática, pediu-se que a "
            f"turma classificasse a voz verbal do período abaixo:"
            f"\n\n    \"{frase}\"",
            f"Um exercício sobre vozes verbais apresenta o seguinte "
            f"período para classificação:\n\n    \"{frase}\"",
        ]
        COMANDOS = [
            "Essa frase está na voz:",
            "Assinale a alternativa que indica sua voz verbal.",
            "Quanto à voz verbal, trata-se de:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = "passiva analítica" if usa_passiva else "ativa"
        # "ativa" tem cinco letras e é a resposta em metade dos
        # sorteios; os outros rótulos vão até 19. Marcar o mais curto
        # acertava 49% das questões.
        #
        # "média" e "reflexiva indireta" são denominações reais que
        # nenhuma das frases da tabela exemplifica: entram para que o
        # rótulo mais curto deixe de apontar a resposta.
        distratores = ["ativa", "passiva analítica", "passiva sintética",
                       "reflexiva", "reflexiva recíproca",
                       "reflexiva indireta", "média"]
        distratores = [d for d in distratores if d != correta]
        if usa_passiva:
            explicacao = (
                f"A frase está na voz PASSIVA ANALÍTICA: o sujeito "
                f"\"{suj_pas.lower()}\" sofre a ação, e o verbo aparece "
                f"como locução com o auxiliar \"ser\". O agente da "
                f"passiva é \"{suj_at.lower()}\". Na voz ativa seria: "
                f"\"{ativa}\""
            )
        else:
            explicacao = (
                f"A frase está na voz ATIVA: o sujeito "
                f"\"{suj_at.lower()}\" pratica a ação. Na voz passiva "
                f"seria: \"{passiva}\""
            )

    q = _montar(enunciado, correta, distratores, explicacao,
                "Português (vozes verbais)", rng)
    if q:
        q["_fato"] = f"voz:{sentido}:{suj_pas[:14]}"
    return q


# ══════════════════════════════════════════════════════════
#  CATÁLOGO POR TÓPICO
# ══════════════════════════════════════════════════════════

TEMPLATES_PORTUGUES = {
    "crase_ocorrencia":  gerar_crase_ocorrencia,
    "crase_regra":       gerar_crase_regra,
    "classe_palavra":    gerar_classe_palavra,
    "concordancia":      gerar_concordancia,
    "figura_linguagem":  gerar_figura_linguagem,
    "regencia":          gerar_regencia_correta,
    "regencia_sentido":  gerar_regencia_sentido,
    "colocacao":         gerar_colocacao_pronominal,
    "colocacao_nome":    gerar_colocacao_nome,
    "voz_verbal":        gerar_voz_verbal,
}

# (chave, rótulo legível, nível, área)
CATALOGO = [
    ("crase_ocorrencia", "Crase — usar ou não",       "médio",       "ortografia"),
    ("crase_regra",      "Crase — qual regra",        "médio",       "ortografia"),
    ("classe_palavra",   "Classes de palavras",       "fundamental", "morfologia"),
    ("concordancia",     "Concordância verbal",       "médio",       "sintaxe"),
    ("figura_linguagem", "Figuras de linguagem",      "fundamental", "estilística"),
    ("regencia",         "Regência verbal",           "médio",       "sintaxe"),
    ("regencia_sentido", "Regência e mudança de sentido", "médio",   "sintaxe"),
    ("colocacao",        "Colocação pronominal",      "médio",       "sintaxe"),
    ("colocacao_nome",   "Próclise, ênclise ou mesóclise", "médio",  "sintaxe"),
    ("voz_verbal",       "Vozes verbais",             "fundamental", "sintaxe"),
]

NIVEIS = ["fundamental", "médio"]

TOPICOS_PORTUGUES = {}
for _ch, _rot, _niv, _area in CATALOGO:
    TOPICOS_PORTUGUES.setdefault(_area, []).append(_ch)
for _niv in NIVEIS:
    TOPICOS_PORTUGUES[_niv] = [c[0] for c in CATALOGO if c[2] == _niv]
# Agrupamento amigável, para o botão "crase" trazer os dois templates
TOPICOS_PORTUGUES["crase"] = ["crase_ocorrencia", "crase_regra"]
TOPICOS_PORTUGUES["regencia"] = ["regencia", "regencia_sentido"]
TOPICOS_PORTUGUES["colocacao"] = ["colocacao", "colocacao_nome"]


def listar_topicos(nivel: str = None):
    """Catálogo para o app montar os botões."""
    return [
        {"chave": ch, "rotulo": rot, "nivel": niv, "area": area}
        for ch, rot, niv, area in CATALOGO
        if nivel is None or niv == nivel
    ]


PALAVRAS_CHAVE = {
    "crase_ocorrencia": ["crase", "acento grave", "preposicao a",
                         "artigo definido feminino"],
    "crase_regra":      ["crase", "acento grave", "regencia verbal",
                         "regencia nominal"],
    "classe_palavra":   ["classes de palavras", "classe gramatical",
                         "morfologia", "substantivo", "adjetivo",
                         "adverbio", "preposicao", "conjuncao",
                         "interjeicao", "numeral"],
    "concordancia":     ["concordancia verbal", "concordancia",
                         "verbo impessoal", "voz passiva sintetica",
                         "sujeito"],
    "regencia":         ["regencia verbal", "regencia", "transitividade",
                         "verbo transitivo", "assistir", "aspirar",
                         "visar", "implicar", "preferir"],
    "regencia_sentido": ["regencia verbal", "regencia", "transitividade",
                         "mudanca de sentido"],
    "colocacao":        ["colocacao pronominal", "proclise", "enclise",
                         "mesoclise", "pronome obliquo",
                         "pronome atono"],
    "colocacao_nome":   ["colocacao pronominal", "proclise", "enclise",
                         "mesoclise"],
    "voz_verbal":       ["voz verbal", "vozes verbais", "voz passiva",
                         "voz ativa", "agente da passiva",
                         "passiva sintetica"],
    "figura_linguagem": ["figura de linguagem", "figuras de linguagem",
                         "metafora", "metonimia", "hiperbole",
                         "eufemismo", "ironia", "personificacao",
                         "antitese", "pleonasmo"],
}

CHAVES_GENERICAS = {"palavra", "palavras", "frase", "verbo", "regra",
                    "forma", "uso", "sentido", "texto"}


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
               topico: str = None, templates: list = None,
               nivel: str = None, formato: str = None):
    """
    Gera um lote de questões de português.

    `formato` controla a extensão do enunciado:
      "contextualizado"  moldura completa — padrão do SIMULADO
      "direto"           só a frase — padrão da REVISÃO por tópico

    Quando não informado, deduz pelo uso: pedir UM tópico específico
    (o botão do app) é revisão, e o enunciado sai direto; pedir vários
    é simulado, e o enunciado sai contextualizado.
    """
    if quantidade is None or quantidade <= 0:
        return []

    rng = random.Random(seed)
    disponiveis = list(TEMPLATES_PORTUGUES)

    if templates:
        pedidos = [t for t in templates if t in TEMPLATES_PORTUGUES]
        if pedidos:
            disponiveis = pedidos
    if nivel:
        n = _normalizar(nivel)
        por_nivel = [c[0] for c in CATALOGO if _normalizar(c[2]) == n]
        if por_nivel:
            disponiveis = [t for t in disponiveis if t in por_nivel]
    if topico:
        chave = _normalizar(topico).strip()
        por_area = {_normalizar(k): v for k, v in TOPICOS_PORTUGUES.items()}
        if chave in por_area:
            disponiveis = [t for t in por_area[chave]
                           if t in TEMPLATES_PORTUGUES]
        elif chave in TEMPLATES_PORTUGUES:
            disponiveis = [chave]
        else:
            casados = templates_para_topicos([topico])
            if casados:
                disponiveis = casados

    if not disponiveis:
        return []

    # Um único template pedido = o aluno clicou num botão de tópico,
    # está treinando aquele assunto. Enunciado curto e direto.
    # Vários templates = simulado. Enunciado contextualizado.
    if formato is None:
        formato = "direto" if len(disponiveis) == 1 else "contextualizado"

    posicao = 0
    questoes, tentativas, limite = [], 0, quantidade * 15
    vistos, fatos_usados = set(), set()

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        nome = disponiveis[posicao % len(disponiveis)]
        posicao += 1
        try:
            q = TEMPLATES_PORTUGUES[nome](rng, formato)
        except Exception:
            continue
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
                   topico: str = None, templates: list = None,
                   nivel: str = None, formato: str = None):
    """Devolve (questoes, gabarito) no formato que a API espera."""
    lote = gerar_lote(quantidade, seed=seed, topico=topico,
                      templates=templates, nivel=nivel, formato=formato)
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
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    print("═" * 64)
    print("  GERADOR DE PORTUGUÊS")
    print("═" * 64)
    if not alvo:
        print("\n  TÓPICOS DISPONÍVEIS:\n")
        for it in listar_topicos():
            print(f"    {it['chave']:<18} {it['rotulo']:<26} "
                  f"{it['nivel']:<12} {it['area']}")
    else:
        for q in gerar_lote(4, seed=2026, templates=[alvo]):
            print(f"\n{q['numero']}. {q['enunciado']}")
            for L, t in q["alternativas"].items():
                print(f"     {L}) {t}")
            print(f"   GABARITO: {q['gabarito']}")
            print(f"   {q['explicacao']}")
