"""
=============================================================
  NIVELIS — Gerador Procedural de Questões  v2
=============================================================

  Gera questões de matemática SEM IA: o Python calcula o
  gabarito, que é SEMPRE correto por construção. Distratores
  são os erros que um aluno cometeria de verdade.

  15 TEMPLATES — cobertura do livro "Fundamentos de
  Matemática Elementar Vol. 5 (Combinatória e Probabilidade)":

  CONTAGEM
    1. Princípio fundamental da contagem (senhas/códigos)
    2. Arranjo (pódio)
    3. Permutação circular (mesa redonda)
  ANAGRAMAS
    4. Anagrama simples (letras distintas)
    5. Anagrama com letras repetidas
    6. Anagrama com bloco de letras juntas
  COMBINAÇÕES
    7. Combinação simples (apertos de mão / duplas)
    8. Combinação dupla (comissão mista)
    9. Permutação de blocos (estante)
  BINÔMIO
   10. Coeficiente no binômio de Newton
   11. Soma de linha do triângulo de Pascal
  PROBABILIDADE
   12. Espaço equiprovável (soma de dois dados)
   13. Probabilidade condicional (urna, sem reposição)
   14. Eventos independentes (urna, COM reposição)
   15. Distribuição binomial (moedas)

  USO:
    python gerador_procedural.py              # 15 questões (1/template)
    python gerador_procedural.py 30           # 30 questões
    python gerador_procedural.py 10 probabilidade
=============================================================
"""

import sys
import re
import random
from math        import comb, perm, factorial
from fractions   import Fraction
from collections import Counter

import equilibrio_numerico as _EQ


# ──────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────

LETRAS = ["A", "B", "C", "D", "E"]


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


def _fmt_fracao(fr: Fraction) -> str:
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ══════════════════════════════════════════════════════════════════
#  METADADOS DE RESPOSTA — ver explicação equivalente em gerador_ads.py
#  Campos internos: a API não os envia ao aplicativo.
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


def _montar_questao(enunciado, correta, distratores, explicacao,
                    topico, formatador, rng, filtro=None,
                    tipo_resposta="numerica"):
    """
    Junta gabarito + 4 distratores únicos, embaralha, acha a letra.
    `filtro` opcional descarta candidatos inválidos (ex: prob > 1).
    `tipo_resposta` descreve a natureza das alternativas (metadado interno).
    Retorna None se faltar distrator único (template re-sorteia).
    """
    assert tipo_resposta in TIPOS_RESPOSTA, f"tipo inválido: {tipo_resposta}"

    unicos = []
    for d in distratores:
        if filtro and not filtro(d):
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
        "origem":         "gerador_procedural",
        # ── metadados internos (não vão para o app) ──
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
    }


def _prob_valida(fr):
    """Filtro: probabilidade tem que estar em (0, 1)."""
    return isinstance(fr, Fraction) and 0 < fr < 1


# ══════════════════════════════════════════
#  CONTAGEM
# ══════════════════════════════════════════

