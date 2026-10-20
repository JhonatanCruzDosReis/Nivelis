// ─────────────────────────────────────────────────────────────────────────────
//  MINHAS QUESTÕES — banco pessoal do usuário
//
//  Questão escrita pelo próprio usuário. Vive só no aparelho dele
//  (AsyncStorage), sem passar pela API: não custa cota, funciona offline e
//  não polui o banco compartilhado.
//
//  Ela tem o mesmo formato de `Questao` do apiService justamente para poder
//  entrar no fluxo de praticar junto com as demais, sem a tela precisar
//  saber de onde cada uma veio. O que distingue é o prefixo do id
//  (`minha:`), que a tela usa para oferecer o botão de excluir.
// ─────────────────────────────────────────────────────────────────────────────

import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Questao, Alternativa } from './apiService';

const CHAVE = '@minhas_questoes';

/** Prefixo do id. Serve para reconhecer a questão como do usuário. */
export const PREFIXO_MINHA = 'minha:';

export const LETRAS = ['A', 'B', 'C', 'D', 'E'] as const;

export interface MinhaQuestao extends Questao {
  id: string;
  criadaEm: string;    // ISO
  propria: true;       // marcador explícito, além do prefixo do id
}

/** O que a tela de criação entrega. */
export interface RascunhoQuestao {
  materia:      string;
  topico?:      string;
  enunciado:    string;
  alternativas: string[];   // na ordem A, B, C…
  gabarito:     string;     // letra
  explicacao?:  string;
  tipo?:        'ENEM' | 'ENADE';
}

export interface ErroValidacao {
  campo: 'materia' | 'enunciado' | 'alternativas' | 'gabarito';
  mensagem: string;
}

export function ehQuestaoPropria(q: { id: string | number }): boolean {
  return String(q.id).startsWith(PREFIXO_MINHA);
}

/**
 * Valida o rascunho e devolve a lista de problemas.
 *
 * A validação é aqui, e não na tela, porque a mesma regra precisa valer
 * para a criação e para a edição.
 */
export function validar(r: RascunhoQuestao): ErroValidacao[] {
  const erros: ErroValidacao[] = [];
  const preenchidas = r.alternativas.map(a => a.trim()).filter(Boolean);

  if (!r.materia?.trim()) {
    erros.push({ campo: 'materia', mensagem: 'Escolha a matéria.' });
  }
  if (!r.enunciado?.trim()) {
    erros.push({ campo: 'enunciado', mensagem: 'Escreva o enunciado.' });
  } else if (r.enunciado.trim().length < 10) {
    erros.push({ campo: 'enunciado', mensagem: 'O enunciado está curto demais.' });
  }

  if (preenchidas.length < 2) {
    erros.push({ campo: 'alternativas', mensagem: 'Preencha pelo menos duas alternativas.' });
  } else {
    // Alternativa repetida deixa a questão com duas respostas marcáveis.
    const vistas = new Set<string>();
    for (const t of preenchidas) {
      const chave = t.toLowerCase().replace(/\s+/g, ' ');
      if (vistas.has(chave)) {
        erros.push({ campo: 'alternativas', mensagem: 'Há duas alternativas iguais.' });
        break;
      }
      vistas.add(chave);
    }
  }

  const idxGab = LETRAS.indexOf(r.gabarito as any);
  if (idxGab < 0) {
    erros.push({ campo: 'gabarito', mensagem: 'Marque qual alternativa é a correta.' });
  } else if (!r.alternativas[idxGab]?.trim()) {
    erros.push({
      campo: 'gabarito',
      mensagem: `A alternativa ${r.gabarito} está vazia — não pode ser o gabarito.`,
    });
  }

  return erros;
}

/**
 * Monta as alternativas e devolve o gabarito JÁ REMAPEADO.
 *
 * Quem deixa a alternativa C em branco e marca a D como certa não espera
 * ver "A, B, D" na hora de responder. As letras são compactadas, e por
 * isso o gabarito precisa acompanhar: o D do formulário vira o C da
 * questão. Mapear um sem o outro apontaria para a alternativa errada.
 */
