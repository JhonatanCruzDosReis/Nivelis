"""
=============================================================
  NIVELIS — Inventário e limpeza do banco
=============================================================

Faz cinco coisas, nesta ordem de segurança:

  1. CONTA    (padrão)              — não altera nada. Mostra o que existe,
                                      por coleção e por área.
  2. EXPORTA  --exportar            — grava tudo em JSON antes de mexer.
  3. APAGA    --apagar              — coleções inteiras, com confirmação.
  4. FAXINA   --apagar-orfaos       — só o lixo: gabarito sem simulado e
                                      simulado sem questão. Não toca no resto.
  5. ARRUMA   --normalizar-rotulos  — junta "Matemática" e "matematica" num
                                      rótulo só. Reescreve, não apaga.

USO

    python limpar_banco.py                          # só conta
    python limpar_banco.py --exportar               # conta e salva backup
    python limpar_banco.py --apagar questoes        # apaga uma coleção
    python limpar_banco.py --apagar questoes,simulados,gabaritos
    python limpar_banco.py --apagar tudo            # as de conteúdo
    python limpar_banco.py --apagar questoes --sim  # sem perguntar

    python limpar_banco.py --apagar-orfaos          # mostra o que sobrou solto
    python limpar_banco.py --apagar-orfaos --aplicar
    python limpar_banco.py --normalizar-rotulos     # mostra o de-para
    python limpar_banco.py --normalizar-rotulos --aplicar

Os dois últimos são SIMULAÇÃO por padrão. Sem --aplicar, mostram o que
fariam e saem sem escrever nada.

A CREDENCIAL é procurada na pasta deste arquivo (chave-firebase.json),
ou na variável de ambiente FIREBASE_CRED.

⚠️ Exclusão no Firestore NÃO TEM DESFAZER. O --exportar roda sozinho
antes de apagar, a menos que você passe --sem-backup.
=============================================================
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

AQUI = Path(__file__).resolve().parent

# Coleções que guardam CONTEÚDO de estudo — o que "--apagar tudo" alcança.
# Deliberadamente fora: livros e provas_analisadas (material de origem,
# caro de refazer), e qualquer coisa de usuário.
CONTEUDO = ["questoes", "simulados", "gabaritos", "pools_questoes",
            "sessoes_exercicio"]

# Coleções de USUÁRIO. Só sofrem se forem nomeadas explicitamente — apagar
# resultado de aluno junto com questão de teste seria um estrago silencioso.
USUARIO = ["resultados", "resultados_exercicio", "questoes_feitas"]

# Nem conta nem apaga por padrão: são grandes e não são questão.
OUTRAS = ["livros", "provas_analisadas", "provas_processadas",
          "cache_noticias", "uso_tokens", "limite_diario",
          "topicos", "materias"]

# Campos que identificam a "área" de um documento, na ordem em que
# valem a pena. Coleções diferentes usam nomes diferentes.
CAMPOS_AREA = ["materia", "disciplina", "area", "concurso", "topico"]

# Quais desses o --normalizar-rotulos pode reescrever.
#
# "concurso" está de fora de propósito: enem/enade não são rótulos
# bagunca, são chaves que a API compara com ==. E "topico" também:
# tópico é texto livre, mexer nele juntaria assuntos diferentes.
CAMPOS_NORMALIZAVEIS = ["materia", "disciplina", "area"]

# Rótulos que a regra automática NÃO junta, porque juntá-los é uma
# decisão sua, não uma correção de acento.
#
# A regra automática só conserta maiúscula, acento e espaço sobrando:
# "Matemática" e "matematica" são a MESMA palavra escrita de dois jeitos,
# então viram uma. Já "Saúde Coletiva" e "Saúde Pública" são palavras
# diferentes — o programa não tem como saber se você quer as duas juntas.
#
# Para juntar, escreva aqui: forma_canonica_de_origem -> destino.
# A chave é o rótulo JÁ sem acento e minúsculo (é assim que o programa
# enxerga); rode --normalizar-rotulos sem --aplicar para ver a lista
# exata e copiar de lá.
APELIDOS = {
    "redes de computadores": "redes",
}

# Margem de segurança: documento criado há menos disso não é considerado
# órfão. Um simulado pode estar sendo gravado agora, com o gabarito ainda
# a caminho — apagá-lo no meio da escrita seria destruir trabalho vivo.
IDADE_MINIMA_ORFAO = timedelta(hours=1)


def conectar():
    caminho = Path(os.getenv("FIREBASE_CRED") or (AQUI / "chave-firebase.json"))
    if not caminho.exists():
        print(f"❌ Credencial não encontrada em {caminho}")
        print("   Coloque a chave-firebase.json nesta pasta, ou aponte "
              "FIREBASE_CRED para ela.")
        sys.exit(1)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(caminho)))
    return firestore.client()


def _area_de(dados: dict) -> str:
    for campo in CAMPOS_AREA:
        valor = dados.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    # simulados guardam a matéria dentro de meta
    meta = dados.get("meta")
    if isinstance(meta, dict):
        for campo in CAMPOS_AREA:
            valor = meta.get(campo)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
    return "(sem área)"


def canonizar(rotulo: str) -> str:
    """
    A forma única de um rótulo de área.

    Minúscula, sem acento, sem espaço duplicado, sem pontuação nas pontas.
    O SEPARADOR É PRESERVADO de propósito: "ciencias humanas" continua com
    espaço e "ciencias_humanas" continua com underline.

    Trocar um pelo outro parece arrumação, mas quebraria metade das buscas:
    o aplicativo procura matéria por pedaço de texto ("ciencias" dentro de
    "ciencias humanas") enquanto a API compara com == ("ciencias_humanas"
    exato). Qualquer troca de separador agrada um e quebra o outro. Acento
    e maiúscula não têm esse problema: ninguém depende deles.
    """
    t = unicodedata.normalize("NFD", str(rotulo).strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t).strip(" -–—.,;:/")
    return APELIDOS.get(t, t)


def _caminho_area(dados: dict):
    """
    Onde mora o rótulo de área deste documento, e qual é.

    Devolve (caminho, valor) — caminho é "materia" ou "meta.materia",
    no formato que o update() do Firestore entende. Devolve (None, None)
    se o documento não tiver rótulo nenhum.
    """
    for campo in CAMPOS_NORMALIZAVEIS:
        valor = dados.get(campo)
        if isinstance(valor, str) and valor.strip():
            return campo, valor.strip()
    meta = dados.get("meta")
    if isinstance(meta, dict):
        for campo in CAMPOS_NORMALIZAVEIS:
            valor = meta.get(campo)
            if isinstance(valor, str) and valor.strip():
                return f"meta.{campo}", valor.strip()
    return None, None


def inventariar(db, colecoes):
    """Lê tudo e devolve {colecao: {'total': n, 'areas': Counter, 'docs': [...]}}."""
    relatorio = {}
    for nome in colecoes:
        print(f"  lendo {nome}...", end=" ", flush=True)
        try:
            docs = list(db.collection(nome).stream())
        except Exception as e:
            print(f"falhou ({e})")
            relatorio[nome] = {"total": 0, "areas": Counter(), "docs": [],
                               "erro": str(e)}
            continue
        areas = Counter()
        guardados = []
        for d in docs:
            dados = d.to_dict() or {}
            areas[_area_de(dados)] += 1
            guardados.append({"_id": d.id, **dados})
        relatorio[nome] = {"total": len(docs), "areas": areas,
                           "docs": guardados}
        print(f"{len(docs)}")
    return relatorio


def imprimir(relatorio):
    print()
    print("═" * 64)
    print("  O QUE EXISTE HOJE")
    print("═" * 64)

    total_geral = 0
    for nome, info in relatorio.items():
        if info.get("erro"):
            print(f"\n  {nome}: ERRO — {info['erro']}")
            continue
        total_geral += info["total"]
        print(f"\n  {nome}  —  {info['total']} documento(s)")
        if not info["total"]:
            continue
        for area, n in info["areas"].most_common():
            barra = "█" * min(30, max(1, n * 30 // max(info["total"], 1)))
            print(f"      {str(area)[:34]:34s} {n:6d}  {barra}")

    print()
    print("─" * 64)
    print(f"  TOTAL: {total_geral} documento(s)")
    print("─" * 64)
    return total_geral


def exportar(relatorio, destino: Path):
    """Backup em JSON. Data vira texto para o json não engasgar."""
    def limpar(o):
        if isinstance(o, dict):
            return {k: limpar(v) for k, v in o.items()}
        if isinstance(o, list):
            return [limpar(v) for v in o]
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, (str, int, float, bool)) or o is None:
            return o
        return str(o)

    saida = {nome: limpar(info["docs"]) for nome, info in relatorio.items()}
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    tamanho = destino.stat().st_size / 1024
    print(f"\n  💾 Backup: {destino}  ({tamanho:.0f} KB)")
    return destino


def apagar_colecao(db, nome: str, total: int) -> int:
    """
    Apaga em lotes de 400.

    O Firestore aceita no máximo 500 operações por batch, e uma coleção
    grande não cabe em uma só — por isso o laço.
    """
    apagados = 0
    while True:
        docs = list(db.collection(nome).limit(400).stream())
        if not docs:
            break
        lote = db.batch()
        for d in docs:
            lote.delete(d.reference)
        lote.commit()
        apagados += len(docs)
        print(f"      {nome}: {apagados}/{total}", end="\r", flush=True)
    print(f"      {nome}: {apagados} apagado(s)          ")
    return apagados


def apagar_documentos(db, alvos) -> int:
    """
    Apaga documentos escolhidos a dedo — [(colecao, id), ...].

    Diferente de apagar_colecao, que leva a coleção toda. Mesmo limite do
    Firestore: 500 operações por batch, então vai de 400 em 400.
    """
    apagados = 0
    for i in range(0, len(alvos), 400):
        fatia = alvos[i:i + 400]
        lote = db.batch()
        for colecao, doc_id in fatia:
            lote.delete(db.collection(colecao).document(doc_id))
        lote.commit()
        apagados += len(fatia)
        print(f"      apagando... {apagados}/{len(alvos)}", end="\r", flush=True)
    print(f"      {apagados} documento(s) apagado(s).            ")
    return apagados


def escrever_campos(db, alvos) -> int:
    """
    Reescreve um campo por documento — [(colecao, id, caminho, valor), ...].

    O caminho pode ser aninhado ("meta.materia"): o Firestore entende o
    ponto como caminho de campo e troca só aquele, sem reescrever o resto
    do documento.
    """
    escritos = 0
    for i in range(0, len(alvos), 400):
        fatia = alvos[i:i + 400]
        lote = db.batch()
        for colecao, doc_id, caminho, valor in fatia:
            lote.update(db.collection(colecao).document(doc_id),
                        {caminho: valor})
        lote.commit()
        escritos += len(fatia)
        print(f"      gravando... {escritos}/{len(alvos)}", end="\r", flush=True)
    print(f"      {escritos} documento(s) atualizado(s).          ")
    return escritos


# ──────────────────────────────────────────
#  FAXINA — órfãos
# ──────────────────────────────────────────

def _quando(valor):
    """A data de criação, venha ela como for. None se não der para saber."""
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    if isinstance(valor, str):
        try:
            d = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    # Timestamp do Firestore — tem .timestamp() mas não é datetime
    if hasattr(valor, "timestamp"):
        try:
            return datetime.fromtimestamp(valor.timestamp(), tz=timezone.utc)
        except Exception:
            return None
    return None


def achar_orfaos(relatorio):
    """
    O lixo que sobra quando uma geração falha no meio.

    Duas formas:
      • gabarito sem simulado — o simulado foi apagado e a resposta ficou;
      • simulado sem questão  — a gravação morreu antes das questões.

    Devolve (lista_de_alvos, poupados_por_serem_novos). Cada alvo é
    (colecao, id, motivo).
    """
    sim = relatorio.get("simulados")
    gab = relatorio.get("gabaritos")
    if sim is None or gab is None:
        print("\n  ❌ Preciso ler 'simulados' e 'gabaritos' para achar órfãos.")
        return None, []

    # Se a leitura falhou, TODO gabarito parece órfão. Apagar aqui seria
    # confundir "não consegui ler" com "não existe" — e levar os 145.
    for nome, info in (("simulados", sim), ("gabaritos", gab)):
        if info.get("erro"):
            print(f"\n  ❌ A leitura de '{nome}' falhou ({info['erro']}).")
            print("     Sem ela não dá para saber o que é órfão. Abortando.")
            return None, []

    ids_simulados = {d["_id"] for d in sim["docs"]}
    limite = datetime.now(timezone.utc) - IDADE_MINIMA_ORFAO
    alvos, poupados = [], []

    def novo_demais(doc):
        criado = _quando(doc.get("criado_em"))
        return criado is not None and criado > limite

    # 1. Simulado sem questão. Vai junto com o gabarito dele, senão
    #    apagar o simulado cria o órfão que estamos tirando.
    vazios = set()
    for d in sim["docs"]:
        if d.get("questoes"):
            continue
        if novo_demais(d):
            poupados.append(("simulados", d["_id"]))
            continue
        vazios.add(d["_id"])
        alvos.append(("simulados", d["_id"], "sem questões"))

    # 2. Gabarito cujo simulado não existe (ou acabou de entrar na lista
    #    acima). O id do documento É o id do simulado, mas o campo
    #    simulado_id também vale: basta um dos dois achar o par.
    for d in gab["docs"]:
        refs = {d["_id"]}
        if isinstance(d.get("simulado_id"), str) and d["simulado_id"].strip():
            refs.add(d["simulado_id"].strip())
        if refs & ids_simulados and not (refs & vazios):
            continue
        if novo_demais(d):
            poupados.append(("gabaritos", d["_id"]))
            continue
        motivo = ("simulado vai junto" if refs & vazios
                  else "simulado não existe")
        alvos.append(("gabaritos", d["_id"], motivo))

    return alvos, poupados


# ──────────────────────────────────────────
#  ARRUMAÇÃO — rótulos
# ──────────────────────────────────────────

def plano_normalizacao(relatorio, colecoes):
    """
    O de-para dos rótulos: o que muda, o que fica, o que ficou parecido.

    Devolve (escritas, grupos, sozinhos) — escritas é a lista pronta para
    o escrever_campos; grupos é {canonico: Counter(original -> n)} só dos
    que têm mais de uma grafia; sozinhos são os rótulos que ninguém junta.
    """
    escritas = []
    grupos = defaultdict(Counter)

    for nome in colecoes:
        info = relatorio.get(nome)
        if not info or info.get("erro"):
            continue
        for d in info["docs"]:
            caminho, valor = _caminho_area(d)
            if not caminho:
                continue
            alvo = canonizar(valor)
            grupos[alvo][valor] += 1
            if alvo != valor:
                escritas.append((nome, d["_id"], caminho, alvo))

    bagunca = {k: v for k, v in grupos.items() if len(v) > 1 or
                  any(o != k for o in v)}
    sozinhos = sorted(k for k, v in grupos.items()
                      if k not in bagunca)
    return escritas, bagunca, sozinhos


def _parecidos(rotulos):
    """
    Rótulos que começam igual mas o programa não vai juntar.

    Não é adivinhação: é uma lista para você olhar. "saude coletiva" e
    "saude publica" aparecem lado a lado, e aí você decide se viram uma
    só — escrevendo em APELIDOS, no topo do arquivo.
    """
    familias = defaultdict(list)
    for r in rotulos:
        familias[re.split(r"[ _]", r)[0]].append(r)
    return {raiz: sorted(membros) for raiz, membros in familias.items()
            if len(membros) > 1}


def _backup_se_preciso(relatorio, args, etiqueta: str):
    if args.sem_backup:
        return
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    exportar(relatorio, AQUI / f"backup_{etiqueta}_{carimbo}.json")


def _confirmar(args, pergunta: str, palavra: str = "APAGAR") -> bool:
    if args.sim:
        return True
    print()
    return input(f"  {pergunta} ").strip() == palavra


def faxina_orfaos(db, relatorio, args):
    """Mostra os órfãos e, com --aplicar, apaga só eles."""
    print()
    print("═" * 64)
    print("  ÓRFÃOS")
    print("═" * 64)

    alvos, poupados = achar_orfaos(relatorio)
    if alvos is None:
        return

    if poupados:
        print(f"\n  ⏳ {len(poupados)} documento(s) criado(s) na última hora "
              f"ficaram de fora.")
        print("     Pode ser geração em andamento; rode de novo mais tarde.")

    if not alvos:
        print("\n  ✅ Nada solto. O banco está consistente.\n")
        return

    porc = Counter(f"{c} — {motivo}" for c, _, motivo in alvos)
    print()
    for descricao, n in porc.most_common():
        print(f"      {descricao:44s} {n:6d}")
    print(f"\n      TOTAL: {len(alvos)} documento(s)")

    mostra = alvos[:8]
    print("\n  Exemplos:")
    for colecao, doc_id, motivo in mostra:
        print(f"      {colecao}/{doc_id}  ({motivo})")
    if len(alvos) > len(mostra):
        print(f"      ... e mais {len(alvos) - len(mostra)}")

    if not args.aplicar:
        print("\n  Simulação — nada foi alterado.")
        print("  Para apagar de verdade: --apagar-orfaos --aplicar\n")
        return

    print("\n  ⚠️  Exclusão no Firestore não tem desfazer.")
    _backup_se_preciso(relatorio, args, "orfaos")

    if not _confirmar(args, f"Digite APAGAR para remover os {len(alvos)}:"):
        print("\n  Cancelado. Nada foi alterado.\n")
        return

    print()
    apagar_documentos(db, [(c, i) for c, i, _ in alvos])
    print()


def arrumar_rotulos(db, relatorio, colecoes, args):
    """Mostra o de-para dos rótulos e, com --aplicar, reescreve."""
    print()
    print("═" * 64)
    print("  RÓTULOS DE ÁREA")
    print("═" * 64)

    escritas, bagunca, sozinhos = plano_normalizacao(relatorio, colecoes)

    if not bagunca:
        print("\n  ✅ Todo rótulo já está na forma única.\n")
    else:
        print()
        for canonico in sorted(bagunca):
            formas = bagunca[canonico]
            total = sum(formas.values())
            print(f"      → {canonico}   ({total} doc)")
            for original, n in formas.most_common():
                marca = "  (já está)" if original == canonico else ""
                print(f"           {original:38s} {n:6d}{marca}")

    familias = _parecidos(sozinhos + list(bagunca))
    if familias:
        print("\n  ── Parecidos, mas NÃO vou juntar ──")
        print("     Se algum par for a mesma coisa, escreva em APELIDOS,")
        print("     no topo deste arquivo, e rode de novo.")
        for raiz, membros in sorted(familias.items()):
            print(f"      {raiz}: {', '.join(membros)}")

    if not escritas:
        print("\n  Nada a reescrever.\n")
        return

    print(f"\n      {len(escritas)} documento(s) vão ser reescrito(s).")
    print("      Só o campo do rótulo muda; o resto do documento fica igual.")

    if not args.aplicar:
        print("\n  Simulação — nada foi alterado.")
        print("  Para gravar de verdade: --normalizar-rotulos --aplicar\n")
        return

    _backup_se_preciso(relatorio, args, "rotulos")

    if not _confirmar(args, f"Digite ARRUMAR para reescrever os "
                            f"{len(escritas)}:", "ARRUMAR"):
        print("\n  Cancelado. Nada foi alterado.\n")
        return

    print()
    escrever_campos(db, escritas)
    print()


def main():
    p = argparse.ArgumentParser(
        description="Inventário e limpeza do banco do Nivelis.")
    p.add_argument("--apagar", metavar="COLECOES",
                   help="separadas por vírgula, ou 'tudo' para as de conteúdo")
    p.add_argument("--exportar", action="store_true",
                   help="salva backup JSON mesmo sem apagar")
    p.add_argument("--sem-backup", action="store_true",
                   help="pula o backup automático antes de apagar")
    p.add_argument("--sim", action="store_true",
                   help="não pergunta a confirmação")
    p.add_argument("--apagar-orfaos", action="store_true",
                   help="remove gabarito sem simulado e simulado sem questão")
    p.add_argument("--normalizar-rotulos", action="store_true",
                   help="junta 'Matemática' e 'matematica' num rótulo só")
    p.add_argument("--aplicar", action="store_true",
                   help="sai da simulação: as duas opções acima passam a "
                        "escrever de verdade")
    p.add_argument("--incluir-usuario", action="store_true",
                   help=f"conta também {', '.join(USUARIO)}")
    p.add_argument("--incluir-outras", action="store_true",
                   help=f"conta também {', '.join(OUTRAS)}")
    args = p.parse_args()

    if args.aplicar and not (args.apagar_orfaos or args.normalizar_rotulos):
        print("\n  ⚠️  --aplicar sozinho não faz nada: ele tira a simulação "
              "de --apagar-orfaos\n      e --normalizar-rotulos. Para apagar "
              "coleção inteira, use --apagar.\n")

    db = conectar()

    colecoes = list(CONTEUDO)
    if args.incluir_usuario:
        colecoes += USUARIO
    if args.incluir_outras:
        colecoes += OUTRAS

    # Quem vai ser apagado precisa ser lido, mesmo fora da lista padrão.
    alvos = []
    if args.apagar:
        alvos = (list(CONTEUDO) if args.apagar.strip().lower() == "tudo"
                 else [c.strip() for c in args.apagar.split(",") if c.strip()])
        for c in alvos:
            if c not in colecoes:
                colecoes.append(c)

    # Achar órfão exige os dois lados da conta.
    if args.apagar_orfaos:
        for c in ("simulados", "gabaritos"):
            if c not in colecoes:
                colecoes.append(c)

    print("\nLendo o banco (nada é alterado nesta etapa)...")
    relatorio = inventariar(db, colecoes)
    imprimir(relatorio)

    if args.apagar_orfaos:
        faxina_orfaos(db, relatorio, args)

    if args.normalizar_rotulos:
        arrumar_rotulos(db, relatorio, colecoes, args)

    if args.exportar and not alvos:
        carimbo = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        exportar(relatorio, AQUI / f"backup_banco_{carimbo}.json")

    if not alvos:
        if args.apagar_orfaos or args.normalizar_rotulos:
            return
        print("\n  Nada foi apagado. Para apagar, use --apagar.")
        print("  Ex.: python limpar_banco.py --apagar questoes,simulados,gabaritos\n")
        return

    # ── A partir daqui, destrutivo ──
    a_apagar = sum(relatorio[c]["total"] for c in alvos if c in relatorio)
    print()
    print("═" * 64)
    print("  VAI APAGAR")
    print("═" * 64)
    for c in alvos:
        print(f"      {c:24s} {relatorio.get(c, {}).get('total', 0):6d}")
    print(f"\n      TOTAL: {a_apagar} documento(s)")
    print("\n  ⚠️  Exclusão no Firestore não tem desfazer.")

    perigosas = [c for c in alvos if c in USUARIO]
    if perigosas:
        print(f"  ⚠️  {', '.join(perigosas)} guarda(m) dado de USUÁRIO, "
              f"não questão de teste.")

    if a_apagar == 0:
        print("\n  Não há nada para apagar.\n")
        return

    if not args.sem_backup:
        carimbo = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        exportar(relatorio, AQUI / f"backup_banco_{carimbo}.json")

    if not args.sim:
        print()
        resposta = input(f'  Digite APAGAR para confirmar os {a_apagar}: ')
        if resposta.strip() != "APAGAR":
            print("\n  Cancelado. Nada foi alterado.\n")
            return

    print()
    total = 0
    for c in alvos:
        total += apagar_colecao(db, c, relatorio.get(c, {}).get("total", 0))
    print(f"\n  ✅ {total} documento(s) apagado(s).\n")


if __name__ == "__main__":
    main()
