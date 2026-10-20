"""
=============================================================
  TESTE 10 — ROBUSTEZ E REPRODUTIBILIDADE
=============================================================
  Os outros testes verificam a QUALIDADE do que sai. Este
  verifica o COMPORTAMENTO do sistema:

    • a mesma semente produz sempre o mesmo lote?
    • entrada malformada quebra ou é tratada?
    • todos os templates são alcançáveis?
    • quanta variedade cada template oferece?
    • o formato de saída é o que a API espera?

  Um gerador que produz questão excelente mas quebra com
  parâmetro inesperado não serve em produção.

  USO: python teste_10_robustez.py
=============================================================
"""

import sys
import traceback
from collections import Counter

sys.path.insert(0, ".")

import gerador_ads, gerador_procedural, gerador_saude
import gerador_decoreba, gerador_direito, gerador_redes
import gerador_interpretacao
from _trechos_teste import TRECHOS_TESTE

# Geradores acrescentados ao longo do projeto entram apenas se estiverem
# presentes. Import direto quebrava a suíte inteira quando um arquivo
# faltava no diretório — e o teste de robustez é justamente o que não
# pode deixar de rodar.
OPCIONAIS = {}
for _nome, _modulo in [("Fisiologia", "gerador_fisiologia"),
                       ("Anatomia", "gerador_anatomia")]:
    try:
        OPCIONAIS[_nome] = __import__(_modulo)
    except ImportError:
        pass

GERADORES = [
    ("ADS",        gerador_ads),
    ("Matemática", gerador_procedural),
    ("Saúde",      gerador_saude),
    ("Conceitual", gerador_decoreba),
    ("Direito",    gerador_direito),
    ("Redes",      gerador_redes),
]


def testar_reprodutibilidade():
    """
    Mesma semente, mesmo resultado — sempre.

    Sem isso, investigar um problema relatado é impossível: o
    usuário informa a seed e o lote sai diferente.
    """
    print("\n  ── 10a) Reprodutibilidade ──\n")
    falhas = 0
    for nome, mod in GERADORES:
        a = mod.gerar_lote(60, seed=12345)
        b = mod.gerar_lote(60, seed=12345)
        iguais = all(
            x["enunciado"] == y["enunciado"] and
            x["alternativas"] == y["alternativas"] and
            x["gabarito"] == y["gabarito"]
            for x, y in zip(a, b)
        ) and len(a) == len(b)

        # E sementes diferentes devem dar lotes diferentes
        c = mod.gerar_lote(60, seed=54321)
        variam = any(x["enunciado"] != z["enunciado"] for x, z in zip(a, c))

        ok = iguais and variam
        falhas += 0 if ok else 1
        detalhe = ("determinístico e sensível à seed" if ok
                   else ("NÃO determinístico" if not iguais
                         else "ignora a seed"))
        print(f"     {'✅' if ok else '❌'} {nome:<12} {detalhe}")
    return falhas


def testar_entradas_malformadas():
    """
    O que acontece com parâmetro inesperado?

    Quantidade zero, negativa, absurda; tópico inexistente;
    lista de templates vazia. O esperado é erro claro ou
    comportamento sensato — nunca stack trace.
    """
    print("\n  ── 10b) Entradas malformadas ──\n")
    falhas = 0

    CASOS = [
        ("quantidade=0",        dict(quantidade=0)),
        ("quantidade=-5",       dict(quantidade=-5)),
        ("quantidade=1",        dict(quantidade=1)),
        ("tópico inexistente",  dict(quantidade=5, topico="xyz_nao_existe")),
        ("tópico None",         dict(quantidade=5, topico=None)),
        ("templates vazio",     dict(quantidade=5, templates=[])),
        ("template inválido",   dict(quantidade=5, templates=["nao_existe"])),
        ("seed None",           dict(quantidade=5, seed=None)),
        ("seed negativa",       dict(quantidade=5, seed=-99)),
    ]

    for nome, mod in GERADORES:
        problemas = []
        for descricao, kwargs in CASOS:
            try:
                r = mod.gerar_lote(**kwargs)
                # Sucesso: o retorno precisa ser lista coerente
                if not isinstance(r, list):
                    problemas.append(f"{descricao}: retornou {type(r).__name__}")
                elif kwargs.get("quantidade", 0) > 0 and len(r) == 0:
                    problemas.append(f"{descricao}: lista vazia")
            except (ValueError, KeyError) as e:
                # Erro esperado e tratado — aceitável
                pass
            except Exception as e:
                problemas.append(f"{descricao}: {type(e).__name__}: {str(e)[:40]}")

        falhas += len(problemas)
        marca = "✅" if not problemas else "❌"
        print(f"     {marca} {nome:<12} {len(CASOS)} casos"
              f"{'' if not problemas else f' — {len(problemas)} falha(s)'}")
        for p in problemas[:3]:
            print(f"          ⚠ {p}")
    return falhas


