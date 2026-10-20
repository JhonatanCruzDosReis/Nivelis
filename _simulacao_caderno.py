"""
Trechos REAIS do Caderno de Atenção Básica nº 28 (Acolhimento à Demanda
Espontânea), com a análise que o Gemini produziu na indexação do Nicolas.

Serve para reproduzir localmente o comportamento do gerador com material
de produção, sem depender de chave de API nem de acesso ao Firestore.
"""

TRECHOS_CADERNO = [
    {
        "trecho_id": "cad-01",
        "capitulo": 1, "pagina": 22,
        "texto": (
            "Existem várias definições de acolhimento, tanto nos dicionários "
            "quanto em setores como a saúde. A existência de várias definições "
            "revela os múltiplos sentidos e significados atribuídos a esse "
            "termo, de maneira legítima, como pretensões de verdade. Ou seja, o "
            "mais importante não é a busca pela definição correta ou verdadeira "
            "de acolhimento, mas a clareza e explicitação da noção de "
            "acolhimento que é adotada ou assumida situacionalmente por atores "
            "concretos, revelando perspectivas e intencionalidades. Em outras "
            "palavras, ele não é, a priori, algo bom ou ruim, mas sim uma "
            "prática constitutiva das relações de cuidado. O acolhimento se "
            "revela menos no discurso sobre ele do que nas práticas concretas."),
        "tese": "O mais importante sobre o acolhimento não é encontrar uma definição única",
        "pressupostos": [
            "O termo acolhimento possui múltiplos significados legítimos",
            "As práticas concretas revelam mais que o discurso sobre elas"],
        "ideia_secundaria": "A análise do acolhimento deve focar em como ele se manifesta nas práticas",
        "afirmacoes_falsas": [
            "A definição correta de acolhimento é o aspecto mais crucial a ser buscado",
            "O discurso sobre acolhimento é mais revelador do que as práticas concretas",
            "O acolhimento é uma prática que pode ser intrinsecamente boa ou ruim",
            "A definição correta de acolhimento é universalmente aceita na área da saúde"],
    },
    {
        "trecho_id": "cad-02",
        "capitulo": 3, "pagina": 44,
        "texto": (
            "Na quase totalidade das situações, o primeiro contato dos usuários "
            "que procuram a unidade de Saúde da Família se dá com profissionais "
            "que não tiveram formação específica para atuar na área da saúde. "
            "Isso pode levar as equipes de Saúde da Família e os gestores, por "
            "vezes, a excluírem essas pessoas de momentos de reflexão sobre o "
            "acolhimento. Já foram indicadas situações em que os profissionais "
            "da recepção podem identificar casos de maior risco e "
            "vulnerabilidade e facilitar o acesso dos usuários a uma avaliação "
            "mais rápida por parte de um profissional de saúde. Para isso, esses "
            "trabalhadores deveriam ser envolvidos em reuniões sistemáticas das "
            "unidades."),
        "tese": "Os trabalhadores da recepção têm papel central no acolhimento e devem participar das reflexões da equipe",
        "pressupostos": [
            "Profissionais da recepção desempenham papel importante no primeiro contato",
            "A identificação de risco não depende exclusivamente de formação em saúde"],
        "ideia_secundaria": "Profissionais da recepção podem identificar casos de maior risco e vulnerabilidade",
        "afirmacoes_falsas": [
            "A exclusão dos profissionais da recepção das reflexões é benéfica para o serviço",
            "Profissionais da recepção não podem contribuir para a identificação de riscos",
            "A organização da recepção é responsabilidade exclusiva dos profissionais de saúde",
            "Apenas profissionais de saúde podem identificar riscos e vulnerabilidades"],
    },
    {
        "trecho_id": "cad-03",
        "capitulo": 2, "pagina": 33,
        "texto": (
            "A fila e a cota de consultas do dia, com senhas limitadas, além de "
            "submeterem as pessoas à espera em situação desconfortável e sem "
            "garantia de acesso, são muitas vezes o contrário do princípio da "
            "equidade, na medida em que o critério mais comum de acesso, nesses "
            "casos, é a ordem de chegada. Dessa forma, o acesso com equidade "
            "deve ser uma preocupação constante no acolhimento da demanda "
            "espontânea. A equidade, como princípio de justiça, baseia-se na "
            "premissa de que é preciso tratar diferentemente os desiguais, ou "
            "cada um de acordo com a sua necessidade, corrigindo diferenciações "
            "injustas e negativas."),
        "tese": "O acesso por ordem de chegada contraria a equidade, que exige tratar cada um conforme sua necessidade",
        "pressupostos": [
            "A ordem de chegada nem sempre garante acesso equitativo",
            "Existem diferenças de necessidade entre os usuários que buscam o serviço"],
        "ideia_secundaria": "A diferenciação positiva é uma forma de promover a equidade",
        "afirmacoes_falsas": [
            "A diferenciação positiva é uma prática que prejudica a equidade no acesso",
            "A ordem de chegada é o critério mais justo de acesso ao serviço",
            "A fila com senhas limitadas garante acesso equitativo à população",
            "Tratar todos exatamente da mesma forma é o que define a equidade"],
    },
    {
        "trecho_id": "cad-04",
        "capitulo": 1, "pagina": 20,
        "texto": (
            "Conforme vimos anteriormente, a atenção básica lida com situações e "
            "problemas de saúde de grande variabilidade, desde as mais simples "
            "até as mais complexas, que exigem diferentes tipos de esforços de "
            "suas equipes. Tal complexidade se caracteriza pela exigência de se "
            "considerarem, a todo tempo e de acordo com cada situação, as "
            "dimensões orgânica, subjetiva e social do processo "
            "saúde-doença-cuidado, para que as ações de cuidado possam ter "
            "efetividade. Nesse sentido, a capacidade de acolhida e escuta das "
            "equipes aos pedidos, demandas, necessidades e manifestações dos "
            "usuários é um elemento-chave."),
        "tese": "A variabilidade dos problemas na atenção básica exige equipes com alta capacidade de acolhida e escuta",
        "pressupostos": [
            "A efetividade do cuidado depende de considerar dimensões além da orgânica",
            "Problemas de saúde variam em complexidade dentro da atenção básica"],
        "ideia_secundaria": "A complexidade exige considerar as dimensões orgânica, subjetiva e social",
        "afirmacoes_falsas": [
            "A atenção básica lida apenas com problemas de saúde simples",
            "A efetividade do cuidado não depende das dimensões subjetiva e social",
            "O acolhimento é um elemento secundário na atenção básica",
            "Todas as situações da atenção básica exigem o mesmo tipo de esforço"],
    },
    {
        "trecho_id": "cad-05",
        "capitulo": 3, "pagina": 48,
        "texto": (
            "Se os usuários compreenderem os objetivos do acolhimento e, nas "
            "situações concretas, se sentirem de fato acolhidos, escutados, "
            "cuidados, isso pode facilitar o entendimento de outros e diminuir "
            "algumas tensões. É comum que usuários agendados fiquem irritados "
            "com o fato de alguns pacientes de demanda espontânea serem "
            "priorizados. Essas situações evidenciam a necessidade de haver "
            "conversas entre trabalhadores e usuários sobre o modo de "
            "funcionamento da unidade, em diferentes ocasiões. Acolher a "
            "irritação e ansiedade dos usuários, em vez de reagir, e "
            "problematizá-los sem deslegitimar a manifestação deles são atitudes "
            "que podem facilitar a construção de consensos."),
        "tese": "O diálogo sobre o funcionamento da unidade reduz tensões e constrói consensos com os usuários",
        "pressupostos": [
            "A irritação dos usuários é uma manifestação que precisa ser acolhida",
            "A compreensão do funcionamento da unidade influencia a aceitação das regras"],
        "ideia_secundaria": "Conversas sobre o funcionamento devem ocorrer em diversos espaços e momentos",
        "afirmacoes_falsas": [
            "Diante da irritação do usuário, cabe à equipe reagir e impor as regras",
            "O diálogo sobre o funcionamento só deve ocorrer em consultas agendadas",
            "Acolher a irritação dos usuários significa ceder a todas as suas demandas",
            "A manifestação de irritação deve ser deslegitimada pela equipe"],
    },
    {
        "trecho_id": "cad-06",
        "capitulo": 2, "pagina": 26,
        "texto": (
            "Para implantar práticas e processos de acolhimento visando a "
            "melhorar a acessibilidade do usuário e a escuta dos profissionais, "
            "não são suficientes ações normativas, burocráticas nem discursivas. "
            "Além disso, não basta ter uma sala de acolhimento, e é equivocado "
            "restringir a responsabilidade pelo ato de acolher aos trabalhadores "
            "da recepção, pois o acolhimento não se reduz a uma etapa nem a um "
            "lugar. Assumir efetivamente o acolhimento como diretriz é um "
            "processo que demanda transformações intensas na maneira de "
            "funcionar a atenção básica. Isso requer um conjunto de ações "
            "articuladas, envolvendo usuários, trabalhadores e gestores."),
        "tese": "Implantar o acolhimento exige transformar o funcionamento da unidade, não apenas criar normas ou espaços",
        "pressupostos": [
            "O acolhimento atravessa todas as etapas do atendimento",
            "A transformação de práticas depende do envolvimento de múltiplos atores"],
        "ideia_secundaria": "Restringir a responsabilidade pelo acolhimento a um único grupo é um equívoco",
        "afirmacoes_falsas": [
            "Ações normativas e burocráticas são suficientes para garantir o acolhimento",
            "Ter uma sala de acolhimento é o principal fator para sua implantação",
            "O acolhimento se resume a uma etapa inicial do atendimento",
            "A implantação do acolhimento decorre da vontade de um único ator"],
    },
    {
        "trecho_id": "cad-07",
        "capitulo": 1, "pagina": 21,
        "texto": (
            "A primeira razão é porque, a despeito da existência de formas "
            "cientificamente fundadas de definição objetiva das necessidades de "
            "saúde, é preciso entender que a ciência e os profissionais de saúde "
            "não são os únicos definidores das necessidades de saúde. Queiramos "
            "ou não, o usuário também define, com formas e graus variados, o que "
            "é necessidade de saúde para ele, podendo apresentá-la enquanto "
            "demanda ao serviço. E é importante que a demanda apresentada pelo "
            "usuário seja acolhida, escutada, problematizada, reconhecida como "
            "legítima. Quando não há coincidência entre a demanda e o olhar "
            "técnico-profissional, é necessário um esforço de diálogo e "
            "compreensão, sem o qual são produzidos ruídos."),
        "tese": "O usuário também define suas necessidades de saúde, e sua demanda deve ser reconhecida como legítima",
        "pressupostos": [
            "A definição de necessidade de saúde não é monopólio técnico",
            "A divergência entre demanda e olhar profissional é possível e frequente"],
        "ideia_secundaria": "A falta de diálogo produz ruídos como queixas e busca por outros serviços",
        "afirmacoes_falsas": [
            "A ciência e os profissionais são os únicos definidores das necessidades de saúde",
            "Quando a demanda coincide com o olhar técnico, o diálogo é desnecessário",
            "A demanda espontânea não precisa ser reconhecida como legítima",
            "O usuário não tem competência para identificar suas próprias necessidades"],
    },
]
