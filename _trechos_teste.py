"""Trechos sintéticos que imitam o formato salvo pelo indexar_livro."""

TRECHOS_TESTE = [
    {
        "trecho_id": "abc12345-01", "capitulo": 1, "pagina": 23,
        "livro_titulo": "Fundamentos da Saúde Coletiva", "livro_autor": "M. Almeida",
        "texto": ("A vigilância epidemiológica não se resume à coleta de dados sobre "
                  "doenças notificáveis. Seu propósito é gerar informação capaz de "
                  "orientar decisões sanitárias em tempo hábil. Um sistema que acumula "
                  "registros sem devolvê-los ao serviço que os produziu perde sua "
                  "razão de existir, pois converte em burocracia aquilo que deveria "
                  "ser instrumento de ação."),
        "tese": "A vigilância epidemiológica só cumpre sua função quando a informação retorna ao serviço e orienta decisões",
        "pressupostos": ["Os serviços de saúde tomam decisões com base em informação sistematizada",
                         "A notificação de doenças por si só não altera a prática sanitária"],
        "ideia_secundaria": "Um sistema que apenas acumula registros transforma-se em burocracia",
        "afirmacoes_falsas": ["A vigilância epidemiológica limita-se à coleta de dados de notificação compulsória",
                              "O acúmulo de registros é o principal objetivo dos sistemas de informação em saúde",
                              "A devolução de dados aos serviços é dispensável quando a notificação é regular"],
    },
    {
        "trecho_id": "abc12345-02", "capitulo": 2, "pagina": 47,
        "livro_titulo": "Fundamentos da Saúde Coletiva", "livro_autor": "M. Almeida",
        "texto": ("A determinação social da saúde desloca o foco da explicação "
                  "individual para as condições em que as pessoas vivem e trabalham. "
                  "Atribuir o adoecimento exclusivamente a escolhas pessoais ignora "
                  "que essas escolhas são feitas dentro de margens estreitas, "
                  "definidas por renda, moradia e acesso a serviços."),
        "tese": "O adoecimento resulta das condições de vida e trabalho, não apenas de escolhas individuais",
        "pressupostos": ["As escolhas individuais são limitadas por condições materiais",
                         "Renda e moradia influenciam o estado de saúde da população"],
        "ideia_secundaria": "As margens de escolha das pessoas são estreitadas por renda, moradia e acesso a serviços",
        "afirmacoes_falsas": ["O estado de saúde depende exclusivamente de decisões pessoais de cada indivíduo",
                              "Condições de moradia e renda têm efeito irrelevante sobre o adoecimento",
                              "A explicação individual é suficiente para compreender os padrões de doença"],
    },
    {
        "trecho_id": "abc12345-03", "capitulo": 3, "pagina": 68,
        "livro_titulo": "Fundamentos da Saúde Coletiva", "livro_autor": "M. Almeida",
        "texto": ("A integralidade não significa oferecer todos os procedimentos "
                  "disponíveis a todos os usuários. Significa organizar o cuidado de "
                  "modo que a pessoa seja acompanhada em suas necessidades reais, "
                  "articulando prevenção, tratamento e reabilitação. Confundir "
                  "integralidade com quantidade de exames é esvaziar o princípio."),
        "tese": "A integralidade consiste em organizar o cuidado conforme as necessidades reais da pessoa",
        "pressupostos": ["Nem todo procedimento disponível é necessário para cada usuário",
                         "O cuidado em saúde envolve etapas articuladas entre si"],
        "ideia_secundaria": "Confundir integralidade com quantidade de exames esvazia o princípio",
        "afirmacoes_falsas": ["A integralidade exige a oferta de todos os procedimentos a todos os usuários",
                              "O número de exames realizados mede o grau de integralidade do serviço",
                              "Prevenção e reabilitação são etapas independentes que não se articulam"],
    },
    {
        "trecho_id": "abc12345-04", "capitulo": 4, "pagina": 92,
        "livro_titulo": "Fundamentos da Saúde Coletiva", "livro_autor": "M. Almeida",
        "texto": ("O rastreamento populacional só se justifica quando a detecção "
                  "precoce altera o desfecho da doença. Rastrear condições para as "
                  "quais não há tratamento eficaz produz diagnóstico sem benefício e "
                  "expõe pessoas saudáveis a procedimentos desnecessários."),
        "tese": "O rastreamento populacional se justifica apenas quando a detecção precoce muda o desfecho",
        "pressupostos": ["Existem condições para as quais o diagnóstico precoce não traz benefício",
                         "Procedimentos diagnósticos têm riscos associados"],
        "ideia_secundaria": "Rastrear sem tratamento eficaz expõe pessoas saudáveis a procedimentos desnecessários",
        "afirmacoes_falsas": ["Todo rastreamento populacional é benéfico independentemente do tratamento disponível",
                              "A detecção precoce sempre melhora o prognóstico de qualquer condição",
                              "Procedimentos diagnósticos não apresentam riscos aos indivíduos saudáveis"],
    },
    {
        "trecho_id": "abc12345-05", "capitulo": 5, "pagina": 115,
        "livro_titulo": "Fundamentos da Saúde Coletiva", "livro_autor": "M. Almeida",
        "texto": ("A participação social no SUS não é um adorno democrático. Os "
                  "conselhos de saúde exercem função deliberativa prevista em lei, e "
                  "esvaziá-los reduz o controle público sobre a aplicação de recursos "
                  "que pertencem à sociedade."),
        "tese": "Os conselhos de saúde exercem função deliberativa e são instrumento de controle público",
        "pressupostos": ["Os recursos do sistema de saúde são de natureza pública",
                         "A participação prevista em lei tem efeito prático sobre a gestão"],
        "ideia_secundaria": "Esvaziar os conselhos reduz o controle público sobre a aplicação de recursos",
        "afirmacoes_falsas": ["A participação social no SUS tem caráter meramente simbólico",
                              "Os conselhos de saúde possuem função apenas consultiva",
                              "O controle sobre recursos públicos independe da participação da sociedade"],
    },
]
