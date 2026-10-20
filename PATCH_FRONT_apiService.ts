/*
==============================================================
  PATCH FRONT-END — apiService.ts
==============================================================

INSTRUÇÕES:

Esse patch tem 3 partes. Aplica na ordem.

ARQUIVO: services/apiService.ts

──────────────────────────────────────────────────────────────
  PARTE 1: ADICIONAR helper buildSimuladoFromMeta
──────────────────────────────────────────────────────────────

LOCAL: logo APÓS a função normalizeSimulado (~linha 164)
       (antes de "// ── FIRESTORE HELPERS")

COLA:
*/

// ── BUILDER: META → SIMULADO ──────────────────────────────────────────────────

/**
 * Constroi um Simulado parcial a partir dos metadados de GET /disponiveis.
 * As questoes ficam vazias — serao carregadas via buscarPorId quando o
 * usuario clicar no card.
 */
function buildSimuladoFromMeta(meta: any, tipo: 'ENEM' | 'ENADE'): Simulado {
  const ano       = meta.ano ?? '';
  const materiaR  = String(meta.materia ?? meta.area ?? 'geral').replace(/_/g, ' ');
  const materiaCap = materiaR.charAt(0).toUpperCase() + materiaR.slice(1);
  const totalQ    = meta.total_questoes ?? 0;

  // Imagens padrao por tipo (Unsplash, sem autenticacao)
  const IMG_ENEM  = 'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?q=80&w=600';
  const IMG_ENADE = 'https://images.unsplash.com/photo-1491841573634-28140fc7ced7?q=80&w=600';

  return {
    id:              meta.simulado_id,
    titulo:          ano ? `${tipo} ${ano} — ${materiaCap}` : `${tipo} — ${materiaCap}`,
    descricao:       `${totalQ} questao(oes) — pronto pra fazer`,
    tipo,
    questoes:        [],  // vazio: carregado sob demanda em buscarPorId
    duracao_minutos: Math.max(totalQ * 3, 15),
    total_questoes:  totalQ,
    imagem:          tipo === 'ENEM' ? IMG_ENEM : IMG_ENADE,
  };
}


/*
──────────────────────────────────────────────────────────────
  PARTE 2: SUBSTITUIR simuladosApi.listar
──────────────────────────────────────────────────────────────

LOCAL: dentro do objeto simuladosApi (~linha 353)

SUBSTITUI a funcao listar INTEIRA (linha do "listar: async" ate o }
do return [];).

COLA esta versao nova:
*/

  listar: async (tipo?: 'ENEM' | 'ENADE'): Promise<Simulado[]> => {
    const t = tipo ?? 'ENEM';

    // 1. Firestore cache
    try {
      const docs = await fsSimulados(tipo);
      if (docs.length > 0) return docs;
    } catch (e) { console.warn('[simuladosApi] Firestore:', e); }

    // 2. NOVA: GET /disponiveis — lista simulados ja prontos no banco (ZERO Gemini)
    //    Retorna 20+ simulados via metadados (questoes carregadas sob demanda).
    try {
      const concurso = t.toLowerCase();
      const qs = new URLSearchParams({ concurso, limite: '50' });
      console.log('[simuladosApi] GET /disponiveis?' + qs.toString());
      const raw = await restFetch<any>(`/disponiveis?${qs}`, undefined, 30000);
      const lista = Array.isArray(raw?.simulados) ? raw.simulados : [];
      if (lista.length > 0) {
        const sims = lista.map((s: any) => buildSimuladoFromMeta(s, t));
        syncToFirestore('simulados', sims).catch(() => {});
        return sims;
      }
    } catch (e) { console.warn('[simuladosApi] /disponiveis:', e); }

    // 3. Fallback: POST /simulado?fonte=banco — 1 simulado de 5 questoes
    try {
      const concurso = t.toLowerCase();
      const def      = t === 'ENADE' ? ENADE_DEFAULT : ENEM_DEFAULT;
      const simuladoMateria = ({ humanas: 'ciencias_humanas', natureza: 'ciencias_natureza' } as Record<string,string>)[def.area] ?? def.area;
      const qs = new URLSearchParams({
        concurso,
        materia:    simuladoMateria,
        quantidade: '5',
        ano:        String(def.ano),
        fonte:      'banco',
      });
      console.log('[simuladosApi] POST /simulado?' + qs.toString());
      const raw = await restFetch<any>(`/simulado?${qs}`, { method: 'POST' }, 60000);
      if (raw?.id || raw?.questoes || raw?.questions) {
        const sim = normalizeSimulado(raw, t);
        if (sim.questoes.length > 0) {
          syncToFirestore('simulados', [sim]).catch(() => {});
          return [sim];
        }
      }
    } catch (e) { console.warn('[simuladosApi] /simulado (fonte=banco):', e); }

    // 4. Ultimo recurso: POST /{tipo}/inspirar — gera com Gemini (gasta cota)
    try {
      const concurso = t.toLowerCase();
      const qs       = buildInspirParams(t, undefined, 5);
      console.log('[simuladosApi] fallback POST /' + concurso + '/inspirar?' + qs.toString());
      const raw = await restFetch<any>(`/${concurso}/inspirar?${qs}`, { method: 'POST' }, 150000);
      if (raw) {
        const sim = normalizeSimulado(raw, t);
        if (sim.questoes.length > 0) {
          syncToFirestore('simulados', [sim]).catch(() => {});
          return [sim];
        }
      }
    } catch (e) { console.warn('[simuladosApi] /inspirar fallback:', e); }

    return [];
  },


