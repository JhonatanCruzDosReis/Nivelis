"""
=============================================================
  NIVELIS — Validador de Gabaritos
=============================================================

  Usa o Gemini como REVISOR independente: ele resolve cada
  questão do zero (sem ver o gabarito salvo) e compara com
  o gabarito do banco. Se divergir, marca como suspeita.

  NÃO altera gabaritos automaticamente — só MARCA as suspeitas
  pra você revisar. Segurança em primeiro lugar.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api

    # Valida questões de matemática (padrão, onde erros são comuns):
    python validar_gabaritos.py matematica

    # Valida outra matéria:
    python validar_gabaritos.py fisica
    python validar_gabaritos.py humanas

    # Quantidade específica (ex: 15):
    python validar_gabaritos.py matematica 15

  DEPOIS:
    # Ver só as questões marcadas como suspeitas:
    python validar_gabaritos.py --ver-suspeitas

=============================================================
"""

import os
import sys
import re
import time
import google.generativeai as genai
import firebase_admin
from pathlib         import Path
from dotenv          import load_dotenv
from firebase_admin  import credentials, firestore

# ──────────────────────────────────────────
#  CONFIGURAÇÃO (mesmo padrão do indexar_livro.py)
# ──────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY não configurada no .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-2.5-flash-lite")

if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  Formata alternativas
# ──────────────────────────────────────────
def formatar_alternativas(alternativas) -> str:
    linhas = []
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                letra = alt.get("id") or alt.get("letra") or "?"
                texto = alt.get("texto") or alt.get("text") or ""
                linhas.append(f"{letra}) {texto}")
    elif isinstance(alternativas, dict):
        for letra, texto in sorted(alternativas.items()):
            linhas.append(f"{letra}) {texto}")
    return "\n".join(linhas)


# ──────────────────────────────────────────
#  Pergunta pro Gemini resolver (SEM ver gabarito)
# ──────────────────────────────────────────
def resolver_questao(enunciado, contexto, alternativas_str):
    ctx = f"CONTEXTO:\n{contexto}\n\n" if contexto else ""
    prompt = f"""Você é um professor resolvendo uma questão de prova. Resolva com atenção.

{ctx}ENUNCIADO:
{enunciado}

ALTERNATIVAS:
{alternativas_str}

Resolva a questão do zero, calculando/raciocinando com cuidado.
Depois, responda APENAS com a letra da alternativa correta.

Formato da resposta (siga EXATAMENTE):
RACIOCINIO: <seu raciocínio em 1-3 frases>
RESPOSTA: <apenas a letra, ex: A>"""

    try:
        resposta = modelo.generate_content(
            prompt,
            generation_config={"max_output_tokens": 500, "temperature": 0.1}
        )
        texto = resposta.text.strip()

        # Extrai a letra da resposta
        match = re.search(r'RESPOSTA:\s*([A-E])', texto, re.IGNORECASE)
        if match:
            return match.group(1).upper(), texto
        # Fallback: procura letra isolada no fim
        match2 = re.search(r'\b([A-E])\b', texto[-50:])
        if match2:
            return match2.group(1).upper(), texto
        return None, texto
    except Exception as e:
        return None, f"ERRO: {e}"


