"""
=============================================================
  TESTE 11 — REDAÇÃO E COERÊNCIA DE TIPO
=============================================================
  Verifica dois defeitos que os testes anteriores não pegavam,
  e que apareceram em produção:

  1. CONCORDÂNCIA E CONTRAÇÃO
     Campos das tabelas entram em frases que assumem gênero
     fixo. "Considere a {via}" funciona para "a
     gliconeogênese" mas produz "a ciclo da ureia".
     E "corresponde a {descricao}" produz "a o dobramento"
     quando a descrição já traz artigo.

  2. COERÊNCIA DE TIPO ENTRE AS ALTERNATIVAS
     Quando um campo é acrescentado a uma tabela, os acessos
     por índice ficam deslocados, e o distrator passa a vir do
     campo errado. O sintoma: "onde ocorre a glicólise?" com
     alternativa "o ciclo de Krebs" — nome de etapa onde se
     esperava um local.

     O teste detecta isso comparando as alternativas entre si:
     se uma pertence a um conjunto semântico diferente das
     demais, algo está deslocado.

  USO:
      python teste_11_redacao.py [repeticoes]
=============================================================
"""

import sys
import re
import importlib

sys.path.insert(0, ".")

# Padrões de concordância e contração quebradas
CONTRACOES_RUINS = [
    # "de a" e "de o" NÃO se contraem antes de oração infinitiva:
    # "a chance de A PRÓXIMA CRIANÇA SER afetada" e "a possibilidade de
    # O GENE ESTAR no X" estão corretos — o artigo pertence ao sujeito
    # do infinitivo, não ao sintagma regido pela preposição.
    #
    # Só acusa quando NÃO há infinitivo logo adiante.
    # A exceção vale para INFINITIVOS de verdade. Terminação em -ar
    # também ocorre em adjetivos ("celular", "molecular", "nuclear"),
    # e aceitar qualquer palavra assim deixava passar erro real.
    (r'\bde a (?![^.]{0,40}\b(?:ser|estar|ter|haver|poder|dever|ir|vir|'
     r'fazer|receber|nascer|manifestar-se|apresentar|desenvolver|'
     r'transmitir|herdar|surgir|ocorrer|manifestar|lançar|obter|tirar|sortear|escolher|acertar|falhar|repetir|sair|conter|ultrapassar|atingir|resultar)\b)', "falta contração 'da'"),
    (r'\bde o (?![^.]{0,40}\b(?:ser|estar|ter|haver|poder|dever|ir|vir|'
     r'fazer|receber|nascer|manifestar-se|apresentar|desenvolver|'
     r'transmitir|herdar|surgir|ocorrer|manifestar|lançar|obter|tirar|sortear|escolher|acertar|falhar|repetir|sair|conter|ultrapassar|atingir|resultar)\b)', "falta contração 'do'"),
    (r'\bem a \b',                    "falta contração 'na'"),
    (r'\bem o \b',                    "falta contração 'no'"),
    # "a a" é erro, mas NÃO quando o primeiro "a" é pronome
    # oblíquo enclítico: "aplicando-a a 7 elementos" está certo.
    (r'(?<![\w-])a a (?!\w*mente)', "dupla preposição 'a a'"),
    (r'\bcorresponde a [ao] ',        "falta contração após 'corresponde'"),
    (r'\bchega a [ao] ',              "falta contração após 'chega'"),
    (r'\bos receptores (?:nuclear|canal|acoplado|ligado)\b', "número errado"),
    (r'\bseu (?:meia-vida|função|estrutura|via)\b', "gênero errado"),
    (r'\bgram:\s*gram-', "'Gram' duplicado entre comando e alternativa"),
    # Preposição truncada por fatiamento manual: "o papel d plasmócito".
    # Acontece quando se escreve d{art[1:]} em vez de usar a função de
    # contração — o fatiamento devolve o espaço junto.
    # "n", "d" e "p" soltos são VARIÁVEIS em enunciados de
    # matemática e computação: "n registros", "p elementos". A
    # truncagem real vem de d{art[1:]} e cola a letra a um termo
    # que já traria artigo — por isso a lista fechada.
    (r'(?<![A-Za-zÀ-ÿ0-9])[dnp]\s+(?:glicólise|plasmócito|ciclo|via|etapa|'
     r'folheto|epitélio|estrutura|organela|receptor|fármaco|músculo|'
     r'nervo|classe|célula|linfócito|macrófago|neutrófilo)(?![a-zà-ÿ])',
     "preposição truncada"),
    # "ao a", "ao o" — mas NÃO "ao I par", em que I é algarismo romano.
    (r'\bao\s+[ao]\s', "preposição malformada"),
    # Pronome oblíquo cujo referente muda de gênero conforme o campo
    # inserido: "a etapa que A precede" quebra quando o referente é "o
    # ciclo de Krebs". A correção é repetir o substantivo em vez de
    # pronominalizar.
    # Pronome oblíquo só é problema quando o REFERENTE vem de um campo
    # de gênero variável. "Considere o XI par... que O identifica" está
    # correto — "par" é sempre masculino.
    #
    # O padrão abaixo pega só a combinação arriscada: pronome FEMININO
    # cujo referente, na mesma frase, é uma palavra masculina do
    # catálogo. É a assinatura do erro real.
    (r'\b(?:o ciclo|o efeito|o volume|o clearance|o receptor|o reagente|'
     r'o gênero|o fármaco|o nível)\b[^.]{0,90}\bque\s+a\s+'
     r'(?:precede|sucede|antecede|classifica|identifica|define|caracteriza)\b',
     "pronome feminino com referente masculino"),
    (r'\b(?:a via|a etapa|a enzima|a célula|a classe|a estrutura)\b'
     r'[^.]{0,90}\bque\s+o\s+'
     r'(?:precede|sucede|antecede|classifica|identifica|define|caracteriza)\b',
     "pronome masculino com referente feminino"),
    # Cenário que já é oração completa emendado por ", considere":
    # "os reagentes seguem ordem definida, considere o álcool-acetona".
    (r'\b(?:seguem|segue|são|é|têm|tem|possui|apresenta)\b[^.,;]{0,40},\s*'
     r'(?:considere|analise|observe)\b', "duas orações emendadas por vírgula"),
]