def testar_cobertura_templates():
    """
    Todo template registrado é alcançável pela geração?

    Um template que nunca é sorteado é código morto — e pior,
    nunca é testado pelos outros testes.
    """
    print("\n  ── 10c) Cobertura dos templates ──\n")
    falhas = 0
    for nome, mod in GERADORES:
        tabela = (getattr(mod, "TEMPLATES_ADS", None)
                  or getattr(mod, "TEMPLATES_SAUDE", None)
                  or getattr(mod, "TEMPLATES_DECOREBA", None)
                  or getattr(mod, "TEMPLATES_DIREITO", None)
                  or getattr(mod, "TEMPLATES_REDES", None)
                  or getattr(mod, "TEMPLATES", {}))
        if not tabela:
            continue

        # Gera o suficiente para todos aparecerem
        lote = mod.gerar_lote(len(tabela) * 30, seed=777)
        vistos = Counter(q.get("topico") for q in lote)

        # Confere que cada template gera individualmente
        mortos = []
        for tnome, fn in tabela.items():
            import random as _r
            try:
                if fn(_r.Random(1)) is None:
                    mortos.append(tnome)
            except Exception as e:
                mortos.append(f"{tnome} ({type(e).__name__})")

        falhas += len(mortos)
        marca = "✅" if not mortos else "❌"
        print(f"     {marca} {nome:<12} {len(tabela)} templates, "
              f"{len(vistos)} tópicos distintos gerados")
        for m in mortos[:3]:
            print(f"          ⚠ template inacessível: {m}")
    return falhas


def testar_variedade():
    """
    Quantas questões DISTINTAS cada gerador oferece?

    Espaço pequeno significa repetição rápida para o aluno.
    Não é falha, mas precisa ser medido e visível.
    """
    print("\n  ── 10d) Variedade (enunciados distintos) ──\n")
    alertas = 0
    for nome, mod in GERADORES:
        lote = mod.gerar_lote(1500, seed=2026)
        unicos = len({q["enunciado"] for q in lote})
        taxa = unicos / len(lote)

        # Abaixo de 50% significa que metade repete em 1500 gerações
        marca = "✅" if taxa >= 0.5 else ("⚠ " if taxa >= 0.3 else "❌")
        if taxa < 0.3:
            alertas += 1
        print(f"     {marca} {nome:<12} {unicos:>4} distintos em 1500 "
              f"({taxa:>5.1%})")

        # Detalha os templates mais pobres
        por_topico = {}
        for q in lote:
            por_topico.setdefault(q["topico"], set()).add(q["enunciado"])
        pobres = sorted(por_topico.items(), key=lambda x: len(x[1]))[:2]
        for topico, enunciados in pobres:
            if len(enunciados) < 15:
                print(f"          · {topico}: só {len(enunciados)} enunciados")
    return alertas


