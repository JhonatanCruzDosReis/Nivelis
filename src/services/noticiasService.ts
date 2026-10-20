// ─────────────────────────────────────────────────────────────────────────────
//  NOTÍCIAS — busca, junção e cache
//
//  Estava tudo dentro do componente da home. Saiu de lá por dois motivos:
//  a lógica é testável sozinha, e a tela não precisa saber de RSS.
//
//  O BUG QUE ISSO CORRIGE
//  ──────────────────────
//  A busca antiga devolvia na PRIMEIRA fonte que respondesse com 2+ itens:
//
//      for (const url of fontes) { ...; if (items.length >= 2) return items; }
//
//  e a primeira fonte das duas abas era a mesma — o feed geral de educação
//  da Agência Brasil. Consequência: ENEM e ENADE mostravam a mesma lista, as
//  fontes específicas de cada prova nunca eram consultadas, e o conteúdo não
//  falava de ENEM nem de ENADE. Era essa a "notícia repetida".
//
//  Agora percorre TODAS as fontes, junta, e descarta repetição por título e
//  por link. O feed geral entra por último e só com matéria do assunto.
// ─────────────────────────────────────────────────────────────────────────────

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// ── O PROXY (noticias_api.py) ────────────────────────────────────────────────
//
// No NAVEGADOR, buscar RSS direto é impossível: news.google.com e
// agenciabrasil não mandam Access-Control-Allow-Origin, e o navegador
// bloqueia antes da resposta chegar ("blocked by CORS policy"). No celular
// isso não acontece, porque React Native não aplica CORS.
//
// O noticias_api.py existe exatamente para isso: ele busca do lado do
// servidor, libera CORS e ainda guarda 8 h em cache — o que também segura
// o 429 do GNews, já que passa a ser uma chamada por categoria a cada 8 h
// em vez de uma por usuário por aba.
//
// E tira a chave do GNews do aplicativo. Chave usada no cliente é pública
// por construção: ela viaja na URL e aparece no console de quem abrir a
// versão web.
// EM PRODUÇÃO não há nada para ninguém iniciar: o noticias_api roda
// montado dentro da API que já está publicada, e o aparelho do usuário
// chama a URL pública. O uvicorn na máquina do desenvolvedor existe só
// para trabalhar no arquivo — por isso o localhost fica atrás de __DEV__.
const PROXY_PRODUCAO = 'https://nivelis-api-1.onrender.com/v1/noticias';

const PROXY_DESENVOLVIMENTO = Platform.OS === 'web'
  ? 'http://localhost:8000'        // uvicorn na própria máquina
  : 'http://10.0.2.2:8000';        // emulador Android enxerga o PC assim

// Em desenvolvimento, se o uvicorn local não estiver de pé, ainda vale
// tentar o publicado antes de desistir.
const PROXY_PADRAO = __DEV__ ? PROXY_DESENVOLVIMENTO : PROXY_PRODUCAO;
const PROXY_RESERVA = __DEV__ ? PROXY_PRODUCAO : null;

let proxyBase: string | null = PROXY_PADRAO;

/** Aponta para onde o noticias_api.py estiver publicado. */
export function definirProxyNoticias(url: string | null) {
  proxyBase = url ? url.replace(/\/+$/, '') : null;
}

export interface Noticia {
  titulo: string;
  imagem: string;
  link:   string;
  tag:    string;
}

export type AbaNoticia = 'ENEM' | 'ENADE';

/** Quantas a tela mostra. */
export const LIMITE_NOTICIAS = 8;
/** Quantas ler de cada feed antes de deduplicar e filtrar. */
export const POR_FEED = 12;

const CACHE_TTL = 4 * 60 * 60 * 1000;   // 4 h
// v8: o formato mudou (junta as fontes), então a chave muda junto — senão
// o cache antigo continuaria servindo a lista repetida.
const cacheKey = (tab: string) => `@noticias_v8_${tab}`;

/** Imagens de reserva, para feed que não traz imagem própria. */
export const FALLBACK_IMGS = [
  'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400',
  'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400',
  'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400',
  'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400',
  'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?w=400',
];
export const variantImg = (i: number) => FALLBACK_IMGS[i % FALLBACK_IMGS.length];