def gerar_pfc_senha(rng):
    """Códigos de L dígitos, 1º != 0, sem repetição: 9 * A(9, L-1)."""
    contextos = ["um cofre", "um sistema de segurança", "um cadeado digital",
                 "um aplicativo bancário"]
    for _ in range(60):
        L   = rng.choice([3, 4, 5])
        ctx = rng.choice(contextos)
        correta = 9 * perm(9, L - 1)
        distratores = [10 ** L, 9 * 10 ** (L - 1), perm(10, L), 9 ** L,
                       perm(9, L),           # tirou o zero de todas as casas
                       9 * perm(8, L - 1),   # proibiu repetir e mais alguma
                       10 ** (L - 1)]        # esqueceu uma casa inteira

        passos = " × ".join(["9"] + [str(9 - i) for i in range(L - 1)])
        VARIACOES = [
            f"{ctx.capitalize()} utiliza códigos de {L} dígitos (0 a 9). Se o primeiro "
            f"dígito não pode ser zero e os dígitos não podem se repetir, quantos "
            f"códigos diferentes podem ser formados?",
            f"Para acessar {ctx}, o usuário define uma senha numérica de {L} dígitos. "
            f"A senha não pode começar por zero nem repetir dígitos. Quantas senhas "
            f"distintas são possíveis?",
            f"Um técnico precisa cadastrar códigos de {L} algarismos em {ctx}. "
            f"Sabendo que o algarismo inicial deve ser diferente de zero e que "
            f"nenhum algarismo se repete, quantos códigos podem ser criados?",
            f"{ctx.capitalize()} gera identificadores numéricos de {L} posições, "
            f"usando os algarismos de 0 a 9 sem repetição e nunca iniciando por "
            f"zero. Qual é a quantidade total de identificadores possíveis?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"Primeiro dígito: 9 opções (1 a 9). Os seguintes excluem os já "
            f"usados, mas o zero volta a valer: {passos} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Princípio fundamental da contagem", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("pfc_senha")


def gerar_arranjo_podio(rng):
    """n competidores, 3 primeiros lugares: A(n,3)."""
    contextos = ["uma corrida de 100 metros rasos", "um torneio de xadrez",
                 "uma competição de natação", "um campeonato de e-sports"]
    for _ in range(60):
        n   = rng.randint(6, 10)
        ctx = rng.choice(contextos)
        correta = perm(n, 3)
        distratores = [comb(n, 3), n ** 3, 3 * n, (n - 1) * (n - 2) * (n - 3),
                       perm(n, 4),        # premiou quatro lugares
                       perm(n + 1, 3)]    # contou um finalista a mais

        VARIACOES = [
            f"Em {ctx} há {n} finalistas. De quantas maneiras distintas os três "
            f"primeiros lugares (ouro, prata e bronze) podem ser preenchidos?",
            f"{n} competidores disputam {ctx}. Quantos pódios diferentes são "
            f"possíveis, considerando que as três medalhas são distintas?",
            f"A final de {ctx} reúne {n} participantes. De quantos modos distintos "
            f"pode ser formada a classificação dos três primeiros colocados?",
            f"Um campeonato chega à decisão com {n} finalistas. Sabendo que a ordem "
            f"de chegada define ouro, prata e bronze, quantos resultados diferentes "
            f"o pódio pode ter?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"A ordem importa (medalhas distintas): arranjo A({n},3) = "
            f"{n} × {n - 1} × {n - 2} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Arranjos", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("arranjo_podio")


def gerar_circular(rng):
    """n pessoas em mesa redonda: (n-1)!."""
    for _ in range(60):
        n = rng.randint(4, 9)
        correta = factorial(n - 1)
        distratores = [factorial(n), n * (n - 1),
                       factorial(n - 1) // 2, factorial(n) // 2,
                       factorial(n - 2),        # fixou duas posições
                       2 * factorial(n - 1),    # contou o espelho como novo
                       (n - 1) ** 2]

        CENARIOS = [
            (f"De quantas maneiras distintas {n} pessoas podem se sentar ao redor de "
             f"uma mesa circular, considerando que disposições obtidas por rotação "
             f"são consideradas iguais?", "pessoas", "mesa"),
            (f"Uma família de {n} integrantes vai se sentar em volta de uma mesa "
             f"redonda para o jantar. De quantos modos diferentes isso pode ser "
             f"feito, se rotações da mesma disposição não contam como novas?", "integrantes", "mesa"),
            (f"Em uma reunião de diretoria, {n} conselheiros ocupam cadeiras dispostas "
             f"em círculo. Quantas disposições distintas existem, desconsiderando "
             f"rotações?", "conselheiros", "círculo"),
            (f"{n} amigos formam uma roda de conversa. Quantas configurações "
             f"diferentes da roda são possíveis, sabendo que girar todos de posição "
             f"não cria uma nova configuração?", "amigos", "roda"),
            (f"Um artesão vai montar um colar circular com {n} contas de cores "
             f"diferentes. Fixando o colar em uma posição, de quantas maneiras "
             f"distintas as contas podem ser dispostas?", "contas", "colar"),
        ]
        enunciado, obj, lugar = rng.choice(CENARIOS)
        explicacao = (
            f"Em uma permutação circular, uma das {n} posições é fixada como "
            f"referência (pois rotações não geram arranjos novos) e as demais "
            f"{n - 1} permutam livremente: ({n}−1)! = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Permutação circular", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("circular")


# ══════════════════════════════════════════
#  ANAGRAMAS
# ══════════════════════════════════════════

def gerar_anagrama_simples(rng):
    """Palavra com letras todas distintas: n! anagramas."""
    palavras = ["LIVRO", "FUSCA", "MARTELO", "TECLADO"]
    for _ in range(60):
        p = rng.choice(palavras)
        n = len(p)
        correta = factorial(n)
        # Os quatro distratores eram todos MENORES que n!, porque todos
        # nasciam de operações que erram para baixo. A resposta certa era
        # sempre o maior número da lista, e marcar a alternativa mais
        # longa acertava 100% destas questões.
        #
        # (n+1)! entra na frente e fica garantido na questão: é o erro de
        # quem conta uma letra a mais, e erra para cima.
        menores = [factorial(n - 1), n ** 2, 2 ** n, n * (n - 1)]
        # Com um só distrator acima de n!, a resposta certa era a
        # segunda maior em 100% das questões. Três acima devolvem
        # variedade de posição.
        maiores = [2 * factorial(n),                    # dobrou sem motivo
                   factorial(n) + factorial(n - 1),     # somou o caso menor
                   factorial(n + 1) // 2]               # contou os espelhos
        rng.shuffle(menores)
        rng.shuffle(maiores)
        distratores = [factorial(n + 1)] + maiores + menores

        VARIACOES = [
            f"Quantos anagramas possui a palavra {p}, que tem {n} letras todas distintas?",
            f"De quantas maneiras diferentes as {n} letras da palavra {p} podem ser "
            f"reordenadas, formando sequências distintas?",
            f"Um professor propõe que os alunos formem todas as sequências possíveis "
            f"com as letras da palavra {p}, sem repetir nenhuma letra. Quantas "
            f"sequências existem?",
            f"A palavra {p} possui {n} letras distintas. Quantas permutações dessas "
            f"letras podem ser formadas?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"Com {n} letras distintas, cada permutação é um anagrama: "
            f"{n}! = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Anagramas (permutação simples)", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("anagrama_simples")


def gerar_anagrama_repeticao(rng):
    """Palavra com letras repetidas: n! / (produto dos fatoriais)."""
    palavras = ["ARARA", "BANANA", "BATATA", "ARROZ", "SUCESSO", "CAMISA",
                "ABACAXI", "PARALELO", "ESTRELA", "COMISSAO", "TERRENO",
                "PROCESSO", "ELEMENTO", "MATEMATICA"]
    for _ in range(60):
        p = rng.choice(palavras)
        n = len(p)
        reps = [v for v in Counter(p).values() if v > 1]
        den = 1
        for r in reps:
            den *= factorial(r)
        correta = factorial(n) // den
        distratores = [
            factorial(n),                          # ignorar repetições
            factorial(n) // factorial(max(reps)),  # dividir por só um fatorial
            correta // factorial(max(reps)),       # dividiu duas vezes
            factorial(n - 1) // den,               # perdeu uma letra
            correta * 2,
            factorial(n - 1),
            correta // 2 if correta % 2 == 0 and correta > 2 else correta + n,
            factorial(n) // (den * 2),
            correta + 10,
        ]

        reps_txt = ", ".join(
            f"{letra} aparece {v} vezes"
            for letra, v in Counter(p).items() if v > 1
        )
        den_txt = " × ".join(f"{r}!" for r in reps)
        VARIACOES = [
            f"Quantos anagramas possui a palavra {p}?",
            f"De quantas maneiras distintas as letras da palavra {p} podem ser "
            f"reorganizadas?",
            f"Considerando que letras iguais são indistinguíveis entre si, quantos "
            f"anagramas diferentes a palavra {p} admite?",
            f"Um jogo de palavras pede todas as sequências distintas formadas com as "
            f"letras de {p}. Quantas sequências existem?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"A palavra tem {n} letras, mas há repetições ({reps_txt}). "
            f"Anagramas = {n}! / ({den_txt}) = {_fmt_int(factorial(n))} / "
            f"{den} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Anagramas (permutação com repetição)", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("anagrama_repeticao")


def gerar_anagrama_bloco(rng):
    """Letras repetidas iguais JUNTAS: bloco vira 1 unidade."""
    opcoes = [("SUCESSO", "S"), ("BANANA", "A"), ("BATATA", "A"), ("ARROZ", "R")]
    for _ in range(60):
        p, letra = rng.choice(opcoes)
        k = p.count(letra)
        restantes = [c for c in p if c != letra]
        unidades = len(restantes) + 1
        den = 1
        for v in Counter(restantes).values():
            if v > 1:
                den *= factorial(v)
        correta = factorial(unidades) // den

        den_total = den * factorial(k)
        anagrama_total = factorial(len(p)) // den_total
        distratores = [
            anagrama_total,                 # sem a restrição de juntas
            correta * factorial(k),         # permutar dentro do bloco (erro!)
            factorial(len(p)),              # ignorar tudo
            factorial(unidades),            # esquecer repetições restantes
            factorial(unidades - 1) * k,    # candidato extra p/ unicidade
            factorial(unidades - 1),        # colou o bloco e parou aí
            correta // factorial(k) if k > 1 else correta // 2,
        ]

        VARIACOES = [
            f"Quantos anagramas da palavra {p} têm as {k} letras '{letra}' sempre juntas?",
            f"Considerando todos os anagramas da palavra {p}, em quantos deles as {k} "
            f"letras '{letra}' aparecem em posições consecutivas?",
            f"De quantas maneiras as letras da palavra {p} podem ser reordenadas de "
            f"modo que as {k} ocorrências da letra '{letra}' fiquem lado a lado?",
            f"Um professor pede aos alunos que formem anagramas de {p} mantendo as {k} "
            f"letras '{letra}' agrupadas. Quantos anagramas atendem a essa condição?",
        ]
        enunciado = rng.choice(VARIACOES)
        expl_den = f" / {den}" if den > 1 else ""
        explicacao = (
            f"Tratando as {k} letras '{letra}' como um bloco único, restam "
            f"{len(restantes)} letras + 1 bloco = {unidades} unidades. Como "
            f"as letras do bloco são iguais, ele não permuta internamente. "
            f"Anagramas = {unidades}!{expl_den} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Anagramas (letras juntas)", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("anagrama_bloco")


# ══════════════════════════════════════════
#  COMBINAÇÕES
# ══════════════════════════════════════════

def gerar_combinacao_simples(rng):
    """Apertos de mão / duplas: C(n,2)."""
    # (grupo, o que se conta, gênero do que se conta)
    # O gênero acompanha o contexto porque define a flexão de "quantos":
    # "quantas duplas", "quantos apertos de mão". Sem isso, sobrava o
    # "quantos(as)", que fica truncado na tela.
    contextos = [
        ("pessoas em uma reunião",
         "apertos de mão são trocados se todos se cumprimentam exatamente uma vez", "m"),
        ("jogadores em um torneio",
         "partidas são necessárias para que todos se enfrentem exatamente uma vez", "f"),
        ("alunos em uma turma",
         "duplas distintas de trabalho podem ser formadas", "f"),
        ("equipes em um campeonato de pontos corridos",
         "confrontos ocorrem no primeiro turno", "m"),
        ("cidades atendidas por uma companhia aérea",
         "rotas diretas ligam cada par de cidades", "f"),
        ("computadores em uma rede ponto a ponto",
         "conexões diretas existem entre pares de máquinas", "f"),
        ("participantes de um congresso",
         "trocas de cartão ocorrem entre todos os pares", "f"),
        ("pontos distintos marcados em uma circunferência",
         "cordas podem ser traçadas ligando esses pontos", "f"),
        ("times de um grupo da Copa",
         "partidas são disputadas em turno único", "f"),
        ("vértices de um polígono convexo",
         "diagonais e lados podem ser traçados ao todo", "f"),
        ("moléculas em um experimento",
         "pares distintos podem interagir entre si", "m"),
    ]
    for _ in range(60):
        grupo, pergunta, genero = rng.choice(contextos)
        quantos = "Quantas" if genero == "f" else "Quantos"
        n = rng.randint(6, 24)      # MELHORIA 4
        correta = comb(n, 2)
        distratores = [n * (n - 1), n ** 2, n * (n + 1) // 2, 2 * n,
                       comb(n - 1, 2),   # esqueceu um do grupo
                       n,                # contou um por participante
                       n - 1]

        ABERTURAS_CS = [
            f"Há {n} {grupo}.",
            f"Considere {n} {grupo}.",
            f"Um evento reúne {n} {grupo}.",
            f"Foram contabilizados {n} {grupo}.",
            f"Em determinada situação, existem {n} {grupo}.",
        ]
        FECHOS_CS = [
            f"{quantos} {pergunta}?",
            f"Nessas condições, {quantos.lower()} {pergunta}?",
            f"Determine {quantos.lower()} {pergunta}.",
            f"Calcule {quantos.lower()} {pergunta}.",
        ]
        _ab = rng.choice(ABERTURAS_CS)
        enunciado = f"{_ab} {_juntar(_ab, rng.choice(FECHOS_CS))}"
        explicacao = (
            f"Cada par conta uma única vez (a ordem não importa): "
            f"C({n},2) = {n}×{n - 1}/2 = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Combinações", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("combinacao_simples")


def gerar_combinacao_dupla(rng):
    """Comissão com a do grupo M e b do grupo N: C(m,a)*C(n,b)."""
    contextos = [
        ("professores de Matemática", "professores de Português", "uma comissão"),
        ("engenheiros", "arquitetos", "uma equipe de projeto"),
        ("médicos", "enfermeiros", "uma equipe de plantão"),
        ("desenvolvedores", "designers", "um squad"),
        ("alunos do turno da manhã", "alunos do turno da noite", "um grupo de estudos"),
        ("jogadores de defesa", "jogadores de ataque", "uma escalação"),
        ("pesquisadores", "bolsistas", "uma banca"),
        ("músicos de sopro", "músicos de cordas", "um conjunto"),
        ("advogados", "estagiários", "uma equipe do caso"),
    ]
    ABERTURAS = [
        "Em uma instituição há {m} {g1} e {n} {g2}.",
        "Uma organização conta com {m} {g1} e {n} {g2}.",
        "Do quadro disponível, {m} são {g1} e {n} são {g2}.",
        "Um levantamento identificou {m} {g1} e {n} {g2} aptos a participar.",
        "Estão disponíveis {m} {g1} e {n} {g2}.",
        "A lista de convocáveis reúne {m} {g1} e {n} {g2}.",
    ]
    PERGUNTAS = [
        "Para formar {nome} de {t} membros, de quantos modos podemos escolher exatamente {a} {g1} e {b} {g2}?",
        "De quantas maneiras é possível montar {nome} com exatamente {a} {g1} e {b} {g2}?",
        "Quantas composições diferentes de {nome} existem, contendo exatamente {a} {g1} e {b} {g2}?",
        "Determine de quantos modos {nome} pode ser formada com exatamente {a} {g1} e {b} {g2}.",
        "Quantos grupos distintos podem ser montados com exatamente {a} {g1} e {b} {g2}?",
    ]
    for _ in range(60):
        g1, g2, nome = rng.choice(contextos)
        m = rng.randint(6, 16)      # MELHORIA 4: faixas ampliadas
        n = rng.randint(5, 14)
        a = rng.randint(2, 5)
        b = rng.randint(1, 4)
        if a > m or b > n:
            continue

        correta = comb(m, a) * comb(n, b)
        distratores = [
            comb(m, a) + comb(n, b),
            comb(m + n, a + b),
            perm(m, a) * comb(n, b),
            comb(m, b) * comb(n, a) if (b <= m and a <= n) else correta + 1,
            comb(m, a) * comb(n, b + 1) if b + 1 <= n else comb(m, a),
            comb(m - 1, a) * comb(n, b),      # esqueceu um do primeiro grupo
            comb(m, a) * perm(n, b),          # ordenou o segundo grupo
        ]

        # MONTAGEM POR PARTES (melhoria 2): abertura e pergunta são frases
        # completas; os slots recebem apenas substantivos já flexionados,
        # então não há risco de concordância cruzada.
        _ab = rng.choice(ABERTURAS).format(m=m, n=n, g1=g1, g2=g2)
        _pg = rng.choice(PERGUNTAS).format(nome=nome, t=a + b, a=a, b=b, g1=g1, g2=g2)
        enunciado = f"{_ab} {_juntar(_ab, _pg)}"
        explicacao = (
            f"Escolhas independentes: C({m},{a}) = {comb(m, a)} e "
            f"C({n},{b}) = {comb(n, b)}. Pelo princípio multiplicativo: "
            f"{comb(m, a)} × {comb(n, b)} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Combinações", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("combinacao_dupla")


def gerar_permutacao_blocos(rng):
    """Livros por disciplina juntos: 3! * n1! * n2! * n3!."""
    pool = ["Matemática", "Física", "Química", "História",
            "Biologia", "Geografia", "Português"]
    for _ in range(60):
        d1, d2, d3 = rng.sample(pool, 3)
        n1, n2, n3 = rng.randint(2, 5), rng.randint(2, 5), rng.randint(2, 4)
        total = n1 + n2 + n3

        correta = factorial(3) * factorial(n1) * factorial(n2) * factorial(n3)
        distratores = [
            factorial(n1) * factorial(n2) * factorial(n3),
            factorial(total),
            factorial(3) * (n1 * n2 * n3),
            factorial(n1) + factorial(n2) + factorial(n3),
            factorial(total) // factorial(3),     # dividiu pelos blocos
            factorial(4) * factorial(n1) * factorial(n2) * factorial(n3),
            factorial(total - 1),                 # fixou um elemento
        ]

        VARIACOES = [
            f"Um estudante possui {n1} livros de {d1}, {n2} de {d2} e {n3} de {d3}. "
            f"De quantas maneiras esses {total} livros podem ser organizados numa "
            f"prateleira, se os de cada disciplina devem ficar juntos?",
            f"Uma biblioteca vai expor {total} obras: {n1} de {d1}, {n2} de {d2} e "
            f"{n3} de {d3}. Quantas disposições diferentes são possíveis em uma "
            f"estante única, mantendo cada disciplina agrupada?",
            f"Um professor organiza {n1} apostilas de {d1}, {n2} de {d2} e {n3} de "
            f"{d3} sobre uma bancada, em fila. Se as apostilas de uma mesma matéria "
            f"não podem ser separadas, de quantos modos ele pode arrumá-las?",
            f"Em uma feira de ciências, {total} materiais serão dispostos lado a lado: "
            f"{n1} de {d1}, {n2} de {d2} e {n3} de {d3}. Quantas ordenações existem, "
            f"exigindo que materiais da mesma área fiquem sempre adjacentes?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"Os 3 blocos permutam entre si: 3! = 6. Dentro de cada bloco: "
            f"{n1}! = {factorial(n1)}, {n2}! = {factorial(n2)}, "
            f"{n3}! = {factorial(n3)}. Total: 6 × {factorial(n1)} × "
            f"{factorial(n2)} × {factorial(n3)} = {_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Permutação com restrição (blocos)", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("permutacao_blocos")


# ══════════════════════════════════════════
#  BINÔMIO DE NEWTON
# ══════════════════════════════════════════

def gerar_binomio_coeficiente(rng):
    """Coeficiente de x^(n-k) y^k em (x + c*y)^n: C(n,k)*c^k."""
    for _ in range(60):
        n = rng.randint(4, 9)
        k = rng.randint(2, n - 2)
        c = rng.choice([2, 3])
        correta = comb(n, k) * c ** k
        # Mesmo problema dos anagramas: o coeficiente certo é um produto,
        # e os distratores eram seus fatores — todos menores. O primeiro
        # da lista usa ARRANJO no lugar de combinação (erro clássico de
        # esquecer o k! do denominador) e erra sempre para cima.
        distratores = [
            comb(n, k) * factorial(k) * c ** k,
            comb(n, k),
            c ** k,
            comb(n, k) * c,
            comb(n, k) * c ** (n - k),
            comb(n, k - 1) * c ** k,
            comb(n, k) * c ** (k + 1),    # errou o expoente para cima
            comb(n + 1, k) * c ** k,      # leu um grau a mais
        ]

        VARIACOES = [
            f"No desenvolvimento de (x + {c}y)^{n}, qual é o coeficiente do termo "
            f"em x^{n - k} y^{k}?",
            f"Expandindo o binômio (x + {c}y)^{n}, determine o coeficiente numérico "
            f"que acompanha x^{n - k} y^{k}.",
            f"Considere o polinômio resultante da expansão de (x + {c}y)^{n}. Qual "
            f"número multiplica o termo x^{n - k} y^{k}?",
            f"Ao aplicar o binômio de Newton em (x + {c}y)^{n}, qual é o coeficiente "
            f"do termo cujo grau em x é {n - k} e em y é {k}?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"Termo geral: C({n},{k}) · x^{n - k} · ({c}y)^{k}. O coeficiente "
            f"é C({n},{k}) · {c}^{k} = {comb(n, k)} × {c ** k} = "
            f"{_fmt_int(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Binômio de Newton", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("binomio_coeficiente")


def gerar_pascal_linha(rng):
    """Soma da linha n do triângulo de Pascal: 2^n."""
    for _ in range(60):
        n = rng.randint(3, 12)
        correta = 2 ** n
        distratores = [2 ** (n - 1), 2 ** (n + 1), n ** 2, 2 * n,
                       2 ** n + 1,        # contou o topo duas vezes
                       3 ** n,            # trocou a base
                       2 ** (n + 2)]

        VARIANTES = [
            (f"No triângulo de Pascal, considerando o topo (o número 1 isolado) como "
             f"a linha 0, qual é a soma de todos os elementos da linha {n}?",
             f"A soma dos elementos da linha n do triângulo de Pascal equivale a "
             f"C(n,0)+C(n,1)+...+C(n,n), que vale 2^n. Para a linha {n}, isso dá {_fmt_int(correta)}."),
            (f"Um conjunto possui {n} elementos distintos. Quantos subconjuntos "
             f"(incluindo o vazio e o próprio conjunto) podem ser formados?",
             f"Cada elemento pode estar ou não no subconjunto, gerando 2 escolhas por "
             f"elemento. O total de subconjuntos de um conjunto com {n} elementos é "
             f"2^{n} = {_fmt_int(correta)}."),
            (f"Qual é o valor da soma C({n},0) + C({n},1) + C({n},2) + ... + C({n},{n})?",
             f"Essa soma corresponde ao total de subconjuntos possíveis e, pelo binômio "
             f"de Newton aplicado a (1+1)^{n}, resulta em 2^{n} = {_fmt_int(correta)}."),
            (f"No desenvolvimento de (a + b)^{n}, qual é a soma de todos os "
             f"coeficientes binomiais do polinômio resultante?",
             f"Substituindo a = b = 1 no binômio, a soma dos coeficientes é "
             f"(1+1)^{n} = 2^{n} = {_fmt_int(correta)}."),
        ]
        enunciado, explicacao = rng.choice(VARIANTES)
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Triângulo de Pascal", _fmt_int, rng)
        if q:
            return q
    raise RuntimeError("pascal_linha")


# ══════════════════════════════════════════
#  PROBABILIDADE
# ══════════════════════════════════════════

def gerar_prob_dados(rng):
    """Dois dados, P(soma = s). Casos favoráveis = 6 - |s - 7|."""
    for _ in range(60):
        s = rng.randint(4, 10)
        casos = 6 - abs(s - 7)
        correta = Fraction(casos, 36)
        distratores = [
            Fraction(casos + 1, 36),
            Fraction(max(casos - 1, 1), 36),
            Fraction(s, 36),
            Fraction(1, 6) if correta != Fraction(1, 6) else Fraction(1, 12),
            Fraction(casos, 12),              # contou 12 resultados possíveis
            Fraction(casos, 72),              # dobrou o espaço amostral
            Fraction(max(casos - 2, 1), 36),
        ]

        CENARIOS = [
            ("Um dado cúbico não viciado é lançado duas vezes.", "a soma dos resultados ser igual a {s}"),
            ("Dois dados honestos de seis faces são lançados simultaneamente.", "a soma das faces voltadas para cima ser {s}"),
            ("Em um jogo de tabuleiro, o jogador lança dois dados a cada rodada.", "o jogador obter soma {s} em uma rodada"),
            ("Uma máquina sorteia, de forma independente, dois números inteiros de 1 a 6.", "a soma dos dois números sorteados ser {s}"),
            ("Num cassino, a aposta é feita sobre o resultado do lançamento de dois dados equilibrados.", "a soma apostada de {s} ocorrer"),
        ]
        ABERTURAS = [
            "Qual é a probabilidade de {ev}?",
            "Nessas condições, qual a probabilidade de {ev}?",
            "A probabilidade de {ev} é:",
            "Determine a probabilidade de {ev}.",
        ]
        ctx, ev_tpl = rng.choice(CENARIOS)
        pergunta = rng.choice(ABERTURAS).format(ev=ev_tpl.format(s=s))
        enunciado = f"{ctx} {_juntar(ctx, pergunta)}"
        explicacao = (
            f"Ao lançar dois dados, o espaço amostral tem 6 × 6 = 36 pares "
            f"equiprováveis. Os pares cuja soma vale {s} totalizam {casos}. "
            f"Dividindo, a probabilidade é {_fmt_fracao(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Probabilidade (espaço equiprovável)",
                            _fmt_fracao, rng, filtro=_prob_valida,
                            tipo_resposta="fracao")
        if q:
            return q
    raise RuntimeError("prob_dados")


def gerar_prob_condicional(rng):
    """Urna sem reposição: P(2ª = Y | 1ª = X) = v/(total-1)."""
    cores = [("azuis", "azul", "vermelhas", "vermelha"),
             ("verdes", "verde", "amarelas", "amarela"),
             ("pretas", "preta", "brancas", "branca")]
    objetos = [("bolas", "bola"), ("fichas", "ficha")]
    for _ in range(60):
        ca_pl, ca_sg, cv_pl, cv_sg = rng.choice(cores)
        obj_pl, obj_sg = rng.choice(objetos)
        a = rng.randint(2, 12)      # MELHORIA 4
        v = rng.randint(2, 14)
        total = a + v

        correta = Fraction(v, total - 1)
        distratores = [
            Fraction(v, total),
            Fraction(v - 1, total - 1),
            Fraction(a, total - 1),
            Fraction(max(a - 1, 1), total - 1),
        ]

        VARIACOES = [
            f"Uma urna contém {a} {obj_pl} {ca_pl} e {v} {obj_pl} {cv_pl}. Duas "
            f"{obj_pl} são retiradas sucessivamente, sem reposição. Qual a "
            f"probabilidade de a segunda ser {cv_sg}, dado que a primeira foi {ca_sg}?",
            f"Em uma caixa há {a} {obj_pl} {ca_pl} e {v} {obj_pl} {cv_pl}. Retira-se "
            f"uma {obj_sg} de cada vez, sem devolvê-la. Sabendo que a primeira "
            f"retirada foi {ca_sg}, qual a probabilidade de a segunda ser {cv_sg}?",
            f"Um sorteio usa {a} {obj_pl} {ca_pl} e {v} {obj_pl} {cv_pl}, retiradas "
            f"uma após a outra e sem reposição. Considerando que já saiu uma "
            f"{obj_sg} {ca_sg} no primeiro sorteio, qual a probabilidade de sair uma "
            f"{cv_sg} no segundo?",
            f"De um recipiente com {a} {obj_pl} {ca_pl} e {v} {obj_pl} {cv_pl} são "
            f"retiradas duas {obj_pl} em sequência, sem reposição. Qual é a "
            f"probabilidade condicional de a segunda ser {cv_sg}, sabendo que a "
            f"primeira foi {ca_sg}?",
        ]
        enunciado = rng.choice(VARIACOES)
        fr_bruta = f"{v}/{total - 1}"
        fr_final = _fmt_fracao(correta)
        explicacao = (
            f"Após sair uma {obj_sg} {ca_sg}, restam {a - 1} {ca_pl} e "
            f"{v} {cv_pl}, total {total - 1}. P = {fr_bruta}"
            + (f" = {fr_final}." if fr_bruta != fr_final else ".")
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Probabilidade condicional",
                            _fmt_fracao, rng, filtro=_prob_valida,
                            tipo_resposta="fracao")
        if q:
            return q
    raise RuntimeError("prob_condicional")


def gerar_prob_independentes(rng):
    """
    Urna COM reposição: P(duas da cor V) = (v/total)^2.

    O objeto e a cor andam JUNTOS na mesma tupla porque precisam concordar
    em gênero: "cartões brancos" e "fichas brancas". Sorteá-los em listas
    separadas produzia "cartões brancas".
    """
    # (plural_obj, singular_obj, cor_plural, cor_singular)
    OBJETOS_E_CORES = [
        # femininos
        ("bolas", "bola", "azuis", "azul"),
        ("bolas", "bola", "vermelhas", "vermelha"),
        ("bolas", "bola", "verdes", "verde"),
        ("bolas", "bola", "brancas", "branca"),
        ("fichas", "ficha", "azuis", "azul"),
        ("fichas", "ficha", "vermelhas", "vermelha"),
        ("fichas", "ficha", "verdes", "verde"),
        ("fichas", "ficha", "brancas", "branca"),
        ("bolinhas", "bolinha", "azuis", "azul"),
        ("bolinhas", "bolinha", "amarelas", "amarela"),
        # masculinos
        ("cartões", "cartão", "azuis", "azul"),
        ("cartões", "cartão", "vermelhos", "vermelho"),
        ("cartões", "cartão", "verdes", "verde"),
        ("cartões", "cartão", "brancos", "branco"),
        ("chips", "chip", "azuis", "azul"),
        ("chips", "chip", "vermelhos", "vermelho"),
    ]
    cores = [("azuis", "azul"), ("vermelhas", "vermelha"),
             ("verdes", "verde"), ("brancas", "branca")]
    for _ in range(60):
        obj_pl, obj_sg, cor_pl, cor_sg = rng.choice(OBJETOS_E_CORES)
        v = rng.randint(2, 9)       # MELHORIA 4
        outras = rng.randint(3, 12)
        total = v + outras

        base = Fraction(v, total)
        correta = base * base
        distratores = [
            base,
            Fraction(v, total) * Fraction(max(v - 1, 1), total - 1),  # sem reposição (erro clássico)
            Fraction(outras, total) * Fraction(outras, total),
            Fraction(v, total * 2),
            Fraction(2 * v, total) if 2 * v < total else Fraction(1, total),
        ]

        # Gênero derivado da própria tupla, para as flexões acompanharem
        fem = cor_sg.endswith("a") or obj_pl in ("bolas", "fichas", "bolinhas")
        art_ind   = "uma" if fem else "um"        # uma / um
        art_def   = "a"   if fem else "o"         # a / o
        pron       = "ela" if fem else "ele"
        retirada   = "retirada"   if fem else "retirado"
        devolvida  = "devolvida"  if fem else "devolvido"
        recolocada = "recolocada" if fem else "recolocado"
        outra      = "outra"      if fem else "outro"
        ambas      = "ambas"      if fem else "ambos"
        as_duas    = "as duas"    if fem else "os dois"
        sorteadas  = "sorteadas"  if fem else "sorteados"

        VARIACOES = [
            f"Uma urna contém {v} {obj_pl} {cor_pl} e {outras} {obj_pl} de outras "
            f"cores. {art_ind.capitalize()} {obj_sg} é {retirada}, sua cor é anotada "
            f"e {pron} é {devolvida} à urna; em seguida, retira-se {outra}. "
            f"Qual a probabilidade de {ambas} serem {cor_pl}?",

            f"Em um sorteio, uma caixa guarda {v} {obj_pl} {cor_pl} e {outras} "
            f"{obj_pl} de outras cores. Sorteia-se {art_ind} {obj_sg}, {pron} é "
            f"{recolocada} na caixa e um novo sorteio é feito. Qual a probabilidade "
            f"de {as_duas} {obj_pl} {sorteadas} serem {cor_pl}?",

            f"Um recipiente contém {v} {obj_pl} {cor_pl} e {outras} {obj_pl} de "
            f"outras cores. Retira-se {art_ind} {obj_sg} ao acaso, anota-se a cor e "
            f"{pron} é {devolvida} ao recipiente antes da segunda retirada. Qual a "
            f"probabilidade de {as_duas} retiradas resultarem em {obj_pl} {cor_pl}?",

            f"Uma máquina de prêmios contém {v} {obj_pl} {cor_pl} e {outras} {obj_pl} "
            f"de outras cores. Após cada retirada, {art_def} {obj_sg} volta para a "
            f"máquina. Retirando {'duas' if fem else 'dois'} {obj_pl} nessas condições, "
            f"qual a probabilidade de {ambas} serem {cor_pl}?",
        ]
        enunciado = rng.choice(VARIACOES)
        explicacao = (
            f"Com reposição, as retiradas são independentes: "
            f"P = ({v}/{total}) × ({v}/{total}) = {_fmt_fracao(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Eventos independentes",
                            _fmt_fracao, rng, filtro=_prob_valida,
                            tipo_resposta="fracao")
        if q:
            return q
    raise RuntimeError("prob_independentes")


def gerar_binomial_moedas(rng):
    """Ensaios de Bernoulli com p=1/2: P(exatamente k sucessos) = C(n,k)/2^n."""
    # (contexto, evento_sing, evento_plur, termo_sing, termo_plur)
    # Os eventos vêm em duas versões para concordar com k = 1 ou k > 1.
    CENARIOS = [
        ("Uma moeda honesta é lançada {n} vezes.",
         "sair exatamente {k} cara", "sair exatamente {k} caras",
         "cara", "caras"),
        ("Em um jogo, um dado honesto é lançado {n} vezes e anota-se apenas se o "
         "resultado é par ou ímpar.",
         "obter exatamente {k} resultado par", "obter exatamente {k} resultados pares",
         "resultado par", "resultados pares"),
        ("Um sistema de testes automatizados executa {n} verificações "
         "independentes, cada uma com 50% de chance de passar.",
         "exatamente {k} verificação passar", "exatamente {k} verificações passarem",
         "aprovação", "aprovações"),
        ("Uma pesquisa entrevista {n} pessoas escolhidas ao acaso sobre uma "
         "proposta que divide a opinião pública igualmente.",
         "exatamente {k} delas se declarar favorável",
         "exatamente {k} delas se declararem favoráveis",
         "resposta favorável", "respostas favoráveis"),
        ("Um casal planeja ter {n} filhos, e a probabilidade de cada um ser "
         "menino é de 50%.",
         "exatamente {k} deles ser menino", "exatamente {k} deles serem meninos",
         "menino", "meninos"),
        ("Uma linha de produção testa {n} peças, e cada uma tem a mesma chance "
         "de ser aprovada ou reprovada.",
         "exatamente {k} peça ser aprovada", "exatamente {k} peças serem aprovadas",
         "aprovação", "aprovações"),
    ]
    ABERTURAS = [
        "Qual é a probabilidade de {evento}?",
        "Nessas condições, qual a probabilidade de {evento}?",
        "Determine a probabilidade de {evento}.",
        "A probabilidade de {evento} é igual a:",
    ]

    for _ in range(80):
        n = rng.randint(4, 9)
        k = rng.randint(1, n - 1)
        correta = Fraction(comb(n, k), 2 ** n)
        # A resposta certa guarda o denominador 2^n inteiro (21/128),
        # enquanto os distratores reduziam para frações curtas (2/7,
        # 1/128): a alternativa mais longa era a certa em 90% dos casos.
        #
        # Os três primeiros da lista — garantidos na questão — erram no
        # EXPOENTE ou na combinação e mantêm o mesmo porte da resposta.
        distratores = [
            Fraction(comb(n, k), 2 ** (n - 1)),
            Fraction(comb(n, k) + 1, 2 ** n),
            Fraction(comb(n, k), 2 ** (n + 1)),
            Fraction(1, 2 ** n),
            Fraction(comb(n, k), 2 ** k) if 2 ** k > comb(n, k) else Fraction(k, 2 * n),
            Fraction(k, n),
            Fraction(comb(n, k), n * n) if n * n > comb(n, k) else Fraction(1, n),
            Fraction(max(comb(n, k) - 1, 1), 2 ** n),
        ]

        contexto, ev_sing, ev_plur, termo_s, termo_p = rng.choice(CENARIOS)
        evento    = (ev_sing if k == 1 else ev_plur).format(k=k)
        palavra_k = termo_s if k == 1 else termo_p
        pergunta = rng.choice(ABERTURAS).format(evento=evento)
        _ctx = contexto.format(n=n)
        enunciado = f"{_ctx} {_juntar(_ctx, pergunta)}"

        explicacao = (
            f"Trata-se de {n} ensaios independentes com probabilidade 1/2 cada. "
            f"Cada sequência específica tem probabilidade 1/2^{n} = 1/{2 ** n}, e "
            f"existem C({n},{k}) = {comb(n, k)} "
            f"{_plural(comb(n, k), 'sequência', 'sequências')} com {k} {palavra_k}. "
            f"Multiplicando, a probabilidade é {_fmt_fracao(correta)}."
        )
        q = _montar_questao(enunciado, correta, distratores, explicacao,
                            "Distribuição binomial",
                            _fmt_fracao, rng, filtro=_prob_valida,
                            tipo_resposta="fracao")
        if q:
            return q
    raise RuntimeError("binomial_moedas")


# ══════════════════════════════════════════════════════════
#  PROGRESSÕES
# ══════════════════════════════════════════════════════════
#
#  As respostas são CALCULADAS, não tabeladas — o que se
#  verifica são as fórmulas, registradas em
#  matematica/_fontes.md.
#
#  Os distratores reproduzem erros reais: expoente n em vez
#  de n−1, esquecer a divisão por 2 na soma da PA, aplicar
#  soma infinita com |q| ≥ 1.
#

def _fmt(v):
    """Formata número no padrão brasileiro, sem casas inúteis."""
    from fractions import Fraction
    if isinstance(v, Fraction):
        if v.denominator == 1:
            v = v.numerator
        else:
            v = float(v)
    if isinstance(v, float) and abs(v - round(v)) < 1e-9:
        v = int(round(v))
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def gerar_pa_termo(rng):
    """Termo geral de uma PA — aₙ = a₁ + (n−1)·r."""
    a1 = rng.choice([2, 3, 5, 7, 8, 10, 12, 15, 20])
    r = rng.choice([2, 3, 4, 5, 6, 7, -3, -4, -5])
    n = rng.choice([8, 10, 12, 15, 18, 20, 25, 30])
    an = a1 + (n - 1) * r

    primeiros = ", ".join(str(a1 + i * r) for i in range(4))
    CENARIOS = [
        f"Considere a progressão aritmética ({primeiros}, ...).",
        f"Uma progressão aritmética tem primeiro termo {a1} e razão {r}.",
        f"Os primeiros termos de uma sequência são ({primeiros}, ...), "
        f"que formam uma progressão aritmética.",
        f"Em uma progressão aritmética, o primeiro termo vale {a1} e a "
        f"razão vale {r}.",
    ]
    COMANDOS = [
        f"O termo de ordem {n} dessa progressão é:",
        f"O {n}º termo dessa progressão vale:",
        f"Determine o termo que ocupa a posição {n}.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = an
    distratores = [
        a1 + n * r,              # usou n em vez de n−1
        # Aplicar exponenciação numa PA gera número de ordem de grandeza
        # absurda — 56.687 vezes o gabarito, no pior caso. Um distrator
        # assim é descartado de imediato, e o teste 9 acusa.
        a1 + (n - 2) * r,
        a1 - (n - 1) * r,        # trocou o sinal da razão
        (n - 1) * r,             # esqueceu o primeiro termo
        a1 + (n + 1) * r,
        an + r,
        an - r,
    ]
    distratores = [d for d in distratores if d != correta]

    explicacao = (
        f"O termo geral da progressão aritmética é aₙ = a₁ + (n − 1)·r. "
        f"Com a₁ = {a1}, r = {r} e n = {n}: "
        f"a{n} = {a1} + ({n} − 1)·({r}) = {a1} + {(n-1)*r} = {an}. "
        f"O erro mais comum é usar n no lugar de n − 1, o que daria "
        f"{a1 + n * r}."
    )
    q = _montar_questao(enunciado, correta, distratores, explicacao,
                        "Matemática (progressão aritmética)", _fmt, rng)
    return q


def gerar_pa_soma(rng):
    """Soma dos n primeiros termos de uma PA — Sₙ = n·(a₁ + aₙ)/2."""
    a1 = rng.choice([1, 2, 3, 4, 5, 6, 10])
    r = rng.choice([2, 3, 4, 5, 6])
    n = rng.choice([10, 12, 15, 20, 25, 30, 40, 50])
    an = a1 + (n - 1) * r
    sn = n * (a1 + an) // 2

    # O cenário precisa MENCIONAR n: o teste de coerência acusa número
    # que aparece só na pergunta e não no contexto — e com razão, porque
    # um dado solto no comando é sinal de enunciado mal montado.
    CENARIOS = [
        f"Considere os {n} primeiros termos da progressão aritmética de "
        f"primeiro termo {a1} e razão {r}.",
        f"Uma progressão aritmética começa em {a1} e cresce de {r} em "
        f"{r}. Tomam-se seus {n} primeiros termos.",
        f"Em uma sequência aritmética, a₁ = {a1} e r = {r}. Considere "
        f"seus {n} primeiros termos.",
        f"Um plano de economia guarda {a1} reais no primeiro mês e "
        f"aumenta {r} reais a cada mês seguinte, durante {n} meses.",
    ]
    COMANDOS = [
        f"A soma desses termos é:",
        f"A soma dos {n} termos é:",
        f"O total acumulado corresponde a:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = sn
    distratores = [
        n * (a1 + an),            # esqueceu dividir por 2
        (a1 + an) // 2,           # esqueceu multiplicar por n
        n * a1 + r,
        n * an,
        sn + an,
        sn - a1,
        n * (a1 + an + r) // 2,
    ]
    distratores = [d for d in distratores if d != correta]

    explicacao = (
        f"Primeiro calcula-se o último termo: a{n} = {a1} + ({n} − 1)·"
        f"{r} = {an}. A soma é Sₙ = n·(a₁ + aₙ)/2 = {n}·({a1} + {an})/2 "
        f"= {n}·{a1+an}/2 = {sn}. Esquecer a divisão por 2 é o erro mais "
        f"frequente, e levaria a {n * (a1 + an)}."
    )
    q = _montar_questao(enunciado, correta, distratores, explicacao,
                        "Matemática (progressão aritmética)", _fmt, rng)
    return q


def gerar_pg_termo(rng):
    """Termo geral de uma PG — aₙ = a₁·q^(n−1)."""
    a1 = rng.choice([1, 2, 3, 4, 5])
    q_raz = rng.choice([2, 3, 2, 2, 3, -2])
    n = rng.choice([5, 6, 7, 8, 9])
    an = a1 * q_raz ** (n - 1)

    primeiros = ", ".join(str(a1 * q_raz ** i) for i in range(4))
    CENARIOS = [
        f"Considere a progressão geométrica ({primeiros}, ...).",
        f"Uma progressão geométrica tem primeiro termo {a1} e razão "
        f"{q_raz}.",
        f"Os primeiros termos de uma sequência são ({primeiros}, ...), "
        f"que formam uma progressão geométrica.",
        f"Em uma progressão geométrica, a₁ = {a1} e q = {q_raz}.",
    ]
    COMANDOS = [
        f"O termo de ordem {n} dessa progressão é:",
        f"O {n}º termo dessa progressão vale:",
        f"Determine o termo que ocupa a posição {n}.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = an
    distratores = [
        a1 * q_raz ** n,          # usou n em vez de n−1
        a1 * q_raz ** (n - 2),
        a1 + (n - 1) * q_raz,     # aplicou fórmula da PA
        a1 * q_raz * (n - 1),     # multiplicou em vez de exponenciar
        abs(an) if an < 0 else -an,
        2 * an,                   # contou o termo em dobro
        an + a1,                  # somou o primeiro termo ao final
        an - a1,
    ]
    distratores = [d for d in distratores if d != correta]

    explicacao = (
        f"O termo geral da progressão geométrica é aₙ = a₁·q^(n−1). "
        f"Com a₁ = {a1}, q = {q_raz} e n = {n}: "
        f"a{n} = {a1}·({q_raz})^({n} − 1) = {a1}·({q_raz})^{n-1} = {an}. "
        f"O expoente é n − 1, não n — usar n daria "
        f"{a1 * q_raz ** n}."
    )
    q = _montar_questao(enunciado, correta, distratores, explicacao,
                        "Matemática (progressão geométrica)", _fmt, rng)
    return q


def gerar_pg_soma_infinita(rng):
    """
    Soma de uma PG infinita — S = a₁/(1 − q), só para |q| < 1.

    Metade das questões apresenta uma PG DIVERGENTE, em que a soma não
    existe: é a armadilha mais cobrada do assunto.
    """
    from fractions import Fraction
    converge = rng.random() < 0.6

    if converge:
        a1 = rng.choice([1, 2, 3, 4, 6, 8, 10, 12])
        q_raz = rng.choice([Fraction(1, 2), Fraction(1, 3), Fraction(1, 4),
                            Fraction(2, 3), Fraction(1, 5)])
        soma = Fraction(a1) / (1 - q_raz)
        # A soma de uma PG de razão racional é um racional EXATO. Sair
        # com "0,67" declarava tipo_resposta="fracao" e entregava
        # decimal — além de arredondar uma resposta que não precisa ser
        # arredondada, e de dar às alternativas dois formatos diferentes
        # ("6" exato ao lado de "0,67" truncado).
        primeiros = ", ".join(
            _fmt_fracao(Fraction(a1) * q_raz ** i) for i in range(3))
        CENARIOS = [
            f"Considere a progressão geométrica infinita ({primeiros}, "
            f"...), de razão {_fmt_fracao(q_raz)}.",
            f"Uma progressão geométrica infinita tem primeiro termo "
            f"{a1} e razão {q_raz.numerator}/{q_raz.denominator}.",
        ]
        enunciado = (f"{rng.choice(CENARIOS)} A soma de seus infinitos "
                     f"termos é:")
        correta = soma
        distratores = [
            Fraction(a1) / (1 + q_raz),
            Fraction(a1) * (1 - q_raz),
            Fraction(a1) / q_raz,
            Fraction(a1),
            soma + a1,
            Fraction(1) / (1 - q_raz),
        ]
        distratores = [d for d in distratores if d != correta]
        explicacao = (
            f"A soma de uma progressão geométrica infinita existe apenas "
            f"quando |q| < 1, e vale S = a₁/(1 − q). Aqui a₁ = {a1} e "
            f"q = {q_raz.numerator}/{q_raz.denominator}, então "
            f"S = {a1}/(1 − {q_raz.numerator}/{q_raz.denominator}) = "
            f"{_fmt_fracao(soma)}."
        )
        formatador = _fmt_fracao
    else:
        a1 = rng.choice([1, 2, 3, 5])
        q_raz = rng.choice([2, 3, 4, -2, -3])
        primeiros = ", ".join(str(a1 * q_raz ** i) for i in range(4))
        CENARIOS = [
            f"Considere a progressão geométrica infinita ({primeiros}, "
            f"...), de razão {q_raz}.",
            f"Uma progressão geométrica infinita tem primeiro termo "
            f"{a1} e razão {q_raz}.",
        ]
        enunciado = (f"{rng.choice(CENARIOS)} Sobre a soma de seus "
                     f"infinitos termos, é correto afirmar que:")
        correta = "não existe, pois a série diverge"
        distratores = [
            f"vale {_fmt(a1 / (1 - q_raz))}",
            f"vale {_fmt(a1 / (1 + q_raz))}" if q_raz != -1 else "vale zero",
            f"vale {_fmt(a1)}",
            "vale zero, pois os termos se anulam",
            f"vale {_fmt(a1 * q_raz)}",
        ]
        explicacao = (
            f"A soma de uma progressão geométrica infinita SÓ EXISTE "
            f"quando |q| < 1, e aplicar S = a₁/(1 − q) fora dessa "
            f"condição é o erro clássico do assunto. Aqui q = {q_raz}, e "
            f"|{q_raz}| ≥ 1: a série diverge, e a soma não existe."
        )
        formatador = str

    # Quando a série diverge, a resposta é textual — daí o tipo variável.
    q = _montar_questao(enunciado, correta, distratores, explicacao,
                        "Matemática (progressão geométrica)", formatador, rng,
                        tipo_resposta="fracao" if converge else "textual")
    if q:
        # Sem "_fato" para o caso convergente: a soma é calculada e cada
        # progressão é um exercício distinto. Marcar o template inteiro
        # como um fato só fazia o simulado aceitar uma única questão de
        # PG infinita por caderno.
        if not converge:
            q["_fato"] = "pg_infinita:diverge"
    return q


def gerar_pg_classificacao(rng):
    """
    Classificar uma PG exige olhar razão E sinal dos termos.

    q > 1 com termos negativos produz sequência DECRESCENTE — é o ponto
    que a prova cobra.
    """
    from fractions import Fraction
    CASOS = [
        (3, 2, "crescente", "razão maior que 1 e termos positivos"),
        (-3, 2, "decrescente", "razão maior que 1, mas termos negativos: "
         "os valores ficam cada vez menores"),
        (81, Fraction(1, 3), "decrescente", "razão entre 0 e 1 com termos "
         "positivos"),
        (-81, Fraction(1, 3), "crescente", "razão entre 0 e 1 com termos "
         "negativos: os valores se aproximam de zero, ou seja, crescem"),
        (2, -3, "oscilante", "razão negativa, o que alterna o sinal dos "
         "termos"),
        (5, 1, "constante", "razão igual a 1"),
    ]
    a1, q_raz, classe, motivo = rng.choice(CASOS)
    termos = [Fraction(a1) * Fraction(q_raz) ** i for i in range(4)]
    primeiros = ", ".join(_fmt(t) for t in termos)

    CENARIOS = [
        f"Considere a progressão geométrica ({primeiros}, ...).",
        f"Uma sequência tem os seguintes primeiros termos: "
        f"({primeiros}, ...), formando uma progressão geométrica.",
        f"Os quatro primeiros termos de uma progressão geométrica são "
        f"({primeiros}).",
    ]
    COMANDOS = [
        "Essa progressão é classificada como:",
        "Assinale a alternativa que a classifica corretamente.",
        "Quanto à sua classificação, trata-se de progressão:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = classe
    distratores = [c for c in ["crescente", "decrescente", "oscilante",
                               "constante"] if c != classe]
    distratores += ["alternante convergente", "estacionária"]

    # A explicação termina no RESULTADO, não em comentário — o teste de
    # português verifica isso, e com razão: o aluno lê a última linha.
    explicacao = (
        f"Classificar uma progressão geométrica exige olhar a razão "
        f"JUNTO com o sinal dos termos — razão maior que 1 com termos "
        f"negativos produz sequência decrescente, não crescente. "
        f"Aqui a progressão tem {motivo}, portanto é {classe}."
    )
    # Resposta TEXTUAL: o teste de português só exige número no fim da
    # explicação quando a resposta é numérica, e o metadado informa isso.
    q = _montar_questao(enunciado, correta, distratores, explicacao,
                        "Matemática (progressão geométrica)", str, rng,
                        tipo_resposta="textual")
    if q:
        q["_fato"] = f"pg_classe:{classe}"
    return q


# ──────────────────────────────────────────
#  REGISTRO E GERAÇÃO
# ──────────────────────────────────────────

TEMPLATES = {
    "pfc_senha":            gerar_pfc_senha,
    "arranjo_podio":        gerar_arranjo_podio,
    "circular":             gerar_circular,
    "anagrama_simples":     gerar_anagrama_simples,
    "anagrama_repeticao":   gerar_anagrama_repeticao,
    "anagrama_bloco":       gerar_anagrama_bloco,
    "combinacao_simples":   gerar_combinacao_simples,
    "combinacao_dupla":     gerar_combinacao_dupla,
    "permutacao_blocos":    gerar_permutacao_blocos,
    "binomio_coeficiente":  gerar_binomio_coeficiente,
    "pascal_linha":         gerar_pascal_linha,
    "prob_dados":           gerar_prob_dados,
    "prob_condicional":     gerar_prob_condicional,
    "prob_independentes":   gerar_prob_independentes,
    "binomial_moedas":      gerar_binomial_moedas,
    # ── progressões ──
    "pa_termo":          gerar_pa_termo,
    "pa_soma":           gerar_pa_soma,
    "pg_termo":          gerar_pg_termo,
    "pg_soma_infinita":  gerar_pg_soma_infinita,
    "pg_classificacao":  gerar_pg_classificacao,
}

TOPICOS = {
    "contagem":      ["pfc_senha", "arranjo_podio", "circular"],
    "anagramas":     ["anagrama_simples", "anagrama_repeticao", "anagrama_bloco"],
    "combinacoes":   ["combinacao_simples", "combinacao_dupla", "permutacao_blocos"],
    "binomio":       ["binomio_coeficiente", "pascal_linha"],
    "probabilidade": ["prob_dados", "prob_condicional",
                      "prob_independentes", "binomial_moedas"],
    "progressoes":   ["pa_termo", "pa_soma", "pg_termo",
                      "pg_soma_infinita", "pg_classificacao"],
}


# ──────────────────────────────────────────
#  CASAMENTO COM LIVRO INDEXADO
#
#  Sem isto, um livro de combinatória não acionava gerador nenhum — e a
#  rota /procedural/gerar-do-livro acabava casando com geradores de
#  outras áreas por coincidência de palavra.
# ──────────────────────────────────────────

PALAVRAS_CHAVE = {
    "pa_termo":         ["progressao aritmetica", "pa", "termo geral",
                         "sequencia numerica", "progressoes"],
    "pa_soma":          ["progressao aritmetica", "pa", "soma dos termos",
                         "progressoes"],
    "pg_termo":         ["progressao geometrica", "pg", "termo geral",
                         "progressoes", "crescimento exponencial"],
    "pg_soma_infinita": ["progressao geometrica", "pg", "soma infinita",
                         "serie geometrica", "convergencia"],
    "pg_classificacao": ["progressao geometrica", "pg", "progressoes",
                         "razao"],
    "pfc_senha":           ["principio fundamental da contagem", "pfc",
                            "principio multiplicativo", "analise combinatoria"],
    "arranjo_podio":       ["arranjo", "arranjos", "analise combinatoria",
                            "agrupamento ordenado"],
    "circular":            ["permutacao circular", "permutacoes circulares",
                            "analise combinatoria"],
    "anagrama_simples":    ["anagrama", "anagramas", "permutacao", "permutacoes",
                            "fatorial"],
    "anagrama_repeticao":  ["anagrama com repeticao", "permutacao com repeticao",
                            "elementos repetidos", "anagramas"],
    "anagrama_bloco":      ["anagrama", "anagramas", "permutacao com restricao",
                            "letras juntas"],
    "combinacao_simples":  ["combinacao", "combinacoes", "analise combinatoria",
                            "agrupamento nao ordenado"],
    "combinacao_dupla":    ["combinacao", "combinacoes", "comissao",
                            "analise combinatoria"],
    "permutacao_blocos":   ["permutacao de blocos", "permutacao", "anagramas"],
    "binomio_coeficiente": ["binomio de newton", "coeficiente binomial",
                            "numero binomial", "teorema binomial"],
    "pascal_linha":        ["triangulo de pascal", "triangulo aritmetico",
                            "binomio de newton", "linha de pascal"],
    "prob_dados":          ["probabilidade", "espaco amostral", "evento",
                            "espaco equiprovavel", "experimento aleatorio"],
    "prob_condicional":    ["probabilidade condicional", "teorema da multiplicacao",
                            "probabilidade total"],
    "prob_independentes":  ["eventos independentes", "independencia de eventos",
                            "probabilidade"],
    "binomial_moedas":     ["lei binomial", "distribuicao binomial",
                            "binomial da probabilidade", "ensaios de bernoulli"],
}

# Chaves que aparecem em outras áreas e, sozinhas, não bastam.
CHAVES_GENERICAS = {
    "contagem", "arranjo", "sequencia", "evento", "espaco", "grupo",
    "permutacao", "combinacao", "probabilidade", "fatorial",
}


def _normalizar(txt: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def templates_para_topicos(topicos: list) -> list:
    """
    Casa os tópicos de um livro indexado com os templates deste gerador.

    A comparação é por PALAVRA INTEIRA, não por substring: "ip" não pode
    casar dentro de "princípio". Chaves genéricas (que existem em várias
    áreas) só valem quando aparecem em par.
    """
    texto = " " + " ".join(_normalizar(str(t)) for t in topicos) + " "

    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        especificas = genericas = 0
        for chave in chaves:
            cn = _normalizar(chave)
            if not cn:
                continue
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


def gerar_lote(quantidade: int = 15, topico: str = None,
               templates: list = None, seed: int = None):
    """
    Gera questões alternando entre templates.
    `topico` filtra: contagem | anagramas | combinacoes | binomio | probabilidade
    """
    rng = random.Random(seed)

    # Lista explícita de templates tem prioridade (usada pelo pipeline do
    # livro indexado, que casa tópicos com PALAVRAS_CHAVE).
    if templates:
        nomes = [n for n in templates if n in TEMPLATES]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
        funcoes = [TEMPLATES[n] for n in nomes]
        rng.shuffle(funcoes)
        questoes = []
        for i in range(quantidade):
            q = funcoes[i % len(funcoes)](rng)
            q["numero"] = i + 1
            questoes.append(q)
        return questoes


    if topico:
        nomes = TOPICOS.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS)}")
        funcoes = [TEMPLATES[n] for n in nomes]
    else:
        funcoes = list(TEMPLATES.values())

    ordem = funcoes[:]
    rng.shuffle(ordem)

    questoes = []
    for i in range(quantidade):
        template = ordem[i % len(ordem)]
        q = template(rng)
        q["numero"] = i + 1
        questoes.append(q)
    return questoes


def gerar_para_api(quantidade: int = 10, topico: str = None,
                   templates: list = None, seed: int = None):
    """
    Formato compatível com salvar_questoes_banco da simulados_api:
    retorna (questoes_limpas, gabarito_final).

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


# ──────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────

if __name__ == "__main__":
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    topico = sys.argv[2] if len(sys.argv) > 2 else None

    for q in gerar_lote(qtd, topico):
        print("─" * 64)
        print(f"Q{q['numero']} [{q['topico']}]")
        print(f"\n{q['enunciado']}\n")
        for L, txt in q["alternativas"].items():
            print(f"   {L}) {txt}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   Explicação: {q['explicacao']}")
    print("─" * 64)
    print(f"\n{qtd} questões | Custo: R$ 0,00 | Gabaritos garantidos.\n")
