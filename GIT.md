# 🚀 Instalação e Deploy — passo a passo

## 1. Backup (antes de qualquer coisa)

```cmd
cd K:\nivelis-teste\Nivelis-Api

copy simulados_api.py simulados_api.py.bak
copy questoes_api.py  questoes_api.py.bak
copy indexar_livro.py indexar_livro.py.bak
```

## 2. Copiar os arquivos

**Substituir 3:**
```
simulados_api.py
questoes_api.py
indexar_livro.py
```

**Adicionar 14 (novos):**
```
gerador_ads.py                  gerador_procedural.py
gerador_saude.py                gerador_decoreba.py
gerador_interpretacao.py        montar_simulado_procedural.py
rodar_testes.py                 _trechos_teste.py
teste_1_gabarito.py             teste_2_coerencia.py
teste_3_portugues.py            teste_4_fatos.py
teste_5_interpretacao.py        teste_6_simulado.py
```

**Colar 1:**
O conteúdo de `ROTA_procedural.py` vai **dentro** do `simulados_api.py`,
no final do arquivo, **antes** da seção:

```python
# ──────────────────────────────────────────
#  HANDLERS DE EXCEÇÃO (SEGURANÇA)
# ──────────────────────────────────────────
```

> `ROTA_procedural.py` NÃO é um arquivo do projeto — é um trecho para colar.
> Não o adicione ao Git.

## 3. Testar ANTES de subir

```cmd
python rodar_testes.py 500
```

Não precisa de internet nem Firebase. Se der verde, siga.

```cmd
copy chave-nivelis.json chave-firebase.json
uvicorn nivelis_api:app --reload --port 8000
```

Deve aparecer no terminal:
```
[PROCEDURAL] ✅ 5 geradores carregados
```

Teste em `http://localhost:8000/docs`:
```
POST /v1/simulados/procedural/simulado?quantidade=30&disciplinas=ads
POST /v1/simulados/procedural/gerar?disciplina=saude&quantidade=5&salvar=false
```

---

## 4. Git — comandos completos

```cmd
cd K:\nivelis-teste\Nivelis-Api

REM Arquivos alterados
git add simulados_api.py questoes_api.py indexar_livro.py

REM Geradores
git add gerador_ads.py gerador_procedural.py gerador_saude.py
git add gerador_decoreba.py gerador_interpretacao.py
git add montar_simulado_procedural.py

REM Testes
git add rodar_testes.py _trechos_teste.py
git add teste_1_gabarito.py teste_2_coerencia.py teste_3_portugues.py
git add teste_4_fatos.py teste_5_interpretacao.py teste_6_simulado.py

REM Confere o que entrou (deve listar 17 arquivos)
git status

REM Commit
git commit -m "Geradores procedurais em Python (ADS, matematica, saude, conceitual, interpretacao), montador de simulado, suite de 6 testes e correcoes de validacao"

REM Envia
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

O commit mais recente deve ter `(HEAD -> main, origin/main)` ao lado.

---

## 5. Deploy no Render

Auto-deploy está ligado: após o `git push`, o Render redeploya em ~2 minutos.

**Acompanhe:** dashboard → serviço `nivelis-api-1` → aba **Events**.
Procure "Deploy live for <hash do commit>".

Se falhar, a aba **Logs** mostra o motivo.
Se não disparar sozinho: **Manual Deploy** → *Deploy latest commit*.

**Testar em produção:**
```
https://nivelis-api-1.onrender.com/docs
https://nivelis-api-1.onrender.com/v1/simulados/procedural/areas
```

---

## 6. NÃO versionar

Confirme que continuam fora do Git:
```
chave-nivelis.json
chave-firebase.json
.env
```

`.gitignore` sugerido:
```
chave-*.json
.env
__pycache__/
*.pyc
*.bak
```

---

## 7. Rotas novas

| Rota | O que faz |
|---|---|
| `GET  /procedural/areas` | lista disciplinas e tópicos disponíveis |
| `POST /procedural/gerar` | questões de uma disciplina (`ads`, `matematica`, `saude`, `conceitual`) |
| `POST /procedural/gerar-do-livro` | usa os tópicos do livro para escolher os geradores |
| `POST /procedural/interpretacao` | questões sobre trechos analisados de um livro |
| `POST /procedural/simulado` | **simulado completo** — mistura 40/30/30 |

Todas com prefixo `/v1/simulados/` em produção.

---

## 8. Para usar interpretação de texto

Livros indexados **antes** desta versão não têm trechos salvos. Reindexe:

```cmd
python indexar_livro.py "livros/seu_livro.pdf" --forcar
```

O Gemini extrai 8-20 parágrafos com análise (tese, pressupostos, afirmações
falsas). Depois disso, as questões saem em Python, sem custo de IA.

---

## 9. Cobertura

| Gerador | Templates | Área |
|---|---|---|
| `gerador_ads` | 23 | ENADE Computação |
| `gerador_procedural` | 15 | Combinatória e probabilidade |
| `gerador_saude` | 11 | Cálculo clínico, epidemiologia, bioestatística |
| `gerador_decoreba` | 10 | Memorização (fatos verificados em fonte primária) |
| `gerador_interpretacao` | 5 tipos | Interpretação sobre trechos de livros |

**59 templates + 5 tipos de interpretação.**

---

## 10. Verificações feitas

**Fórmulas conferidas em fonte primária:**
- Portas TCP/UDP → registro IANA
- Códigos HTTP → RFC 9110
- Camadas OSI → ISO/IEC 7498-1
- Gotejamento → literatura de enfermagem + 2 questões reais de banca
- Sensibilidade, especificidade, VPP, VPN → material acadêmico (UFG, UFRRJ)
- Risco relativo, odds ratio, NNT → literatura de epidemiologia (UFRGS, SciELO)

**Testes automatizados:** 6 baterias, 6 sementes, ~12.000 questões por rodada.

**Lacuna conhecida:** o gerador de interpretação nunca rodou com trecho real
vindo do Gemini. Ao reindexar um livro, confira os trechos salvos no Firestore
antes de gerar — se a tese extraída não bater com o parágrafo, a questão sai
errada e os testes não pegam isso.
