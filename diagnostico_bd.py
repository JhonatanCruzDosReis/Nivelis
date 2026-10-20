"""
diagnostico_bd.py
Lê a coleção 'simulados' do Firestore e mostra a estrutura real de cada um.
Ajuda a entender por que a tela de Questões mostra "Demo" em vez das questões reais.

COMO RODAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python diagnostico_bd.py

Precisa do arquivo de chave do Firebase (chave-firebase.json ou chave-nivelis.json)
na mesma pasta.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# ─── Inicializa Firebase ──────────────────────────────────────────────────────
def init_firebase():
    # Tenta achar o arquivo de chave (vários nomes possíveis)
    nomes_possiveis = [
        "chave-firebase.json",
        "chave-nivelis.json",
        "serviceAccountKey.json",
        "firebase-key.json",
    ]
    chave = None
    for nome in nomes_possiveis:
        if os.path.exists(nome):
            chave = nome
            break

    if not chave:
        print("❌ ERRO: Não achei o arquivo de chave do Firebase!")
        print(f"   Procurei por: {', '.join(nomes_possiveis)}")
        print("   Coloque o arquivo de chave nesta pasta e rode de novo.")
        exit(1)

    print(f"🔑 Usando chave: {chave}\n")
    if not firebase_admin._apps:
        cred = credentials.Certificate(chave)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ─── Análise dos simulados ────────────────────────────────────────────────────
def analisar_simulados(db):
    print("=" * 70)
    print("ANÁLISE DA COLEÇÃO 'simulados'")
    print("=" * 70)

    docs = list(db.collection("simulados").stream())
    print(f"\n📊 Total de documentos: {len(docs)}\n")

    # Contadores
    com_questoes_embarcadas = 0
    sem_questoes = 0
    por_tipo = {}
    por_fonte = {}

    # Detalhe de cada um
    for i, doc in enumerate(docs):
        data = doc.to_dict()
        doc_id = doc.id

        # Campos principais
        titulo = data.get("titulo", "(sem título)")
        tipo = data.get("tipo", "(sem tipo)")
        fonte = data.get("fonte") or data.get("meta", {}).get("fonte", "(sem fonte)")
        disciplina = data.get("disciplina") or data.get("meta", {}).get("disciplina", "")
        total_q = data.get("total_questoes", 0)

        # O campo 'questoes' tem array?
        questoes = data.get("questoes")
        tem_array = isinstance(questoes, list)
        n_questoes_reais = len(questoes) if tem_array else 0

        # Contadores
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        por_fonte[str(fonte)] = por_fonte.get(str(fonte), 0) + 1
        if n_questoes_reais > 0:
            com_questoes_embarcadas += 1
        else:
            sem_questoes += 1

        # Mostra só os primeiros 15 em detalhe (pra não poluir)
        if i < 15:
            status = "✅" if n_questoes_reais > 0 else "❌"
            print(f"{status} [{i+1}] {titulo[:45]}")
            print(f"     ID: {doc_id}")
            print(f"     tipo: {tipo} | disciplina: {disciplina} | fonte: {fonte}")
            print(f"     total_questoes (campo): {total_q}")
            print(f"     questoes (array real): {n_questoes_reais} questões")

            # Se tem questões, mostra a estrutura da primeira
            if n_questoes_reais > 0:
                q0 = questoes[0]
                campos_q = list(q0.keys()) if isinstance(q0, dict) else []
                print(f"     → Campos de uma questão: {campos_q}")
                # Mostra enunciado curto
                enunciado = q0.get("enunciado", "")[:60] if isinstance(q0, dict) else ""
                print(f"     → Exemplo enunciado: {enunciado}...")
                # Verifica se tem alternativas e gabarito
                tem_alt = "alternativas" in q0 if isinstance(q0, dict) else False
                tem_gab = "gabarito" in q0 if isinstance(q0, dict) else False
                print(f"     → tem alternativas: {tem_alt} | tem gabarito: {tem_gab}")
            print()

    # ─── Resumo ───────────────────────────────────────────────────────────────
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"\n✅ Simulados COM questões embarcadas: {com_questoes_embarcadas}")
    print(f"❌ Simulados SEM questões (vazios):   {sem_questoes}")

    print(f"\n📂 Por tipo:")
    for tipo, n in sorted(por_tipo.items()):
        print(f"   {tipo}: {n}")

    print(f"\n🔗 Por fonte:")
    for fonte, n in sorted(por_fonte.items()):
        print(f"   {fonte}: {n}")

    # ─── Diagnóstico ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO")
    print("=" * 70)

    if com_questoes_embarcadas == 0:
        print("\n⚠️  PROBLEMA: Nenhum simulado tem questões embarcadas!")
        print("   Por isso a tela de Questões mostra 'Demo'.")
        print("   As questões podem estar na coleção 'questoes' separada,")
        print("   ou precisam ser geradas via /livro/inspirar.")
    else:
        print(f"\n✅ {com_questoes_embarcadas} simulados têm questões prontas.")
        print("   A tela de Questões DEVERIA mostrar essas.")
        print("   Se mostra 'Demo', o problema é no filtro de tipo (ENEM vs ENADE).")


# ─── Análise da coleção 'questoes' (separada) ─────────────────────────────────
def analisar_questoes_avulsas(db):
    print("\n" + "=" * 70)
    print("ANÁLISE DA COLEÇÃO 'questoes' (avulsas)")
    print("=" * 70)

    docs = list(db.collection("questoes").limit(100).stream())
    print(f"\n📊 Total de documentos (limitado a 100): {len(docs)}\n")

    if len(docs) == 0:
        print("   (vazia)")
        return

    por_tipo = {}
    por_materia = {}
    for doc in docs:
        data = doc.to_dict()
        tipo = data.get("tipo", "(sem tipo)")
        materia = data.get("materia", "(sem materia)")
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        por_materia[materia] = por_materia.get(materia, 0) + 1

    print("📂 Por tipo:")
    for tipo, n in sorted(por_tipo.items()):
        print(f"   {tipo}: {n}")

    print("\n📚 Por matéria:")
    for materia, n in sorted(por_materia.items()):
        print(f"   {materia}: {n}")

    # Mostra estrutura de uma questão
    q0 = docs[0].to_dict()
    print(f"\n→ Campos de uma questão avulsa: {list(q0.keys())}")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 DIAGNÓSTICO DO BANCO DE DADOS NIVELIS\n")
    db = init_firebase()

    analisar_simulados(db)
    analisar_questoes_avulsas(db)

    print("\n" + "=" * 70)
    print("✅ Diagnóstico completo!")
    print("=" * 70)
    print("\nCopia TODO esse resultado e cola pro Claude analisar.\n")