def testar_contrato_api():
    """
    O formato de gerar_para_api é o que salvar_questoes_banco espera?

    Campos internos (tipo_resposta, resposta_bruta, origem) NÃO podem
    vazar para o app; os campos obrigatórios precisam existir.
    """
    print("\n  ── 10e) Contrato da API ──\n")
    falhas = 0
    OBRIGATORIOS_Q = {"numero", "enunciado", "alternativas", "tem_elemento_visual"}
    OBRIGATORIOS_G = {"numero", "resposta_correta", "explicacao"}
    PROIBIDOS = {"tipo_resposta", "resposta_bruta", "origem", "topico"}

    for nome, mod in GERADORES:
        problemas = []
        qs, gb = mod.gerar_para_api(quantidade=40, seed=99)

        if len(qs) != len(gb):
            problemas.append(f"{len(qs)} questões para {len(gb)} gabaritos")

        for q in qs:
            faltando = OBRIGATORIOS_Q - set(q)
            if faltando:
                problemas.append(f"questão sem {faltando}")
                break
            vazando = PROIBIDOS & set(q)
            if vazando:
                problemas.append(f"campo interno vazou: {vazando}")
                break
            if len(q["alternativas"]) != 5:
                problemas.append(f"{len(q['alternativas'])} alternativas")
                break

        for g in gb:
            faltando = OBRIGATORIOS_G - set(g)
            if faltando:
                problemas.append(f"gabarito sem {faltando}")
                break

        # Numeração sequencial e casada
        if [q["numero"] for q in qs] != list(range(1, len(qs) + 1)):
            problemas.append("numeração não sequencial")
        if [q["numero"] for q in qs] != [g["numero"] for g in gb]:
            problemas.append("numeração de questão e gabarito não casam")

        falhas += len(problemas)
        marca = "✅" if not problemas else "❌"
        print(f"     {marca} {nome:<12} formato "
              f"{'correto' if not problemas else 'com problema'}")
        for p in problemas[:3]:
            print(f"          ⚠ {p}")
    return falhas


def testar_interpretacao_robustez():
    """Entradas degeneradas no gerador de interpretação."""
    print("\n  ── 10f) Robustez da interpretação ──\n")
    falhas = 0
    CASOS = [
        ("lista vazia",        []),
        ("um trecho só",       TRECHOS_TESTE[:1]),
        ("dois trechos",       TRECHOS_TESTE[:2]),
        ("trecho sem tese",    [{**TRECHOS_TESTE[0], "tese": ""}] + TRECHOS_TESTE[1:]),
        ("sem pressupostos",   [{**t, "pressupostos": []} for t in TRECHOS_TESTE]),
        ("sem falsas",         [{**t, "afirmacoes_falsas": []} for t in TRECHOS_TESTE]),
        ("campos None",        [{**t, "ideia_secundaria": None} for t in TRECHOS_TESTE]),
    ]
    for descricao, trechos in CASOS:
        try:
            r = gerador_interpretacao.gerar_lote(trechos, 5, seed=1)
            estado = f"gerou {len(r)}"
            ok = isinstance(r, list)
        except ValueError:
            estado = "ValueError (tratado)"
            ok = True
        except Exception as e:
            estado = f"{type(e).__name__}: {str(e)[:40]}"
            ok = False
        falhas += 0 if ok else 1
        print(f"     {'✅' if ok else '❌'} {descricao:<20} {estado}")
    return falhas


