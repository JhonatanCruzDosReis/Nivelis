# Fatos de redes verificados

---

## Modelo OSI

Publicado pela ISO em 1984, como parte do padrão ISO/IEC 7498-1.

| Nº | Camada | Função | PDU | Exemplos |
|---|---|---|---|---|
| 1 | física | transmissão de bits brutos pelo meio, definindo sinais elétricos e conectores | bit | cabos, conectores, sinal de rádio |
| 2 | enlace de dados | transformar o canal bruto em linha livre de erros, com endereçamento físico | quadro | Ethernet, PPP |
| 3 | rede | roteamento de pacotes entre redes distintas, com endereçamento lógico | pacote | IP, ICMP |
| 4 | transporte | comunicação fim a fim entre processos, com segmentação e controle de fluxo | segmento ou datagrama | TCP, UDP |
| 5 | sessão | estabelecer, manter e sincronizar sessões de comunicação | dados | NetBIOS, RPC |
| 6 | apresentação | tradução, compressão e criptografia dos dados | dados | TLS, formatos de codificação |
| 7 | aplicação | interface com as aplicações do usuário | dados | HTTP, SMTP, DNS, FTP |

**Equipamento por camada:**

| Camada | Equipamento |
|---|---|
| 1 | hub, repetidor |
| 2 | switch, bridge |
| 3 | roteador |

⚠️ ARMADILHAS DE PROVA:
- SWITCH é camada 2 e HUB é camada 1 — a diferença é que o switch
  encaminha por endereço MAC, e o hub replica para todas as portas.
- A PDU muda de nome a cada camada: bit, quadro, pacote, segmento.
- O modelo OSI é REFERÊNCIA CONCEITUAL; quem roda na internet é o
  TCP/IP.

---

## Modelo TCP/IP e correspondência com o OSI

| TCP/IP | Corresponde a (OSI) |
|---|---|
| acesso à rede | camadas 1 e 2 — física e enlace |
| internet | camada 3 — rede |
| transporte | camada 4 — transporte |
| aplicação | camadas 5, 6 e 7 — sessão, apresentação e aplicação |

---

## TCP versus UDP

| Característica | TCP | UDP |
|---|---|---|
| conexão | orientado a conexão, com handshake de três vias | sem conexão |
| confiabilidade | garante entrega, com retransmissão | não garante entrega |
| ordenação | reordena os segmentos no destino | não reordena |
| controle de fluxo | possui | não possui |
| tamanho do cabeçalho | 20 bytes | 8 bytes |
| usos típicos | HTTP, FTP, SMTP, SSH | DNS, DHCP, streaming, VoIP, jogos |

⚠️ A escolha entre TCP e UDP é entre CONFIABILIDADE e LATÊNCIA: o UDP
é preferido quando o atraso da retransmissão custaria mais que a perda
de um pacote.

---

## Portas bem conhecidas

| Porta | Serviço |
|---|---|
| 20 e 21 | FTP |
| 22 | SSH |
| 23 | Telnet |
| 25 | SMTP |
| 53 | DNS |
| 67 e 68 | DHCP |
| 80 | HTTP |
| 110 | POP3 |
| 143 | IMAP |
| 443 | HTTPS |
| 3306 | MySQL |
| 5432 | PostgreSQL |

Fontes: Check Point (What is the OSI Model); OpServices; Alura;
Estratégia Concursos (TSE-TI); Homehost; Tanenbaum, Redes de
Computadores; Kurose & Ross, Redes de Computadores e a Internet.
