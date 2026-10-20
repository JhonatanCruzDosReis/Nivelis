"""
=============================================================
  NIVELIS — apaga o CPF dos usuários já cadastrados
=============================================================

Tirar o campo do formulário impede CPF NOVO de entrar. Quem já se cadastrou
continua com o dele gravado em `users/{uid}`, e é esse que precisa sair.

O que este programa faz:

  1. CONTA  (padrão)   — não altera nada. Diz quantos documentos têm CPF.
  2. EXPORTA           — backup JSON antes de apagar (pode desligar).
  3. APAGA  --apagar   — remove SÓ o campo CPF. O resto do documento fica
                         intacto: nome, email, data de nascimento, celular.

USO

    python apagar_cpf.py                 # só conta
    python apagar_cpf.py --apagar        # apaga, perguntando antes
    python apagar_cpf.py --apagar --sim  # sem perguntar

A CREDENCIAL é procurada na pasta deste arquivo (chave-firebase.json), ou na
variável de ambiente FIREBASE_CRED.

⚠️ O backup que isto gera CONTÉM os CPFs. Ele existe para o caso de a
exclusão sair errada — apague o arquivo assim que confirmar que deu certo.
Guardar um backup de CPF indefinidamente recria o problema que estamos
resolvendo, só que num arquivo solto em vez do banco.
=============================================================
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

AQUI = Path(__file__).resolve().parent

# O campo foi gravado como "CPF" (maiúsculo) em Cadastro/index.tsx. As outras
# grafias entram na lista porque custa nada e um campo esquecido por causa de
# maiúscula seria o pior desfecho possível aqui.
CAMPOS = ["CPF", "cpf", "Cpf"]


def conectar():
    caminho = Path(os.getenv("FIREBASE_CRED") or (AQUI / "chave-firebase.json"))
    if not caminho.exists():
        print(f"❌ Credencial não encontrada em {caminho}")
        sys.exit(1)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(caminho)))
    return firestore.client()


def main():
    p = argparse.ArgumentParser(description="Remove o campo CPF dos usuários.")
    p.add_argument("--apagar", action="store_true", help="apaga de verdade")
    p.add_argument("--sim", action="store_true", help="não pergunta")
    p.add_argument("--sem-backup", action="store_true",
                   help="pula o backup (o backup contém os CPFs)")
    args = p.parse_args()

    db = conectar()

    print("\nLendo a coleção 'users' (nada é alterado nesta etapa)...")
    try:
        docs = list(db.collection("users").stream())
    except Exception as e:
        print(f"❌ Não consegui ler: {e}")
        sys.exit(1)

    com_cpf = []
    for d in docs:
        dados = d.to_dict() or {}
        achados = [c for c in CAMPOS if c in dados]
        if achados:
            com_cpf.append((d.id, achados, dados))

    print()
    print("═" * 60)
    print(f"  {len(docs)} usuário(s) no total")
    print(f"  {len(com_cpf)} com CPF gravado")
    print("═" * 60)

    if not com_cpf:
        print("\n  ✅ Nenhum CPF no banco. Nada a fazer.\n")
        return

    for uid, achados, _ in com_cpf[:8]:
        print(f"      users/{uid}  →  {', '.join(achados)}")
    if len(com_cpf) > 8:
        print(f"      ... e mais {len(com_cpf) - 8}")

    if not args.apagar:
        print("\n  Nada foi alterado. Para apagar: python apagar_cpf.py --apagar\n")
        return

    # ── Destrutivo a partir daqui ──
    if not args.sem_backup:
        carimbo = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        destino = AQUI / f"backup_cpf_{carimbo}.json"
        destino.write_text(json.dumps(
            [{"uid": uid, **{c: dados.get(c) for c in achados}}
             for uid, achados, dados in com_cpf],
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  💾 Backup: {destino}")
        print("     ⚠️  Este arquivo CONTÉM os CPFs. Apague-o assim que "
              "confirmar que deu certo.")

    if not args.sim:
        print()
        if input(f"  Digite APAGAR para remover o CPF de {len(com_cpf)}: ").strip() != "APAGAR":
            print("\n  Cancelado. Nada foi alterado.\n")
            return

    print()
    apagados = 0
    for i in range(0, len(com_cpf), 400):
        fatia = com_cpf[i:i + 400]
        lote = db.batch()
        for uid, achados, _ in fatia:
            lote.update(db.collection("users").document(uid),
                        {c: firestore.DELETE_FIELD for c in achados})
        lote.commit()
        apagados += len(fatia)
        print(f"      {apagados}/{len(com_cpf)}", end="\r", flush=True)

    print(f"      {apagados} usuário(s) sem CPF agora.          ")
    print("\n  ✅ Pronto. Confira no console do Firebase e apague o backup.\n")


if __name__ == "__main__":
    main()
