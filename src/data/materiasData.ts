// ─────────────────────────────────────────────────────────────────────────────
// Dados das matérias com associação a vídeos
//
// Como adicionar um vídeo do YouTube:
//   1. Pegue o link: https://youtube.com/watch?v=XXXXXXXXXXX
//   2. Cole apenas o XXXXXXXXXXX no campo videoId
//   3. Tipo: 'youtube'
//
// Como adicionar um vídeo do Google Drive:
//   1. Compartilhe como "Qualquer pessoa com o link"
//   2. Link: https://drive.google.com/file/d/XXXXXXXX/view
//   3. Cole apenas o XXXXXXXX no campo videoId
//   4. Tipo: 'drive'
//
// videoId: null  →  exibe "Em Produção"
// ─────────────────────────────────────────────────────────────────────────────

export interface Aula {
  id: string;
  titulo: string;
  duracao: string;
  videoId: string | null;
  videoTipo?: 'youtube' | 'drive';
}

export interface Subtopico {
  id: string;
  nome: string;
  aulas: Aula[];
}

export interface Materia {
  id: string;
  nome: string;
  icone: string;       // Nome do ícone FontAwesome5
  cor: string;         // Cor principal da matéria
  subtopicos: Subtopico[];
}

export const MATERIAS: Materia[] = [
  {
    id: 'mat',
    nome: 'Matemática',
    icone: 'calculator',
    cor: '#4F46E5',
    subtopicos: [
      {
        id: 'mat_alg',
        nome: 'ÁLGEBRA',
        aulas: [
          { id: 'mat_alg_1', titulo: 'Equações do 2º Grau — Parte 1', duracao: '15 min', videoId: '1CJku5XQuq2FtxYoyIsSpQ3CZEGUgoFXM', videoTipo: 'drive' },
          { id: 'mat_alg_2', titulo: 'Equações do 2º Grau — Parte 2', duracao: '18 min', videoId: null },
          { id: 'mat_alg_3', titulo: 'Função Exponencial',            duracao: '20 min', videoId: null },
          { id: 'mat_alg_4', titulo: 'Função Logarítmica',            duracao: '22 min', videoId: null },
        ],
      },
      {
        id: 'mat_geo',
        nome: 'GEOMETRIA',
        aulas: [
          { id: 'mat_geo_1', titulo: 'Geometria Plana — Áreas',    duracao: '25 min', videoId: null },
          { id: 'mat_geo_2', titulo: 'Geometria Espacial — Volume', duracao: '18 min', videoId: null },
          { id: 'mat_geo_3', titulo: 'Trigonometria Básica',        duracao: '30 min', videoId: null },
        ],
      },
      {
        id: 'mat_est',
        nome: 'ESTATÍSTICA',
        aulas: [
          { id: 'mat_est_1', titulo: 'Média, Moda e Mediana', duracao: '14 min', videoId: null },
          { id: 'mat_est_2', titulo: 'Probabilidade',         duracao: '20 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'port',
    nome: 'Português',
    icone: 'book-open',
    cor: '#7D53DD',
    subtopicos: [
      {
        id: 'port_gram',
        nome: 'GRAMÁTICA',
        aulas: [
          { id: 'port_gram_1', titulo: 'Classes de Palavras',     duracao: '22 min', videoId: null },
          { id: 'port_gram_2', titulo: 'Crase: Regras Gerais',    duracao: '15 min', videoId: null },
          { id: 'port_gram_3', titulo: 'Concordância Verbal',     duracao: '18 min', videoId: null },
          { id: 'port_gram_4', titulo: 'Regência Verbal e Nominal', duracao: '20 min', videoId: null },
        ],
      },
      {
        id: 'port_lit',
        nome: 'LITERATURA',
        aulas: [
          { id: 'port_lit_1', titulo: 'Realismo — Machado de Assis', duracao: '30 min', videoId: null },
          { id: 'port_lit_2', titulo: 'Modernismo Brasileiro',       duracao: '25 min', videoId: null },
        ],
      },
      {
        id: 'port_red',
        nome: 'REDAÇÃO',
        aulas: [
          { id: 'port_red_1', titulo: 'Estrutura da Dissertação',   duracao: '20 min', videoId: null },
          { id: 'port_red_2', titulo: 'Proposta de Intervenção',    duracao: '15 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'hist',
    nome: 'História',
    icone: 'history',
    cor: '#F59E0B',
    subtopicos: [
      {
        id: 'hist_br',
        nome: 'HISTÓRIA DO BRASIL',
        aulas: [
          { id: 'hist_br_1', titulo: 'Período Colonial',    duracao: '20 min', videoId: null },
          { id: 'hist_br_2', titulo: 'Era Vargas',          duracao: '25 min', videoId: null },
          { id: 'hist_br_3', titulo: 'Ditadura Militar',    duracao: '22 min', videoId: null },
        ],
      },
      {
        id: 'hist_geral',
        nome: 'HISTÓRIA GERAL',
        aulas: [
          { id: 'hist_geral_1', titulo: 'Revolução Francesa',   duracao: '20 min', videoId: null },
          { id: 'hist_geral_2', titulo: 'Primeira Guerra Mundial', duracao: '18 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'geo',
    nome: 'Geografia',
    icone: 'globe-americas',
    cor: '#10B981',
    subtopicos: [
      {
        id: 'geo_fis',
        nome: 'GEOGRAFIA FÍSICA',
        aulas: [
          { id: 'geo_fis_1', titulo: 'Climatologia Básica', duracao: '18 min', videoId: null },
          { id: 'geo_fis_2', titulo: 'Geomorfologia',       duracao: '20 min', videoId: null },
        ],
      },
      {
        id: 'geo_hum',
        nome: 'GEOGRAFIA HUMANA',
        aulas: [
          { id: 'geo_hum_1', titulo: 'Urbanização Brasileira', duracao: '22 min', videoId: null },
          { id: 'geo_hum_2', titulo: 'Globalização',           duracao: '16 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'fis',
    nome: 'Física',
    icone: 'atom',
    cor: '#3B82F6',
    subtopicos: [
      {
        id: 'fis_mec',
        nome: 'MECÂNICA',
        aulas: [
          { id: 'fis_mec_1', titulo: 'Leis de Newton',         duracao: '25 min', videoId: null },
          { id: 'fis_mec_2', titulo: 'Energia e Trabalho',     duracao: '20 min', videoId: null },
          { id: 'fis_mec_3', titulo: 'Momento e Impulso',      duracao: '18 min', videoId: null },
        ],
      },
      {
        id: 'fis_elet',
        nome: 'ELETROMAGNETISMO',
        aulas: [
          { id: 'fis_elet_1', titulo: 'Eletrostática',  duracao: '22 min', videoId: null },
          { id: 'fis_elet_2', titulo: 'Circuitos Elétricos', duracao: '28 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'qui',
    nome: 'Química',
    icone: 'flask',
    cor: '#EC4899',
    subtopicos: [
      {
        id: 'qui_geral',
        nome: 'QUÍMICA GERAL',
        aulas: [
          { id: 'qui_geral_1', titulo: 'Tabela Periódica',   duracao: '15 min', videoId: null },
          { id: 'qui_geral_2', titulo: 'Ligações Químicas',  duracao: '20 min', videoId: null },
        ],
      },
      {
        id: 'qui_org',
        nome: 'QUÍMICA ORGÂNICA',
        aulas: [
          { id: 'qui_org_1', titulo: 'Hidrocarbonetos',  duracao: '18 min', videoId: null },
          { id: 'qui_org_2', titulo: 'Funções Orgânicas', duracao: '22 min', videoId: null },
        ],
      },
    ],
  },
  {
    id: 'bio',
    nome: 'Biologia',
    icone: 'leaf',
    cor: '#22C55E',
    subtopicos: [
      {
        id: 'bio_cel',
        nome: 'CITOLOGIA',
        aulas: [
          { id: 'bio_cel_1', titulo: 'Organelas Celulares', duracao: '20 min', videoId: null },
          { id: 'bio_cel_2', titulo: 'Mitose e Meiose',     duracao: '18 min', videoId: null },
        ],
      },
      {
        id: 'bio_gen',
        nome: 'GENÉTICA',
        aulas: [
          { id: 'bio_gen_1', titulo: 'Leis de Mendel',    duracao: '22 min', videoId: null },
          { id: 'bio_gen_2', titulo: 'DNA e RNA',         duracao: '20 min', videoId: null },
        ],
      },
    ],
  },
];
