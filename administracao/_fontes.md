# Fatos de administração verificados

As fórmulas abaixo foram conferidas contra a literatura brasileira de
contabilidade gerencial e finanças (Martins, *Contabilidade de Custos*;
Matarazzo, *Análise Financeira de Balanços*; Assaf Neto, *Finanças
Corporativas*) e contra material de concurso. Onde as fontes divergem,
a divergência está registrada e o gerador ou evita o ponto, ou fixa a
convenção no próprio enunciado.

---

## ⚠️ DIVERGÊNCIA: o ROI ficou de fora

O ROI tem dois denominadores incompatíveis na literatura brasileira:

- **análise de balanço** — ROI = lucro operacional ÷ investimento
  (ativo total, ou ativo operacional líquido, conforme o autor);
- **marketing e projetos** — ROI = (ganho − custo) ÷ custo.

Uma questão de ROI teria duas respostas defensáveis conforme a escola
de quem corrige. O gerador **não cobra ROI**. Cobra ROA e ROE, cujos
denominadores não divergem:

| Índice | Fórmula | Pergunta que responde |
|---|---|---|
| ROA | lucro operacional ÷ ativo total | o que o ativo inteiro produz, independentemente de quem o financiou |
| ROE | lucro líquido ÷ patrimônio líquido | o que sobra para o sócio sobre o capital dele |
| margem líquida | lucro líquido ÷ receita líquida | quanto de cada real vendido vira lucro |

⚠️ ARMADILHA: o ROA usa lucro **operacional** e o ROE usa lucro
**líquido**. Trocar o numerador é o erro que os distratores exploram.

### ⚠️ E o ROA também precisou de convenção fixada

O ROI não foi o único caso. O **numerador do ROA** também diverge:

- **Assaf Neto** — retorno sobre o ativo = lucro **operacional** ÷ ativo;
- **Matarazzo** — rentabilidade do ativo = lucro **líquido** ÷ ativo.

As duas são consagradas e as duas caem em prova. A primeira versão do
template não dizia qual, e a questão tinha duas respostas defensáveis —
pior ainda porque o lucro líquido ÷ ativo já estava entre os
distratores. O enunciado agora **pede o ROA "com base no lucro
operacional"**, e desempata.

---

## ⚠️ CONVENÇÃO FIXADA: ano comercial de 360 dias

Prazo médio de estocagem = 360 ÷ giro. A literatura usa 360 (ano
comercial) e 365 (ano civil), e a diferença muda a resposta: com giro
de 10, dá 36 ou 36,5 dias.

O enunciado do template **diz "considerando o ano comercial de 360
dias"**, sempre. Sem isso a questão teria duas respostas certas. O
valor de 365 aparece como distrator, que é o papel dele.

Os dias saem todos arredondados para inteiro, inclusive o distrator de
365. Não é preciosismo de formatação: 360 ÷ giro é sempre exato no
gerador, e 365 ÷ giro quase nunca é — deixar a vírgula só nos
distratores entregava a resposta a quem não soubesse a matéria.

---

## Ponto de equilíbrio

| Tipo | Numerador | Fórmula |
|---|---|---|
| contábil (PEC) | custos e despesas fixos | CF ÷ MCu |
| financeiro (PEF) | fixos **menos** depreciação | (CF − depreciação) ÷ MCu |
| econômico (PEE) | fixos **mais** lucro desejado | (CF + lucro desejado) ÷ MCu |

Os três dividem pela mesma margem de contribuição unitária. O que muda
é o numerador — e daí a ordem, que é **invariável**:

**PEF < PEC < PEE**

A depreciação sai do numerador do financeiro porque reduz o lucro mas
não sai do caixa. O template verifica essa ordem em toda questão
gerada.

---

## Margem de contribuição

MCu = preço de venda − custo variável − **despesas variáveis**

⚠️ ARMADILHA: a comissão do vendedor é despesa variável e entra no
cálculo. Deixá-la de fora é o erro mais cobrado, e é o distrator
principal do template.

---

## ⚠️ MARKUP: por que há distratores ACIMA do preço correto

Todos os erros clássicos do markup **subestimam** o preço: somar o
percentual ao custo, esquecer o lucro no divisor, dividir só pelo
lucro. Com cinco alternativas assim, a resposta certa era **o maior
valor das cinco em 84% das questões** — acertava-se sem fazer conta
nenhuma, e nenhum dos treze testes do projeto percebia, porque nenhum
deles olha a POSIÇÃO NUMÉRICA da resposta (o teste 8 mede comprimento
de texto, não magnitude).

Dois distratores foram acrescentados para passar do preço correto:

