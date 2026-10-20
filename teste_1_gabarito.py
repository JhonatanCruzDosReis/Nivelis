"""
=============================================================
  TESTE 1 — GABARITO
=============================================================
  Recalcula a resposta de cada questão com lógica INDEPENDENTE
  (escrita separadamente do gerador) e compara com o gabarito.

  Se o gerador e este teste discordam, um dos dois está errado —
  e isso aparece imediatamente.

  USO: python teste_1_gabarito.py [quantidade]
=============================================================
"""
import sys, re, ipaddress
from math       import comb, perm, factorial, ceil, log2
from itertools  import product
from fractions  import Fraction
from collections import Counter

sys.path.insert(0, ".")


def _valor(txt):
    """
    Converte texto de alternativa em número.
    Aceita fração (2/3), percentual (95,8%), formato BR (1.234,56) e ns.
    """
    # Remove marcadores de unidade e moeda antes de converter
    t = str(txt).strip().rstrip("%").replace(" ns", "").replace("R$", "").strip()
    if "/" in t and re.fullmatch(r'\d+\s*/\s*\d+', t):
        a, b = t.split("/")
        return float(a) / float(b)
    # separador de milhar só quando seguido de 3 dígitos
    t = re.sub(r'\.(?=\d{3}\b)', "", t).replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# ── Verificadores independentes, um por família de questão ──

def v_pilha(e):
    ops = re.findall(r'empilha\((\d+)\)|(desempilha\(\))', e)
    p, rem = [], []
    for val, des in ops:
        if val: p.append(int(val))
        else:   rem.append(p.pop())
    if "topo da pilha" in e:       return p[-1]
    if "quantos elementos" in e:   return len(p)
    return rem[-1]

def v_fila(e):
    ops = re.findall(r'insere\((\d+)\)|(remove\(\))', e)
    f = []
    for val, r in ops:
        if val: f.append(int(val))
        else:   f.pop(0)
    return f[0] if "frente da fila" in e else len(f)

def v_arvore(e):
    m = re.search(r'\n\n([\d,\s]+?)\n\n', e)
    if not m: return None
    vals = [int(x) for x in m.group(1).split(",")]
    class N:
        __slots__ = ("v","e","d")
        def __init__(s,v): s.v,s.e,s.d = v,None,None
    def ins(r,v):
        if r is None: return N(v)
        if v < r.v: r.e = ins(r.e,v)
        else:       r.d = ins(r.d,v)
        return r
    raiz = None
    for v in vals: raiz = ins(raiz,v)
    pre = lambda n: ([n.v]+pre(n.e)+pre(n.d)) if n else []
    pos = lambda n: (pos(n.e)+pos(n.d)+[n.v]) if n else []
    alt = lambda n: 0 if n is None else 1+max(alt(n.e),alt(n.d))
    def fol(n):
        if n is None: return 0
        if n.e is None and n.d is None: return 1
        return fol(n.e)+fol(n.d)
    if "PRÉ-ORDEM" in e:  return ", ".join(map(str, pre(raiz)))
    if "PÓS-ORDEM" in e:  return ", ".join(map(str, pos(raiz)))
    if "altura" in e:     return alt(raiz)
    return fol(raiz)

def v_logica(e):
    m = re.search(r'\n\n(.+?)\n\n', e, re.S)
    if not m: return None
    mapa = {
        "(p ∧ q) → r":       lambda p,q,r: (not(p and q)) or r,
        "p ∨ (q ∧ ¬r)":      lambda p,q,r: p or (q and not r),
        "(p → q) ∧ (q → r)": lambda p,q,r: ((not p) or q) and ((not q) or r),
        "¬(p ∧ q) ∨ r":      lambda p,q,r: (not(p and q)) or r,
        "(p ↔ q) ∧ r":       lambda p,q,r: (p==q) and r,
        "p ⊕ (q ∨ r)":       lambda p,q,r: p != (q or r),
    }
    fn = mapa.get(m.group(1).strip())
    if not fn: return None
    return sum(1 for a,b,c in product([True,False],repeat=3) if fn(a,b,c))

def v_redes(e):
    m = re.search(r'([\d.]+/\d+)', e)
    if not m: return None
    rd = ipaddress.ip_network(m.group(1), strict=False)
    if "atribuídos a hosts" in e:    return rd.num_addresses - 2
    if "máscara de sub-rede" in e:   return str(rd.netmask)
    if "broadcast" in e:             return str(rd.broadcast_address)
    return None

def v_sql(e):
    linhas = [(n,d,int(s)) for n,d,s in
              re.findall(r'\n\s+(\w+)\s+\|\s+(\w+)\s+\|\s+(\d+)', e)]
    if not linhas: return None
    if "MAX(salario)" in e:
        lim = int(re.search(r'salario > (\d+)', e).group(1))
        cand = [s for _,_,s in linhas if s > lim]
        return max(cand) if cand else None
    if "AVG(salario)" in e:
        sal = [s for _,d,s in linhas if d == "TI"]
        return round(sum(sal)/len(sal)) if sal else None
    if "WHERE salario >" in e:
        lim = int(re.search(r'salario > (\d+)', e).group(1))
        return sum(1 for _,_,s in linhas if s > lim)
    m = re.search(r"departamento '(\w+)'", e)
    if m: return sum(1 for _,d,_ in linhas if d == m.group(1))
    return None

def v_grafos(e):
    m = re.search(r'(\d+)\s*(?:vértices|nós|usuários|equipamentos|dispositivos|páginas|itens)', e)
    if not m: return None
    n = int(m.group(1))
    if "máximo de arestas" in e or "conexões possíveis" in e or "conectividade total" in e:
        return comb(n, 2)
    if "árvore" in e or "sem formar ciclos" in e or "sem ciclos" in e or "pai-filho" in e:
        return n - 1
    if "grau" in e or "diretamente conectado" in e:
        return n - 1
    if "arcos" in e or "links possíveis" in e:
        return n * (n - 1)
    return None