function compactar(textos: string[], gabarito: string): {
  alternativas: Alternativa[];
  gabarito: string;
} {
  const idxOriginal = LETRAS.indexOf(gabarito as any);
  const alternativas: Alternativa[] = [];
  let novoGabarito = gabarito;

  textos.forEach((bruto, i) => {
    const texto = bruto.trim();
    if (!texto) return;
    const letra = LETRAS[alternativas.length];
    if (i === idxOriginal) novoGabarito = letra;
    alternativas.push({ id: letra, texto });
  });

  return { alternativas, gabarito: novoGabarito };
}

async function lerTudo(): Promise<MinhaQuestao[]> {
  try {
    const raw = await AsyncStorage.getItem(CHAVE);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    // Storage corrompido não pode derrubar a tela de praticar.
    return [];
  }
}

async function gravarTudo(lista: MinhaQuestao[]): Promise<void> {
  await AsyncStorage.setItem(CHAVE, JSON.stringify(lista));
}

/** Todas as questões do usuário, da mais recente para a mais antiga. */
export async function listar(filtro?: {
  tipo?: 'ENEM' | 'ENADE';
  materia?: string;
}): Promise<MinhaQuestao[]> {
  let lista = await lerTudo();
  if (filtro?.tipo) lista = lista.filter(q => !q.tipo || q.tipo === filtro.tipo);
  if (filtro?.materia && filtro.materia !== 'Todas') {
    const alvo = filtro.materia.toLowerCase();
    lista = lista.filter(q => (q.materia ?? '').toLowerCase() === alvo);
  }
  return lista.sort((a, b) => (a.criadaEm < b.criadaEm ? 1 : -1));
}

export async function contar(): Promise<number> {
  return (await lerTudo()).length;
}

export async function buscar(id: string): Promise<MinhaQuestao | null> {
  return (await lerTudo()).find(q => q.id === id) ?? null;
}

/**
 * Cria a questão. Lança se o rascunho não passar na validação — a tela
 * deve chamar `validar` antes e só chegar aqui com o formulário limpo.
 */
export async function criar(r: RascunhoQuestao): Promise<MinhaQuestao> {
  const erros = validar(r);
  if (erros.length) throw new Error(erros[0].mensagem);

  const compacto = compactar(r.alternativas, r.gabarito);
  const nova: MinhaQuestao = {
    id:           `${PREFIXO_MINHA}${Date.now()}`,
    materia:      r.materia.trim(),
    topico:       r.topico?.trim() || undefined,
    enunciado:    r.enunciado.trim(),
    alternativas: compacto.alternativas,
    gabarito:     compacto.gabarito,
    explicacao:   r.explicacao?.trim() || undefined,
    tipo:         r.tipo,
    criadaEm:     new Date().toISOString(),
    propria:      true,
  };

  const lista = await lerTudo();
  await gravarTudo([nova, ...lista]);
  return nova;
}

/** Substitui uma questão existente, preservando id e data de criação. */
export async function atualizar(id: string, r: RascunhoQuestao): Promise<MinhaQuestao> {
  const erros = validar(r);
  if (erros.length) throw new Error(erros[0].mensagem);

  const lista = await lerTudo();
  const i = lista.findIndex(q => q.id === id);
  if (i < 0) throw new Error('Questão não encontrada.');

  const compacto = compactar(r.alternativas, r.gabarito);
  const atualizada: MinhaQuestao = {
    ...lista[i],
    materia:      r.materia.trim(),
    topico:       r.topico?.trim() || undefined,
    enunciado:    r.enunciado.trim(),
    alternativas: compacto.alternativas,
    gabarito:     compacto.gabarito,
    explicacao:   r.explicacao?.trim() || undefined,
    tipo:         r.tipo,
  };
  lista[i] = atualizada;
  await gravarTudo(lista);
  return atualizada;
}

/** Remove a questão. Devolve true se havia o que remover. */
export async function excluir(id: string): Promise<boolean> {
  const lista = await lerTudo();
  const restante = lista.filter(q => q.id !== id);
  if (restante.length === lista.length) return false;
  await gravarTudo(restante);
  return true;
}

/** Apaga todas — usado pelo "limpar dados" do app. */
export async function excluirTodas(): Promise<void> {
  await AsyncStorage.removeItem(CHAVE);
}