- `custo ÷ divisor²` — aplicou o markup duas vezes;
- `custo ÷ (1 − DV − DF − 2×LP)` — contou o lucro duas vezes.

Com eles, a taxa caiu de 84% para 7%.

No mesmo diagnóstico apareceu o motivo de os distratores extras não
ajudarem: `_montar` pegava os **quatro primeiros** da lista, e tudo o
que estivesse em quinto ou sexto lugar quase nunca era usado. Agora o
primeiro distrator (o erro clássico da matéria) entra sempre e os
demais são sorteados.

⚠️ ESTE DIAGNÓSTICO VALE PARA AS OUTRAS DISCIPLINAS. Nenhum teste do
projeto mede se a resposta certa é sistematicamente o maior ou o menor
valor. Administração foi medida à mão e está limpa; as outras dezenove
não foram.

---

## Markup

Os percentuais de despesa e lucro incidem sobre o **preço de venda**,
não sobre o custo. Por isso se **divide**:

- markup divisor = 1 − (DV% + DF% + LP%)
- preço = custo ÷ markup divisor
- markup multiplicador = 1 ÷ markup divisor

⚠️ ARMADILHA: somar os percentuais ao custo (custo × 1,37 para 37%)
dá um preço que **não cobre as despesas**, porque elas são calculadas
sobre o preço maior. É o distrator nomeado na explicação.

---

## Custeio por absorção × custeio variável

| | custo fixo de produção | custo unitário |
|---|---|---|
| absorção | rateado pela quantidade, entra no produto | CVu + CF ÷ q |
| variável | despesa do período, fora do produto | CVu |

Só o **absorção** é aceito para fins societários e fiscais (CPC 16 /
legislação do IR). O variável serve à decisão gerencial.

---

## Índices de liquidez

| Índice | Fórmula |
|---|---|
| imediata | disponível ÷ passivo circulante |
| seca | (ativo circulante − estoques) ÷ passivo circulante |
| corrente | ativo circulante ÷ passivo circulante |
| geral | (AC + realizável a LP) ÷ (PC + passivo não circulante) |

O que muda entre eles é o que se admite como recurso: a imediata conta
só o caixa; a seca exclui o estoque, de realização mais lenta; a
corrente aceita todo o circulante; a geral estende a conta ao longo
prazo dos dois lados.

Todas as alternativas saem com **duas casas decimais**, sempre. Um
índice exato viraria "2" no meio de "1,50" e "0,38", e a alternativa
de formato diferente se denuncia sozinha.

---

## Depreciação linear (quotas constantes)

depreciação anual = (valor de aquisição − valor residual) ÷ vida útil

⚠️ ARMADILHA: deprecia-se o que o bem **perde**, não o que ele custou.
Esquecer de subtrair o valor residual é o distrator principal.

---

## Payback simples e VPL

- **payback simples** (fluxo uniforme) = investimento ÷ entrada anual.
  É medida de **prazo**, não de rentabilidade: ignora o valor do
  dinheiro no tempo e tudo o que entra depois do retorno.
- **VPL** = Σ (FCt ÷ (1+i)^t) − investimento inicial.
  VPL positivo significa que o projeto rende **acima** da taxa
  exigida — não apenas que dá lucro.

---

## Escolas da administração

| Escola | Autor | Ênfase |
|---|---|---|
| administração científica | Frederick Taylor | a tarefa executada no chão de fábrica |
| teoria clássica | Henri Fayol | a estrutura e as funções da organização |
| teoria das relações humanas | Elton Mayo | as pessoas e os grupos informais |
| teoria da burocracia | Max Weber | as normas e a racionalidade formal |
| teoria comportamental | Herbert Simon | o processo de tomada de decisão |
| teoria geral dos sistemas | Ludwig von Bertalanffy | a organização como sistema aberto |
| teoria da contingência | — | a adequação da estrutura ao ambiente |

A contingência não tem autor único atribuído no gerador (Lawrence e
Lorsch, Woodward e Burns e Stalker chegaram a ela por caminhos
diferentes), e por isso não entra nas questões de autoria.

---

## Funções administrativas (PODC)

Planejar, organizar, dirigir, controlar. O ciclo se fecha e se
realimenta: o desvio que o controle detecta volta ao planejamento.

⚠️ ARMADILHA: **coordenar** é função na lista original de Fayol
(prever, organizar, comandar, coordenar, controlar) e foi absorvida
por "dirigir" no PODC moderno. O template usa "coordenar" como
distrator, e por isso **o enunciado fixa "as quatro funções do
processo administrativo"** — sem essa moldura, "coordenar" seria
resposta defensável.

---

## ⚠️ CINCO FORÇAS DE PORTER: como NÃO perguntar

