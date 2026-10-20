"""
=============================================================
  NIVELIS — Rotas dos Geradores Procedurais
=============================================================

  Módulo importável, não trecho para colar.

  No simulados_api.py, DEPOIS de criar o app e de definir
  salvar_questoes_banco e salvar_simulado_firebase, basta:

      from rotas_procedurais import registrar_rotas
      registrar_rotas(app, db, log, salvar_questoes_banco,
                      salvar_simulado_firebase)

  Assim, substituir o simulados_api.py não apaga mais as rotas
  procedurais — elas vivem aqui.

  Requer na MESMA pasta:
     gerador_ads.py            (23 templates — ENADE Computação)
     gerador_procedural.py     (15 templates — matemática)
     gerador_saude.py          (16 templates — saúde)
     gerador_fisiologia.py     (14 templates — fisiologia médica)
     gerador_anatomia.py       (7 templates — anatomia humana)
     gerador_farmacologia.py   (7 templates — farmacologia)
     gerador_imunologia.py     (11 templates — imunologia)
     gerador_bioquimica.py     (9 templates — bioquímica)
     gerador_microbiologia.py  (7 templates — microbiologia)
     gerador_histologia.py     (6 templates — histologia)
     gerador_embriologia.py    (6 templates — embriologia)
     gerador_genetica.py       (6 templates — genética médica)
     gerador_biocelular.py     (6 templates — biologia celular)
     gerador_decoreba.py       (10 templates — conceitual)
     gerador_direito.py        (17 templates — direito)
     gerador_redes.py          (12 templates — redes)
     gerador_interpretacao.py  (5 tipos — interpretação de texto)
     montar_simulado_procedural.py
=============================================================
"""

import uuid
from datetime import datetime, timezone
from typing   import Optional

from fastapi import HTTPException, Query


