"""
=============================================================
  NIVELIS — Gerador Procedural: Redes de Computadores
  Foco: ENADE, concursos de TI, certificações
=============================================================

  Gera questões SEM IA. Todo cálculo usa a biblioteca padrão
  `ipaddress`, que implementa as RFCs — o gabarito é o que a
  própria especificação define.

  O gerador_ads já tinha 1 template de sub-rede. Este módulo
  amplia para 12, cobrindo endereçamento, VLSM, IPv6,
  desempenho e camadas.

  12 TEMPLATES:

  ENDEREÇAMENTO IPv4
    1. Hosts válidos por prefixo
    2. Máscara e wildcard
    3. Endereço de rede e broadcast
    4. Classe e tipo do endereço (público/privado)
    5. Pertencimento de host a uma rede
  SUB-REDES
    6. Divisão em sub-redes (quantas e de que tamanho)
    7. VLSM — menor prefixo que comporta N hosts
    8. Sumarização de rotas (supernetting)
  IPv6
    9. Compressão e expansão de endereço
  DESEMPENHO
   10. Tempo de transmissão e vazão
   11. Sobrecarga de cabeçalho (eficiência)
  ENCAPSULAMENTO
   12. Fragmentação e MTU

  USO:
    python gerador_redes.py            # 12 questões
    python gerador_redes.py 20 subredes
=============================================================
"""

import sys
import re
import random
import ipaddress

import equilibrio_numerico as _EQ

LETRAS = ["A", "B", "C", "D", "E"]

TIPOS_RESPOSTA = {
    "numerica", "fracao", "simbolica", "codigo_numerico",
    "sequencia", "textual", "endereco_ip", "percentual", "monetaria",
}


def _fmt(v) -> str:
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return str(v)


def _fmt_dec(v, casas=2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def _plural(n, singular, plural=None):
    if plural is None:
        plural = singular + "s"
    return singular if abs(n) == 1 else plural


def _juntar(anterior: str, seguinte: str) -> str:
    if not seguinte:
        return seguinte
    if anterior.rstrip().endswith((".", "!", "?", ":")):
        return seguinte[0].upper() + seguinte[1:]
    return seguinte[0].lower() + seguinte[1:]


def _montar(enunciado, correta, distratores, explicacao, topico, rng,
            formatador=_fmt, tipo_resposta="numerica"):
    assert tipo_resposta in TIPOS_RESPOSTA
    unicos = []
    for d in distratores:
        if d != correta and d not in unicos:
            unicos.append(d)
    if len(unicos) < 4:
        return None
    # A POSIÇÃO da resposta certa é sorteada, não deixada ao acaso da
    # ordem em que o template escreveu os distratores. Sem isto, o
    # valor certo cai no meio das cinco questão após questão — ver
    # equilibrio_numerico.py.
    unicos = _EQ.escolher(correta, unicos, rng,
                          chave=lambda d: _EQ.valor_de(formatador(d)))
    valores = [correta] + unicos[:4]
    rng.shuffle(valores)
    return {
        "enunciado":      enunciado,
        "alternativas":   {L: formatador(v) for L, v in zip(LETRAS, valores)},
        "gabarito":       LETRAS[valores.index(correta)],
        "explicacao":     explicacao,
        "topico":         topico,
        "origem":         "gerador_redes",
        "tipo_resposta":  tipo_resposta,
        "resposta_bruta": correta,
    }


def _rede_aleatoria(rng, prefixos=None):
    """Sorteia uma rede IPv4 privada com prefixo dentro da faixa dada."""
    prefixo = rng.choice(prefixos or [22, 23, 24, 25, 26, 27, 28, 29, 30])
    base = rng.choice([
        f"192.168.{rng.randint(0, 254)}.0",
        f"10.{rng.randint(0, 254)}.{rng.randint(0, 254)}.0",
        f"172.{rng.randint(16, 31)}.{rng.randint(0, 254)}.0",
    ])
    return ipaddress.ip_network(f"{base}/{prefixo}", strict=False)


CENARIOS_REDE = [
    "Um administrador configurou a sub-rede {rede} em um roteador.",
    "O plano de endereçamento de uma filial reservou o bloco {rede}.",
    "Durante a segmentação de uma rede corporativa, definiu-se o bloco {rede}.",
    "Um data center alocou o intervalo {rede} para um novo ambiente.",
    "A documentação de infraestrutura registra a sub-rede {rede}.",
    "Em um laboratório de redes, os alunos analisam o bloco {rede}.",
    "A equipe de infraestrutura recebeu o bloco {rede} para uso interno.",
]

LIGACOES = ["Nessas condições,", "Diante disso,", "A partir dessa informação,",
            "Considerando esse endereçamento,", "Com base nesse bloco,"]


# ══════════════════════════════════════════
#  ENDEREÇAMENTO IPv4
# ══════════════════════════════════════════

def gerar_hosts_validos(rng):
    """Quantos hosts podem ser endereçados numa sub-rede."""
    for _ in range(50):
        rede = _rede_aleatoria(rng, [22, 23, 24, 25, 26, 27, 28, 29])
        correta = rede.num_addresses - 2

        distratores = [rede.num_addresses, rede.num_addresses - 1,
                       correta // 2, correta * 2, rede.prefixlen,
                       correta // 4, correta * 4,
                       max(1, correta - 2)]

        cen = rng.choice(CENARIOS_REDE).format(rede=rede)
        lig = rng.choice(LIGACOES)
        PERGUNTAS = [
            "quantos endereços podem ser atribuídos a hosts?",
            "qual é a quantidade de endereços utilizáveis por hosts?",
            "determine quantos hosts a sub-rede comporta.",
        ]
        enunciado = f"{cen} {_juntar(cen, lig)} {_juntar(lig, rng.choice(PERGUNTAS))}"
        explicacao = (
            f"Um prefixo /{rede.prefixlen} reserva {32 - rede.prefixlen} bits "
            f"para host, totalizando {_fmt(rede.num_addresses)} endereços. "
            f"Descontando o de rede e o de broadcast, restam "
            f"{_fmt(correta)} endereços atribuíveis a hosts."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (endereçamento IPv4)", rng)
        if q:
            return q
    raise RuntimeError("hosts_validos")


def gerar_mascara_wildcard(rng):
    """Máscara de sub-rede ou máscara curinga (wildcard)."""
    for _ in range(50):
        rede = _rede_aleatoria(rng)
        pede_wildcard = rng.random() < 0.4

        mascara = rede.netmask
        wildcard = ipaddress.ip_address(
            int(ipaddress.ip_address("255.255.255.255")) - int(mascara))

        if pede_wildcard:
            correta = str(wildcard)
            PERGUNTAS = [
                "qual é a máscara curinga (wildcard) correspondente?",
                "determine a wildcard mask desse bloco.",
            ]
            explicacao = (
                f"A wildcard é o complemento da máscara de sub-rede. Para "
                f"/{rede.prefixlen}, a máscara é {mascara}; subtraindo de "
                f"255.255.255.255, obtém-se {correta}."
            )
            # Os distratores eram MÁSCARAS ("255.255.255.248", 15
            # caracteres) enquanto a wildcard certa tem 7. Marcar a mais
            # curta acertava 100% das questões de wildcard.
            #
            # Agora três distratores são outras wildcards, do mesmo
            # porte, e só um é a máscara — que é justamente a confusão
            # que a questão quer pegar, mas sozinha não desequilibra a
            # média de comprimento.
            todos_uns = int(ipaddress.ip_address("255.255.255.255"))
            outras = [
                str(ipaddress.ip_address(
                    todos_uns
                    - int(ipaddress.ip_network(f"10.0.0.0/{p}").netmask)))
                for p in range(20, 31)
            ]
            outras = [o for o in outras if o != correta]
            rng.shuffle(outras)
            distratores = outras[:3] + [str(mascara)]
        else:
            correta = str(mascara)
            PERGUNTAS = [
                "qual é a máscara de sub-rede em notação decimal?",
                "determine a máscara correspondente ao prefixo.",
            ]
            explicacao = (
                f"O prefixo /{rede.prefixlen} indica {rede.prefixlen} bits em 1 "
                f"seguidos de {32 - rede.prefixlen} bits em 0, o que em notação "
                f"decimal pontuada corresponde a {correta}."
            )
            distratores = [str(ipaddress.ip_network(f"10.0.0.0/{p}").netmask)
                           for p in range(20, 31)
                           if str(ipaddress.ip_network(f"10.0.0.0/{p}").netmask) != correta]

        rng.shuffle(distratores)
        cen = rng.choice(CENARIOS_REDE).format(rede=rede)
        lig = rng.choice(LIGACOES)
        enunciado = f"{cen} {_juntar(cen, lig)} {_juntar(lig, rng.choice(PERGUNTAS))}"

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (máscaras)", rng, formatador=str,
                    tipo_resposta="endereco_ip")
        if q:
            return q
    raise RuntimeError("mascara_wildcard")


def gerar_rede_broadcast(rng):
    """Endereço de rede ou de broadcast, dado um IP com máscara."""
    for _ in range(50):
        prefixo = rng.choice([24, 25, 26, 27, 28, 29])
        octeto = rng.randint(1, 254)
        ip_str = f"192.168.{rng.randint(0,254)}.{octeto}"
        rede = ipaddress.ip_network(f"{ip_str}/{prefixo}", strict=False)

        pede_broadcast = rng.random() < 0.5
        correta = str(rede.broadcast_address) if pede_broadcast else str(rede.network_address)

        # Distratores: redes vizinhas e o próprio IP
        vizinhas = []
        for delta in (-2, -1, 1, 2):
            try:
                nova = ipaddress.ip_network(
                    f"{ipaddress.ip_address(int(rede.network_address) + delta * rede.num_addresses)}"
                    f"/{prefixo}", strict=False)
                vizinhas.append(str(nova.broadcast_address if pede_broadcast
                                    else nova.network_address))
            except (ValueError, ipaddress.AddressValueError):
                pass
        distratores = [ip_str] + vizinhas
        if pede_broadcast:
            distratores.append(str(rede.network_address))
        else:
            distratores.append(str(rede.broadcast_address))

        alvo = "broadcast" if pede_broadcast else "de rede"
        CEN = [
            f"Um host está configurado com o endereço {ip_str} e máscara "
            f"/{prefixo}.",
            f"Na análise de um pacote, identificou-se o IP de origem {ip_str} "
            f"em uma rede com prefixo /{prefixo}.",
            f"Um técnico documenta a estação {ip_str}, pertencente a uma "
            f"sub-rede /{prefixo}.",
        ]
        PER = [f"Qual é o endereço {alvo} da sub-rede a que ele pertence?",
               f"Determine o endereço {alvo} correspondente.",
               f"O endereço {alvo} dessa sub-rede é:"]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"

        if pede_broadcast:
            explicacao = (
                f"Com prefixo /{prefixo}, a sub-rede que contém {ip_str} é "
                f"{rede}. O endereço de broadcast é o último do bloco: "
                f"{correta}."
            )
        else:
            explicacao = (
                f"Aplicando a máscara /{prefixo} ao endereço {ip_str}, "
                f"obtém-se a sub-rede {rede}, cujo endereço de rede — o "
                f"primeiro do bloco — é {correta}."
            )

        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (endereçamento IPv4)", rng, formatador=str,
                    tipo_resposta="endereco_ip")
        if q:
            return q
    raise RuntimeError("rede_broadcast")


