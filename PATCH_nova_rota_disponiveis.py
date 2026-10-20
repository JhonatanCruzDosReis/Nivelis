"""
PATCH: Adicionar rota GET /simulados/disponiveis no simulados_api.py

INSTRUÇÕES:
1. Abra o arquivo simulados_api.py
2. Localize a linha com: @app.get("/historico")  (perto da linha 3589)
3. Cole o código abaixo LOGO ANTES dessa linha
4. Salve, commite, dá push -- Render re-deploya sozinho
"""

# ──────────────────────────────────────────────────────
#  NOVA ROTA: Listar simulados disponíveis no banco
#  Sem custo Gemini — lê do Firestore
# ──────────────────────────────────────────────────────

@app.get("/simulados/disponiveis")
def listar_simulados_disponiveis(
    concurso: str           = Query(..., pattern="^(enem|enade)$", description="Tipo de concurso"),
    materia:  Optional[str] = Query(default=None, max_length=100, description="Filtrar por matéria (opcional)"),
    ano:      Optional[int] = Query(default=None, ge=2000, le=2030, description="Filtrar por ano (opcional)"),
    limite:   int           = Query(default=20, ge=1, le=100, description="Máximo de resultados"),
):
    """
    Lista simulados JÁ GERADOS disponíveis no banco.

    Vantagens:
    - ZERO custo Gemini (só lê do Firestore)
    - Resposta instantânea
    - Filtra por concurso/matéria/ano

    Uso típico (cache-first):
    1. Frontend chama GET /simulados/disponiveis primeiro
    2. Se retorna >0 simulados → usa um deles (instantâneo)
    3. Se retorna 0 → chama POST /enem/inspirar (gera com IA)
    """
    concurso_norm = concurso.lower().strip()
    materia_norm  = materia.lower().strip() if materia else None

    # Busca apenas por concurso + ativos (filtros simples)
    # Filtros adicionais aplicados em Python para evitar índices compostos
    try:
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .where("ativo", "==", True) \
                  .limit(100)

        docs = list(query.stream())
    except Exception as e:
        # Fallback: alguns simulados antigos podem não ter campo "ativo"
        log.warning(f"Query com 'ativo' falhou, tentando sem: {e}")
        query = db.collection("simulados") \
                  .where("meta.concurso", "==", concurso_norm) \
                  .limit(100)
        docs = list(query.stream())

    simulados = []
    for doc_snap in docs:
        d = doc_snap.to_dict()
        meta = d.get("meta", {}) or {}

        # Aplica filtros opcionais em Python
        if materia_norm and meta.get("materia", "").lower() != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        # Monta resposta resumida (sem as questões — só metadados)
        criado_em = d.get("criado_em")
        criado_iso = criado_em.isoformat() if hasattr(criado_em, "isoformat") else str(criado_em)

        simulados.append({
            "simulado_id":     d.get("simulado_id") or doc_snap.id,
            "concurso":        meta.get("concurso"),
            "materia":         meta.get("materia"),
            "ano":             meta.get("ano"),
            "total_questoes":  len(d.get("questoes", [])),
            "criado_em":       criado_iso,
        })

        if len(simulados) >= limite:
            break

    # Ordena: mais recentes primeiro
    simulados.sort(key=lambda s: s.get("criado_em", ""), reverse=True)

    return {
        "total":      len(simulados),
        "filtros":    {"concurso": concurso_norm, "materia": materia_norm, "ano": ano},
        "simulados":  simulados,
    }


# ──────────────────────────────────────────────────────
#  FIM DO PATCH — abaixo continua o código original (@app.get("/historico"))
# ──────────────────────────────────────────────────────
