"""
=============================================================
  NIVELIS — Analisar Provas em Lote (ENEM + ENADE)
=============================================================

  Baixa e analisa várias provas oficiais de uma vez, salvando
  no cache do Firebase. Respeita a regra de NÃO-REGENERAR:
  provas já em cache são puladas.

  COMO USAR:
    python analisar_provas_lote.py                  (analisa tudo)
    python analisar_provas_lote.py --concurso enem  (só ENEM)
    python analisar_provas_lote.py --concurso enade (só ENADE)
    python analisar_provas_lote.py --pausa 30       (30s entre análises)
    python analisar_provas_lote.py --forcar         (re-analisa tudo)

  ⚠️ CUSTO:
    - Cada prova nova = 1 chamada Gemini (~50-100k tokens)
    - 12 provas = ~12 chamadas (se nenhuma estiver em cache)
    - Rode aos poucos se a cota estiver baixa

  ECONOMIA:
    Provas já analisadas (em provas_analisadas) são PULADAS.
    Rodar de novo só preenche o que falta.

=============================================================
"""

import os
import sys
import io
import json
import time
import uuid
import argparse
import requests
import pdfplumber
import google.generativeai as genai
import firebase_admin
from pathlib        import Path
from dotenv         import load_dotenv
from firebase_admin import credentials, firestore
from datetime       import datetime, timezone

# A chamada `urllib3.disable_warnings(InsecureRequestWarning)` que ficava
# aqui saiu junto com o `verify=False`. Ela calava o aviso de conexão não
# verificada no script INTEIRO — e um silenciador global desses não esconde
# só o problema que existia quando foi escrito, esconde o próximo também.

