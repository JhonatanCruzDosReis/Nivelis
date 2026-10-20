# 📦 Nivelis — Instalação e Deploy

Tudo vai em `K:\nivelis-teste\Nivelis-Api\` (mesma pasta do `nivelis_api.py`).

---

## 1. Arquivos que SUBSTITUEM os existentes

| Arquivo | O que mudou |
|---|---|
| `simulados_api.py` | validação de qualidade (distrator próximo, questão quebrada, frações, resposta não-escalar), reparo de JSON (control chars + nível 2 na rota do livro), casamento questão↔gabarito por índice, blindagem contra campos `null` |
| `questoes_api.py` | mesmas correções + limite de quantidade coerente + correção por `questao_id` |
| `indexar_livro.py` | reparo de JSON truncado, checagem `isinstance`, reorganização de funções, **extração de trechos analisados para questões de interpretação** |

**Faça backup antes:**
```cmd
copy simulados_api.py simulados_api.py.bak
copy questoes_api.py questoes_api.py.bak
copy indexar_livro.py indexar_livro.py.bak
```

## 2. Arquivos NOVOS — geradores

| Arquivo | Conteúdo |
|---|---|
| `gerador_ads.py` | **23 templates** — ENADE Computação |
| `gerador_procedural.py` | **15 templates** — combinatória e probabilidade |
| `gerador_saude.py` | **11 templates** — cálculo clínico, epidemiologia, bioestatística |
| `gerador_decoreba.py` | **10 templates** — memorização (fatos verificados em fonte primária) |
| `gerador_interpretacao.py` | **5 tipos de questão** sobre trechos de livros indexados |
| `montar_simulado_procedural.py` | monta simulado completo combinando os geradores |

Todos precisam ficar **na mesma pasta** do `simulados_api.py`.

## 3. Arquivos NOVOS — testes

| Arquivo | Verifica |
|---|---|
| `rodar_testes.py` | roda tudo de uma vez (use este) |
| `teste_1_gabarito.py` | recalcula a resposta de forma independente |
| `teste_2_coerencia.py` | se a frase faz sentido |
| `teste_3_portugues.py` | concordância, contrações, pontuação |
| `teste_4_fatos.py` | consistência da tabela do gerador conceitual |
| `teste_5_interpretacao.py` | gabarito rastreável à análise do trecho |
| `teste_6_simulado.py` | composição, numeração e mistura do simulado |
| `_trechos_teste.py` | trechos sintéticos usados pelo teste 5 |

## 4. Bloco para COLAR

`ROTA_procedural.py` **não é** arquivo solto — é um trecho para colar dentro do `simulados_api.py`.

**Onde exatamente:** no final do arquivo, **antes** desta seção:

```python
# ──────────────────────────────────────────
#  HANDLERS DE EXCEÇÃO (SEGURANÇA)
# ──────────────────────────────────────────
```

---

## 5. Testar local ANTES de subir

```cmd
cd K:\nivelis-teste\Nivelis-Api

REM 1. Roda a bateria de testes (não precisa de internet nem Firebase)
python rodar_testes.py 500

REM 2. Se der verde, sobe a API
copy chave-nivelis.json chave-firebase.json
uvicorn nivelis_api:app --reload --port 8000
```

No terminal deve aparecer:
```
[PROCEDURAL] ✅ 4 geradores carregados (59 templates)
```

Abra `http://localhost:8000/docs` e teste:

```
GET  /v1/simulados/procedural/areas
POST /v1/simulados/procedural/gerar?disciplina=ads&quantidade=10&salvar=false
POST /v1/simulados/procedural/gerar?disciplina=saude&topico=epidemiologia&quantidade=5
POST /v1/simulados/procedural/gerar?disciplina=conceitual&quantidade=10
POST /v1/simulados/procedural/gerar-do-livro?livro_id=SEU_ID&quantidade=10
POST /v1/simulados/procedural/interpretacao?livro_id=SEU_ID&quantidade=10
POST /v1/simulados/procedural/simulado?quantidade=30&disciplinas=ads&livro_id=SEU_ID
```

Use `salvar=false` para pré-visualizar sem gravar no banco.

---

## 6. Subir para o GitHub

### Passo a passo

```cmd
cd K:\nivelis-teste\Nivelis-Api

REM 1. Veja o que mudou
git status

REM 2. Adicione os arquivos
git add simulados_api.py questoes_api.py indexar_livro.py
git add gerador_ads.py gerador_procedural.py gerador_saude.py gerador_decoreba.py
git add gerador_interpretacao.py montar_simulado_procedural.py _trechos_teste.py
git add rodar_testes.py teste_1_gabarito.py teste_2_coerencia.py teste_3_portugues.py
git add teste_4_fatos.py teste_5_interpretacao.py teste_6_simulado.py

REM 3. Confirme o que entrou (deve listar os 12 arquivos em verde)
git status

REM 4. Commit
git commit -m "Geradores procedurais (ADS, matematica, saude, conceitual) + suite de testes + correcoes de validacao"

REM 5. Envia
git push
```