As cinco forças são:

1. rivalidade entre os concorrentes existentes
2. ameaça de novos entrantes
3. ameaça de produtos substitutos
4. poder de barganha dos fornecedores
5. poder de barganha dos compradores

**Não se pergunta "qual das alternativas é uma das cinco forças"** com
as outras quatro entre os distratores: as cinco são todas corretas e a
questão fica sem resposta. A primeira versão do template fazia
exatamente isso e gerava questões com cinco gabaritos possíveis.

A pergunta correta parte de uma **situação concreta** e pede a força
que ela representa. O que distingue as forças está escrito na própria
situação:

- **rivalidade** — a disputa é entre empresas que **já estão** no setor;
- **novos entrantes** — o que está em causa é a **barreira de entrada**
  (capital, licença, patente);
- **substitutos** — a alternativa vem de **outro setor** e atende à
  mesma necessidade por outro meio;
- **fornecedores** — quem **vende o insumo** é concentrado ou
  insubstituível;
- **compradores** — quem **compra** é concentrado, ou o produto é
  padronizado e a troca não custa nada.

---

## Outros modelos de estratégia

**SWOT** — dois eixos: origem (interna: forças e fraquezas / externa:
oportunidades e ameaças) e efeito (positivo / negativo).

**BSC** — quatro perspectivas encadeadas de baixo para cima:
aprendizado e crescimento sustentam os processos internos, que
entregam valor aos clientes, que produzem o resultado financeiro.

**Estratégias genéricas de Porter** — liderança em custo,
diferenciação e enfoque. Combinam duas decisões: a fonte da vantagem
(custo ou diferenciação) e a amplitude do mercado. O enfoque é a
escolha de atuar em alvo estreito, por qualquer das duas fontes.

---

## Lastro: onde a disciplina é forte e onde é fina

Medido simulando o veto de repetição do montador (não contando
chaves), em 400 sementes × 40 questões:

| Tópico | Fatos distintos |
|---|---|
| Administração (custos) | 2097 |
| Administração (análise de balanço) | 1992 |
| Administração (análise de investimentos) | 1006 |
| Administração (formação de preço) | 487 |
| Administração (gestão de estoques) | 126 |
| Administração (contabilidade) | 84 |
| Administração (planejamento estratégico) | 21 |
| Administração (gestão de pessoas) | 18 |
| Administração (processo administrativo) | 16 |
| Administração (teorias da administração) | 13 |
| Administração (estrutura organizacional) | 12 |
| **TOTAL** | **5872** |

Os seis tópicos com conta têm lastro praticamente ilimitado — o
cenário é sorteado e a resposta, calculada. Os cinco conceituais são
finos, e é da natureza deles: o PODC tem quatro funções e não vai ter
cinco.

Isso importa em um caso só: **um caderno restrito a um tópico
conceitual esgota o material**. Pedir 30 questões de "estrutura
organizacional" devolve 12 e para. Em um caderno de administração
misto não se nota, porque o teto por tópico
(`max(2, quantidade // 6)`) já limita cada um a 5 em 30 questões, e os
tópicos finos sustentam isso com folga.

O que já foi feito para engordar os conceituais, e que vale como
receita para a próxima disciplina:

1. **Separar a chave do fato por modo de pergunta.** Saber quem
   formulou a teoria clássica não é saber qual é a ênfase dela: são
   dois fatos, não um. Só os dois sentidos da *mesma* informação
   (escola → ênfase e ênfase → escola) dividem chave. Isso levou
   "teorias" de 7 para 13 e "estrutura" de 4 para 8 sem inventar
   conteúdo nenhum.
2. **Acrescentar o modo aplicado.** Reconhecer a função administrativa
   em uma situação de trabalho é conhecimento distinto de recitar a
   definição, e é como a banca cobra. Levou "processo administrativo"
   de 4 para 16.
3. **Só então acrescentar linhas à tabela** (linha-staff e por
   processos, em estruturas).

---

## Coerência de cenário: quem tem CMV, quem tem CPV

O sorteio de empresa é separado por ramo, porque a conta depende dele:

- **`_revendedor`** (farmácia, distribuidora, atacadista, loja) — tem
  **CMV** e **custo de aquisição**. Usado no giro de estoque e no
  markup. Uma transportadora não tem estoque de revenda, e uma
  indústria apura CPV, não CMV.
- **`_industria`** (metalúrgica, fábrica, gráfica, confecção) — é quem
  "produziu N unidades" e tem custo fixo de produção. Usado no
  custeio. Uma transportadora que produziu 500 unidades não é cenário
  de prova.
- **`_empresa`** (todas) — nos templates em que o ramo não muda a
  conta.
