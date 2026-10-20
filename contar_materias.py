"""
=============================================================
  NIVELIS — Contador de Matérias
=============================================================
  Mostra quantas questões tem de cada matéria, separado por
  tipo (ENEM/ENADE) e considerando os filtros do app.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python contar_materias.py
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

# Mapa area -> materias (igual ao apiService v13)
AREA_MATERIAS = {
    'humanas':    ['sociologia', 'historia', 'história', 'geografia', 'filosofia', 'humanas'],
    'natureza':   ['biologia', 'fisica', 'física', 'quimica', 'química', 'natureza'],
    'linguagens': ['linguagens', 'portugues', 'português', 'literatura', 'ingles', 'inglês', 'espanhol'],
    'matematica': ['matematica', 'matemática'],
    'atualidades':['atualidades'],
}

if __name__ == "__main__":
    print("\n📊 CONTADOR DE MATÉRIAS — NIVELIS\n")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    print(f"Total de questões no banco: {len(docs)}\n")

    # Conta por materia, e separa quebradas/validas
    por_materia = {}
    por_materia_valida = {}   # sem visual quebrado
    por_tipo = {}
    materia_x_tipo = {}

    for doc in docs:
        data = doc.to_dict()
        materia = (data.get("materia") or "(vazio)").lower().strip()
        # tipo pode estar em 'tipo' ou 'concurso'
        tipo = (data.get("tipo") or data.get("concurso") or "(sem tipo)").upper()
        quebrada = data.get("tem_visual_quebrado") is True

        por_materia[materia] = por_materia.get(materia, 0) + 1
        if not quebrada:
            por_materia_valida[materia] = por_materia_valida.get(materia, 0) + 1
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        chave = f"{tipo} | {materia}"
        materia_x_tipo[chave] = materia_x_tipo.get(chave, 0) + 1

    # ─── Matérias (todas) ───
    print("MATÉRIAS NO BANCO (todas | válidas sem visual quebrado):")
    print("-" * 70)
    for mat, n in sorted(por_materia.items(), key=lambda x: -x[1]):
        validas = por_materia_valida.get(mat, 0)
        print(f"  {mat:35} {n:4} total | {validas:4} válidas")

    # ─── Tipos ───
    print("\n" + "-" * 70)
    print("POR TIPO/CONCURSO:")
    print("-" * 70)
    for tipo, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:20} {n:4}")

    # ─── Matéria x Tipo ───
    print("\n" + "-" * 70)
    print("MATÉRIA x TIPO (como o app vê):")
    print("-" * 70)
    for chave, n in sorted(materia_x_tipo.items()):
        print(f"  {chave:45} {n:4}")

    # ─── Simulação dos filtros do app ───
    print("\n" + "=" * 70)
    print("SIMULAÇÃO DOS BOTÕES DO APP (área → quantas questões válidas):")
    print("=" * 70)

    for area, alvos in AREA_MATERIAS.items():
        # conta validas cujas materia bate com algum alvo
        count_enem = 0
        count_enade = 0
        for doc in docs:
            data = doc.to_dict()
            if data.get("tem_visual_quebrado") is True:
                continue
            m = (data.get("materia") or "").lower().strip()
            tipo = (data.get("tipo") or data.get("concurso") or "").upper()
            bate = any(m == alvo or (alvo in m) or (m in alvo and m != "") for alvo in alvos)
            if bate:
                if "ENEM" in tipo:
                    count_enem += 1
                elif "ENADE" in tipo:
                    count_enade += 1
        print(f"  {area:15} → ENEM: {count_enem:3} | ENADE: {count_enade:3}")

    print("\n" + "=" * 70)
    print("Concluído!")
    print("=" * 70)
