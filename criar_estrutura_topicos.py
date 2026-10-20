"""
=============================================================
  NIVELIS — Criar Estrutura de Tópicos (SEM GERAR QUESTÕES)
=============================================================

  Este script cria a estrutura no Firebase com os tópicos das
  matérias, mas SEM gerar questões.

  Use quando quiser apenas montar o catálogo no banco para o
  app já listar as matérias/tópicos disponíveis. As questões
  podem ser geradas depois, uma matéria por vez, via Gemini.

  COMO USAR:
    1. Certifique-se que o chave-firebase.json está na pasta
    2. Rode: python criar_estrutura_topicos.py
    3. Pronto — sem custo de quota Gemini

  DIFERENÇA PARA popular_banco.py:
    - popular_banco.py:           cria tópicos E gera questões com Gemini
    - criar_estrutura_topicos.py: só cria a estrutura no Firebase

=============================================================
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime       import datetime, timezone

# ──────────────────────────────────────────
#  FIREBASE
# ──────────────────────────────────────────

cred = credentials.Certificate("chave-firebase.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ──────────────────────────────────────────
#  MATÉRIAS E TÓPICOS DO ENADE FORMAÇÃO GERAL
# ──────────────────────────────────────────

MATERIAS_TOPICOS = {

    "portugues": {
        "nome_exibicao": "Português",
        "ordem": 1,
        "icone": "📝",
        "topicos": [
            "Interpretação e compreensão de textos",
            "Tipologia e gêneros textuais",
            "Coesão e coerência textual",
            "Argumentação e dissertação",
            "Variação linguística",
            "Figuras de linguagem",
            "Concordância verbal e nominal",
            "Regência verbal e nominal",
        ]
    },

    "matematica": {
        "nome_exibicao": "Matemática",
        "ordem": 2,
        "icone": "🔢",
        "topicos": [
            "Raciocínio lógico e matemático",
            "Conjuntos e operações",
            "Proporcionalidade e porcentagem",
            "Funções e gráficos",
            "Estatística e probabilidade",
            "Geometria plana e espacial",
            "Progressões aritméticas e geométricas",
            "Matemática financeira",
        ]
    },

    "atualidades": {
        "nome_exibicao": "Atualidades",
        "ordem": 3,
        "icone": "📰",
        "topicos": [
            "Política nacional e internacional",
            "Economia e mercado de trabalho",
            "Meio ambiente e sustentabilidade",
            "Ciência e tecnologia",
            "Cultura e sociedade brasileira",
            "Direitos humanos e cidadania",
            "Saúde pública e epidemiologia",
        ]
    },

    "filosofia": {
        "nome_exibicao": "Filosofia",
        "ordem": 4,
        "icone": "🤔",
        "topicos": [
            "Ética e moral",
            "Filosofia política e cidadania",
            "Epistemologia e teoria do conhecimento",
            "Lógica e argumentação filosófica",
            "Filosofia da ciência",
        ]
    },

    "sociologia": {
        "nome_exibicao": "Sociologia",
        "ordem": 5,
        "icone": "👥",
        "topicos": [
            "Estrutura social e desigualdade",
            "Cultura e identidade",
            "Trabalho e relações sociais",
            "Estado, sociedade e cidadania",
            "Movimentos sociais e mudança",
        ]
    },

}


def criar_estrutura():
    """
    Cria as coleções no Firebase com a estrutura básica de matérias e tópicos.
    Não gera questões — só estrutura.
    """
    print("\n" + "=" * 60)
    print("  CRIANDO ESTRUTURA DE MATÉRIAS E TÓPICOS")
    print("=" * 60)

    total_topicos = 0

    for materia_id, config in MATERIAS_TOPICOS.items():
        print(f"\n📚 Matéria: {config['nome_exibicao']}")

        # Cria o documento da matéria
        doc_materia = {
            "id":              materia_id,
            "nome_exibicao":   config["nome_exibicao"],
            "icone":           config["icone"],
            "ordem":           config["ordem"],
            "total_topicos":   len(config["topicos"]),
            "criado_em":       datetime.now(timezone.utc),
        }
        db.collection("materias").document(materia_id).set(doc_materia, merge=True)

        # Cria cada tópico como subcoleção
        for i, topico_nome in enumerate(config["topicos"], start=1):
            topico_slug = topico_nome.lower().replace(" ", "_").replace("ç", "c") \
                .replace("ã", "a").replace("õ", "o").replace("á", "a") \
                .replace("é", "e").replace("í", "i").replace("ó", "o") \
                .replace("ú", "u").replace("â", "a").replace("ê", "e") \
                .replace("ô", "o").replace(",", "").replace(":", "")

            doc_topico = {
                "id":             topico_slug,
                "nome_exibicao":  topico_nome,
                "materia":        materia_id,
                "ordem":          i,
                "total_questoes": 0,  # vai ser atualizado quando popular questões
                "criado_em":      datetime.now(timezone.utc),
            }
            db.collection("materias").document(materia_id) \
              .collection("topicos").document(topico_slug).set(doc_topico, merge=True)

            print(f"   ✓ {topico_nome}")
            total_topicos += 1

    print("\n" + "=" * 60)
    print(f"  ✅ ESTRUTURA CRIADA: {len(MATERIAS_TOPICOS)} matérias, {total_topicos} tópicos")
    print("=" * 60)
    print("\nPróximo passo:")
    print("  Para gerar questões de uma matéria, use popular_banco.py")
    print("  ou crie um simulado via POST /enade/inspirar\n")


if __name__ == "__main__":
    criar_estrutura()
