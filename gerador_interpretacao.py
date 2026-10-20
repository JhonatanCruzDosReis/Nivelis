"""
=============================================================
  NIVELIS — Gerador de Questões de Interpretação de Texto
=============================================================

  Monta questões sobre trechos de livros JÁ INDEXADOS, em
  Python puro — sem chamar IA no momento da geração.

  COMO ISSO É POSSÍVEL
  --------------------
  Interpretação exige leitura, e o Python não lê. A solução é
  deslocar a leitura para a INDEXAÇÃO: quando o Gemini analisa
  o PDF (uma única vez, em indexar_livro.py), ele já extrai os
  parágrafos aproveitáveis junto com a análise de cada um —
  tese, pressupostos, ideia secundária e afirmações falsas.

  Essa análise vira o gabarito. A partir daí este gerador só
  reorganiza material já verificado: escolhe o trecho, escolhe
  o tipo de pergunta, sorteia a redação, embaralha as
  alternativas. Custo de IA por questão gerada: zero.

  TIPOS DE PERGUNTA (todos com gabarito vindo da análise):
    1. Tese central do trecho
    2. Pressuposto do texto
    3. Ideia secundária / argumento de apoio
    4. Afirmação NÃO sustentada pelo texto
    5. Asserção-razão (formato clássico do ENADE)

  Funciona para QUALQUER disciplina — o que define o conteúdo
  é o livro indexado, não o gerador. Português, Direito,
  Medicina, Filosofia: tudo que tiver trecho analisado no
  banco pode virar questão aqui.

  USO (como biblioteca):
    from gerador_interpretacao import gerar_para_api
    questoes, gabarito = gerar_para_api(trechos, quantidade=10)
=============================================================
"""

import sys
import random

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "fracao", "simbolica", "codigo_numerico",
    "sequencia", "textual", "endereco_ip", "percentual", "monetaria",
}


# ──────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────

def _juntar(anterior: str, seguinte: str) -> str:
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _frase(txt: str) -> str:
    """Normaliza uma alternativa: inicial maiúscula, ponto final."""
    t = " ".join(str(txt).split()).strip()
    if not t:
        return t
    t = t[0].upper() + t[1:]
    if not t.endswith((".", "!", "?")):
        t += "."
    return t


def _equilibrar_tamanhos(correta: str, distratores: list, rng,
                         tolerancia: float = 2.4):
    """
    Rejeita conjuntos em que a alternativa correta se destaca pelo tamanho.

    A tese vem da análise do modelo e costuma ser longa e explicativa; os
    distratores são frases curtas de negação. O contraste vira uma pista
    visual: o aluno marca a maior e acerta sem ler o texto.

    Esta função devolve apenas os distratores cujo comprimento é compatível
    com o da resposta certa. Se sobrarem menos de 4, o template descarta o
    sorteio e tenta outro — melhor perder uma tentativa do que gerar uma
    questão que se resolve por eliminação visual.
    """
    n_correta = len(str(correta))
    compativeis, resto = [], []
    for d in distratores:
        n = len(str(d))
        if n == 0:
            continue
        razao = max(n_correta, n) / min(n_correta, n)
        (compativeis if razao <= tolerancia else resto).append((razao, d))

    compativeis.sort(key=lambda x: x[0])
    resto.sort(key=lambda x: x[0])

    # Se o filtro deixou menos de 4, completa com os mais próximos que
    # sobraram — mas ENCURTANDO-OS antes. Aceitar um distrator de 246
    # caracteres ao lado de quatro de 70 apenas troca o problema de lado:
    # em vez do gabarito se destacar, é a alternativa errada que grita, e
    # o aluno a elimina por instinto.
    escolhidos = [d for _, d in compativeis]
    if len(escolhidos) < 4:
        limite = int(n_correta * tolerancia)
        for _, d in resto:
            if len(escolhidos) >= 4:
                break
            texto = str(d)
            if len(texto) > limite:
                texto = _encurtar_tese(texto, limite)
                if len(texto) > limite * 1.15:
                    continue
            escolhidos.append(texto)

    # ── Segunda passada: nivelar contra o CONJUNTO ──
    #
    # Comparar cada distrator só com a resposta certa não basta. Com
    # correta de 71 caracteres e tolerância de 2.4, um distrator de 176
    # passava — mas as outras três tinham ~75, e ele destoava de todas.
    # O aluno elimina a alternativa que grita, e a questão perde uma
    # opção efetiva.
    #
    # Aqui cada item é comparado com a média dos DEMAIS (incluindo a
    # correta) e encurtado quando foge do conjunto.
    for _ in range(2):                      # duas passadas bastam
        todos = [str(correta)] + [str(x) for x in escolhidos]
        tamanhos = [len(x) for x in todos]
        if len(tamanhos) < 3:
            break
        mudou = False
        for i in range(1, len(todos)):      # não mexe na correta
            demais = [n for j, n in enumerate(tamanhos) if j != i]
            media = sum(demais) / len(demais)
            if media > 0 and tamanhos[i] / media > 1.9:
                novo_txt = _encurtar_tese(todos[i], int(media * 1.5))
                if novo_txt != todos[i] and not _e_fragmento(novo_txt):
                    escolhidos[i - 1] = novo_txt
                    mudou = True
        if not mudou:
            break

    return escolhidos


def _tem_predicado(fragmento: str) -> bool:
    """
    O fragmento contém um verbo em forma finita?

    Duas abordagens falharam antes:

      • lista de verbos — faltou "possui", depois "orienta";
      • desinência -a/-e — "juntamente" e "conforme" casam tanto quanto
        "orienta" e "define". O português não distingue verbo de
        substantivo pela terminação, e regex não faz análise morfológica.

    O que resta é uma lista NEGATIVA: palavras que ocupam a posição de
    verbo mas não são. É finita e pequena — advérbios em -mente e
    preposições complexas —, ao contrário da lista de verbos, que é
    aberta. Tudo que não estiver nela e tiver desinência verbal conta
    como predicado.
    """
    import re as _re

    # Palavras que aparecem logo após vírgula sem serem verbo
    NAO_SAO_VERBO = _re.compile(
        r'^(?:'
        r'\w+mente|'                                  # juntamente, conforme
        r'conforme|segundo|consoante|mediante|'        # preposições complexas
        r'como|quando|onde|enquanto|porque|pois|'      # conjunções
        r'exceto|salvo|inclusive|sobretudo|'
        r'ou\s+seja|isto\s+é|por\s+exemplo|a\s+saber'
        r')\b', _re.IGNORECASE)

    t = str(fragmento).lstrip(" ,;:")
    if NAO_SAO_VERBO.match(t):
        return False

    # Preposição ou determinante abrindo = sintagma, não predicado
    if _re.match(r'^(?:de|do|da|dos|das|em|no|na|nos|nas|por|para|com|'
                 r'sem|sob|sobre|entre|ao|à|aos|às|o|a|os|as|um|uma)\b',
                 t, _re.IGNORECASE):
        return False

    # Sobrou algo com cara de verbo na abertura
    return bool(_re.match(r'^\w{3,}\b', t))


