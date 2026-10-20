"""
limpar_questoes.py
Detecta questoes na colecao 'questoes' com explicacao "baguncada" — aquelas
onde a IA vazou o rascunho de raciocinio (frases como "houve um erro",
"vamos refazer", "valor incorreto para pi", etc).

MODO SEGURO: roda primeiro em ANALISE (so mostra, nao muda nada).
Depois voce escolhe o que fazer.

COMO RODAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python limpar_questoes.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import re

# ─── Inicializa Firebase ──────────────────────────────────────────────────────
def init_firebase():
    nomes_possiveis = [
        "chave-firebase.json", "chave-nivelis.json",
        "serviceAccountKey.json", "firebase-key.json",
    ]
    chave = next((n for n in nomes_possiveis if os.path.exists(n)), None)
    if not chave:
        print("❌ ERRO: Não achei o arquivo de chave do Firebase!")
        print(f"   Procurei por: {', '.join(nomes_possiveis)}")
        print("   RODE NA PASTA DO BACKEND: K:\\nivelis-teste\\Nivelis-Api")
        exit(1)
    print(f"🔑 Usando chave: {chave}\n")
    if not firebase_admin._apps:
        cred = credentials.Certificate(chave)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ─── Sinais de explicação "bagunçada" ─────────────────────────────────────────
# Frases que indicam que a IA vazou o rascunho dela em vez de explicar limpo.
SINAIS_RUINS = [
    "houve um erro",
    "vamos refazer",
    "vamos recalcular",
    "vamos verificar",
    "vamos assumir",
    "vamos manter",
    "valor incorreto",
    "está inconsistente",
    "esta inconsistente",
    "a questão está inconsistente",
    "no meu cálculo",
    "no meu calculo",
    "erro no meu",
    "ajustar alternativas",
    "nova alternativa",
    "o gabarito é",  # quando aparece no meio explicando o próprio gabarito
    "vamos calcular novamente",
    "refazendo",
    "corrigindo",
    "me enganei",
]

# Tamanho acima do qual a explicação é "suspeita" de ter rascunho
TAMANHO_SUSPEITO = 600  # caracteres


def explicacao_eh_ruim(texto: str) -> tuple[bool, list[str]]:
    """Retorna (eh_ruim, lista_de_sinais_encontrados)."""
    if not texto:
        return False, []
    t = texto.lower()
    encontrados = [s for s in SINAIS_RUINS if s in t]
    # É ruim se: tem sinais claros OU é muito longa E tem pelo menos 1 sinal fraco
    eh_ruim = len(encontrados) > 0
    return eh_ruim, encontrados


# ─── Análise ──────────────────────────────────────────────────────────────────
def analisar(db):
    print("=" * 70)
    print("ANÁLISE: procurando explicações bagunçadas em 'questoes'")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    print(f"\n📊 Total de questões: {len(docs)}\n")

    ruins = []      # (doc_id, materia, sinais, tamanho)
    longas = []     # explicações muito longas (suspeitas, mas sem sinal claro)
    sem_explicacao = 0

    for doc in docs:
        data = doc.to_dict()
        doc_id = doc.id
        materia = data.get("materia", "(sem materia)")

        # Campo de explicação (vários nomes possíveis)
        expl = data.get("explicacao_ia") or data.get("explicacao") or ""

        if not expl:
            sem_explicacao += 1
            continue

        eh_ruim, sinais = explicacao_eh_ruim(expl)
        if eh_ruim:
            ruins.append((doc_id, materia, sinais, len(expl)))
        elif len(expl) > TAMANHO_SUSPEITO:
            longas.append((doc_id, materia, len(expl)))

    # ─── Relatório ────────────────────────────────────────────────────────────
    print(f"🔴 Questões com explicação BAGUNÇADA: {len(ruins)}")
    print(f"🟡 Questões com explicação muito longa (suspeita): {len(longas)}")
    print(f"⚪ Questões sem explicação: {sem_explicacao}")
    print(f"🟢 Questões OK: {len(docs) - len(ruins) - len(longas) - sem_explicacao}")

    if ruins:
        print("\n" + "─" * 70)
        print("DETALHE das bagunçadas (até 20):")
        print("─" * 70)
        for doc_id, materia, sinais, tam in ruins[:20]:
            print(f"\n  ID: {doc_id}")
            print(f"  Matéria: {materia} | Tamanho: {tam} chars")
            print(f"  Sinais encontrados: {', '.join(sinais[:3])}")

    # Conta por matéria
    if ruins:
        por_materia = {}
        for _, materia, _, _ in ruins:
            por_materia[materia] = por_materia.get(materia, 0) + 1
        print("\n" + "─" * 70)
        print("Bagunçadas por matéria:")
        print("─" * 70)
        for materia, n in sorted(por_materia.items(), key=lambda x: -x[1]):
            print(f"  {materia}: {n}")

    return ruins, longas


# ─── Limpeza ──────────────────────────────────────────────────────────────────
def limpar(db, ruins, modo):
    """
    modo='remover_explicacao': apaga só o campo de explicação (mantém a questão)
    modo='desativar_questao':  marca ativo=False (some do app, mas fica no banco)
    """
    print("\n" + "=" * 70)
    print(f"LIMPANDO {len(ruins)} questões — modo: {modo}")
    print("=" * 70)

    batch = db.batch()
    contador = 0

    for doc_id, materia, sinais, tam in ruins:
        ref = db.collection("questoes").document(doc_id)
        if modo == "remover_explicacao":
            # Remove os dois campos possíveis de explicação
            batch.update(ref, {
                "explicacao_ia": firestore.DELETE_FIELD,
                "explicacao": firestore.DELETE_FIELD,
            })
        elif modo == "desativar_questao":
            batch.update(ref, {"ativo": False})

        contador += 1
        # Firestore aceita até 500 operações por batch
        if contador % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  ... {contador} processadas")

    batch.commit()
    print(f"\n✅ {contador} questões processadas com sucesso!")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🧹 LIMPEZA DE QUESTÕES BAGUNÇADAS — NIVELIS\n")
    db = init_firebase()

    ruins, longas = analisar(db)

    if not ruins:
        print("\n🎉 Nenhuma questão bagunçada encontrada! Banco limpo.")
        exit(0)

    # ─── Menu de ação ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("O QUE FAZER?")
    print("=" * 70)
    print(f"\nEncontradas {len(ruins)} questões com explicação bagunçada.\n")
    print("  [1] Remover só a EXPLICAÇÃO (mantém a questão, tira o texto ruim)")
    print("  [2] Desativar a QUESTÃO inteira (ativo=False, some do app)")
    print("  [3] Não fazer nada (sair)")
    print()

    escolha = input("Digite 1, 2 ou 3: ").strip()

    if escolha == "1":
        confirma = input(f"\n⚠️  Confirma REMOVER explicação de {len(ruins)} questões? (sim/nao): ").strip().lower()
        if confirma == "sim":
            limpar(db, ruins, "remover_explicacao")
        else:
            print("Cancelado.")
    elif escolha == "2":
        confirma = input(f"\n⚠️  Confirma DESATIVAR {len(ruins)} questões? (sim/nao): ").strip().lower()
        if confirma == "sim":
            limpar(db, ruins, "desativar_questao")
        else:
            print("Cancelado.")
    else:
        print("\nNada foi alterado. Até mais!")

    print("\n" + "=" * 70)
    print("Pronto!")
    print("=" * 70)