def v_bases(e):
    m = re.search(r'decimal (\d+)', e)
    if m and "base 2" in e:  return bin(int(m.group(1)))[2:]
    if m and "base 16" in e: return hex(int(m.group(1)))[2:].upper()
    m2 = re.search(r'binário ([01]+)', e)
    if m2: return str(int(m2.group(1), 2))
    m3 = re.search(r'hexadecimal ([0-9A-F]+)', e)
    if m3: return str(int(m3.group(1), 16))
    return None

def v_bubble(e):
    m = re.search(r'(\d+)\s*(?:elementos|registros|números|posições)', e)
    if not m: return None
    n = int(m.group(1))
    return n * (n - 1) // 2

def v_contagem(e):
    ranges = re.findall(r'range\(([^)]+)\)', e)
    if len(ranges) != 2: return None
    a = [x.strip() for x in ranges[0].split(",")]
    b = [x.strip() for x in ranges[1].split(",")]
    try:
        if b[0] == "i":
            n = int(b[1]); return sum(1 for i in range(n) for j in range(i, n))
        if len(a) == 3:
            n = int(a[1]); return sum(1 for i in range(0, n, 2) for j in range(n))
        n = int(a[1]); return n * n
    except (ValueError, IndexError):
        return None

def v_circular(e):
    m = re.search(r'(\d+)\s*(?:pessoas|integrantes|conselheiros|amigos|contas)', e)
    return factorial(int(m.group(1)) - 1) if m else None

def v_pascal(e):
    # Cuidado: o enunciado cita "como a linha 0" ao explicar a convenção.
    # A linha perguntada é a ÚLTIMA citada, não a primeira.
    todas = re.findall(r'linha (\d+)', e)
    if todas: return 2 ** int(todas[-1])
    m = re.search(r'(\d+) elementos distintos', e)
    if m: return 2 ** int(m.group(1))
    m = re.search(r'C\((\d+),0\)', e)
    if m: return 2 ** int(m.group(1))
    m = re.search(r'\(a \+ b\)\^(\d+)', e)
    if m: return 2 ** int(m.group(1))
    return None

def v_dados(e):
    m = re.search(r'(?:igual a|ser|soma apostada de|vale) (\d+)', e)
    if not m: return None
    s = int(m.group(1))
    if not 2 <= s <= 12: return None
    return Fraction(6 - abs(s - 7), 36)

def v_binomial(e):
    mn = re.search(r'(\d+)\s*(?:vezes|verificações|pessoas|filhos|peças)', e)
    mk = re.search(r'exatamente (\d+)', e)
    if not (mn and mk): return None
    n, k = int(mn.group(1)), int(mk.group(1))
    if k > n: return None
    return Fraction(comb(n, k), 2 ** n)

def v_podio(e):
    m = re.search(r'(\d+)\s*(?:finalistas|competidores|participantes)', e)
    return perm(int(m.group(1)), 3) if m else None


# ── Verificadores dos templates de Eng. Software e CC ──

def v_pontos_funcao(e):
    pares = re.findall(r':\s*(\d+) de complexidade \w+ \(peso (\d+)\)', e)
    if not pares: return None
    return sum(int(q) * int(p) for q, p in pares)

def v_ciclomatica(e):
    if "ciclomática" not in e: return None
    n_if    = int(re.search(r'(\d+) comando\(s\) if', e).group(1)) if "comando(s) if" in e else 0
    n_while = int(re.search(r'(\d+) laço\(s\) while', e).group(1)) if "laço(s) while" in e else 0
    n_and   = int(re.search(r'(\d+) operador\(es\)', e).group(1)) if "operador(es)" in e else 0
    return n_if + n_while + n_and + 1

def v_caminhos(e):
    m = re.search(r'(\d+) (?:comandos if independentes|decisões binárias independentes|'
                  r'verificações condicionais independentes)', e)
    return 2 ** int(m.group(1)) if m else None

def v_cobertura(e):
    if "cobertura de linhas" not in e and "cobertura de código" not in e:
        return None
    nums = [int(x) for x in re.findall(r'\d+', e)]
    if len(nums) < 2: return None
    cob, tot = min(nums[0], nums[1]), max(nums[0], nums[1])
    return round(cob / tot * 100, 1)

def v_velocidade(e):
    m = re.search(r'(?:história|pontos)[:\s]+((?:\d+,\s*)+\d+)', e)
    if not m or "velocidade média" not in e: return None
    pts = [int(x) for x in re.findall(r'\d+', m.group(1))]
    return round(sum(pts) / len(pts), 1)

def v_sprints(e):
    if "sprints" not in e or "backlog" not in e.lower(): return None
    m1 = re.search(r'(\d+) pontos de história|(\d+) pontos pendentes|Restam (\d+) pontos', e)
    m2 = re.search(r'(\d+) pontos por sprint|(\d+) pontos a cada sprint', e)
    if not (m1 and m2): return None
    b = int(next(g for g in m1.groups() if g))
    v = int(next(g for g in m2.groups() if g))
    return ceil(b / v)

def v_esforco(e):
    if "homens-hora" not in e: return None
    nums = [int(x) for x in re.findall(r'\d+', e)]
    if len(nums) < 3: return None
    devs, horas, dias = nums[0], nums[1], nums[2]
    return devs * horas * dias

def v_hash_posicao(e):
    m1 = re.search(r'k mod (\d+)', e)
    m2 = re.search(r'chave (\d+)', e)
    if not (m1 and m2) or "índice" not in e and "posição" not in e: return None
    if "colis" in e or "sondagem" in e: return None
    return int(m2.group(1)) % int(m1.group(1))

def v_enderecamento(e):
    if not re.search(r'(?:posições de memória|células endereçáveis|'
                     r'endereços possíveis)', e): return None
    m = re.search(r'(\d+) bits', e)
    return 2 ** int(m.group(1)) if m else None

def v_hit_rate(e):
    # Só a questão que PERGUNTA a taxa (não a que a fornece como dado)
    if "tempo médio" in e: return None
    if not re.search(r'(?:Qual é a taxa de acerto|taxa de acertos obtida|'
                     r'Determine o hit rate)', e): return None
    m = re.search(r'(\d+) (?:acessos|referências)[^\d]+(\d+)', e)
    if not m: return None
    tot, fal = int(m.group(1)), int(m.group(2))
    return round((tot - fal) / tot * 100, 1)