def gerar_tipo_endereco(rng):
    """Classifica o endereço: privado, público, loopback, APIPA, multicast."""
    CLASSES = [
        ("privado (RFC 1918)",    lambda: rng.choice([
            f"10.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
            f"172.{rng.randint(16,31)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
            f"192.168.{rng.randint(0,255)}.{rng.randint(1,254)}"])),
        ("público",               lambda: f"{rng.choice([8,20,50,64,200,201])}."
                                          f"{rng.randint(1,254)}.{rng.randint(0,255)}."
                                          f"{rng.randint(1,254)}"),
        ("de loopback",           lambda: f"127.{rng.randint(0,255)}."
                                          f"{rng.randint(0,255)}.{rng.randint(1,254)}"),
        ("de link-local (APIPA)", lambda: f"169.254.{rng.randint(0,255)}."
                                          f"{rng.randint(1,254)}"),
        ("de multicast",          lambda: f"{rng.randint(224,239)}."
                                          f"{rng.randint(0,255)}.{rng.randint(0,255)}."
                                          f"{rng.randint(1,254)}"),
    ]
    for _ in range(50):
        correta, gerador = rng.choice(CLASSES)
        ip = gerador()
        distratores = [c for c, _ in CLASSES if c != correta]
        distratores.append("de broadcast limitado")

        CEN = [
            f"Durante a análise de tráfego, identificou-se o endereço {ip}.",
            f"Um analista encontrou o IP {ip} na tabela de conexões.",
            f"A configuração de uma interface apresenta o endereço {ip}.",
            f"O log de um firewall registrou pacotes originados de {ip}.",
        ]
        PER = ["Esse endereço é classificado como:",
               "Qual é a classificação desse endereço?",
               "Trata-se de um endereço:"]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"

        FUNDAMENTOS = {
            "privado (RFC 1918)":    "as faixas 10.0.0.0/8, 172.16.0.0/12 e "
                                     "192.168.0.0/16 são reservadas para uso privado",
            "público":               "não pertence a nenhuma faixa reservada, sendo "
                                     "roteável na Internet",
            "de loopback":           "a faixa 127.0.0.0/8 é reservada para loopback",
            "de link-local (APIPA)": "a faixa 169.254.0.0/16 é usada na autoconfiguração "
                                     "quando não há servidor DHCP",
            "de multicast":          "a faixa 224.0.0.0/4 é destinada a multicast",
        }
        explicacao = (
            f"O endereço {ip} é {correta}, porque {FUNDAMENTOS[correta]}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (classificação de endereços)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("tipo_endereco")


def gerar_pertencimento(rng):
    """Verifica se um host pertence a determinada sub-rede."""
    for _ in range(60):
        rede = _rede_aleatoria(rng, [24, 25, 26, 27, 28])
        dentro = rng.random() < 0.5

        if dentro:
            offset = rng.randint(1, max(1, rede.num_addresses - 2))
            ip = ipaddress.ip_address(int(rede.network_address) + offset)
            correta = "Sim, o endereço pertence à sub-rede."
        else:
            # host de uma sub-rede vizinha
            salto = rng.choice([1, 2, 3]) * rede.num_addresses
            try:
                ip = ipaddress.ip_address(int(rede.network_address) + salto + 5)
            except ValueError:
                continue
            if ip in rede:
                continue
            correta = "Não, o endereço está fora da sub-rede."

        distratores = [
            "Sim, o endereço pertence à sub-rede." if not dentro
            else "Não, o endereço está fora da sub-rede.",
            "Não é possível determinar sem conhecer o gateway.",
            "Somente se a máscara for alterada para /24.",
            "Apenas se o roteamento estático estiver habilitado.",
        ]

        CEN = [
            f"Uma estação recebeu o endereço {ip} e o administrador precisa "
            f"confirmar se ela está na sub-rede {rede}.",
            f"Verifica-se se o host {ip} integra o bloco {rede}.",
            f"Um técnico investiga se o endereço {ip} pertence à rede {rede}.",
        ]
        PER = ["Qual é a conclusão correta?",
               "Assinale a afirmação correta.",
               "O que se pode concluir?"]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"A sub-rede {rede} abrange os endereços de "
            f"{rede.network_address} a {rede.broadcast_address}. Como {ip} "
            f"{'está' if dentro else 'não está'} nesse intervalo, "
            f"{'pertence' if dentro else 'não pertence'} à sub-rede."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (endereçamento IPv4)", rng,
                    formatador=str, tipo_resposta="textual")
        if q:
            return q
    raise RuntimeError("pertencimento")


# ══════════════════════════════════════════
#  SUB-REDES
# ══════════════════════════════════════════

