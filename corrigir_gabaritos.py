"""
=============================================================
  NIVELIS — Corretor de Gabaritos (busca por prefixo)
=============================================================
  Corrige os 9 gabaritos confirmados errados. Como os IDs
  mostrados eram truncados (8 chars), este script busca as
  questoes pelo INICIO do id e confirma pelo gabarito atual.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python corrigir_gabaritos.py
=============================================================
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    if not os.path.exists(chave):
        print("Nao achei a chave do Firebase! Rode na pasta do backend.")
        sys.exit(1)
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# prefixo_id -> (gabarito_errado, gabarito_correto, motivo)
CORRECOES = {
    "5LlqiJgW": ("B", "A", "Desconto 15% de 2.500 = 2.125 (alt A)"),
    "GLiXZu4x": ("C", "B", "Volume cilindro 3,14*9*10 = 282,6 (alt B)"),
    "H25eo0dC": ("B", "A", "C(7,2)*C(5,2) = 21*10 = 210 (alt A)"),
    "MCGa7ZcQ": ("D", "C", "375 - 78,54 = 296,5 (alt C)"),
    "NKMsJIKA": ("C", "B", "Volume piramide (1/3)*100*15 = 500 (alt B)"),
    "bMK3PQCY": ("C", "B", "15/50*100 = 30% (alt B)"),
    "kvKkU9NB": ("C", "A", "9*9*8*7 = 4536 (alt A)"),
    "nvWLAlOC": ("C", "B", "120 - 48 = 72 (alt B)"),
    "u4CEcYR6": ("C", "A", "4.000 - 3.000 = 1.000 (alt A)"),
}


def main():
    print("\nCORRETOR DE GABARITOS - NIVELIS (v2, busca por prefixo)\n")
    print("=" * 70)
    print("Carregando questoes do banco...")
    docs = list(db.collection("questoes").stream())
    print(f"  {len(docs)} questoes carregadas.\n")

    print("PLANO DE CORRECAO:\n")
    encontradas = []

    for i, (prefixo, (errado, correto, motivo)) in enumerate(CORRECOES.items(), start=1):
        achado = None
        for doc in docs:
            if doc.id.startswith(prefixo):
                achado = doc
                break

        if achado is None:
            print(f"  [{i}] prefixo '{prefixo}' NAO encontrado")
            continue

        data = achado.to_dict()
        gab_atual = str(data.get("gabarito", "?")).upper()
        enunciado = (data.get("enunciado") or "")[:50]

        status = "OK" if gab_atual == errado else "!!"
        print(f"  [{i}] [{status}] {achado.id[:12]}... | {gab_atual} -> {correto}")
        print(f"       {enunciado}...")
        print(f"       {motivo}")
        if gab_atual != errado:
            print(f"       AVISO: gabarito atual '{gab_atual}' difere do esperado '{errado}'")
            if gab_atual == correto:
                print(f"       (ja esta correto! provavelmente ja corrigido antes)")
        print()

        if gab_atual != correto:
            encontradas.append((achado.id, gab_atual, correto, motivo))

    if not encontradas:
        print("=" * 70)
        print("Nenhuma correcao pendente (ou todas ja corrigidas).")
        return

    print("=" * 70)
    print(f"Aplicar {len(encontradas)} correcoes?")
    resp = input("(sim/nao): ").strip().lower()
    if resp not in ("sim", "s", "y", "yes"):
        print("Cancelado.")
        return

    print("\nAplicando...")
    batch = db.batch()
    for doc_id, gab_atual, correto, motivo in encontradas:
        ref = db.collection("questoes").document(doc_id)
        batch.update(ref, {
            "gabarito": correto,
            "gabarito_anterior": gab_atual,
            "gabarito_corrigido": True,
            "gabarito_suspeito": firestore.DELETE_FIELD,
            "gabarito_suspeito_motivo": firestore.DELETE_FIELD,
            "gabarito_suspeito_detalhe": firestore.DELETE_FIELD,
        })
    batch.commit()
    print(f"  OK! {len(encontradas)} gabaritos corrigidos!")

    print("\n" + "=" * 70)
    print("Concluido! Gabaritos agora batem com as explicacoes.")
    print("=" * 70)


if __name__ == "__main__":
    main()
