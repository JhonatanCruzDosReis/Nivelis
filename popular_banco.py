"""
=============================================================
  NIVELIS — Popular Banco de Questões (todas as matérias)
=============================================================

  Gera questões REAIS para todas as matérias e tópicos,
  salvando no Firebase. Respeita a regra de NÃO-REGENERAR:
  se um tópico já tem questões suficientes, pula (não gasta Gemini).

  COMO USAR:
    python popular_banco.py
    python popular_banco.py --por-topico 5      (5 questões por tópico)
    python popular_banco.py --forcar            (regenera tudo, cuidado!)
    python popular_banco.py --materia matematica (só uma matéria)

  ⚠️ CUSTO: 1 chamada Gemini por tópico que ainda NÃO tem questões.
     Com 5 matérias e ~6 tópicos cada = ~30 tópicos = até 30 chamadas.
     Rode aos poucos se a cota estiver baixa.

  ECONOMIA: tópicos já populados são PULADOS automaticamente.
     Rodar de novo só preenche o que falta (a menos que --forcar).

=============================================================
"""

import os
import sys
import json
import uuid
import time
import argparse
import google.generativeai as genai
import firebase_admin
from pathlib        import Path
from dotenv         import load_dotenv
from firebase_admin import credentials, firestore
from datetime       import datetime, timezone

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY não configurada no .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-2.5-flash-lite")

