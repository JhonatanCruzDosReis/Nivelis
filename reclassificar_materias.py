"""
=============================================================
  NIVELIS — Reclassificador de Matérias (HÍBRIDO)
=============================================================

  Corrige o campo 'materia' das questões baseado no CONTEÚDO real.
  Muitas questões estão classificadas errado (ex: bioma Cerrado
  marcado como "matematica").

  ESTRATÉGIA HÍBRIDA (economiza cota):
    1. PALAVRAS-CHAVE resolvem a maioria (grátis, instantâneo)
    2. Gemini só nos casos DUVIDOSOS (que não bateram palavra clara)

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api

    # Modo análise (só mostra o que MUDARIA, não altera nada):
    python reclassificar_materias.py

    # Aplicar as mudanças (só as por palavra-chave, sem IA):
    python reclassificar_materias.py --aplicar

    # Aplicar + usar IA nos duvidosos (gasta cota nos poucos difíceis):
    python reclassificar_materias.py --aplicar --usar-ia

=============================================================
"""

import os
import sys
import re
import time
import firebase_admin
from firebase_admin import credentials, firestore

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────
if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    if not os.path.exists(chave):
        print("❌ Não achei a chave do Firebase! Rode na pasta do backend.")
        sys.exit(1)
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Gemini só é carregado se --usar-ia
modelo = None
def init_gemini():
    global modelo
    if modelo is None:
        import google.generativeai as genai
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).parent / ".env")
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            print("❌ GEMINI_API_KEY não configurada (necessária pra --usar-ia)")
            sys.exit(1)
        genai.configure(api_key=key)
        modelo = genai.GenerativeModel("gemini-2.5-flash-lite")
    return modelo