// ── FONTES ───────────────────────────────────────────────────────────────────
//
// ORDEM IMPORTA: específicas primeiro, geral por último.
// O feed de educação da Agência Brasil SAIU: ele responde 404
// (confirmado no log do app, não é CORS — é a URL que não existe mais).
// A cobertura geral foi para uma busca do Google News, que é o mesmo
// mecanismo das outras e não some sem avisar.
export const RSS_SOURCES: Record<AbaNoticia, string[]> = {
  ENEM: [
    'https://news.google.com/rss/search?q=ENEM+INEP+vestibular+prova&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=ENEM+nota+candidatos+educacao&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=ENEM+SISU+inscricao+cronograma&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=educacao+ensino+medio+MEC&hl=pt-BR&gl=BR&ceid=BR:pt',
  ],
  ENADE: [
    'https://news.google.com/rss/search?q=ENADE+MEC+avaliacao+cursos&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=ENADE+ensino+superior+universidade&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=ENADE+resultado+nota+curso&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=ensino+superior+MEC+universidade+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt',
    'https://news.google.com/rss/search?q=educacao+superior+graduacao+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt',
  ],
};

/** Busca ampla — passa pelo filtro de assunto antes de entrar. */
export const ehFeedGeral = (url: string) =>
  url.includes('q=educacao+ensino+medio') || url.includes('q=educacao+superior');

/** Palavras que tornam a matéria relevante para a aba. */
export const PALAVRAS_DA_ABA: Record<AbaNoticia, string[]> = {
  ENEM:  ['enem', 'sisu', 'prouni', 'fies', 'inep', 'vestibular', 'redacao',
          'ensino medio'],
  ENADE: ['enade', 'mec', 'ensino superior', 'universidade', 'faculdade',
          'graduacao', 'curso superior', 'inep'],
};

// ── TEXTO ────────────────────────────────────────────────────────────────────

export const semAcento = (t: string) =>
  String(t).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

export function combinaComAba(titulo: string, tab: AbaNoticia): boolean {
  const t = semAcento(titulo);
  return (PALAVRAS_DA_ABA[tab] ?? []).some(p => t.includes(p));
}

/**
 * Chave de comparação do título.
 *
 * Tira o sufixo do veículo ("... - G1", "... | Folha"), que muda de fonte
 * para fonte na MESMA matéria, e normaliza acento e espaço.
 */
export function chaveTitulo(titulo: string): string {
  // Corta no ÚLTIMO separador, não no primeiro: o veículo fica no fim, e
  // título de Google News costuma ter hífen no meio. Cortando no primeiro,
  // "ENEM 2026 - inscrições abertas - G1" e "ENEM 2026 - gabarito sai hoje
  // - Folha" viravam a mesma chave "enem 2026", e a segunda era descartada
  // como repetida.
  let limpo = String(titulo);
  for (const sep of [' - ', ' | ']) {
    const i = limpo.lastIndexOf(sep);
    if (i > 0) limpo = limpo.slice(0, i);
  }
  return semAcento(limpo).replace(/\s+/g, ' ');
}

/** Link sem query string: utm_source muda entre agregadores. */
export function chaveLink(link: string): string {
  return String(link || '').split('?')[0].replace(/\/+$/, '');
}

// ── PARSER ───────────────────────────────────────────────────────────────────

export function parseRSSXML(xml: string, tab: string): Noticia[] {
  const items: Noticia[] = [];
  const blocks = xml.match(/<item>([\s\S]*?)<\/item>/g) ?? [];

  for (let i = 0; i < Math.min(blocks.length, POR_FEED); i++) {
    const block = blocks[i];
    const titleMatch = block.match(/<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/);
    const titulo = titleMatch?.[1]?.trim()
      .replace(/&amp;/g, '&').replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>').replace(/&quot;/g, '"') ?? '';
    if (!titulo) continue;

    const linkMatch = block.match(/<link>([\s\S]*?)<\/link>/)
      ?? block.match(/<guid[^>]*>([\s\S]*?)<\/guid>/);
    const link = linkMatch?.[1]?.trim() ?? '';

    const imgMatch =
      block.match(/media:content[^>]*url="([^"]+)"/)
      ?? block.match(/media:thumbnail[^>]*url="([^"]+)"/)
      ?? block.match(/enclosure[^>]*url="([^"']+)"/);

    // Sem imagem própria fica vazio: quem escolhe a de reserva é a junção,
    // que conhece a posição final do item.
    items.push({ titulo, link, imagem: imgMatch?.[1] ?? '', tag: tab });
  }
  return items;
}

// ── JUNÇÃO ───────────────────────────────────────────────────────────────────

/** Injetável para teste. */
export type Buscador = (url: string) => Promise<string | null>;

