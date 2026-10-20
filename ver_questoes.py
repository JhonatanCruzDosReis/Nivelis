"""
=============================================================
  NIVELIS — Visualizador de Questões
=============================================================

  Mostra uma amostra de questões do banco no terminal,
  com enunciado + alternativas + gabarito + explicação.
  Ideal pra copiar e passar pro Claude analisar.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api

    # 20 questões aleatórias de qualquer matéria:
    python ver_questoes.py

    # 20 questões de uma matéria específica:
    python ver_questoes.py matematica
    python ver_questoes.py direito
    python ver_questoes.py humanas

    # Quantidade diferente (ex: 10):
    python ver_questoes.py matematica 10

=============================================================
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────
if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    if not os.path.exists(chave):
        print("❌ Não achei a chave do Firebase!")
        print("   Rode na pasta do backend: K:\\nivelis-teste\\Nivelis-Api")
        sys.exit(1)
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  Formata alternativas (lista ou dict)
# ──────────────────────────────────────────
def formatar_alternativas(alternativas) -> list[str]:
    linhas = []
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                letra = alt.get("id") or alt.get("letra") or "?"
                texto = alt.get("texto") or alt.get("text") or ""
                linhas.append(f"    {letra}) {texto}")
            else:
                linhas.append(f"    - {alt}")
    elif isinstance(alternativas, dict):
        for letra, texto in sorted(alternativas.items()):
            linhas.append(f"    {letra}) {texto}")
    return linhas


# ──────────────────────────────────────────
#  Mostra uma questão formatada
# ──────────────────────────────────────────
def mostrar_questao(i, data):
    materia   = data.get("materia", "(sem materia)")
    enunciado = data.get("enunciado", "(sem enunciado)")
    gabarito  = data.get("gabarito", "(sem gabarito)")
    expl      = data.get("explicacao_ia") or data.get("explicacao") or "(sem explicação)"
    contexto  = data.get("contexto", "")
    tem_visual = data.get("tem_elemento_visual", False)

    print("\n" + "═" * 70)
    print(f"QUESTÃO {i} | Matéria: {materia}" + ("  [TEM ELEMENTO VISUAL]" if tem_visual else ""))
    print("═" * 70)

    if contexto:
        print(f"\n📄 CONTEXTO:\n{contexto}")

    print(f"\n❓ ENUNCIADO:\n{enunciado}")

    print(f"\n📝 ALTERNATIVAS:")
    for linha in formatar_alternativas(data.get("alternativas")):
        print(linha)

    print(f"\n✅ GABARITO: {gabarito}")

    print(f"\n💡 EXPLICAÇÃO:\n{expl}")


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    # Argumentos: [materia] [quantidade]
    materia_filtro = None
    quantidade = 20

    if len(sys.argv) >= 2:
        materia_filtro = sys.argv[1].lower()
    if len(sys.argv) >= 3:
        try:
            quantidade = int(sys.argv[2])
        except ValueError:
            pass

    print("\n📚 VISUALIZADOR DE QUESTÕES — NIVELIS")
    if materia_filtro:
        print(f"   Filtro de matéria: {materia_filtro}")
    print(f"   Mostrando até: {quantidade} questões\n")

    # Busca as questões
    docs = list(db.collection("questoes").stream())
    print(f"📊 Total no banco: {len(docs)} questões")

    # Filtra por matéria se pedido
    selecionadas = []
    for doc in docs:
        data = doc.to_dict()
        mat = (data.get("materia") or "").lower()
        if materia_filtro:
            # Compara flexível (matematica pega Matemática também)
            if materia_filtro in mat or mat in materia_filtro:
                selecionadas.append(data)
        else:
            selecionadas.append(data)

    if materia_filtro:
        print(f"🔍 Com matéria '{materia_filtro}': {len(selecionadas)} questões")

    if not selecionadas:
        print("\n❌ Nenhuma questão encontrada com esse filtro.")
        print("   Matérias disponíveis:")
        materias = {}
        for doc in docs:
            m = doc.to_dict().get("materia", "(sem)")
            materias[m] = materias.get(m, 0) + 1
        for m, n in sorted(materias.items()):
            print(f"      {m}: {n}")
        sys.exit(0)

    # Limita à quantidade pedida
    mostrar = selecionadas[:quantidade]

    print(f"\n{'▼' * 35}")
    print(f"MOSTRANDO {len(mostrar)} QUESTÕES (copie tudo abaixo pro Claude)")
    print(f"{'▼' * 35}")

    for i, data in enumerate(mostrar, start=1):
        mostrar_questao(i, data)

    print("\n" + "═" * 70)
    print(f"FIM — {len(mostrar)} questões mostradas.")
    print("═" * 70)
    print("\n👆 Copie desde 'MOSTRANDO X QUESTÕES' até aqui e cole pro Claude.\n")
