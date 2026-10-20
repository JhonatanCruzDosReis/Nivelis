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
import AsyncStorage from '@react-native-async-storage/async-storage';
import { auth, db } from './firebase';

// ── BASE URLs ─────────────────────────────────────────────────────────────────
// Todos os paths no openapi.json sao relativos ao prefixo do servidor
const API_ROOT       = 'https://nivelis-api-1.onrender.com';
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

// ── AUTENTICAÇÃO NAS CHAMADAS À API ───────────────────────────────────────────
//
// O app mandava `X-Dev-User-Id: <uid>` — um header que a API aceitava como
// prova de identidade quando o modo dev estava ligado, e o modo dev vinha
// ligado por padrão. Na prática qualquer pessoa trocava o uid e lia o
// histórico de outra: `curl -H "X-Dev-User-Id: <uid-alheio>" .../historico`.
//
// Agora vai o token do Firebase, que a API valida contra o Google e que
// ninguém consegue forjar. Fica aqui dentro do apiFetch, e não em cada
// chamada, porque header de autenticação esquecido numa rota é exatamente o
// tipo de falha que não aparece em teste — só em produção, e só para quem
// está logado.
//
// Deslogado continua funcionando: sem token o header não vai, e a API só
// recusa o que exige usuário. Praticar questão não exige.
async function cabecalhoAuth(): Promise<Record<string, string>> {
  const usuario = auth.currentUser;
  if (!usuario) return {};
  try {
    // getIdToken usa o token em cache e só vai à rede perto de expirar
    // (1 hora), então chamar a cada requisição não custa round-trip.
    return { Authorization: `Bearer ${await usuario.getIdToken()}` };
  } catch (e) {
    // Offline ou token irrecuperável: segue sem o header. Melhor uma
    // requisição que talvez seja recusada do que nenhuma requisição.
    console.warn('[auth] não consegui o token do Firebase:', e);
    return {};
  }
}

