"""
==============================================================
  PATCH 3: Rota que JUNTA simulados existentes
==============================================================

CONTEXTO:
Você tem 20+ simulados de 5 questões no banco. Essa nova rota
junta as questões deles num "super simulado" com 10, 20, 30+
questões. ZERO custo Gemini.

INSTRUÇÕES:
1. Abra simulados_api.py
2. Localize a rota /disponiveis (a do PATCH 2 que você acabou
   de atualizar — linha ~3603)
3. Cole o código abaixo LOGO ABAIXO do return dela
   (antes do próximo @app.get)

URL FINAL:
   POST /v1/simulados/montar
   Exemplo: POST /v1/simulados/montar?concurso=enem&quantidade=20

PARÂMETROS:
   - concurso: "enem" ou "enade" (obrigatório)
   - quantidade: número de questões desejadas (default 20, max 50)
   - materia: filtrar por matéria/área (opcional)
   - ano: filtrar por ano (opcional)
   - embaralhar: mistura aleatória (default true)

RETORNA:
   {
     "simulado_id": "novo-uuid-aqui",
     "origem": "montado_do_banco",
     "concurso": "enem",
     "total_questoes": 20,
     "questoes": [...],
     "fonte_simulados": ["id1", "id2", "id3"],  // de onde veio
     "custo_gemini": 0
   }
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMECE A COPIAR DAQUI ↓
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ──────────────────────────────────────────────────────
#  ROTA: Montar simulado a partir de simulados existentes
#  Zero custo Gemini — junta questões já no banco
# ──────────────────────────────────────────────────────

@app.post("/montar")
def montar_simulado_do_banco(
    concurso:    str            = Query(..., pattern="^(enem|enade)$", description="Tipo de concurso"),
    quantidade:  int            = Query(default=20, ge=5, le=50, description="Quantidade de questões (5-50)"),
    materia:     Optional[str]  = Query(default=None, max_length=100, description="Filtrar por matéria/área"),
    ano:         Optional[int]  = Query(default=None, ge=2000, le=2030, description="Filtrar por ano"),
    embaralhar:  bool           = Query(default=True, description="Embaralhar questões"),
):
    """
    Cria um simulado JUNTANDO questões de simulados já existentes no banco.

    Vantagens:
    - ZERO custo Gemini
    - Resposta em ~200ms
    - Aproveita simulados de 5 questões pra montar simulados maiores

    Lógica:
    1. Busca simulados ativos do concurso especificado
    2. Junta as questões de vários simulados
    3. Aplica filtros (matéria, ano) se houver
    4. Remove duplicatas (mesmo enunciado)
    5. Embaralha (opcional) e pega 'quantidade' questões
    6. Cria um NOVO simulado no banco com essas questões
    7. Retorna pronto pra uso
    """
    import random

    concurso_norm = concurso.lower().strip()

    # Normalizar matéria (mesma lógica do PATCH 2)
    def normalizar_materia(valor):
        if not valor:
            return None
        v = str(valor).lower().strip()
        equivalencias = {
            "ciencias_humanas":  "humanas",
            "ciencias_natureza": "natureza",
            "ciencias da humanas":  "humanas",
            "ciencias da natureza": "natureza",
            "linguagem":   "linguagens",
            "matemática":  "matematica",
        }
        return equivalencias.get(v, v)

    materia_norm = normalizar_materia(materia)

    # Busca simulados disponíveis
    try:
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .where("ativo", "==", True) \
                  .limit(100)
        docs = list(query.stream())
    except Exception as e:
        log.warning(f"Query com 'ativo' falhou: {e}")
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .limit(100)
        docs = list(query.stream())

    if not docs:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum simulado de '{concurso_norm}' encontrado no banco."
        )

    # Junta todas as questões aplicando filtros
    todas_questoes = []
    fontes_usadas = []  # IDs dos simulados origem (pra rastreabilidade)

    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        # Aplica filtros opcionais
        materia_doc = normalizar_materia(meta.get("materia") or meta.get("area"))
        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        questoes_doc = d.get("questoes", [])
        if not questoes_doc:
            continue

        # Marca cada questão com a origem (pra debug)
        sim_id = d.get("simulado_id") or doc_snap.id
        for q in questoes_doc:
            q_copy = dict(q)
            q_copy["_origem_simulado"] = sim_id
            todas_questoes.append(q_copy)

        fontes_usadas.append(sim_id)

    if not todas_questoes:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma questão encontrada com os filtros (concurso={concurso_norm}, materia={materia_norm}, ano={ano})"
        )

    # Remove duplicatas (mesmo enunciado — questões idênticas)
    vistos = set()
    questoes_unicas = []
    for q in todas_questoes:
        enunciado = (q.get("enunciado") or "").strip()[:200]  # primeiros 200 chars como chave
        if enunciado and enunciado not in vistos:
            vistos.add(enunciado)
            questoes_unicas.append(q)

    if len(questoes_unicas) < 5:
        raise HTTPException(
            status_code=404,
            detail=f"Apenas {len(questoes_unicas)} questões únicas no banco. Mínimo é 5."
        )

    # Embaralha se solicitado
    if embaralhar:
        random.shuffle(questoes_unicas)

    # Pega a quantidade pedida (ou menos se não tiver tantas)
    questoes_finais = questoes_unicas[:quantidade]

    # Renumera questões pra ter sequência 1, 2, 3...
    for idx, q in enumerate(questoes_finais, start=1):
        q["numero"] = idx

    # Cria novo simulado no banco
    novo_simulado_id = str(uuid.uuid4())

    # Monta gabarito a partir das questões originais (se tiverem gabarito embutido)
    # Como não temos acesso direto aos gabaritos antigos aqui, vamos buscar
    gabarito_final = []
    for idx, q in enumerate(questoes_finais, start=1):
        sim_origem = q.get("_origem_simulado")
        if sim_origem:
            try:
                gab_doc = db.collection("gabaritos").document(sim_origem).get()
                if gab_doc.exists:
                    gab_data = gab_doc.to_dict() or {}
                    gab_list = gab_data.get("gabarito", [])
                    # Procura o gabarito da questão pelo número ORIGINAL
                    numero_original = q.get("_numero_original") or q.get("numero")
                    for g in gab_list:
                        if g.get("numero") == numero_original:
                            gabarito_final.append({
                                "numero":           idx,  # numero novo
                                "resposta_correta": g.get("resposta_correta", "?"),
                                "explicacao":       g.get("explicacao", "")
                            })
                            break
            except Exception as e:
                log.warning(f"Não conseguiu buscar gabarito do simulado {sim_origem}: {e}")

    # Limpa o campo de debug "_origem_simulado" das questões antes de retornar
    questoes_limpas = []
    for q in questoes_finais:
        q_limpa = {k: v for k, v in q.items() if not k.startswith("_")}
        questoes_limpas.append(q_limpa)

    # Salva o novo simulado
    meta_novo = {
        "concurso":         concurso_norm,
        "materia":          materia_norm,
        "ano":              ano,
        "quantidade":       len(questoes_limpas),
        "fonte":            "montado_do_banco",
        "simulados_origem": fontes_usadas[:10],  # primeiros 10 pra não crescer demais
    }

    db.collection("simulados").document(novo_simulado_id).set({
        "simulado_id": novo_simulado_id,
        "questoes":    questoes_limpas,
        "meta":        meta_novo,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })

    # Salva gabarito separado
    if gabarito_final:
        db.collection("gabaritos").document(novo_simulado_id).set({
            "simulado_id": novo_simulado_id,
            "gabarito":    gabarito_final,
            "criado_em":   datetime.now(timezone.utc)
        })

    return {
        "simulado_id":      novo_simulado_id,
        "origem":           "montado_do_banco",
        "concurso":         concurso_norm,
        "materia":          materia_norm,
        "ano":              ano,
        "total_questoes":   len(questoes_limpas),
        "questoes":         questoes_limpas,
        "fonte_simulados":  fontes_usadas[:5],  # mostra de onde veio
        "custo_gemini":     0,
        "mensagem":         f"Simulado montado com {len(questoes_limpas)} questões do banco. Zero custo Gemini.",
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARE DE COPIAR AQUI ↑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