/*
──────────────────────────────────────────────────────────────
  PARTE 3: ADICIONAR nova funcao simuladosApi.montar
──────────────────────────────────────────────────────────────

LOCAL: dentro do objeto simuladosApi
       (logo APÓS listar e ANTES de buscarPorId, OU
        em qualquer outro lugar dentro do objeto)

ATENCAO: nao esqueca da virgula antes!

COLA:
*/

  /**
   * Monta simulado grande juntando varios simulados existentes do banco.
   * ZERO custo Gemini — usa apenas questoes ja salvas.
   *
   * Usado para criar simulados de 20-40 questoes sem gastar quota.
   *
   * @param tipo       'ENEM' ou 'ENADE'
   * @param quantidade Numero de questoes desejadas (5-50, padrao 20)
   * @param materia    Filtrar por materia/area (opcional)
   * @param ano        Filtrar por ano (opcional)
   */
  montar: async (
    tipo: 'ENEM' | 'ENADE',
    quantidade = 20,
    materia?:  string,
    ano?:      number,
  ): Promise<Simulado | null> => {
    try {
      const concurso = tipo.toLowerCase();
      const qs = new URLSearchParams({
        concurso,
        quantidade: String(quantidade),
      });
      if (materia) qs.append('materia', materia);
      if (ano)     qs.append('ano',     String(ano));

      console.log('[simuladosApi.montar] POST /montar?' + qs.toString());
      const raw = await restFetch<any>(`/montar?${qs}`, { method: 'POST' }, 30000);

      if (raw?.questoes?.length > 0) {
        const sim = normalizeSimulado(raw, tipo);
        // Sobrescreve titulo pra ficar mais legivel
        sim.titulo    = `${tipo} — Simulado Completo (${sim.questoes.length} questoes)`;
        sim.descricao = 'Montado a partir do banco — questoes variadas';
        syncToFirestore('simulados', [sim]).catch(() => {});
        return sim;
      }
    } catch (e) {
      console.warn('[simuladosApi.montar]:', e);
    }
    return null;
  },


/*
==============================================================
  FIM DOS PATCHES
==============================================================

VERIFICACAO APOS APLICAR:
  - npx tsc --noEmit (verifica erros de tipo)
  - Inicia o app e abre tela de simulados
  - Esperado: ~20 cards aparecem (eram 1 antes)

COMO USAR O simuladosApi.montar (chamada futura):
  // Em qualquer tela onde queira simulado de 40 questoes:
  const sim = await simuladosApi.montar('ENEM', 40);
  if (sim) navigate('FazerSimulado', { simuladoId: sim.id });

  // Filtrado por materia:
  const sim = await simuladosApi.montar('ENEM', 30, 'humanas');

  // Filtrado por ano e materia:
  const sim = await simuladosApi.montar('ENEM', 20, 'matematica', 2023);
*/