async function apiFetch<T>(base: string, path: string, opts?: RequestInit, ms = 35000): Promise<T> {
  const ctrl = new AbortController();
  const tid  = setTimeout(() => ctrl.abort(), ms);
  try {
    const auten = await cabecalhoAuth();
    const res = await fetch(base + path, {
      ...opts,
      signal: ctrl.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...auten,
        ...(opts?.headers ?? {}),
      },
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

// As rotas /procedural/* sao registradas na raiz do app FastAPI, e o
// prefixo montado no Render nao e o mesmo das duas bases acima. Em vez de
// chutar, tenta as bases conhecidas na primeira chamada e guarda a que
// respondeu — as seguintes vao direto.
const PROCEDURAL_BASES = [SIMULADOS_BASE, QUESTOES_BASE, API_ROOT];
let proceduralBaseOk: string | null = null;

async function proceduralFetch<T>(path: string, opts?: RequestInit, ms?: number): Promise<T> {
  if (proceduralBaseOk) return apiFetch<T>(proceduralBaseOk, path, opts, ms);
  let ultimoErro: any;
  for (const base of PROCEDURAL_BASES) {
    try {
      const r = await apiFetch<T>(base, path, opts, ms);
      proceduralBaseOk = base;
      console.log('[procedural] base confirmada: ' + base);
      return r;
    } catch (e: any) {
      ultimoErro = e;
      // 400 e 422 são a base CERTA recusando o parâmetro (grupo mandado
      // para a rota de disciplina única, tópico inexistente). Repetir nas
      // outras bases só gasta três requisições lentas e ainda deixa a base
      // sem confirmar, refazendo a sondagem na chamada seguinte.
      const msg = String(e?.message ?? '');
      if (msg.includes('[400]') || msg.includes('[422]')) {
        proceduralBaseOk = base;
        throw e;
      }
    }
  }
  throw ultimoErro;
}

// ── NORMALIZERS ───────────────────────────────────────────────────────────────

function normalizeList<T>(raw: any): T[] {
  if (Array.isArray(raw)) return raw;
  for (const k of ['exercicios', 'questoes', 'items', 'results', 'data', 'simulados', 'content', 'list', 'questions']) {
    if (Array.isArray(raw?.[k])) return raw[k] as T[];
  }
  return [];
}

/** Aceita alternativas como {A:"...",B:"..."} ou [{id:"A",texto:"..."}] */
const LETRAS_ALT = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

function normalizeAlternativas(alts: any): Alternativa[] {
  if (!alts) return [];
  if (Array.isArray(alts)) {
    return alts.map((a: any, i: number) => {
      // Quando a API manda a lista como texto puro — ["uma","duas","três"] —
      // não existe `a.id`, `a.letra` nem `a.key`. Antes isso caía no '?' e
      // TODAS as alternativas ficavam com o MESMO id.
      //
      // Não era só o aviso de chave repetida do React: id é o que compara a
      // alternativa com o gabarito e o que marca a escolhida. Com todos em
      // '?', o gabarito nunca casa e o app não distingue uma da outra —
      // a questão fica impossível de responder certo.
      //
      // Posição vira letra, que é a convenção das provas: 1ª = A, 2ª = B.
      const bruto = (a && typeof a === 'object')
        ? (a.id ?? a.letra ?? a.key ?? a.opcao)
        : undefined;
      const id = bruto !== undefined && bruto !== null && String(bruto).trim() !== ''
        ? String(bruto)
        : (LETRAS_ALT[i] ?? String(i + 1));
      return {
        id,
        texto: String((a && typeof a === 'object')
          ? (a.texto ?? a.text ?? a.enunciado ?? a.descricao ?? '')
          : a),
      };
    });
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
    // Estes dois são o que aparece na tela quando a API não manda título ou
    // descrição. Diziam "Simulado IA" e "Gerado por IA com base em provas
    // oficiais" — e a segunda virou MENTIRA quando as rotas de criação por
    // Gemini saíram da API. Hoje os simulados vêm do banco de questões
    // oficiais e do gerador procedural em Python; nenhum deles é escrito por
    // IA. Dizer ao usuário de onde veio o conteúdo é o tipo de coisa que não
    // pode ficar desatualizada.
    titulo:          raw.titulo ?? raw.title ?? raw.nome ?? (`Simulado ${tipo}`),
    descricao:       raw.descricao ?? raw.description ?? 'Montado a partir do banco de questões',
    tipo,
    questoes,
    duracao_minutos: raw.duracao_minutos ?? raw.tempo ?? Math.max(questoes.length * 3, 10),
    total_questoes:  raw.total_questoes  ?? questoes.length,
    imagem:          raw.imagem,
  };
}

/**
 * Casa `questoes` com `gabarito` de uma resposta /procedural/*.
 *
 * As duas rotas procedurais devolvem listas SEPARADAS, ligadas pelo campo
 * `numero` — a questao nao carrega a resposta dentro dela. O normalize do
 * app espera tudo num objeto so, entao a juncao acontece aqui.
 *
 * Tambem fixa um `id` estavel (`<simulado>:<numero>`). Sem isso o
 * normalizeQuestao cai no `Date.now() + Math.random()`, e a mesma questao
 * ganha id novo a cada carregamento — o que estraga a memoria de questoes
 * ja respondidas.
 *
 * Resposta que nao seja procedural passa intacta.
 */
function mesclarGabarito(raw: any): any {
  const questoes = raw?.questoes ?? raw?.questions;
  if (!Array.isArray(questoes)) return raw;

  const gab = Array.isArray(raw?.gabarito) ? raw.gabarito : [];
  const porNumero = new Map<any, any>(gab.map((g: any) => [g?.numero, g]));

  // /procedural/simulado traz simulado_id; /procedural/gerar NÃO traz id
  // nenhum. Usar 'proc' fixo fazia todo lote gerado sair com os mesmos ids
  // proc:1…proc:N — e aí dois estragos: o syncToFirestore sobrescrevia os
  // mesmos documentos com questões diferentes, e o questoesFeitasApi
  // marcava proc:1… como respondidas, rebaixando TODO lote procedural
  // seguinte. Sem id do servidor, gera um por lote.
  const prefixo = raw?.simulado_id ?? raw?.id
    ?? `proc-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

  return {
    ...raw,
    questoes: questoes.map((q: any, i: number) => {
      const g = porNumero.get(q?.numero) ?? {};
      return {
        ...q,
        id:         q.id ?? `${prefixo}:${q?.numero ?? i}`,
        gabarito:   q.gabarito ?? g.resposta_correta,
        explicacao: q.explicacao ?? g.explicacao,
        materia:    q.materia ?? q.disciplina ?? g.topico,
        topico:     q.topico ?? g.topico,
      };
    }),
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

// ── SIMULADO GERADO FICA NO APARELHO ──────────────────────────────────────────
//
// Antes havia um syncToFirestore que gravava questões e simulados gerados
// direto nas coleções COMPARTILHADAS. Duas razões para sair:
//
//   1. Segurança. Enquanto o cliente escreve em `questoes` e `simulados`, as
//      regras do Firestore precisam permitir essa escrita — e permissão de
//      escrita vale para qualquer um com a apiKey do app, que é pública por
//      construção. Ou seja: qualquer pessoa poderia reescrever enunciados e
//      inverter gabaritos do banco inteiro. Com o sync fora, a regra passa a
//      ser `allow write: if false`, e só a API (Admin SDK, que ignora regras)
//      escreve lá.
//
//   2. Curadoria. O banco voltaria a inchar sozinho com tudo que foi gerado,
//      desfazendo a limpeza que deixou ~15 questões por área.
//
// O simulado gerado continua precisando ser reencontrado quando o usuário
// toca nele na lista — senão o buscarPorId cai no /montar e devolve OUTRAS
// questões. Então ele é guardado aqui, no aparelho: é onde foi gerado e onde
// vai ser aberto, funciona offline, e não entrega escrita a ninguém.
const CHAVE_SIMULADOS = 'nivelis:simulados_gerados';
const TETO_SIMULADOS = 20;

async function guardarSimuladoLocal(sim: Simulado): Promise<void> {
  if (!sim?.id) return;
  try {
    const bruto = await AsyncStorage.getItem(CHAVE_SIMULADOS);
    const atual: Simulado[] = bruto ? JSON.parse(bruto) : [];
    const semEste = Array.isArray(atual)
      ? atual.filter(s => String(s?.id) !== String(sim.id))
      : [];
    // Mais recente na frente; corta a cauda para não encher o armazenamento.
    const novo = [sim, ...semEste].slice(0, TETO_SIMULADOS);
    await AsyncStorage.setItem(CHAVE_SIMULADOS, JSON.stringify(novo));
  } catch (e) { console.warn('[simuladoLocal] gravar:', e); }
}

async function lerSimuladoLocal(id: string | number): Promise<Simulado | null> {
  try {
    const bruto = await AsyncStorage.getItem(CHAVE_SIMULADOS);
    if (!bruto) return null;
    const lista = JSON.parse(bruto);
    if (!Array.isArray(lista)) return null;
    const achado = lista.find((s: any) => String(s?.id) === String(id));
    return achado && Array.isArray(achado.questoes) && achado.questoes.length > 0
      ? achado as Simulado
      : null;
  } catch { return null; }
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
// ENEM 2024/2023/2022 PDFs indisponiveis — humanas e a area com cache confiavel
const ENEM_DEFAULT  = { ano: 2022, area: 'humanas' } as const;
// ENADE 2022: direito confirmado no Firebase cache (/admin/cache)
const ENADE_DEFAULT = { ano: 2022, area: 'direito'    } as const;

// ── PROCEDURAL (geradores em Python) ─────────────────────────────────────────
//
// As rotas /procedural/* montam questao e simulado sem chamar IA: o
// enunciado sai de um sorteio de cenario e a resposta e CALCULADA. Sao o
// ULTIMO degrau das duas cascatas — e tambem o unico gerador que sobrou,
// depois que as rotas com Gemini sairam da API.
//
// Se a rota ainda nao estiver publicada no Render, o fetch levanta e o
// passo cai fora sozinho: cada etapa da cascata ja tem seu try/catch.

/** Materia do app → disciplina (ou grupo) do catalogo procedural. */
const MATERIA_TO_PROCEDURAL: Record<string, string> = {
  matematica:        'matematica,basica',
  portugues:         'portugues',
  linguagens:        'portugues',
  direito:           'direito',
  administracao:     'administracao',
  medicina:          'medicina',          // grupo: as dez do ciclo basico
  enfermagem:        'saude',
  biologia:          'biocelular,genetica',
  engenharia_civil:  'engenharia',
  computacao:        'computacao',        // grupo: ads, redes, engenharia
  ads:               'ads',
  redes:             'redes',
};

/** Disciplinas procedurais por tipo de prova, quando a materia nao diz. */
const PROCEDURAL_DEFAULT: Record<'ENEM' | 'ENADE', string> = {
  ENEM:  'enem',          // grupo: basica + portugues
  ENADE: 'ads',
};

function disciplinasProcedurais(materia?: string, tipo?: 'ENEM' | 'ENADE'): string {
  const m = (materia ?? '').toLowerCase().replace(/\s+/g, '_');
  return MATERIA_TO_PROCEDURAL[m] ?? PROCEDURAL_DEFAULT[tipo ?? 'ENEM'];
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
  linguagens:        'interpretacao_de_texto',
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

// ── LEITURA DO BANCO DE QUESTOES ──────────────────────────────────────────────
//
// Uma leitura, tres consumidores. Separado porque o `listarSessao` precisa do
// MESMO conjunto para duas perguntas — "quais entrego agora" e "quantas feitas
// existem" — e chamar duas vezes custava 800 leituras de documento por sessao
// no Firestore, contra 400. No plano gratuito (50 mil leituras/dia) isso e a
// diferenca entre 60 e 120 sessoes por dia no app inteiro.

/** Teto de documentos lidos por vez. Ver o aviso logo abaixo. */
const TETO_LEITURA = 400;

/** Mapa de AREA (botao do app) -> materias especificas do banco. */
const AREA_MATERIAS: Record<string, string[]> = {
  'humanas':    ['sociologia', 'historia', 'história', 'geografia', 'filosofia', 'humanas'],
  'natureza':   ['biologia', 'fisica', 'física', 'quimica', 'química', 'natureza'],
  'linguagens': ['linguagens', 'portugues', 'português', 'literatura', 'ingles', 'inglês', 'espanhol'],
  'matematica': ['matematica', 'matemática'],
  'matemática': ['matematica', 'matemática'],
  'atualidades':['atualidades'],
};

// ── CACHE DO BANCO NO APARELHO ────────────────────────────────────────────────
//
// O Firestore do SDK web guarda cache só em MEMORIA. Num app recem-aberto sem
// rede o `getDocs` falha, e sem isto o usuario offline caia nas tres questoes
// de demonstracao. Persistencia em disco resolveria, mas o SDK web depende de
// IndexedDB, que o React Native nao tem — e pedido aberto no repositorio deles
// (firebase-js-sdk #7947). Trocar pelo @react-native-firebase seria mudar de
// dependencia. Guardar a leitura aqui custa nada e resolve o caso real.
//
// O teto existe porque o AsyncStorage nao e feito para blobs grandes: no
// Android ha limite por item e um total modesto para o banco inteiro. 150
// questoes dao umas dez sessoes de 15 e casam com o tamanho do banco curado
// (~15 por area). Se o banco crescer muito, o cache fica sendo uma amostra —
// e isso e aceitavel: ele e rede de seguranca, nao fonte primaria.
const CHAVE_CACHE_BANCO = 'nivelis:cache_banco';
const TETO_CACHE = 150;

async function gravarCacheBanco(todas: Questao[]): Promise<void> {
  try {
    await AsyncStorage.setItem(CHAVE_CACHE_BANCO, JSON.stringify({
      em: Date.now(),
      questoes: todas.slice(0, TETO_CACHE),
    }));
  } catch (e) { console.warn('[cacheBanco] gravar:', e); }
}

async function lerCacheBanco(): Promise<{ em: number; questoes: Questao[] } | null> {
  try {
    const bruto = await AsyncStorage.getItem(CHAVE_CACHE_BANCO);
    if (!bruto) return null;
    const d = JSON.parse(bruto);
    if (!Array.isArray(d?.questoes) || d.questoes.length === 0) return null;
    return d;
  } catch { return null; }
}

async function lerBanco(params?: {
  materia?: string;
  tipo?:    'ENEM' | 'ENADE';
  uid?:     string;
}): Promise<{ todas: Questao[]; feitas: Set<string>; doCache: boolean }> {
  const tipo    = params?.tipo;
  const materia = params?.materia?.toLowerCase();

  // Lê do Firestore; sem rede, cai para o que o aparelho guardou.
  let todas: Questao[] = [];
  let doCache = false;
  try {
    const snap = await getDocs(query(collection(db, 'questoes'), fsLimit(TETO_LEITURA)));

    // Uma query sem orderBy sai ordenada por ID de documento — ou seja, sempre
    // os MESMOS primeiros N. Enquanto o banco couber no teto isso nao tem
    // efeito nenhum. Se passar, as questoes do fim ficam invisiveis e a
    // anti-repeticao fica sem material SEM AVISAR. Daí o grito: em silencio
    // esse teto custa horas de diagnostico.
    if (snap.size >= TETO_LEITURA) {
      console.warn(
        `[lerBanco] ⚠ o banco encostou no teto de ${TETO_LEITURA} documentos. `
      + `As questoes alem disso NAO sao alcancaveis — e preciso paginar ou `
      + `filtrar materia no servidor.`);
    }

    todas = snap.docs
      .map(d => ({ id: d.id, raw: docToObj<any>(d) }))
      // Descarta visual quebrado (grafico/imagem que nao aparece) e desativadas
      .filter(({ raw }) => raw.tem_visual_quebrado !== true && raw.ativo !== false)
      .map(({ raw }) => {
        // A questao pode ter 'concurso' (enem/enade) em vez de 'tipo'
        const concursoRaw = (raw.concurso ?? raw.tipo ?? '').toString().toUpperCase();
        const tipoQ: 'ENEM' | 'ENADE' =
          concursoRaw.includes('ENADE') ? 'ENADE'
          : concursoRaw.includes('ENEM') ? 'ENEM'
          : classificarTipoPorDisciplina(raw.materia ?? '');
        const norm = normalizeQuestao(raw, tipoQ);
        norm.tipo = tipoQ;
        return norm;
      });

    // Guarda a lista JA normalizada e ANTES dos filtros, para o cache servir
    // qualquer materia depois — nao so a que foi pedida nesta chamada.
    if (todas.length > 0) await gravarCacheBanco(todas);
  } catch (e) {
    const guardado = await lerCacheBanco();
    if (!guardado) {
      console.warn('[lerBanco] sem rede e sem cache:', e);
      throw e;                       // deixa o chamador decidir o que mostrar
    }
    const dias = Math.floor((Date.now() - guardado.em) / 86_400_000);
    console.log(`[lerBanco] offline — usando cache de ${guardado.questoes.length} `
              + `questoes (${dias} dia(s))`);
    todas = guardado.questoes;
    doCache = true;
  }

  if (tipo) todas = todas.filter(qq => qq.tipo === tipo);

  if (materia && materia !== 'todas' && materia !== 'geral') {
    const alvos = AREA_MATERIAS[materia];
    const filtradas = todas.filter(qq => {
      const m = (qq.materia ?? '').toLowerCase();
      if (alvos) return alvos.some(alvo => m === alvo || m.includes(alvo) || alvo.includes(m));
      return m.includes(materia) || materia.includes(m);
    });
    // Filtro que nao acha nada nao deve zerar a tela: melhor devolver as do
    // tipo do que uma lista vazia por causa de um rotulo divergente.
    if (filtradas.length > 0) todas = filtradas;
    else console.log(`[lerBanco] filtro de materia '${materia}' nao achou nada`);
  }

  const feitas = await questoesFeitasApi.listar(params?.uid ?? '');
  console.log(`[lerBanco] ${todas.length} questoes | ${feitas.size} ja feitas`
            + `${doCache ? ' | DO CACHE' : ''}`);
  return { todas, feitas, doCache };
}

/** Aplica o modo de anti-repeticao a um conjunto ja lido. */
function porModo(todas: Questao[], feitas: Set<string>,
                 modo: 'novas' | 'refazer' | 'todas'): Questao[] {
  const ehFeita = (qq: Questao) => feitas.has(String(qq.id));
  if (modo === 'refazer') return todas.filter(ehFeita);
  if (modo === 'todas')   return todas;
  return todas.filter(qq => !ehFeita(qq));
}

export const questoesApi = {

  /**
   * v11: Busca questoes da colecao 'questoes' do Firestore (que TEM gabarito
   * e explicacao). NAO gera questoes novas.
   * A colecao 'questoes' nao tem campo 'tipo', usa 'concurso' e materias em
   * minusculo (direito, humanas, matematica...). Classificamos no cliente.
   * Ideal pra tela de "Questoes avulsas".
   */
  listarDoBanco: async (params?: {
    materia?: string;
    tipo?:    'ENEM' | 'ENADE';
    limit?:   number;
    uid?:     string;
    /**
     * 'novas'   (padrao) — exclui o que o usuario ja respondeu
     * 'refazer'          — devolve SO o que ele ja respondeu
     * 'todas'            — sem filtro de memoria
     */
    modo?:    'novas' | 'refazer' | 'todas';
  }): Promise<Questao[]> => {
    const lim  = params?.limit ?? 15;
    const modo = params?.modo ?? 'novas';
    try {
      const { todas, feitas } = await lerBanco(params);
      const escolhidas = embaralhar(porModo(todas, feitas, modo)).slice(0, lim);
      console.log(`[listarDoBanco] modo=${modo} | devolvendo ${escolhidas.length}/${lim}`);
      return escolhidas;
    } catch (e) {
      console.warn('[questoesApi.listarDoBanco]:', e);
      return [];
    }
  },

  /**
   * A SESSAO DE PRATICAR, montada inteira.
   *
   * Banco inedito primeiro; se vier menos do que o pedido, o procedural gera
   * a diferenca na hora. Essa e a troca que resolve a repeticao: um banco de
   * 15 questoes por area acaba em UMA sessao, e a partir dai qualquer leitura
   * do banco so teria repetida para oferecer. O gerador nao acaba — saude tem
   * 1862 fatos, administracao 5862.
   *
   * Por que o procedural entra AQUI e nao como degrau da cascata: na cascata
   * ele so rodava quando o Firestore devolvia NADA, e o Firestore sempre
   * devolvia algo — as repetidas. "Banco com repetida" contava como sucesso e
   * o gerador nunca era alcancado.
   *
   * O que o procedural gera NAO e salvo no banco (`salvar: false` na rota) e
   * NAO entra na memoria de feitas. Sao duas decisoes ligadas: o banco fica do
   * tamanho que voce curou, e o id sorteado por lote nunca reaparece para ser
   * vetado. Repeticao de conteudo quem evita e o veto de `_fato` do gerador.
   */
  listarSessao: async (params: {
    materia?: string;
    tipo?:    'ENEM' | 'ENADE';
    limit?:   number;
    uid?:     string;
    modo?:    'novas' | 'refazer';
  }): Promise<{
    questoes:   Questao[];
    doBanco:    number;
    geradas:    number;
    repetidas:  number;   // feitas usadas para nao deixar a tela vazia
    feitas:     number;   // quantas feitas o banco tem (oferta de refazer)
    doCache:    boolean;  // veio do aparelho, nao do Firestore
  }> => {
    const lim  = params.limit ?? 15;
    const modo = params.modo ?? 'novas';

    // UMA leitura serve as duas perguntas: o que entregar agora, e quantas
    // feitas existem para a tela oferecer revisao.
    let todas: Questao[] = [];
    let feitasSet = new Set<string>();
    let doCache = false;
    try {
      const r = await lerBanco(params);
      todas = r.todas; feitasSet = r.feitas; doCache = r.doCache;
    } catch (e) { console.warn('[listarSessao] lerBanco:', e); }

    const feitasNoBanco = todas.filter(qq => feitasSet.has(String(qq.id))).length;
    const doBanco = embaralhar(porModo(todas, feitasSet, modo)).slice(0, lim);

    // Refazer e pedido explicito de rever. Completar com questao nova ali
    // seria desobedecer: devolve so as feitas.
    if (modo === 'refazer') {
      return { questoes: doBanco, doBanco: doBanco.length, geradas: 0,
               repetidas: 0, feitas: feitasNoBanco, doCache };
    }

    const falta = lim - doBanco.length;
    let geradas: Questao[] = [];
    // O que o veto tirou do gerador. Guardado porque, se sobrar zero questão
    // no fim, é melhor devolver estas AVISANDO do que entregar tela vazia.
    const vetadas: Questao[] = [];
    if (falta > 0) {
      const alvo = disciplinasProcedurais(params.materia, params.tipo).split(',')[0];
      console.log(`[listarSessao] banco deu ${doBanco.length}/${lim}; gerando ${falta} de '${alvo}'`);
      try {
        geradas = await proceduralApi.questoes(alvo, falta, params.tipo ?? 'ENEM');

        // ── o gerador também passa pelo veto ──
        //
        // Antes o resultado do banco era filtrado e o do gerador entrava
        // direto. Normalmente não dá problema: o gerador devolve ids `proc-`
        // frescos, e `marcar` nem guarda esses ids. Mas "normalmente" é uma
        // suposição sobre um serviço do outro lado da rede, e esta função
        // existe justamente para que questão repetida não apareça sozinha.
        //
        // Se o gerador devolver algo que o usuário já fez — por mudança lá,
        // por cache, por id reaproveitado — o veto agora pega. Quando ele se
        // comporta, isto não descarta nada e não custa nada.
        //
        // Também tira duplicata entre gerador e banco: os dois podem servir
        // a mesma questão, e vê-la duas vezes na MESMA lista é pior ainda.
        const jaNaLista = new Set(doBanco.map(q => String(q.id)));
        const antes = geradas.length;
        geradas = geradas.filter(q => {
          const id = String(q.id);
          if (jaNaLista.has(id)) { vetadas.push(q); return false; }
          if (modo === 'novas' && feitasSet.has(id)) { vetadas.push(q); return false; }
          jaNaLista.add(id);
          return true;
        });
        if (geradas.length !== antes) {
          console.log(`[listarSessao] veto cortou ${antes - geradas.length} `
                    + `das ${antes} geradas (já vistas ou repetidas do banco)`);
        }
      } catch (e) { console.warn('[listarSessao] procedural:', e); }
    }

    // ── Rede de seguranca: nem banco nem gerador tinham o que dar ──
    //
    // Acontece quando a API esta fora (ou o aparelho offline) E o usuario ja
    // fez tudo o que o banco tem daquela materia. Sem isto a tela fica VAZIA,
    // e vazio parece app quebrado — pior do que a repeticao que a gente foi
    // matar. Entao completa com as feitas, mas devolve `repetidas > 0` para a
    // tela DIZER que esta repetindo. Repetida escolhida e o que o usuario
    // pediu; repetida silenciosa e o defeito.
    //
    // So entra quando o resultado seria ZERO. Com 3 ineditas e o gerador fora,
    // melhor 3 frescas do que 3 frescas e 12 repetidas.
    let repetidas: Questao[] = [];
    if (doBanco.length + geradas.length === 0) {
      if (feitasNoBanco > 0) {
        repetidas = embaralhar(porModo(todas, feitasSet, 'refazer')).slice(0, lim);
        console.log(`[listarSessao] nada inedito e sem gerador — `
                  + `completando com ${repetidas.length} ja feitas`);
      } else if (vetadas.length > 0) {
        // O veto do gerador cortou TUDO e o banco não tinha nada para
        // completar. Sem isto a tela ficaria vazia — e vazio parece app
        // quebrado, que é pior do que a repetição que o veto foi matar.
        //
        // Então as vetadas voltam, mas contadas como `repetidas`, que é o
        // que faz a tela dizer "estas você já fez". A regra da casa continua
        // valendo: repetida avisada é aceitável, repetida silenciosa não.
        repetidas = embaralhar(vetadas).slice(0, lim);
        console.log(`[listarSessao] o veto cortou tudo do gerador e o banco `
                  + `nao tinha reserva — devolvendo ${repetidas.length} ja vistas, avisando`);
      }
    }

    return {
      questoes:  [...doBanco, ...geradas, ...repetidas].slice(0, lim),
      doBanco:   doBanco.length,
      geradas:   geradas.length,
      repetidas: repetidas.length,
      feitas:    feitasNoBanco,
      doCache,
    };
  },

  /** Quantas ineditas e quantas feitas o banco tem para esta materia. */
  contarDisponiveis: async (params?: {
    materia?: string;
    tipo?:    'ENEM' | 'ENADE';
    uid?:     string;
  }): Promise<{ ineditas: number; feitas: number }> => {
    try {
      const { todas, feitas } = await lerBanco(params);
      const jaFeitas = todas.filter(qq => feitas.has(String(qq.id))).length;
      return { ineditas: todas.length - jaFeitas, feitas: jaFeitas };
    } catch { return { ineditas: 0, feitas: 0 }; }
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
          return list;
        }
      } catch (e) { console.warn('[questoesApi.listar] GET /exercicios:', e); }
    }

    // 3. POST /procedural/gerar — Python puro, ultimo degrau da cascata.
    //
    //    FORA do `if (tipo !== 'ENADE')` de proposito. Ele estava dentro, e
    //    isso deixava o ENADE sem gerador nenhum: caia direto no /inspirar.
    //    O que justificava a exclusao era o passo 2 (o backend so tem
    //    materia de ENEM na colecao de exercicios), e isso nao vale aqui —
    //    os geradores procedurais cobrem ads, saude, direito, redes e
    //    administracao, que sao justamente as areas do ENADE.
    try {
      const qs = new URLSearchParams({
        disciplina: disciplinasProcedurais(mat, tipo).split(',')[0],
        quantidade: String(Math.min(lim, 10)),
        salvar:     'false',   // com salvar=true a rota devolve o gabarito como texto
      });
      console.log('[questoesApi.listar] POST /procedural/gerar?' + qs.toString());
      const raw  = await proceduralFetch<any>(`/procedural/gerar?${qs}`, { method: 'POST' }, 60000);
      const list = normalizeList<any>(mesclarGabarito(raw).questoes)
                     .map((q: any) => normalizeQuestao(q, tipo));
      if (list.length > 0) {
        return list;
      }
    } catch (e) { console.warn('[questoesApi.listar] POST /procedural/gerar:', e); }

    // Antes havia mais dois degraus aqui: POST /exercicios/gerar e
    // POST /{tipo}/inspirar, os dois com Gemini. Sairam da API. Mantê-los
    // aqui custaria 120s + 120s de espera por dois 404 antes de desistir.
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

// ── CATALOGO PROCEDURAL ───────────────────────────────────────────────────────

export interface TopicoProcedural {
  chave:  string;
  rotulo: string;
  nivel?: string | null;
  area?:  string;
}

export interface DisciplinaProcedural {
  chave:   string;
  topicos: TopicoProcedural[];
  /** Maior caderno que o material daquela disciplina sustenta sem repetir. */
  maximoSugerido: number;
}

export interface CatalogoProcedural {
  disciplinas:    DisciplinaProcedural[];
  /** nome do grupo → disciplinas que ele reúne */
  grupos:         Record<string, string[]>;
  /** disciplina OU grupo → teto de questões sem repetir fato */
  maximoSugerido: Record<string, number>;
}

export const proceduralApi = {
  /**
   * Catalogo de disciplinas, topicos e grupos.
   *
   * Serve a tela de montagem: e daqui que sai a lista do seletor e o
   * `maximo_sugerido`, que e o teto de questoes que a disciplina aguenta
   * antes de comecar a repetir fato. Pedir acima disso nao quebra — o
   * montador devolve um caderno menor e avisa em `fatos_repetidos`.
   */
  topicos: async (): Promise<CatalogoProcedural | null> => {
    try {
      const raw = await proceduralFetch<any>('/procedural/topicos', undefined, 45000);

      // A rota devolve `disciplinas` como OBJETO (chave -> lista de tópicos),
      // não como lista. Passar isso por normalizeList devolvia vazio.
      const dicionario = raw?.disciplinas ?? {};
      const maximos: Record<string, number> = raw?.maximo_sugerido ?? {};

      const disciplinas: DisciplinaProcedural[] = Object.keys(dicionario).map(chave => ({
        chave,
        topicos: Array.isArray(dicionario[chave]) ? dicionario[chave] : [],
        maximoSugerido: maximos[chave] ?? 30,
      }));

      return { disciplinas, grupos: raw?.grupos ?? {}, maximoSugerido: maximos };
    } catch (e) {
      console.warn('[proceduralApi.topicos]', e);
      return null;
    }
  },

  /** Simulado procedural sob medida — usado pela tela de montagem. */
  simulado: async (
    disciplinas: string,
    quantidade = 30,
    tipo: 'ENEM' | 'ENADE' = 'ENADE',
    duracaoMinutos?: number,
  ): Promise<Simulado | null> => {
    try {
      const qs = new URLSearchParams({
        quantidade:       String(quantidade),
        disciplinas,
        incluir_gabarito: 'true',
      });
      const raw = await proceduralFetch<any>(`/procedural/simulado?${qs}`, { method: 'POST' }, 90000);
      const sim = normalizeSimulado(mesclarGabarito(raw), tipo);
      if (sim.questoes.length === 0) return null;
      // O cronômetro da tela de simulado lê duracao_minutos.
      if (duracaoMinutos) sim.duracao_minutos = duracaoMinutos;
      return sim;
    } catch (e) {
      console.warn('[proceduralApi.simulado]', e);
      return null;
    }
  },

  /**
   * Questões avulsas, para praticar sem cronômetro.
   *
   * `alvo` pode ser uma disciplina OU um grupo ("medicina", "enem",
   * "computacao"). As duas rotas se dividem assim:
   *
   *   /procedural/gerar     — uma disciplina só, e aceita filtro de tópico,
   *                           mas RECUSA nome de grupo (400).
   *   /procedural/simulado  — expande grupo, mistura as disciplinas e aplica
   *                           o veto de repetição, mas não filtra tópico.
   *
   * Então tenta a primeira e cai para a segunda. Sem isso, escolher
   * "Medicina" e pedir para praticar devolvia lista vazia.
   */
  questoes: async (
    alvo: string,
    quantidade = 10,
    tipo: 'ENEM' | 'ENADE' = 'ENADE',
    topico?: string,
  ): Promise<Questao[]> => {
    try {
      const qs = new URLSearchParams({
        disciplina: alvo,
        quantidade: String(quantidade),
        salvar:     'false',
      });
      if (topico) qs.set('topico', topico);
      const raw = await proceduralFetch<any>(`/procedural/gerar?${qs}`, { method: 'POST' }, 60000);
      const lista = normalizeList<any>(mesclarGabarito(raw).questoes)
                      .map((q: any) => normalizeQuestao(q, tipo));
      if (lista.length > 0) return lista;
    } catch (e) {
      console.warn('[proceduralApi.questoes] /gerar:', e);
    }

    // Grupo, ou disciplina que a rota simples não atende.
    const sim = await proceduralApi.simulado(alvo, quantidade, tipo);
    return sim?.questoes ?? [];
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
          guardarSimuladoLocal(sim).catch(() => {});
          return [sim];
        }
      }
    } catch (e) { console.warn('[simuladosApi.listar] /simulado:', e); }

    // 4. POST /procedural/simulado — gerado em Python, ultimo degrau.
    //    incluir_gabarito=true porque a tela de simulado corrige offline
    //    (simulados.tsx compara respostas[q.id] com q.gabarito); sem o
    //    campo, todo acerto seria contado como erro.
    try {
      const qs = new URLSearchParams({
        quantidade:       '30',
        disciplinas:      disciplinasProcedurais(undefined, t),
        incluir_gabarito: 'true',
      });
      console.log('[simuladosApi.listar] POST /procedural/simulado?' + qs.toString());
      const raw = await proceduralFetch<any>(`/procedural/simulado?${qs}`, { method: 'POST' }, 60000);
      const sim = normalizeSimulado(mesclarGabarito(raw), t);
      if (sim.questoes.length > 0) {
        guardarSimuladoLocal(sim).catch(() => {});
        return [sim];
      }
    } catch (e) { console.warn('[simuladosApi.listar] /procedural/simulado:', e); }

    // Havia um degrau 5 aqui: POST /{tipo}/inspirar, com Gemini e timeout de
    // 150s. A rota saiu da API — esperar por ela seria dois minutos e meio
    // de ampulheta para chegar no mesmo lugar.
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
        guardarSimuladoLocal(sim).catch(() => {});
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

    // 0. O APARELHO primeiro. Simulado gerado aqui foi guardado aqui, e é
    //    isto que faz tocar na lista abrir EXATAMENTE o caderno que estava
    //    na lista. Sem este passo a busca cai no /montar, que monta outro
    //    simulado do banco — mesmo título, questões diferentes.
    //    Vem antes do Firestore de propósito: é instantâneo e offline.
    const local = await lerSimuladoLocal(id);
    if (local) {
      console.log(`[simuladosApi.buscarPorId] do aparelho: ${local.questoes.length} questões`);
      return { ...local, questoes: ordenarQuestoes(local.questoes, feitas) };
    }

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
        guardarSimuladoLocal(sim).catch(() => {});
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
      });
    } catch (e) { console.warn('[simuladosApi.enviarResultado] REST:', e); }
  },
};

// ── QUESTOES FEITAS (memoria anti-repeticao) ──────────────────────────────────
//
// Duas camadas, e a de baixo e que sustenta a promessa:
//
//   APARELHO (AsyncStorage)  gravacao local, sincrona, nunca falha por rede.
//   NUVEM    (Firestore)     sincroniza entre aparelhos do mesmo login.
//
// A versao anterior so tinha a nuvem, com `.catch(() => {})` na gravacao. Duas
// consequencias: um write que falhasse perdia o registro em silencio, e a
// questao voltava a aparecer; e usuario DESLOGADO nao tinha anti-repeticao
// nenhuma, porque as duas funcoes desistiam no `uid === 'anonimo'`.
//
// Agora o aparelho sempre registra, logado ou nao. A nuvem e um bonus que
// atravessa aparelhos quando ha login. Na leitura, os dois conjuntos sao
// UNIDOS — nunca intersectados: na duvida sobre ter feito ou nao, a resposta
// segura e "ja fez", porque mostrar repetida e o defeito que queremos matar.

const CHAVE_FEITAS = 'nivelis:questoes_feitas';

/** Le o registro do aparelho. Falha de storage devolve vazio, nao explode. */
async function feitasLocais(uid: string): Promise<Set<string>> {
  try {
    const bruto = await AsyncStorage.getItem(`${CHAVE_FEITAS}:${uid || 'anonimo'}`);
    if (!bruto) return new Set();
    const ids = JSON.parse(bruto);
    return new Set(Array.isArray(ids) ? ids.map(String) : []);
  } catch { return new Set(); }
}

async function gravarLocais(uid: string, ids: Set<string>): Promise<void> {
  try {
    await AsyncStorage.setItem(
      `${CHAVE_FEITAS}:${uid || 'anonimo'}`,
      JSON.stringify([...ids]),
    );
  } catch (e) { console.warn('[questoesFeitas] storage local:', e); }
}

export const questoesFeitasApi = {
  /**
   * Set de IDs que o usuario ja respondeu — uniao de aparelho e nuvem.
   *
   * Funciona sem login: o Set do aparelho vale por si. Com login, a nuvem
   * entra em cima e o resultado volta gravado localmente, para o proximo
   * carregamento nao depender de rede.
   */
  listar: async (uid: string): Promise<Set<string>> => {
    const locais = await feitasLocais(uid);
    if (!uid || uid === 'anonimo') return locais;

    try {
      const snap = await getDoc(doc(db, 'questoes_feitas', uid));
      if (snap.exists()) {
        const ids = snap.data()?.ids ?? [];
        const daNuvem: string[] = Array.isArray(ids) ? ids.map(String) : [];
        const antes = locais.size;
        for (const id of daNuvem) locais.add(id);
        // Só reescreve se a nuvem trouxe novidade — evita I/O a cada tela.
        if (locais.size > antes) await gravarLocais(uid, locais);
      }
    } catch (e) { console.warn('[questoesFeitasApi.listar] nuvem:', e); }

    return locais;
  },

  /**
   * Marca questoes como feitas. O aparelho grava PRIMEIRO e e aguardado;
   * a nuvem vai depois e pode falhar sem prejuizo.
   *
   * Questao gerada na hora (id `proc-...`) e descartada aqui de proposito:
   * o id dela e sorteado por lote e nunca reaparece, entao registrar so
   * engordaria o documento com entradas mortas. O que pode repetir e o que
   * vem do banco, e e isso que a memoria guarda.
   */
  marcar: async (uid: string, questaoIds: string[]): Promise<void> => {
    // `mock_` entra na lista por um motivo bobo mas real: as tres questoes de
    // demonstracao tem id estavel e sem prefixo, entao sem este filtro elas
    // eram gravadas como feitas e sujavam a memoria com ids que nao existem
    // no banco.
    const persistiveis = questaoIds
      .map(String)
      .filter(id => id && !id.startsWith('proc-')
                       && !id.startsWith('minha:')
                       && !id.startsWith('mock_'));
    if (persistiveis.length === 0) return;

    const locais = await feitasLocais(uid);
    for (const id of persistiveis) locais.add(id);
    await gravarLocais(uid, locais);

    if (!uid || uid === 'anonimo') return;
    try {
      await setDoc(
        doc(db, 'questoes_feitas', uid),
        { ids: arrayUnion(...persistiveis), atualizadoEm: serverTimestamp() },
        { merge: true },
      );
      console.log(`[questoesFeitasApi.marcar] ${persistiveis.length} na nuvem para ${uid}`);
    } catch (e) {
      // Sem drama: o aparelho ja registrou, e a proxima leitura une os dois.
      console.warn('[questoesFeitasApi.marcar] nuvem falhou, local ok:', e);
    }
  },

  /** Esquece o que foi feito — usado pelo "começar de novo" do usuario. */
  limpar: async (uid: string): Promise<void> => {
    await gravarLocais(uid, new Set());
    if (!uid || uid === 'anonimo') return;
    try {
      await setDoc(doc(db, 'questoes_feitas', uid),
                   { ids: [], atualizadoEm: serverTimestamp() }, { merge: true });
    } catch (e) { console.warn('[questoesFeitasApi.limpar] nuvem:', e); }
  },
};

// ── HELPERS de ordem ──────────────────────────────────────────────────────────

/** Fisher-Yates. Sem efeito colateral: devolve copia. */
function embaralhar<T>(itens: T[]): T[] {
  const arr = [...itens];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/**
 * Embaralha e coloca as JA FEITAS no fim da fila.
 *
 * Usado onde o conjunto e FECHADO e precisa ser entregue inteiro — o
 * simulado, que tem N questoes fixas e nao pode descartar nenhuma. Ali
 * empurrar para o fim e o certo: o usuario vê as ineditas primeiro e o
 * caderno continua completo.
 *
 * Na tela de praticar e o contrario: o conjunto e aberto, entao a feita e
 * EXCLUIDA (modo 'novas' do listarDoBanco) e o procedural cobre a falta.
 */
function ordenarQuestoes(questoes: Questao[], feitas: Set<string>): Questao[] {
  const arr = embaralhar(questoes);
  const novas:     Questao[] = [];
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

export const MOCK_QUESTOES: Questão[] = [
  {
    id: 'mock_q1', materia: 'LINGUAGENS', topico: 'Literatura', tipo: 'ENEM', ano: 2023,
    enunciado: 'Leia o poema de Camoes:\n\n"Amor e fogo que arde sem se ver;\nE ferida que doi e não se sente;"\n\nA principal figura de linguagem usada para expressar a natureza contraditoria do amor e:',
    alternativas: [
      { id: 'A', texto: 'Metáfora - comparações implicitas.' },
      { id: 'B', texto: 'Paradoxo - união de ideias irreconciliaveis.' },
      { id: 'C', texto: 'Hipérbole - exagero intencional.' },
      { id: 'D', texto: 'Pleonasmo - repetição de termos.' },
      { id: 'E', texto: 'Eufemismo - suavização da dor.' },
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
    enunciado: 'Qual processo celular converte glicose em ATP na ausência de oxigenio?',
    alternativas: [
      { id: 'A', texto: 'Respiração aerobica' },
      { id: 'B', texto: 'Fotossintese' },
      { id: 'C', texto: 'Fermentação' },
      { id: 'D', texto: 'Ciclo de Krebs' },
      { id: 'E', texto: 'Fosforilação oxidativa' },
    ],
    gabarito: 'C',
  },
];

/**
 * Os simulados que aparecem quando o servidor não responde.
 *
 * O título e a descrição são TEXTO DE TELA — o usuário lê isso no painel de
 * simulados sempre que a API está fora. Diziam "Simulado Demo ENEM" e
 * "Questoes demonstrativas (sem conexao)": "Demo" é a nossa palavra, não a
 * dele, e os acentos faltavam nas duas. Quem abrisse o app sem internet via
 * um nome de rascunho e uma frase mal escrita.
 *
 * A duração também era mentira: 270 e 240 minutos para cadernos de 2 e 1
 * questão. Agora acompanha o tamanho, pela mesma regra do item 12.
 */
export const MOCK_SIMULADOS: Simulado[] = [
  {
    id: 'mock_enem', titulo: 'Exemplo — ENEM', tipo: 'ENEM',
    descricao: 'Algumas questões para praticar enquanto o servidor não responde',
    questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENEM'),
    duracao_minutos: Math.max(10, MOCK_QUESTOES.filter(q => q.tipo === 'ENEM').length * 3),
    total_questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENEM').length,
    imagem: 'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?q=80&w=600',
  },
  {
    id: 'mock_enade', titulo: 'Exemplo — ENADE', tipo: 'ENADE',
    descricao: 'Algumas questões para praticar enquanto o servidor não responde',
    questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENADE'),
    duracao_minutos: Math.max(10, MOCK_QUESTOES.filter(q => q.tipo === 'ENADE').length * 3),
    total_questoes: MOCK_QUESTOES.filter(q => q.tipo === 'ENADE').length,
    imagem: 'https://images.unsplash.com/photo-1491841573634-28140fc7ced7?q=80&w=600',
  },
];
