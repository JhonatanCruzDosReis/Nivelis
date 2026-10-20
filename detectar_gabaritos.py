"""
=============================================================
  NIVELIS — Detector de Gabaritos Suspeitos (CAMADA 1)
=============================================================

  Detecta gabaritos possivelmente ERRADOS por CONTRADIÇÃO INTERNA,
  SEM usar IA (grátis, instantâneo).

  COMO FUNCIONA:
    Compara o VALOR que a explicação calcula no final com a
    ALTERNATIVA apontada pelo gabarito. Se não baterem, é suspeita.

    Exemplo (Q6 smartphone):
      Gabarito: A (R$ 1.987,50)
      Explicação calcula: "...resultando em R$ 1.912,50"
      → 1.912,50 ≠ 1.987,50 → SUSPEITA!

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api

    # Analisa (marca suspeitas, não muda gabarito):
    python detectar_gabaritos.py

    # Ver as já marcadas:
    python detectar_gabaritos.py --ver

    # Limpar marcações:
    python detectar_gabaritos.py --limpar

  DEPOIS (camada 2):
    As suspeitas podem ser validadas com IA via validar_gabaritos.py

=============================================================
"""

import os
import sys
import re
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    if not os.path.exists(chave):
        print("❌ Não achei a chave do Firebase! Rode na pasta do backend.")
        sys.exit(1)
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  Extrai números de um texto
# ──────────────────────────────────────────
def extrair_numeros(texto: str):
    """
    Extrai todos os números de um texto, normalizados.
    Trata formato brasileiro: 1.987,50 → 1987.50
    Retorna lista de floats.
    """
    if not texto:
        return []
    numeros = []
    # Padrão: números com . de milhar e , decimal (1.987,50) ou simples (195,83 / 210)
    # Primeiro pega padrões monetários/decimais brasileiros
    for match in re.finditer(r'\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?|\d+(?:\.\d+)?', texto):
        s = match.group()
        # Normaliza formato BR → float
        if ',' in s:
            # tem vírgula decimal
            s_norm = s.replace('.', '').replace(',', '.')
        elif s.count('.') == 1 and len(s.split('.')[-1]) <= 2:
            # ponto decimal simples (ex: 200.83)
            s_norm = s
        else:
            # ponto de milhar (ex: 1.987) ou inteiro
            s_norm = s.replace('.', '')
        try:
            numeros.append(float(s_norm))
        except ValueError:
            pass
    return numeros


# ──────────────────────────────────────────
#  Pega o texto da alternativa do gabarito
# ──────────────────────────────────────────
def texto_da_alternativa(alternativas, letra_gabarito):
    """Retorna o texto da alternativa apontada pelo gabarito."""
    letra = str(letra_gabarito).upper().strip()
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                l = (alt.get("id") or alt.get("letra") or "").upper()
                if l == letra:
                    return alt.get("texto") or alt.get("text") or ""
    elif isinstance(alternativas, dict):
        for l, texto in alternativas.items():
            if l.upper() == letra:
                return texto
    return None


def todas_alternativas_texto(alternativas):
    """Retorna dict {letra: texto} de todas alternativas."""
    resultado = {}
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                l = (alt.get("id") or alt.get("letra") or "").upper()
                resultado[l] = alt.get("texto") or alt.get("text") or ""
    elif isinstance(alternativas, dict):
        for l, texto in alternativas.items():
            resultado[l.upper()] = str(texto)
    return resultado


