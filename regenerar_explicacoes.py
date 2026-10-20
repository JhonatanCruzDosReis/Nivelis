"""
=============================================================
  NIVELIS — Regenerador de Explicações
=============================================================

  Acha questões com explicação "bagunçada" (onde a IA vazou
  o rascunho de raciocínio) e REGENERA uma explicação limpa
  e direta via Gemini.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api
    python regenerar_explicacoes.py

  MODO SEGURO:
    - Primeiro mostra quantas questões serão regeneradas
    - Você confirma antes de começar
    - Faz uma pausa entre chamadas (respeita cota Gemini)
    - Mostra cada antes/depois

=============================================================
"""

import os
import sys
import json
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

# Firebase (mesma chave do indexar_livro.py)
if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  Sinais de explicação bagunçada
# ──────────────────────────────────────────
SINAIS_RUINS = [
    "houve um erro", "houve um equívoco", "houve um engano", "houve um equivoco",
    "vamos refazer", "vamos recalcular", "vamos verificar", "vamos revisar",
    "vamos assumir", "vamos manter", "vamos analisar novamente", "vamos focar",
    "valor incorreto", "está inconsistente", "esta inconsistente",
    "no meu cálculo", "no meu calculo", "erro no meu", "há um erro na minha",
    "ajustar alternativas", "nova alternativa", "vamos calcular novamente",
    "refazendo", "me enganei", "ainda não cheguei", "ainda nao cheguei",
    "parece que me confundi", "parece que estou", "ainda há um equívoco",
    "vamos tentar de outra", "oops", "parece que houve",
]


def explicacao_eh_ruim(texto: str) -> bool:
    if not texto:
        return False
    t = texto.lower()
    return any(s in t for s in SINAIS_RUINS)


# ──────────────────────────────────────────
#  Formata alternativas pra mostrar ao Gemini
# ──────────────────────────────────────────
def formatar_alternativas(alternativas) -> str:
    """Alternativas podem ser lista [{id,texto}] ou dict {A:"...", B:"..."}."""
    linhas = []
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                letra = alt.get("id") or alt.get("letra") or "?"
                texto = alt.get("texto") or alt.get("text") or ""
                linhas.append(f"{letra}) {texto}")
    elif isinstance(alternativas, dict):
        for letra, texto in alternativas.items():
            linhas.append(f"{letra}) {texto}")
    return "\n".join(linhas)


# ──────────────────────────────────────────
#  Regenera UMA explicação via Gemini
# ──────────────────────────────────────────
def regenerar_explicacao(enunciado, alternativas_str, gabarito, materia):
    prompt = f"""Você é um professor escrevendo a resolução DEFINITIVA de uma questão para um gabarito oficial.

MATÉRIA: {materia}

ENUNCIADO:
{enunciado}

ALTERNATIVAS:
{alternativas_str}

RESPOSTA CORRETA (already verified): {gabarito}

Escreva a explicação de por que a alternativa {gabarito} é correta.

═══ REGRAS ABSOLUTAS (quebrar = explicação rejeitada) ═══

1. Escreva como um TEXTO FINAL e POLIDO, já revisado. NÃO é rascunho.
2. PROIBIDO escrever qualquer uma destas frases ou similares:
   ❌ "oops", "ops", "houve um erro", "houve um equívoco", "houve um engano"
   ❌ "vamos refazer", "vamos recalcular", "vamos revisar", "vamos analisar novamente"
   ❌ "ainda não cheguei", "parece que me confundi", "vamos tentar de outra forma"
   ❌ "há um erro na minha", "ainda há um equívoco"
3. Faça o cálculo UMA ÚNICA VEZ, do começo ao fim, de forma correta.
4. Se precisar pensar, pense ANTES — escreva só a versão final correta.
5. Máximo 5 frases ou os passos do cálculo (limpos).

═══ EXEMPLO DO FORMATO ESPERADO ═══

Pergunta: De quantas formas 5 tarefas podem ser ordenadas com A antes de B?
Explicação BOA:
"O número total de maneiras de ordenar 5 tarefas distintas é 5! = 120. Em qualquer sequência, ou A vem antes de B, ou B vem antes de A — duas possibilidades igualmente prováveis. Portanto, metade das 120 permutações tem A antes de B: 120 / 2 = 60. A alternativa correta é {gabarito}."

Note: direto, um cálculo só, sem 'oops', sem refazer.

═══ AGORA ESCREVA ═══

Retorne SOMENTE o texto final da explicação. Sem título, sem "Explicação:", sem aspas, sem rascunho."""

    try:
        resposta = modelo.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 600,
                "temperature":       0.1,   # bem baixa: menos divagação
            }
        )
        nova = resposta.text.strip()
        nova = nova.replace("```", "").strip()
        if nova.lower().startswith("explicação:"):
            nova = nova[len("explicação:"):].strip()

        # ─── CORTE DE SEGURANÇA ───
        # Se mesmo assim vazou rascunho, corta tudo a partir do primeiro sinal ruim.
        nova = cortar_no_primeiro_erro(nova)

        return nova
    except Exception as e:
        print(f"      ⚠ Erro ao regenerar: {e}")
        return None