# ──────────────────────────────────────────
#  Validação
# ──────────────────────────────────────────
def validar(db, materia_filtro, quantidade, pausa):
    print("=" * 70)
    print(f"VALIDANDO GABARITOS — matéria: {materia_filtro}")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())

    # Filtra por matéria e ignora as já marcadas/quebradas
    selecionadas = []
    for doc in docs:
        data = doc.to_dict()
        mat = (data.get("materia") or "").lower()
        if materia_filtro not in mat and mat not in materia_filtro:
            continue
        if data.get("tem_visual_quebrado") is True:
            continue  # pula as com visual quebrado
        if data.get("gabarito_validado") is True:
            continue  # pula as já validadas antes
        # Precisa ter os dados
        if data.get("enunciado") and data.get("alternativas") and data.get("gabarito"):
            selecionadas.append({"id": doc.id, "data": data})

    print(f"\n📊 Questões de '{materia_filtro}' a validar: {len(selecionadas)}")
    if len(selecionadas) > quantidade:
        selecionadas = selecionadas[:quantidade]
        print(f"   (limitando a {quantidade})")

    if not selecionadas:
        print("\n✅ Nada a validar (ou todas já validadas).")
        return

    print(f"\n⚠  Vai fazer {len(selecionadas)} chamadas ao Gemini.")
    print(f"   Cota free: 20/dia. Você tem {len(selecionadas)} questões.")
    if len(selecionadas) > 20:
        print(f"   ⚠  Pode estourar a cota — considere validar em partes.")
    resp = input("\nContinuar? (sim/nao): ").strip().lower()
    if resp not in ("sim", "s", "y", "yes"):
        print("Cancelado.")
        return

    # ─── Valida cada uma ───
    concordam = 0
    divergem = 0
    erros = 0
    suspeitas = []

    for i, item in enumerate(selecionadas, start=1):
        data = item["data"]
        gab_banco = str(data.get("gabarito", "")).upper().strip()
        alts_str = formatar_alternativas(data.get("alternativas"))

        print(f"\n[{i}/{len(selecionadas)}] {item['id'][:8]} | gabarito banco: {gab_banco}")
        print(f"   {(data.get('enunciado') or '')[:55]}...")

        gab_ia, raciocinio = resolver_questao(
            data.get("enunciado", ""),
            data.get("contexto", ""),
            alts_str,
        )

        if gab_ia is None:
            print(f"   ⚠ Não consegui validar (erro/cota)")
            erros += 1
        elif gab_ia == gab_banco:
            print(f"   ✅ CONCORDAM (IA também diz {gab_ia})")
            concordam += 1
            # Marca como validada (não revalida no futuro)
            try:
                db.collection("questoes").document(item["id"]).update({"gabarito_validado": True})
            except Exception:
                pass
        else:
            print(f"   🔴 DIVERGEM! Banco={gab_banco}, IA={gab_ia}")
            divergem += 1
            suspeitas.append({
                "id": item["id"],
                "materia": data.get("materia"),
                "gab_banco": gab_banco,
                "gab_ia": gab_ia,
                "enunciado": (data.get("enunciado") or "")[:80],
            })
            # Marca como suspeita pra revisar
            try:
                db.collection("questoes").document(item["id"]).update({
                    "gabarito_suspeito": True,
                    "gabarito_ia_sugerido": gab_ia,
                })
            except Exception:
                pass

        if i < len(selecionadas) and pausa > 0:
            time.sleep(pausa)

    # ─── Resumo ───
    print("\n" + "=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print(f"  ✅ Concordam (gabarito OK):     {concordam}")
    print(f"  🔴 Divergem (suspeitas):        {divergem}")
    print(f"  ⚠  Erros/não validou:          {erros}")

    if suspeitas:
        print("\n" + "─" * 70)
        print("QUESTÕES SUSPEITAS (revise estas!):")
        print("─" * 70)
        for s in suspeitas:
            print(f"\n  ID: {s['id']}")
            print(f"  Matéria: {s['materia']}")
            print(f"  Gabarito no banco: {s['gab_banco']} | IA sugere: {s['gab_ia']}")
            print(f"  {s['enunciado']}...")
        print("\n  → Essas foram marcadas com 'gabarito_suspeito: true'")
        print("  → Use 'python ver_questoes.py' pra revisar o texto completo.")


# ──────────────────────────────────────────
#  Ver suspeitas já marcadas
# ──────────────────────────────────────────
def ver_suspeitas(db):
    print("=" * 70)
    print("QUESTÕES MARCADAS COMO SUSPEITAS")
    print("=" * 70)

    docs = list(db.collection("questoes").where("gabarito_suspeito", "==", True).stream())
    print(f"\n📊 Total de suspeitas: {len(docs)}\n")

    for doc in docs:
        data = doc.to_dict()
        print(f"  ID: {doc.id}")
        print(f"  Matéria: {data.get('materia')}")
        print(f"  Gabarito banco: {data.get('gabarito')} | IA sugeriu: {data.get('gabarito_ia_sugerido')}")
        print(f"  {(data.get('enunciado') or '')[:80]}...")
        print()


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 VALIDADOR DE GABARITOS — NIVELIS\n")

    if len(sys.argv) > 1 and sys.argv[1] == "--ver-suspeitas":
        ver_suspeitas(db)
        sys.exit(0)

    materia = sys.argv[1].lower() if len(sys.argv) > 1 else "matematica"
    quantidade = 20
    if len(sys.argv) > 2:
        try:
            quantidade = int(sys.argv[2])
        except ValueError:
            pass

    validar(db, materia, quantidade, pausa=3)

    print("\n" + "=" * 70)
    print("Concluído! Para ver todas as suspeitas: python validar_gabaritos.py --ver-suspeitas")
    print("=" * 70)