def _e_fragmento(frase: str) -> bool:
    """
    A frase é um fragmento — sintagma com adjunto, sem predicado?

    Reconhece dois casos:
      • oração reduzida aberta e não fechada
          "O acesso equitativo, fundamentado no princípio de justiça"
      • adjunto adverbial sem oração principal
          "Para um acolhimento eficaz da demanda espontânea"

    Duplica a lógica de indexar_livro._checar_redacao de propósito: o
    encurtamento acontece DEPOIS da validação da indexação, e pode
    transformar uma tese correta em fragmento. Sem verificar o próprio
    resultado, o corte reintroduz o defeito que a indexação barrou.
    """
    import re as _re
    t = " ".join(str(frase or "").split()).rstrip(".!?")
    if not t:
        return True

    # ── Oração reduzida não fechada ──
    INTRO = (r'(?:ao|à|aos|às|de|em|por|para|sem|com|após|antes de|'
             r'apesar de|além de|em vez de|ao invés de|a fim de|'
             r'depois de|desde)?')
    m = _re.search(r',\s*' + INTRO + r'\s*'
                   r'\w+(?:ando|endo|indo|arem|erem|irem|ar|er|ir|'
                   r'ad[oa]s?|id[oa]s?)\b', t, _re.IGNORECASE)
    if m:
        depois = t[m.end():]

        # A oração reduzida pode ser fechada por vírgula OU simplesmente
        # seguida do predicado sem pontuação: "O acesso, fundamentado no
        # princípio de justiça DEVE ORIENTAR a organização" é frase
        # completa, embora não tenha a segunda vírgula.
        #
        # Procuramos um verbo finito em qualquer ponto depois da reduzida.
        VERBO_APOS = _re.compile(
            r'\b(?:é|são|era|eram|foi|foram|será|serão|está|estão|'
            r'tem|têm|há|deve|devem|pode|podem|precisa|precisam|'
            r'exige|exigem|requer|requerem|constitui|constituem|'
            r'demanda|demandam|permite|permitem|garante|garantem|'
            r'representa|representam|significa|significam|'
            r'orienta|orientam|envolve|envolvem|depende|dependem|'
            r'implica|implicam|resulta|resultam|contribui|contribuem|'
            r'favorece|favorecem|reduz|reduzem|amplia|ampliam|'
            r'\w{3,}(?:am|em|ou|iu|ram|vam|rá|rão|ria|sse|imos|emos|amos))\b',
            _re.IGNORECASE)

        fecha = depois.find(",")
        resto = depois[fecha + 1:].strip() if fecha >= 0 else ""

        tem_predicado = (len(resto.split()) >= 2) or bool(VERBO_APOS.search(depois))
        if not tem_predicado:
            return True

    # ── Adjunto adverbial sem principal ──
    CONTRAI = r'(?:d[aeo]s?|n[aeo]s?|à|às|ao|aos|em|a)'
    if _re.match(rf'^\s*(?:para|a fim de|'
                 rf'com o (?:objetivo|intuito|propósito|fim) de|'
                 rf'em razão {CONTRAI}|devido {CONTRAI}|diante {CONTRAI}|'
                 rf'com base {CONTRAI}|a partir {CONTRAI}|'
                 rf'por meio {CONTRAI}|através {CONTRAI}|'
                 rf'ao longo {CONTRAI}|apesar {CONTRAI})\b',
                 t, _re.IGNORECASE):
        pv = t.find(",")
        resto = t[pv + 1:].strip() if pv >= 0 else ""
        if len(resto.split()) < 3:
            return True

    return False


def _encurtar_tese(texto: str, limite: int = 110) -> str:
    """
    Reduz uma tese longa ao seu núcleo, cortando em fronteira de oração.

    NUNCA devolve frase truncada: se o corte deixaria a oração incompleta
    (terminando em verbo de ligação, preposição ou conectivo), o texto é
    devolvido inteiro. Uma alternativa longa demais é um problema menor
    que uma alternativa sem sentido — "o número de pares ordenados é."
    não é resposta, é fragmento.
    """
    t = " ".join(str(texto).split())
    if len(t) <= limite:
        return t

    # Palavras que não podem terminar a alternativa
    TERMINACOES_RUINS = {
        # verbos de ligação e auxiliares
        "é", "são", "era", "eram", "foi", "seja", "sendo", "tem", "têm",
        "está", "estão", "pode", "podem", "deve", "devem", "há",
        # preposições e contrações
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "por", "para", "com", "sem", "sob", "sobre", "entre", "ao", "à",
        "aos", "às", "pela", "pelo", "pelas", "pelos", "num", "numa",
        # artigos e conectivos
        "que", "e", "ou", "mas", "a", "o", "as", "os", "um", "uma",
        "uns", "umas", "como", "quando", "onde", "se", "nem", "porque",
        # POSSESSIVOS E DEMONSTRATIVOS — pedem substantivo depois.
        # Foi aqui que escapou "definidores de suas." (faltava
        # "necessidades"): o corte caiu logo após o possessivo.
        "seu", "sua", "seus", "suas", "meu", "minha", "nosso", "nossa",
        "este", "esta", "esse", "essa", "aquele", "aquela", "isso",
        "seus", "cujo", "cuja", "cujos", "cujas",
        # quantificadores
        "todo", "toda", "todos", "todas", "cada", "qualquer", "algum",
        "alguma", "outro", "outra", "outros", "outras", "muito", "muita",
    }

    # Separadores em ordem de preferência: cortar numa fronteira de oração
    # preserva melhor o sentido que cortar entre palavras quaisquer.
    SEPARADORES = (
        ", sendo", ", onde", ", que", ", pois", ", já que", ", uma vez que",
        ", inclusive", ", também", ", além de", ", e ", ", ou ", "; ",
        " e reconhecer", " e garantir", " para ", " com ", ", ",
    )
    candidatos = []
    for sep in SEPARADORES:
        i = t.rfind(sep, 0, limite)
        if i > limite * 0.4:
            candidatos.append(t[:i])

    # Sem separador: varre para trás palavra a palavra até achar corte válido.
    # A versão anterior tentava só a última palavra antes do limite; se ela
    # fosse preposição ou possessivo, desistia e devolvia a frase inteira —
    # que então era descartada por tamanho, zerando os distratores.
    palavras = t.split()
    for corte in range(len(palavras) - 1, 2, -1):
        parcial = " ".join(palavras[:corte])
        if len(parcial) <= limite:
            candidatos.append(parcial)
            if len(candidatos) > 12:
                break

    import re as _re_term

    for cand in candidatos:
        limpo = cand.rstrip(" ,;:")
        palavras = limpo.split()
        if not palavras:
            continue
        ultima = palavras[-1].lower().strip(".,;:")

        if ultima in TERMINACOES_RUINS:
            continue
        # Gerúndio e infinitivo pedem complemento: "...equipes utilizando"
        # e "...processo para implementar" ficam pendurados.
        if _re_term.fullmatch(r'\w+(?:ando|endo|indo|ar|er|ir)', ultima):
            continue
        # O corte não pode transformar a tese em fragmento: cortar
        # "O acesso equitativo, fundamentado no princípio, exige X" na
        # segunda vírgula deixa sujeito com adjunto e nenhum predicado.
        if _e_fragmento(limpo):
            continue

        # Nem pode deixar um aposto ou intercalação pela metade.
        #
        # "...é crucial porque ele, juntamente" veio de "...porque ele,
        # juntamente COM OS PROFISSIONAIS, define suas necessidades": o
        # corte caiu dentro da intercalação.
        #
        # A regra é geral e não depende de listar advérbios: se a última
        # vírgula abre um elemento com menos de três palavras, esse
        # elemento ficou truncado.
        # Se o texto tem número ÍMPAR de vírgulas e a última abre um
        # elemento curto, a intercalação ficou aberta. "porque ele,
        # juntamente com os profissionais" tem a vírgula de abertura mas
        # não a de fechamento — o predicado ficou de fora.
        virgulas = limpo.count(",")
        ult_virgula = limpo.rfind(",")
        if ult_virgula >= 0:
            cauda = limpo[ult_virgula + 1:].split()
            # Elemento curto demais: truncado no meio
            if len(cauda) < 3:
                continue
            # Intercalação aberta e não fechada: a última vírgula é de
            # abertura (número ímpar) e o que vem depois não é predicado
            if virgulas % 2 == 1 and not _tem_predicado(limpo[ult_virgula:]):
                continue

        return limpo

    # Nenhum corte seguro: melhor a frase longa do que o fragmento
    return t


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            tipo_resposta="textual", equilibrar=True):
    assert tipo_resposta in TIPOS_RESPOSTA
    # Encurta teses muito longas antes de comparar: o objetivo é que a
    # resposta certa tenha porte semelhante ao dos distratores.
    correta_f = _frase(_encurtar_tese(correta))

    # Mantém só os distratores de comprimento compatível.
    #
    # Não se aplica à asserção-razão: ali as cinco opções são FIXAS pelo
    # formato ENADE, e uma delas ("As asserções I e II são proposições
    # falsas") é naturalmente mais curta. Filtrar por tamanho eliminava
    # essa opção e, com ela, o modo em que ambas são verdadeiras — que
    # deixava de aparecer como gabarito.
    if equilibrar:
        distratores = _equilibrar_tamanhos(correta_f, distratores, rng)

    unicos = []
    for d in distratores:
        df = _frase(d)
        if not df or df == correta_f or df in unicos:
            continue
        # Paráfrase da correta ou de outro distrator: a questão perde uma
        # opção efetiva quando duas alternativas dizem o mesmo.
        if _quase_iguais(df, correta_f) or any(_quase_iguais(df, u) for u in unicos):
            continue
        # Descarta o distrator que é a negação exata do gabarito ou de outro
        # distrator já aceito: o par entrega a resposta por eliminação lógica.
        if _sao_contraditorias(df, correta_f):
            continue
        if any(_sao_contraditorias(df, u) for u in unicos):
            continue
        unicos.append(df)
    if len(unicos) < 4:
        return None

    valores = [correta_f] + unicos[:4]
    rng.shuffle(valores)
    return {
        "enunciado":      enunciado,
        "alternativas":   {L: v for L, v in zip(LETRAS, valores)},
        "gabarito":       LETRAS[valores.index(correta_f)],
        "explicacao":     explicacao,
        "topico":         topico,
        "origem":         "gerador_interpretacao",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta_f,
    }