if not firebase_admin._apps:
    cred = credentials.Certificate("chave-firebase.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  REFORÇO COM LIVROS E PROVAS
# ──────────────────────────────────────────

LIMITE_LIVROS_REFORCO = 3
LIMITE_PROVAS_REFORCO = 3  # Por banca (3 ENEM + 3 ENADE = até 6 no total)

# Disciplinas de livros que servem como reforço para cada matéria
DISCIPLINAS_REFORCO = {
    "portugues":   ["portugues", "literatura", "redacao", "linguistica", "linguagens"],
    "matematica":  ["matematica"],
    "atualidades": ["atualidades", "geografia", "historia", "politica", "sociologia"],
    "filosofia":   ["filosofia"],
    "sociologia":  ["sociologia", "ciencias_sociais"],
}

# Provas que servem como reforço por matéria
PROVAS_REFORCO = {
    "portugues":   {"termos": ["portugues", "linguagens", "jornalismo", "letras"], "concursos": ["enem", "enade"]},
    "matematica":  {"termos": ["matematica", "engenharia", "fisica"],             "concursos": ["enem", "enade"]},
    "atualidades": {"termos": ["humanas", "direito", "historia", "geografia"],    "concursos": ["enem", "enade"]},
    "filosofia":   {"termos": ["filosofia", "humanas"],                           "concursos": ["enem", "enade"]},
    "sociologia":  {"termos": ["sociologia", "ciencias_sociais", "humanas"],      "concursos": ["enem", "enade"]},
}


def buscar_livros_para_materia(materia: str) -> list:
    """Busca até 3 livros com disciplina compatível com a matéria."""
    disciplinas_alvo = [d.lower() for d in DISCIPLINAS_REFORCO.get(materia, [materia])]
    livros = []

    try:
        for doc in db.collection("livros").stream():
            data       = doc.to_dict()
            disciplina = (data.get("disciplina") or "").lower()

            if any(d in disciplina or disciplina in d for d in disciplinas_alvo):
                capitulos = []
                for cap in data.get("capitulos", []):
                    capitulos.append({
                        "numero":  cap.get("numero"),
                        "titulo":  cap.get("titulo"),
                        "topicos": cap.get("topicos", [])[:5],
                    })
                livros.append({
                    "titulo":      data.get("titulo"),
                    "autor":       data.get("autor"),
                    "disciplina":  disciplina,
                    "capitulos":   capitulos,
                    "indexado_em": data.get("indexado_em"),
                })
    except Exception as e:
        print(f"   ⚠ Erro ao buscar livros: {e}")

    livros.sort(key=lambda x: x.get("indexado_em") or 0, reverse=True)
    return livros[:LIMITE_LIVROS_REFORCO]


def buscar_provas_para_materia(materia: str) -> list:
    """
    Busca provas oficiais já analisadas compatíveis com a matéria.
    Pega até 3 provas POR BANCA (3 ENEM + 3 ENADE = até 6 no total).
    """
    config    = PROVAS_REFORCO.get(materia, {"termos": [materia], "concursos": ["enem", "enade"]})
    termos    = [t.lower() for t in config["termos"]]
    concursos = config["concursos"]

    # Agrupa provas por concurso para limitar 3 por banca
    provas_por_concurso = {c: [] for c in concursos}

    try:
        for doc in db.collection("provas_analisadas").stream():
            data     = doc.to_dict()
            area     = (data.get("area")     or "").lower()
            concurso = (data.get("concurso") or "").lower()

            if concurso not in concursos:
                continue

            if any(t in area or area in t for t in termos):
                provas_por_concurso[concurso].append({
                    "concurso": concurso,
                    "ano":      data.get("ano"),
                    "area":     data.get("area"),
                    "topicos":  data.get("topicos", [])[:15],
                })
    except Exception as e:
        print(f"   ⚠ Erro ao buscar provas: {e}")

    # Pega as 3 mais recentes DE CADA banca
    provas_finais = []
    for concurso, lista in provas_por_concurso.items():
        lista.sort(key=lambda x: x.get("ano") or 0, reverse=True)
        provas_finais.extend(lista[:LIMITE_PROVAS_REFORCO])

    return provas_finais


def montar_contexto_livros(livros: list) -> str:
    """Texto resumido dos livros para o prompt."""
    if not livros:
        return ""
    partes = ["\n=== MATERIAL DE REFORÇO (livros do acervo) ===\n"]
    for i, l in enumerate(livros, 1):
        partes.append(f"📚 LIVRO {i}: {l['titulo']} | Autor: {l['autor']} | Disciplina: {l['disciplina']}")
        for cap in l.get("capitulos", []):
            partes.append(f"   Cap {cap.get('numero')}. {cap.get('titulo')}")
            if cap.get("topicos"):
                partes.append(f"      → {', '.join(cap['topicos'])}")
    return "\n".join(partes) + "\n"


def montar_contexto_provas(provas: list) -> str:
    """Texto resumido das provas oficiais para o prompt."""
    if not provas:
        return ""
    partes = ["\n=== PROVAS OFICIAIS DE REFERÊNCIA ===\n"]
    for i, p in enumerate(provas, 1):
        partes.append(f"📄 PROVA {i}: {p['concurso'].upper()} {p['ano']} — {p['area']}")
        for t in p.get("topicos", []):
            tema   = t.get("tema", "")
            sub    = t.get("subtopico", "")
            estilo = t.get("estilo_questao", "")
            partes.append(f"   • {tema} ({sub}) — estilo: {estilo}")
    return "\n".join(partes) + "\n"


# ──────────────────────────────────────────
#  MATÉRIAS E TÓPICOS
# ──────────────────────────────────────────

MATERIAS_TOPICOS = {
    "portugues": {
        "nome": "Português",
        "topicos": [
            "interpretacao_de_texto",
            "tipologia_textual",
            "coesao_e_coerencia",
            "argumentacao",
            "variacao_linguistica",
            "figuras_de_linguagem",
        ],
    },
    "matematica": {
        "nome": "Matemática",
        "topicos": [
            "raciocinio_logico",
            "proporcionalidade_e_porcentagem",
            "funcoes_e_graficos",
            "estatistica_e_probabilidade",
            "geometria",
            "combinatoria",
        ],
    },
    "atualidades": {
        "nome": "Atualidades",
        "topicos": [
            "politica_nacional",
            "economia",
            "meio_ambiente",
            "ciencia_e_tecnologia",
            "direitos_humanos",
        ],
    },
    "filosofia": {
        "nome": "Filosofia",
        "topicos": [
            "etica_e_moral",
            "filosofia_politica",
            "teoria_do_conhecimento",
            "logica_e_argumentacao",
        ],
    },
    "sociologia": {
        "nome": "Sociologia",
        "topicos": [
            "estrutura_social_e_desigualdade",
            "cultura_e_identidade",
            "trabalho_e_sociedade",
            "movimentos_sociais",
        ],
    },
}

QUESTOES_POR_TOPICO = 5


def ja_tem_questoes(materia: str, topico: str, minimo: int) -> int:
    """Retorna quantas questões já existem para o par materia/topico."""
    try:
        docs = (
            db.collection("questoes")
              .where("materia", "==", materia)
              .where("topico", "==", topico)
              .limit(minimo)
              .stream()
        )
        return sum(1 for _ in docs)
    except Exception as e:
        print(f"   ⚠ Erro ao checar existentes: {e}")
        return 0


def gerar_questoes(materia: str, nome_materia: str, topico: str, quantidade: int) -> tuple[list, dict]:
    """
    Gera questões via Gemini para um tópico, usando livros + provas como reforço.
    Retorna (lista_de_questoes, info_das_fontes).
    """
    # ─── REFORÇO ───
    livros = buscar_livros_para_materia(materia)
    provas = buscar_provas_para_materia(materia)

    contexto_livros = montar_contexto_livros(livros)
    contexto_provas = montar_contexto_provas(provas)

    # Resumo das fontes
    fontes_info = {
        "livros": [{"titulo": l["titulo"], "disciplina": l["disciplina"]} for l in livros],
        "provas": [{"concurso": p["concurso"], "ano": p["ano"], "area": p["area"]} for p in provas],
    }

    if livros: print(f"      📚 Reforço: {len(livros)} livro(s)")
    if provas: print(f"      📄 Reforço: {len(provas)} prova(s) oficial(is)")

    # ─── CADEIA DE FONTES (fallback) ───
    if provas or livros:
        instrucao_fonte = (
            "REGRAS:\n"
            "- O ESTILO ENADE é a referência principal\n"
            "- As PROVAS OFICIAIS (se houver) são referência de estilo e abrangência\n"
            "- Os LIVROS (se houver) servem como reforço de conteúdo\n"
            "- NÃO copie questões nem trechos literais\n"
            "- Crie questões INÉDITAS combinando o melhor de cada fonte"
        )
    else:
        instrucao_fonte = (
            "REGRAS:\n"
            f"- Não há provas/livros cadastrados para '{materia}'\n"
            "- Use seu CONHECIMENTO sobre o tema para criar questões de qualidade\n"
            "- Mantenha o ESTILO ENADE: contextualizadas, interdisciplinares\n"
            "- Garanta precisão factual e gabaritos corretos\n"
            "- NÃO invente fatos; baseie-se em conhecimento consolidado"
        )

    prompt = f"""
Você é um professor especialista no ENADE Formação Geral.

Gere {quantidade} questões inéditas sobre '{topico.replace('_', ' ')}' de {nome_materia}.
Use contextos variados. Estilo ENADE: contextualizadas, interdisciplinares, nível universitário.

{instrucao_fonte}

{contexto_provas}{contexto_livros}

Retorne SOMENTE um JSON válido, sem markdown:
[
  {{
    "numero": 1,
    "contexto": "tema do contexto",
    "enunciado": "enunciado completo",
    "alternativas": {{ "A": "...", "B": "...", "C": "...", "D": "...", "E": "..." }},
    "gabarito": "letra correta",
    "explicacao": "explicação didática em 2 parágrafos"
  }}
]
"""
    resposta = modelo.generate_content(
        prompt,
        generation_config={
            "max_output_tokens":  15000,
            "temperature":        0.7,
            "response_mime_type": "application/json",
        }
    )

    raw = resposta.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw), fontes_info


