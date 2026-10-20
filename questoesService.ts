/**
 * questoesService.ts
 * Histórico de sessões de questões avulsas (AsyncStorage local).
 * Gêmeo do desempenhoService, mas focado em prática de questões soltas
 * (não simulados completos). Guarda cada sessão e calcula stats por matéria.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Questao } from './apiService';

// ─── Storage key ──────────────────────────────────────────────────────────────
const QUESTOES_HIST_KEY = '@nivelis_questoes_hist_v1';

// ─── Types ────────────────────────────────────────────────────────────────────
export interface SessaoQuestoes {
  id: string;               // Date.now().toString()
  tipo: 'ENEM' | 'ENADE';
  materia: string;          // matéria praticada (ou 'Todas')
  data: string;             // ISO date
  acertos: number;
  erros: number;
  total: number;
  // detalhe de cada questão respondida (pra revisar depois)
  detalhes: {
    questaoId: string;
    materia: string;
    enunciado: string;
    respostaDada: string;
    gabarito: string;
    acertou: boolean;
  }[];
}

export interface QuestoesStats {
  totalRespondidas: number;
  totalAcertos: number;
  percentualGeral: number;       // 0–100
  totalSessoes: number;
  porMateria: Record<string, { acertos: number; total: number; percentual: number }>;
}

// ─── Helpers internos ─────────────────────────────────────────────────────────
async function carregarSessoes(): Promise<SessaoQuestoes[]> {
  try {
    const raw = await AsyncStorage.getItem(QUESTOES_HIST_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [];
}

async function salvarSessoes(sessoes: SessaoQuestoes[]): Promise<void> {
  await AsyncStorage.setItem(QUESTOES_HIST_KEY, JSON.stringify(sessoes));
}

// ─── API Pública ──────────────────────────────────────────────────────────────

/**
 * Salva uma sessão de questões concluída.
 * Chamado quando o usuário termina de responder um conjunto de questões.
 */
export async function salvarSessaoQuestoes(
  tipo: 'ENEM' | 'ENADE',
  materia: string,
  questoes: Questao[],
  respostas: Record<string, string>,
): Promise<void> {
  const sessoes = await carregarSessoes();

  // Monta detalhes de cada questão respondida
  const detalhes = questoes
    .filter(q => respostas[q.id] != null) // só as respondidas
    .map(q => {
      const respostaDada = respostas[q.id];
      const gabarito = String(q.gabarito ?? '');
      return {
        questaoId:    String(q.id),
        materia:      q.materia ?? 'Geral',
        enunciado:    q.enunciado ?? '',
        respostaDada,
        gabarito,
        acertou:      respostaDada?.toUpperCase() === gabarito.toUpperCase(),
      };
    });

  if (detalhes.length === 0) return; // nada respondido, não salva

  const acertos = detalhes.filter(d => d.acertou).length;

  const sessao: SessaoQuestoes = {
    id:       Date.now().toString(),
    tipo,
    materia:  materia || 'Todas',
    data:     new Date().toISOString(),
    acertos,
    erros:    detalhes.length - acertos,
    total:    detalhes.length,
    detalhes,
  };

  sessoes.unshift(sessao);
  // Mantém só as últimas 50 sessões
  if (sessoes.length > 50) sessoes.splice(50);

  await salvarSessoes(sessoes);
}

/** Carrega histórico de sessões (mais recente primeiro). */
export async function carregarSessoesQuestoes(): Promise<SessaoQuestoes[]> {
  return carregarSessoes();
}

/** Calcula estatísticas agregadas de todas as sessões. */
export async function carregarStatsQuestoes(): Promise<QuestoesStats> {
  const sessoes = await carregarSessoes();

  let totalRespondidas = 0;
  let totalAcertos = 0;
  const porMateria: Record<string, { acertos: number; total: number; percentual: number }> = {};

  for (const s of sessoes) {
    for (const d of s.detalhes) {
      totalRespondidas++;
      if (d.acertou) totalAcertos++;

      const mat = d.materia || 'Geral';
      if (!porMateria[mat]) porMateria[mat] = { acertos: 0, total: 0, percentual: 0 };
      porMateria[mat].total++;
      if (d.acertou) porMateria[mat].acertos++;
    }
  }

  // Calcula percentual por matéria
  Object.values(porMateria).forEach(m => {
    m.percentual = m.total > 0 ? Math.round((m.acertos / m.total) * 100) : 0;
  });

  return {
    totalRespondidas,
    totalAcertos,
    percentualGeral: totalRespondidas > 0 ? Math.round((totalAcertos / totalRespondidas) * 100) : 0,
    totalSessoes: sessoes.length,
    porMateria,
  };
}

/** Limpa todo o histórico de questões (para testes). */
export async function limparHistoricoQuestoes(): Promise<void> {
  await AsyncStorage.removeItem(QUESTOES_HIST_KEY);
}

/** Formata data ISO para exibição em pt-BR. */
export function formatarDataQuestoes(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  } catch { return iso; }
}