# ═══════════════════════════════════════════════════════════════════════════════
#  PALAVRAS-CHAVE POR MATÉRIA
#  Cada matéria tem palavras FORTES que denunciam o conteúdo.
#  Ordem importa: matérias mais específicas primeiro.
# ═══════════════════════════════════════════════════════════════════════════════
PALAVRAS_POR_MATERIA = {
    # ── MATEMÁTICA ── (exige contexto matemático real, evita falsos positivos)
    "matematica": [
        r'\bcalcul\w+', r'\bequa[çc][ãa]o\b', r'\bf\(x\)', r'\bgr[áa]fico da fun[çc]',
        r'\bdesconto de \d', r'\blucro de \d', r'\bpre[çc]o\b.*\br\$', r'\br\$\s*\d.*\bcalcul',
        r'\bvolume\b.*\b(cilindro|esfera|cubo|cone|litros?|m[³3])',
        r'\b[áa]rea\b.*\b(m[²2]|ret[âa]ngul|c[íi]rculo|tri[âa]ngul|calcul)',
        r'\bper[íi]metro\b', r'\braio de \d', r'\bdi[âa]metro de \d',
        r'\bm[ée]dia\b.*\b(aritm[ée]tica|dos? \d|calcul)',
        r'\bmediana\b.*\b(dados|valores|\d)', r'\bmoda\b.*\b(dados|frequ|estat)',
        r'\banagrama', r'\bcombina[çc][ãa]o\b.*\b(\d|element)', r'\barranjo\b.*\d',
        r'\bfatorial\b', r'\bpermuta[çc]',
        r'\bprobabilidade de\b', r'\bteorema de pit', r'\bpit[áa]goras\b', r'\bhipotenusa\b',
        r'\btri[âa]ngulo\b.*\b(ret[âa]ng|lado|[áa]rea)',
        r'\bret[âa]ngulo\b.*\b(lado|[áa]rea|m[²2])',
        r'\bcilindro\b', r'\bpir[âa]mide\b.*\b(volume|base|altura)', r'\bhex[áa]gono\b',
        r'\d+\s*cm[²³23]', r'\d+\s*m[²³23]\b', r'\d+\s*kg\b',
        r'\bde quantas maneiras\b', r'\bquantos\b.*\bposs[íi]ve', r'\bquantas\b.*\bdistint',
        r'\bdensidade\b.*\b(g/cm|kg/m|massa)', r'\bescala\b.*\d+\s*:\s*\d', r'\bπ\b',
        r'\bjuros\b.*\b(compost|simples|\d%)', r'\bmontante\b', r'\btaxa de juros\b',
    ],
    # ── FÍSICA ──
    "fisica": [
        r'\btransfer[êe]ncia de calor\b', r'\birradia[çc]', r'\bconve[çc][ãa]o\b',
        r'\bcondu[çc][ãa]o t[ée]rmica\b', r'\btermodin[âa]mica\b',
        r'\bvelocidade\b.*\bacelera', r'\bforça\b.*\bnewton', r'\benergia cin[ée]tica\b',
        r'\benergia potencial\b', r'\bpot[êe]ncia\b.*\bwatt', r'\bcorrente el[ée]trica\b',
        r'\btens[ãa]o\b.*\bvolt', r'\bresist[êe]ncia\b.*\bohm', r'\bonda\b.*\bfrequ',
        r'\brefra[çc][ãa]o\b', r'\breflex[ãa]o\b.*\bluz', r'\b[óo]tica\b',
        r'\bmovimento uniforme\b', r'\bqueda livre\b', r'\bgravidade\b',
    ],
    # ── BIOLOGIA ──
    "biologia": [
        r'\bbioma\b', r'\bcerrado\b', r'\becossistema\b', r'\besp[ée]cies?\b',
        r'\bc[ée]lula\b', r'\bDNA\b', r'\bgen[ée]tica\b', r'\bcromossomo\b',
        r'\bfotoss[íi]ntese\b', r'\borganismo\b', r'\banf[íi]bio', r'\bmam[íi]fero',
        r'\bvegeta[çc][ãa]o\b', r'\bfauna\b', r'\bflora\b', r'\bbiodiversidade\b',
        r'\bpredador', r'\bcadeia alimentar\b', r'\bhabitat\b', r'\bevolu[çc][ãa]o\b',
        r'\btoxina\b', r'\bveneno\b.*\bplanta', r'\bnicho ecol', r'\binvas[ãa]o.*esp[ée]cie',
        r'\bplantas exóticas\b', r'\bnativa', r'\bpolui[çc]',
    ],
    # ── QUÍMICA ──
    "quimica": [
        r'\breação qu[íi]mica\b', r'\b[áa]tomo\b', r'\bmol[ée]cula\b', r'\bmol\b',
        r'\btabela peri[óo]dica\b', r'\belemento qu[íi]mico\b', r'\b[íi]on\b',
        r'\b[áa]cido\b.*\bbase\b', r'\bph\b', r'\boxida[çc]', r'\bcombust[ãa]o\b',
        r'\bsolu[çc][ãa]o\b.*\bconcentra', r'\bcompostos?\b.*\borg[âa]nic',
    ],
    # ── HISTÓRIA ──
    "historia": [
        r'\bs[ée]culo [xiv]+\b', r'\bguerra\b', r'\brevolu[çc][ãa]o\b',
        r'\bimp[ée]rio\b', r'\bcolonial', r'\bescravid[ãa]o\b', r'\bescravizado',
        r'\brep[úu]blica\b', r'\bmonarquia\b', r'\bditadura\b', r'\bindepend[êe]ncia\b',
        r'\bidade m[ée]dia\b', r'\bfeudalismo\b', r'\bcapitalismo\b.*hist',
        r'\babolição\b', r'\balforria\b', r'\bfeitor\b',
    ],
    # ── GEOGRAFIA ──
    "geografia": [
        r'\burbaniza[çc][ãa]o\b', r'\bsegrega[çc][ãa]o socioespacial\b',
        r'\bmetr[óo]pole\b', r'\b[êe]xodo rural\b', r'\bsaneamento b[áa]sico\b',
        r'\brede de esgoto\b', r'\bclima\b.*\bregi[ãa]o', r'\brelevo\b',
        r'\bpopula[çc][ãa]o\b.*\bdensidade', r'\bmigra[çc][ãa]o\b', r'\bperiferia\b',
        r'\bgentrifica[çc]', r'\bvertical[íi]za', r'\bfronteira agr[íi]cola\b',
        r'\bagroneg[óo]cio\b', r'\bdistribui[çc][ãa]o de renda\b',
    ],
    # ── FILOSOFIA ──
    "filosofia": [
        r'\bfil[óo]sofo\b', r'\bfilosofia\b', r'\bwittgenstein\b', r'\bmaquiavel\b',
        r'\bplat[ãa]o\b', r'\barist[óo]teles\b', r'\bkant\b', r'\bnietzsche\b',
        r'\bfoucault\b', r'\barendt\b', r'\b[ée]tica\b', r'\bmetaf[íi]sica\b',
        r'\bepistemologia\b', r'\bexist[êe]ncia\b.*\bser\b', r'\bjogos de linguagem\b',
        r'\bo pr[íi]ncipe\b', r'\bcontrato social\b', r'\besfera p[úu]blica\b', r'\bcondi[çc][ãa]o humana\b', r'\ba[çc][ãa]o comunicativa\b', r'\bhabermas\b', r'\bchomsky\b', r'\bkuhn\b', r'\bparadigma\b',
    ],
    # ── SOCIOLOGIA ──
    "sociologia": [
        r'\bpatriarcado\b', r'\bviol[êe]ncia de g[êe]nero\b', r'\bviol[êe]ncia contra a mulher\b',
        r'\bdesigualdade de g[êe]nero\b', r'\bmachismo\b', r'\bempoderamento\b',
        r'\bmovimento social\b', r'\bclasse social\b', r'\bexclus[ãa]o social\b',
        r'\bexclus[ãa]o digital\b', r'\bfosso digital\b', r'\bcidadania\b',
        r'\bcomunidades? tradicion', r'\bquilombola', r'\bribeirinh', r'\bind[íi]gena',
        r'\bsaberes ancestrais\b', r'\bidentidade cultural\b', r'\bpatrim[ôo]nio imaterial\b',
    ],
    # ── ATUALIDADES ──
    "atualidades": [
        r'\bfiocruz\b', r'\bpandemia\b', r'\bcovid', r'\bor[çc]amento federal\b',
        r'\bor[çc]amento discricion', r'\bminist[ée]rio da sa[úu]de\b',
        r'\bsoberania sanit', r'\bvacina', r'\bvigil[âa]ncia sanit', r'\bsus\b',
        r'\bpol[íi]tica p[úu]blica\b', r'\bfomento\b.*\bci[êe]ncia',
    ],
    # ── LINGUAGENS / PORTUGUÊS ──
    "linguagens": [
        r'\btirinha\b', r'\bcharge\b', r'\bquadrinho', r'\bfigura de linguagem\b',
        r'\bmet[áa]fora\b', r'\bmet[ôo]nimia\b', r'\ban[áa]lise sint[áa]tica\b',
        r'\bora[çc][ãa]o\b.*\bsujeito', r'\bverbo\b.*\bconjuga', r'\bcr[óo]nica\b',
        r'\bpoema\b', r'\bpoesia\b', r'\bsoneto\b', r'\beu l[íi]rico\b',
        r'\bvariação lingu', r'\bnorma culta\b', r'\bden[oo]tativo\b', r'\bconotativo\b',
    ],
    # ── DIREITO (real) ──
    "direito": [
        r'\bconstitui[çc][ãa]o federal\b', r'\bart(igo)?\.?\s*\d+.*\bconstitui',
        r'\bc[óo]digo civil\b', r'\bc[óo]digo penal\b', r'\bhabeas corpus\b',
        r'\bdireito constitucional\b', r'\bdireito penal\b', r'\bdireito civil\b',
        r'\bjurisprud[êe]ncia\b', r'\bsupremo tribunal\b', r'\bstf\b',
        r'\blei\b.*\bn[ºo°]\s*\d', r'\bpetição\b', r'\bprocesso judicial\b',
        r'\bcontrato\b.*\bcl[áa]usula', r'\bresponsabilidade civil\b',
    ],
    # ── ADMINISTRAÇÃO ──
    "administracao": [
        r'\badministra[çc][ãa]o\b.*\bempresa', r'\bgest[ãa]o\b.*\borganiza',
        r'\bplanejamento estrat[ée]gico\b', r'\brecursos humanos\b',
        r'\bmarketing\b', r'\bcontabilidade\b', r'\bbalanço patrimonial\b',
        r'\bfluxo de caixa\b', r'\blideran[çc]a\b.*\bequipe',
    ],
    # ── REDES / COMPUTAÇÃO ──
    "redes": [
        r'\bprotocolo\b.*\b(tcp|ip|http)', r'\brede de computadores\b',
        r'\bendere[çc]o ip\b', r'\bsub-?rede\b', r'\brouteador\b', r'\bswitch\b',
        r'\bfirewall\b', r'\btopologia de rede\b', r'\bmodelo osi\b',
    ],
    "programacao": [
        r'\balgoritmo\b', r'\bestrutura de dados\b', r'\bvari[áa]vel\b.*\bc[óo]digo',
        r'\bfun[çc][ãa]o\b.*\bprogram', r'\bla[çc]o\b.*\brepeti', r'\bloop\b',
        r'\borienta[çc][ãa]o a objetos\b', r'\bclasse\b.*\bm[ée]todo', r'\bpython\b',
        r'\bjava\b', r'\bjavascript\b', r'\bbanco de dados\b.*\bsql',
    ],
}