const buscarXml: Buscador = async (url) => {
  try {
    const res = await fetch(url, {
      headers: { Accept: 'application/rss+xml, application/xml, text/xml, */*' },
    });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
};

/**
 * Percorre TODAS as fontes da aba, junta e remove repetição.
 *
 * Uma fonte que falhe (rede, CORS, feed fora do ar) apenas não contribui —
 * as outras seguem.
 */
export async function buscarViaRSS(
  tab: AbaNoticia,
  buscador: Buscador = buscarXml,
): Promise<Noticia[]> {
  const reunidas: Noticia[] = [];
  const titulos = new Set<string>();
  const links   = new Set<string>();

  for (const url of RSS_SOURCES[tab] ?? []) {
    if (reunidas.length >= LIMITE_NOTICIAS) break;

    const xml = await buscador(url);
    if (!xml) continue;

    for (const item of parseRSSXML(xml, tab)) {
      if (reunidas.length >= LIMITE_NOTICIAS) break;

      // O feed geral só entra se a matéria for do assunto da aba.
      if (ehFeedGeral(url) && !combinaComAba(item.titulo, tab)) continue;

      const kt = chaveTitulo(item.titulo);
      const kl = chaveLink(item.link);
      if (!kt || titulos.has(kt)) continue;
      if (kl && links.has(kl)) continue;

      titulos.add(kt);
      if (kl) links.add(kl);
      reunidas.push({ ...item, imagem: item.imagem || variantImg(reunidas.length) });
    }
  }
  return reunidas;
}

//
// Só entra quando o RSS não trouxe nada: tem cota diária pequena.


// buscarViaGNews foi REMOVIDA daqui.
//
// Ela chamava gnews.io direto do aplicativo, com a chave vinda do .env —
// e chave empacotada no aplicativo é chave pública: qualquer um extrai do
// APK e passa a gastar a sua cota.
//
// Quem fala com o GNews agora é o noticias_api.py, no servidor, com a
// chave numa variável de ambiente. O aplicativo chama o servidor
// (buscarViaProxy, logo acima) e de quebra aproveita o cache de 8 h, que
// serve todos os aparelhos com uma consulta só.
//
// Se um dia alguém for tentado a trazer isto de volta: o problema não é o
// GNews, é o lugar da chave. Não tem como esconder segredo no cliente.

// ── PROXY ────────────────────────────────────────────────────────────────────

/** Categoria do noticias_api.py correspondente à aba. */
const CATEGORIA_PROXY: Record<AbaNoticia, string> = {
  ENEM:  'enem',
  ENADE: 'enade',
};

/**
 * Busca pelo noticias_api.py. Devolve [] se ele não estiver no ar.
 *
 * Timeout curto de propósito: se o proxy não responder, o celular ainda
 * tem o caminho direto, e não faz sentido travar a home esperando.
 */
async function _tentarBase(base: string, tab: AbaNoticia): Promise<Noticia[]> {
  const controle = new AbortController();
  const timer = setTimeout(() => controle.abort(), 12000);
  try {
    // A rota curta (/enade) é a que existe quando o módulo está montado
    // na API publicada. Rodando o arquivo sozinho, ela também responde.
    const url = `${base}/${CATEGORIA_PROXY[tab]}?quantidade=${LIMITE_NOTICIAS}`;
    const res = await fetch(url, { signal: controle.signal });
    if (!res.ok) return [];
    const dados = await res.json();
    const lista = Array.isArray(dados?.noticias) ? dados.noticias : [];
    return lista.map((n: any, i: number) => ({
      titulo: n?.titulo ?? '',
      imagem: n?.imagem || variantImg(i),
      link:   n?.link ?? '',
      tag:    tab,
    })).filter((n: Noticia) => n.titulo);
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}

export async function buscarViaProxy(
  tab: AbaNoticia,
  base: string | null = proxyBase,
): Promise<Noticia[]> {
  if (base) {
    const r = await _tentarBase(base, tab);
    if (r.length) return r;
  }
  // Em desenvolvimento, cai para o publicado se o uvicorn local não subiu.
  if (PROXY_RESERVA && PROXY_RESERVA !== base) {
    return _tentarBase(PROXY_RESERVA, tab);
  }
  return [];
}

/** No navegador o RSS direto é sempre bloqueado — nem tenta. */
export const rssDiretoFunciona = Platform.OS !== 'web';

// ── CACHE ────────────────────────────────────────────────────────────────────

export async function lerCache(tab: string): Promise<Noticia[] | null> {
  try {
    const raw = await AsyncStorage.getItem(cacheKey(tab));
    if (!raw) return null;
    const { ts, data } = JSON.parse(raw);
    if (Array.isArray(data) && data.length >= 2 && Date.now() - ts < CACHE_TTL) {
      return data;
    }
  } catch {}
  return null;
}

export async function gravarCache(tab: string, data: Noticia[]): Promise<void> {
  try {
    await AsyncStorage.setItem(cacheKey(tab), JSON.stringify({ ts: Date.now(), data }));
  } catch {}
}

export async function limparCache(tab?: string): Promise<void> {
  try {
    if (tab) await AsyncStorage.removeItem(cacheKey(tab));
    else await Promise.all(['ENEM', 'ENADE'].map(t => AsyncStorage.removeItem(cacheKey(t))));
  } catch {}
}