# ──────────────────────────────────────────
#  Detecta contradição
# ──────────────────────────────────────────
def detectar_contradicao(data):
    """
    Retorna (suspeita, motivo, detalhe).
    Compara o valor final da explicação com a alternativa do gabarito.
    """
    explicacao = data.get("explicacao_ia") or data.get("explicacao") or ""
    gabarito = str(data.get("gabarito", "")).upper().strip()
    alternativas = data.get("alternativas")

    if not explicacao or not gabarito or not alternativas:
        return False, None, None

    # Texto da alternativa correta (do gabarito)
    txt_gab = texto_da_alternativa(alternativas, gabarito)
    if txt_gab is None:
        return False, None, None

    # Números na alternativa do gabarito
    nums_gabarito = extrair_numeros(txt_gab)
    if not nums_gabarito:
        # Alternativa não tem número (questão de texto) — não dá pra checar por contradição
        return False, None, None

    # Números que a explicação calcula
    nums_explicacao = extrair_numeros(explicacao)
    if not nums_explicacao:
        return False, None, None

    # ─── Lógica: o último número relevante da explicação deve bater
    #     com algum número da alternativa do gabarito ───
    # Pega os últimos 3 números da explicação (o resultado costuma estar no fim)
    ultimos = nums_explicacao[-3:]

    # Verifica se ALGUM dos números finais da explicação bate com o gabarito
    def proximo(a, b, tol=0.02):
        """Compara com tolerância de 2% (arredondamentos)."""
        if b == 0:
            return abs(a - b) < 0.01
        return abs(a - b) / abs(b) < tol

    bateu_gabarito = any(
        proximo(ne, ng)
        for ne in ultimos
        for ng in nums_gabarito
    )

    if bateu_gabarito:
        return False, None, None  # explicação bate com gabarito, OK

    # ─── Não bateu. Vamos ver se bate com OUTRA alternativa ───
    todas = todas_alternativas_texto(alternativas)
    alt_que_bate = None
    for letra, txt in todas.items():
        if letra == gabarito:
            continue
        nums_alt = extrair_numeros(txt)
        for ne in ultimos:
            for na in nums_alt:
                if proximo(ne, na):
                    alt_que_bate = letra
                    break
            if alt_que_bate:
                break
        if alt_que_bate:
            break

    valor_final = ultimos[-1] if ultimos else "?"
    if alt_que_bate:
        motivo = "explicacao_aponta_outra_alternativa"
        detalhe = f"Explicação calcula ~{valor_final}, que corresponde à alternativa {alt_que_bate}, não à {gabarito}"
    else:
        motivo = "explicacao_nao_bate_gabarito"
        detalhe = f"Explicação calcula ~{valor_final}, que não corresponde à alternativa {gabarito} ({txt_gab[:40]})"

    return True, motivo, detalhe


# ──────────────────────────────────────────
#  Análise
# ──────────────────────────────────────────
def analisar(db):
    print("=" * 70)
    print("DETECTANDO GABARITOS SUSPEITOS (por contradição interna, sem IA)")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    print(f"\n📊 Total de questões: {len(docs)}\n")

    suspeitas = []
    sem_numero = 0    # questões que não dá pra checar (texto puro)
    ok = 0

    for doc in docs:
        data = doc.to_dict()
        # Pula visual quebrado (já filtradas)
        if data.get("tem_visual_quebrado") is True:
            continue

        suspeita, motivo, detalhe = detectar_contradicao(data)
        if suspeita:
            suspeitas.append({
                "id": doc.id,
                "materia": data.get("materia"),
                "gabarito": data.get("gabarito"),
                "motivo": motivo,
                "detalhe": detalhe,
                "enunciado": (data.get("enunciado") or "")[:60],
            })
        else:
            # Distingue "OK" de "não dava pra checar"
            expl = data.get("explicacao_ia") or data.get("explicacao") or ""
            alt = data.get("alternativas")
            gab = str(data.get("gabarito", "")).upper()
            txt_gab = texto_da_alternativa(alt, gab) if alt else None
            if txt_gab and extrair_numeros(txt_gab) and extrair_numeros(expl):
                ok += 1
            else:
                sem_numero += 1

    print(f"🔴 Gabaritos SUSPEITOS (contradição):     {len(suspeitas)}")
    print(f"✅ Explicação bate com gabarito:          {ok}")
    print(f"⚪ Sem número pra checar (texto puro):    {sem_numero}")

    if suspeitas:
        por_materia = {}
        for s in suspeitas:
            por_materia[s["materia"]] = por_materia.get(s["materia"], 0) + 1
        print("\n  Suspeitas por matéria:")
        for mat, n in sorted(por_materia.items(), key=lambda x: -x[1]):
            print(f"    {mat}: {n}")

        print("\n" + "─" * 70)
        print("DETALHE DAS SUSPEITAS:")
        print("─" * 70)
        for i, s in enumerate(suspeitas, start=1):
            print(f"\n[{i}] {s['materia']} | gabarito: {s['gabarito']} | id: {s['id'][:8]}")
            print(f"    {s['enunciado']}...")
            print(f"    🔴 {s['detalhe']}")

    return suspeitas