def _quase_iguais(a: str, b: str, limiar: float = 0.75) -> bool:
    """
    Duas alternativas afirmam a mesma coisa com outras palavras?

    O filtro de duplicata compara strings, e por isso deixava passar
    pares como:

        "A participação não é ESSENCIAL para o sucesso e sustentabilidade"
        "A participação não é FUNDAMENTAL para a sustentabilidade"

    São a mesma proposição — a questão perde uma opção efetiva, porque o
    aluno percebe que ambas dizem o mesmo e elimina as duas ou nenhuma.

    Compara o vocabulário de conteúdo depois de normalizar sinônimos
    frequentes em texto acadêmico. Não pretende cobrir a sinonímia do
    português: cobre os pares que aparecem nesta aplicação.
    """
    import re as _re
    import unicodedata as _ud

    SINONIMOS = {
        "essencial": "fundamental", "crucial": "fundamental",
        "imprescindivel": "fundamental", "indispensavel": "fundamental",
        "primordial": "fundamental", "basilar": "fundamental",
        "central": "fundamental", "chave": "fundamental",
        "importante": "relevante", "significativo": "relevante",
        "necessario": "preciso", "requerido": "preciso",
        "adequado": "apropriado", "conveniente": "apropriado",
        "possibilita": "permite", "viabiliza": "permite",
        "propicia": "permite", "faculta": "permite",
        "assegura": "garante", "assegurar": "garantir",
        "demanda": "exige", "requer": "exige", "reclama": "exige",
        "sucesso": "efetividade", "eficacia": "efetividade",
        "sustentabilidade": "continuidade", "manutencao": "continuidade",
        "iniciativa": "proposta", "acao": "proposta",
        "trabalhador": "profissional", "servidor": "profissional",
        "usuario": "paciente", "pessoa": "paciente",
    }

    def _conteudo(t):
        t = _ud.normalize("NFKD", str(t or "").lower())
        t = "".join(ch for ch in t if not _ud.combining(ch))
        palavras = _re.findall(r'[a-z]{4,}', t)
        VAZIAS = {"para", "como", "mais", "menos", "pelo", "pela", "esse",
                  "essa", "este", "esta", "aquele", "aquela", "seus",
                  "suas", "todo", "toda", "cada", "entre", "sobre",
                  "quando", "onde", "porque", "assim", "tambem", "ainda",
                  "apenas", "sendo", "pode", "deve", "sera"}
        base = set()
        for p in palavras:
            if p in VAZIAS:
                continue
            base.add(SINONIMOS.get(p, p)[:6])
        return base

    # As cinco opções fixas do formato asserção-razão compartilham quase
    # todo o vocabulário por construção ("As asserções I e II são
    # proposições..."), mas descrevem combinações lógicas distintas. O
    # mesmo cuidado já foi necessário em _sao_contraditorias — sem ele, o
    # tipo inteiro parava de gerar.
    if (_re.match(r'^\s*(?:a|as)\s+asser[çc][õoã][eo]?s?\b', str(a), _re.I)
            and _re.match(r'^\s*(?:a|as)\s+asser[çc][õoã][eo]?s?\b', str(b), _re.I)):
        return False

    ca, cb = _conteudo(a), _conteudo(b)
    if not ca or not cb:
        return False

    # Polaridade precisa coincidir: "é fundamental" e "não é fundamental"
    # são opostos, não paráfrases.
    neg_a = bool(_re.search(r'\b(?:não|nunca|jamais|nem)\b', str(a).lower()))
    neg_b = bool(_re.search(r'\b(?:não|nunca|jamais|nem)\b', str(b).lower()))
    if neg_a != neg_b:
        return False

    return len(ca & cb) / min(len(ca), len(cb)) >= limiar


