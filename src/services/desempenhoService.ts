/**
 * desempenhoService.ts
 * Tracks simulado results locally (AsyncStorage).
 * Computes per-subject stats, banco de horas, and generates cronograma events.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Questao } from './apiService';

// ─── Storage keys ────────────────────────────────────────────────────────────
const DESEMPENHO_KEY    = '@nivelis_desempenho_v1';
const CRONOGRAMA_KEY    = '@meu_cronograma_eventos';   // same key used by cronograma screen

// ─── Types ───────────────────────────────────────────────────────────────────
export interface HistoricoItem {
  id: string;               // uuid-ish: Date.now().toString()
  simuladoId: string | null;
  titulo: string;
  tipo: 'ENEM' | 'ENADE';
  data: string;             // ISO date string
  acertos: number;
  total: number;
  tempoSegundos: number;
  porMateria: Record<string, { acertos: number; total: number }>;
  respostas: Record<string, string>;
  questoes: Questao[];
}

export interface MateriaStats {
  acertos: number;
  total: number;
  percentualAcerto: number;   // 0–100
  percentualErro: number;     // 0–100
  horasBanco: number;         // study hours recommended (0–10)
}

export interface Desempenho {
  historico: HistoricoItem[];
  /** Cumulative cross-simulado per-subject stats */
  porMateria: Record<string, { acertos: number; total: number }>;
}

// Cronograma event shape (matches cronograma/index.tsx expectations)
interface CronogramaEvento {
  id: string;
  nome: string;
  dia: string;    // 'SEG' | 'TER' | 'QUA' | 'QUI' | 'SEX' | 'SAB' | 'DOM'
  inicioIdx: number;  // half-hour index 0–47
  fimIdx: number;
  cor: string;
  horaStr: string;
}

// ─── Constants ───────────────────────────────────────────────────────────────
const MATERIA_CORES: Record<string, string> = {
  'MATEMÁTICA':          '#4F46E5',
  'LINGUAGENS':          '#7D53DD',
  'CIÊNCIAS HUMANAS':    '#F59E0B',
  'CIÊNCIAS DA NATUREZA':'#10B981',
  'REDAÇÃO':             '#EC4899',
  'HISTÓRIA':            '#F59E0B',
  'GEOGRAFIA':           '#059669',
  'FÍSICA':              '#3B82F6',
  'QUÍMICA':             '#EC4899',
  'BIOLOGIA':            '#22C55E',
  'FILOSOFIA':           '#A78BFA',
  'SOCIOLOGIA':          '#FB923C',
  'INGLÊS':              '#14B8A6',
  'ARTES':               '#F43F5E',
};
const DEFAULT_COR = '#6B7280';

const DIAS_SEMANA = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM'];

// Half-hour slots for study sessions (morning / evening)
const SESSOES = [
  { inicioIdx: 14, fimIdx: 17 }, // 07:00 – 08:30
  { inicioIdx: 22, fimIdx: 25 }, // 11:00 – 12:30
  { inicioIdx: 38, fimIdx: 41 }, // 19:00 – 20:30
];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function idxToHoraStr(idx: number): string {
  const h = Math.floor(idx / 2).toString().padStart(2, '0');
  const m = idx % 2 === 0 ? '00' : '30';
  return `${h}:${m}`;
}