# ──────────────────────────────────────────
#  CONFIGURAÇÃO
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
    cred = credentials.Certificate("chave-firebase.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ──────────────────────────────────────────
#  LISTA DE PROVAS A ANALISAR
# ──────────────────────────────────────────

PROVAS_PARA_ANALISAR = {
    # ENADE — 3 áreas populares, 3 anos cada
    "enade": [
        {"ano": 2019, "area": "direito"},
        {"ano": 2022, "area": "direito"},
        {"ano": 2022, "area": "administracao"},
        {"ano": 2022, "area": "psicologia"},
        {"ano": 2018, "area": "medicina"},
        {"ano": 2018, "area": "engenharia_civil"},
    ],

    # ENEM — 3 anos, áreas principais
    "enem": [
        {"ano": 2022, "area": "matematica",  "dia": 2, "caderno": 1},
        {"ano": 2023, "area": "matematica",  "dia": 2, "caderno": 1},
        {"ano": 2024, "area": "matematica",  "dia": 2, "caderno": 1},
        {"ano": 2022, "area": "linguagens",  "dia": 1, "caderno": 1},
        {"ano": 2023, "area": "humanas",     "dia": 1, "caderno": 1},
        {"ano": 2024, "area": "natureza",    "dia": 2, "caderno": 1},
    ],
}


# ──────────────────────────────────────────
#  FUNÇÕES AUXILIARES
# ──────────────────────────────────────────

def baixar_pdf(url: str) -> bytes:
    """Baixa um PDF da URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # Certificado verificado (padrão do requests). O `verify=False` que
        # estava aqui aceitava qualquer certificado, inclusive de quem se
        # passasse pelo servidor de origem — e este script alimenta o banco
        # de questões com o que baixa.
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 200:
            return resp.content
        return None
    except requests.exceptions.SSLError as e:
        print(f"      ⚠ Certificado TLS recusado: {e}")
        print( "        Não baixo sem verificar. Atualize o certifi "
               "(pip install -U certifi) ou pegue o arquivo à mão.")
        return None
    except Exception as e:
        print(f"      ⚠ Erro ao baixar: {e}")
        return None


def ja_em_cache(chave: str) -> bool:
    """Verifica se a prova já foi analisada (cache HIT)."""
    doc = db.collection("provas_analisadas").document(chave).get()
    return doc.exists


def analisar_prova_enade(ano: int, area: str) -> dict:
    """Baixa e analisa uma prova do ENADE."""
    url = f"https://download.inep.gov.br/enade/provas_e_gabaritos/{ano}_PV_{area}.pdf"
    pdf_bytes = baixar_pdf(url)

    if not pdf_bytes:
        return {"sucesso": False, "motivo": "PDF não encontrado"}

    return _analisar_pdf(pdf_bytes, f"ENADE {ano} {area}", "enade", ano, area, url)


def analisar_prova_enem(ano: int, area: str, dia: int, caderno: int) -> dict:
    """Baixa e analisa uma prova do ENEM."""
    url = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{caderno}.pdf"
    pdf_bytes = baixar_pdf(url)

    # Fallback: tenta outras cores de caderno
    if not pdf_bytes:
        for cd in range(1, 10):
            if cd == caderno:
                continue
            url_alt = f"https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_PV_impresso_D{dia}_CD{cd}.pdf"
            pdf_bytes = baixar_pdf(url_alt)
            if pdf_bytes:
                url = url_alt
                caderno = cd
                break

    if not pdf_bytes:
        return {"sucesso": False, "motivo": "PDF não encontrado"}

    return _analisar_pdf(
        pdf_bytes, f"ENEM {ano} {area} D{dia}",
        "enem", ano, area, url,
        extras={"dia": dia, "caderno": caderno},
    )


def _analisar_pdf(pdf_bytes: bytes, label: str, concurso: str,
                  ano: int, area: str, url: str, extras: dict = None) -> dict:
    """Análise compartilhada: manda o PDF inteiro para o Gemini."""
    # Conta páginas
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_paginas = len(pdf.pages)
    except Exception:
        total_paginas = 0

    print(f"   📄 PDF de {label}: {total_paginas} páginas, {len(pdf_bytes)/1024/1024:.1f} MB")
    print(f"   🤖 Enviando para análise...")

    prompt = f"""
Você é um especialista em análise de provas do {concurso.upper()}.

Recebeu o PDF COMPLETO da prova de {area.replace('_', ' ')} do {concurso.upper()} {ano}.
Analise TODA a prova (textos, enunciados, gráficos, tabelas, imagens) e
identifique os TÓPICOS de conteúdo cobrados nas questões.

NÃO copie questões. Apenas identifique os TEMAS abordados.

Retorne SOMENTE um JSON válido neste formato:
{{
  "topicos": [
    {{
      "tema": "Nome do tópico",
      "subtopico": "Detalhe específico",
      "estilo_questao": "Como a questão é formulada",
      "nivel": "facil, medio ou dificil",
      "tem_imagem": true ou false
    }}
  ]
}}

Identifique entre 15 e 35 tópicos. Use apenas aspas duplas.
"""

    arquivo_pdf = {
        "mime_type": "application/pdf",
        "data":      pdf_bytes,
    }

    try:
        resposta = modelo.generate_content(
            [arquivo_pdf, prompt],
            generation_config={
                "max_output_tokens":  15000,
                "temperature":        0.3,
                "response_mime_type": "application/json",
            }
        )

        raw = resposta.text.strip().replace("```json", "").replace("```", "").strip()
        resultado = json.loads(raw)
        topicos = resultado.get("topicos", [])

        # Tokens usados
        tokens_input = 0
        tokens_output = 0
        try:
            usage = resposta.usage_metadata
            tokens_input  = usage.prompt_token_count
            tokens_output = usage.candidates_token_count
        except AttributeError:
            pass

        # Monta chave do cache
        if concurso == "enem":
            chave = f"enem_{ano}_{area}_cd{extras.get('caderno', 1)}"
        else:
            chave = f"{concurso}_{ano}_{area}"

        # Salva no Firebase
        doc = {
            "concurso":      concurso,
            "ano":           ano,
            "area":          area,
            "url_pdf":       url,
            "topicos":       topicos,
            "total_paginas": total_paginas,
            "total_topicos": len(topicos),
            "modo_analise":  "pdf_nativo",
            "analisado_em":  datetime.now(timezone.utc),
        }
        if extras:
            doc.update(extras)

        db.collection("provas_analisadas").document(chave).set(doc)

        return {
            "sucesso":       True,
            "chave":         chave,
            "topicos":       len(topicos),
            "paginas":       total_paginas,
            "tokens_input":  tokens_input,
            "tokens_output": tokens_output,
        }

    except json.JSONDecodeError as e:
        return {"sucesso": False, "motivo": f"JSON inválido: {e}"}
    except Exception as e:
        return {"sucesso": False, "motivo": str(e)}


# ──────────────────────────────────────────
#  FUNÇÃO PRINCIPAL
# ──────────────────────────────────────────

def analisar_em_lote(concurso_filtro: str = None, pausa: int = 5, forcar: bool = False):
    """Analisa todas as provas configuradas em PROVAS_PARA_ANALISAR."""
    print("\n" + "=" * 60)
    print("  ANÁLISE EM LOTE DE PROVAS OFICIAIS")
    print(f"  Pausa entre análises: {pausa}s | Forçar: {forcar}")
    print("=" * 60)

    total_analisadas = 0
    total_puladas    = 0
    total_falhas     = 0
    tokens_acumulados = 0

    for concurso, lista in PROVAS_PARA_ANALISAR.items():
        if concurso_filtro and concurso != concurso_filtro:
            continue

        print(f"\n🏛️  {concurso.upper()} ({len(lista)} provas)")

        for prova in lista:
            ano  = prova["ano"]
            area = prova["area"]

            # Monta chave do cache
            if concurso == "enem":
                chave = f"enem_{ano}_{area}_cd{prova.get('caderno', 1)}"
            else:
                chave = f"{concurso}_{ano}_{area}"

            # Pula se já está em cache (a menos que forçar)
            if not forcar and ja_em_cache(chave):
                print(f"   ⏭  {chave} — já em cache, pulando")
                total_puladas += 1
                continue

            print(f"\n   🔎 Analisando {chave}...")

            try:
                if concurso == "enade":
                    res = analisar_prova_enade(ano, area)
                else:  # enem
                    res = analisar_prova_enem(
                        ano, area,
                        prova.get("dia", 1),
                        prova.get("caderno", 1),
                    )

                if res.get("sucesso"):
                    total_analisadas += 1
                    tokens_acumulados += res.get("tokens_input", 0) + res.get("tokens_output", 0)
                    print(f"   ✅ {res['topicos']} tópicos | {res['paginas']} páginas | "
                          f"{res['tokens_input']:,}+{res['tokens_output']:,} tokens")
                else:
                    total_falhas += 1
                    print(f"   ❌ Falhou: {res.get('motivo')}")

                # Pausa para respeitar RPM
                if pausa > 0:
                    print(f"   ⏳ Pausando {pausa}s...")
                    time.sleep(pausa)

            except Exception as e:
                total_falhas += 1
                print(f"   ❌ Exceção: {e}")
                continue

    print("\n" + "=" * 60)
    print(f"  ✅ CONCLUÍDO")
    print(f"     Provas analisadas:  {total_analisadas}")
    print(f"     Provas puladas:     {total_puladas} (já em cache)")
    print(f"     Falhas:             {total_falhas}")
    print(f"     Tokens consumidos:  {tokens_acumulados:,}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analisa provas ENEM/ENADE em lote.")
    parser.add_argument("--concurso", type=str, choices=["enem", "enade"], default=None,
                        help="Analisa só ENEM ou só ENADE (padrão: ambos)")
    parser.add_argument("--pausa", type=int, default=5,
                        help="Pausa em segundos entre análises (padrão 5)")
    parser.add_argument("--forcar", action="store_true",
                        help="Re-analisa mesmo se já em cache (cuidado: gasta Gemini)")

    args = parser.parse_args()
    analisar_em_lote(args.concurso, args.pausa, args.forcar)
