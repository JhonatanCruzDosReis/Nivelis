"""
=============================================================
  NIVELIS — Migração Firebase
=============================================================

  Copia TODOS os documentos de TODAS as coleções
  do projeto Firebase ANTIGO para o projeto NOVO.

  PRÉ-REQUISITOS:
  1. Ter as DUAS chaves JSON na pasta:
     - chave-firebase.json  (projeto antigo: api-teste-78277)
     - chave-nivelis.json   (projeto novo: nivelis)

  2. Instalar firebase-admin (já tem)

  COMO USAR:
    python migrar_firebase.py                  (modo análise, não copia)
    python migrar_firebase.py --executar       (executa a migração)
    python migrar_firebase.py --executar --sobrescrever
                                               (sobrescreve docs existentes
                                                no banco novo)

  CARACTERÍSTICAS:
  ✅ Lista TODAS as coleções automaticamente (não precisa nomear)
  ✅ Mantém os MESMOS IDs (não quebra referências)
  ✅ Idempotente: pula docs que já existem (a menos que use --sobrescrever)
  ✅ Migra SUB-COLEÇÕES recursivamente
  ✅ Mostra progresso por coleção
  ✅ Logs detalhados de erros

=============================================================
"""

import sys
import argparse
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib        import Path

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────

CHAVE_ANTIGA = "chave-antiga.json"     # projeto antigo (api-teste-78277)
CHAVE_NOVA   = "chave-nivelis.json"    # projeto novo (nivelis)


def validar_arquivos():
    """Confirma que as 2 chaves existem antes de começar."""
    if not Path(CHAVE_ANTIGA).is_file():
        print(f"❌ Arquivo '{CHAVE_ANTIGA}' não encontrado!")
        print(f"   Coloque a chave do projeto antigo nessa pasta.")
        sys.exit(1)

    if not Path(CHAVE_NOVA).is_file():
        print(f"❌ Arquivo '{CHAVE_NOVA}' não encontrado!")
        print(f"   Baixe a chave do projeto novo no Firebase Console")
        print(f"   (Configurações → Contas de serviço → Gerar chave privada)")
        print(f"   Salve como '{CHAVE_NOVA}' nesta pasta.")
        sys.exit(1)


def inicializar_apps():
    """
    Inicializa as duas conexões Firebase com nomes diferentes.
    Retorna (db_antigo, db_novo).
    """
    cred_antiga = credentials.Certificate(CHAVE_ANTIGA)
    cred_nova   = credentials.Certificate(CHAVE_NOVA)

    app_antigo = firebase_admin.initialize_app(cred_antiga, name="antigo")
    app_novo   = firebase_admin.initialize_app(cred_nova,   name="novo")

    db_antigo = firestore.client(app=app_antigo)
    db_novo   = firestore.client(app=app_novo)

    print(f"✅ Conectado nos 2 projetos:")
    print(f"   ANTIGO: {cred_antiga.project_id}")
    print(f"   NOVO:   {cred_nova.project_id}")
    print()

    return db_antigo, db_novo


def migrar_subcolecoes(doc_antigo_ref, doc_novo_ref, executar: bool, sobrescrever: bool, indent: str = "      "):
    """
    Migra recursivamente as sub-coleções de um documento.
    """
    contagem = {"docs": 0, "subcols": 0}

    for sub_col in doc_antigo_ref.collections():
        contagem["subcols"] += 1
        print(f"{indent}↳ Sub-coleção: {sub_col.id}")

        for sub_doc in sub_col.stream():
            sub_doc_id   = sub_doc.id
            sub_doc_data = sub_doc.to_dict()

            sub_doc_novo_ref = doc_novo_ref.collection(sub_col.id).document(sub_doc_id)

            # Checa se já existe
            existe = sub_doc_novo_ref.get().exists if not sobrescrever else False

            if existe:
                print(f"{indent}   ⏭  {sub_doc_id} (já existe, pulando)")
                continue

            if executar:
                sub_doc_novo_ref.set(sub_doc_data)
                contagem["docs"] += 1
                print(f"{indent}   ✅ {sub_doc_id}")
            else:
                contagem["docs"] += 1
                print(f"{indent}   📝 {sub_doc_id} (simulação)")

            # Recursão pra netos
            netos = migrar_subcolecoes(
                sub_doc.reference,
                sub_doc_novo_ref,
                executar,
                sobrescrever,
                indent + "      "
            )
            contagem["docs"]    += netos["docs"]
            contagem["subcols"] += netos["subcols"]

    return contagem


