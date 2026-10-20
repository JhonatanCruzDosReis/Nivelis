// ─────────────────────────────────────────────────────────────────────────────
//  CONTRASTE — escolher a cor do texto pelo fundo, não pelo chute
//
//  O cronograma deixa o usuário pintar cada evento, e a paleta inclui
//  #FFFFFF, #DAF7A6 e #FFC300. O texto era branco FIXO, então nessas três
//  cores o nome do evento simplesmente sumia — o usuário via um retângulo
//  amarelo vazio e nenhuma pista de que havia algo escrito ali.
//
//  A conta é a luminância relativa da WCAG. Não é estética: é a mesma
//  fórmula que define se um par de cores passa no critério de contraste.
// ─────────────────────────────────────────────────────────────────────────────

/** #RGB, #RRGGBB ou #RRGGBBAA → [r, g, b] de 0 a 255. */
function paraRGB(hex: string): [number, number, number] {
  let h = String(hex || '').trim().replace('#', '');
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  if (h.length < 6) return [128, 128, 128];     // irreconhecível: cinza médio
  const n = parseInt(h.slice(0, 6), 16);
  if (Number.isNaN(n)) return [128, 128, 128];
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/**
 * Luminância relativa (WCAG 2.x), de 0 (preto) a 1 (branco).
 *
 * Os três canais NÃO pesam igual porque o olho humano não os enxerga
 * igual: o verde responde por quase três quartos da luminosidade
 * percebida, e o azul por menos de 8%. É por isso que um azul escuro
 * parece mais escuro que um verde da mesma "intensidade" em RGB.
 */
export function luminancia(hex: string): number {
  const [r, g, b] = paraRGB(hex).map(v => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Quase-preto, calibrado — não escolhido no olho.
 *
 * Com #16181D a pior cor da paleta do cronograma (#A855F7) ficava em
 * 4.488:1, doze milésimos abaixo do mínimo de 4.5 da WCAG. Testei a
 * paleta inteira contra cinco tons e este é o mais claro que aprova todas
 * as quinze: #121418 leva o pior caso a 4.66:1. Escurecer mais não ganha
 * nada — daí em diante o gargalo vira o cinza #64748B, que trava em 4.76
 * com qualquer preto.
 */
const ESCURO = '#121418';
const CLARO  = '#FFFFFF';

/**
 * Razão de contraste da WCAG entre duas cores, de 1:1 a 21:1.
 * O mínimo para texto é 4.5:1 (3:1 para texto grande).
 */
export function razaoDeContraste(a: string, b: string): number {
  const la = luminancia(a), lb = luminancia(b);
  const claro = Math.max(la, lb), escuro = Math.min(la, lb);
  return (claro + 0.05) / (escuro + 0.05);
}

/**
 * A cor de texto que fica legível sobre `fundo`.
 *
 * CALCULA as duas razões e escolhe a maior, em vez de decidir por um
 * limiar de luminância. A diferença não é acadêmica: num laranja
 * #F59E0B — luminância 0.47, logo acima de qualquer corte em 0.45 — o
 * limiar escolhia branco, que dá 2.15:1. O preto ali dá 9.1:1. Quatro
 * vezes melhor, e o limiar entregava o pior dos dois.
 *
 * Tom médio é exatamente onde o limiar erra, e tom médio é a maior parte
 * de qualquer paleta.
 */
export function corDoTextoSobre(fundo: string): string {
  return razaoDeContraste(fundo, ESCURO) >= razaoDeContraste(fundo, CLARO)
    ? ESCURO
    : CLARO;
}

/**
 * A sombra do texto.
 *
 * Acompanha o FUNDO, não o texto: a sombra é um halo que separa as letras
 * do que está atrás. Fundo claro ganha halo claro, fundo escuro ganha halo
 * escuro — assim o halo some no fundo e sobra só o contorno do texto.
 * Fazer o contrário (halo escuro sob texto escuro) borra em vez de separar.
 */
export function sombraDoTextoSobre(fundo: string): string {
  return luminancia(fundo) > 0.45
    ? 'rgba(255,255,255,0.55)'
    : 'rgba(0,0,0,0.5)';
}