def registrar_rotas(app, db, log, salvar_questoes_banco,
                    salvar_simulado_firebase):
    """
    Registra as rotas procedurais no app do simulados_api.

    Recebe as dependências por parâmetro (injeção) em vez de importá-las,
    evitando import circular: o simulados_api importa este módulo, não o
    contrário.
    """

    # ──────────────────────────────────────────
    #  BLOCO — GERAÇÃO PROCEDURAL (sem IA, custo zero)
    # ──────────────────────────────────────────

    GERADORES = {}

    # Cada disciplina é carregada de forma INDEPENDENTE.
    #
    # Antes, todos os imports ficavam num único bloco try: um arquivo
    # ausente derrubava o módulo inteiro, e a rota devolvia 503 para
    # TODAS as disciplinas — inclusive as que estavam presentes.
    #
    # Agora a disciplina que falta simplesmente não aparece na lista, e
    # o log diz qual arquivo não foi encontrado.
    _CATALOGO = [
        ("ads", "gerador_ads", "TOPICOS_ADS",
         "Análise e Desenvolvimento de Sistemas — algoritmos, estruturas "
         "de dados, banco de dados e redes"),
        ("administracao", "gerador_administracao", "TOPICOS_ADMINISTRACAO",
         "Administração — custos, formação de preço, análise de balanço, "
         "investimentos e teorias da administração"),
        ("matematica", "gerador_procedural", "TOPICOS_MATEMATICA",
         "Matemática — combinatória, probabilidade e estatística"),
        ("saude", "gerador_saude", "TOPICOS_SAUDE",
         "Saúde — cálculo clínico, epidemiologia e bioestatística"),
        # "medicina" não entra: não existe gerador_medicina.py. Medicina é
        # um grupo que a montagem expande nas dez disciplinas do ciclo
        # básico, todas listadas logo abaixo. Enquanto a linha existiu, todo
        # boot registrava "gerador_medicina ausente" em _ausentes — um
        # alarme falso num log que só deveria apontar arquivo que sumiu.
        ("fisiologia", "gerador_fisiologia", "TOPICOS_FISIOLOGIA",
         "Fisiologia médica — transporte de gases, filtração glomerular, "
         "hemodinâmica e sistema renina-angiotensina"),
        ("anatomia", "gerador_anatomia", "TOPICOS_ANATOMIA",
         "Anatomia humana — nervos cranianos, base do crânio e "
         "Terminologia Anatômica"),
        ("farmacologia", "gerador_farmacologia", "TOPICOS_FARMACOLOGIA",
         "Farmacologia — receptores adrenérgicos, superfamílias de "
         "receptores e farmacocinética (mecanismo, sem dose)"),
        ("imunologia", "gerador_imunologia", "TOPICOS_IMUNOLOGIA",
         "Imunologia — hipersensibilidade (Gell e Coombs), "
         "imunoglobulinas e células do sistema imune"),
        ("bioquimica", "gerador_bioquimica", "TOPICOS_BIOQUIMICA",
         "Bioquímica — respiração celular, glicólise, proteínas e vias "
         "metabólicas"),
        ("microbiologia", "gerador_microbiologia", "TOPICOS_MICROBIOLOGIA",
         "Microbiologia — coloração de Gram, parede bacteriana, "
         "morfologia e alvos dos antimicrobianos"),
        ("histologia", "gerador_histologia", "TOPICOS_HISTOLOGIA",
         "Histologia — epitélios de revestimento e tecido muscular"),
        ("embriologia", "gerador_embriologia", "TOPICOS_EMBRIOLOGIA",
         "Embriologia — folhetos germinativos, derivados e cronologia "
         "do desenvolvimento"),
        ("genetica", "gerador_genetica", "TOPICOS_GENETICA",
         "Genética médica — padrões de herança, heredograma e "
         "probabilidade"),
        ("biocelular", "gerador_biocelular", "TOPICOS_BIOCELULAR",
         "Biologia celular — organelas, transporte pela membrana e "
         "ciclo celular"),
        ("direito", "gerador_direito", "TOPICOS_DIREITO",
         "Direito — prazos processuais, competência e recursos"),
        ("redes", "gerador_redes", "TOPICOS_REDES",
         "Redes de computadores — endereçamento, sub-redes e protocolos"),
        ("portugues", "gerador_portugues", "TOPICOS_PORTUGUES",
         "Português — crase, classes de palavras, concordância verbal "
         "e figuras de linguagem"),
        ("basica", "gerador_basica", "TOPICOS_BASICA",
         "Matemática básica — fundamental, médio e ENEM: porcentagem, "
         "regra de três, equações, juros, estatística e geometria"),
        ("engenharia", "gerador_engenharia", "TOPICOS_ENGENHARIA",
         "Engenharia de software — princípios SOLID, orientação a "
         "objetos e padrões de projeto"),
        ("conceitual", "gerador_decoreba", "TOPICOS_DECOREBA",
         "Conceitual — definições, siglas e classificações"),
    ]

    _ausentes = []
    for _chave, _modulo, _attr_topicos, _descricao in _CATALOGO:
        try:
            _m = __import__(_modulo)
        except ImportError:
            _ausentes.append(_modulo)
            continue
        if not hasattr(_m, "gerar_para_api"):
            _ausentes.append(f"{_modulo} (sem gerar_para_api)")
            continue
        GERADORES[_chave] = {
            "modulo":    _m,
            "gerar":     _m.gerar_para_api,
            "topicos":   getattr(_m, _attr_topicos, {}),
            "casar":     getattr(_m, "templates_para_topicos", None),
            "descricao": _descricao,
        }

    try:
        import gerador_interpretacao as _g_int
    except ImportError:
        _g_int = None
        _ausentes.append("gerador_interpretacao")

    PROCEDURAL_OK = bool(GERADORES)

    if GERADORES:
        _total = sum(sum(len(v) for v in g["topicos"].values())
                     for g in GERADORES.values() if g["topicos"])
        print(f"[PROCEDURAL] ✅ {len(GERADORES)} geradores carregados "
              f"({_total} templates)")
    if _ausentes:
        print(f"[PROCEDURAL] ⚠ Não encontrados: {', '.join(_ausentes)}")
        print(f"[PROCEDURAL]   As demais disciplinas continuam disponíveis.")




    def _carregar_livros(ids_texto: str):
        """
        Carrega um ou mais livros e devolve (docs, topicos, trechos, titulos).

        Aceita IDs separados por vírgula. Vários livros da mesma área são
        comuns — medicina raramente cabe num volume só —, e uni-los amplia
        tanto o casamento de tópicos quanto o acervo de trechos para
        interpretação, que é onde a variedade mais faz falta.

        Um ID inválido interrompe com 404: falhar em silêncio faria o
        usuário achar que o livro foi considerado quando não foi.
        """
        ids = [x.strip() for x in str(ids_texto).split(",") if x.strip()]
        if not ids:
            raise HTTPException(status_code=400, detail="Nenhum livro_id informado.")

        docs, topicos, trechos, titulos = [], [], [], []
        for lid in ids:
            doc = db.collection("livros").document(lid).get()
            if not doc.exists:
                raise HTTPException(status_code=404,
                                    detail=f"Livro não encontrado: {lid}")
            dados = doc.to_dict()
            titulo = dados.get("titulo", "(sem título)")
            docs.append(dados)
            titulos.append(titulo)

            for cap in dados.get("capitulos", []):
                if cap.get("titulo"):
                    topicos.append(cap["titulo"])
                topicos.extend(cap.get("topicos", []) or [])

            for t in (dados.get("trechos") or []):
                trechos.append({**t,
                                "livro_titulo": titulo,
                                "livro_autor": dados.get("autor", "")})

        return docs, topicos, trechos, titulos


    def _exigir_procedural():
        if not PROCEDURAL_OK:
            raise HTTPException(
                status_code=503,
                detail="Geradores procedurais indisponíveis. Confirme que "
                       "gerador_ads.py, gerador_procedural.py, gerador_saude.py, "
                       "gerador_fisiologia.py e "
                       "gerador_decoreba.py estão na mesma pasta da API."
            )


    @app.get("/procedural/areas", tags=["Procedural (sem IA)"],
             summary="O que os geradores em Python cobrem")
    def listar_areas_procedurais():
        """Lista todas as disciplinas e áreas cobertas pelos geradores em Python."""
        _exigir_procedural()
        return {
            "disciplinas": {
                nome: {
                    "descricao": g["descricao"],
                    "areas":     {t: len(v) for t, v in g["topicos"].items()},
                    "templates": sum(len(v) for v in g["topicos"].values()),
                }
                for nome, g in GERADORES.items()
            },
            "total_templates": sum(sum(len(v) for v in g["topicos"].values())
                                   for g in GERADORES.values()),
            "custo_gemini": 0,
            "observacao": "Gabaritos calculados por código — sem cota, sem IA.",
        }


    @app.get("/procedural/topicos",
             tags=["Procedural (sem IA)"],
             summary="Catálogo de tópicos, para o app montar botões")
    def procedural_topicos(
        disciplina: str = Query(None, description="Filtra por disciplina"),
        nivel: str = Query(None, description="fundamental | médio"),
    ):
        """
        Devolve os tópicos com RÓTULO LEGÍVEL, para o app montar botões
        do tipo "gerar questão de equação do segundo grau".

        Cada item traz:
          chave   — o que enviar em `topico` na rota de geração
          rotulo  — o texto do botão
          nivel   — fundamental ou médio, quando aplicável
          area    — agrupamento para organizar a tela

        Depois, para gerar daquele tópico:
          POST /procedural/gerar?disciplina=basica&topico=equacao_2grau
        """
        if not PROCEDURAL_OK:
            raise HTTPException(status_code=503,
                                detail="geradores não disponíveis")

        saida = {}
        for chave, cfg in GERADORES.items():
            if disciplina and chave != disciplina:
                continue
            mod = cfg["modulo"]
            listar = getattr(mod, "listar_topicos", None)
            if listar:
                itens = listar(nivel) if nivel else listar()
            elif nivel:
                # Sem catálogo próprio, o filtro por nível não se aplica
                itens = []
            else:
                itens = [{"chave": area,
                          "rotulo": area.replace("_", " ").capitalize(),
                          "nivel": None, "area": area}
                         for area in (cfg["topicos"] or {})]
            if itens:
                saida[chave] = itens

        # TETO POR DISCIPLINA, para a tela não oferecer o que o material
        # não sustenta. Engenharia tem doze fatos distintos: um caderno
        # de 30 repete assunto, e antes isso só aparecia depois, dentro
        # da prova. Aqui o app já monta o seletor com o limite certo.
        limites, grupos = {}, {}
        try:
            from montar_simulado_procedural import (
                GRUPOS_DISCIPLINA, expandir_grupos, maximo_sugerido)
            _carregados = {k: True for k in GERADORES}
            for chave in list(saida) + list(GRUPOS_DISCIPLINA):
                expandidas = expandir_grupos([chave], _carregados)
                limites[chave] = maximo_sugerido(expandidas)
            grupos = {g: d for g, d in GRUPOS_DISCIPLINA.items()}
        except ImportError:
            pass

        return {
            "disciplinas": saida,
            "maximo_sugerido": limites,
            "grupos": grupos,
            "como_usar": ("POST /procedural/gerar?disciplina=<disciplina>"
                          "&topico=<chave do tópico>"),
            "sobre_o_maximo": (
                "maximo_sugerido é quantas questões o material da "
                "disciplina sustenta sem repetir assunto. Acima disso o "
                "simulado ainda é montado, mas o campo fatos_repetidos "
                "da resposta dirá quantas questões reaproveitaram um "
                "assunto já presente. Disciplinas de lastro curto rendem "
                "mais dentro de um grupo: engenharia sozinha comporta "
                "poucos, dentro de 'computacao' comporta muitos."),
        }

    @app.post("/procedural/gerar", tags=["Procedural (sem IA)"],
              summary="Gera questões de uma disciplina")
    def gerar_questoes_procedurais(
        disciplina: str           = Query(default="ads",
                                          description="ads | matematica | saude | fisiologia | "
                                                      "anatomia | farmacologia | imunologia | "
                                                      "bioquimica | microbiologia | histologia | "
                                                      "embriologia | genetica | biocelular | "
                                                      "direito | redes | conceitual"),
        quantidade: int           = Query(default=10, ge=1, le=100),
        topico:     Optional[str] = Query(default=None,
                                          description="Área dentro da disciplina (ver /procedural/areas)"),
        salvar:     bool          = Query(default=True,
                                          description="false = apenas pré-visualizar"),
        seed:       Optional[int] = Query(default=None, description="Lote reproduzível"),
    ):
        """
        Gera questões por CÓDIGO — sem IA, sem cota, gabarito garantido.

        disciplina=ads         → ENADE Computação (algoritmos, ED, BD, redes, SO, ES)
        disciplina=matematica  → combinatória e probabilidade
        disciplina=saude       → cálculo clínico, epidemiologia, bioestatística
        disciplina=fisiologia   → transporte de gases, filtração glomerular,
                                  hemodinâmica, sistema renina-angiotensina
        disciplina=anatomia     → nervos cranianos, base do crânio,
                                  Terminologia Anatômica
        disciplina=farmacologia → receptores adrenérgicos, superfamílias
                                  de receptores, farmacocinética
        disciplina=imunologia   → hipersensibilidade (Gell e Coombs),
                                  imunoglobulinas, células do sistema imune
        disciplina=bioquimica   → respiração celular, glicólise,
                                  proteínas, vias metabólicas
        disciplina=microbiologia → coloração de Gram, parede bacteriana,
                                  morfologia, antimicrobianos
        disciplina=histologia   → epitélios de revestimento, tecido muscular
        disciplina=embriologia  → folhetos germinativos, derivados,
                                  cronologia do desenvolvimento
        disciplina=genetica     → padrões de herança, heredograma,
                                  probabilidade em cruzamentos
        disciplina=biocelular   → organelas, transporte pela membrana,
                                  ciclo celular
        disciplina=direito     → prazos, prescrição, competências, honorários
        disciplina=redes       → IPv4/IPv6, sub-redes, VLSM, sumarização
        disciplina=conceitual  → memorização (portas, HTTP, OSI, ACID, Scrum...)

        Para matérias interpretativas (português, filosofia), use as rotas com Gemini.
        """
        _exigir_procedural()

        disciplina = (disciplina or "ads").lower().strip()
        if disciplina not in GERADORES:
            raise HTTPException(
                status_code=400,
                detail=f"disciplina inválida. Use: {list(GERADORES.keys())}"
            )

        g = GERADORES[disciplina]

        # O tópico pode ser uma ÁREA ("álgebra") ou a chave de um tópico
        # individual ("equacao_2grau"), que é o que o app envia quando o
        # aluno clica num botão específico. Ambos são válidos.
        _mod = g["modulo"]
        _chaves_individuais = set()
        for _attr in dir(_mod):
            if _attr.startswith("TEMPLATES_") or _attr == "TEMPLATES":
                _t = getattr(_mod, _attr)
                if isinstance(_t, dict):
                    _chaves_individuais |= set(_t)

        if (topico and topico.lower() not in g["topicos"]
                and topico not in _chaves_individuais):
            _opcoes = list(g["topicos"].keys())
            if _chaves_individuais:
                _opcoes += sorted(_chaves_individuais)
            raise HTTPException(
                status_code=400,
                detail=f"Tópico '{topico}' inválido para '{disciplina}'. "
                       f"Use: {_opcoes}"
            )

        try:
            questoes_limpas, gabarito_final = g["gerar"](
                quantidade=quantidade,
                topico=topico.lower() if topico else None,
                seed=seed,
            )
        except Exception as e:
            log.error(f"[PROCEDURAL] Falha ao gerar ({disciplina}): {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao gerar questões: {e}")

        print(f"[PROCEDURAL] {len(questoes_limpas)} questões de {disciplina} "
              f"(tópico: {topico or 'todos'}) — custo Gemini: 0")

        if salvar:
            salvar_questoes_banco(
                questoes_limpas, gabarito_final,
                concurso="enade_procedural",
                ano=datetime.now(timezone.utc).year,
                materia=disciplina,
            )

        return {
            "origem":         "gerador_procedural",
            "disciplina":     disciplina,
            "topico":         topico or "todos",
            "total_geradas":  len(questoes_limpas),
            "salvo_no_banco": salvar,
            "custo_gemini":   0,
            "tokens_usados":  0,
            "questoes":       questoes_limpas,
            "gabarito":       "salvo no banco" if salvar else gabarito_final,
        }


    @app.post("/procedural/gerar-do-livro", tags=["Procedural (sem IA)"],
              summary="Gera a partir dos tópicos de um livro indexado")
    def gerar_do_livro_indexado(
        livro_id:   str           = Query(...,
                                          description="ID do livro indexado. Aceita "
                                                      "vários separados por vírgula."),
        quantidade: int           = Query(default=10, ge=1, le=100),
        salvar:     bool          = Query(default=True),
        seed:       Optional[int] = Query(default=None),
    ):
        """
        PIPELINE COMPLETO: livro indexado → questões em Python.

        O Gemini leu o livro UMA VEZ (na indexação) e registrou seus tópicos.
        Esta rota lê esses tópicos, descobre quais geradores correspondem a eles
        (em qualquer disciplina) e produz questões alinhadas ao conteúdo do livro,
        sem gastar nenhuma requisição de IA.

        Se nenhum gerador for compatível (ex.: livro de humanas), a rota informa
        isso em vez de gerar conteúdo fora do assunto.
        """
        _exigir_procedural()

        docs, topicos_livro, _trechos, titulos = _carregar_livros(livro_id)
        titulo     = " + ".join(titulos)
        disciplina = docs[0].get("disciplina", "")

        # Remove tópicos repetidos entre livros da mesma área
        vistos_top = set()
        topicos_livro = [t for t in topicos_livro
                         if not (str(t).lower() in vistos_top
                                 or vistos_top.add(str(t).lower()))]

        if not topicos_livro:
            raise HTTPException(
                status_code=400,
                detail=f"O livro '{titulo}' não possui tópicos indexados. "
                       f"Rode indexar_livro.py novamente."
            )

        # Procura templates compatíveis em TODAS as disciplinas
        casados = {}
        for nome, g in GERADORES.items():
            if not g["casar"]:
                continue
            achados = g["casar"](topicos_livro)
            if achados:
                casados[nome] = achados

        if not casados:
            _consultados = [n for n, g in GERADORES.items() if g["casar"]]
            _sem_casar   = [n for n, g in GERADORES.items() if not g["casar"]]
            return {
                "livro_id":      livro_id,
                "livro_titulo":  titulo,
                "livros_usados": titulos,
                "disciplina":    disciplina,
                "topicos_lidos": len(topicos_livro),
                "total_geradas": 0,
                "compativel":    False,
                "geradores_consultados": _consultados,
                "geradores_sem_casamento": _sem_casar,
                "topicos_do_livro": topicos_livro[:15],
                "mensagem":      (
                    "Nenhum gerador em Python corresponde aos tópicos deste "
                    "livro. Confira 'topicos_do_livro' e "
                    "'geradores_consultados' acima: se a área do livro está "
                    "na lista de consultados e mesmo assim não casou, as "
                    "palavras-chave do gerador podem precisar de ajuste. "
                    "Para conteúdo interpretativo, use /procedural/interpretacao "
                    "ou /livro/inspirar."
                ),
                "questoes":      [],
            }

        # Distribui a quantidade entre as disciplinas compatíveis
        por_disciplina = max(1, quantidade // len(casados))
        todas_q, todas_g = [], []
        numero = 1
        for nome, templates in casados.items():
            faltam = quantidade - len(todas_q)
            if faltam <= 0:
                break
            n = min(por_disciplina, faltam)
            qs, gb = GERADORES[nome]["gerar"](
                quantidade=n, templates=templates, seed=seed
            )
            for q, g_ in zip(qs, gb):
                q["numero"] = numero
                g_["numero"] = numero
                numero += 1
                todas_q.append(q)
                todas_g.append(g_)

        print(f"[PROCEDURAL] Livro '{titulo}': {len(topicos_livro)} tópicos → "
              f"{sum(len(v) for v in casados.values())} geradores → "
              f"{len(todas_q)} questões (custo Gemini: 0)")

        if salvar:
            salvar_questoes_banco(
                todas_q, todas_g,
                concurso="enade_procedural",
                ano=datetime.now(timezone.utc).year,
                materia=disciplina or "geral",
            )

        return {
            "livro_id":          livro_id,
            "livro_titulo":      titulo,
            "livros_usados":     titulos,
            "disciplina":        disciplina,
            "compativel":        True,
            "topicos_lidos":     len(topicos_livro),
            "geradores_casados": casados,
            "total_geradas":     len(todas_q),
            "salvo_no_banco":    salvar,
            "custo_gemini":      0,
            "questoes":          todas_q,
            "gabarito":          "salvo no banco" if salvar else todas_g,
        }


    @app.post("/procedural/interpretacao", tags=["Procedural (sem IA)"],
              summary="Questões de interpretação sobre trechos de um livro")
    def gerar_questoes_interpretacao(
        livro_id:   str           = Query(...,
                                          description="ID do livro indexado. Aceita "
                                                      "vários separados por vírgula — "
                                                      "mais livros, mais textos-base."),
        quantidade: int           = Query(default=10, ge=1, le=100),
        tipos:      Optional[str] = Query(default=None,
                                          description="Separados por vírgula: tese, pressuposto, "
                                                      "ideia_secundaria, nao_sustentada, assercao_razao"),
        salvar:     bool          = Query(default=True),
        seed:       Optional[int] = Query(default=None),
    ):
        """
        Gera questões de INTERPRETAÇÃO DE TEXTO a partir de um livro indexado —
        sem chamar IA no momento da geração.

        Como funciona: na indexação (indexar_livro.py), o Gemini já lê o PDF para
        montar o índice. Na mesma chamada ele extrai parágrafos aproveitáveis com
        a análise de cada um — tese, pressupostos, ideia secundária e afirmações
        que o texto não sustenta. Essa análise fica salva e vira o gabarito.

        Esta rota apenas reorganiza esse material verificado: escolhe o trecho,
        o tipo de pergunta, a redação do comando e embaralha as alternativas.
        Custo de Gemini por questão gerada: zero.

        Funciona para QUALQUER disciplina — o conteúdo vem do livro, não do código.
        Se o livro foi indexado antes desta funcionalidade, reindexe-o para que os
        trechos sejam extraídos.
        """
        _exigir_procedural()

        docs, _topicos, trechos, titulos = _carregar_livros(livro_id)
        dados   = docs[0]
        titulo  = " + ".join(titulos)

        if not trechos:
            raise HTTPException(
                status_code=400,
                detail=f"O livro '{titulo}' não possui trechos analisados. "
                       f"Isso acontece com livros indexados antes desta "
                       f"funcionalidade, ou com obras sem parágrafos adequados "
                       f"(coletâneas de exercícios, tabelas). Reindexe com "
                       f"indexar_livro.py --forcar para extrair os trechos."
            )

        if len(trechos) < _g_int.MIN_TRECHOS_NECESSARIOS:
            raise HTTPException(
                status_code=400,
                detail=f"O livro tem apenas {len(trechos)} trecho(s); são "
                       f"necessários ao menos {_g_int.MIN_TRECHOS_NECESSARIOS} "
                       f"para gerar distratores variados."
            )

        lista_tipos = None
        if tipos:
            lista_tipos = [x.strip() for x in tipos.split(",") if x.strip()]
            invalidos = [x for x in lista_tipos if x not in _g_int.TIPOS_QUESTAO]
            if invalidos:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipos inválidos: {invalidos}. "
                           f"Use: {list(_g_int.TIPOS_QUESTAO.keys())}"
                )

        try:
            questoes_limpas, gabarito_final = _g_int.gerar_para_api(
                trechos, quantidade=quantidade, tipos=lista_tipos, seed=seed
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.error(f"[INTERPRETACAO] Falha ao gerar: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao gerar questões: {e}")

        print(f"[INTERPRETACAO] Livro '{titulo}': {len(trechos)} trechos → "
              f"{len(questoes_limpas)} questões (custo Gemini: 0)")

        if salvar:
            salvar_questoes_banco(
                questoes_limpas, gabarito_final,
                concurso="interpretacao",
                ano=datetime.now(timezone.utc).year,
                materia=dados.get("disciplina", "geral"),
            )

        return {
            "origem":          "gerador_interpretacao",
            "livro_id":        livro_id,
            "livro_titulo":    titulo,
            "livros_usados":   titulos,
            "disciplina":      dados.get("disciplina", ""),
            "trechos_no_banco": len(trechos),
            "trechos_sem_ancora": sum(
                1 for t in trechos if t.get("ancoras")
                and not t.get("ancoras_verificadas", True)),
            "tipos":           lista_tipos or list(_g_int.TIPOS_QUESTAO.keys()),
            "total_geradas":   len(questoes_limpas),
            "salvo_no_banco":  salvar,
            "custo_gemini":    0,
            "aviso": (
                "Alguns trechos têm afirmações que não foram localizadas no "
                "próprio texto — as questões geradas a partir deles merecem "
                "conferência. Reindexe o livro para regerar a análise."
                if any(t.get("ancoras") and not t.get("ancoras_verificadas", True)
                       for t in trechos) else None),
            "questoes":        questoes_limpas,
            "gabarito":        "salvo no banco" if salvar else gabarito_final,
        }


    @app.post("/procedural/simulado", tags=["Procedural (sem IA)"],
              summary="Simulado completo — funciona SEM livro; o livro só "
                      "acrescenta a fatia de interpretação")
    def montar_simulado_procedural(
        quantidade:  int           = Query(default=30, ge=5, le=100),
        disciplinas: str           = Query(default="ads",
                                           description="Separadas por vírgula. Veja a lista "
                                                       "completa em GET /procedural/areas. "
                                                       "Ex.: basica,portugues — ou "
                                                       "fisiologia,anatomia"),
        livro_id:    Optional[str] = Query(default=None,
                                           description="OPCIONAL — deixe VAZIO para gerar sem "
                                                       "livro. Se informado, acrescenta uma "
                                                       "fatia de interpretação a partir do "
                                                       "livro indexado; sem ele, essa fatia é "
                                                       "redistribuída entre as demais fontes."),
        ponderar:    bool          = Query(default=True,
                                           description="Usar provas analisadas para pesar as áreas"),
        area_prova:  Optional[str] = Query(default=None,
                                           description="Área das provas a considerar (ex: computacao)"),
        mistura:     Optional[str] = Query(default=None,
                                           description="Proporção custom: 'procedural,conceitual,interpretacao' "
                                                       "— ex: '50,25,25'"),
        conceitual:  Optional[str] = Query(default=None,
                                           description="Áreas conceituais, separadas por vírgula "
                                                       "(redes, banco_dados, algoritmos, eng_software). "
                                                       "Por padrão só entram as compatíveis com a disciplina."),
        seed:        Optional[int] = Query(default=None),
        incluir_gabarito: bool     = Query(default=False,
                                           description="Devolve o gabarito junto com as questões. "
                                                       "O app precisa disso para corrigir offline — "
                                                       "a tela de simulado compara a resposta com "
                                                       "q.gabarito na hora da entrega, e sem o campo "
                                                       "toda questão contaria como erro. Mesma "
                                                       "convenção de /exercicios/gerar."),
    ):
        """
        Monta um SIMULADO COMPLETO em Python — sem chamar IA.

        Combina as três fontes de questão na proporção 40/30/30 (ajustável):

          40%  procedural    — cálculo e simulação (gabarito calculado)
          30%  conceitual    — memorização (tabela de fatos verificados)
          30%  interpretação — sobre trechos de um livro indexado

        Se o livro não for informado ou não tiver trechos, a fatia de
        interpretação é redistribuída e o simulado sai completo mesmo assim.

        A fatia CONCEITUAL só traz áreas compatíveis com a disciplina pedida. Como
        o conteúdo conceitual disponível é todo de computação, um simulado de
        matemática ou saúde não recebe questões sobre portas de rede ou SQL — a
        fatia é redistribuída. Use `conceitual` para sobrescrever esse filtro.

        Quando há provas em 'provas_analisadas', a distribuição DENTRO da fatia
        procedural segue a frequência com que cada assunto foi cobrado — o
        simulado espelha o que a banca realmente pede.

        O resultado é salvo como simulado (coleção 'simulados' + 'gabaritos'),
        no mesmo formato das rotas com IA, então o aplicativo consome sem
        nenhuma alteração.
        """
        _exigir_procedural()

        lista_disc = [d.strip().lower() for d in disciplinas.split(",") if d.strip()]

        # As disciplinas válidas vêm dos geradores REALMENTE CARREGADOS,
        # não de uma lista fixa. Antes eram cinco nomes escritos à mão, e
        # as disciplinas acrescentadas depois eram recusadas pela rota
        # mesmo estando disponíveis no módulo de simulado.
        validas = {k for k in GERADORES
                   if k not in ("conceitual", "interpretacao")}

        # Os GRUPOS também são nomes válidos: "medicina" expande para as
        # dez disciplinas do ciclo básico, "computacao" para três, e
        # assim por diante. Sem isso, o app teria de montar a lista
        # completa na tela.
        try:
            import montar_simulado_procedural as _ms
            validas |= set(getattr(_ms, "GRUPOS_DISCIPLINA", {}))
        except ImportError:
            pass
        invalidas = [d for d in lista_disc if d not in validas]
        if invalidas:
            raise HTTPException(
                status_code=400,
                detail=f"Disciplinas inválidas: {invalidas}. Use: {sorted(validas)}"
            )
        if not lista_disc:
            lista_disc = ["ads"]

        # ── Mistura customizada ──
        proporcao = None
        if mistura:
            try:
                partes = [float(x) for x in mistura.split(",")]
                if len(partes) != 3 or sum(partes) <= 0:
                    raise ValueError
                total = sum(partes)
                proporcao = {
                    "procedural":    partes[0] / total,
                    "conceitual":    partes[1] / total,
                    "interpretacao": partes[2] / total,
                }
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=400,
                    detail="mistura deve ter 3 números separados por vírgula, "
                           "ex: '50,25,25'"
                )

        # ── Áreas conceituais (sobrescreve o filtro automático) ──
        lista_conceitual = None
        if conceitual:
            lista_conceitual = [x.strip().lower() for x in conceitual.split(",") if x.strip()]
            validas_con = set(_g_con.TOPICOS_DECOREBA)
            invalidas_con = [x for x in lista_conceitual if x not in validas_con]
            if invalidas_con:
                raise HTTPException(
                    status_code=400,
                    detail=f"Áreas conceituais inválidas: {invalidas_con}. "
                           f"Use: {sorted(validas_con)}"
                )

        # ── Trechos do livro (fatia de interpretação) ──
        trechos, livro_titulo, titulos = None, None, []
        if livro_id:
            _docs, _tops, brutos, titulos = _carregar_livros(livro_id)
            livro_titulo = " + ".join(titulos)
            if brutos:
                trechos = brutos
            else:
                print(f"[SIMULADO] '{livro_titulo}' sem trechos — "
                      f"fatia de interpretação será redistribuída")

        # ── Provas para ponderação ──
        provas = []
        if ponderar:
            try:
                query = db.collection("provas_analisadas")
                for d in query.stream():
                    p = d.to_dict()
                    if area_prova and _g_int and \
                       area_prova.lower() not in str(p.get("area", "")).lower():
                        continue
                    provas.append(p)
            except Exception as e:
                print(f"[SIMULADO] Não foi possível ler provas_analisadas: {e}")

        # ── Monta ──
        #
        # O módulo é importado AQUI, não no bloco global: a refatoração
        # que tornou os imports independentes removeu o `_montador` sem
        # que nada acusasse, porque ele só é referenciado nesta linha.
        try:
            import montar_simulado_procedural as _montador
        except ImportError as _e:
            raise HTTPException(
                status_code=503,
                detail=f"montador de simulado não disponível: {_e}"
            )

        try:
            resultado = _montador.montar(
                quantidade=quantidade,
                disciplinas=lista_disc,
                trechos=trechos,
                provas=provas or None,
                mistura=proporcao,
                seed=seed,
                areas_conceituais=lista_conceitual,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.error(f"[SIMULADO] Falha ao montar: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao montar simulado: {e}")

        questoes = resultado["questoes"]
        gabarito = resultado["gabarito"]

        if len(questoes) < quantidade:
            print(f"[SIMULADO] ⚠ Material insuficiente: {len(questoes)} de "
                  f"{quantidade} questões geradas")

        # ── Salva no mesmo formato das rotas com IA ──
        simulado_id = str(uuid.uuid4())
        meta = {
            "origem":      "procedural",
            "disciplinas": lista_disc,
            "composicao":  resultado["composicao"],
            "areas_conceituais": resultado.get("areas_conceituais", []),
            "livro_id":    livro_id,
            "livro_titulo": livro_titulo,
            "livros_usados": titulos,
            "ponderado_por_prova": resultado["ponderado_por_prova"],
            "provas_consideradas": len(provas),
            "custo_gemini": 0,
        }
        salvar_simulado_firebase(simulado_id, questoes, gabarito, meta)

        print(f"[SIMULADO] {simulado_id[:8]}: {len(questoes)} questões "
              f"({resultado['composicao']}) — custo Gemini: 0")

        corpo = {
            "simulado_id":   simulado_id,
            "origem":        "procedural",
            "total":         len(questoes),
            "solicitado":    quantidade,
            "composicao":    resultado["composicao"],
            "areas_conceituais": resultado.get("areas_conceituais", []),
            "disciplinas":   lista_disc,
            "livro_titulo":  livro_titulo,
            "livros_usados": titulos,
            "ponderado_por_prova": resultado["ponderado_por_prova"],
            "custo_gemini":  0,
            "tokens_usados": 0,
            "questoes":      questoes,
        }
        # O gabarito só sai quando pedido. O padrão continua sendo não
        # mandar — quem corrige pelo servidor (POST /simulado/{id}/
        # resultado) não precisa dele, e mandar à toa entrega a prova.
        if incluir_gabarito:
            corpo["gabarito"] = gabarito
        return corpo


    print(f"[PROCEDURAL] Rotas registradas no app")
