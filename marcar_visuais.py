"""
=============================================================
  NIVELIS — Marcador de Questões com Elemento Visual
=============================================================

  Detecta questões que dependem de imagem/gráfico/tabela que
  NÃO aparece no app (só a descrição em texto). Essas questões
  são impossíveis de responder, então marcamos pra tela filtrar.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python marcar_visuais.py

  MODO SEGURO:
    - Primeiro só ANALISA (mostra quantas, não muda nada)
    - Você confirma antes de marcar
    - Marca com campo 'tem_visual_quebrado: true' (não deleta)
    - A tela de Questões filtra essas (não mostra)

=============================================================
"""

import os
import sys
import re
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
#  Detecção de elemento visual quebrado
# ──────────────────────────────────────────
# Padrões que indicam referência a imagem/gráfico/tabela que não aparece
PADROES_VISUAIS = [
    r'\[gr[áa]fico',           # [Gráfico...]
    r'\[imagem',                # [IMAGEM...] [Imagem hipotética...]
    r'\[imagine',               # [Imagine um gráfico...]
    r'\[figura',                # [Figura...]
    r'\[mapa',                  # [MAPA...]
    r'\(imagem hipot',          # (Imagem hipotética...)
    r'\(gr[áa]fico hipot',      # (Gráfico hipotético...)
    r'\bgr[áa]fico a seguir\b', # "o gráfico a seguir"
    r'\bgr[áa]fico abaixo\b',   # "o gráfico abaixo"
    r'\btabela a seguir\b',     # "a tabela a seguir"
    r'\btabela abaixo\b',       # "a tabela abaixo"
    r'\bmapa a seguir\b',
    r'\bimagem a seguir\b',
    r'\bfigura a seguir\b',
    r'gr[áa]fico \d',           # "Gráfico 1"
]

# Frases que sozinhas NÃO significam problema (podem ter a tabela em texto no próprio enunciado)
# Vamos verificar se tem tabela markdown de verdade no texto
def tem_tabela_markdown(texto: str) -> bool:
    """Detecta se tem tabela markdown real (com | e ---) no texto."""
    return bool(re.search(r'\|.*\|.*\n.*\|.*[-].*\|', texto))


def tem_visual_quebrado(data: dict) -> tuple[bool, str]:
    """
    Retorna (tem_problema, motivo).
    Um visual é 'quebrado' se o texto REFERENCIA uma imagem/gráfico
    que não pode ser exibida (não temos como renderizar).
    """
    enunciado = (data.get("enunciado") or "").lower()
    contexto  = (data.get("contexto") or "").lower()
    texto = enunciado + " " + contexto

    # Campo explícito do banco
    if data.get("tem_elemento_visual") is True:
        return True, "campo tem_elemento_visual=true"

    # Procura padrões de referência visual
    for padrao in PADROES_VISUAIS:
        if re.search(padrao, texto):
            # Se for tabela E tiver tabela markdown real, pode estar OK
            # (o app consegue mostrar texto com |)
            if 'tabela' in padrao:
                if tem_tabela_markdown(data.get("enunciado", "") + data.get("contexto", "")):
                    continue  # tem a tabela em texto, não é quebrado
            return True, f"referencia visual: '{padrao}'"

    return False, ""


# ──────────────────────────────────────────
#  Análise
# ──────────────────────────────────────────
def analisar(db):
    print("=" * 70)
    print("ANÁLISE: procurando questões com elemento visual quebrado")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    print(f"\n📊 Total de questões: {len(docs)}\n")

    quebradas = []
    por_materia = {}
    por_motivo = {}

    for doc in docs:
        data = doc.to_dict()
        tem_problema, motivo = tem_visual_quebrado(data)
        if tem_problema:
            materia = data.get("materia", "(sem)")
            quebradas.append({
                "id": doc.id,
                "materia": materia,
                "motivo": motivo,
                "enunciado": (data.get("enunciado") or "")[:60],
            })
            por_materia[materia] = por_materia.get(materia, 0) + 1
            # Simplifica motivo pra estatística
            motivo_simples = motivo.split(":")[0]
            por_motivo[motivo_simples] = por_motivo.get(motivo_simples, 0) + 1

    print(f"🔴 Questões com visual quebrado: {len(quebradas)}")
    print(f"🟢 Questões OK: {len(docs) - len(quebradas)}")

    if por_materia:
        print("\n  Por matéria:")
        for materia, n in sorted(por_materia.items(), key=lambda x: -x[1]):
            print(f"    {materia}: {n}")

    if por_motivo:
        print("\n  Por motivo:")
        for motivo, n in sorted(por_motivo.items(), key=lambda x: -x[1]):
            print(f"    {motivo}: {n}")

    # Mostra amostra
    if quebradas:
        print("\n  Amostra (até 10):")
        for q in quebradas[:10]:
            print(f"    ❌ [{q['materia']}] {q['enunciado']}...")
            print(f"       → {q['motivo']}")

    return quebradas


# ──────────────────────────────────────────
#  Marcar
# ──────────────────────────────────────────
def marcar(db, quebradas):
    print(f"\n🏷️  Marcando {len(quebradas)} questões com 'tem_visual_quebrado: true'...")
    batch = db.batch()
    contador = 0
    for q in quebradas:
        ref = db.collection("questoes").document(q["id"])
        batch.update(ref, {"tem_visual_quebrado": True})
        contador += 1
        if contador % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"    ... {contador}")
    batch.commit()
    print(f"  ✅ {contador} questões marcadas!")


def desmarcar(db):
    """Remove a marca de todas (pra reverter, se precisar)."""
    print("\n🔄 Removendo marca 'tem_visual_quebrado' de todas...")
    docs = list(db.collection("questoes").where("tem_visual_quebrado", "==", True).stream())
    batch = db.batch()
    contador = 0
    for doc in docs:
        batch.update(doc.reference, {"tem_visual_quebrado": firestore.DELETE_FIELD})
        contador += 1
        if contador % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    print(f"  ✅ {contador} marcas removidas!")


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n🖼️  MARCADOR DE QUESTÕES COM ELEMENTO VISUAL — NIVELIS\n")

    # Modo reverter?
    if len(sys.argv) > 1 and sys.argv[1] == "--reverter":
        desmarcar(db)
        sys.exit(0)

    quebradas = analisar(db)

    if not quebradas:
        print("\n🎉 Nenhuma questão com visual quebrado! Tudo certo.")
        sys.exit(0)

    print("\n" + "=" * 70)
    print("O QUE FAZER?")
    print("=" * 70)
    print(f"\n  Encontradas {len(quebradas)} questões que referenciam imagem/gráfico")
    print("  que o app não consegue mostrar (aluno não consegue responder).\n")
    print("  [1] Marcar essas questões (tela vai filtrar/esconder elas)")
    print("  [2] Não fazer nada (sair)")
    print("\n  (Pra reverter depois: python marcar_visuais.py --reverter)")
    print()

    escolha = input("Digite 1 ou 2: ").strip()

    if escolha == "1":
        confirma = input(f"\n⚠️  Confirma marcar {len(quebradas)} questões? (sim/nao): ").strip().lower()
        if confirma in ("sim", "s", "y", "yes"):
            marcar(db, quebradas)
            print("\n✅ Pronto! Agora atualize a tela de Questões pra filtrar as marcadas.")
            print("   (Vou te passar o ajuste no apiService/tela.)")
        else:
            print("Cancelado.")
    else:
        print("\nNada foi alterado.")

    print("\n" + "=" * 70)
    print("Concluído!")
    print("=" * 70)