def cortar_no_primeiro_erro(texto: str) -> str:
    """
    Se a explicação vazou rascunho (oops, houve um erro...), corta tudo
    a partir desse ponto. A parte ANTES do erro geralmente já tem a
    resolução completa e correta.
    """
    marcadores = [
        "oops", "ops,", "ops!", "houve um erro", "houve um equívoco",
        "houve um engano", "vamos refazer", "vamos recalcular",
        "vamos revisar", "vamos analisar novamente", "ainda não cheguei",
        "ainda nao cheguei", "parece que me confundi", "parece que estou",
        "vamos tentar de outra", "há um erro na minha", "ha um erro na minha",
        "ainda há um equívoco", "ainda ha um equivoco", "vamos focar",
        "vamos calcular novamente", "me enganei", "parece que houve",
    ]
    t_lower = texto.lower()
    pos_corte = len(texto)
    for marc in marcadores:
        idx = t_lower.find(marc)
        if idx != -1 and idx < pos_corte:
            pos_corte = idx

    if pos_corte < len(texto):
        # Corta e limpa pontuação solta no fim
        cortado = texto[:pos_corte].strip()
        # Remove conectivos pendurados no fim (",", "e", "que"...)
        cortado = cortado.rstrip(" ,;:-—e").strip()
        # Garante que termina com ponto
        if cortado and not cortado.endswith((".", "!", "?")):
            cortado += "."
        return cortado

    return texto


# ──────────────────────────────────────────
#  Análise
# ──────────────────────────────────────────
def analisar(db):
    print("=" * 70)
    print("ANÁLISE: procurando explicações bagunçadas")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    ruins = []

    for doc in docs:
        data = doc.to_dict()
        expl = data.get("explicacao_ia") or data.get("explicacao") or ""
        if explicacao_eh_ruim(expl):
            # Só regenera se tiver os dados necessários
            enunciado = data.get("enunciado", "")
            alternativas = data.get("alternativas")
            gabarito = data.get("gabarito", "")
            if enunciado and alternativas and gabarito:
                ruins.append({
                    "id": doc.id,
                    "materia": data.get("materia", "geral"),
                    "enunciado": enunciado,
                    "alternativas": alternativas,
                    "gabarito": gabarito,
                    "expl_antiga": expl,
                })

    print(f"\n📊 Total de questões: {len(docs)}")
    print(f"🔴 Com explicação bagunçada (e regeneráveis): {len(ruins)}")

    if ruins:
        por_materia = {}
        for r in ruins:
            por_materia[r["materia"]] = por_materia.get(r["materia"], 0) + 1
        print("\n  Por matéria:")
        for materia, n in sorted(por_materia.items(), key=lambda x: -x[1]):
            print(f"    {materia}: {n}")

    return ruins


# ──────────────────────────────────────────
#  Regenera todas
# ──────────────────────────────────────────
def regenerar_todas(db, ruins, pausa):
    print("\n" + "=" * 70)
    print(f"REGENERANDO {len(ruins)} explicações")
    print("=" * 70)

    sucessos = 0
    falhas = 0

    for i, r in enumerate(ruins, start=1):
        print(f"\n[{i}/{len(ruins)}] {r['materia']} | {r['id'][:8]}")
        print(f"   Enunciado: {r['enunciado'][:60]}...")

        alts_str = formatar_alternativas(r["alternativas"])
        nova = regenerar_explicacao(r["enunciado"], alts_str, r["gabarito"], r["materia"])

        if nova:
            # Mostra preview
            print(f"   ✨ Nova explicação: {nova[:80]}...")
            # Salva no Firebase (atualiza explicacao_ia)
            try:
                db.collection("questoes").document(r["id"]).update({
                    "explicacao_ia": nova,
                    "explicacao_regenerada": True,  # marca que foi limpa
                })
                sucessos += 1
                print(f"   ✅ Salva!")
            except Exception as e:
                print(f"   ❌ Erro ao salvar: {e}")
                falhas += 1
        else:
            falhas += 1

        # Pausa pra respeitar cota Gemini
        if i < len(ruins) and pausa > 0:
            time.sleep(pausa)

    print("\n" + "=" * 70)
    print(f"✅ CONCLUÍDO: {sucessos} regeneradas, {falhas} falhas")
    print("=" * 70)


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n✨ REGENERADOR DE EXPLICAÇÕES — NIVELIS\n")

    ruins = analisar(db)

    if not ruins:
        print("\n🎉 Nenhuma explicação bagunçada! Tudo limpo.")
        sys.exit(0)

    # Estima cota
    print("\n" + "=" * 70)
    print("ATENÇÃO — USO DE COTA GEMINI")
    print("=" * 70)
    print(f"\n  Vai fazer {len(ruins)} chamadas ao Gemini (1 por questão).")
    print(f"  Modelo: gemini-2.5-flash-lite")
    print(f"  Com pausa de 3s entre cada, leva ~{len(ruins) * 3 // 60} min.")
    print(f"\n  Lembre: cota free é 20/dia (ou 1000/dia se ativou billing).")
    if len(ruins) > 20:
        print(f"  ⚠  São {len(ruins)} questões — pode passar da cota free de 20/dia!")
        print(f"     Considere ativar o billing tier, ou rodar em partes.")

    print()
    resp = input("Continuar e regenerar? (sim/nao): ").strip().lower()

    if resp in ("sim", "s", "y", "yes", "1"):
        # Pergunta a pausa
        try:
            pausa_str = input("Pausa entre chamadas em segundos (padrão 3): ").strip()
            pausa = int(pausa_str) if pausa_str else 3
        except ValueError:
            pausa = 3
        regenerar_todas(db, ruins, pausa)
    else:
        print("\nCancelado. Nada foi alterado.")

    print("\n✅ Pronto! Abra o app e veja as explicações limpas.\n")
