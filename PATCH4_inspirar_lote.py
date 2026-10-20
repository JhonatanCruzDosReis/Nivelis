"""
==============================================================
  PATCH 4: Rotas /inspirar-lote (gera em lotes de 5)
==============================================================

CONTEXTO:
O Gemini quebra JSON quando pede >5 questões com LaTeX (matemática).
Solução: gerar em lotes de 5 + 5 + 5... internamente, e juntar.

ESTRATÉGIA:
Criar rotas NOVAS (não modificar as existentes):
   POST /enem/inspirar-lote
   POST /enade/inspirar-lote

Front pode usar essas rotas pra pedir 20+ questões.
Rotas antigas (/inspirar) continuam funcionando do jeito que estão.

⚠️ IMPORTANTE:
- Cada lote chama Gemini 1x. 20 questões = 4 chamadas Gemini.
- Gasta MAIS cota que /inspirar normal.
- Se 1 lote falhar, os outros continuam (resiliente).

INSTRUÇÕES:
1. Abra simulados_api.py
2. Localize a rota /enem/inspirar (linha ~2451)
3. Cole o código abaixo LOGO APÓS o último return dela
   (antes do próximo @app.get/@app.post)
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMECE A COPIAR DAQUI ↓
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ──────────────────────────────────────────────────────
#  ROTA: ENEM em LOTES — divide pedidos grandes em 5+5+5
#  Resolve problema de JSON quebrado com >5 questões
# ──────────────────────────────────────────────────────

@app.post("/enem/inspirar-lote")
def gerar_enem_em_lotes(
    ano:        AnoEnemEnum,
    area:       AreaEnemEnum  = AreaEnemEnum.matematica,
    quantidade: int           = Query(default=20, ge=10, le=50, description="Quantidade (10-50)"),
    caderno:    int           = Query(default=1, ge=1, le=10),
):
    """
    Gera simulado ENEM com 10+ questões dividindo em lotes de 5.

    Estratégia:
    - Pedido de 20 questões → chama Gemini 4x com 5 cada
    - Se 1 lote falha, outros continuam
    - Junta tudo num simulado só ao final

    Custo:
    - 20 questões = ~4 chamadas Gemini (uma por lote)
    - Tempo: ~1 minuto (Gemini é serial)

    Use isso quando precisar de simulado grande.
    Para simulado pequeno (5 questões), use /enem/inspirar normal.
    """
    import uuid as uuid_lib

    LOTE_SIZE = 5  # quantidade por chamada Gemini
    num_lotes = (quantidade + LOTE_SIZE - 1) // LOTE_SIZE  # arredonda pra cima

    log.info(f"[LOTE ENEM] Pedido de {quantidade} questões → {num_lotes} lotes de {LOTE_SIZE}")

    todas_questoes  = []
    todos_gabaritos = []
    lotes_falhados  = 0
    lotes_sucesso   = 0

    for i in range(num_lotes):
        # Quantos pedir nesse lote (último lote pode pedir menos)
        restantes = quantidade - len(todas_questoes)
        qtd_lote = min(LOTE_SIZE, restantes)

        if qtd_lote <= 0:
            break

        log.info(f"[LOTE ENEM] Lote {i+1}/{num_lotes}: pedindo {qtd_lote} questões...")

        try:
            # Chama a função que já existe (mesma que /enem/inspirar usa)
            resultado_lote = gerar_questoes_inspiradas_enem(
                ano=ano,
                area=area,
                quantidade=qtd_lote,
                caderno=caderno,
            )

            questoes_lote = resultado_lote.get("questoes", [])
            if questoes_lote:
                # Renumera questões pra ter sequência única
                for q in questoes_lote:
                    q["numero"] = len(todas_questoes) + 1
                    todas_questoes.append(q)

                lotes_sucesso += 1
                log.info(f"[LOTE ENEM] Lote {i+1} OK ({len(questoes_lote)} questões)")
            else:
                lotes_falhados += 1
                log.warning(f"[LOTE ENEM] Lote {i+1} retornou vazio")

        except Exception as e:
            lotes_falhados += 1
            log.warning(f"[LOTE ENEM] Lote {i+1} falhou: {e}")
            # Continua pros próximos lotes mesmo se um falhar

    if not todas_questoes:
        raise HTTPException(
            status_code=500,
            detail=f"Todos os {num_lotes} lotes falharam. Tente novamente ou use /enem/inspirar."
        )

    # Cria simulado novo juntando tudo
    novo_simulado_id = str(uuid_lib.uuid4())

    meta_novo = {
        "concurso":       "enem",
        "ano":            int(ano.value) if hasattr(ano, "value") else int(ano),
        "area":           str(area.value) if hasattr(area, "value") else str(area),
        "quantidade":     len(todas_questoes),
        "fonte":          "inspirado_em_lotes",
        "lotes_sucesso":  lotes_sucesso,
        "lotes_falhados": lotes_falhados,
    }

    db.collection("simulados").document(novo_simulado_id).set({
        "simulado_id": novo_simulado_id,
        "questoes":    todas_questoes,
        "meta":        meta_novo,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })

    log.info(f"[LOTE ENEM] Concluído: {len(todas_questoes)} questões em {lotes_sucesso}/{num_lotes} lotes")

    return {
        "simulado_id":     novo_simulado_id,
        "origem":          "inspirado_em_lotes",
        "concurso":        "enem",
        "ano":             meta_novo["ano"],
        "area":            meta_novo["area"],
        "total_questoes":  len(todas_questoes),
        "lotes_sucesso":   lotes_sucesso,
        "lotes_falhados":  lotes_falhados,
        "questoes":        todas_questoes,
    }


# ──────────────────────────────────────────────────────
#  ROTA: ENADE em LOTES — mesma estratégia
# ──────────────────────────────────────────────────────

@app.post("/enade/inspirar-lote")
def gerar_enade_em_lotes(
    ano:               AnoEnadeEnum,
    area:              AreaEnadeEnum  = AreaEnadeEnum.direito,
    quantidade:        int            = Query(default=20, ge=10, le=50, description="Quantidade (10-50)"),
    dificuldade:       Optional[DificuldadeEnum] = None,
    topico_especifico: Optional[str]  = Query(default=None, max_length=TOPICO_MAX_LENGTH),
):
    """
    Gera simulado ENADE com 10+ questões dividindo em lotes de 5.

    Mesma estratégia do /enem/inspirar-lote: divide em lotes,
    cada lote é uma chamada Gemini independente, se um falhar
    os outros continuam.
    """
    import uuid as uuid_lib

    LOTE_SIZE = 5
    num_lotes = (quantidade + LOTE_SIZE - 1) // LOTE_SIZE

    log.info(f"[LOTE ENADE] Pedido de {quantidade} questões → {num_lotes} lotes")

    todas_questoes  = []
    lotes_falhados  = 0
    lotes_sucesso   = 0

    for i in range(num_lotes):
        restantes = quantidade - len(todas_questoes)
        qtd_lote = min(LOTE_SIZE, restantes)

        if qtd_lote <= 0:
            break

        log.info(f"[LOTE ENADE] Lote {i+1}/{num_lotes}: pedindo {qtd_lote} questões")

        try:
            resultado_lote = gerar_questoes_inspiradas_enade(
                ano=ano,
                area=area,
                quantidade=qtd_lote,
                dificuldade=dificuldade,
                topico_especifico=topico_especifico,
            )

            questoes_lote = resultado_lote.get("questoes", [])
            if questoes_lote:
                for q in questoes_lote:
                    q["numero"] = len(todas_questoes) + 1
                    todas_questoes.append(q)

                lotes_sucesso += 1
                log.info(f"[LOTE ENADE] Lote {i+1} OK")
            else:
                lotes_falhados += 1

        except Exception as e:
            lotes_falhados += 1
            log.warning(f"[LOTE ENADE] Lote {i+1} falhou: {e}")

    if not todas_questoes:
        raise HTTPException(
            status_code=500,
            detail=f"Todos os {num_lotes} lotes falharam. Tente novamente ou use /enade/inspirar."
        )

    novo_simulado_id = str(uuid_lib.uuid4())

    meta_novo = {
        "concurso":       "enade",
        "ano":            int(ano.value) if hasattr(ano, "value") else int(ano),
        "area":           str(area.value) if hasattr(area, "value") else str(area),
        "quantidade":     len(todas_questoes),
        "fonte":          "inspirado_em_lotes",
        "lotes_sucesso":  lotes_sucesso,
        "lotes_falhados": lotes_falhados,
    }

    db.collection("simulados").document(novo_simulado_id).set({
        "simulado_id": novo_simulado_id,
        "questoes":    todas_questoes,
        "meta":        meta_novo,
        "criado_em":   datetime.now(timezone.utc),
        "ativo":       True
    })

    log.info(f"[LOTE ENADE] Concluído: {len(todas_questoes)} questões")

    return {
        "simulado_id":     novo_simulado_id,
        "origem":          "inspirado_em_lotes",
        "concurso":        "enade",
        "ano":             meta_novo["ano"],
        "area":            meta_novo["area"],
        "total_questoes":  len(todas_questoes),
        "lotes_sucesso":   lotes_sucesso,
        "lotes_falhados":  lotes_falhados,
        "questoes":        todas_questoes,
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARE DE COPIAR AQUI ↑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
