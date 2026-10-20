"""
=============================================================
  NIVELIS — Revisar Reclassificação (antes de aplicar)
=============================================================

  Mostra as questões que MUDARIAM para uma matéria específica,
  pra você conferir se a reclassificação está certa ANTES de aplicar.

  COMO USAR:
    cd K:\\nivelis-teste\\Nivelis-Api

    # Ver o que vai virar 'matematica' (os casos suspeitos):
    python revisar_reclassificacao.py matematica

    # Ver o que vai virar biologia, etc:
    python revisar_reclassificacao.py biologia

=============================================================
"""

import os
import sys
import re
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    chave = "chave-nivelis.json" if os.path.exists("chave-nivelis.json") else "chave-firebase.json"
    cred = credentials.Certificate(chave)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── MESMAS palavras-chave do reclassificar_materias.py ───
PALAVRAS_POR_MATERIA = {
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
    "fisica": [
        r'\btransfer[êe]ncia de calor\b', r'\birradia[çc]', r'\bconve[çc][ãa]o\b',
        r'\bcondu[çc][ãa]o t[ée]rmica\b', r'\btermodin[âa]mica\b',
        r'\bvelocidade\b.*\bacelera', r'\bforça\b.*\bnewton', r'\benergia cin[ée]tica\b',
        r'\benergia potencial\b', r'\bpot[êe]ncia\b.*\bwatt', r'\bcorrente el[ée]trica\b',
        r'\btens[ãa]o\b.*\bvolt', r'\bresist[êe]ncia\b.*\bohm', r'\bonda\b.*\bfrequ',
        r'\brefra[çc][ãa]o\b', r'\breflex[ãa]o\b.*\bluz', r'\b[óo]tica\b',
        r'\bmovimento uniforme\b', r'\bqueda livre\b', r'\bgravidade\b',
    ],
    "biologia": [
        r'\bbioma\b', r'\bcerrado\b', r'\becossistema\b', r'\besp[ée]cies?\b',
        r'\bc[ée]lula\b', r'\bDNA\b', r'\bgen[ée]tica\b', r'\bcromossomo\b',
        r'\bfotoss[íi]ntese\b', r'\borganismo\b', r'\banf[íi]bio', r'\bmam[íi]fero',
        r'\bvegeta[çc][ãa]o\b', r'\bfauna\b', r'\bflora\b', r'\bbiodiversidade\b',
        r'\bpredador', r'\bcadeia alimentar\b', r'\bhabitat\b', r'\bevolu[çc][ãa]o\b',
        r'\btoxina\b', r'\bveneno\b.*\bplanta', r'\bnicho ecol', r'\binvas[ãa]o.*esp[ée]cie',
        r'\bplantas exóticas\b', r'\bnativa', r'\bpolui[çc]',
    ],
    "quimica": [
        r'\breação qu[íi]mica\b', r'\b[áa]tomo\b', r'\bmol[ée]cula\b', r'\bmol\b',
        r'\btabela peri[óo]dica\b', r'\belemento qu[íi]mico\b', r'\b[íi]on\b',
        r'\b[áa]cido\b.*\bbase\b', r'\bph\b', r'\boxida[çc]', r'\bcombust[ãa]o\b',
        r'\bsolu[çc][ãa]o\b.*\bconcentra', r'\bcompostos?\b.*\borg[âa]nic',
    ],
    "historia": [
        r'\bs[ée]culo [xiv]+\b', r'\bguerra\b', r'\brevolu[çc][ãa]o\b',
        r'\bimp[ée]rio\b', r'\bcolonial', r'\bescravid[ãa]o\b', r'\bescravizado',
        r'\brep[úu]blica\b', r'\bmonarquia\b', r'\bditadura\b', r'\bindepend[êe]ncia\b',
        r'\bidade m[ée]dia\b', r'\bfeudalismo\b', r'\bcapitalismo\b.*hist',
        r'\babolição\b', r'\balforria\b', r'\bfeitor\b',
    ],
    "geografia": [
        r'\burbaniza[çc][ãa]o\b', r'\bsegrega[çc][ãa]o socioespacial\b',
        r'\bmetr[óo]pole\b', r'\b[êe]xodo rural\b', r'\bsaneamento b[áa]sico\b',
        r'\brede de esgoto\b', r'\bclima\b.*\bregi[ãa]o', r'\brelevo\b',
        r'\bpopula[çc][ãa]o\b.*\bdensidade', r'\bmigra[çc][ãa]o\b', r'\bperiferia\b',
        r'\bgentrifica[çc]', r'\bvertical[íi]za', r'\bfronteira agr[íi]cola\b',
        r'\bagroneg[óo]cio\b', r'\bdistribui[çc][ãa]o de renda\b',
    ],
    "filosofia": [
        r'\bfil[óo]sofo\b', r'\bfilosofia\b', r'\bwittgenstein\b', r'\bmaquiavel\b',
        r'\bplat[ãa]o\b', r'\barist[óo]teles\b', r'\bkant\b', r'\bnietzsche\b',
        r'\bfoucault\b', r'\barendt\b', r'\b[ée]tica\b', r'\bmetaf[íi]sica\b',
        r'\bepistemologia\b', r'\bexist[êe]ncia\b.*\bser\b', r'\bjogos de linguagem\b',
        r'\bo pr[íi]ncipe\b', r'\bcontrato social\b', r'\besfera p[úu]blica\b', r'\bcondi[çc][ãa]o humana\b', r'\ba[çc][ãa]o comunicativa\b', r'\bhabermas\b', r'\bchomsky\b', r'\bkuhn\b', r'\bparadigma\b',
    ],
    "sociologia": [
        r'\bpatriarcado\b', r'\bviol[êe]ncia de g[êe]nero\b', r'\bviol[êe]ncia contra a mulher\b',
        r'\bdesigualdade de g[êe]nero\b', r'\bmachismo\b', r'\bempoderamento\b',
        r'\bmovimento social\b', r'\bclasse social\b', r'\bexclus[ãa]o social\b',
        r'\bexclus[ãa]o digital\b', r'\bfosso digital\b', r'\bcidadania\b',
        r'\bcomunidades? tradicion', r'\bquilombola', r'\bribeirinh', r'\bind[íi]gena',
        r'\bsaberes ancestrais\b', r'\bidentidade cultural\b', r'\bpatrim[ôo]nio imaterial\b',
    ],
    "atualidades": [
        r'\bfiocruz\b', r'\bpandemia\b', r'\bcovid', r'\bor[çc]amento federal\b',
        r'\bor[çc]amento discricion', r'\bminist[ée]rio da sa[úu]de\b',
        r'\bsoberania sanit', r'\bvacina', r'\bvigil[âa]ncia sanit', r'\bsus\b',
        r'\bpol[íi]tica p[úu]blica\b', r'\bfomento\b.*\bci[êe]ncia',
    ],
    "linguagens": [
        r'\btirinha\b', r'\bcharge\b', r'\bquadrinho', r'\bfigura de linguagem\b',
        r'\bmet[áa]fora\b', r'\bmet[ôo]nimia\b', r'\ban[áa]lise sint[áa]tica\b',
        r'\bora[çc][ãa]o\b.*\bsujeito', r'\bverbo\b.*\bconjuga', r'\bcr[óo]nica\b',
        r'\bpoema\b', r'\bpoesia\b', r'\bsoneto\b', r'\beu l[íi]rico\b',
        r'\bvariação lingu', r'\bnorma culta\b', r'\bden[oo]tativo\b', r'\bconotativo\b',
    ],
    "direito": [
        r'\bconstitui[çc][ãa]o federal\b', r'\bart(igo)?\.?\s*\d+.*\bconstitui',
        r'\bc[óo]digo civil\b', r'\bc[óo]digo penal\b', r'\bhabeas corpus\b',
        r'\bdireito constitucional\b', r'\bdireito penal\b', r'\bdireito civil\b',
        r'\bjurisprud[êe]ncia\b', r'\bsupremo tribunal\b', r'\bstf\b',
        r'\blei\b.*\bn[ºo°]\s*\d', r'\bpetição\b', r'\bprocesso judicial\b',
        r'\bcontrato\b.*\bcl[áa]usula', r'\bresponsabilidade civil\b',
    ],
    "administracao": [
        r'\badministra[çc][ãa]o\b.*\bempresa', r'\bgest[ãa]o\b.*\borganiza',
        r'\bplanejamento estrat[ée]gico\b', r'\brecursos humanos\b',
        r'\bmarketing\b', r'\bcontabilidade\b', r'\bbalanço patrimonial\b',
        r'\bfluxo de caixa\b', r'\blideran[çc]a\b.*\bequipe',
    ],
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


def classificar_por_palavras(data):
    enunciado = (data.get("enunciado") or "").lower()
    contexto  = (data.get("contexto") or "").lower()
    alternativas = data.get("alternativas")
    alt_texto = ""
    if isinstance(alternativas, list):
        for alt in alternativas:
            if isinstance(alt, dict):
                alt_texto += " " + (alt.get("texto") or alt.get("text") or "")
    elif isinstance(alternativas, dict):
        alt_texto = " ".join(str(v) for v in alternativas.values())
    texto = f"{enunciado} {contexto} {alt_texto}".lower()

    scores = {}
    matches_por_materia = {}
    for materia, padroes in PALAVRAS_POR_MATERIA.items():
        matches = [p for p in padroes if re.search(p, texto)]
        if matches:
            scores[materia] = len(matches)
            matches_por_materia[materia] = matches
    if not scores:
        return None, []
    melhor = max(scores, key=scores.get)
    return melhor, matches_por_materia[melhor]


if __name__ == "__main__":
    alvo = sys.argv[1].lower() if len(sys.argv) > 1 else "matematica"

    print(f"\n🔍 REVISANDO questões que virariam '{alvo}'\n")
    print("=" * 70)

    docs = list(db.collection("questoes").stream())
    encontradas = []

    for doc in docs:
        data = doc.to_dict()
        atual = (data.get("materia") or "").lower().strip()
        sugerida, matches = classificar_por_palavras(data)
        # Só as que MUDARIAM para o alvo (atual != alvo, sugerida == alvo)
        if sugerida == alvo and atual != alvo:
            encontradas.append({
                "id": doc.id,
                "atual": atual,
                "enunciado": data.get("enunciado") or "",
                "matches": matches,
            })

    print(f"📊 {len(encontradas)} questões virariam '{alvo}'\n")

    for i, q in enumerate(encontradas, start=1):
        print("─" * 70)
        print(f"[{i}] {q['atual']} → {alvo}  (id: {q['id'][:8]})")
        print(f"    Palavras que bateram: {', '.join(q['matches'][:5])}")
        print(f"    ENUNCIADO: {q['enunciado'][:200]}")
        print()

    print("=" * 70)
    print(f"FIM — {len(encontradas)} questões que virariam '{alvo}'")
    print("=" * 70)
    print("\n👆 Confira se essas mudanças fazem sentido!")
    print("   Se alguma estiver errada, me avise (pode ser palavra-chave enganosa).\n")
