"""
PATCH 2: Atualizar rota GET /disponiveis para lidar com `area` vs `materia`

CONTEXTO:
Os simulados no banco têm o campo como `meta.area` (não `meta.materia`),
porque foram gerados pela rota /enem/inspirar que usa `area`.
Este patch faz a rota /disponiveis entender AMBOS os campos.

INSTRUÇÕES:
1. Abra simulados_api.py
2. Localize a função `listar_simulados_disponiveis` (linha ~3603)
3. SUBSTITUA a função INTEIRA pelo código abaixo
   (ou seja: do @app.get até o último return inclusive)
"""

# ──────────────────────────────────────────────────────
#  ROTA: Listar simulados disponíveis no banco
#  Sem custo Gemini — lê do Firestore
#  Versão 2: entende meta.area e meta.materia
# ──────────────────────────────────────────────────────

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMECE A COPIAR DAQUI ↓
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    - Aceita filtro por materia OU area (normaliza os 2)

    Uso típico (cache-first):
    1. Frontend chama GET /disponiveis primeiro
    2. Se retorna >0 simulados → usa um deles (instantâneo)
    3. Se retorna 0 → chama POST /enem/inspirar (gera com IA)
    """
    concurso_norm = concurso.lower().strip()

    # Normalização de matéria/área — torna humanas == ciencias_humanas
    def normalizar_materia(valor):
        if not valor:
            return None
        v = str(valor).lower().strip()
        # Mapeia variações comuns para forma canônica
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

        # Pega materia OU area (o que tiver)
        materia_raw = meta.get("materia") or meta.get("area")
        materia_doc = normalizar_materia(materia_raw)

        # Aplica filtros opcionais em Python
        if materia_norm and materia_doc != materia_norm:
            continue
        if ano is not None and meta.get("ano") != ano:
            continue

        # Monta resposta resumida (sem as questões — só metadados)
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

    # Ordena: mais recentes primeiro
    simulados.sort(key=lambda s: s.get("criado_em", ""), reverse=True)

    return {
        "total":      len(simulados),
        "filtros":    {"concurso": concurso_norm, "materia": materia_norm, "ano": ano},
        "simulados":  simulados,
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARE DE COPIAR AQUI ↑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
