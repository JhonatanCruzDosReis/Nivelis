/**
 * livrosData.ts
 * Curated book recommendations separated by ENEM and ENADE.
 */

export interface Livro {
  id: string;
  titulo: string;
  autor: string;
  editora: string;
  materia: string;          // Subject / area label
  tipo: 'ENEM' | 'ENADE';
  area?: string;            // For ENADE: Exatas | Humanas | Saúde | Tecnologia | Direito | Agro
  capa: string;             // Image URL
  descricao: string;
  paginas: number;
  link: string;             // Google Books or publisher URL
}

// ─── ENEM ────────────────────────────────────────────────────────────────────

export const LIVROS_ENEM: Livro[] = [
  // Linguagens
  {
    id: 'enem_l1',
    titulo: 'Gramática da Língua Portuguesa',
    autor: 'Pasquale Cipro Neto & Ulisses Infante',
    editora: 'Scipione',
    materia: 'LINGUAGENS',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?q=80&w=400',
    descricao: 'Obra de referência para quem quer dominar gramática normativa, interpretação e produção textual. Aborda todos os tópicos cobrados no ENEM com exemplos práticos e exercícios.',
    paginas: 530,
    link: 'https://www.google.com.br/search?q=Gram%C3%A1tica+da+L%C3%ADngua+Portuguesa+Pasquale+livro',
  },
  {
    id: 'enem_l2',
    titulo: 'Literatura Brasileira — Textos e Contextos',
    autor: 'Leodegário A. de Azevedo Filho',
    editora: 'Ática',
    materia: 'LINGUAGENS',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1512820790803-83ca734da794?q=80&w=400',
    descricao: 'Percurso completo pela literatura brasileira do Quinhentismo ao Modernismo, com fragmentos de obras originais, análises e questões no estilo ENEM.',
    paginas: 480,
    link: 'https://www.google.com.br/search?q=Literatura+Brasileira+Textos+Contextos+livro',
  },
  // Matemática
  {
    id: 'enem_m1',
    titulo: 'Matemática — Ensino Médio Completo',
    autor: 'Gelson Iezzi',
    editora: 'Atual',
    materia: 'MATEMÁTICA',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?q=80&w=400',
    descricao: 'Coleção clássica que cobre álgebra, geometria, trigonometria, probabilidade e estatística. Cada capítulo termina com exercícios no padrão ENEM.',
    paginas: 600,
    link: 'https://www.google.com.br/search?q=Matematica+Ensino+Medio+Gelson+Iezzi+livro',
  },
  {
    id: 'enem_m2',
    titulo: 'Matemática ENEM — Guia Definitivo',
    autor: 'Leonardo Miguez',
    editora: 'Vestibulando Digital',
    materia: 'MATEMÁTICA',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=400',
    descricao: 'Resolução comentada das questões de matemática dos últimos 10 anos do ENEM, com estratégias de resolução rápida e eliminação de alternativas.',
    paginas: 320,
    link: 'https://www.google.com.br/search?q=Matematica+ENEM+Guia+Definitivo+livro',
  },
  // Ciências Humanas
  {
    id: 'enem_h1',
    titulo: 'História Geral e do Brasil',
    autor: 'Cláudio Vicentino & Gianpaolo Dorigo',
    editora: 'Scipione',
    materia: 'CIÊNCIAS HUMANAS',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1524666643752-b381eb00effb?q=80&w=400',
    descricao: 'Do surgimento das civilizações antigas até a história contemporânea do Brasil, com ênfase nos temas mais cobrados no ENEM: ditaduras, movimentos sociais e globalização.',
    paginas: 700,
    link: 'https://www.google.com.br/search?q=Hist%C3%B3ria+Geral+Brasil+Vicentino+Dorigo+livro',
  },
  {
    id: 'enem_h2',
    titulo: 'Geografia — Espaço e Sociedade',
    autor: 'Eustáquio de Sene & João Carlos Moreira',
    editora: 'Scipione',
    materia: 'CIÊNCIAS HUMANAS',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1521295121783-8a321d551ad2?q=80&w=400',
    descricao: 'Abordagem completa de geografia física, humana e econômica com ênfase em temas atuais: meio ambiente, urbanização, globalização e geopolítica.',
    paginas: 520,
    link: 'https://www.google.com.br/search?q=Geografia+Espa%C3%A7o+Sociedade+Sene+Moreira+livro',
  },
  // Ciências da Natureza
  {
    id: 'enem_n1',
    titulo: 'Física Conceitual',
    autor: 'Paul G. Hewitt',
    editora: 'Bookman',
    materia: 'CIÊNCIAS DA NATUREZA',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1446776877081-d282a0f896e2?q=80&w=400',
    descricao: 'A obra mais acessível para aprender física sem medo: explica cada conceito com analogias do cotidiano antes de apresentar equações. Perfeito para o estilo ENEM.',
    paginas: 740,
    link: 'https://www.google.com.br/search?q=F%C3%ADsica+Conceitual+Paul+Hewitt+livro',
  },
  {
    id: 'enem_n2',
    titulo: 'Química — A Ciência Central',
    autor: 'Theodore L. Brown',
    editora: 'Pearson',
    materia: 'CIÊNCIAS DA NATUREZA',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?q=80&w=400',
    descricao: 'Referência global para o ensino de química geral e orgânica. Cobre reações, ligações, equilíbrio e eletroquímica com muitos exercícios contextualizados.',
    paginas: 850,
    link: 'https://www.google.com.br/search?q=Qu%C3%ADmica+Ci%C3%AAncia+Central+Brown+livro',
  },
  {
    id: 'enem_n3',
    titulo: 'Biologia Moderna',
    autor: 'José Mariano Amabis & Gilberto Rodrigues Martho',
    editora: 'Moderna',
    materia: 'CIÊNCIAS DA NATUREZA',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1530026405186-ed1f139313f8?q=80&w=400',
    descricao: 'Biologia do nível celular ao ecossistema: genética, evolução, ecologia, botânica e zoologia. Ideal para questões de biologia e ciências ambientais do ENEM.',
    paginas: 660,
    link: 'https://www.google.com.br/search?q=Biologia+Moderna+Amabis+Martho+livro',
  },
  // Redação
  {
    id: 'enem_r1',
    titulo: 'Redação Nota Mil',
    autor: 'Luciana Bártoli',
    editora: 'Gente',
    materia: 'REDAÇÃO',
    tipo: 'ENEM',
    capa: 'https://images.unsplash.com/photo-1455390207574-4f4ae6cd0a41?q=80&w=400',
    descricao: 'Guia prático para atingir a nota máxima na redação do ENEM: estrutura dissertativa-argumentativa, repertórios culturais, proposta de intervenção e competências avaliadas.',
    paginas: 280,
    link: 'https://www.google.com.br/search?q=Reda%C3%A7%C3%A3o+Nota+Mil+Luciana+Bartoli+livro',
  },
];

