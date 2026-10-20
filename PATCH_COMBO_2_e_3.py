"""
==============================================================
  PATCH 2 + 3 COMBINADO — Cola tudo de uma vez
==============================================================

OBJETIVO:
  - Corrige a rota /disponiveis (mostra "materia" preenchido)
  - Adiciona rota nova /montar (junta simulados em 1 grande)

ONDE COLAR:
  1. Abra simulados_api.py
  2. Ctrl + F: @app.get("/simulados/disponiveis")
  3. Selecione DA LINHA dessa rota ATÉ a linha em branco depois do
     return da função (vai cobrir ~75 linhas)
  4. APAGUE essa seleção
  5. COLE o bloco entre os marcadores ↓↓↓ e ↑↑↑ abaixo
  6. Ctrl + S pra salvar

NÃO COLE OS MARCADORES NEM ESSE COMENTÁRIO DE INSTRUÇÕES.
SÓ O QUE TIVER ENTRE ↓↓↓ E ↑↑↑.
"""

# ↓↓↓ COMECE A COPIAR DA LINHA SEGUINTE ↓↓↓

# ──────────────────────────────────────────────────────
#  ROTA: Listar simulados disponíveis no banco
#  Sem custo Gemini — lê do Firestore
# ──────────────────────────────────────────────────────

def _normalizar_materia(valor):
    """Normaliza nomes de matérias/áreas. Ex: ciencias_humanas -> humanas"""
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


@app.get("/disponiveis")
def listar_simulados_disponiveis(
    concurso: str           = Query(..., pattern="^(enem|enade)$", description="Tipo de concurso"),
    materia:  Optional[str] = Query(default=None, max_length=100, description="Filtrar por matéria/área (opcional)"),
    ano:      Optional[int] = Query(default=None, ge=2000, le=2030, description="Filtrar por ano (opcional)"),
    limite:   int           = Query(default=20, ge=1, le=100, description="Máximo de resultados"),
):
    """
    Lista simulados JÁ GERADOS disponíveis no banco.

    Vantagens:
    - ZERO custo Gemini (só lê do Firestore)
    - Resposta instantânea
    - Aceita materia OU area como filtro (normaliza)
    """
    concurso_norm = concurso.lower().strip()
    materia_norm  = _normalizar_materia(materia)

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

    simulados = []
    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        materia_doc = _normalizar_materia(meta.get("materia") or meta.get("area"))

        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        criado_em = d.get("criado_em")
        criado_iso = criado_em.isoformat() if hasattr(criado_em, "isoformat") else str(criado_em)

        simulados.append({
            "simulado_id":     d.get("simulado_id") or doc_snap.id,
            "concurso":        meta.get("concurso"),
            "materia":         materia_doc,
            "ano":             meta.get("ano"),
            "total_questoes":  len(d.get("questoes", [])),
            "criado_em":       criado_iso,
        })

        if len(simulados) >= limite:
            break

    simulados.sort(key=lambda s: s.get("criado_em", ""), reverse=True)

    return {
        "total":      len(simulados),
        "filtros":    {"concurso": concurso_norm, "materia": materia_norm, "ano": ano},
        "simulados":  simulados,
    }


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
    Cria simulado JUNTANDO questões de simulados já existentes.

    Vantagens:
    - ZERO custo Gemini
    - Resposta em ~200ms
    - Aproveita banco já populado
    """
    import random

    concurso_norm = concurso.lower().strip()
    materia_norm  = _normalizar_materia(materia)

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
    fontes_usadas  = []

    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        materia_doc = _normalizar_materia(meta.get("materia") or meta.get("area"))
        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        questoes_doc = d.get("questoes", [])
        if not questoes_doc:
            continue

        sim_id = d.get("simulado_id") or doc_snap.id
        for q in questoes_doc:
            q_copy = dict(q)
            q_copy["_origem_simulado"] = sim_id
            q_copy["_numero_original"] = q.get("numero")
            todas_questoes.append(q_copy)

        fontes_usadas.append(sim_id)

    if not todas_questoes:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma questão encontrada com os filtros (concurso={concurso_norm}, materia={materia_norm}, ano={ano})"
        )

    # Remove duplicatas (mesmo enunciado)
    vistos = set()
    questoes_unicas = []
    for q in todas_questoes:
        enunciado = (q.get("enunciado") or "").strip()[:200]
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

    # Pega a quantidade pedida
    questoes_finais = questoes_unicas[:quantidade]

    # Busca gabaritos das questões originais
    gabarito_final = []
    for idx, q in enumerate(questoes_finais, start=1):
        sim_origem = q.get("_origem_simulado")
        numero_original = q.get("_numero_original")
        if sim_origem and numero_original is not None:
            try:
                gab_doc = db.collection("gabaritos").document(sim_origem).get()
                if gab_doc.exists:
                    gab_data = gab_doc.to_dict() or {}
                    gab_list = gab_data.get("gabarito", [])
                    for g in gab_list:
                        if g.get("numero") == numero_original:
                            gabarito_final.append({
                                "numero":           idx,
                                "resposta_correta": g.get("resposta_correta", "?"),
                                "explicacao":       g.get("explicacao", "")
                            })
                            break
            except Exception as e:
                log.warning(f"Erro ao buscar gabarito de {sim_origem}: {e}")

    # Renumera questões e remove campos de debug
    questoes_limpas = []
    for idx, q in enumerate(questoes_finais, start=1):
        q_limpa = {k: v for k, v in q.items() if not k.startswith("_")}
        q_limpa["numero"] = idx
        questoes_limpas.append(q_limpa)

    # Cria novo simulado no banco
    novo_simulado_id = str(uuid.uuid4())

    meta_novo = {
        "concurso":         concurso_norm,
        "materia":          materia_norm,
        "ano":              ano,
        "quantidade":       len(questoes_limpas),
        "fonte":            "montado_do_banco",
        "simulados_origem": fontes_usadas[:10],
    }

    db.collection("simulados").document(novo_simulado_id).set({
        "simulado_id": novo_simulado_id,
        "questoes":    questoes_limpas,
        "meta":        meta_novo,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })

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
        "fonte_simulados":  fontes_usadas[:5],
        "custo_gemini":     0,
        "mensagem":         f"Simulado montado com {len(questoes_limpas)} questões do banco. Zero custo Gemini.",
    }


# ↑↑↑ PARE DE COPIAR NA LINHA ANTERIOR ↑↑↑
