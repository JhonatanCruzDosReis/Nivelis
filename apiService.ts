// Nivelis API Service - v14 (reconhece tipos _INSPIRADO)
// MUDANCA v14: listarDoBanco reconhece ENEM_INSPIRADO/ENADE_INSPIRADO (usa
//   includes em vez de ===). Antes essas questoes caiam no fallback e
//   embaralhavam ENEM/ENADE. Agora o tipo e lido corretamente.
// MUDANCA v13: listarDoBanco mapeia area do app (humanas/natureza/linguagens)
//   para materias granulares do banco (sociologia, historia, biologia, etc).
//   Necessario porque reclassificamos as materias para nomes especificos.
// MUDANCA v12: listarDoBanco ignora questoes com tem_visual_quebrado=true ou
//   ativo=false (graficos/imagens que nao aparecem no app). Busca 300 (compensa filtro).
// MUDANCA v11: listarDoBanco usa colecao 'questoes' com gabarito
// MUDANCA v10: nova funcao listarDoBanco (versao antiga, lia simulados)
// MUDANCA v9: simulados de livro aparecem no app, classificados por disciplina
// MUDANCA v8: buscarPorId pede 20 questoes e usa todas
// MUDANCA v7: filtra simulados vazios + parou de poluir banco
// Cascata simulados: 1. Firestore (so cheios)  2. GET /disponiveis (so se Firestore vazio)
// buscarPorId: prioriza questoes salvas, senao /montar com materia + filtra ja feitas
// questoesFeitasApi: grava no Firestore quais questoes o usuario respondeu (anti-repeticao)

import {
  collection, getDocs, doc, getDoc,
  addDoc, setDoc, query, where,
  limit as fsLimit, serverTimestamp,
  arrayUnion,
} from 'firebase/firestore';
import { db } from './firebase';

// ── BASE URLs ─────────────────────────────────────────────────────────────────
// Todos os paths no openapi.json sao relativos ao prefixo do servidor
const SIMULADOS_BASE = 'https://nivelis-api-1.onrender.com/v1/simulados';
const QUESTOES_BASE  = 'https://nivelis-api-1.onrender.com/v1/questoes';

// ── TIPOS ─────────────────────────────────────────────────────────────────────

export interface Alternativa {
  id: string;
  texto: string;
}

export interface Questao {
  id: string | number;
  materia: string;
  topico?: string;
  enunciado: string;
  alternativas: Alternativa[];
  gabarito?: string;
  ano?: number;
  tipo?: 'ENEM' | 'ENADE';
  sessao_id?: string; // ID da sessao na API de Questoes (para correcao)
  explicacao?: string; // explicacao da resposta (explicacao_ia na colecao questoes)
  contexto?: string;   // texto de apoio antes do enunciado
}

export interface Simulado {
  id: string | number;
  titulo: string;
  descricao?: string;
  tipo: 'ENEM' | 'ENADE';
  questoes: Questao[];
  duracao_minutos?: number;
  total_questoes?: number;
  imagem?: string;
}

export interface ResultadoSimulado {
  simulado_id: string | number;
  usuario_uid: string;
  respostas: Record<string, string>;
  acertos: number;
  total: number;
  tempo_segundos?: number;
  data: string;
}

export interface NoticiaAPI {
  id?: string | number;
  titulo?: string;
  title?: string;
  imagem?: string;
  image?: string;
  url?: string;
  link?: string;
  tipo?: string;
  tag?: string;
  publicado_em?: string;
  fonte?: string;
}

// ── HTTP HELPERS ──────────────────────────────────────────────────────────────

async function apiFetch<T>(base: string, path: string, opts?: RequestInit, ms = 35000): Promise<T> {
  const ctrl = new AbortController();
  const tid  = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(base + path, {
      ...opts,
      signal: ctrl.signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(opts?.headers ?? {}) },
    });
    clearTimeout(tid);
    if (!res.ok) {
      const b = await res.text().catch(() => '');
      throw new Error('[' + res.status + '] ' + path + ' — ' + b);
    }
    return res.json() as Promise<T>;
  } catch (e: any) {
    clearTimeout(tid);
    if (e.name === 'AbortError') throw new Error('Tempo esgotado: ' + path);
    throw e;
  }
}

const restFetch     = <T>(path: string, opts?: RequestInit, ms?: number) => apiFetch<T>(SIMULADOS_BASE, path, opts, ms);
const questoesFetch = <T>(path: string, opts?: RequestInit, ms?: number) => apiFetch<T>(QUESTOES_BASE,  path, opts, ms);

// ── NORMALIZERS ───────────────────────────────────────────────────────────────

function normalizeList<T>(raw: any): T[] {
  if (Array.isArray(raw)) return raw;
  for (const k of ['exercicios', 'questoes', 'items', 'results', 'data', 'simulados', 'content', 'list', 'questions']) {
    if (Array.isArray(raw?.[k])) return raw[k] as T[];
  }
  return [];
}

/** Aceita alternativas como {A:"...",B:"..."} ou [{id:"A",texto:"..."}] */
function normalizeAlternativas(alts: any): Alternativa[] {
  if (!alts) return [];
  if (Array.isArray(alts)) {
    return alts.map((a: any) => ({
      id:    String(a.id ?? a.letra ?? a.key ?? a.opcao ?? '?'),
      texto: String(a.texto ?? a.text ?? a.enunciado ?? a.descricao ?? a),
    }));
  }
  if (typeof alts === 'object') {
    return Object.entries(alts).map(([k, v]) => ({ id: k, texto: String(v) }));
  }
  return [];
}