def migrar_colecao(colecao_antiga, db_novo, executar: bool, sobrescrever: bool):
    """Migra UMA coleção raiz e suas sub-coleções."""
    nome_colecao = colecao_antiga.id
    print(f"\n📁 Coleção: {nome_colecao}")

    total_docs    = 0
    pulados       = 0
    com_subs      = 0
    docs_em_subs  = 0

    for doc in colecao_antiga.stream():
        doc_id   = doc.id
        doc_data = doc.to_dict()

        doc_novo_ref = db_novo.collection(nome_colecao).document(doc_id)

        # Checa se já existe
        existe = doc_novo_ref.get().exists if not sobrescrever else False

        if existe:
            pulados += 1
            print(f"   ⏭  {doc_id[:50]} (já existe)")
        else:
            if executar:
                doc_novo_ref.set(doc_data)
                total_docs += 1
                print(f"   ✅ {doc_id[:50]}")
            else:
                total_docs += 1
                print(f"   📝 {doc_id[:50]} (simulação)")

        # Migra sub-coleções desse documento
        subs = migrar_subcolecoes(doc.reference, doc_novo_ref, executar, sobrescrever)
        if subs["subcols"] > 0:
            com_subs     += 1
            docs_em_subs += subs["docs"]

    return {
        "colecao":      nome_colecao,
        "docs":         total_docs,
        "pulados":      pulados,
        "com_subs":     com_subs,
        "docs_em_subs": docs_em_subs,
    }


def main(executar: bool, sobrescrever: bool):
    print("=" * 70)
    print("  MIGRAÇÃO FIREBASE — NIVELIS")
    print(f"  Modo: {'EXECUTAR' if executar else 'ANÁLISE (não copia)'}")
    print(f"  Sobrescrever existentes: {sobrescrever}")
    print("=" * 70)

    validar_arquivos()
    db_antigo, db_novo = inicializar_apps()

    if not executar:
        print("⚠ MODO ANÁLISE: nenhum dado será copiado.")
        print("  Use --executar para fazer a migração de verdade.\n")

    # Lista TODAS as coleções raiz do projeto antigo
    colecoes = list(db_antigo.collections())
    print(f"📊 Encontrei {len(colecoes)} coleção(ões) no projeto antigo:\n")
    for c in colecoes:
        print(f"   • {c.id}")

    print()

    resumo = []
    for colecao in colecoes:
        res = migrar_colecao(colecao, db_novo, executar, sobrescrever)
        resumo.append(res)

    # Resumo final
    print("\n" + "=" * 70)
    print("  RESUMO")
    print("=" * 70)

    total_geral_docs    = 0
    total_geral_pulados = 0
    total_em_subs       = 0

    for r in resumo:
        print(f"📁 {r['colecao']:30s}  docs: {r['docs']:5d}  pulados: {r['pulados']:5d}  sub-cols: {r['docs_em_subs']:4d}")
        total_geral_docs    += r["docs"]
        total_geral_pulados += r["pulados"]
        total_em_subs       += r["docs_em_subs"]

    print("─" * 70)
    print(f"   TOTAL                          docs: {total_geral_docs:5d}  pulados: {total_geral_pulados:5d}  sub-cols: {total_em_subs:4d}")
    print("=" * 70)

    if executar:
        print(f"\n✅ Migração concluída! Verifique o projeto novo no Firebase Console.\n")
    else:
        print(f"\n💡 Para executar de verdade:")
        print(f"   python migrar_firebase.py --executar\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra dados do Firebase antigo pro novo.")
    parser.add_argument("--executar", action="store_true",
                        help="Executa a migração (padrão: só simula)")
    parser.add_argument("--sobrescrever", action="store_true",
                        help="Sobrescreve documentos existentes no projeto novo")
    args = parser.parse_args()
    main(args.executar, args.sobrescrever)
