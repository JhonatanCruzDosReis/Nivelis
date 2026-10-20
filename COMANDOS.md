# 🚀 Comandos — instalação, testes e deploy

Tudo roda em `K:\nivelis-teste\Nivelis-Api\`.

---

## 1. Backup antes de tudo

```cmd
cd K:\nivelis-teste\Nivelis-Api

copy simulados_api.py simulados_api.py.bak
copy indexar_livro.py indexar_livro.py.bak
```

---

## 2. Copiar os arquivos

### Substituir (já existem na pasta)

```
simulados_api.py          questoes_api.py           indexar_livro.py
nivelis_api.py            gerador_ads.py            gerador_procedural.py
gerador_saude.py          gerador_decoreba.py       gerador_interpretacao.py
montar_simulado_procedural.py                       rodar_testes.py
teste_1_gabarito.py       teste_2_coerencia.py      teste_3_portugues.py
teste_4_fatos.py          teste_5_interpretacao.py  teste_6_simulado.py
_trechos_teste.py
```

### Adicionar (novos)

```
gerador_direito.py        gerador_redes.py
```

### Colar dentro do simulados_api.py

O conteúdo de **`ROTA_procedural.py`** vai no final do `simulados_api.py`,
**antes** desta seção:

```python
# ──────────────────────────────────────────────
#  PYDANTIC MODELS — Documentação do /docs
# ──────────────────────────────────────────────
```

> `ROTA_procedural.py` **não** é arquivo do projeto e **não** vai para o Git.
> Ele mudou nesta rodada (ganhou `direito`, `redes` e o parâmetro
> `conceitual`), então precisa ser colado de novo.

**Confirme que colou:**
```cmd
findstr /C:"procedural/simulado" simulados_api.py
```
Deve retornar a linha com `@app.post(`. Se retornar só a menção na descrição,
o bloco não está lá.

---

## 3. Reindexar o livro

O filtro de notação matemática e a extração de trechos rodam na indexação.
Livros indexados antes disso precisam ser reprocessados:

```cmd
python indexar_livro.py "livros/combinatoria.pdf" --forcar
```

Deve terminar com algo como:
```
Trechos para interpretação: 8 (de 12 extraídos)
```

**Para reindexar outros livros:**
```cmd
python indexar_livro.py "livros/nome_do_arquivo.pdf" --forcar
```

**Se aparecer "0 trechos":** o livro é de exercícios/fórmulas e não tem prosa
argumentativa suficiente. Não é bug — livros conceituais rendem mais.

**Conferir o resultado:**
```
GET https://nivelis-api-1.onrender.com/v1/simulados/livro/{livro_id}
```
Procure o campo `trechos` na resposta.

---

## 4. Testar antes de subir

```cmd
python rodar_testes.py 500
```

Roda offline, sem Firebase nem internet. Deve mostrar 6 geradores:
```
ADS / Computação | Matemática | Saúde | Conceitual (decoreba) | Direito | Redes
```

**Testes que rodam separado:**
```cmd
python teste_4_fatos.py 1000
python teste_5_interpretacao.py 800
python teste_6_simulado.py 20
```

**Subir local:**
```cmd
copy chave-nivelis.json chave-firebase.json
uvicorn nivelis_api:app --reload --port 8000
```

Procure no terminal:
```
[PROCEDURAL] ✅ 6 geradores carregados
```

Se aparecer `⚠ Geradores não encontrados`, falta algum `gerador_*.py`.

**Endereços:**
```
http://localhost:8000/v1/simulados/docs     ← as 40 rotas
http://localhost:8000/docs                  ← wrapper
```

---

## 5. Git

```cmd
cd K:\nivelis-teste\Nivelis-Api
```

**Geradores:**
```cmd
git add gerador_ads.py gerador_procedural.py gerador_saude.py gerador_decoreba.py gerador_direito.py gerador_redes.py gerador_interpretacao.py
```

**Montagem e API:**
```cmd
git add montar_simulado_procedural.py simulados_api.py questoes_api.py nivelis_api.py indexar_livro.py
```

**Testes:**
```cmd
git add rodar_testes.py _trechos_teste.py teste_1_gabarito.py teste_2_coerencia.py teste_3_portugues.py teste_4_fatos.py teste_5_interpretacao.py teste_6_simulado.py
```

**Conferir e enviar:**
```cmd
git status
```
```cmd
git commit -m "Geradores de direito e redes, templates de raciocinio juridico e clinico, filtro conceitual por disciplina e suite de 6 testes"
```
```cmd
git push
```

**Se der divergência:**
```cmd
git pull --rebase
```
```cmd
git push
```

**Conferir se subiu:**
```cmd
git log --oneline -3
```

---

## 6. Deploy no Render

Auto-deploy dispara sozinho após o push (~2 min).

**Acompanhar:** dashboard → `nivelis-api-1` → aba **Events** → procure
"Deploy live for <hash>".

Se falhar, veja a aba **Logs**.
Se não disparar: **Manual Deploy** → *Deploy latest commit*.

**Testar em produção:**
```
https://nivelis-api-1.onrender.com/v1/simulados/docs
```

---

## 7. Rotas procedurais

```
GET  /v1/simulados/procedural/areas
POST /v1/simulados/procedural/gerar?disciplina=direito&quantidade=10&salvar=false
POST /v1/simulados/procedural/gerar?disciplina=redes&quantidade=10&salvar=false
POST /v1/simulados/procedural/gerar-do-livro?livro_id=SEU_ID&quantidade=10
POST /v1/simulados/procedural/interpretacao?livro_id=SEU_ID&quantidade=5
POST /v1/simulados/procedural/simulado?quantidade=30&disciplinas=direito
```

**Disciplinas:** `ads`, `matematica`, `saude`, `direito`, `redes`, `conceitual`

**Parâmetros do simulado:**

| Parâmetro | Efeito |
|---|---|
| `quantidade` | 5 a 100 |
| `disciplinas` | separadas por vírgula |
| `livro_id` | fatia de interpretação |
| `mistura` | ex: `50,25,25` |
| `conceitual` | sobrescreve o filtro automático |
| `seed` | reproduzível |

---

## 8. Não versionar

```
chave-nivelis.json
chave-firebase.json
.env
ROTA_procedural.py
```

`.gitignore` sugerido:
```
chave-*.json
.env
__pycache__/
*.pyc
*.bak
ROTA_procedural.py
```

---

## 9. Cobertura atual

| Gerador | Templates |
|---|---|
| `gerador_ads` | 23 |
| `gerador_direito` | 17 |
| `gerador_saude` | 16 |
| `gerador_procedural` | 15 |
| `gerador_redes` | 12 |
| `gerador_decoreba` | 10 |
| `gerador_interpretacao` | 5 tipos |

**93 templates + 5 tipos de interpretação.**

---

## 10. O que mudou nesta rodada

**Geradores novos:** direito (17) e redes (12).

**Templates de raciocínio** adicionados a direito e saúde — antes eram quase
só cálculo e consulta a tabela; agora exigem aplicar regra a caso concreto e
interpretar resultados.

**Filtro conceitual por disciplina:** um simulado de matemática não recebe
mais questão sobre porta de rede. A fatia é redistribuída.

**Correções:** concordância objeto/cor, alternativas contraditórias, vazamento
de resposta no OSI, sumarização com rotas idênticas, distratores negativos,
cenários de infusão fora da faixa clínica, artigo e verbo duplicados.

**Testes:** o teste 1 ganhou 23 verificadores novos (redes e direito), mais
checagem de distratores impossíveis e de plausibilidade clínica.

---

## 11. Verificação feita

**Fontes primárias consultadas:**
- Portas TCP/UDP → registro IANA
- Códigos HTTP → RFC 9110
- Camadas OSI → ISO/IEC 7498-1
- Gotejamento → literatura de enfermagem + 2 questões reais de banca
- Sensibilidade, VPP, RR, odds ratio, NNT → material acadêmico
- Prazos processuais → CPC/2015
- Prescrição → Código Civil arts. 205 e 206 + STJ

**Recálculo independente:**
- Redes: 2000 verificações → 0 erros
- Direito: 1800 verificações → 0 erros
- Templates de raciocínio: 600 verificações → 0 erros

**Bateria:** 14.400 questões × 6 dimensões → 0 falhas

---

## 12. Lacunas conhecidas

**O gerador de interpretação nunca rodou com trecho real de livro conceitual.**
Os testes usam trechos sintéticos. Ao reindexar, confira os trechos salvos no
Firestore antes de gerar — se a tese extraída não bater com o parágrafo, a
questão sai errada e nenhum teste pega isso.

**A legislação muda.** Os prazos do `gerador_direito.py` refletem o CPC/2015 e
o Código Civil vigentes em agosto/2026. Antes de usar em produção, confirme
que não houve reforma processual.

**Billing do Gemini** continua pendente. Sem ele, 20 requisições/dia — o
suficiente para poucas indexações. As rotas procedurais não consomem nada.