function normalizeQuestao(q: any, tipo?: 'ENEM' | 'ENADE', sessao_id?: string): Questao {
  const inferido: 'ENEM' | 'ENADE' | undefined =
    tipo
    ?? (q.tipo === 'ENEM'  || q.tipo  === 'enem'  ? 'ENEM'
      : q.tipo === 'ENADE' || q.tipo  === 'enade' ? 'ENADE'
      : q.concurso === 'enem'  ? 'ENEM'
      : q.concurso === 'enade' ? 'ENADE'
      : undefined);
  return {
    id:           q.id ?? q.questao_id ?? String(Date.now() + Math.random()),
    materia:      q.materia ?? q.area ?? q.disciplina ?? q.categoria ?? 'Geral',
    topico:       q.topico  ?? q.assunto ?? q.tema ?? q.subtopico,
    enunciado:    q.enunciado ?? q.texto  ?? q.pergunta ?? q.statement ?? '',
    alternativas: normalizeAlternativas(q.alternativas ?? q.opcoes ?? q.options ?? q.choices),
    gabarito:     q.gabarito ?? q.resposta_correta ?? q.answer ?? q.correta,
    ano:          q.ano ?? q.year,
    tipo:         inferido,
    sessao_id:    sessao_id ?? q.sessao_id,
    explicacao:   q.explicacao ?? q.explicacao_ia ?? q.explanation ?? q.justificativa,
    contexto:     q.contexto ?? q.texto_apoio ?? q.suporte,
  };
}

/** Normaliza resposta da API de Questoes: { sessao_id, exercicios:[...] } */
function normalizeExercicios(raw: any, tipo: 'ENEM' | 'ENADE'): Questao[] {
  const sessao_id: string | undefined = raw?.sessao_id ?? raw?.id;
  const items = normalizeList<any>(raw);
  return items.map((q: any) => normalizeQuestao(q, tipo, sessao_id));
}

function normalizeSimulado(raw: any, tipo: 'ENEM' | 'ENADE'): Simulado {
  const rawQuestoes = raw?.questoes ?? raw?.questions ?? [];
  const questoes = normalizeList<any>(rawQuestoes).map((q: any) => normalizeQuestao(q, tipo));
  return {
    id:              raw.id ?? raw.simulado_id ?? String(Date.now()),
    titulo:          raw.titulo ?? raw.title ?? raw.nome ?? (tipo + ' — Simulado IA'),
    descricao:       raw.descricao ?? raw.description ?? 'Gerado por IA com base em provas oficiais',
    tipo,
    questoes,
    duracao_minutos: raw.duracao_minutos ?? raw.tempo ?? Math.max(questoes.length * 3, 10),
    total_questoes:  raw.total_questoes  ?? questoes.length,
    imagem:          raw.imagem,
  };
}

// ── BUILDER: META → SIMULADO ──────────────────────────────────────────────────

/**
 * Constroi um Simulado parcial a partir dos metadados de GET /disponiveis.
 * As questoes ficam vazias — serao carregadas via buscarPorId quando o
 * usuario clicar no card.
 */
