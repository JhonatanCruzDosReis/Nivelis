"""
=============================================================
  NIVELIS — Limpar Livros Duplicados
=============================================================

  Detecta livros duplicados no Firebase (mesmo título OU mesmo
  hash de conteúdo) e oferece deletar os duplicatas mantendo
  apenas o mais antigo.

  COMO USAR:
    python limpar_duplicatas.py            (modo análise, não deleta)
    python limpar_duplicatas.py --deletar  (deleta as duplicatas)

  CRITÉRIO:
    - Mesmo hash_conteudo (definitivo)
    - OU mesmo título + autor (provável)

  Em caso de duplicata, MANTÉM o mais antigo (primeiro indexado)
  e deleta os mais novos.

=============================================================
"""

import argparse
import firebase_admin
from firebase_admin import credentials, firestore
from collections    import defaultdict

if not firebase_admin._apps:
    cred = credentials.Certificate("chave-firebase.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


def encontrar_duplicatas():
    """
    Lista todos os livros e detecta duplicatas.
    Retorna dict de grupos de duplicatas.
    """
    docs = list(db.collection("livros").stream())
    print(f"\n📚 Total de livros no banco: {len(docs)}\n")

    if not docs:
        return {}

    # Agrupa por hash (se tiver) ou por título+autor
    grupos = defaultdict(list)

    for doc in docs:
        data = doc.to_dict()

        # Chave: hash do conteúdo (preferencial) OU título+autor
        hash_pdf = data.get("hash_conteudo")
        if hash_pdf:
            chave = f"hash:{hash_pdf[:16]}"
        else:
            titulo = (data.get("titulo") or "").strip().lower()
            autor  = (data.get("autor")  or "").strip().lower()
            chave = f"titulo+autor:{titulo}|{autor}"

        grupos[chave].append({
            "doc_id":      doc.id,
            "livro_id":    data.get("livro_id"),
            "titulo":      data.get("titulo"),
            "autor":       data.get("autor"),
            "arquivo":     data.get("arquivo_original"),
            "indexado_em": data.get("indexado_em"),
            "tem_hash":    bool(hash_pdf),
        })

    # Filtra só os grupos com mais de 1 item (duplicatas)
    duplicatas = {k: v for k, v in grupos.items() if len(v) > 1}
    return duplicatas


def main(deletar: bool):
    duplicatas = encontrar_duplicatas()

    if not duplicatas:
        print("✅ Nenhuma duplicata encontrada! Banco limpo.\n")
        return

    print(f"⚠️  {len(duplicatas)} grupo(s) de duplicatas encontrado(s):\n")

    total_a_deletar = 0
    ids_para_deletar = []

    for chave, livros in duplicatas.items():
        # Ordena pelo mais antigo primeiro
        livros.sort(key=lambda x: x.get("indexado_em") or 0)

        manter = livros[0]
        deletar_lista = livros[1:]

        print(f"📚 GRUPO: {livros[0]['titulo']}")
        print(f"   Identificado por: {chave.split(':')[0]}")
        print(f"   Total: {len(livros)} cópias")
        print(f"   ✅ MANTER: {manter['livro_id']} (arquivo: {manter['arquivo']})")

        for d in deletar_lista:
            print(f"   ❌ DELETAR: {d['livro_id']} (arquivo: {d['arquivo']})")
            ids_para_deletar.append(d['doc_id'])
            total_a_deletar += 1

        print()

    if not deletar:
        print(f"📊 RESUMO (modo análise):")
        print(f"   {total_a_deletar} livros seriam deletados")
        print(f"\nPara deletar de verdade, rode:")
        print(f"   python limpar_duplicatas.py --deletar\n")
    else:
        print(f"🗑  DELETANDO {total_a_deletar} duplicatas...")
        for doc_id in ids_para_deletar:
            db.collection("livros").document(doc_id).delete()
            print(f"   ✓ Deletado: {doc_id}")

        print(f"\n✅ Limpeza concluída! {total_a_deletar} duplicatas removidas.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detecta e remove livros duplicados.")
    parser.add_argument("--deletar", action="store_true",
                        help="Deleta as duplicatas (padrão: só analisa)")
    args = parser.parse_args()
    main(args.deletar)