def popular(por_topico: int, forcar: bool, materia_filtro: str = None):
    """Popula o banco respeitando a regra de não-regenerar."""
    print("\n" + "=" * 60)
    print("  POPULANDO BANCO DE QUESTÕES")
    print(f"  Questões por tópico: {por_topico} | Forçar: {forcar}")
    print("=" * 60)

    total_geradas = 0
    total_puladas = 0
    chamadas_gemini = 0

    for materia_id, config in MATERIAS_TOPICOS.items():
        if materia_filtro and materia_id != materia_filtro:
            continue

        print(f"\n📚 {config['nome']}")

        for topico in config["topicos"]:
            # REGRA: pula se já tem questões suficientes (a menos que forçar)
            if not forcar:
                existentes = ja_tem_questoes(materia_id, topico, por_topico)
                if existentes >= por_topico:
                    print(f"   ⏭  {topico} — já tem {existentes} questões, pulando")
                    total_puladas += 1
                    continue

            print(f"   🤖 {topico} — gerando {por_topico} questões...")

            try:
                questoes, fontes_info = gerar_questoes(materia_id, config["nome"], topico, por_topico)
                chamadas_gemini += 1

                # Salva cada questão (com info das fontes usadas)
                for q in questoes:
                    questao_id = str(uuid.uuid4())
                    db.collection("questoes").document(questao_id).set({
                        "questao_id":   questao_id,
                        "materia":      materia_id,
                        "topico":       topico,
                        "contexto":     q.get("contexto", ""),
                        "enunciado":    q.get("enunciado", ""),
                        "alternativas": q.get("alternativas", {}),
                        "gabarito":     q.get("gabarito", ""),
                        "explicacao":   q.get("explicacao", ""),
                        "origem":       "popular_banco",
                        "fontes":       fontes_info,
                        "criado_em":    datetime.now(timezone.utc),
                    })
                    total_geradas += 1

                print(f"      ✅ {len(questoes)} questões salvas")

                # Pausa pra respeitar limite por minuto (15 RPM)
                time.sleep(4)

            except Exception as e:
                print(f"      ❌ Erro: {e}")
                continue

    print("\n" + "=" * 60)
    print(f"  ✅ CONCLUÍDO")
    print(f"     Questões geradas:  {total_geradas}")
    print(f"     Tópicos pulados:   {total_puladas} (já tinham questões)")
    print(f"     Chamadas Gemini:   {chamadas_gemini}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Popula o banco de questões do Nivelis.")
    parser.add_argument("--por-topico", type=int, default=QUESTOES_POR_TOPICO,
                        help="Quantas questões gerar por tópico (padrão 5)")
    parser.add_argument("--forcar", action="store_true",
                        help="Regenera mesmo se já existir (cuidado: gasta Gemini)")
    parser.add_argument("--materia", type=str, default=None,
                        help="Popular só uma matéria específica")

    args = parser.parse_args()
    popular(args.por_topico, args.forcar, args.materia)