# Nível de confiança: quantas palavras precisam bater pra ter certeza
MIN_MATCHES_CONFIANCA = 1  # 1 palavra forte já classifica


def classificar_por_palavras(data: dict):
    """
    Retorna (materia_sugerida, confianca, matches).
    confianca: 'alta' (bateu palavra forte), 'nenhuma' (não bateu nada).
    """
    enunciado = (data.get("enunciado") or "").lower()
    contexto  = (data.get("contexto") or "").lower()
    alternativas = data.get("alternativas")

    # Junta texto das alternativas também
    alt_texto = ""
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                alt_texto += " " + (alt.get("texto") or alt.get("text") or "")
    elif isinstance(alternativas, dict):
        alt_texto = " ".join(str(v) for v in alternativas.values())

    texto = f"{enunciado} {contexto} {alt_texto}".lower()

    # Conta matches por matéria
    scores = {}
    matches_por_materia = {}
    for materia, padroes in PALAVRAS_POR_MATERIA.items():
        matches = []
        for padrao in padroes:
            if re.search(padrao, texto):
                matches.append(padrao)
        if matches:
            scores[materia] = len(matches)
            matches_por_materia[materia] = matches

    if not scores:
        return None, "nenhuma", []

    # Matéria com mais matches vence
    melhor = max(scores, key=scores.get)
    return melhor, "alta", matches_por_materia[melhor]