def _sao_contraditorias(a: str, b: str) -> bool:
    """
    Detecta se duas alternativas são negação direta uma da outra.

    Ex.: "A contagem é possível" vs "A contagem é impossível".
    Quando isso acontece, o aluno resolve por lógica pura — uma delas TEM
    que ser a certa — sem precisar ler o texto. A questão deixa de medir
    interpretação.

    Compara as frases ignorando marcas de negação: se o resto coincide,
    são o mesmo enunciado com polaridade trocada.
    """
    import re as _re

    def _nucleo(t: str) -> str:
        t = " ".join(str(t).lower().split()).rstrip(".")
        # remove negações e prefixos privativos
        t = _re.sub(r'\b(?:não|nao|nunca|jamais|nem)\b', "", t)
        # Prefixos privativos: "impossível" -> "possível", "irrelevante" ->
        # "relevante". Sem o \b inicial, porque a palavra negada é uma só.
        t = _re.sub(r'\b(?:im|in|ir|i|des|a)(possível|possivel|correto|correta|'
                    r'viável|viavel|válido|valido|relevante|suficiente|'
                    r'necessário|necessario|dependente|comum|regular|'
                    r'adequado|adequada|coerente|preciso|precisa)\b',
                    r'\1', t)
        return " ".join(t.split())

    na, nb = _nucleo(a), _nucleo(b)
    if not na or not nb or na == " " or nb == " ":
        return False

    # Caso 1 — mesma frase com marca de negação trocada
    if na == nb and " ".join(str(a).lower().split()) != " ".join(str(b).lower().split()):
        return True

    # As cinco opções fixas do formato asserção-razão são mutuamente
    # exclusivas POR DEFINIÇÃO — é assim que o formato funciona. Aplicar
    # o teste de contradição a elas zerava a geração do tipo inteiro.
    # Casa qualquer uma das cinco opções fixas: "As asserções I e II..."
    # e "A asserção I é uma proposição...". O padrão anterior exigia que
    # "asserção" viesse logo após o artigo, e as três opções no singular
    # ("A asserção I é...") escapavam — o que zerava o tipo inteiro.
    MOLDE_ASSERCAO = _re.compile(r'^\s*(?:a|as)\s+asser[çc][õoã][eo]?s?\b',
                                 _re.IGNORECASE)
    if MOLDE_ASSERCAO.match(str(a)) and MOLDE_ASSERCAO.match(str(b)):
        return False

    # Caso 1b — MESMO ASSUNTO, uma negada e outra não.
    #
    # A comparação por igualdade de núcleo falha quando o modelo usa
    # verbos diferentes para a mesma ideia: "não TÊM papel na
    # identificação de risco" contra "DESEMPENHAM papel importante na
    # identificação de risco". As frases não coincidem palavra a palavra,
    # mas afirmam o oposto sobre o mesmo sujeito.
    #
    # O critério é: polaridade diferente + vocabulário de conteúdo
    # majoritariamente compartilhado.
    neg_a = bool(_re.search(r'\b(?:não|nunca|jamais|nem)\b', str(a).lower()))
    neg_b = bool(_re.search(r'\b(?:não|nunca|jamais|nem)\b', str(b).lower()))
    if neg_a != neg_b:
        pa_c = {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(a).lower())}
        pb_c = {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(b).lower())}
        if pa_c and pb_c:
            cobertura = len(pa_c & pb_c) / min(len(pa_c), len(pb_c))

            # 0.85 em vez de 0.6: com o limiar baixo, duas afirmações
            # FALSAS sobre o mesmo tema eram tratadas como contraditórias
            # entre si — "a organização é responsabilidade exclusiva dos
            # profissionais" e "apenas profissionais podem identificar
            # riscos" falam do mesmo assunto sem se contradizer. Isso
            # derrubava distratores legítimos e travava a geração.
            #
            # A contradição real exige quase o mesmo vocabulário: é a
            # MESMA proposição com polaridade trocada, não duas ideias
            # vizinhas.
            if cobertura >= 0.85:
                return True

    # Caso 2 — mesmo sujeito com ANTÔNIMOS LEXICAIS.
    # "A inclusão é desnecessária" vs "A inclusão é benéfica" não tem
    # marca de negação, mas afirma o oposto. Sem isso, o par escapava e
    # virava asserção-razão sem relação causal possível.
    ANTONIMOS = [
        {"necessário", "necessária", "essencial", "fundamental", "indispensável",
         "importante", "benéfico", "benéfica", "útil", "relevante", "crucial"},
        {"desnecessário", "desnecessária", "dispensável", "irrelevante",
         "inútil", "prejudicial", "nocivo", "nociva", "supérfluo", "supérflua"},
    ]
    pa = set(_re.findall(r'[a-zà-ÿ]{4,}', str(a).lower()))
    pb = set(_re.findall(r'[a-zà-ÿ]{4,}', str(b).lower()))

    lados_a = [i for i, g in enumerate(ANTONIMOS) if pa & g]
    lados_b = [i for i, g in enumerate(ANTONIMOS) if pb & g]
    if lados_a and lados_b and set(lados_a).isdisjoint(lados_b):
        # Polaridades opostas. Só é contradição se falarem do MESMO sujeito.
        comuns = {p[:6] for p in pa} & {p[:6] for p in pb}
        # Desconta as próprias palavras de polaridade
        polares = {p[:6] for g in ANTONIMOS for p in g}
        if len(comuns - polares) >= 2:
            return True

    return False


def _mesmo_assunto(a: str, b: str, minimo: float = 0.15) -> bool:
    """
    Duas frases tratam do mesmo tema?

    Compara radicais de palavras de conteúdo. Serve para impedir que um
    distrator vindo de outro trecho entre numa questão — se ele fala de
    assunto diferente, o aluno o elimina sem ler o texto, e a questão
    deixa de medir interpretação.
    """
    import re as _re
    def _rad(t):
        return {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(t).lower())}
    ra, rb = _rad(a), _rad(b)
    if not ra or not rb:
        return False
    return len(ra & rb) / min(len(ra), len(rb)) >= minimo


def _distratores(rng, proprios: list, externos: list, minimo: int = 4,
                 extras_do_trecho: list = None) -> list:
    """
    Monta a lista de distratores dando PRIORIDADE aos do próprio trecho.

    Um distrator vindo de outro trecho fala de assunto diferente, e o aluno
    o elimina sem ler o texto-base — a questão vira reconhecimento de tema,
    não interpretação.

    A ordem de preferência é:
      1. afirmações falsas registradas para ESTE trecho
      2. negações das afirmações verdadeiras DESTE trecho (falsas por
         construção, sobre o mesmo assunto, verificáveis na leitura)
      3. teses de outros trechos, priorizando as de tema próximo

    O nível 2 foi acrescentado depois de uma conferência manual em que 4 de
    10 questões traziam alternativa de outro trecho: o parágrafo tinha 4
    falsas, uma virava gabarito, e as 3 restantes não fechavam as opções.
    """
    proprios = [str(x).strip() for x in proprios if str(x).strip()]
    externos = [str(x).strip() for x in externos if str(x).strip()]
    extras   = [str(x).strip() for x in (extras_do_trecho or []) if str(x).strip()]
    rng.shuffle(proprios)
    rng.shuffle(externos)

    # ── Nível 2: negar as verdadeiras do próprio trecho ──
    #
    # Com material mínimo — 2 falsas, 1 pressuposto, sem ideia secundária
    # — este nível é o que salva o lote. Antes ele parava no primeiro
    # `minimo` alcançado; agora esgota as fontes, porque os níveis
    # seguintes descartam por paráfrase e contradição, e sobrar margem
    # aqui evita voltar de mãos vazias.
    if len(proprios) < minimo + 2 and extras:
        for base in extras:
            if len(proprios) >= minimo + 2:
                break
            neg = _negar(base)
            if neg and neg not in proprios and not any(
                    _quase_iguais(neg, p) for p in proprios):
                proprios.append(neg)

    # ── Nível 3: externos, só se ainda faltar ──
    if len(proprios) >= minimo:
        return proprios

    if proprios and externos:
        referencia = " ".join(proprios)

        def _rad(t):
            import re as _re
            return {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(t).lower())}

        def _afinidade(e):
            ref, alv = _rad(referencia), _rad(e)
            return len(ref & alv) / max(1, len(alv))

        # Do tema primeiro; depois os demais, do mais próximo ao mais distante
        do_tema = [e for e in externos if _mesmo_assunto(e, referencia)]
        fora    = sorted((e for e in externos if e not in do_tema),
                         key=_afinidade, reverse=True)
        faltam  = minimo - len(proprios)
        externos = (do_tema + fora)[:max(0, faltam)]

    return proprios + externos

def _cabecalho(rng, trecho: dict) -> str:
    """Monta a introdução que apresenta o texto-base."""
    ABERTURAS = [
        "Leia o texto a seguir para responder à questão.",
        "Considere o trecho abaixo.",
        "Leia atentamente o excerto a seguir.",
        "O texto a seguir serve de base para a questão.",
        "Analise o trecho reproduzido abaixo.",
        "Com base no texto a seguir, responda à questão.",
    ]
    fonte = ""
    if trecho.get("livro_titulo"):
        autor = trecho.get("livro_autor") or ""
        fonte = f"\n\n({trecho['livro_titulo']}"
        if autor and autor.lower() != "desconhecido":
            fonte += f", {autor}"
        if trecho.get("pagina"):
            fonte += f", p. {trecho['pagina']}"
        fonte += ", adaptado)"
    return f"{rng.choice(ABERTURAS)}\n\n\u201c{trecho['texto']}\u201d{fonte}"