# Substantivos de gênero conhecido, para detectar artigo trocado sem
# depender de listar cada combinação. Cobrem os campos que aparecem nas
# tabelas destes geradores.
#
# Listar caso a caso não funcionava: eu vinha acrescentando um padrão
# por vez conforme os erros apareciam em produção ("a ciclo", "o
# safranina", "a ácidos"), e a lista nunca fechava.
MASCULINOS = [
    "ciclo", "processo", "método", "efeito", "volume", "clearance",
    "receptor", "nervo", "par", "reagente", "lugol", "cristal",
    "álcool-acetona", "gênero", "fármaco", "alvo", "mecanismo",
    "peptidoglicano", "ácidos", "corpúsculo", "ducto", "forame",
    "ligamento", "tendão", "canal", "aqueduto", "antro", "espaço",
    "nível", "aminoácido", "piruvato", "citosol", "linfócito",
    "anticorpo", "macrófago", "neutrófilo", "basófilo", "eosinófilo",
    "plasmócito", "bacilo", "coco", "esporo",
    # Acrescentados após o erro "avalia-se a tipo de controle" passar:
    # a palavra não estava catalogada, e o teste não tinha como acusar.
    "tipo", "tipos", "número", "grau", "critério", "critérios",
    "componente", "modo", "papel", "sítio", "alvo", "arranjo",
    "conjunto", "produto", "produtos", "evento", "eventos", "folheto",
    "folhetos", "padrão", "padrões", "cruzamento", "genótipo",
    "fenótipo", "alelo", "alelos", "reagente", "reagentes",
]

# Exceções: expressões que começam com palavra masculina mas cujo NÚCLEO
# é feminino. "a piruvato quinase" está correto — o núcleo é "quinase".
EXCECOES_GENERO = [
    "piruvato quinase", "piruvato desidrogenase", "ácido cítrico",
    "ácido graxo", "ciclo de Krebs",
]
FEMININOS = [
    "via", "etapa", "cadeia", "enzima", "glicólise", "safranina",
    "estrutura", "função", "membrana", "parede", "célula", "reação",
    "meia-vida", "biodisponibilidade", "ligação", "curva", "pressão",
    "taxa", "arteríola", "secreção", "conversão", "reabsorção",
    "imunoglobulina", "hipersensibilidade", "coloração", "morfologia",
    "bactéria", "cápsula", "toxina", "endotoxina", "proteína",
    "descarboxilação", "gliconeogênese", "glicogênese", "lipogênese",
    "cetogênese", "beta-oxidação", "espessura", "cor", "presença",
    "suscetibilidade", "tuba", "glândula", "veia", "artéria", "fissura",
    "estriação", "posição", "origem", "marca", "delimitação",
    "característica", "particularidade", "denominação", "camada",
    "lâmina", "fibra", "junção", "herança", "transmissão",
]