def v_tempo_medio(e):
    if "tempo médio de acesso" not in e: return None
    ns = [int(x) for x in re.findall(r'(\d+) ns', e)]
    mh = re.search(r'(\d+)%', e)
    if len(ns) < 2 or not mh: return None
    tc, tr, h = min(ns), max(ns), int(mh.group(1))
    return round(tc * (h/100) + tr * (1 - h/100), 2)



# ── Verificadores da área de SAÚDE (recálculo independente) ──

def v_gotejamento(e):
    m = re.search(r'(\d+) mL[^.]*?(\d+) horas', e)
    if not m: return None
    vol, hrs = int(m.group(1)), int(m.group(2))
    if "microgotas" in e:
        return round(vol / hrs)
    if "gotas por minuto" in e or "gotas" in e:
        return round(vol / (hrs * 3))
    return None

def v_tempo_infusao(e):
    if "tempo" not in e.lower() and "horas a infusão" not in e: return None
    m = re.search(r'(\d+) mL', e)
    g = re.search(r'(\d+) gotas por minuto', e)
    if not (m and g): return None
    return round(int(m.group(1)) / (int(g.group(1)) * 3), 1)

def v_diluicao(e):
    m = re.search(r'(\d+) mg[^.]*?(\d+) mL', e)
    d = re.search(r'(?:solicita|prescrita a dose de|indica|administrar) (\d+) mg', e)
    if not (m and d): return None
    conc_mg, conc_ml, dose = int(m.group(1)), int(m.group(2)), int(d.group(1))
    return round(dose * conc_ml / conc_mg, 2)

def v_dose_peso(e):
    mk = re.search(r'([\d,]+) mg/kg', e)
    pk = re.search(r'(\d+) kg', e)
    if not (mk and pk): return None
    mg_kg = float(mk.group(1).replace(",", "."))
    peso  = int(pk.group(1))
    total = mg_kg * peso
    dv = re.search(r'dividida em (\d+) administra', e)
    return round(total / int(dv.group(1)), 1) if dv else round(total, 1)

def v_prevalencia(e):
    if "prevalência" not in e.lower(): return None
    nums = [int(x.replace(".", "")) for x in re.findall(r'\d[\d.]*', e)]
    if len(nums) < 2: return None
    pop, casos = max(nums[0], nums[1]), min(nums[0], nums[1])
    return round(casos / pop * 100000)

def v_incidencia(e):
    if "incidência" not in e.lower(): return None
    nums = [int(x.replace(".", "")) for x in re.findall(r'\d[\d.]*', e)]
    nums = [n for n in nums if n not in (1000, 12)]
    if len(nums) < 2: return None
    exp, novos = max(nums[0], nums[1]), min(nums[0], nums[1])
    return round(novos / exp * 1000, 1)

def _tabela_2x2(e):
    """Extrai (vp, fp, fn, vn) de tabela Doente/Não doente."""
    mp = re.search(r'Teste positivo\s+(\d+)\s+(\d+)', e)
    mn = re.search(r'Teste negativo\s+(\d+)\s+(\d+)', e)
    if not (mp and mn): return None
    return (int(mp.group(1)), int(mp.group(2)),
            int(mn.group(1)), int(mn.group(2)))

def v_sensibilidade(e):
    t = _tabela_2x2(e)
    if not t: return None
    vp, fp, fn, vn = t
    if "sensibilidade" in e.lower():   return round(vp / (vp + fn) * 100, 1)
    if "especificidade" in e.lower():  return round(vn / (vn + fp) * 100, 1)
    return None

def v_valor_preditivo(e):
    t = _tabela_2x2(e)
    if not t: return None
    vp, fp, fn, vn = t
    if "preditivo positivo" in e.lower() or "VPP" in e:
        return round(vp / (vp + fp) * 100, 1)
    if "preditivo negativo" in e.lower() or "VPN" in e:
        return round(vn / (vn + fn) * 100, 1)
    return None

def v_risco_relativo(e):
    me = re.search(r'Expostos\s+(\d+)\s+(\d+)', e)
    mn = re.search(r'Não expostos\s+(\d+)\s+(\d+)', e)
    if not (me and mn): return None
    ce, ne = int(me.group(1)), int(me.group(2))
    cn, nn = int(mn.group(1)), int(mn.group(2))
    if nn == 0 or cn == 0: return None
    re_, rn = ce / ne, cn / nn
    if "risco relativo" in e.lower():
        return round(re_ / rn, 2)
    if "atribuível" in e.lower() or "diferença absoluta" in e.lower():
        return round(abs(re_ - rn) * 100, 1)
    return None

def v_odds_ratio(e):
    me = re.search(r'Expostos\s+(\d+)\s+(\d+)', e)
    mn = re.search(r'Não expostos\s+(\d+)\s+(\d+)', e)
    if not (me and mn) or "chances" not in e.lower() and "odds" not in e.lower():
        return None
    a, b = int(me.group(1)), int(me.group(2))
    c, d = int(mn.group(1)), int(mn.group(2))
    if b * c == 0: return None
    return round((a * d) / (b * c), 2)

def v_nnt(e):
    if "NNT" not in e and "necessário para tratar" not in e: return None
    mt = re.search(r'Grupo tratamento\s+(\d+)\s+(\d+)', e)
    mc = re.search(r'Grupo controle\s+(\d+)\s+(\d+)', e)
    if not (mt and mc): return None
    et, nt = int(mt.group(1)), int(mt.group(2))
    ec, nc = int(mc.group(1)), int(mc.group(2))
    rar = ec / nc - et / nt
    if rar <= 0: return None
    return ceil(1 / rar)



# ── Verificadores de REDES (recálculo pela biblioteca ipaddress) ──

def v_hosts_validos(e):
    if not re.search(r'atribuídos a hosts|utilizáveis por hosts|'
                     r'sub-rede comporta', e):
        return None
    m = re.search(r'([\d.]+/\d+)', e)
    if not m: return None
    return ipaddress.ip_network(m.group(1)).num_addresses - 2