def testar_casamento_por_area():
    """
    Um livro só pode acionar geradores da SUA área.

    O casamento é por palavra-chave, e várias palavras existem em mais de
    um domínio: "rede" (de computadores / de atenção à saúde), "porta"
    (TCP / de entrada do SUS), "classificação" (algoritmo de ordenação /
    de risco). Sem separar as ambíguas das inequívocas, um Caderno do
    Ministério da Saúde gerava questões sobre firewall e máscara de
    sub-rede.

    Este teste fixa o comportamento esperado para livros de cada área.
    """
    print("\n  ── 10g) Casamento por área ──\n")

    CASOS = [
        ("Saúde pública (interpretativo)",
         ["Acolhimento à demanda espontânea", "Rede de atenção à saúde",
          "Classificação de risco", "Protocolo de acolhimento",
          "Porta de entrada do SUS", "Fluxo dos usuários na unidade",
          "Equipe de referência", "Escuta qualificada"],
         set()),                       # nenhum gerador deve casar

        ("Redes de computadores",
         ["Endereçamento IP", "Sub-redes", "Máscara de sub-rede", "CIDR",
          "Roteamento", "MTU e fragmentação", "IPv6", "VLSM"],
         {"redes"}),

        ("Epidemiologia",
         ["Prevalência", "Incidência", "Estudos de coorte", "Caso-controle",
          "Sensibilidade e especificidade", "Viés e confundimento"],
         {"saude", "medicina"}),      # ambos cobrem epidemiologia
                                      # (medicina é opcional)

        ("Direito processual",
         ["Prazos processuais", "Apelação", "Agravo de instrumento",
          "Embargos de declaração", "Prescrição"],
         {"direito"}),

        ("Combinatória",
         ["Análise Combinatória", "Arranjos", "Permutações",
          "Binômio de Newton", "Triângulo de Pascal"],
         {"matematica"}),

        ("Fisiologia",
         ["Curva de dissociação da hemoglobina", "Efeito Bohr",
          "Filtração glomerular", "Arteríola aferente", "Débito cardíaco"],
         {"fisiologia"}),

        ("Anatomia",
         ["Nervos cranianos", "Terminologia Anatômica", "Forame jugular",
          "Epônimos", "Base do crânio"],
         {"anatomia"}),

        ("Literatura (sem gerador)",
         ["Romantismo", "Modernismo", "Machado de Assis", "Poesia lírica",
          "Figuras de linguagem"],
         set()),
    ]

    MAPA = {"ads": gerador_ads, "conceitual": gerador_decoreba,
            "redes": gerador_redes, "saude": gerador_saude,
            "direito": gerador_direito, "matematica": gerador_procedural}
    # Geradores acrescentados depois entram se estiverem presentes
    for _chave, _mod in [("fisiologia", "gerador_fisiologia"),
                         ("anatomia", "gerador_anatomia")]:
        try:
            MAPA[_chave] = __import__(_mod)
        except ImportError:
            pass
    # Geradores de computação convivem entre si; a checagem é por DOMÍNIO
    COMPUTACAO = {"ads", "conceitual", "redes"}
    # Saúde, medicina e fisiologia se sobrepõem de propósito:
    # epidemiologia aparece em mais de um, e fisiologia renal toca
    # temas cobertos pelo gerador de saúde.
    SAUDE = {"saude", "medicina", "fisiologia", "anatomia"}

    falhas = 0
    for nome, topicos, esperados in CASOS:
        casados = set()
        for chave, mod in MAPA.items():
            fn = getattr(mod, "templates_para_topicos", None)
            if fn and fn(topicos):
                casados.add(chave)

        if not esperados:
            ok = not casados
            detalhe = "nenhum casamento" if ok else f"casou com {sorted(casados)}"
        else:
            # Os "afins" são calculados com a lista ORIGINAL: um gerador
            # ausente não deixa de indicar o domínio do caso.
            afins = set()
            if esperados & COMPUTACAO:
                afins |= COMPUTACAO
            if esperados & SAUDE:
                afins |= SAUDE

            # Já a exigência de presença considera só os geradores que
            # existem neste diretório. O teste roda em ambientes onde nem
            # todos os arquivos estão disponíveis, e cobrar um módulo
            # ausente transformaria uma condição de ambiente em falha de
            # casamento.
            esperados = {e for e in esperados if e in MAPA}
            if not esperados:
                print(f"     ·  {nome:<32} geradores esperados ausentes "
                      f"neste diretório")
                continue

            # Os esperados precisam estar; nada de OUTRO domínio pode entrar
            dominio_ok = esperados <= casados
            fora = casados - esperados - afins
            ok = dominio_ok and not fora
            detalhe = f"{sorted(casados)}"
            if not dominio_ok:
                detalhe += f" — faltou {sorted(esperados - casados)}"
            elif fora:
                detalhe += f" — invadiu {sorted(fora)}"

        falhas += 0 if ok else 1
        print(f"     {'✅' if ok else '❌'} {nome:<32} {detalhe}")
    return falhas


if __name__ == "__main__":
    print("═" * 64)
    print("  TESTE 10 — ROBUSTEZ E REPRODUTIBILIDADE")
    print("═" * 64)

    total = 0
    total += testar_reprodutibilidade()
    total += testar_entradas_malformadas()
    total += testar_cobertura_templates()
    testar_variedade()          # informativo, não conta como falha
    total += testar_contrato_api()
    total += testar_interpretacao_robustez()
    total += testar_casamento_por_area()

    print("\n" + "═" * 64)
    print(f"  {'🎉 TESTE 10 PASSOU' if total == 0 else f'❌ {total} PROBLEMA(S)'}")
    print("═" * 64)
    sys.exit(1 if total else 0)