function buildSimuladoFromMeta(meta: any, tipo: 'ENEM' | 'ENADE'): Simulado {
  const ano        = meta.ano ?? '';
  const materiaR   = String(meta.materia ?? meta.area ?? 'geral').replace(/_/g, ' ');
  const materiaCap = materiaR.charAt(0).toUpperCase() + materiaR.slice(1);
  const totalQ     = meta.total_questoes ?? 0;

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

// ── ATUALIZACAO EM BACKGROUND ─────────────────────────────────────────────────

/**
 * DESLIGADO na v7. Esta funcao salvava os simulados do /disponiveis no Firestore,
 * mas eles vinham VAZIOS (so metadados, questoes: []). Isso poluia o banco com
 * "simulados fantasmas" que apareciam na lista mas nao tinham questoes.
 *
 * Mantida aqui (sem ser chamada) caso queira reativar com filtro no futuro.
 */
async function atualizarCacheEmBackground(_tipo: 'ENEM' | 'ENADE'): Promise<void> {
  // No-op: nao faz nada. Veja comentario acima.
  return;
}

// ── FIRESTORE HELPERS ─────────────────────────────────────────────────────────

function docToObj<T>(d: any): T {
  return { id: d.id, ...d.data() } as T;
}

async function syncToFirestore(col: 'simulados' | 'questoes', items: any[]): Promise<void> {
  const c = collection(db, col);
  await Promise.allSettled(
    items.map(i =>
      setDoc(doc(c, String(i.id)), { ...i, _sync: new Date().toISOString() }, { merge: true })
    )
  );
}

// ── FIRESTORE QUERY BUILDERS ──────────────────────────────────────────────────

async function fsQuestoes(tipo?: string, materia?: string, lim = 20): Promise<Questao[]> {
  const col = collection(db, 'questoes');
  let q: any;
  if (tipo && materia) q = query(col, where('tipo', '==', tipo), where('materia', '==', materia), fsLimit(lim));
  else if (tipo)       q = query(col, where('tipo', '==', tipo), fsLimit(lim));
  else if (materia)    q = query(col, where('materia', '==', materia), fsLimit(lim));
  else                 q = query(col, fsLimit(lim));
  const snap = await getDocs(q);
  // Normalizar ao ler — alternativas podem estar como objeto {A:"..."} no Firestore
  return snap.docs.map(d => {
    const raw = docToObj<any>(d);
    return normalizeQuestao(raw, raw.tipo);
  });
}

// ── CLASSIFICACAO DE DISCIPLINAS (livro → ENEM ou ENADE) ──────────────────────
// Materias do ensino medio caem no ENEM; areas tecnicas/superiores no ENADE.
// Usado para simulados gerados de livros (fonte: inspirado_em_livro), que vem
// com disciplina mas sem o campo tipo.

// Palavras-chave que indicam ENEM (ensino medio)
const DISCIPLINAS_ENEM = [
  'matematica', 'matemática',
  'portugues', 'português', 'lingua portuguesa', 'língua portuguesa',
  'literatura', 'redacao', 'redação', 'linguagens',
  'historia', 'história',
  'geografia',
  'fisica', 'física',
  'quimica', 'química',
  'biologia',
  'filosofia',
  'sociologia',
  'ingles', 'inglês', 'espanhol',
  'artes', 'educacao fisica', 'educação física',
  'ciencias da natureza', 'ciências da natureza',
  'ciencias humanas', 'ciências humanas',
  'atualidades', 'ensino medio', 'ensino médio', 'enem',
];

// Palavras-chave que indicam ENADE (tecnico/superior)
const DISCIPLINAS_ENADE = [
  'redes', 'rede de computadores', 'redes de computadores',
  'programacao', 'programação',
  'banco de dados', 'database',
  'engenharia',
  'computacao', 'computação', 'ciencia da computacao', 'ciência da computação',
  'sistemas', 'sistemas de informacao', 'sistemas de informação',
  'analise e desenvolvimento', 'análise e desenvolvimento', 'ads',
  'direito', 'juridico', 'jurídico',
  'administracao', 'administração',
  'contabilidade', 'economia',
  'medicina', 'enfermagem', 'odontologia', 'farmacia', 'farmácia',
  'psicologia', 'pedagogia',
  'arquitetura', 'urbanismo',
  'gestao', 'gestão', 'tecnologia da informacao', 'tecnologia da informação',
  'seguranca da informacao', 'segurança da informação',
  'desenvolvimento de software', 'engenharia de software',
  'estrutura de dados', 'algoritmos',
  'enade', 'tecnologo', 'tecnólogo', 'bacharelado', 'licenciatura',
];

/**
 * Classifica uma disciplina/titulo como ENEM ou ENADE.
 * Busca palavras-chave no texto (disciplina + titulo do livro).
 * Default: ENADE (a maioria dos livros tecnicos cai aqui).
 */
function classificarTipoPorDisciplina(texto: string): 'ENEM' | 'ENADE' {
  const t = (texto ?? '').toLowerCase();

  // Primeiro checa ENADE (mais especifico), depois ENEM
  for (const kw of DISCIPLINAS_ENADE) {
    if (t.includes(kw)) return 'ENADE';
  }
  for (const kw of DISCIPLINAS_ENEM) {
    if (t.includes(kw)) return 'ENEM';
  }

  return 'ENADE'; // default: livros tecnicos sao mais comuns
}

async function fsSimulados(tipo?: string): Promise<Simulado[]> {
  const col  = collection(db, 'simulados');
  // Busca TODOS (sem filtrar por tipo no servidor), porque simulados de livro
  // tem concurso:"livro" e nao tem campo tipo:"ENADE". Filtramos no cliente.
  const q    = query(col, fsLimit(100));
  const snap = await getDocs(q);

  const todos = snap.docs.map(d => {
    const raw = docToObj<any>(d);
    // Determina o tipo do simulado, considerando varias fontes:
    // 1. campo "tipo" explicito (ENEM/ENADE)
    // 2. meta.concurso (enem/enade)
    // 3. fonte "inspirado_em_livro" → classifica pela DISCIPLINA (medio=ENEM, tecnico=ENADE)
    let t: 'ENEM' | 'ENADE';
    const fonte = raw.fonte ?? raw.meta?.fonte;
    const concursoMeta = (raw.meta?.concurso ?? '').toLowerCase();

    if (raw.tipo === 'ENADE' || raw.tipo === 'ENEM') {
      t = raw.tipo;
    } else if (concursoMeta === 'enade') {
      t = 'ENADE';
    } else if (concursoMeta === 'enem') {
      t = 'ENEM';
    } else if (fonte === 'inspirado_em_livro') {
      // Simulado de livro: classifica pela disciplina + titulo
      const disciplina = raw.meta?.disciplina ?? raw.disciplina ?? '';
      const livroTitulo = raw.meta?.livro_titulo ?? raw.livro_titulo ?? '';
      t = classificarTipoPorDisciplina(`${disciplina} ${livroTitulo}`);
    } else {
      t = 'ENEM'; // fallback
    }

    // Grava o tipo normalizado de volta no objeto (pro resto do app usar)
    raw.tipo = t;

    // Simulados de livro nao tem "titulo" — gera um a partir da disciplina
    if (!raw.titulo && fonte === 'inspirado_em_livro') {
      const disc = raw.meta?.disciplina ?? raw.disciplina ?? 'Geral';
      const nQ = Array.isArray(raw.questoes) ? raw.questoes.length : (raw.total_questoes ?? 0);
      raw.titulo = `${disc} — ${nQ} questões`;
      raw.descricao = raw.descricao ?? `Gerado de: ${raw.meta?.livro_titulo ?? 'livro'}`;
    }

    // Normalizar questoes embarcadas
    if (Array.isArray(raw.questoes)) {
      raw.questoes = raw.questoes.map((q: any) => normalizeQuestao(q, t));
    }
    return raw as Simulado;
  });

  // Filtra por tipo solicitado (agora no cliente, ja com livros classificados)
  const doTipo = tipo ? todos.filter((s: Simulado) => s.tipo === tipo) : todos;

  // FILTRO v7: so mantem simulados que TEM questoes de verdade.
  const comQuestoes = doTipo.filter((s: Simulado) =>
    (Array.isArray(s.questoes) && s.questoes.length > 0) ||
    (s.total_questoes ?? 0) > 0
  );

  console.log(`[fsSimulados] ${tipo ?? 'todos'}: ${todos.length} total, ${doTipo.length} do tipo, ${comQuestoes.length} com questoes`);
  return comQuestoes.slice(0, 20);
}

// ── DEFAULTS ─────────────────────────────────────────────────────────────────
// ENEM 2024/2023/2022 PDFs indisponiveis — humanas: factual, sem LaTeX, JSON limpo no Gemini
const ENEM_DEFAULT  = { ano: 2022, area: 'humanas' } as const;
// ENADE 2022: direito confirmado no Firebase cache (/admin/cache)
const ENADE_DEFAULT = { ano: 2022, area: 'direito'    } as const;

function buildInspirParams(tipo: 'ENEM' | 'ENADE', materia?: string, quantidade = 5): URLSearchParams {
  const def = tipo === 'ENADE' ? ENADE_DEFAULT : ENEM_DEFAULT;
  return new URLSearchParams({
    ano:        String(def.ano),
    area:       materia ?? def.area,
    quantidade: String(quantidade),
  });
}

// Topico padrao por materia (usado quando nenhum topico e especificado)
// A API de Questoes aceita: portugues, matematica, atualidades, filosofia, sociologia
// A API de Simulados/Inspirar usa areas ENEM: linguagens, matematica, humanas, natureza
const DEFAULT_TOPICOS: Record<string, string> = {
  portugues:         'interpretação_e_compreensão_de_textos', // topico real confirmado em /topicos/portugues
  matematica:        'geometria',
  atualidades:       'politica_e_economia',
  filosofia:         'etica',
  sociologia:        'cidadania',
  linguagens:        'interpretacao_de_texto', // alias (validado apenas no inspirar)
  humanas:           'historia_do_brasil',
  natureza:          'quimica',
  direito:           'direito_constitucional',
  administracao:     'gestao_organizacional',
  pedagogia:         'didatica',
  medicina:          'anatomia',
  enfermagem:        'semiologia',
  engenharia_civil:  'estruturas',
  psicologia:        'psicologia_clinica',
  biologia:          'genetica',
  fisica:            'mecanica',
  quimica:           'quimica_organica',
};

// Mapeamento materia (API de Questoes) → area (API de Simulados/Inspirar)
const MATERIA_TO_ENEM_AREA: Record<string, string> = {
  portugues:    'linguagens',
  matematica:   'matematica',
  atualidades:  'humanas',
  filosofia:    'humanas',
  sociologia:   'humanas',
  biologia:     'natureza',
  fisica:       'natureza',
  quimica:      'natureza',
  historia:     'humanas',
  geografia:    'humanas',
};

function defaultTopico(materia: string): string {
  return DEFAULT_TOPICOS[materia.toLowerCase().replace(/\s+/g, '_')] ?? 'conceitos_gerais';
}

// ── QUESTOES API ──────────────────────────────────────────────────────────────

export const questoesApi = {

  /**
   * v11: Busca questoes da colecao 'questoes' do Firestore (que TEM gabarito
   * e explicacao). NAO gera questoes novas (nao chama /inspirar).
   * A colecao 'questoes' nao tem campo 'tipo', usa 'concurso' e materias em
   * minusculo (direito, humanas, matematica...). Classificamos no cliente.
   * Ideal pra tela de "Questoes avulsas".
   */
  listarDoBanco: async (params?: {
    materia?: string;
    tipo?:    'ENEM' | 'ENADE';
    limit?:   number;
    uid?:     string;
  }): Promise<Questao[]> => {
    const lim     = params?.limit ?? 10;
    const tipo    = params?.tipo;
    const materia = params?.materia?.toLowerCase();
    console.log(`[questoesApi.listarDoBanco v11] === ${tipo ?? 'todos'} | materia: ${materia ?? 'qualquer'} ===`);

    try {
      // Busca da colecao 'questoes' (tem gabarito). Pega bastante (200) e
      // filtra no cliente, porque a colecao nao tem campo 'tipo' confiavel.
      const col  = collection(db, 'questoes');
      const q    = query(col, fsLimit(300));
      const snap = await getDocs(q);

      let todas: Questao[] = snap.docs
        .map(d => ({ id: d.id, raw: docToObj<any>(d) }))
        // Filtra questoes com visual quebrado (grafico/imagem que nao aparece)
        // e questoes desativadas (ativo: false)
        .filter(({ raw }) => raw.tem_visual_quebrado !== true && raw.ativo !== false)
        .map(({ raw }) => {
          // A questao pode ter 'concurso' (enem/enade) em vez de 'tipo'
          const concursoRaw = (raw.concurso ?? raw.tipo ?? '').toString().toUpperCase();
          const tipoQ: 'ENEM' | 'ENADE' =
            concursoRaw.includes('ENADE') ? 'ENADE'
            : concursoRaw.includes('ENEM') ? 'ENEM'
            : concursoRaw.includes('LIVRO') ? classificarTipoPorDisciplina(raw.materia ?? '')
            : classificarTipoPorDisciplina(raw.materia ?? ''); // fallback pela materia
          const norm = normalizeQuestao(raw, tipoQ);
          norm.tipo = tipoQ;
          return norm;
        });
      console.log(`[listarDoBanco] ${todas.length} questoes validas (sem visual quebrado)`);

      // Filtra por tipo (ENEM/ENADE) no cliente
      if (tipo) {
        const doTipo = todas.filter(qq => qq.tipo === tipo);
        console.log(`[listarDoBanco] ${doTipo.length} do tipo ${tipo}`);
        todas = doTipo;
      }

      // Filtra por materia se especificada
      if (materia && materia !== 'todas' && materia !== 'geral') {
        // Mapa de AREA (botao do app) -> materias especificas do banco
        // (apos reclassificacao, o banco tem materias granulares)
        const AREA_MATERIAS: Record<string, string[]> = {
          'humanas':    ['sociologia', 'historia', 'história', 'geografia', 'filosofia', 'humanas'],
          'natureza':   ['biologia', 'fisica', 'física', 'quimica', 'química', 'natureza'],
          'linguagens': ['linguagens', 'portugues', 'português', 'literatura', 'ingles', 'inglês', 'espanhol'],
          'matematica': ['matematica', 'matemática'],
          'matemática': ['matematica', 'matemática'],
          'atualidades':['atualidades'],
        };

        const materiaLow = materia.toLowerCase();
        const alvos = AREA_MATERIAS[materiaLow];

        const filtradas = todas.filter(qq => {
          const m = (qq.materia ?? '').toLowerCase();
          // Se for uma area conhecida, checa se a materia esta na lista de alvos
          if (alvos) {
            return alvos.some(alvo => m === alvo || m.includes(alvo) || alvo.includes(m));
          }
          // Senao, comportamento antigo (match direto)
          return m.includes(materiaLow) || materiaLow.includes(m);
        });

        if (filtradas.length > 0) {
          todas = filtradas;
          console.log(`[listarDoBanco] ${filtradas.length} apos filtro de materia '${materia}'`);
        } else {
          console.log(`[listarDoBanco] filtro de materia '${materia}' nao achou nada, mantendo todas do tipo`);
        }
      }

      // Embaralha + prioriza nao-feitas (se uid dado)
      const feitas = params?.uid ? await questoesFeitasApi.listar(params.uid) : new Set<string>();
      const ordenadas = ordenarQuestoes(todas, feitas);

      console.log(`[listarDoBanco] retornando ${Math.min(ordenadas.length, lim)} questoes`);
      return ordenadas.slice(0, lim);
    } catch (e) {
      console.warn('[questoesApi.listarDoBanco]:', e);
      return [];
    }
  },

  listar: async (params?: {
    materia?: string;
    topico?:  string;
    tipo?:    'ENEM' | 'ENADE';
    page?:    number;
    limit?:   number;
  }): Promise<Questao[]> => {
    const lim    = params?.limit ?? 5;
    const tipo   = params?.tipo ?? 'ENEM';
    const mat    = (params?.materia ?? (tipo === 'ENADE' ? 'direito' : 'portugues')).toLowerCase().replace(/\s+/g, '_');
    const topico = (params?.topico  ?? defaultTopico(mat)).toLowerCase().replace(/\s+/g, '_');

    console.log(`[questoesApi.listar] === ${tipo} | ${mat} / ${topico} ===`);

    // 1. PRIMEIRO: Firestore (rapido, sem cold start)
    try {
      const docs = await fsQuestoes(tipo, params?.materia, lim);
      console.log(`[questoesApi.listar] Firestore tem ${docs.length} questoes`);
      if (docs.length > 0) return docs;
    } catch (e) { console.warn('[questoesApi.listar] Firestore:', e); }

    // 2. GET /exercicios/{materia}/{topico} — banco sem custo Gemini
    //    Backend so tem materias ENEM. Pula direto pro proximo passo se ENADE.
    if (tipo !== 'ENADE') {
      try {
        console.log('[questoesApi.listar] GET /exercicios/' + mat + '/' + topico);
        const raw  = await questoesFetch<any>(`/exercicios/${encodeURIComponent(mat)}/${encodeURIComponent(topico)}`, undefined, 60000);
        const list = normalizeExercicios(raw, tipo);
        if (list.length > 0) {
          syncToFirestore('questoes', list).catch(() => {});
          return list;
        }
      } catch (e) { console.warn('[questoesApi.listar] GET /exercicios:', e); }

      // 3. POST /exercicios/gerar — gera com Gemini + reforco de livros/provas
      try {
        const genQtd = Math.min(lim, 5);
        const qs = new URLSearchParams({ materia: mat, topico, quantidade: String(genQtd), incluir_gabarito: 'true' });
        console.log('[questoesApi.listar] POST /exercicios/gerar?' + qs.toString());
        const raw  = await questoesFetch<any>(`/exercicios/gerar?${qs}`, { method: 'POST' }, 120000);
        const list = normalizeExercicios(raw, tipo);
        if (list.length > 0) {
          syncToFirestore('questoes', list).catch(() => {});
          return list;
        }
      } catch (e) { console.warn('[questoesApi.listar] POST /exercicios/gerar:', e); }
    }

    // 4. POST /{tipo}/inspirar — gera com Gemini (funciona pra ENEM e ENADE)
    try {
      const concurso     = tipo.toLowerCase();
      const inspirarArea = tipo === 'ENADE' ? ENADE_DEFAULT.area : ENEM_DEFAULT.area;
      const qs = buildInspirParams(tipo, inspirarArea, Math.min(lim, 5));
      console.log('[questoesApi.listar] POST /' + concurso + '/inspirar?' + qs.toString());
      const raw  = await restFetch<any>(`/${concurso}/inspirar?${qs}`, { method: 'POST' }, 120000);
      const list = normalizeList<any>(raw?.questoes ?? raw?.questions ?? raw)
                     .map((q: any) => normalizeQuestao(q, tipo));
      if (list.length > 0) {
        syncToFirestore('questoes', list).catch(() => {});
        return list;
      }
    } catch (e) { console.warn('[questoesApi.listar] /inspirar:', e); }

    console.warn(`[questoesApi.listar] === Cascata esgotada, vai cair em MOCK ===`);
    return [];
  },

  /** Busca questao individual — Firestore primeiro, sem fallback REST */
  buscarPorId: async (id: string | number): Promise<Questao | null> => {
    try {
      const s = await getDoc(doc(db, 'questoes', String(id)));
      if (s.exists()) {
        const raw = docToObj<any>(s);
        return normalizeQuestao(raw, raw.tipo);
      }
    } catch {}
    return null;
  },
};

// ── SIMULADOS API ─────────────────────────────────────────────────────────────

export const simuladosApi = {

  listar: async (tipo?: 'ENEM' | 'ENADE'): Promise<Simulado[]> => {
    const t = tipo ?? 'ENEM';
    console.log(`[simuladosApi.listar] === Iniciando cascata para ${t} ===`);

    // 1. PRIMEIRO: Firestore (rapido, sem cold start)
    //    Render free demora 30-50s na primeira request. Firestore responde em ms.
    //    fsSimulados ja filtra os vazios (v7).
    try {
      const docs = await fsSimulados(tipo);
      console.log(`[simuladosApi.listar] Firestore tem ${docs.length} simulados com questoes`);
      if (docs.length > 0) {
        // v7: NAO chama mais atualizarCacheEmBackground (ele poluia o banco com vazios)
        return docs;
      }
    } catch (e) { console.warn('[simuladosApi.listar] Firestore:', e); }

    // 2. GET /disponiveis (so se Firestore vazio)
    //    v7: NAO salva mais no Firestore (esses vem vazios e poluiam o banco).
    //    Mostra na sessao atual mas nao persiste.
    try {
      const concurso = t.toLowerCase();
      const qs = new URLSearchParams({ concurso, limite: '50' });
      console.log('[simuladosApi.listar] GET /disponiveis?' + qs.toString());
      const raw = await restFetch<any>(`/disponiveis?${qs}`, undefined, 60000);
      const lista = Array.isArray(raw?.simulados) ? raw.simulados : [];
      console.log(`[simuladosApi.listar] /disponiveis retornou ${lista.length} simulados`);
      if (lista.length > 0) {
        const sims = lista.map((s: any) => buildSimuladoFromMeta(s, t));
        // v7: removido syncToFirestore — nao persiste metadados vazios
        return sims;
      }
    } catch (e) { console.warn('[simuladosApi.listar] /disponiveis falhou:', e); }

    // 3. POST /simulado?fonte=banco — 1 simulado de 5 questoes
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
      console.log('[simuladosApi.listar] POST /simulado?' + qs.toString());
      const raw = await restFetch<any>(`/simulado?${qs}`, { method: 'POST' }, 60000);
      if (raw?.id || raw?.questoes || raw?.questions) {
        const sim = normalizeSimulado(raw, t);
        if (sim.questoes.length > 0) {
          syncToFirestore('simulados', [sim]).catch(() => {});
          return [sim];
        }
      }
    } catch (e) { console.warn('[simuladosApi.listar] /simulado:', e); }

    // 4. Ultimo recurso — POST /{tipo}/inspirar (gasta cota Gemini)
    try {
      const concurso = t.toLowerCase();
      const qs       = buildInspirParams(t, undefined, 5);
      console.log('[simuladosApi.listar] POST /' + concurso + '/inspirar?' + qs.toString());
      const raw = await restFetch<any>(`/${concurso}/inspirar?${qs}`, { method: 'POST' }, 150000);
      if (raw) {
        const sim = normalizeSimulado(raw, t);
        if (sim.questoes.length > 0) {
          syncToFirestore('simulados', [sim]).catch(() => {});
          return [sim];
        }
      }
    } catch (e) { console.warn('[simuladosApi.listar] /inspirar:', e); }

    console.warn(`[simuladosApi.listar] === Cascata esgotada, vai cair em MOCK ===`);
    return [];
  },

  /**
   * Monta simulado grande juntando varios simulados existentes do banco.
   * ZERO custo Gemini — usa apenas questoes ja salvas.
   *
   * Usado para criar simulados de 20-50 questoes sem gastar quota.
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

  buscarPorId: async (id: string | number, uid?: string): Promise<Simulado | null> => {
    console.log(`[simuladosApi.buscarPorId] === Buscando simulado ${id} ===`);

    // Carrega questoes ja feitas pelo usuario (pra priorizar novas)
    const feitas = uid ? await questoesFeitasApi.listar(uid) : new Set<string>();

    // 1. Firestore — SO retorna se tiver questoes embarcadas (prioridade!)
    let metaFirestore: Simulado | null = null;
    try {
      const s = await getDoc(doc(db, 'simulados', String(id)));
      if (s.exists()) {
        const raw = { id: s.id, ...s.data() } as any;
        const t: 'ENEM' | 'ENADE' = raw.tipo === 'ENADE' ? 'ENADE' : 'ENEM';
        if (Array.isArray(raw.questoes) && raw.questoes.length > 0) {
          raw.questoes = ordenarQuestoes(
            raw.questoes.map((q: any) => normalizeQuestao(q, t)),
            feitas,
          );
          console.log(`[simuladosApi.buscarPorId] Firestore: ${raw.questoes.length} questoes embarcadas (prioridade)`);
          return raw as Simulado;
        }
        metaFirestore = raw as Simulado;
        console.log('[simuladosApi.buscarPorId] Firestore tem metadados mas 0 questoes');
      }
    } catch (e) { console.warn('[simuladosApi.buscarPorId] Firestore:', e); }

    // Descobre tipo, materia e ano (pra filtrar /montar corretamente)
    const tipo: 'ENEM' | 'ENADE' =
      (metaFirestore?.tipo) ?? (String(id).includes('enade') ? 'ENADE' : 'ENEM');
    // Extrai materia do titulo: "ENEM 2022 — Humanas" → "humanas"
    const materiaSim = metaFirestore?.titulo?.split('—')?.[1]?.trim()?.toLowerCase();
    // Extrai ano do titulo: "ENEM 2022 — ..." → 2022
    const anoMatch = metaFirestore?.titulo?.match(/\b(20\d{2})\b/);
    const anoSim = anoMatch ? Number(anoMatch[1]) : undefined;

    // 2. REST — GET /simulado/{id} (pode ter questoes salvas no backend)
    try {
      console.log('[simuladosApi.buscarPorId] GET /simulado/' + id);
      const raw  = await restFetch<any>(`/simulado/${id}`, undefined, 60000);
      const tipoRest: 'ENEM' | 'ENADE' = raw?.concurso === 'enade' ? 'ENADE' : 'ENEM';
      const sim = normalizeSimulado(raw, tipoRest);
      if (sim.questoes.length > 0) {
        sim.questoes = ordenarQuestoes(sim.questoes, feitas);
        console.log(`[simuladosApi.buscarPorId] REST retornou ${sim.questoes.length} questoes`);
        syncToFirestore('simulados', [sim]).catch(() => {});
        return sim;
      }
      console.log('[simuladosApi.buscarPorId] REST retornou 0 questoes (backend nao gerou ainda)');
    } catch (e) { console.warn('[simuladosApi.buscarPorId] REST /simulado:', e); }

    // 3. Fallback: POST /montar COM materia+ano (traz questoes reais do banco)
    //    Pede 20 (bom pra simulado de teste) e USA TUDO que o banco tiver.
    try {
      const concurso = tipo.toLowerCase();
      const QTD_ALVO = 20; // tamanho desejado do simulado
      const qs = new URLSearchParams({ concurso, quantidade: String(QTD_ALVO) });
      if (materiaSim && materiaSim !== 'geral') qs.append('materia', materiaSim);
      if (anoSim) qs.append('ano', String(anoSim));

      console.log('[simuladosApi.buscarPorId] POST /montar?' + qs.toString());
      const raw = await restFetch<any>(`/montar?${qs}`, { method: 'POST' }, 60000);
      if (raw?.questoes?.length > 0) {
        const sim = normalizeSimulado(raw, tipo);
        // Ordena (novas primeiro) e USA TODAS — nao corta mais no total_questoes
        // (antes cortava em 0 quando o metadado tinha total_questoes=0)
        sim.questoes = ordenarQuestoes(sim.questoes, feitas);
        sim.id     = metaFirestore?.id ?? sim.id;
        sim.titulo = metaFirestore?.titulo ?? sim.titulo;
        // Atualiza o total pra refletir o que realmente veio
        sim.total_questoes = sim.questoes.length;
        console.log(`[simuladosApi.buscarPorId] /montar retornou ${raw.questoes.length}, usando TODAS as ${sim.questoes.length}`);
        return sim;
      }
    } catch (e) { console.warn('[simuladosApi.buscarPorId] /montar:', e); }

    // 4. Ultimo recurso: retorna metadados (UI mostra "sem questoes" melhor que MOCK)
    if (metaFirestore) {
      console.warn('[simuladosApi.buscarPorId] Retornando metadados sem questoes');
      return metaFirestore;
    }

    console.warn('[simuladosApi.buscarPorId] === Nada encontrado ===');
    return null;
  },

  enviarResultado: async (resultado: Omit<ResultadoSimulado, 'data'>): Promise<void> => {
    const payload = { ...resultado, data: new Date().toISOString() };

    // Salva sempre no Firestore
    try {
      await addDoc(collection(db, 'resultados'), { ...payload, criadoEm: serverTimestamp() });
    } catch (e) { console.warn('[simuladosApi.enviarResultado] Firestore:', e); }

    // POST /simulado/{id}/resultado
    try {
      await restFetch<void>(`/simulado/${resultado.simulado_id}/resultado`, {
        method:  'POST',
        body:    JSON.stringify({ respostas: resultado.respostas }),
        headers: { 'X-Dev-User-Id': resultado.usuario_uid },
      });
    } catch (e) { console.warn('[simuladosApi.enviarResultado] REST:', e); }
  },
};

// ── QUESTOES FEITAS (memoria anti-repeticao) ──────────────────────────────────
// Guarda no Firestore quais questoes cada usuario ja respondeu.
// Estrutura: colecao 'questoes_feitas', documento = uid, campo ids = array de questaoId.

export const questoesFeitasApi = {
  /**
   * Retorna o Set de IDs de questoes que o usuario ja respondeu.
   * Set facilita checagem rapida com .has().
   */
  listar: async (uid: string): Promise<Set<string>> => {
    if (!uid || uid === 'anonimo') return new Set();
    try {
      const snap = await getDoc(doc(db, 'questoes_feitas', uid));
      if (snap.exists()) {
        const ids = snap.data()?.ids ?? [];
        return new Set(Array.isArray(ids) ? ids.map(String) : []);
      }
    } catch (e) { console.warn('[questoesFeitasApi.listar]:', e); }
    return new Set();
  },

  /**
   * Marca varias questoes como feitas (merge — nao apaga as antigas).
   * Usa arrayUnion pra evitar duplicatas automaticamente.
   */
  marcar: async (uid: string, questaoIds: string[]): Promise<void> => {
    if (!uid || uid === 'anonimo' || questaoIds.length === 0) return;
    try {
      const ref = doc(db, 'questoes_feitas', uid);
      // arrayUnion adiciona sem duplicar; cada ID vira argumento
      await setDoc(
        ref,
        { ids: arrayUnion(...questaoIds.map(String)), atualizadoEm: serverTimestamp() },
        { merge: true },
      );
      console.log(`[questoesFeitasApi.marcar] ${questaoIds.length} questoes marcadas para ${uid}`);
    } catch (e) { console.warn('[questoesFeitasApi.marcar]:', e); }
  },
};