async function carregarDesempenho(): Promise<Desempenho> {
  try {
    const raw = await AsyncStorage.getItem(DESEMPENHO_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { historico: [], porMateria: {} };
}

async function salvarDesempenho(d: Desempenho): Promise<void> {
  await AsyncStorage.setItem(DESEMPENHO_KEY, JSON.stringify(d));
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Save a completed simulado result.
 * Updates cumulative porMateria stats automatically.
 */
export async function salvarHistorico(
  simuladoId: string | null,
  titulo: string,
  tipo: 'ENEM' | 'ENADE',
  acertos: number,
  total: number,
  tempoSegundos: number,
  respostas: Record<string, string>,
  questoes: Questao[],
): Promise<void> {
  const d = await carregarDesempenho();

  // Build per-materia breakdown for this simulado
  const porMateria: Record<string, { acertos: number; total: number }> = {};
  questoes.forEach(q => {
    const mat = q.materia ?? 'GERAL';
    if (!porMateria[mat]) porMateria[mat] = { acertos: 0, total: 0 };
    porMateria[mat].total++;
    if (respostas[q.id] === q.gabarito) porMateria[mat].acertos++;
  });

  const item: HistoricoItem = {
    id: Date.now().toString(),
    simuladoId,
    titulo,
    tipo,
    data: new Date().toISOString(),
    acertos,
    total,
    tempoSegundos,
    porMateria,
    respostas,
    questoes,
  };

  d.historico.unshift(item);
  // Keep last 50 simulados only
  if (d.historico.length > 50) d.historico = d.historico.slice(0, 50);

  // Merge into cumulative stats
  Object.entries(porMateria).forEach(([mat, vals]) => {
    if (!d.porMateria[mat]) d.porMateria[mat] = { acertos: 0, total: 0 };
    d.porMateria[mat].acertos += vals.acertos;
    d.porMateria[mat].total   += vals.total;
  });

  await salvarDesempenho(d);
}

/** Load full simulado history (most recent first). */
export async function carregarHistorico(): Promise<HistoricoItem[]> {
  const d = await carregarDesempenho();
  return d.historico;
}

/** Load computed stats per subject. */
export async function carregarEstatisticasPorMateria(): Promise<Record<string, MateriaStats>> {
  const d = await carregarDesempenho();
  const result: Record<string, MateriaStats> = {};

  Object.entries(d.porMateria).forEach(([mat, raw]) => {
    if (raw.total === 0) return;
    const pctAcerto = Math.round((raw.acertos / raw.total) * 100);
    const pctErro   = 100 - pctAcerto;
    // Hours: every 10% error rate = 1 hour of study, max 10h
    const horas     = Math.min(10, Math.round(pctErro / 10));
    result[mat] = {
      acertos:          raw.acertos,
      total:            raw.total,
      percentualAcerto: pctAcerto,
      percentualErro:   pctErro,
      horasBanco:       horas,
    };
  });

  return result;
}

/**
 * Calculate banco de horas from a single simulado's per-subject breakdown.
 * Returns: { materia -> horasNecessarias }
 */
export function calcularBancoDeHoras(
  porMateria: Record<string, { acertos: number; total: number }>,
): Record<string, number> {
  const result: Record<string, number> = {};
  Object.entries(porMateria).forEach(([mat, v]) => {
    if (v.total === 0) return;
    const pctErro = ((v.total - v.acertos) / v.total) * 100;
    const horas   = Math.max(0, Math.min(10, Math.round(pctErro / 10)));
    if (horas > 0) result[mat] = horas;
  });
  return result;
}

/**
 * Generate cronograma events from a banco de horas map and append them
 * to the existing cronograma in AsyncStorage.
 * Subjects with 0 hours needed are skipped.
 * Returns how many events were created.
 */
export async function gerarEventosCronograma(
  bancoDeHoras: Record<string, number>,
): Promise<number> {
  // Sort subjects by hours needed (most critical first)
  const materias = Object.entries(bancoDeHoras)
    .filter(([, h]) => h > 0)
    .sort((a, b) => b[1] - a[1]);

  if (materias.length === 0) return 0;

  // Load existing events
  let eventos: CronogramaEvento[] = [];
  try {
    const raw = await AsyncStorage.getItem(CRONOGRAMA_KEY);
    if (raw) eventos = JSON.parse(raw);
  } catch {}

  const novosEventos: CronogramaEvento[] = [];
  let diaIdx   = 0;  // cycle through week days
  let sessaoIdx = 0; // cycle through time sessions

  for (const [materia, horas] of materias) {
    // Each session covers 1.5h; how many sessions needed?
    const sessoesPrecisa = Math.max(1, Math.round(horas / 1.5));
    const cor = MATERIA_CORES[materia.toUpperCase()] ?? DEFAULT_COR;

    for (let s = 0; s < sessoesPrecisa; s++) {
      const dia    = DIAS_SEMANA[diaIdx % DIAS_SEMANA.length];
      const sessao = SESSOES[sessaoIdx % SESSOES.length];

      novosEventos.push({
        id:        `auto_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        nome:      `📚 ${materia}`,
        dia,
        inicioIdx: sessao.inicioIdx,
        fimIdx:    sessao.fimIdx,
        cor,
        horaStr:   idxToHoraStr(sessao.inicioIdx),
      });

      sessaoIdx++;
      if (sessaoIdx % SESSOES.length === 0) diaIdx++;
    }
  }

  // Merge (new events don't overwrite existing ones, user can clean manually)
  const merged = [...eventos, ...novosEventos];
  await AsyncStorage.setItem(CRONOGRAMA_KEY, JSON.stringify(merged));
  return novosEventos.length;
}

/** Get subject color */
export function getMateriaCor(materia: string): string {
  return MATERIA_CORES[materia?.toUpperCase()] ?? DEFAULT_COR;
}

/** Clear all performance data (for testing) */
export async function limparDesempenho(): Promise<void> {
  await AsyncStorage.removeItem(DESEMPENHO_KEY);
}