def _artigo_trocado(texto):
    """
    Artigo masculino antes de substantivo feminino, ou vice-versa.

    Verifica apenas as palavras cujo gênero está catalogado acima —
    quando não sabemos o gênero, não acusamos.
    """
    achados = []
    baixo = texto.lower()
    for excecao in EXCECOES_GENERO:
        baixo = baixo.replace(excecao.lower(), "«excecao»")

    # O "a" depois de certos verbos é PREPOSIÇÃO de regência, não
    # artigo: "obedece a critérios", "corresponde a padrões",
    # "refere-se a folhetos". Neutraliza-se essa posição antes de
    # procurar artigo trocado, para não acusar construção correta.
    baixo = re.sub(r'\b(obedec\w+|correspond\w+|refer\w+-se|equival\w+|'
                   r'atend\w+|visa\w*|assist\w+|proced\w+|recorr\w+|'
                   r'aspir\w+|sobrevi\w+)\s+a\s+', r'\1 «prep» ', baixo)
    for palavra in MASCULINOS:
        # As CONTRAÇÕES também marcam gênero: "à", "pela", "numa".
        # Sem elas, "Quanto À tipo de controle" escapava.
        if re.search(r'(?:\b(?:a|na|da|uma|essa|esta|aquela|pela|nessa|'
                     r'desta|numa)|à)\s+' +
                     re.escape(palavra) + r'(?![a-zà-ÿ])', baixo):
            achados.append(f"artigo feminino antes de '{palavra}'")
    for palavra in FEMININOS:
        if re.search(r'\b(?:o|no|do|um|ao|esse|este|aquele|pelo|nesse|'
                     r'deste|num)\s+' +
                     re.escape(palavra) + r'(?![a-zà-ÿ])', baixo):
            achados.append(f"artigo masculino antes de '{palavra}'")
    return achados

# Nome próprio rebaixado por .capitalize()
NOMES_PROPRIOS = ["Krebs", "Gram", "Bohr", "Ranvier", "Golgi", "Bowman",
                  "Starling", "Falópio", "Eustáquio", "Willis", "Havers",
                  "Langerhans", "Malpighi", "Sylvius", "Monro", "Wirsung",
                  "Douglas", "Bauhin", "Aquiles", "Poupart", "Coombs",
                  "Gell", "Ziehl", "Neelsen", "Mycobacterium", "Mycoplasma",
                  "Staphylococcus", "Streptococcus", "Escherichia",
                  "Neisseria", "Clostridium", "Bacillus", "Treitz",
                  "Winslow", "Houston", "Wharton", "Stensen", "Vater",
                  "Oddi", "His", "Cooper", "Louis", "Galeno", "Wormian",
                  "Botallo", "Pecquet", "Santorini", "Highmore",
                  "Rosenmüller", "Skene", "Cowper", "Bartholin", "Retzius",
                  "Alcock", "Varólio", "Keith", "Flack", "Aschoff", "Tawara"]


def checar_redacao(questoes):
    """Concordância, contração e nomes próprios rebaixados."""
    achados = []
    for q in questoes:
        texto = q["enunciado"]
        baixo = texto.lower()

        for padrao, motivo in CONTRACOES_RUINS:
            if re.search(padrao, baixo):
                achados.append((motivo, texto[:88]))
                break
        else:
            trocados = _artigo_trocado(texto)
            if trocados:
                achados.append((trocados[0], texto[:88]))
                continue
            # Nome próprio em minúscula no meio da frase
            for nome in NOMES_PROPRIOS:
                if re.search(r'(?<![A-Za-zÀ-ÿ])' + nome.lower() +
                             r'(?![a-zà-ÿ])', texto):
                    achados.append((f"'{nome}' em minúscula", texto[:88]))
                    break
    return achados