def v_mascara(e):
    m = re.search(r'([\d.]+/\d+)', e)
    if not m: return None
    rede = ipaddress.ip_network(m.group(1))
    if "wildcard" in e or "curinga" in e:
        return str(ipaddress.ip_address(
            int(ipaddress.ip_address("255.255.255.255")) - int(rede.netmask)))
    if "máscara" in e:
        return str(rede.netmask)
    return None

def v_rede_broadcast(e):
    mi = re.search(r'endereço (?:de origem )?(\d+\.\d+\.\d+\.\d+)', e) or \
         re.search(r'estação (\d+\.\d+\.\d+\.\d+)', e)
    mp = re.search(r'/(\d+)', e)
    if not (mi and mp): return None
    rede = ipaddress.ip_network(f"{mi.group(1)}/{mp.group(1)}", strict=False)
    if "broadcast" in e:
        return str(rede.broadcast_address)
    if "endereço de rede" in e:
        return str(rede.network_address)
    return None

def v_divisao_subredes(e):
    if "sub-redes" not in e or "Quantas" not in e and "número de sub-redes" not in e \
       and "blocos" not in e:
        return None
    prefixos = [int(x) for x in re.findall(r'/(\d+)', e)]
    if len(prefixos) < 2: return None
    return 2 ** (prefixos[-1] - prefixos[0])

def v_vlsm(e):
    m = re.search(r'(\d+) (?:hosts|dispositivos|equipamentos|estações)', e)
    if not m or "prefixo" not in e and "bloco CIDR" not in e:
        return None
    h = int(m.group(1))
    p = 32
    while (2 ** (32 - p)) - 2 < h:
        p -= 1
    return f"/{p}"

def v_sumarizacao(e):
    if "sumariz" not in e.lower() and "agregar" not in e:
        return None
    redes = re.findall(r'(\d+\.\d+\.\d+\.\d+/\d+)', e)
    if len(redes) < 2: return None
    try:
        colapsadas = list(ipaddress.collapse_addresses(
            [ipaddress.ip_network(r) for r in redes]))
    except (ValueError, TypeError):
        return None
    return str(colapsadas[0]) if len(colapsadas) == 1 else None

def v_ipv6_bits(e):
    if "bits" not in e or "IPv6" not in e: return None
    m = re.search(r'/(\d+)', e)
    return 128 - int(m.group(1)) if m else None

def v_tempo_transmissao(e):
    mt = re.search(r'(\d+) MB', e)
    mr = re.search(r'(\d+) Mbps', e)
    if not (mt and mr): return None
    return round(int(mt.group(1)) * 8 / int(mr.group(1)), 1)

def v_eficiencia(e):
    if "eficiência" not in e.lower() and "dados úteis" not in e:
        return None
    mp = re.search(r'(\d+) bytes de (?:dados úteis|payload)', e)
    mo = re.search(r'(?:somam |acrescidos de )(\d+) bytes', e)
    if not (mp and mo): return None
    p, o = int(mp.group(1)), int(mo.group(1))
    return round(p / (p + o) * 100, 1)