def marcar_suspeitas(db, suspeitas):
    print(f"\n🏷️  Marcando {len(suspeitas)} questões como 'gabarito_suspeito'...")
    batch = db.batch()
    contador = 0
    for s in suspeitas:
        ref = db.collection("questoes").document(s["id"])
        batch.update(ref, {
            "gabarito_suspeito": True,
            "gabarito_suspeito_motivo": s["motivo"],
            "gabarito_suspeito_detalhe": s["detalhe"],
        })
        contador += 1
        if contador % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    print(f"  ✅ {contador} marcadas!")


def ver_marcadas(db):
    print("=" * 70)
    print("GABARITOS MARCADOS COMO SUSPEITOS")
    print("=" * 70)
    docs = list(db.collection("questoes").where("gabarito_suspeito", "==", True).stream())
    print(f"\n📊 Total: {len(docs)}\n")
    for doc in docs:
        data = doc.to_dict()
        print(f"  id: {doc.id[:8]} | {data.get('materia')} | gabarito: {data.get('gabarito')}")
        print(f"    {data.get('gabarito_suspeito_detalhe', '')}")
        print()


def limpar_marcas(db):
    docs = list(db.collection("questoes").where("gabarito_suspeito", "==", True).stream())
    print(f"\n🔄 Removendo marca de {len(docs)} questões...")
    batch = db.batch()
    for doc in docs:
        batch.update(doc.reference, {
            "gabarito_suspeito": firestore.DELETE_FIELD,
            "gabarito_suspeito_motivo": firestore.DELETE_FIELD,
            "gabarito_suspeito_detalhe": firestore.DELETE_FIELD,
        })
    batch.commit()
    print(f"  ✅ Limpo!")


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍 DETECTOR DE GABARITOS SUSPEITOS — NIVELIS\n")

    if len(sys.argv) > 1:
        if sys.argv[1] == "--ver":
            ver_marcadas(db)
            sys.exit(0)
        elif sys.argv[1] == "--limpar":
            limpar_marcas(db)
            sys.exit(0)

    suspeitas = analisar(db)

    if not suspeitas:
        print("\n🎉 Nenhuma contradição óbvia encontrada!")
        print("   (Isso não garante que todos os gabaritos estão certos —")
        print("    questões de texto puro precisam de validação por IA.)")
        sys.exit(0)

    print("\n" + "=" * 70)
    print(f"Marcar essas {len(suspeitas)} como suspeitas? (não muda o gabarito)")
    print("=" * 70)
    resp = input("Marcar? (sim/nao): ").strip().lower()
    if resp in ("sim", "s", "y", "yes"):
        marcar_suspeitas(db, suspeitas)
        print("\n✅ Marcadas! Agora você pode:")
        print("   1. Revisar cada uma manualmente (o detalhe indica o problema)")
        print("   2. Validar com IA: python validar_gabaritos.py matematica")
        print("   3. Ver todas: python detectar_gabaritos.py --ver")
    else:
        print("Nada marcado.")

    print("\n" + "=" * 70)
    print("Concluído!")
    print("=" * 70)