def _conjunto_semantico(texto):
    """
    Classifica a alternativa em um grupo grosseiro, para detectar
    quando uma delas destoa das outras.

    Não pretende ser análise semântica: identifica os tipos que
    aparecem nas tabelas destes geradores.
    """
    t = str(texto).lower()
    if re.search(r'\b(?:citosol|matriz|membrana|lúmen|complexo de golgi|'
                 r'espaço interm|núcleo|retículo|parede|forame|canal|'
                 r'fissura|meato|córtex|medula|plasma|soro)\b', t):
        return "local"
    if re.search(r'\d+\s*(?:atp|nadh|fadh|gtp|co₂|co2|molécula)', t):
        return "rendimento"
    if re.search(r'^(?:a |o )?(?:glicólise|ciclo de krebs|cadeia transp|'
                 r'descarboxilação|gliconeogênese|glicogênese|glicogenólise|'
                 r'beta-oxidação|lipogênese|cetogênese|via das pentoses|'
                 r'ciclo da ureia|fermentação)', t):
        return "nome_de_via"
    if re.search(r'\b(?:mg/l|l/min|mmhg|horas|minutos|segundos|'
                 r'milissegundos)\b', t):
        return "medida"
    return "outro"


def checar_coerencia_tipo(questoes):
    """
    Uma alternativa de tipo diferente das demais indica campo errado.

    Quando um campo é acrescentado a uma tabela e os acessos por índice
    não são atualizados, o distrator passa a vir da coluna vizinha. O
    sintoma é sempre o mesmo: entre cinco alternativas, uma ou duas
    pertencem a outro conjunto semântico.
    """
    achados = []
    for q in questoes:
        tipos = [_conjunto_semantico(v) for v in q["alternativas"].values()]
        conhecidos = [t for t in tipos if t != "outro"]
        if len(conhecidos) < 3:
            continue          # sem base para comparar
        from collections import Counter
        contagem = Counter(conhecidos)
        dominante, n = contagem.most_common(1)[0]
        # Se o tipo dominante cobre a maioria mas há minoria de OUTRO
        # tipo conhecido, alguma alternativa veio do campo errado.
        minoria = [t for t in conhecidos if t != dominante]
        if n >= 3 and minoria:
            destoantes = [v for v, t in zip(q["alternativas"].values(), tipos)
                          if t in minoria]
            achados.append((f"{len(minoria)} alternativa(s) de tipo "
                            f"'{minoria[0]}' entre '{dominante}'",
                            q["enunciado"][:70], destoantes[0][:50]))
    return achados


GERADORES = [
    ("ADS",          "gerador_ads"),
    ("Eng. software", "gerador_engenharia"),
    ("Matemática",   "gerador_procedural"),
    ("Mat. básica",   "gerador_basica"),
    ("Português",     "gerador_portugues"),
    ("Direito",      "gerador_direito"),
    ("Redes",        "gerador_redes"),
    ("Saúde",        "gerador_saude"),
    ("Conceitual",   "gerador_decoreba"),
    ("Fisiologia",    "gerador_fisiologia"),
    ("Anatomia",      "gerador_anatomia"),
    ("Farmacologia",  "gerador_farmacologia"),
    ("Imunologia",    "gerador_imunologia"),
    ("Bioquímica",    "gerador_bioquimica"),
    ("Microbiologia", "gerador_microbiologia"),
    ("Histologia",    "gerador_histologia"),
    ("Embriologia",   "gerador_embriologia"),
    ("Genética",      "gerador_genetica"),
    ("Bio. celular",  "gerador_biocelular"),
]


def main(repeticoes=1000):
    print("═" * 64)
    print("  TESTE 11 — REDAÇÃO E COERÊNCIA DE TIPO")
    print("═" * 64)
    total = 0

    for nome, modulo in GERADORES:
        try:
            m = importlib.import_module(modulo)
        except ImportError:
            print(f"  ·  {nome:<16} (ausente)")
            continue

        lote = m.gerar_lote(repeticoes, seed=20260819)
        red = checar_redacao(lote)
        tipo = checar_coerencia_tipo(lote)
        n = len(red) + len(tipo)
        total += n

        marca = "✅" if n == 0 else "❌"
        print(f"\n  {marca} {nome:<16} {len(lote)} questões, {n} problema(s)")

        vistos = set()
        for motivo, texto in red[:4]:
            if motivo in vistos:
                continue
            vistos.add(motivo)
            print(f"       {motivo}")
            print(f"         {texto}")
        for motivo, enunciado, exemplo in tipo[:3]:
            print(f"       {motivo}")
            print(f"         {enunciado}")
            print(f"         alternativa: {exemplo}")

    print("\n" + "═" * 64)
    if total == 0:
        print("  🎉 TESTE 11 PASSOU")
    else:
        print(f"  ❌ {total} PROBLEMA(S)")
    print("═" * 64)
    return total


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    sys.exit(1 if main(n) else 0)