### Se o push der erro de divergência

```cmd
git pull --rebase
git push
```

### Conferir se subiu

```cmd
git log --oneline -3
```

O commit mais recente deve ser o seu, com `(HEAD -> main, origin/main)` ao lado.

---

## 7. Deploy no Render

O Render tem **auto-deploy** ligado — depois do `git push` ele redeploya sozinho em ~2 minutos.

**Acompanhe:** dashboard do Render → serviço `nivelis-api-1` → aba **Events**.
Procure por "Deploy live for <hash do seu commit>".

Se aparecer "Deploy failed", vá na aba **Logs** para ver o motivo.

**Se o auto-deploy não disparar:** botão **Manual Deploy** → *Deploy latest commit*.

### Testar em produção

```
https://nivelis-api-1.onrender.com/docs
```

As rotas ficam sob `/v1/simulados/`:
```
POST https://nivelis-api-1.onrender.com/v1/simulados/procedural/gerar?disciplina=ads&quantidade=10
```

---

## 8. O que NÃO subir para o GitHub

Confirme que estes continuam fora do versionamento:

```
chave-nivelis.json
chave-firebase.json
.env
```

Se aparecerem no `git status` como *untracked*, está correto — não os adicione.
Se quiser garantir, crie um `.gitignore` com:

```
chave-*.json
.env
__pycache__/
*.pyc
```

---

## 9. Cobertura dos geradores

### `disciplina=ads` — 23 templates
| Área | Conteúdo |
|---|---|
| `algoritmos` | complexidade de loops e de clássicos, contagem de operações, ordenação |
| `estruturas_dados` | pilha, fila, árvore BST, grafos |
| `matematica_disc` | conversão de bases, aritmética binária, lógica, conjuntos |
| `banco_dados` | resultado de query SQL, cardinalidade de JOIN |
| `redes` | sub-rede CIDR |
| `sistemas_op` | escalonamento FIFO/SJF, memória cache |
| `eng_software` | pontos de função, cobertura de testes, métricas de projeto |
| `teoria_computacao` | recorrências (Teorema Mestre), autômatos |
| `arquitetura` | hit rate, tempo médio de acesso, endereçamento |

### `disciplina=matematica` — 15 templates
`contagem` · `anagramas` · `combinacoes` · `binomio` · `probabilidade`

### `disciplina=saude` — 11 templates
| Área | Conteúdo |
|---|---|
| `calculo_clinico` | gotejamento, tempo de infusão, conversão de unidades, diluição, dose por peso |
| `epidemiologia` | prevalência, incidência, sensibilidade, especificidade, VPP, VPN |
| `bioestatistica` | risco relativo, odds ratio, NNT |

### `disciplina=conceitual` — 10 templates
| Área | Conteúdo |
|---|---|
| `redes` | portas padrão (IANA), camadas OSI, códigos HTTP (RFC 9110) |
| `banco_dados` | formas normais, propriedades ACID, categorias SQL |
| `algoritmos` | complexidades clássicas, políticas de estruturas, percursos |
| `eng_software` | paradigmas, pilares OO, Scrum |

---

## 10. Quando usar cada gerador

| Matéria | Use |
|---|---|
| ADS/Computação (ENADE específico) | **procedural** (`disciplina=ads` e `conceitual`) |
| Combinatória e probabilidade | **procedural** (`disciplina=matematica`) |
| Medicina, enfermagem, farmácia (cálculo e epidemiologia) | **procedural** (`disciplina=saude`) |
| Outras áreas da matemática | Gemini, ou escreva templates novos |
| Português, filosofia, sociologia, interpretação | **Gemini** — conteúdo interpretativo não tem fórmula |

---

## 11. Como adicionar um template novo

1. Escreva `gerar_meu_template(rng)` seguindo o padrão dos existentes
2. Calcule `correta` com a lógica certa (ou **simule**, como pilha e SQL fazem)
3. Liste `distratores` = os erros que um aluno cometeria de verdade
4. Declare `tipo_resposta` na chamada de `_montar` (numerica, fracao, simbolica,
   codigo_numerico, sequencia, textual, endereco_ip, percentual)
5. Registre em `TEMPLATES_*` e no tópico certo em `TOPICOS_*`
6. Adicione palavras-chave em `PALAVRAS_CHAVE` (para o pipeline do livro achar)
7. **Rode `python rodar_testes.py 500`** — se acusar falso positivo, calibre o
   teste; se acusar erro real, corrija o template

**Regras que evitam dor de cabeça:**
- Termine a explicação com o resultado final (a validação lê o último número)
- Use `_juntar()` ao montar enunciado por partes (evita minúscula após ponto)
- Use `_plural()` e `_verbo()` quando a contagem puder dar 1