# ══════════════════════════════════════════
#  TIPOS DE QUESTÃO
# ══════════════════════════════════════════

def _negar(frase: str):
    """
    Produz a negação de uma afirmação, mantendo o assunto.

    Serve à asserção-razão e aos distratores: a afirmação negada precisa
    continuar FALANDO DO MESMO PONTO, só que sendo falsa.

    Retorna None sempre que a negação produziria frase defeituosa. Vale
    mais perder um distrator do que gerar alternativa sem sentido — foram
    três os casos que motivaram esta versão:

      "nem sempre é possível"  → "nem sempre NÃO é possível"  (dupla negação)
      "não é X, mas sim Y"     → "É X, mas sim Y"             (correlativa quebrada)
      "é paradoxal, apesar de" → "não é paradoxal, apesar de" (justificativa órfã)
    """
    import re as _re
    t = str(frase).strip().rstrip(".")
    if not t:
        return None

    baixo = t.lower()

    # ── Construções que não sobrevivem à inversão ──
    #
    # Correlativas ("não X, mas sim Y") e concessivas ("apesar de",
    # "embora") ligam duas partes cuja relação depende da polaridade.
    # Inverter só o verbo deixa a segunda parte órfã.
    ESTRUTURAS_FRAGEIS = (
        "mas sim", "e sim", "senão", "apesar de", "embora", "ainda que",
        "por outro lado", "ao contrário", "em vez de", "no entanto",
        "não apenas", "não só", "nem sempre", "nem sempre", "tanto quanto",
        "quanto mais", "não somente",
    )
    if any(e in baixo for e in ESTRUTURAS_FRAGEIS):
        return None

    # ── Já negativa: remover a negação ──
    #
    # Só quando há exatamente UMA marca de negação. Com duas ou mais, o
    # resultado é imprevisível.
    marcas = len(_re.findall(r'\b(?:não|nunca|jamais|nem)\b', baixo))
    if marcas > 1:
        return None
    if marcas == 1:
        # Frase com mais de uma oração: inverter só a primeira deixa o
        # resto contradizendo o começo. O caso real foi
        #   "Não existe uma única forma; diferentes modelagens devem ser
        #    experimentadas e adaptadas a cada contexto"
        # que virou "Existe uma única forma; diferentes modelagens devem
        # ser experimentadas" — a alternativa afirma X e defende não-X.
        if _re.search(r'[;:]|,\s*(?:mas|porém|contudo|embora|já que|pois|'
                      r'enquanto|ao passo que)\b', t, _re.I):
            return None
        # Também recusa quando a frase é longa demais para ter uma oração
        # só: o risco de haver desdobramento após a negação é alto.
        if len(t.split()) > 22:
            return None

        resultado = _re.sub(r'\bnão\s+', "", t, count=1, flags=_re.I)
        if resultado == t:
            return None
        # Capitaliza se a negação abria a frase
        return resultado[0].upper() + resultado[1:] if resultado else None

    # ── Afirmativa: inserir "não" antes do verbo principal ──
    # Palavras que já carregam sentido negativo: negá-las produz dupla
    # negação de leitura penosa — "não é independente", "não é
    # desnecessário". Pior ainda quando o comando da questão já é
    # negativo ("é INCORRETO afirmar que não é independente").
    JA_NEGATIVAS = _re.compile(
        r'\b\w*(?:independente|independência|desnecessári|dispensáve|'
        r'irrelevante|impossíve|improváve|inadequad|insuficiente|'
        r'incapaz|incorret|inexistente|ausência|ausente|isent|'
        r'exclu|impedi|proibi|nega|recusa|falta)\w*\b', _re.I)
    if JA_NEGATIVAS.search(t):
        return None

    # Quantificador restritivo + negação gera ambiguidade de escopo:
    # "Apenas profissionais de saúde não podem identificar riscos" pode
    # ser lido como "só eles não podem" ou "não é só eles que podem".
    if _re.match(r'^\s*(?:apenas|somente|só|exclusivamente|unicamente)\b',
                 t, _re.IGNORECASE):
        return None

    # Localiza o verbo da oração principal.
    #
    # Duas abordagens já falharam aqui:
    #
    #   1. Lista fechada de verbos — "possui" faltava, e a ausência
    #      silenciava a geração inteira de um tipo de questão.
    #   2. Desinência genérica — o padrão aceitava qualquer palavra
    #      terminada em "a" ou "e", e em português isso inclui quase
    #      todo substantivo e adjetivo feminino. O resultado foi
    #      "A estrutura NÃO FÍSICA e a ambiência influenciam" e
    #      "da demanda NÃO ESPONTÂNEA exige mudanças".
    #
    # A abordagem que resta: desinências INEQUÍVOCAS (que só existem em
    # verbo) mais uma lista ampla para as ambíguas de 3ª pessoa. Quando
    # nenhuma casa, desiste — perder um distrator é melhor que produzir
    # frase quebrada.

    # Terminações que só ocorrem em verbo
    DESINENCIA_SEGURA = (
        r'\w{2,}(?:am|em|ou|iu|eu|ram|vam|va|rão|rá|rão|riam|ria|'
        r'ssem|sse|imos|emos|amos|aram|eram|iram|uem|õem|ão)'
    )
    # Irregulares e 3ª pessoa ambígua (-a/-e), listadas por serem as
    # formas que efetivamente aparecem em texto expositivo
    VERBOS_3P = (
        r'(?:é|são|há|vê|vem|têm|tem|vai|vão|dá|dão|põe|põem|'
        r'possui|possuem|exige|exigem|requer|requerem|permite|permitem|'
        r'garante|garantem|envolve|envolvem|depende|dependem|'
        r'constitui|constituem|implica|implicam|representa|representam|'
        r'significa|significam|contribui|contribuem|favorece|favorecem|'
        r'define|definem|revela|revelam|indica|indicam|aponta|apontam|'
        r'demanda|demandam|reduz|reduzem|amplia|ampliam|facilita|'
        r'facilitam|dificulta|dificultam|impede|impedem|assume|assumem|'
        r'reconhece|reconhecem|identifica|identificam|realiza|realizam|'
        r'apoia|apoiam|inclui|incluem|abrange|abrangem|precede|precedem|'
        r'antecede|antecedem|sucede|sucedem|ocorre|ocorrem|acontece|'
        r'acontecem|resulta|resultam|deriva|derivam|decorre|decorrem|'
        r'produz|produzem|gera|geram|cria|criam|altera|alteram|'
        r'melhora|melhoram|piora|pioram|mantém|mantêm|sustenta|'
        r'sustentam|fundamenta|fundamentam|justifica|justificam|'
        r'compete|competem|cabe|cabem|serve|servem|funciona|funcionam|'
        r'opera|operam|atua|atuam|integra|integram|articula|articulam|'
        r'organiza|organizam|estrutura|estruturam|prevê|preveem|'
        r'considera|consideram|avalia|avaliam|analisa|analisam|'
        r'verifica|verificam|confirma|confirmam|comprova|comprovam)'
    )

    m = None
    for m_ in _re.finditer(rf'\b(?:{VERBOS_3P}|{DESINENCIA_SEGURA})\b', t,
                           _re.IGNORECASE):
        palavra = m_.group(0).lower()
        # Substantivos e adjetivos que terminam em desinência "segura"
        FALSOS_VERBOS = {
            "também", "porém", "além", "ninguém", "alguém", "quem",
            "bem", "nem", "tem", "cem", "vem", "item", "ordem", "origem",
            "imagem", "margem", "vantagem", "linguagem", "abordagem",
            "viagem", "passagem", "contagem", "triagem", "montagem",
            "homem", "nuvem", "jovem", "resumem", "volume", "regime",
            "sistema", "problema", "tema", "esquema", "programa",
            "não", "então", "ação", "razão", "questão", "gestão",
            "atenção", "situação", "relação", "condição", "posição",
            "função", "solução", "opção", "versão", "visão", "missão",
            "profissão", "sessão", "pressão", "expressão", "impressão",
            "grão", "irmão", "cidadão", "órgão", "padrão", "verão",
            "coração", "informação", "formação", "avaliação", "educação",
            "população", "organização", "participação", "implantação",
            "identificação", "priorização", "classificação",
        }
        if palavra in FALSOS_VERBOS:
            continue
        # Terminação -ção e -são são substantivos, não verbos
        if _re.search(r'(?:ção|são|ões|ãos)$', palavra) and palavra not in (
                "são",):
            continue
        # Precedido de determinante = é núcleo nominal, não verbo
        antes = t[:m_.start()].rstrip().split()
        if antes and antes[-1].lower() in (
                "o", "a", "os", "as", "um", "uma", "uns", "umas",
                "do", "da", "dos", "das", "no", "na", "nos", "nas",
                "ao", "à", "aos", "às", "de", "em", "por", "para",
                "com", "sem", "seu", "sua", "seus", "suas", "este",
                "esta", "esse", "essa", "aquele", "aquela", "cada",
                "todo", "toda", "todos", "todas", "outro", "outra"):
            continue
        m = m_
        break

    if not m:
        return None

    # O verbo precisa estar na oração PRINCIPAL, não numa subordinada
    # tardia: negar o verbo de uma oração final muda o sentido errado.
    if m.start() > len(t) * 0.7:
        return None

    # Ajusta a caixa: o verbo pode estar capitalizado por abrir a frase,
    # e inserir "não" antes deixa "Não É importante investigar".
    inicio, resto = t[:m.start()], t[m.start():]
    if not inicio.strip() and resto[:1].isupper():
        resto = resto[0].lower() + resto[1:]
    prefixo = "Não " if not inicio.strip() else "não "
    return f"{inicio}{prefixo}{resto}"