# ──────────────────────────────────────────
#  Classificação via IA (só nos duvidosos)
# ──────────────────────────────────────────
MATERIAS_VALIDAS = list(PALAVRAS_POR_MATERIA.keys())

def classificar_por_ia(data: dict):
    m = init_gemini()
    enunciado = (data.get("enunciado") or "")[:800]
    materias_str = ", ".join(MATERIAS_VALIDAS)
    prompt = f"""Classifique a matéria/disciplina desta questão de prova.

QUESTÃO:
{enunciado}

Escolha UMA matéria desta lista: {materias_str}

Responda APENAS com o nome da matéria (uma palavra da lista). Nada mais."""
    try:
        resp = m.generate_content(prompt, generation_config={"max_output_tokens": 20, "temperature": 0})
        sugerida = resp.text.strip().lower()
        # Valida se está na lista
        for mat in MATERIAS_VALIDAS:
            if mat in sugerida:
                return mat
        return None
    except Exception as e:
        print(f"      ⚠ Erro IA: {e}")
        return None


# ──────────────────────────────────────────
#  Análise / Aplicação
# ──────────────────────────────────────────
def processar(db, aplicar, usar_ia):
    print("=" * 70)
    modo = "APLICAR" if aplicar else "ANÁLISE (nada será alterado)"
    print(f"RECLASSIFICAÇÃO DE MATÉRIAS — modo: {modo}")
    if usar_ia:
        print("IA ATIVADA para casos duvidosos")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    print(f"\n📊 Total de questões: {len(docs)}\n")

    mudancas = []       # (id, materia_atual, materia_nova, origem)
    duvidosas = []      # não bateram palavra-chave
    sem_mudanca = 0

    for doc in docs:
        data = doc.to_dict()
        materia_atual = (data.get("materia") or "").lower().strip()

        sugerida, confianca, matches = classificar_por_palavras(data)

        if confianca == "nenhuma":
            duvidosas.append({"id": doc.id, "data": data, "atual": materia_atual})
            continue

        if sugerida != materia_atual:
            mudancas.append({
                "id": doc.id,
                "atual": materia_atual,
                "nova": sugerida,
                "origem": "palavra-chave",
                "enunciado": (data.get("enunciado") or "")[:50],
            })
        else:
            sem_mudanca += 1

    # ─── Resultado palavras-chave ───
    print(f"✅ Já corretas (sem mudança):        {sem_mudanca}")
    print(f"🔄 Mudanças por palavra-chave:       {len(mudancas)}")
    print(f"❓ Duvidosas (não bateram palavra):  {len(duvidosas)}")

    # Estatística de mudanças
    if mudancas:
        print("\n  Mudanças mais comuns (atual → nova):")
        transicoes = {}
        for m in mudancas:
            chave = f"{m['atual']} → {m['nova']}"
            transicoes[chave] = transicoes.get(chave, 0) + 1
        for trans, n in sorted(transicoes.items(), key=lambda x: -x[1])[:15]:
            print(f"    {trans}: {n}")

    # Amostra
    if mudancas:
        print("\n  Amostra de mudanças (até 10):")
        for m in mudancas[:10]:
            print(f"    [{m['atual']:12} → {m['nova']:12}] {m['enunciado']}...")

    # ─── IA nos duvidosos ───
    if usar_ia and duvidosas:
        print(f"\n{'─'*70}")
        print(f"USANDO IA nos {len(duvidosas)} casos duvidosos...")
        print(f"⚠  Isso gasta cota (1 chamada cada). Cota free: 20/dia.")
        if len(duvidosas) > 20:
            print(f"   São {len(duvidosas)} — pode estourar. Processa o que der.")
        resp = input("\nContinuar com IA? (sim/nao): ").strip().lower()
        if resp in ("sim", "s", "y", "yes"):
            for i, d in enumerate(duvidosas, start=1):
                print(f"  [{i}/{len(duvidosas)}] {d['id'][:8]} (atual: {d['atual']})", end=" ")
                sugerida = classificar_por_ia(d["data"])
                if sugerida and sugerida != d["atual"]:
                    print(f"→ IA: {sugerida}")
                    mudancas.append({
                        "id": d["id"], "atual": d["atual"], "nova": sugerida,
                        "origem": "ia", "enunciado": (d["data"].get("enunciado") or "")[:50],
                    })
                elif sugerida:
                    print(f"→ IA confirma {sugerida} (sem mudança)")
                else:
                    print("→ IA não classificou")
                time.sleep(3)

    # ─── Aplicar ───
    if aplicar and mudancas:
        print(f"\n{'='*70}")
        print(f"APLICAR {len(mudancas)} MUDANÇAS?")
        print("="*70)
        resp = input("Confirma? (sim/nao): ").strip().lower()
        if resp in ("sim", "s", "y", "yes"):
            batch = db.batch()
            contador = 0
            for m in mudancas:
                ref = db.collection("questoes").document(m["id"])
                batch.update(ref, {
                    "materia": m["nova"],
                    "materia_reclassificada": True,
                    "materia_anterior": m["atual"],
                })
                contador += 1
                if contador % 400 == 0:
                    batch.commit()
                    batch = db.batch()
                    print(f"    ... {contador}")
            batch.commit()
            print(f"\n  ✅ {contador} matérias reclassificadas!")
        else:
            print("Cancelado. Nada alterado.")
    elif not aplicar:
        print(f"\n💡 Isso foi só ANÁLISE. Para aplicar: python reclassificar_materias.py --aplicar")
        if duvidosas and not usar_ia:
            print(f"   Para classificar os {len(duvidosas)} duvidosos com IA: adicione --usar-ia")

    return mudancas, duvidosas


# ──────────────────────────────────────────
#  Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n📚 RECLASSIFICADOR DE MATÉRIAS (HÍBRIDO) — NIVELIS\n")

    aplicar = "--aplicar" in sys.argv
    usar_ia = "--usar-ia" in sys.argv

    processar(db, aplicar, usar_ia)

    print("\n" + "=" * 70)
    print("Concluído!")
    print("=" * 70)