def gerar_divisao_subredes(rng):
    """Quantas sub-redes cabem num bloco, dado o novo prefixo."""
    for _ in range(50):
        p_orig = rng.choice([16, 20, 22, 24])
        p_novo = p_orig + rng.choice([1, 2, 3, 4, 5, 6])
        if p_novo > 30:
            continue
        rede = _rede_aleatoria(rng, [p_orig])
        correta = 2 ** (p_novo - p_orig)

        # 2^(32-p_novo) é a quantidade de ENDEREÇOS por sub-rede, não de
        # sub-redes — com prefixos pequenos isso dava distratores milhares
        # de vezes maiores que o gabarito, descartáveis à primeira vista.
        candidatos = [
            2 ** (p_novo - p_orig + 1),      # contou um bit a mais
            2 ** (p_novo - p_orig - 1),      # contou um bit a menos
            p_novo - p_orig,                 # respondeu o nº de bits
            correta * 2 - 1,                 # esqueceu a sub-rede zero
            correta + 2,
            max(2, correta // 2),
            max(2, correta - 2),
            correta * 4,
            max(2, correta // 4),
        ]
        # Mantém só o que fica na mesma ordem de grandeza do gabarito
        distratores = [d for d in candidatos
                       if d > 0 and max(d, correta) / min(d, correta) <= 20]

        CEN = [
            f"O bloco {rede} precisa ser dividido em sub-redes de prefixo "
            f"/{p_novo}.",
            f"Uma empresa recebeu o bloco {rede} e pretende segmentá-lo em "
            f"sub-redes /{p_novo}.",
            f"Para isolar departamentos, o administrador dividirá {rede} em "
            f"blocos /{p_novo}.",
        ]
        PER = ["Quantas sub-redes serão obtidas?",
               "Determine o número de sub-redes resultantes.",
               "Quantos blocos /{p} podem ser formados?".format(p=p_novo)]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Ao passar de /{p_orig} para /{p_novo}, tomam-se emprestados "
            f"{p_novo - p_orig} bits da porção de host. Cada bit dobra a "
            f"quantidade de sub-redes: 2^{p_novo - p_orig} = "
            f"{_fmt(correta)} sub-redes."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (sub-redes)", rng)
        if q:
            return q
    raise RuntimeError("divisao_subredes")


def gerar_vlsm(rng):
    """Menor prefixo que comporta N hosts (VLSM)."""
    for _ in range(50):
        hosts = rng.choice([2, 5, 10, 12, 25, 30, 50, 60, 100, 120, 200, 250,
                            300, 500, 1000])
        # menor prefixo tal que 2^(32-p) - 2 >= hosts
        prefixo = 32
        while (2 ** (32 - prefixo)) - 2 < hosts:
            prefixo -= 1
        correta = f"/{prefixo}"

        distratores = [f"/{prefixo + 1}", f"/{prefixo - 1}",
                       f"/{prefixo + 2}", f"/{prefixo - 2}", "/24",
                       f"/{prefixo + 3}", "/30", "/16"]

        CEN = [
            f"Um departamento precisa endereçar {hosts} hosts.",
            f"O setor de engenharia terá {hosts} dispositivos conectados.",
            f"Uma VLAN comportará até {hosts} equipamentos.",
            f"O planejamento de endereçamento prevê {hosts} estações em um "
            f"segmento.",
        ]
        PER = [
            "Qual é o menor prefixo que atende à necessidade sem desperdício?",
            "Determine o prefixo mais econômico capaz de comportar todos.",
            "O menor bloco CIDR suficiente é:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Um prefixo /{prefixo} reserva {32 - prefixo} bits de host, "
            f"oferecendo 2^{32 - prefixo} − 2 = "
            f"{_fmt(2 ** (32 - prefixo) - 2)} endereços utilizáveis — "
            f"suficiente para {hosts}. Um /{prefixo + 1} ofereceria apenas "
            f"{_fmt(2 ** (31 - prefixo) - 2)}, insuficiente."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (VLSM)", rng, formatador=str,
                    tipo_resposta="simbolica")
        if q:
            return q
    raise RuntimeError("vlsm")


def gerar_sumarizacao(rng):
    """
    Sumarização de rotas: menor bloco que engloba redes contíguas.

    As redes precisam ser CONTÍGUAS e ALINHADAS ao bloco resultante. Por
    isso o endereço inicial é escolhido como múltiplo do tamanho total —
    caso contrário, `collapse_addresses` devolveria mais de um bloco e a
    questão não teria resposta única.
    """
    for _ in range(80):
        prefixo = rng.choice([24, 25, 26, 27])
        n = rng.choice([2, 4, 8])

        tam_bloco  = 2 ** (32 - prefixo)      # endereços por rede
        tam_total  = tam_bloco * n            # espaço somado
        p_sumario  = prefixo - (n.bit_length() - 1)

        # Base alinhada ao bloco somado, dentro de 192.168.0.0/16
        espaco = ipaddress.ip_network("192.168.0.0/16")
        max_off = espaco.num_addresses - tam_total
        if max_off <= 0:
            continue
        offset = rng.randrange(0, max_off, tam_total)
        inicio = int(espaco.network_address) + offset

        redes = []
        for i in range(n):
            redes.append(ipaddress.ip_network(
                f"{ipaddress.ip_address(inicio + i * tam_bloco)}/{prefixo}",
                strict=False))

        sumario = list(ipaddress.collapse_addresses(redes))
        if len(sumario) != 1 or sumario[0].prefixlen != p_sumario:
            continue

        correta = str(sumario[0])
        lista = ", ".join(str(r) for r in redes)

        distratores = [
            str(redes[0]),                                   # só a primeira
            f"{sumario[0].network_address}/{p_sumario - 1}",  # bloco maior
            f"{sumario[0].network_address}/{prefixo}",        # sem sumarizar
            "192.168.0.0/16",                                 # bloco inteiro
            str(redes[-1]),                                   # só a última
        ]

        CEN = [
            f"Um roteador anuncia as seguintes rotas: {lista}.",
            f"A tabela de roteamento contém as redes contíguas: {lista}.",
            f"Para reduzir o tamanho da tabela, deseja-se agregar as rotas: "
            f"{lista}.",
            f"Um protocolo de roteamento recebeu os prefixos: {lista}.",
        ]
        PER = [
            "Qual bloco as sumariza sem incluir endereços adicionais?",
            "Determine a rota sumarizada equivalente.",
            "A sumarização correta dessas rotas é:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"As {n} redes /{prefixo} são contíguas e alinhadas, ocupando "
            f"juntas {_fmt(tam_total)} endereços — exatamente o tamanho de um "
            f"bloco /{p_sumario}. A rota sumarizada é {correta}."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (sumarização)", rng, formatador=str,
                    tipo_resposta="simbolica")
        if q:
            return q
    raise RuntimeError("sumarizacao")


# ══════════════════════════════════════════
#  IPv6
# ══════════════════════════════════════════

def gerar_ipv6(rng):
    """Compressão de endereço IPv6 e contagem de endereços."""
    for _ in range(50):
        modo = rng.choice(["comprimir", "hosts", "tipo"])

        if modo == "comprimir":
            grupos = []
            zeros_em = rng.randint(2, 5)
            for i in range(8):
                if zeros_em <= i < zeros_em + rng.randint(2, 3):
                    grupos.append("0000")
                else:
                    grupos.append(f"{rng.randint(0x1000, 0xffff):04x}")
            completo = ":".join(grupos)
            endereco = ipaddress.ip_address(completo)
            correta = str(endereco)          # forma comprimida canônica

            distratores = [
                completo,
                completo.replace(":0000:", "::", 1),
                str(endereco).replace("::", ":0:"),
                completo.replace("0000", "0"),
            ]
            CEN = [f"Considere o endereço IPv6 {completo}."]
            PER = ["Qual é a sua forma comprimida, segundo a RFC 5952?",
                   "A representação comprimida desse endereço é:"]
            explicacao = (
                f"A RFC 5952 permite omitir zeros à esquerda de cada grupo e "
                f"substituir a maior sequência de grupos nulos por '::' uma "
                f"única vez. Aplicando as regras a {completo}, obtém-se "
                f"{correta}."
            )
            fmt, tipo = str, "simbolica"

        elif modo == "hosts":
            prefixo = rng.choice([48, 56, 64, 32])
            correta = 128 - prefixo
            distratores = [prefixo, correta + 8, correta - 8, 32 - prefixo % 32,
                           correta * 2]
            CEN = [f"Uma organização recebeu o bloco IPv6 2001:db8::/{prefixo}."]
            PER = ["Quantos bits restam para endereçamento interno?",
                   "Determine a quantidade de bits disponíveis para hosts e sub-redes."]
            explicacao = (
                f"O IPv6 usa endereços de 128 bits. Com prefixo /{prefixo}, "
                f"restam 128 − {prefixo} = {correta} bits para uso interno."
            )
            fmt, tipo = _fmt, "numerica"

        else:
            TIPOS_V6 = [
                ("fe80::1",           "link-local"),
                ("::1",               "loopback"),
                ("2001:db8::1",       "unicast global (documentação)"),
                ("ff02::1",           "multicast"),
                ("fc00::1",           "unique local (ULA)"),
            ]
            endereco, correta = rng.choice(TIPOS_V6)
            distratores = [t for _, t in TIPOS_V6 if t != correta]
            distratores.append("broadcast")
            CEN = [f"Uma interface apresenta o endereço IPv6 {endereco}."]
            PER = ["Esse endereço é do tipo:", "Trata-se de um endereço:"]
            explicacao = (
                f"O endereço {endereco} é do tipo {correta}. Note que o IPv6 "
                f"não possui endereços de broadcast — essa função é exercida "
                f"por multicast."
            )
            fmt, tipo = str, "textual"

        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (IPv6)", rng, formatador=fmt, tipo_resposta=tipo)
        if q:
            return q
    raise RuntimeError("ipv6")


# ══════════════════════════════════════════
#  DESEMPENHO
# ══════════════════════════════════════════

def gerar_tempo_transmissao(rng):
    """Tempo de transmissão de um arquivo dada a taxa do enlace."""
    for _ in range(50):
        tamanho_mb = rng.choice([10, 25, 50, 100, 200, 500, 1000])
        taxa_mbps = rng.choice([10, 50, 100, 200, 500, 1000])

        bits = tamanho_mb * 8 * 1_000_000
        segundos = bits / (taxa_mbps * 1_000_000)
        if segundos < 0.5 or segundos > 3600:
            continue
        correta = round(segundos, 1)

        distratores = [
            round(tamanho_mb / taxa_mbps, 1),
            round(segundos * 8, 1),
            round(segundos / 8, 1),
            round(segundos * 2, 1),
            round(segundos / 2, 1),
            round(segundos * 60, 1),   # respondeu como se fosse minuto
            round(segundos / 60, 1),   # converteu para minutos sem pedir
            round(segundos * 4, 1),
        ]

        CEN = [
            f"Um arquivo de {tamanho_mb} MB será transferido por um enlace de "
            f"{taxa_mbps} Mbps.",
            f"Uma equipe precisa enviar {tamanho_mb} MB através de uma conexão "
            f"de {taxa_mbps} Mbps.",
            f"O backup de {tamanho_mb} MB trafega por um link de {taxa_mbps} Mbps.",
        ]
        PER = [
            "Desconsiderando latência e sobrecarga, qual é o tempo de "
            "transmissão, em segundos?",
            "Ignorando atrasos e overhead, o tempo de transferência em "
            "segundos é de:",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Convertendo o arquivo para bits: {tamanho_mb} MB × 8 = "
            f"{_fmt(tamanho_mb * 8)} Mb. Dividindo pela taxa do enlace: "
            f"{_fmt(tamanho_mb * 8)} ÷ {taxa_mbps} = {_fmt_dec(correta, 1)} segundos."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (desempenho)", rng,
                    formatador=lambda v: _fmt_dec(v, 1))
        if q:
            return q
    raise RuntimeError("tempo_transmissao")


def gerar_eficiencia_cabecalho(rng):
    """Eficiência do quadro: payload sobre o total transmitido."""
    for _ in range(50):
        payload = rng.choice([46, 64, 128, 256, 512, 1000, 1460, 1500])
        cabecalhos = rng.choice([
            (18, "Ethernet"),
            (38, "Ethernet + IP"),
            (58, "Ethernet + IP + TCP"),
            (46, "Ethernet + IP + UDP"),
        ])
        overhead, descricao = cabecalhos
        total = payload + overhead
        correta = round(payload / total * 100, 1)

        distratores = [
            round(overhead / total * 100, 1),
            round(payload / overhead * 100, 1),
            round(correta + 10, 1),
            round(correta - 10, 1),
            round(payload / (payload + 2 * overhead) * 100, 1),  # contou o cabeçalho duas vezes
            round(correta + 20, 1),
            round(correta - 5, 1),
            round(correta / 2, 1),
        ]

        CEN = [
            f"Um quadro transporta {payload} bytes de dados úteis, acrescidos "
            f"de {overhead} bytes de cabeçalhos ({descricao}).",
            f"Ao encapsular {payload} bytes de payload, os cabeçalhos "
            f"({descricao}) somam {overhead} bytes.",
        ]
        PER = [
            "Qual é a eficiência da transmissão, em percentual?",
            "O percentual de dados úteis no total transmitido é de:",
            "Determine a eficiência percentual do quadro.",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"A eficiência é a razão entre o payload e o total transmitido: "
            f"{payload} ÷ ({payload} + {overhead}) = {payload}/{total}, "
            f"o que corresponde a {_fmt_dec(correta, 1)}%."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (desempenho)", rng,
                    formatador=lambda v: f"{_fmt_dec(v, 1)}%",
                    tipo_resposta="percentual")
        if q:
            return q
    raise RuntimeError("eficiencia_cabecalho")


def gerar_fragmentacao(rng):
    """Fragmentação IP: quantos fragmentos dado um MTU."""
    for _ in range(50):
        datagrama = rng.choice([1500, 2000, 3000, 4000, 5000, 6000])
        mtu = rng.choice([576, 1006, 1280, 1500])
        if datagrama <= mtu:
            continue

        # Payload por fragmento deve ser múltiplo de 8 (campo offset)
        payload_max = ((mtu - 20) // 8) * 8
        dados = datagrama - 20
        correta = -(-dados // payload_max)      # teto da divisão

        distratores = [correta + 1, correta - 1,
                       -(-datagrama // mtu), correta * 2, mtu // 20,
                       correta + 2, max(1, correta - 2),
                       -(-dados // (payload_max - 20)) if payload_max > 40
                       else correta + 3]

        CEN = [
            f"Um datagrama IP de {datagrama} bytes (incluindo 20 bytes de "
            f"cabeçalho) precisa atravessar um enlace com MTU de {mtu} bytes.",
            f"Ao rotear um datagrama de {datagrama} bytes, com cabeçalho IP de "
            f"20 bytes, o próximo enlace impõe MTU de {mtu} bytes.",
        ]
        PER = [
            "Em quantos fragmentos ele será dividido?",
            "Determine o número de fragmentos gerados.",
            "Quantos fragmentos serão necessários?",
        ]
        cen = rng.choice(CEN)
        enunciado = f"{cen} {rng.choice(PER)}"
        explicacao = (
            f"Cada fragmento carrega no máximo {mtu} − 20 = {mtu - 20} bytes "
            f"de dados, mas o offset exige múltiplo de 8, reduzindo para "
            f"{payload_max} bytes. Com {dados} bytes de dados a transportar: "
            f"{dados} ÷ {payload_max} = {dados / payload_max:.2f}, "
            f"arredondando para cima, {correta} fragmentos."
        )
        q = _montar(enunciado, correta, distratores, explicacao,
                    "Redes (camada de rede)", rng)
        if q:
            return q
    raise RuntimeError("fragmentacao")


def _com_preposicao(prep: str, sintagma: str) -> str:
    """Junta preposição e sintagma fazendo a CONTRAÇÃO."""
    s = str(sintagma or "").strip()
    CONTRACOES = {
        ("a", "a "): "à ", ("a", "o "): "ao ", ("a", "as "): "às ",
        ("de", "a "): "da ", ("de", "o "): "do ", ("de", "as "): "das ",
        ("em", "a "): "na ", ("em", "o "): "no ", ("em", "as "): "nas ",
    }
    for (p, art), contraida in CONTRACOES.items():
        if prep == p and s.lower().startswith(art):
            return contraida + s[len(art):]
    return f"{prep} {s}"


def _inicial_maiuscula(t: str) -> str:
    """Eleva só a primeira letra, preservando o resto."""
    s = str(t or "")
    return s[:1].upper() + s[1:] if s else s



# ──────────────────────────────────────────
#  PARTE CONCEITUAL
# ──────────────────────────────────────────
#
#  Os templates acima cobrem CÁLCULO de endereçamento. Os que
#  seguem cobrem a parte conceitual — modelo OSI, TCP/IP,
#  transporte e portas — com fatos verificados em fonte.
#
#  Fontes em redes/_fontes.md.
#
# ══════════════════════════════════════════════════════════
#  BASE DE FATOS
# ══════════════════════════════════════════════════════════

# ── Camadas do modelo OSI ──
#
# Fontes: Check Point; OpServices; Estratégia Concursos; Tanenbaum,
# Redes de Computadores; Kurose & Ross.
#
# (número, nome, com_artigo, função, PDU, exemplos, equipamento)
CAMADAS_OSI = [
    (1, "física", "a camada física",
     "transmitir bits brutos pelo meio, definindo sinais elétricos e "
     "conectores",
     "bit", "cabos, conectores e sinais de rádio", "hub e repetidor"),

    (2, "enlace de dados", "a camada de enlace de dados",
     "transformar o canal bruto em uma linha livre de erros, usando "
     "endereçamento físico",
     "quadro", "Ethernet e PPP", "switch e bridge"),

    (3, "rede", "a camada de rede",
     "rotear pacotes entre redes distintas, com endereçamento lógico",
     "pacote", "IP e ICMP", "roteador"),

    (4, "transporte", "a camada de transporte",
     "estabelecer comunicação fim a fim entre processos, com "
     "segmentação e controle de fluxo",
     "segmento", "TCP e UDP", None),

    (5, "sessão", "a camada de sessão",
     "estabelecer, manter e sincronizar sessões de comunicação",
     "dados", "NetBIOS e RPC", None),

    (6, "apresentação", "a camada de apresentação",
     "traduzir, comprimir e criptografar os dados",
     "dados", "TLS e formatos de codificação", None),

    (7, "aplicação", "a camada de aplicação",
     "fazer a interface com as aplicações do usuário",
     "dados", "HTTP, SMTP, DNS e FTP", None),
]

# ── Correspondência OSI × TCP/IP ──
#
# (camada TCP/IP, com_artigo, camadas OSI correspondentes, descrição)
TCPIP_OSI = [
    ("acesso à rede", "a camada de acesso à rede",
     "às camadas 1 e 2 do OSI, física e enlace",
     "reúne a transmissão física e o enlace de dados"),
    ("internet", "a camada de internet",
     "à camada 3 do OSI, rede",
     "corresponde exatamente à camada de rede"),
    ("transporte", "a camada de transporte",
     "à camada 4 do OSI, transporte",
     "corresponde exatamente à camada de transporte"),
    ("aplicação", "a camada de aplicação",
     "às camadas 5, 6 e 7 do OSI — sessão, apresentação e aplicação",
     "consolida três camadas do modelo OSI em uma só"),
]

# ── TCP versus UDP ──
#
# (característica, valor no TCP, valor no UDP)
TCP_UDP = [
    ("o estabelecimento de conexão",
     "orientado a conexão, com handshake de três vias",
     "sem conexão prévia, envio imediato dos datagramas"),
    ("a garantia de entrega",
     "garantida, com retransmissão dos segmentos perdidos",
     "não garantida, sem retransmissão"),
    ("a ordenação dos dados",
     "reordena os segmentos no destino",
     "não reordena, entrega na ordem de chegada"),
    ("o controle de fluxo",
     "presente, por janela deslizante",
     "ausente, sem janela deslizante"),
    ("o tamanho do cabeçalho",
     "20 bytes",
     "8 bytes"),
]

# Respostas POSSÍVEIS para cada característica.
#
# Os distratores vinham das OUTRAS linhas da tabela, então uma pergunta
# sobre o tamanho do cabeçalho trazia "sem conexão prévia" e "garantida,
# com retransmissão" entre as opções. Três das cinco se descartavam sem
# saber nada de TCP ou UDP, e o aluno decidia entre duas.
#
# Aqui cada característica tem erros do seu próprio tipo.
PLAUSIVEIS_TCP_UDP = {
    "o estabelecimento de conexão": [
        "orientado a conexão, com handshake de duas vias",
        "conexão estabelecida apenas no primeiro datagrama",
        "conexão negociada pela aplicação",
    ],
    "a garantia de entrega": [
        "garantida apenas para segmentos menores que a MTU",
        "garantida pela camada de enlace, não pelo transporte",
        "garantida somente dentro da mesma rede local",
    ],
    "a ordenação dos dados": [
        "reordena na origem, antes do envio",
        "reordena apenas os segmentos marcados com PSH",
        "delega a ordenação à camada de aplicação",
    ],
    "o controle de fluxo": [
        "presente, mas apenas na abertura da conexão",
        "delegado ao roteador de borda",
        "substituído pelo controle de congestionamento",
    ],
    "o tamanho do cabeçalho": [
        "12 bytes",
        "40 bytes",
        "64 bytes",
    ],
}

USOS_TCP = ["a navegação web por HTTP", "a transferência de arquivos por FTP",
            "o envio de correio por SMTP", "o acesso remoto por SSH"]
USOS_UDP = ["a resolução de nomes por DNS", "a atribuição de endereços por "
            "DHCP", "a transmissão de vídeo ao vivo", "a telefonia por VoIP"]

# ── Portas bem conhecidas ──
PORTAS = [
    ("21", "FTP", "transferência de arquivos"),
    ("22", "SSH", "acesso remoto seguro"),
    ("23", "Telnet", "acesso remoto sem criptografia"),
    ("25", "SMTP", "envio de correio eletrônico"),
    ("53", "DNS", "resolução de nomes"),
    ("80", "HTTP", "navegação web sem criptografia"),
    ("110", "POP3", "recebimento de correio, com download"),
    ("143", "IMAP", "recebimento de correio, mantendo no servidor"),
    ("443", "HTTPS", "navegação web com criptografia"),
    ("3306", "MySQL", "banco de dados MySQL"),
    ("5432", "PostgreSQL", "banco de dados PostgreSQL"),
]


# ══════════════════════════════════════════════════════════
#  TEMPLATES — MODELO OSI
# ══════════════════════════════════════════════════════════

def gerar_camada_funcao(rng):
    """Qual a função de determinada camada do OSI?"""
    num, nome, art, funcao, pdu, exemplos, equip = rng.choice(CAMADAS_OSI)

    CENARIOS = [
        f"Considere {art} do modelo OSI, de número {num}.",
        f"O modelo OSI divide a comunicação em sete camadas. Considere "
        f"{art}.",
        f"Um estudante revisa as atribuições {_com_preposicao('de', art)}.",
        f"Entre as camadas do modelo OSI encontra-se {art}, a de número "
        f"{num}.",
        f"Ao diagnosticar um problema de rede, a equipe examina {art}.",
    ]
    COMANDOS = [
        "Assinale a alternativa que apresenta sua função.",
        "Sua função é:",
        "Qual a função dessa camada?",
        "Assinale a alternativa que descreve corretamente sua atribuição.",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = funcao
    distratores = [c[3] for c in CAMADAS_OSI if c[3] != funcao]
    rng.shuffle(distratores)

    explicacao = (
        f"{_inicial_maiuscula(art)} é a de número {num} e tem por função "
        f"{funcao}. Sua unidade de dados é o {pdu}, e são exemplos "
        f"{exemplos}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
               "Redes (modelo OSI)", rng)
    if q:
        q["_fato"] = f"osi:{nome}"
    return q


def gerar_camada_numero(rng):
    """Qual o número de determinada camada, ou vice-versa?"""
    num, nome, art, funcao, pdu, exemplos, equip = rng.choice(CAMADAS_OSI)
    modo = rng.choice(["nome_para_numero", "numero_para_nome"])

    if modo == "nome_para_numero":
        CENARIOS = [
            f"Considere {art} do modelo OSI.",
            f"As camadas do modelo OSI são numeradas de baixo para cima. "
            f"Considere {art}.",
            f"Um profissional de rede menciona {art} em um diagnóstico.",
        ]
        COMANDOS = [
            "Essa camada ocupa a posição:",
            "Assinale a alternativa com seu número.",
            "Que número ela ocupa no modelo?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = f"camada {num}"
        distratores = [f"camada {c[0]}" for c in CAMADAS_OSI if c[0] != num]
    else:
        CENARIOS = [
            f"No modelo OSI, a camada de número {num} tem função "
            f"específica.",
            f"Um engenheiro se refere a um problema na camada {num}.",
            f"A documentação técnica menciona a camada {num} do modelo "
            f"OSI.",
        ]
        COMANDOS = [
            "Trata-se da camada de:",
            "Assinale a alternativa que a nomeia.",
            "Que camada é essa?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = nome
        distratores = [c[1] for c in CAMADAS_OSI if c[1] != nome]

    explicacao = (
        f"{_inicial_maiuscula(art)} é a de número {num} no modelo OSI, e tem por "
        f"função {funcao}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
               "Redes (modelo OSI)", rng)
    if q:
        q["_fato"] = f"osi:{nome}"
    return q


def gerar_pdu_camada(rng):
    """
    Qual a unidade de dados de cada camada?

    A PDU muda de nome a cada camada — bit, quadro, pacote, segmento —
    e essa nomenclatura é cobrada com frequência.
    """
    candidatos = [c for c in CAMADAS_OSI if c[4] != "dados"]
    num, nome, art, funcao, pdu, exemplos, equip = rng.choice(candidatos)

    CENARIOS = [
        f"Cada camada do modelo OSI manipula uma unidade de dados "
        f"própria. Considere {art}.",
        f"A unidade de dados de protocolo varia conforme a camada. "
        f"Considere {art}.",
        f"Um analista descreve o tráfego {_com_preposicao('em', art)}.",
        f"Ao encapsular os dados, {art} produz uma unidade específica.",
    ]
    COMANDOS = [
        "Sua unidade de dados é denominada:",
        "Assinale a alternativa com a unidade correspondente.",
        "Que unidade de dados essa camada manipula?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = pdu
    distratores = [c[4] for c in CAMADAS_OSI if c[4] != pdu]
    distratores += ["célula", "bloco", "fluxo"]

    explicacao = (
        f"{_inicial_maiuscula(art)}, de número {num}, manipula o {pdu}. A "
        f"nomenclatura muda a cada camada: bit na física, quadro no "
        f"enlace, pacote na rede e segmento no transporte."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
               "Redes (modelo OSI)", rng)
    if q:
        q["_fato"] = f"pdu:{nome}"
    return q


def gerar_equipamento_camada(rng):
    """
    Em que camada opera determinado equipamento?

    A distinção entre hub, switch e roteador é clássica de prova.
    """
    candidatos = [c for c in CAMADAS_OSI if c[6]]
    num, nome, art, funcao, pdu, exemplos, equip = rng.choice(candidatos)
    equipamento = equip.split(" e ")[0]

    modo = rng.choice(["equip_para_camada", "camada_para_equip"])

    if modo == "equip_para_camada":
        CENARIOS = [
            f"Um {equipamento} é instalado em uma rede local.",
            f"Considere o funcionamento de um {equipamento}.",
            f"O inventário de uma rede inclui um {equipamento}.",
            f"Um técnico substitui um {equipamento} com defeito.",
        ]
        COMANDOS = [
            "Esse equipamento opera na camada:",
            "Assinale a alternativa com a camada em que ele atua.",
            "Em que camada do modelo OSI ele opera?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = f"{num} — {nome}"
        distratores = [f"{c[0]} — {c[1]}" for c in CAMADAS_OSI if c[0] != num]
    else:
        CENARIOS = [
            f"Considere {art} do modelo OSI, de número {num}.",
            f"A camada {num} do modelo OSI é {art[3:]}.",
            f"Um projeto de rede define os equipamentos por camada. "
            f"Considere {art}.",
        ]
        COMANDOS = [
            "Assinale a alternativa com um equipamento que opera nela.",
            "Que equipamento atua nessa camada?",
            "Um equipamento típico dessa camada é:",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = equipamento
        distratores = []
        for c in CAMADAS_OSI:
            if c[6] and c[0] != num:
                distratores.extend(c[6].split(" e "))
        distratores += ["modem", "gateway de aplicação", "patch panel"]

    explicacao = (
        f"O {equipamento} opera na camada {num}, {art[3:]}, cuja função "
        f"é {funcao}. "
    )
    if num == 1:
        explicacao += ("Convém lembrar a distinção: o HUB é camada 1 e "
                       "replica o sinal para todas as portas; o SWITCH é "
                       "camada 2 e encaminha por endereço MAC.")
    elif num == 2:
        explicacao += ("O switch difere do hub por encaminhar com base no "
                       "endereço MAC, e não replicar para todas as portas.")
    q = _montar(enunciado, correta, distratores, explicacao,
               "Redes (equipamentos e camadas)", rng)
    if q:
        q["_fato"] = f"equip:{nome}"
    return q


# ══════════════════════════════════════════════════════════
#  TEMPLATES — TCP/IP E TRANSPORTE
# ══════════════════════════════════════════════════════════

def gerar_correspondencia_tcpip(rng):
    """A que camadas do OSI corresponde cada camada do TCP/IP?"""
    nome, art, corresponde, descricao = rng.choice(TCPIP_OSI)

    CENARIOS = [
        f"O modelo TCP/IP tem quatro camadas, enquanto o OSI tem sete. "
        f"Considere {art} do TCP/IP.",
        f"Ao comparar os modelos TCP/IP e OSI, examina-se {art}.",
        f"Um estudante mapeia o modelo TCP/IP sobre o OSI e chega "
        f"{_com_preposicao('a', art)}.",
        f"Entre as camadas do modelo TCP/IP encontra-se {art}.",
    ]
    COMANDOS = [
        "Ela corresponde:",
        "Assinale a alternativa com a correspondência correta no OSI.",
        "Qual a correspondência no modelo OSI?",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = corresponde
    distratores = [t[2] for t in TCPIP_OSI if t[2] != corresponde]
    distratores += [
        "à camada 7 do OSI apenas, aplicação",
        "às camadas 2 e 3 do OSI, enlace e rede",
    ]

    # O teste de português exige que a explicação TERMINE no resultado,
    # não em comentário. A descrição vem antes, a correspondência por
    # último.
    explicacao = (
        f"{_inicial_maiuscula(art)} do TCP/IP {descricao}. Corresponde, "
        f"portanto, {corresponde}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
               "Redes (modelo TCP/IP)", rng)
    if q:
        q["_fato"] = f"tcpip:{nome}"
    return q


def gerar_tcp_udp(rng):
    """Como TCP e UDP se comportam em determinada característica?"""
    caracteristica, valor_tcp, valor_udp = rng.choice(TCP_UDP)
    protocolo = rng.choice(["TCP", "UDP"])
    valor = valor_tcp if protocolo == "TCP" else valor_udp
    outro = valor_udp if protocolo == "TCP" else valor_tcp

    CENARIOS = [
        f"Considere o protocolo {protocolo} quanto à seguinte "
        f"característica: {caracteristica}.",
        f"Ao comparar TCP e UDP, avalia-se {caracteristica} no "
        f"{protocolo}.",
        f"Um estudante analisa {caracteristica} no protocolo "
        f"{protocolo}.",
        f"A escolha entre TCP e UDP considera {caracteristica}. "
        f"Considere o {protocolo}.",
    ]
    COMANDOS = [
        "Nesse protocolo, essa característica apresenta-se como:",
        "Assinale a alternativa correta.",
        "A descrição correta é:",
    ]
    enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"

    correta = valor
    distratores = [outro] + PLAUSIVEIS_TCP_UDP.get(caracteristica, [])

    explicacao = (
        f"No {protocolo}, {caracteristica} apresenta-se assim: {valor}. "
        f"No outro protocolo, por contraste: {outro}. A escolha entre os "
        f"dois é entre CONFIABILIDADE e LATÊNCIA — o UDP é preferido "
        f"quando o atraso da retransmissão custaria mais que a perda de "
        f"um pacote."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
               "Redes (camada de transporte)", rng)
    if q:
        q["_fato"] = f"tcpudp:{caracteristica}"
    return q


def gerar_protocolo_por_uso(rng):
    """Dado um uso, TCP ou UDP é o adequado?"""
    protocolo = rng.choice(["TCP", "UDP"])
    uso = rng.choice(USOS_TCP if protocolo == "TCP" else USOS_UDP)

    CENARIOS = [
        f"Considere a seguinte aplicação de rede: {uso}.",
        f"Um sistema depende do seguinte serviço: {uso}.",
        f"Ao projetar uma solução que envolve {uso},",
        f"O tráfego de rede de um servidor inclui {uso}.",
    ]
    COMANDOS = [
        "O protocolo de transporte adequado é:",
        "Assinale a alternativa com o protocolo empregado.",
        "identifica-se o seguinte protocolo de transporte:",
        "Que protocolo de transporte é utilizado?",
    ]
    cenario = rng.choice(CENARIOS)
    if cenario.rstrip().endswith(","):
        comando = "identifica-se o seguinte protocolo de transporte:"
    else:
        comando = rng.choice([c for c in COMANDOS if c[0].isupper()])
    enunciado = f"{cenario} {comando}"

    correta = protocolo
    outro = "UDP" if protocolo == "TCP" else "TCP"
    distratores = [outro, "ICMP", "ARP", "IP", "SCTP"]

    if protocolo == "TCP":
        motivo = ("exige entrega garantida e ordenada, o que justifica o "
                  "custo do handshake e da retransmissão")
    else:
        motivo = ("prioriza baixa latência, e o atraso de uma "
                  "retransmissão custaria mais que a perda de um pacote")
    explicacao = (
        f"O protocolo adequado é o {protocolo}, porque {uso} {motivo}."
    )
    q = _montar(enunciado, correta, distratores, explicacao,
               "Redes (camada de transporte)", rng)
    if q:
        q["_fato"] = f"uso:{protocolo}"
    return q


def gerar_porta_servico(rng):
    """Que serviço usa determinada porta, ou vice-versa?"""
    porta, servico, descricao = rng.choice(PORTAS)
    modo = rng.choice(["porta_para_servico", "servico_para_porta"])

    if modo == "porta_para_servico":
        CENARIOS = [
            f"Uma varredura de rede identifica a porta {porta} aberta em "
            f"um servidor.",
            f"O firewall de uma empresa libera a porta {porta}.",
            f"Um administrador verifica que a porta {porta} está em uso.",
            f"A configuração de um serviço utiliza a porta {porta}.",
        ]
        COMANDOS = [
            "Essa porta corresponde ao serviço:",
            "Assinale a alternativa com o serviço associado.",
            "Que serviço usa essa porta por padrão?",
        ]
        enunciado = f"{rng.choice(CENARIOS)} {rng.choice(COMANDOS)}"
        correta = servico
        distratores = [p[1] for p in PORTAS if p[1] != servico]
    else:
        CENARIOS = [
            f"Considere o serviço {servico}, usado para {descricao}.",
            f"Um servidor precisa expor o serviço {servico}.",
            f"A documentação de um sistema menciona o {servico}.",
            f"Ao configurar o firewall para o {servico},",
        ]
        COMANDOS = [
            "A porta padrão desse serviço é:",
            "Assinale a alternativa com a porta correspondente.",
            "libera-se a seguinte porta padrão:",
            "Que porta ele utiliza por padrão?",
        ]
        cenario = rng.choice(CENARIOS)
        if cenario.rstrip().endswith(","):
            comando = "libera-se a seguinte porta padrão:"
        else:
            comando = rng.choice([c for c in COMANDOS if c[0].isupper()])
        enunciado = f"{cenario} {comando}"
        correta = porta
        distratores = [p[0] for p in PORTAS if p[0] != porta]

    rng.shuffle(distratores)
    explicacao = (
        f"A porta {porta} corresponde ao {servico}, usado para "
        f"{descricao}."
    )
    q = _montar(enunciado, correta, distratores[:6], explicacao,
               "Redes (portas e serviços)", rng)
    if q:
        q["_fato"] = f"porta:{porta}"
    return q


# ──────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────

TEMPLATES_REDES = {
    "hosts_validos":         gerar_hosts_validos,
    "mascara_wildcard":      gerar_mascara_wildcard,
    "rede_broadcast":        gerar_rede_broadcast,
    "tipo_endereco":         gerar_tipo_endereco,
    "pertencimento":         gerar_pertencimento,
    "divisao_subredes":      gerar_divisao_subredes,
    "vlsm":                  gerar_vlsm,
    "sumarizacao":           gerar_sumarizacao,
    "ipv6":                  gerar_ipv6,
    "tempo_transmissao":     gerar_tempo_transmissao,
    "eficiencia_cabecalho":  gerar_eficiencia_cabecalho,
    "fragmentacao":          gerar_fragmentacao,
    # ── conceituais ──
    "camada_funcao":         gerar_camada_funcao,
    "camada_numero":         gerar_camada_numero,
    "pdu_camada":            gerar_pdu_camada,
    "equipamento_camada":    gerar_equipamento_camada,
    "correspondencia":       gerar_correspondencia_tcpip,
    "tcp_udp":               gerar_tcp_udp,
    "protocolo_uso":         gerar_protocolo_por_uso,
    "porta_servico":         gerar_porta_servico,
}

TOPICOS_REDES = {
    "enderecamento": ["hosts_validos", "mascara_wildcard", "rede_broadcast",
                      "tipo_endereco", "pertencimento"],
    "subredes":      ["divisao_subredes", "vlsm", "sumarizacao"],
    "ipv6":          ["ipv6"],
    "desempenho":    ["tempo_transmissao", "eficiencia_cabecalho"],
    "camada_rede":   ["fragmentacao"],
    "modelo_osi":    ["camada_funcao", "camada_numero", "pdu_camada",
                      "equipamento_camada"],
    "transporte":    ["correspondencia", "tcp_udp", "protocolo_uso",
                      "porta_servico"],
}

PALAVRAS_CHAVE = {
    "camada_funcao":        ["modelo osi", "camadas osi", "camada de rede",
                             "camada de transporte", "camada fisica",
                             "camada de enlace", "camada de aplicacao"],
    "camada_numero":        ["modelo osi", "camadas osi", "camada 2",
                             "camada 3", "camada 7"],
    "pdu_camada":           ["pdu", "unidade de dados", "quadro", "datagrama",
                             "encapsulamento", "modelo osi"],
    "equipamento_camada":   ["switch", "roteador", "hub", "bridge",
                             "equipamentos de rede", "modelo osi"],
    "correspondencia":      ["tcp/ip", "modelo tcp-ip", "modelo osi",
                             "camadas tcp/ip"],
    "tcp_udp":              ["tcp", "udp", "camada de transporte",
                             "protocolo de transporte", "handshake"],
    "protocolo_uso":        ["tcp", "udp", "camada de transporte", "voip",
                             "streaming", "protocolo de transporte"],
    "porta_servico":        ["porta", "portas", "porta padrao", "http",
                             "https", "ssh", "smtp", "dns", "ftp",
                             "portas bem conhecidas"],
    "hosts_validos":        ["enderecamento", "sub-rede", "subrede", "host", "cidr",
                             "mascara", "redes", "ipv4"],
    "mascara_wildcard":     ["mascara", "wildcard", "cidr", "prefixo", "redes",
                             "acl", "enderecamento"],
    "rede_broadcast":       ["broadcast", "endereco de rede", "sub-rede", "cidr",
                             "enderecamento", "redes"],
    "tipo_endereco":        ["endereco privado", "endereco publico", "rfc 1918",
                             "loopback", "multicast", "apipa", "redes"],
    "pertencimento":        ["sub-rede", "enderecamento", "roteamento", "host", "redes"],
    "divisao_subredes":     ["sub-rede", "subnetting", "segmentacao", "vlan",
                             "cidr", "redes"],
    "vlsm":                 ["vlsm", "sub-rede", "planejamento de enderecamento",
                             "cidr", "redes"],
    "sumarizacao":          ["sumarizacao", "agregacao de rotas", "supernetting",
                             "roteamento", "cidr", "redes"],
    "ipv6":                 ["ipv6", "enderecamento", "rfc 5952", "link-local",
                             "redes"],
    "tempo_transmissao":    ["desempenho", "largura de banda", "throughput",
                             "vazao", "latencia", "redes"],
    "eficiencia_cabecalho": ["cabecalho", "overhead", "encapsulamento", "quadro",
                             "eficiencia", "redes", "ethernet"],
    "fragmentacao":         ["fragmentacao", "mtu", "camada de rede", "datagrama",
                             "ip", "redes"],
}


# Chaves genéricas demais para identificar redes sozinhas.
# Genéricas de VERDADE: palavras que existem fora de redes e, sozinhas,
# não identificam o assunto. Termos como "sub-rede", "CIDR", "broadcast"
# e "MTU" NÃO entram aqui — são inequívocos, e tratá-los como ambíguos
# fazia o gerador de redes perder um livro de redes de verdade.
CHAVES_GENERICAS = {
    "ip",              # "IP" aparece como sigla em outros contextos
    "rede", "redes",   # rede de atenção à saúde, rede de ensino
    "host",            # host de evento
    "camada",          # camada social, camada de tinta
    "protocolo",       # protocolo clínico, protocolo de pesquisa
    "porta",           # porta de entrada do SUS
    "acesso",          # acesso ao serviço de saúde
    "endereco",        # endereço residencial
    "desempenho", "eficiencia", "vazao", "latencia", "quadro",
    "segmentacao",     # segmentação de mercado
    "triagem",         # triagem clínica
    "servico", "servicos", "fluxo", "classificacao",
}


def _normalizar(txt: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", txt or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def templates_para_topicos(topicos: list) -> list:
    """
    Casa os tópicos de um livro indexado com os templates deste gerador.

    A comparação é por PALAVRA INTEIRA, não por substring: "ip" não pode
    casar dentro de "princípio", nem "or" dentro de "ordenação". Antes
    dessa correção, um livro de combinatória acionava geradores de rede
    porque "Princípio" contém "ip".

    Além disso, chaves de UMA palavra genérica (como "contagem", que
    aparece em combinatória, em análise de algoritmos e em prazo
    processual) só valem quando acompanhadas de outra chave do mesmo
    template — sozinhas, geram falso casamento.
    """
    texto = " " + " ".join(_normalizar(str(t)) for t in topicos) + " "

    achados = []
    for nome, chaves in PALAVRAS_CHAVE.items():
        especificas = 0
        genericas   = 0
        for chave in chaves:
            cn = _normalizar(chave)
            if not cn:
                continue
            # \b não funciona bem com acentos removidos + espaços; usamos
            # delimitadores explícitos de palavra.
            padrao = r'(?<![0-9a-z])' + re.escape(cn) + r'(?![0-9a-z])'
            if re.search(padrao, texto):
                if cn in CHAVES_GENERICAS:
                    genericas += 1
                else:
                    especificas += 1

        # Uma chave específica basta; genéricas NÃO acionam sozinhas,
        # por mais que se acumulem. A regra anterior aceitava duas
        # genéricas, e um Caderno do Ministério da Saúde acionava o
        # gerador de portas por conter "porta de entrada do SUS" e
        # "protocolo de acolhimento" — nenhuma das duas sobre redes.
        #
        # O custo é perder algum casamento legítimo em livro de
        # vocabulário pobre; o benefício é nunca gerar questão de outra
        # área, que é o erro visível para o usuário.
        if especificas >= 1:
            achados.append(nome)

    return achados

def gerar_lote(quantidade=12, topico=None, templates=None, seed=None):
    rng = random.Random(seed)
    if templates:
        nomes = [n for n in templates if n in TEMPLATES_REDES]
        if not nomes:
            raise ValueError("Nenhum template válido na lista fornecida.")
    elif topico:
        nomes = TOPICOS_REDES.get(topico.lower())
        if not nomes:
            raise ValueError(f"Tópico '{topico}' inválido. Use: {list(TOPICOS_REDES)}")
    else:
        nomes = list(TEMPLATES_REDES)

    funcoes = [TEMPLATES_REDES[n] for n in nomes]
    rng.shuffle(funcoes)

    questoes = []
    # O laço anterior aceitava a PRIMEIRA questão de cada template, sem
    # filtro. Num simulado de 30, isso rendia sete questões "quantos
    # hosts nessa sub-rede", três delas com o MESMO prefixo /27 e a
    # mesma resposta.
    #
    # O veto atua em três níveis:
    #   enunciado  — nunca repete texto idêntico
    #   fato       — o par (template, resposta) não se repete
    #   tópico     — no máximo dois do mesmo assunto por lote
    #
    # Cada nível afrouxa perto do limite de tentativas, para não
    # devolver lote incompleto quando o material acaba.
    from collections import Counter
    vistos, fatos_usados = set(), set()
    topicos = Counter()
    # Teto por TEMPLATE: dividir a cota pelo número de templates
    # distribui de verdade, enquanto o teto por tópico agrupava
    # assuntos distintos sob o mesmo rótulo.
    import math
    TETO_TOPICO = math.ceil(quantidade / max(1, len(funcoes))) + 1
    tentativas, limite = 0, quantidade * 15

    while len(questoes) < quantidade and tentativas < limite:
        tentativas += 1
        fn = funcoes[tentativas % len(funcoes)]
        try:
            q = fn(rng)
        except Exception:
            continue
        if not q:
            continue

        if q["enunciado"] in vistos and tentativas < limite * 0.9:
            continue

        # O "fato" combina o tipo de pergunta com a resposta: duas
        # questões de /27 pedindo hosts têm o mesmo fato, ainda que o
        # endereço mudе.
        fato = f"{fn.__name__}:{q['alternativas'][q['gabarito']]}"
        if fato in fatos_usados and tentativas < limite * 0.85:
            continue

        # Conta pelo TEMPLATE, não pelo tópico: tópicos agrupam
        # assuntos distintos e deixam a repetição passar.
        if topicos[fn.__name__] >= TETO_TOPICO and tentativas < limite * 0.75:
            continue

        vistos.add(q["enunciado"])
        fatos_usados.add(fato)
        topicos[fn.__name__] += 1
        q["numero"] = len(questoes) + 1
        questoes.append(q)

    return questoes


def gerar_para_api(quantidade=10, topico=None, templates=None, seed=None):
    """
    Formato compatível com salvar_questoes_banco.
    Metadados internos NÃO são incluídos.
    """
    lote = gerar_lote(quantidade, topico, templates, seed)
    questoes_limpas, gabarito_final = [], []
    for q in lote:
        questoes_limpas.append({
            "numero":              q["numero"],
            "enunciado":           q["enunciado"],
            "alternativas":        q["alternativas"],
            "tem_elemento_visual": False,
        })
        gabarito_final.append({
            "numero":           q["numero"],
            "resposta_correta": q["gabarito"],
            "explicacao":       q["explicacao"],
            # O TÓPICO vai junto. O montador de simulado usa-o para
            # limitar quantas questões do mesmo assunto entram no
            # caderno, e sem ele essa trava ficava sempre inerte — um
            # simulado de direito saía com doze perguntas de prazo
            # trabalhista, onze delas com a mesma resposta.
            #
            # Serve também ao aplicativo, que pode relatar o desempenho
            # por assunto sem precisar reabrir o gerador.
            "topico":           q.get("topico", ""),
            # O FATO — par template+resposta — vai junto pelo mesmo
            # motivo do tópico. O veto interno de cada gerador vale
            # dentro de uma chamada; o simulado faz várias, e sem esta
            # chave o mesmo fato voltava com outra redação: "recurso de
            # revista: 8 dias" apareceu três vezes no mesmo caderno.
            #
            # O montador remove o campo antes de devolver, para não
            # sujar o que é gravado no banco.
            "_fato":            q.get("_fato", ""),
        })
    return questoes_limpas, gabarito_final


if __name__ == "__main__":
    qtd    = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    topico = sys.argv[2] if len(sys.argv) > 2 else None
    for q in gerar_lote(qtd, topico):
        print("─" * 66)
        print(f"Q{q['numero']} [{q['topico']}]\n")
        print(q["enunciado"], "\n")
        for L, t in q["alternativas"].items():
            print(f"   {L}) {t}{' ←' if L == q['gabarito'] else ''}")
        print(f"\n   {q['explicacao']}")
    print("─" * 66)
    print(f"\n{qtd} questões | Cálculos pela biblioteca ipaddress (RFCs).\n")