def _q_tese(rng, trecho, outros):
    """Tese central do trecho. Gabarito: campo 'tese' da análise."""
    PERGUNTAS = [
        "A ideia central defendida no texto é a de que:",
        "Assinale a alternativa que expressa a tese sustentada pelo autor.",
        "O texto defende principalmente que:",
        "Qual das alternativas sintetiza corretamente a tese do texto?",
        "A argumentação do autor se organiza em torno da ideia de que:",
    ]
    correta = trecho["tese"]
    # Só afirmações falsas DESTE trecho entram como distrator: são sobre o
    # mesmo assunto, mas incorretas.
    #
    # A ideia secundária e os pressupostos NÃO servem aqui: eles são
    # verdadeiros segundo o texto, e um comando do tipo "assinale a tese"
    # ficaria com duas alternativas defensáveis. Quando faltam distratores,
    # completa-se com teses de outros trechos.
    proprios = list(trecho.get("afirmacoes_falsas", []))
    distratores = _distratores(
        rng, proprios, [t["tese"] for t in outros],
        extras_do_trecho=[trecho.get("ideia_secundaria")] +
                         list(trecho.get("pressupostos") or []))

    enunciado = f"{_cabecalho(rng, trecho)}\n\n{rng.choice(PERGUNTAS)}"
    explicacao = (
        f"O texto se organiza em torno da defesa de que {trecho['tese'][0].lower()}"
        f"{trecho['tese'][1:].rstrip('.')}. As demais alternativas ou contrariam "
        f"o que foi afirmado ou tratam de ideias ausentes do trecho."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Interpretação de texto (tese)", rng)


def _q_pressuposto(rng, trecho, outros):
    """Pressuposto do texto. Gabarito: campo 'pressupostos'."""
    press = trecho.get("pressupostos") or []
    if not press:
        return None
    correta = rng.choice(press)

    PERGUNTAS = [
        "Assinale a alternativa que apresenta um pressuposto do texto.",
        "O texto assume como verdadeira, sem afirmá-la explicitamente, a ideia de que:",
        "Qual das alternativas expressa algo pressuposto pelo autor?",
        "Depreende-se do texto o pressuposto de que:",
    ]
    proprios = list(trecho.get("afirmacoes_falsas", []))
    # Outros pressupostos do mesmo trecho NÃO entram: seriam também corretos.
    externos = []
    for t in outros:
        externos.extend(t.get("pressupostos", [])[:1])
    distratores = _distratores(
        rng, proprios, externos,
        extras_do_trecho=[trecho.get("tese"), trecho.get("ideia_secundaria")] +
                         list(trecho.get("pressupostos") or []))

    enunciado = f"{_cabecalho(rng, trecho)}\n\n{rng.choice(PERGUNTAS)}"
    explicacao = (
        f"Um pressuposto é aquilo que o texto toma como dado sem enunciar "
        f"diretamente. A argumentação do autor só se sustenta se admitirmos que "
        f"{correta[0].lower()}{correta[1:].rstrip('.')}."
    )
    return _montar(enunciado, correta, distratores, explicacao,
                   "Interpretação de texto (pressupostos)", rng)


def _q_secundaria(rng, trecho, outros):
    """Argumento de apoio. Gabarito: campo 'ideia_secundaria'."""
    # A ideia secundária pode ter sido removida na indexação, quando era
    # cópia literal do parágrafo. Um pressuposto substitui bem: também é
    # conteúdo verdadeiro do trecho, e o comando "argumento de apoio"
    # continua fazendo sentido.
    ideia = (trecho.get("ideia_secundaria") or "").strip()
    if not ideia:
        press = [p for p in (trecho.get("pressupostos") or []) if str(p).strip()]
        ideia = str(press[0]).strip() if press else ""
    if not ideia:
        return None

    PERGUNTAS = [
        "Assinale a alternativa que apresenta um argumento de apoio presente no texto.",
        "Além da tese principal, o texto sustenta que:",
        "Qual das alternativas corresponde a uma ideia secundária do trecho?",
        "O autor recorre ao seguinte argumento de apoio:",
    ]
    # Novamente: só as afirmações falsas do próprio trecho. Tese e
    # pressupostos são verdadeiros e criariam ambiguidade.
    proprios = list(trecho.get("afirmacoes_falsas", []))
    externos = [t.get("ideia_secundaria") or
                (t.get("pressupostos") or [""])[0] for t in outros]
    externos = [e for e in externos if str(e).strip()]
    distratores = _distratores(
        rng, proprios, externos,
        extras_do_trecho=[trecho.get("tese"), trecho.get("ideia_secundaria")] +
                         list(trecho.get("pressupostos") or []))

    enunciado = f"{_cabecalho(rng, trecho)}\n\n{rng.choice(PERGUNTAS)}"
    explicacao = (
        f"Além da tese central, o trecho apresenta como apoio a ideia de que "
        f"{ideia[0].lower()}{ideia[1:].rstrip('.')}."
    )
    return _montar(enunciado, correta := ideia, distratores, explicacao,
                   "Interpretação de texto (argumentação)", rng)


def _q_nao_sustentada(rng, trecho, outros):
    """
    Afirmação que o texto NÃO sustenta. Gabarito: uma 'afirmacao_falsa';
    distratores: tese, pressupostos e ideia secundária (que SÃO sustentados).
    """
    falsas = trecho.get("afirmacoes_falsas") or []
    if not falsas:
        return None
    correta = rng.choice(falsas)

    verdadeiras = [trecho["tese"]]
    verdadeiras += list(trecho.get("pressupostos", []))
    if trecho.get("ideia_secundaria"):
        verdadeiras.append(trecho["ideia_secundaria"])

    # Se faltar material verdadeiro — o que acontece quando a indexação
    # remove a ideia secundária por ser cópia literal —, negar as OUTRAS
    # afirmações falsas produz enunciados verdadeiros sobre o mesmo
    # trecho. "A contagem é impossível" (falsa) vira "a contagem não é
    # impossível", que o texto sustenta.
    if len(verdadeiras) < 4:
        for f in falsas:
            if len(verdadeiras) >= 4:
                break
            if f == correta:
                continue
            neg = _negar(f)
            if neg and neg not in verdadeiras:
                verdadeiras.append(neg)

    if len(verdadeiras) < 4:
        return None

    PERGUNTAS = [
        "Assinale a alternativa que apresenta uma afirmação NÃO sustentada pelo texto.",
        "Todas as alternativas encontram apoio no texto, EXCETO:",
        "Qual das afirmações a seguir CONTRARIA o que foi exposto no trecho?",
        "Com base no texto, é INCORRETO afirmar que:",
    ]
    rng.shuffle(verdadeiras)
    enunciado = f"{_cabecalho(rng, trecho)}\n\n{rng.choice(PERGUNTAS)}"
    explicacao = (
        f"As demais alternativas retomam ideias efetivamente presentes no trecho. "
        f"A afirmação de que {correta[0].lower()}{correta[1:].rstrip('.')} não "
        f"encontra respaldo no que o autor escreveu."
    )
    return _montar(enunciado, correta, verdadeiras, explicacao,
                   "Interpretação de texto (compreensão)", rng)


def _q_assercao_razao(rng, trecho, outros):
    """
    Formato asserção-razão, característico do ENADE.

    A asserção II precisa ser uma CANDIDATA a justificar a I — mesmo quando
    é falsa, o aluno tem que poder avaliar a relação. Por isso II sai sempre
    dos PRESSUPOSTOS (que são, por natureza, o que fundamenta a tese) e a
    variação de gabarito vem de trocar a asserção I ou de usar um pressuposto
    negado, não de sortear qualquer afirmação solta.

    Sem esse cuidado, saía coisa como:
        I.  É possível obter os termos sem diagrama de árvore
        II. O coeficiente de x³ é determinado pela soma dos termos
    — duas frases sem relação, impossíveis de avaliar como razão.
    """
    press  = trecho.get("pressupostos") or []
    falsas = trecho.get("afirmacoes_falsas") or []
    if not press:
        return None

    OPCOES = [
        "As asserções I e II são proposições verdadeiras, e a II é uma "
        "justificativa correta da I.",
        "As asserções I e II são proposições verdadeiras, mas a II não é uma "
        "justificativa correta da I.",
        "A asserção I é uma proposição verdadeira, e a II é uma proposição falsa.",
        "A asserção I é uma proposição falsa, e a II é uma proposição verdadeira.",
        "As asserções I e II são proposições falsas.",
    ]

    # A II é SEMPRE um pressuposto (relação de fundamentação preservada).
    # O que varia é a asserção I e a veracidade da II.
    modo = rng.choice(["ambas_v", "I_falsa", "II_falsa"])

    if modo == "ambas_v":
        # I = tese, II = o pressuposto MAIS PRÓXIMO dela (maior sobreposição
        # de vocabulário), para que a relação de fundamentação seja visível.
        def _rad(txt):
            import re as _re
            return {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(txt).lower())}
        rt = _rad(trecho["tese"])
        a2 = max(press, key=lambda p: len(rt & _rad(p)))
        # Ao menos um radical em comum: garante que as asserções tratam do
        # mesmo tema. Exigir mais rejeitaria pressupostos legítimos que
        # reformulam a ideia com outras palavras — que é justamente o que
        # um bom pressuposto faz.
        if not (rt & _rad(a2)):
            return None
        a1 = trecho["tese"]
        # Ver comentário no modo I_falsa: par contraditório não é
        # asserção-razão.
        if _sao_contraditorias(a1, a2):
            return None
        correta = OPCOES[0]
        just = ("Ambas as asserções são sustentadas pelo texto, e a segunda "
                "explicita o pressuposto que dá base à primeira.")

    elif modo == "I_falsa":
        # I contraria o texto, II continua sendo um pressuposto verdadeiro.
        #
        # As duas precisam falar do MESMO ponto: uma afirmação falsa sobre o
        # tema A com um pressuposto sobre o tema B produz um par que ninguém
        # consegue avaliar como razão. Por isso escolhemos o par com maior
        # sobreposição de vocabulário — e desistimos se não houver nenhuma.
        if not falsas:
            return None

        def _radicais(txt):
            import re as _re
            return {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(txt).lower())}

        # Exige sobreposição REAL de vocabulário entre a asserção falsa e o
        # pressuposto. Sem um mínimo, o par vira duas frases sobre pontos
        # diferentes do texto — como "a irritação é infundada" (que o autor
        # nem discute) com "a irritação deve ser acolhida".
        melhor, melhor_score = None, 0
        for f in falsas:
            for p in press:
                score = len(_radicais(f) & _radicais(p))
                if score > melhor_score:
                    melhor, melhor_score = (f, p), score
        # Sem radical em comum: os enunciados não conversam
        if not melhor or melhor_score < 1:
            return None

        a1, a2 = melhor

        # As duas asserções não podem ser a mesma proposição com
        # polaridade trocada: "a inclusão é desnecessária" PORQUE "a
        # inclusão é benéfica" não estabelece relação causal nenhuma,
        # apenas se contradiz. O aluno resolve por lógica, sem ler.
        if _sao_contraditorias(a1, a2):
            return None

        correta = OPCOES[3]
        just = ("A primeira asserção contraria o texto, enquanto a segunda "
                "corresponde a uma ideia efetivamente pressuposta pelo autor.")

    else:  # II_falsa
        # II é a NEGAÇÃO de um pressuposto: mantém-se pertinente à I (fala do
        # mesmo ponto), mas é falsa — é isso que o aluno precisa perceber.
        def _rad2(txt):
            import re as _re
            return {p[:6] for p in _re.findall(r'[a-zà-ÿ]{5,}', str(txt).lower())}
        rt2 = _rad2(trecho["tese"])
        base = max(press, key=lambda p: len(rt2 & _rad2(p)))
        if not (rt2 & _rad2(base)):
            return None
        a2 = _negar(base)
        if a2 is None:
            return None
        a1 = trecho["tese"]
        correta = OPCOES[2]
        just = (f"A primeira asserção reproduz a tese do texto. A segunda, "
                f"porém, nega um pressuposto que o próprio texto assume, "
                f"sendo portanto falsa.")

    corpo = (
        f"{_cabecalho(rng, trecho)}\n\n"
        f"Avalie as asserções a seguir e a relação proposta entre elas.\n\n"
        f"I. {_frase(a1)}\n\n"
        f"PORQUE\n\n"
        f"II. {_frase(a2)}\n\n"
        f"A respeito dessas asserções, assinale a alternativa correta."
    )
    distratores = [o for o in OPCOES if o != correta]
    explicacao = f"{just} Por isso, a alternativa correta é a que indica essa relação."

    return _montar(corpo, correta, distratores, explicacao,
                   "Interpretação de texto (asserção-razão)", rng,
                   equilibrar=False)