---

## 12. Livros gratuitos para indexar (medicina)

**Melhor fonte:** `bvsms.saude.gov.br/bvs/publicacoes/` — Cadernos de Atenção
Básica do Ministério da Saúde. PDFs diretos, licença Creative Commons, e
alinhados ao que o ENADE de Medicina cobra (SUS).

Exemplos: nº 32 (pré-natal), nº 21 (vigilância em saúde), nº 23 (saúde da
criança), nº 13 (cânceres colo e mama), nº 18 (HIV/hepatites).

Outras: IRIS/OMS (`iris.who.int`), SciELO Livros, Portal Domínio Público.

**Evite** sites de download que hospedam material pirata — se o Nivelis for
comercializado, indexar conteúdo protegido é risco jurídico.

---

## 13. Questões de interpretação de texto

### Como funciona

```
PDF do livro
   ↓  indexar_livro.py  (Gemini lê UMA vez)
Firestore: capítulos + tópicos + TRECHOS ANALISADOS
           (cada trecho traz tese, pressupostos, ideia
            secundária e afirmações que o texto não sustenta)
   ↓  /procedural/interpretacao
Python monta as questões usando a análise como gabarito — custo ZERO
```

O Gemini deixa de ser o gerador e passa a ser o **preparador de material**.
Ele lê o livro uma vez; depois disso, o Python produz quantas questões
quiser sobre aqueles trechos.

### Tipos de questão gerados

| Tipo | Gabarito vem de |
|---|---|
| `tese` | campo `tese` da análise |
| `pressuposto` | campo `pressupostos` |
| `ideia_secundaria` | campo `ideia_secundaria` |
| `nao_sustentada` | campo `afirmacoes_falsas` |
| `assercao_razao` | combinação verificada dos campos (formato ENADE) |

### Uso

```
POST /v1/simulados/procedural/interpretacao?livro_id=SEU_ID&quantidade=10
POST /v1/simulados/procedural/interpretacao?livro_id=SEU_ID&tipos=tese,assercao_razao
```

### Importante

Livros indexados **antes** desta funcionalidade não têm trechos salvos.
Para extraí-los, reindexe:

```cmd
python indexar_livro.py "livros/seu_livro.pdf" --forcar
```

A rota informa isso claramente se você tentar gerar sem trechos.

### Cobertura por disciplina

Este gerador funciona para **qualquer área** — o conteúdo vem do livro, não
do código. Português, Direito, Medicina, Filosofia, Sociologia: tudo que
tiver trecho analisado no banco vira questão.

É por aqui que se resolvem as matérias que os geradores procedurais não
alcançam.

---

## 14. Simulado completo em Python

A rota que fecha o ciclo: monta um simulado inteiro sem chamar IA.

```
POST /v1/simulados/procedural/simulado?quantidade=30&disciplinas=ads&livro_id=SEU_ID
```

### Composição padrão

| Fonte | Fatia | De onde vem o gabarito |
|---|---|---|
| Procedural | 40% | calculado/simulado pelo Python |
| Conceitual | 30% | tabela de fatos verificados |
| Interpretação | 30% | análise dos trechos do livro |

Ajustável pelo parâmetro `mistura`:
```
&mistura=50,25,25      → 50% procedural, 25% conceitual, 25% interpretação
```

### Parâmetros

| Parâmetro | Efeito |
|---|---|
| `quantidade` | 5 a 100 questões |
| `disciplinas` | `ads`, `matematica`, `saude` (separadas por vírgula) |
| `livro_id` | livro indexado para a fatia de interpretação |
| `ponderar` | usa `provas_analisadas` para pesar as áreas (padrão: true) |
| `area_prova` | filtra quais provas considerar |
| `mistura` | proporção custom |
| `seed` | simulado reproduzível (debug) |

### Ponderação por prova real

Se houver provas na coleção `provas_analisadas`, a distribuição **dentro da
fatia procedural** segue a frequência com que cada assunto foi cobrado. Se o
ENADE cobrou muito banco de dados e pouco redes, o simulado espelha isso.

Para popular essa coleção, use `analisar_provas_lote.py` — ele baixa as
provas do INEP e o Gemini extrai os tópicos (uma vez por prova).

### Degradação controlada

Se o livro não tiver trechos, ou nem for informado, a fatia de interpretação
é **redistribuída** entre as outras fontes. O simulado sai com o tamanho
pedido, apenas com composição diferente:

```
com livro:  {'procedural:ads': 12, 'conceitual': 9, 'interpretacao': 9}
sem livro:  {'procedural:ads': 18, 'conceitual': 12}
```

### Compatibilidade com o app

O simulado é salvo com `salvar_simulado_firebase()` — a mesma função das
rotas com IA. Vai para as coleções `simulados` e `gabaritos` no formato de
sempre, então o aplicativo consome sem nenhuma alteração.
