"""
=============================================================
  NIVELIS — Ver Gabaritos Suspeitos (completos)
=============================================================
  Mostra as questões marcadas como 'gabarito_suspeito' com
  TODO o conteúdo (enunciado + alternativas + gabarito +
  explicação inteira + o motivo da suspeita).

  Pra você revisar e julgar: é gabarito errado ou explicação cortada?

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python ver_suspeitos.py
=============================================================
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()


def formatar_alternativas(alternativas):
    linhas = []
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                letra = alt.get("id") or alt.get("letra") or "?"
                texto = alt.get("texto") or alt.get("text") or ""
                linhas.append(f"    {letra}) {texto}")
    elif isinstance(alternativas, dict):
        for letra, texto in sorted(alternativas.items()):
            linhas.append(f"    {letra}) {texto}")
    return linhas


if __name__ == "__main__":
    print("\n🔍 GABARITOS SUSPEITOS — REVISÃO COMPLETA\n")

    docs = list(db.collection("questoes").where("gabarito_suspeito", "==", True).stream())
    print(f"📊 Total de suspeitos: {len(docs)}")
    print(f"\n{'▼'*35}")
    print("COPIE TUDO ABAIXO PRO CLAUDE ANALISAR")
    print(f"{'▼'*35}\n")

    for i, doc in enumerate(docs, start=1):
        data = doc.to_dict()
        print("═" * 70)
        print(f"SUSPEITA {i} | Matéria: {data.get('materia')} | id: {doc.id[:8]}")
        print("═" * 70)

        contexto = data.get("contexto", "")
        if contexto:
            print(f"\n📄 CONTEXTO:\n{contexto}")

        print(f"\n❓ ENUNCIADO:\n{data.get('enunciado', '(sem enunciado)')}")

        print(f"\n📝 ALTERNATIVAS:")
        for linha in formatar_alternativas(data.get("alternativas")):
            print(linha)

        print(f"\n✅ GABARITO NO BANCO: {data.get('gabarito')}")

        expl = data.get("explicacao_ia") or data.get("explicacao") or "(sem explicação)"
        print(f"\n💡 EXPLICAÇÃO:\n{expl}")

        print(f"\n🔴 MOTIVO DA SUSPEITA:")
        print(f"   {data.get('gabarito_suspeito_detalhe', '(sem detalhe)')}")
        print()

    print("═" * 70)
    print(f"FIM — {len(docs)} suspeitos mostrados.")
    print("═" * 70)
    print("\n👆 Copie e cole pro Claude analisar quais são gabarito errado")
    print("   vs explicação cortada.\n")