TIPOS_QUESTAO = {
    "tese":            _q_tese,
    "pressuposto":     _q_pressuposto,
    "ideia_secundaria": _q_secundaria,
    "nao_sustentada":  _q_nao_sustentada,
    "assercao_razao":  _q_assercao_razao,
}


# ──────────────────────────────────────────
#  GERAÇÃO
# ──────────────────────────────────────────

MIN_TRECHOS_NECESSARIOS = 3   # para haver distratores vindos de outros trechos


def gerar_lote(trechos: list, quantidade: int = 10, tipos: list = None,
               seed: int = None) -> list:
    """
    Gera questões de interpretação a partir de trechos já analisados.

    `trechos` é a lista salva no documento do livro (campo 'trechos'),
    idealmente enriquecida com 'livro_titulo' e 'livro_autor'.

    Distribui as questões entre os trechos disponíveis em vez de sortear
    livremente: sem isso, um livro com poucos trechos gera várias questões
    sobre o MESMO parágrafo, e o aluno relê o texto repetidas vezes no
    mesmo simulado.
    """
    if not trechos:
        raise ValueError("Nenhum trecho fornecido.")
    if len(trechos) < MIN_TRECHOS_NECESSARIOS:
        raise ValueError(
            f"São necessários ao menos {MIN_TRECHOS_NECESSARIOS} trechos para "
            f"gerar distratores variados (recebidos: {len(trechos)})."
        )

    rng = random.Random(seed)
    nomes = [t for t in (tipos or TIPOS_QUESTAO) if t in TIPOS_QUESTAO]
    if not nomes:
        nomes = list(TIPOS_QUESTAO)

    # Teto de reuso: distribui as questões o mais uniformemente possível
    # entre os trechos. Com 5 trechos e 9 questões, nenhum aparece mais de
    # 2 vezes; com 12 trechos e 10 questões, cada um aparece no máximo 1.
    max_por_trecho = max(1, -(-quantidade // len(trechos)))   # teto da divisão
    usos = {id(t): 0 for t in trechos}

    # Evita repetir o mesmo par (trecho, tipo de pergunta)
    combinacoes_usadas = set()
    # Evita repetir o mesmo CONJUNTO de alternativas sobre um trecho
    conjuntos_usados = set()

    questoes = []
    tentativas = 0
    limite = quantidade * 40

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1

        # Prioriza os trechos menos usados
        candidatos = [t for t in trechos if usos[id(t)] < max_por_trecho]
        if not candidatos:
            # Todos atingiram o teto: libera mais uma rodada.
            #
            # O `continue` aqui consumia uma tentativa sem produzir nada.
            # Com poucos trechos isso é frequente — 3 trechos e 10
            # questões precisam de várias liberações —, e o limite de
            # tentativas se esgotava antes do lote fechar. Agora a
            # liberação não conta como tentativa.
            max_por_trecho += 1
            tentativas -= 1
            candidatos = list(trechos)

        menor_uso = min(usos[id(t)] for t in candidatos)
        candidatos = [t for t in candidatos if usos[id(t)] == menor_uso]
        trecho = rng.choice(candidatos)

        outros = [t for t in trechos if t is not trecho]
        rng.shuffle(outros)

        nome_tipo = nomes[len(questoes) % len(nomes)]

        # Nota sobre trechos pobres: quando a análise entrega só a tese,
        # 1 pressuposto e 2 afirmações falsas, o parágrafo tem 4 afirmações
        # distintas e uma questão precisa de 5 alternativas. Apenas os
        # tipos "tese" e "asserção-razão" conseguem se montar — os outros
        # três não têm material, e nenhum rodízio resolve isso (testei).
        #
        # O caminho é a INDEXAÇÃO entregar mais: o prompt pede de 2 a 4
        # afirmações falsas justamente por isso.

        chave = (id(trecho), nome_tipo)
        if chave in combinacoes_usadas and tentativas < limite - quantidade:
            continue

        q = TIPOS_QUESTAO[nome_tipo](rng, trecho, outros[:4])

        # Duas questões sobre o MESMO trecho não podem ter o MESMO conjunto
        # de alternativas: quem responde a primeira já viu todas as opções
        # da segunda, e a única variação é qual delas está certa.
        if q:
            # Duas questões sobre o MESMO trecho não devem ter o MESMO
            # conjunto de alternativas. Mas o veto é RELAXADO perto do fim
            # das tentativas: com poucos trechos, o espaço de combinações
            # se esgota, e recusar tudo devolveria um lote vazio — pior que
            # um conjunto repetido no fim da lista.
            # Duas questões sobre o mesmo trecho não devem compartilhar
            # quase todas as alternativas. O veto anterior pegava só o
            # conjunto IDÊNTICO, e sobreposição de 4 em 5 passava — quem
            # respondia a primeira já tinha visto tudo da segunda.
            alts_atual = frozenset(str(v) for v in q["alternativas"].values())

            # O limite de sobreposição afrouxa conforme as tentativas se
            # esgotam. Trechos com pouco material (poucas falsas, sem
            # ideia secundária) têm espaço de combinação pequeno, e um
            # veto rígido devolvia lote incompleto — o caso real foi 7
            # questões de 10 pedidas.
            # O limite afrouxa conforme as tentativas se esgotam E
            # conforme o material disponível. Com poucos trechos, exigir
            # variedade alta desde o início devolve lote incompleto: um
            # livro de 7 trechos rendeu 5 questões de 10 pedidas.
            #
            # A folga inicial é proporcional à razão entre o que se pede
            # e o que existe: pedir 10 questões de 7 trechos dá pouco mais
            # de uma por trecho, e aí a variedade vem naturalmente; pedir
            # 10 de 3 trechos força três por trecho, e o veto precisa
            # ceder para o lote fechar.
            # A folga combina duas medidas: a pressão média do lote e o
            # quanto ESTE trecho já rendeu. A média sozinha liberava cedo
            # demais — o balanceamento distribui melhor que a média
            # sugere, e havia espaço para exigir mais variedade nas
            # primeiras questões de cada parágrafo.
            por_trecho = quantidade / max(1, len(trechos))
            ja_usado = usos.get(id(trecho), 0)

            if ja_usado < 2 and por_trecho <= 2.5:
                base = 2          # ainda há material: exige variedade
            elif por_trecho <= 1.5:
                base = 2
            elif por_trecho <= 2.5:
                base = 3
            else:
                # Poucos trechos para muitas questões: o material de cada
                # parágrafo é finito, e insistir em variedade devolve lote
                # incompleto. Um livro de 3 trechos rendia 2 questões de
                # 10 pedidas — pior para o aluno que alguma repetição.
                base = 4

            fracao = tentativas / max(1, limite)
            if fracao < 0.5:
                max_comuns = base
            elif fracao < 0.8:
                max_comuns = base + 1
            else:
                max_comuns = 5          # fim: aceita o que vier

            # Conjunto EXATAMENTE igual nunca passa — repetir as cinco
            # opções mudando só qual é a certa não gera questão nova.
            # Acima disso, o limite é o max_comuns calculado acima.
            sobrepoe = False
            for tid, alts_ant in conjuntos_usados:
                if tid != id(trecho):
                    continue
                comuns = len(alts_atual & alts_ant)
                if comuns == len(alts_atual) or comuns > max_comuns:
                    sobrepoe = True
                    break
            if sobrepoe:
                continue

            conjuntos_usados.add((id(trecho), alts_atual))
            combinacoes_usadas.add(chave)
            usos[id(trecho)] += 1
            q["numero"] = len(questoes) + 1
            q["trecho_id"] = trecho.get("trecho_id")
            questoes.append(q)

    return questoes


def gerar_para_api(trechos: list, quantidade: int = 10, tipos: list = None,
                   seed: int = None):
    """
    Formato compatível com salvar_questoes_banco.
    Metadados internos (tipo_resposta, resposta_bruta, trecho_id) NÃO são
    incluídos — servem apenas aos testes automatizados.
    """
    lote = gerar_lote(trechos, quantidade, tipos, seed)
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
    print(__doc__)
    print("Este módulo precisa de trechos vindos do banco. "
          "Use a rota /procedural/interpretacao da API.")