// ── HELPER: embaralhar + priorizar questoes novas ─────────────────────────────

/**
 * Embaralha questoes (Fisher-Yates) e coloca as JA FEITAS no fim da fila.
 * Assim o usuario ve questoes novas primeiro, mas ainda pode revisar antigas.
 */
function ordenarQuestoes(questoes: Questao[], feitas: Set<string>): Questao[] {
  // Fisher-Yates shuffle
  const arr = [...questoes];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  // Particiona: novas primeiro, feitas depois (cada grupo ja embaralhado)
  const novas:    Questao[] = [];
  const repetidas: Questao[] = [];
  for (const q of arr) {
    if (feitas.has(String(q.id))) repetidas.push(q);
    else                          novas.push(q);
  }
  return [...novas, ...repetidas];
}

// ── PING ──────────────────────────────────────────────────────────────────────

export const pingApi = async (): Promise<boolean> => {
  try { await restFetch<any>('/', undefined, 40000); return true; } catch { return false; }
};


// ── MOCK DATA ─────────────────────────────────────────────────────────────────

export const MOCK_QUESTOES: Questao[] = [
  {
    id: 'mock_q1', materia: 'LINGUAGENS', topico: 'Literatura', tipo: 'ENEM', ano: 2023,
    enunciado: 'Leia o poema de Camoes:\n\n"Amor e fogo que arde sem se ver;\nE ferida que doi e nao se sente;"\n\nA principal figura de linguagem usada para expressar a natureza contraditoria do amor e:',
    alternativas: [
      { id: 'A', texto: 'Metafora - comparacoes implicitas.' },
      { id: 'B', texto: 'Paradoxo - uniao de ideias irreconciliaveis.' },
      { id: 'C', texto: 'Hiperbole - exagero intencional.' },
      { id: 'D', texto: 'Pleonasmo - repeticao de termos.' },
      { id: 'E', texto: 'Eufemismo - suavizacao da dor.' },
    ],
    gabarito: 'B',
  },
  {
    id: 'mock_q2', materia: 'MATEMATICA', topico: 'Geometria', tipo: 'ENEM', ano: 2023,
    enunciado: 'Um cilindro tem raio 2 m e altura 5 m. Qual seu volume? (pi = 3,14)',
    alternativas: [
      { id: 'A', texto: '31,4 m3' },
      { id: 'B', texto: '42,8 m3' },
      { id: 'C', texto: '62,8 m3' },
      { id: 'D', texto: '12,5 m3' },
      { id: 'E', texto: '20,0 m3' },
    ],
    gabarito: 'C',
  },
  {
    id: 'mock_q3', materia: 'CIENCIAS DA NATUREZA', topico: 'Biologia', tipo: 'ENADE', ano: 2023,
    enunciado: 'Qual processo celular converte glicose em ATP na ausencia de oxigenio?',
    alternativas: [
      { id: 'A', texto: 'Respiracao aerobica' },
      { id: 'B', texto: 'Fotossintese' },
      { id: 'C', texto: 'Fermentacao' },
      { id: 'D', texto: 'Ciclo de Krebs' },
      { id: 'E', texto: 'Fosforilacao oxidativa' },
    ],
    gabarito: 'C',
  },
];

export const MOCK_SIMULADOS: Simulado[] = [
  {
    id: 'mock_enem', titulo: 'Simulado Demo ENEM', tipo: 'ENEM',
    descricao: 'Questoes demonstrativas (sem conexao)',
    questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENEM'),
    duracao_minutos: 270, total_questoes: 2,
    imagem: 'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?q=80&w=600',
  },
  {
    id: 'mock_enade', titulo: 'Simulado Demo ENADE', tipo: 'ENADE',
    descricao: 'Questoes demonstrativas (sem conexao)',
    questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENADE'),
    duracao_minutos: 240, total_questoes: 1,
    imagem: 'https://images.unsplash.com/photo-1491841573634-28140fc7ced7?q=80&w=600',
  },
];