def v_fragmentacao(e):
    if "fragmento" not in e: return None
    md = re.search(r'de (\d+) bytes', e)
    mm = re.search(r'MTU de (\d+) bytes', e)
    if not (md and mm): return None
    dg, mtu = int(md.group(1)), int(mm.group(1))
    payload_max = ((mtu - 20) // 8) * 8
    return -(-(dg - 20) // payload_max)


# ── Verificadores de DIREITO ──
# As tabelas abaixo são ESCRITAS SEPARADAMENTE do gerador, a partir dos
# dispositivos legais. Se gerador e teste divergirem, um dos dois errou.

PRAZOS_CPC_REF = {
    "apelação": 15, "agravo de instrumento": 15, "agravo interno": 15,
    "recurso especial": 15, "recurso extraordinário": 15,
    "recurso ordinário": 15, "embargos de divergência": 15,
    "embargos de declaração": 5, "contestação": 15,
    "réplica (impugnação à contestação)": 15,
    "contrarrazões de apelação": 15,
    "pagamento voluntário no cumprimento de sentença": 15,
    "impugnação ao cumprimento de sentença": 15,
    "embargos à execução": 15,
}

PRESCRICAO_REF = {
    "reparação civil extracontratual": 3,
    "aluguéis de prédios urbanos": 3,
    "enriquecimento sem causa": 3,
    "juros e dividendos": 3,
    "relativa à tutela": 4,
    "dívida líquida constante de instrumento": 5,
    "profissionais liberais quanto a honorários": 5,
    "vencedor para haver o que despendeu": 5,
    "prestações alimentares": 2,
    "segurado contra o segurador": 1,
    "inadimplemento contratual": 10,
    "sem prazo específico": 10,
}

PRAZOS_CPP_REF = {
    "apelação no processo penal": 5,
    "recurso em sentido estrito": 5,
    "embargos de declaração no processo penal": 2,
    "razões de apelação": 8,
    "resposta à acusação": 10,
}

PRAZOS_CLT_REF = {
    "recurso ordinário trabalhista": 8,
    "agravo de petição": 8,
    "recurso de revista": 8,
    "embargos de declaração na Justiça do Trabalho": 5,
}


def v_prazo_cpc(e):
    if "dias úteis" not in e or "dobro" in e or "Fazenda" in e or \
       "Ministério Público" in e or "Defensoria" in e or "litisconsortes" in e:
        return None
    if "CPP" in e or "penal" in e or "CLT" in e or "trabalh" in e:
        return None
    # o ato mais específico primeiro (evita "apelação" casar em "contrarrazões
    # de apelação")
    for ato in sorted(PRAZOS_CPC_REF, key=len, reverse=True):
        if ato in e:
            return PRAZOS_CPC_REF[ato]
    return None

def v_prazo_dobro(e):
    if not re.search(r'Fazenda Pública|Ministério Público|Defensoria Pública|'
                     r'litisconsortes', e):
        return None
    for ato in sorted(PRAZOS_CPC_REF, key=len, reverse=True):
        if ato in e:
            return PRAZOS_CPC_REF[ato] * 2
    return None

def v_contagem_prazo(e):
    from datetime import date as _date, timedelta as _td
    mb = re.search(r'(\d{2})/(\d{2})/(\d{4})', e)
    mp = re.search(r'prazo é de (\d+) dias úteis', e)
    if not (mb and mp): return None
    base = _date(int(mb.group(3)), int(mb.group(2)), int(mb.group(1)))
    prazo = int(mp.group(1))
    contados, atual = 0, base
    while contados < prazo:
        atual += _td(days=1)
        if atual.weekday() < 5:
            contados += 1
    return atual.strftime("%d/%m/%Y")

def v_prescricao(e):
    if "prescricional" not in e and "prescreve" not in e:
        return None
    if "termo final" in e or "até que data" in e:
        return None       # tratado por v_calculo_prescricao
    for chave in sorted(PRESCRICAO_REF, key=len, reverse=True):
        if chave in e:
            return PRESCRICAO_REF[chave]
    return None

def v_calculo_prescricao(e):
    from datetime import date as _date
    if "termo final" not in e and "até que data" not in e:
        return None
    mb = re.search(r'(\d{2})/(\d{2})/(\d{4})', e)
    if not mb: return None
    prazo = None
    for chave in sorted(PRESCRICAO_REF, key=len, reverse=True):
        if chave in e:
            prazo = PRESCRICAO_REF[chave]
            break
    if prazo is None: return None
    d, m, a = int(mb.group(1)), int(mb.group(2)), int(mb.group(3))
    return _date(a + prazo, m, d).strftime("%d/%m/%Y")

def v_capacidade(e):
    m = re.search(r'(\d+) anos', e)
    if not m or "capacidade" not in e.lower(): return None
    idade = int(m.group(1))
    if idade < 16:  return "absolutamente incapaz"
    if idade < 18:  return "relativamente incapaz"
    return "plenamente capaz"

def v_prazo_penal(e):
    if "CPP" not in e and "processo penal" not in e and "criminal" not in e:
        return None
    for ato in sorted(PRAZOS_CPP_REF, key=len, reverse=True):
        if ato in e:
            return PRAZOS_CPP_REF[ato]
    return None

def v_prazo_trabalhista(e):
    if "CLT" not in e and "trabalh" not in e.lower():
        return None
    for ato in sorted(PRAZOS_CLT_REF, key=len, reverse=True):
        if ato in e:
            return PRAZOS_CLT_REF[ato]
    return None

def v_honorarios(e):
    if "honorários" not in e.lower(): return None
    mv = re.search(r'R\$ ([\d.]+),00', e)
    mp = re.search(r'(\d+)%', e)
    if not (mv and mp): return None
    return round(int(mv.group(1).replace(".", "")) * int(mp.group(1)) / 100, 2)



# ── Verificadores de REDES (recálculo pela biblioteca ipaddress) ──

def v_hosts_validos(e):
    if not re.search(r'atribuídos a hosts|utilizáveis por hosts|'
                     r'sub-rede comporta', e):
        return None
    m = re.search(r'([\d.]+/\d+)', e)
    if not m: return None
    return ipaddress.ip_network(m.group(1)).num_addresses - 2

def v_vlsm(e):
    if "prefixo" not in e or "menor" not in e and "econômico" not in e:
        return None
    m = re.search(r'(\d+) (?:hosts|dispositivos|equipamentos|estações)', e)
    if not m: return None
    h = int(m.group(1))
    p = 32
    while (2 ** (32 - p)) - 2 < h:
        p -= 1
    return f"/{p}"

def v_divisao_subredes(e):
    if "sub-redes" not in e and "blocos" not in e:
        return None
    prefixos = re.findall(r'/(\d+)', e)
    if len(prefixos) < 2: return None
    p_orig, p_novo = int(prefixos[0]), int(prefixos[-1])
    if p_novo <= p_orig: return None
    return 2 ** (p_novo - p_orig)

def v_sumarizacao(e):
    if "sumariz" not in e.lower() and "agregar" not in e:
        return None
    redes = re.findall(r'(\d+\.\d+\.\d+\.\d+/\d+)', e)
    if len(redes) < 2: return None
    try:
        col = list(ipaddress.collapse_addresses(
            [ipaddress.ip_network(r) for r in redes]))
    except (ValueError, TypeError):
        return None
    return str(col[0]) if len(col) == 1 else None

def v_fragmentacao(e):
    if "fragmento" not in e: return None
    md = re.search(r'de (\d+) bytes', e)
    mm = re.search(r'MTU de (\d+) bytes', e)
    if not (md and mm): return None
    dg, mtu = int(md.group(1)), int(mm.group(1))
    payload_max = ((mtu - 20) // 8) * 8
    if payload_max <= 0: return None
    return -(-(dg - 20) // payload_max)

def v_tempo_transmissao(e):
    if "tempo de transmissão" not in e and "tempo de transferência" not in e:
        return None
    mt = re.search(r'(\d+) MB', e)
    mr = re.search(r'(\d+) Mbps', e)
    if not (mt and mr): return None
    return round(int(mt.group(1)) * 8 / int(mr.group(1)), 1)

def v_eficiencia(e):
    if "eficiência" not in e and "dados úteis" not in e: return None
    mp = re.search(r'(\d+) bytes de (?:dados úteis|payload)', e)
    mo = re.search(r'(\d+) bytes de cabeçalhos|somam (\d+) bytes', e)
    if not (mp and mo): return None
    payload = int(mp.group(1))
    over = int(mo.group(1) or mo.group(2))
    return round(payload / (payload + over) * 100, 1)

def v_mascara(e):
    if "máscara de sub-rede" not in e: return None
    m = re.search(r'([\d.]+/\d+)', e)
    return str(ipaddress.ip_network(m.group(1)).netmask) if m else None


# ── Verificadores de DIREITO (tabela de referência independente) ──

_PRAZOS_CPC = {
    "apelação": 15, "agravo de instrumento": 15, "agravo interno": 15,
    "recurso especial": 15, "recurso extraordinário": 15,
    "recurso ordinário": 15, "embargos de divergência": 15,
    "embargos de declaração": 5, "contestação": 15,
    "réplica (impugnação à contestação)": 15,
    "contrarrazões de apelação": 15,
    "pagamento voluntário no cumprimento de sentença": 15,
    "impugnação ao cumprimento de sentença": 15,
    "embargos à execução": 15,
}

_PRESCRICAO_CC = [
    ("reparação civil extracontratual", 3), ("aluguéis de prédios urbanos", 3),
    ("enriquecimento sem causa", 3), ("juros e dividendos", 3),
    ("relativa à tutela", 4), ("dívida líquida constante de instrumento", 5),
    ("profissionais liberais quanto a honorários", 5),
    ("vencedor para haver o que despendeu", 5),
    ("prestações alimentares", 2), ("segurado contra o segurador", 1),
    ("inadimplemento contratual", 10), ("sem prazo específico", 10),
]

def v_prazo_cpc(e):
    """Prazo simples do CPC. Não se aplica quando há prazo em dobro."""
    if "dias úteis" not in e or "dobro" in e: return None
    if "CPP" in e or "CLT" in e or "trabalh" in e or "penal" in e: return None
    # Sujeitos com prerrogativa de prazo em dobro têm verificador próprio
    if re.search(r'Fazenda Pública|Ministério Público|Defensoria Pública|'
                 r'litisconsortes', e):
        return None
    for ato, prazo in sorted(_PRAZOS_CPC.items(), key=lambda x: -len(x[0])):
        if ato in e:
            return prazo
    return None

def v_prazo_dobro(e):
    if "dobro" not in e and not re.search(
            r'Fazenda Pública|Ministério Público|Defensoria Pública|'
            r'litisconsortes com procuradores diferentes', e):
        return None
    for ato, prazo in sorted(_PRAZOS_CPC.items(), key=lambda x: -len(x[0])):
        if ato in e:
            return prazo * 2
    return None

def v_prescricao(e):
    if "prescricional" not in e or "termo final" in e: return None
    for chave, prazo in sorted(_PRESCRICAO_CC, key=lambda x: -len(x[0])):
        if chave in e:
            return prazo
    return None

def v_contagem_prazo(e):
    if "dias úteis" not in e or "último dia" not in e and "data final" not in e:
        return None
    from datetime import date as _date, timedelta as _td
    mb = re.search(r'em (\d{2}/\d{2}/\d{4})', e)
    mp = re.search(r'prazo é de (\d+) dias úteis', e)
    if not (mb and mp): return None
    d, m, a = map(int, mb.group(1).split("/"))
    base, prazo = _date(a, m, d), int(mp.group(1))
    cont, atual = 0, base
    while cont < prazo:
        atual += _td(days=1)
        if atual.weekday() < 5:
            cont += 1
    return atual.strftime("%d/%m/%Y")

def v_capacidade(e):
    if "capacidade civil" not in e and "capaz" not in e: return None
    m = re.search(r'(\d+) anos', e)
    if not m: return None
    idade = int(m.group(1))
    if idade < 16:  return "absolutamente incapaz"
    if idade < 18:  return "relativamente incapaz"
    return "plenamente capaz"

def v_honorarios(e):
    if "honorários" not in e: return None
    mv = re.search(r'R\$ ([\d.]+),00', e)
    mp = re.search(r'(\d+)%', e)
    if not (mv and mp): return None
    return round(int(mv.group(1).replace(".", "")) * int(mp.group(1)) / 100, 2)



# ── Verificadores dos templates de RACIOCÍNIO (direito) ──

def v_efeito_recurso(e):
    """
    Embargos de declaração INTERROMPEM: o prazo recomeça integral da
    publicação da decisão dos embargos, desprezando o tempo decorrido.
    """
    if "embargos de declaração" not in e or "apelação" not in e:
        return None
    from datetime import date as _d, timedelta as _t
    m = re.search(r'publicada em (\d{2}/\d{2}/\d{4})', e)
    if not m: return None
    d, mm, a = map(int, m.group(1).split("/"))
    julg = _d(a, mm, d)
    cont, fim = 0, julg
    while cont < 15:
        fim += _t(days=1)
        if fim.weekday() < 5:
            cont += 1
    return fim.strftime("%d/%m/%Y")

def v_competencia_valor(e):
    if "Juizado" not in e and "competente" not in e: return None
    mv = re.search(r'(?:causa de|valor de) R\$ ([\d.]+),00', e)
    ms = re.search(r'salário mínimo de R\$ ([\d.]+),00', e)
    if not (mv and ms): return None
    valor = int(mv.group(1).replace(".", ""))
    teto = 40 * int(ms.group(1).replace(".", ""))
    return ("Justiça Comum estadual, por exceder o teto do Juizado Especial"
            if valor > teto else
            "Juizado Especial Cível, por estar dentro do teto de 40 salários mínimos")


VERIFICADORES = [
    ("pilha (estrutura LIFO)", v_pilha),
    ("fila (estrutura FIFO)",  v_fila),
    ("árvore binária de busca", v_arvore),
    ("tabela-verdade",         v_logica),
    ("sub-rede",               v_redes),
    ("funcionarios",           v_sql),
    ("grafo",                  v_grafos),
    ("base 2",                 v_bases),
    ("base 16",                v_bases),
    ("Bubble Sort",            v_bubble),
    ("contador += 1",          v_contagem),
    ("mesa circular",          v_circular),
    ("roda de conversa",       v_circular),
    ("triângulo de Pascal",    v_pascal),
    ("subconjuntos",           v_pascal),
    ("dado",                   v_dados),
    ("moeda honesta",          v_binomial),
    ("pódio",                  v_podio),
    ("três primeiros lugares", v_podio),
    # ── Eng. Software e Ciência da Computação ──
    ("Pontos de Função",       v_pontos_funcao),
    ("PF não ajustados",       v_pontos_funcao),
    ("ciclomática",            v_ciclomatica),
    ("caminhos de execução",   v_caminhos),
    ("cobertura de linhas",    v_cobertura),
    ("velocidade média",       v_velocidade),
    ("sprints",                v_sprints),
    ("homens-hora",            v_esforco),
    ("k mod",                  v_hash_posicao),
    ("tempo médio de acesso",  v_tempo_medio),   # antes de hit_rate/bits
    ("taxa de acerto",         v_hit_rate),
    ("hit rate",               v_hit_rate),
    ("bits",                   v_enderecamento),
    # ── Saúde ──
    ("gotas por minuto",       v_gotejamento),
    ("microgotas por minuto",  v_gotejamento),
    ("tempo total de infusão", v_tempo_infusao),
    ("horas a infusão",        v_tempo_infusao),
    ("aspirado",               v_diluicao),
    ("mg/kg",                  v_dose_peso),
    ("prevalência",            v_prevalencia),
    ("incidência",             v_incidencia),
    ("sensibilidade",          v_sensibilidade),
    ("especificidade",         v_sensibilidade),
    ("preditivo",              v_valor_preditivo),
    ("risco relativo",         v_risco_relativo),
    ("atribuível",             v_risco_relativo),
    ("razão de chances",       v_odds_ratio),
    ("odds ratio",             v_odds_ratio),
    ("necessário para tratar", v_nnt),
    # ── Redes ──
    ("atribuídos a hosts",     v_hosts_validos),
    ("sub-rede comporta",      v_hosts_validos),
    ("utilizáveis por hosts",  v_hosts_validos),
    ("curinga",                v_mascara),
    ("máscara de sub-rede",    v_mascara),
    ("broadcast",              v_rede_broadcast),
    ("endereço de rede",       v_rede_broadcast),
    ("sub-redes serão obtidas", v_divisao_subredes),
    ("número de sub-redes",    v_divisao_subredes),
    ("blocos /",               v_divisao_subredes),
    ("menor prefixo",          v_vlsm),
    ("mais econômico",         v_vlsm),
    ("bloco CIDR suficiente",  v_vlsm),
    ("sumariza",               v_sumarizacao),
    ("rota sumarizada",        v_sumarizacao),
    ("bits restam",            v_ipv6_bits),
    ("bits disponíveis",       v_ipv6_bits),
    ("tempo de transmissão",   v_tempo_transmissao),
    ("tempo de transferência", v_tempo_transmissao),
    ("eficiência",             v_eficiencia),
    ("dados úteis no total",   v_eficiencia),
    ("fragmentos",             v_fragmentacao),
    # ── Direito ──
    ("goza de prazo em dobro", v_prazo_dobro),
    ("Fazenda Pública",        v_prazo_dobro),
    ("Ministério Público",     v_prazo_dobro),
    ("Defensoria Pública",     v_prazo_dobro),
    ("último dia para a prática", v_contagem_prazo),
    ("qual é a data final",    v_contagem_prazo),
    ("termo final do prazo",   v_calculo_prescricao),
    ("até que data",           v_calculo_prescricao),
    ("prazo prescricional",    v_prescricao),
    ("capacidade civil",       v_capacidade),
    ("processo penal",         v_prazo_penal),
    ("CPP",                    v_prazo_penal),
    ("CLT",                    v_prazo_trabalhista),
    ("Justiça do Trabalho",    v_prazo_trabalhista),
    ("honorários",             v_honorarios),
    ("interpor apelação",      v_efeito_recurso),
    ("órgão competente",       v_competencia_valor),
    ("competência é da",       v_competencia_valor),
    ("juízo competente",       v_competencia_valor),
    ("dias úteis",             v_prazo_cpc),
]


def testar(questoes):
    """
    Compara o gabarito com um recálculo INDEPENDENTE.

    Usa os metadados da questão (tipo_resposta / resposta_bruta) para saber
    COMO comparar, em vez de inferir do texto. Antes dessa mudança, uma
    resposta simbólica como "O(log n)" era tratada como número e acusada
    por engano.
    """
    erros, checados = [], Counter()
    for q in questoes:
        e    = q["enunciado"]
        gab  = q["alternativas"][q["gabarito"]]
        tipo = q.get("tipo_resposta", "numerica")

        for marcador, fn in VERIFICADORES:
            if marcador not in e:
                continue
            try:
                esperado = fn(e)
            except Exception:
                esperado = None
            if esperado is None:
                continue

            checados[marcador] += 1

            # A comparação segue o TIPO declarado pela própria questão
            if tipo in ("simbolica", "textual", "sequencia",
                        "endereco_ip", "codigo_numerico"):
                ok = str(gab).strip() == str(esperado).strip()
            elif isinstance(esperado, str) and not re.fullmatch(r'[\d.,%\s]+', esperado):
                ok = str(gab).strip() == esperado.strip()
            else:
                v = _valor(gab)
                ok = v is not None and abs(v - float(esperado)) < 1e-6

            if not ok:
                erros.append((q["topico"], esperado, gab, e[:90]))
            break

    return checados, erros


def testar_distratores_impossiveis(questoes):
    """
    Detecta alternativas que nenhum aluno consideraria.

    Grandezas de saúde e de rede (risco, dose, volume, quantidade de
    hosts, prazo) são positivas por natureza. Um distrator negativo não
    exerce função pedagógica — só denuncia erro no cálculo do distrator.

    A regra NÃO vale para grandezas abstratas. Uma progressão de razão
    negativa tem termos negativos por definição — "1000, 800, 600, …,
    −200" é uma PA legítima e cobrada no ENEM —, e o mesmo vale para
    raízes de equação e variações de temperatura. Nesses tópicos o
    número negativo é conteúdo, não defeito.
    """
    ABSTRATOS = re.compile(
        r"progress[ãa]o|equa[çc][ãa]o|ra[íi]z|temperatura|varia[çc][ãa]o|"
        r"saldo|coordenada|n[úu]mero inteiro|fun[çc][ãa]o",
        re.IGNORECASE)
    problemas = []
    for q in questoes:
        if q.get("tipo_resposta") not in ("numerica", "percentual",
                                          "fracao", "monetaria"):
            continue
        if ABSTRATOS.search(str(q.get("topico", ""))):
            continue
        for letra, txt in q["alternativas"].items():
            s = str(txt).strip()
            if s.startswith("-") or s.startswith("R$ -"):
                problemas.append((q["topico"],
                                  f"alternativa {letra} negativa: '{s}'", ""))
                break
    return problemas


def testar_plausibilidade_clinica(questoes):
    """
    Confere se os cenários de infusão são clinicamente verossímeis.

    O gabarito pode estar aritmeticamente correto e ainda assim descrever
    uma situação que um profissional estranharia — 250 mL correndo em 12
    horas, por exemplo. Isso não invalida a conta, mas prejudica a questão
    como instrumento de avaliação.
    """
    problemas = []
    for q in questoes:
        e = q["enunciado"]
        if "gotejamento" not in e.lower() and "infusão" not in e.lower():
            continue
        mv = re.search(r'(\d+) mL', e)
        mh = re.search(r'(\d+) horas', e)
        mg = re.search(r'(\d+) gotas por minuto', e)

        horas = None
        if mv and mh:
            volume, horas = int(mv.group(1)), int(mh.group(1))
        elif mv and mg:
            volume = int(mv.group(1))
            horas = volume / (int(mg.group(1)) * 3)

        if horas and horas > 0:
            vazao = volume / horas
            if vazao < 50:
                problemas.append((q["topico"],
                                  f"vazão de {vazao:.0f} mL/h é baixa demais "
                                  f"({volume} mL em {horas:.1f} h)", ""))
            elif vazao > 1200:
                problemas.append((q["topico"],
                                  f"vazão de {vazao:.0f} mL/h é alta demais", ""))
    return problemas


def testar_coerencia_metadado(questoes):
    """
    Confere que o metadado BATE com o conteúdo real das alternativas.
    Um metadado errado é pior que nenhum: os outros testes confiam nele.
    """
    problemas = []
    for q in questoes:
        tipo = q.get("tipo_resposta")
        alts = list(q["alternativas"].values())
        if tipo is None:
            problemas.append((q["topico"], "sem tipo_resposta declarado", ""))
            continue

        amostra = str(alts[0])
        if tipo == "numerica":
            # O sinal faz parte do número: uma PA de razão negativa
            # devolve "-48", que é tão numérico quanto "48".
            if not re.fullmatch(r'-?[\d.,]+', amostra):
                problemas.append((q["topico"], f"tipo=numerica mas alt='{amostra}'", ""))
        elif tipo == "fracao":
            if not re.fullmatch(r'-?\d+(/\d+)?', amostra):
                problemas.append((q["topico"], f"tipo=fracao mas alt='{amostra}'", ""))
        elif tipo == "monetaria":
            if not re.fullmatch(r'R\$\s*[\d.]+,\d{2}', amostra):
                problemas.append((q["topico"], f"tipo=monetaria mas alt='{amostra}'", ""))
        elif tipo == "percentual":
            if "%" not in amostra:
                problemas.append((q["topico"], f"tipo=percentual mas alt='{amostra}'", ""))
        elif tipo == "endereco_ip":
            if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', amostra):
                problemas.append((q["topico"], f"tipo=endereco_ip mas alt='{amostra}'", ""))
        elif tipo == "sequencia":
            if "," not in amostra:
                problemas.append((q["topico"], f"tipo=sequencia mas alt='{amostra}'", ""))
        elif tipo == "simbolica":
            if re.fullmatch(r'[\d.,]+', amostra):
                problemas.append((q["topico"], f"tipo=simbolica mas alt numérica '{amostra}'", ""))
        elif tipo == "codigo_numerico":
            # dígitos/hex sem separador de milhar (não é quantidade)
            if not re.fullmatch(r'[0-9A-Fa-f]+', amostra):
                problemas.append((q["topico"], f"tipo=codigo_numerico mas alt='{amostra}'", ""))
        # textual: qualquer prosa curta serve

        # resposta_bruta deve existir e corresponder ao gabarito
        if "resposta_bruta" not in q:
            problemas.append((q["topico"], "sem resposta_bruta", ""))
    return problemas


if __name__ == "__main__":
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    import gerador_ads, gerador_procedural

    print("═" * 62)
    print("  TESTE 1 — GABARITO (recálculo independente)")
    print("═" * 62)

    total_err = 0
    for nome, mod in [("ADS", gerador_ads), ("Matemática", gerador_procedural)]:
        lote = mod.gerar_lote(qtd, seed=31337)
        checados, erros = testar(lote)
        probs_meta = testar_coerencia_metadado(lote)
        probs_clin = testar_plausibilidade_clinica(lote)
        probs_neg  = testar_distratores_impossiveis(lote)
        total_err += (len(erros) + len(probs_meta) + len(probs_clin)
                      + len(probs_neg))
        print(f"\n  ── {nome}: {sum(checados.values())} de {qtd} verificáveis ──")
        for marc, n in checados.most_common():
            print(f"     {marc:<26} {n:>4}")
        if erros:
            print(f"\n     ❌ {len(erros)} DIVERGÊNCIA(S):")
            for topico, esp, obt, trecho in erros[:5]:
                print(f"        [{topico}] esperado={esp} gabarito={obt}")
                print(f"          {trecho}...")
        else:
            print(f"     ✅ Nenhuma divergência")

        if probs_meta:
            print(f"\n     ❌ {len(probs_meta)} METADADO(S) INCOERENTE(S):")
            vistos = set()
            for topico, det, _ in probs_meta:
                if topico in vistos: continue
                vistos.add(topico)
                print(f"        [{topico}] {det}")
                if len(vistos) >= 4: break
        else:
            print(f"     ✅ Metadados coerentes com as alternativas")

        if probs_clin:
            print(f"\n     ❌ {len(probs_clin)} CENÁRIO(S) CLINICAMENTE IMPLAUSÍVEL(IS):")
            for topico, det, _ in probs_clin[:3]:
                print(f"        [{topico}] {det}")

        if probs_neg:
            print(f"\n     ❌ {len(probs_neg)} DISTRATOR(ES) IMPOSSÍVEL(IS):")
            for topico, det, _ in probs_neg[:3]:
                print(f"        [{topico}] {det}")

    print("\n" + "═" * 62)
    print(f"  {'🎉 TESTE 1 PASSOU' if total_err == 0 else f'❌ {total_err} ERRO(S)'}")
    print("═" * 62)
    sys.exit(1 if total_err else 0)