// ─── ENADE ───────────────────────────────────────────────────────────────────

export const LIVROS_ENADE: Livro[] = [
  // Exatas
  {
    id: 'enade_e1',
    titulo: 'Cálculo — Volume 1',
    autor: 'James Stewart',
    editora: 'Cengage',
    materia: 'Cálculo',
    tipo: 'ENADE',
    area: 'Exatas',
    capa: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=400',
    descricao: 'O livro de cálculo diferencial e integral mais adotado nas universidades brasileiras. Cobre limites, derivadas, integrais e séries com rigor matemático e muitas aplicações.',
    paginas: 900,
    link: 'https://www.google.com.br/search?q=C%C3%A1lculo+James+Stewart+Volume+1+livro',
  },
  {
    id: 'enade_e2',
    titulo: 'Fundamentos de Física — Vol. 1 e 2',
    autor: 'Halliday, Resnick & Krane',
    editora: 'LTC',
    materia: 'Física',
    tipo: 'ENADE',
    area: 'Exatas',
    capa: 'https://images.unsplash.com/photo-1446776877081-d282a0f896e2?q=80&w=400',
    descricao: 'Referência mundial para física universitária. Mecânica, termodinâmica, eletricidade, magnetismo e óptica com enunciados e resolução detalhada.',
    paginas: 760,
    link: 'https://www.google.com.br/search?q=Fundamentos+de+F%C3%ADsica+Halliday+Resnick+livro',
  },
  {
    id: 'enade_e3',
    titulo: 'Álgebra Linear com Aplicações',
    autor: 'Howard Anton & Chris Rorres',
    editora: 'Bookman',
    materia: 'Álgebra Linear',
    tipo: 'ENADE',
    area: 'Exatas',
    capa: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?q=80&w=400',
    descricao: 'Matrizes, determinantes, espaços vetoriais, transformações lineares e autovalores. Muito cobrado no ENADE de Engenharia, Matemática e Computação.',
    paginas: 650,
    link: 'https://www.google.com.br/search?q=Álgebra+Linear+Anton+Rorres+livro',
  },
  // Saúde
  {
    id: 'enade_s1',
    titulo: 'Fisiologia Humana — Uma Abordagem Integrada',
    autor: 'Dee Unglaub Silverthorn',
    editora: 'Artmed',
    materia: 'Fisiologia',
    tipo: 'ENADE',
    area: 'Saúde',
    capa: 'https://images.unsplash.com/photo-1530026405186-ed1f139313f8?q=80&w=400',
    descricao: 'Texto de fisiologia humana com enfoque sistêmico e integrado. Cobre sistemas nervoso, cardiovascular, respiratório, renal, endócrino e reprodutor com clareza didática.',
    paginas: 950,
    link: 'https://www.google.com.br/search?q=Fisiologia+Humana+Silverthorn+livro',
  },
  {
    id: 'enade_s2',
    titulo: 'Bioquímica — Lehninger',
    autor: 'David L. Nelson & Michael M. Cox',
    editora: 'Artmed',
    materia: 'Bioquímica',
    tipo: 'ENADE',
    area: 'Saúde',
    capa: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?q=80&w=400',
    descricao: 'A bíblia da bioquímica universitária: metabolismo, enzimologia, biologia molecular e sinalização celular. Essencial para Medicina, Farmácia, Nutrição e Enfermagem.',
    paginas: 1300,
    link: 'https://www.google.com.br/search?q=Bioqu%C3%ADmica+Lehninger+Nelson+Cox+livro',
  },
  // Humanas / Sociais
  {
    id: 'enade_hu1',
    titulo: 'Introdução ao Estudo do Direito',
    autor: 'Paulo Nader',
    editora: 'Forense',
    materia: 'Direito',
    tipo: 'ENADE',
    area: 'Humanas',
    capa: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?q=80&w=400',
    descricao: 'Base filosófica e técnica para qualquer curso jurídico: fontes do direito, norma jurídica, interpretação, lacunas e relações do direito com outras ciências sociais.',
    paginas: 380,
    link: 'https://www.google.com.br/search?q=Introdu%C3%A7%C3%A3o+Estudo+Direito+Paulo+Nader+livro',
  },
  {
    id: 'enade_hu2',
    titulo: 'Administração — Teoria, Processo e Prática',
    autor: 'Idalberto Chiavenato',
    editora: 'Manole',
    materia: 'Administração',
    tipo: 'ENADE',
    area: 'Humanas',
    capa: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=400',
    descricao: 'Clássico da administração brasileira: evolução das teorias administrativas, planejamento, organização, liderança, controle e empreendedorismo.',
    paginas: 510,
    link: 'https://www.google.com.br/search?q=Administra%C3%A7%C3%A3o+Chiavenato+livro',
  },
  // Tecnologia
  {
    id: 'enade_t1',
    titulo: 'Estruturas de Dados e Algoritmos em Java',
    autor: 'Robert Lafore',
    editora: 'Ciência Moderna',
    materia: 'Computação',
    tipo: 'ENADE',
    area: 'Tecnologia',
    capa: 'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?q=80&w=400',
    descricao: 'Estruturas de dados (listas, pilhas, filas, árvores, grafos) e algoritmos de ordenação e busca implementados em Java. Essencial para ENADE de Computação e Sistemas.',
    paginas: 680,
    link: 'https://www.google.com.br/search?q=Estruturas+Dados+Algoritmos+Java+Lafore+livro',
  },
  {
    id: 'enade_t2',
    titulo: 'Redes de Computadores',
    autor: 'Andrew S. Tanenbaum',
    editora: 'Pearson',
    materia: 'Redes',
    tipo: 'ENADE',
    area: 'Tecnologia',
    capa: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?q=80&w=400',
    descricao: 'Do modelo OSI ao TCP/IP, passando por redes sem fio, segurança, camada de aplicação e protocolos modernos. Referência obrigatória para ENADE de Computação.',
    paginas: 950,
    link: 'https://www.google.com.br/search?q=Redes+de+Computadores+Tanenbaum+livro',
  },
];

export const AREAS_ENADE = ['Todas', 'Exatas', 'Saúde', 'Humanas', 'Tecnologia'];
export const MATERIAS_ENEM = ['Todas', 'LINGUAGENS', 'MATEMÁTICA', 'CIÊNCIAS HUMANAS', 'CIÊNCIAS DA NATUREZA', 'REDAÇÃO'];
