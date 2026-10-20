# ─────────────────────────────────────────────────────────────────────────────
#  CORS — uma configuração só para as quatro APIs
#
#  Antes cada arquivo repetia `allow_origins=["*"]`, e o nivelis_api.py ainda
#  juntava isso com `allow_credentials=True`. Essa combinação não é o curinga
#  inofensivo que parece: o Starlette, quando credenciais estão ligadas, PARA
#  de responder "*" e passa a ECOAR a origem de quem perguntou. Testei —
#  pedindo de `https://site-de-terceiro.example` a resposta voltava com
#
#      Access-Control-Allow-Origin: https://site-de-terceiro.example
#      Access-Control-Allow-Credentials: true
#
#  ou seja, qualquer site do mundo autorizado a falar com a API, com
#  credencial, pelo navegador de quem visitasse esse site.
#
#  ── por que isto não quebra o aplicativo ──
#  CORS é uma regra que o NAVEGADOR aplica. O app é React Native, não manda
#  cabeçalho Origin, e por isso nunca passa por essa checagem. Confirmei num
#  teste: com a lista restrita, uma requisição sem Origin continua devolvendo
#  200 normalmente. Restringir aqui só afeta páginas web.
# ─────────────────────────────────────────────────────────────────────────────

import os
from fastapi.middleware.cors import CORSMiddleware

#  Localhost em qualquer porta, para o console de testes (nivelis_telas.html)
#  e para quem estiver desenvolvendo. Uma página maliciosa NÃO consegue se
#  passar por localhost: quem escreve o cabeçalho Origin é o navegador, não
#  o JavaScript da página.
LOCALHOST = r"http://(localhost|127\.0\.0\.1)(:\d+)?"


def origens_configuradas() -> list:
    """Lê CORS_ORIGENS, separada por vírgula. Vazia é o caso normal."""
    cru = os.getenv("CORS_ORIGENS", "")
    return [o.strip() for o in cru.split(",") if o.strip()]


def aplicar_cors(app, metodos: list, nome: str = "") -> None:
    """
    Instala o CORS com a política única.

        CORS_ORIGENS não definida  → só localhost (o padrão seguro)
        CORS_ORIGENS="a.com,b.com" → a.com, b.com e também localhost
        CORS_ORIGENS="*"           → tudo (válvula de emergência)

    `allow_credentials` fica SEMPRE desligado. O app manda o token do Firebase
    como cabeçalho `Authorization` escrito à mão, que para o CORS é cabeçalho
    comum — não "credencial". Credencial, no sentido do CORS, é cookie e
    autenticação que o navegador anexa sozinho, e a API não usa nenhum dos
    dois. Com isso desligado, nem o curinga "*" consegue virar a resposta que
    ecoa a origem do atacante.
    """
    origens = origens_configuradas()
    tudo_liberado = "*" in origens

    if tudo_liberado:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,      # trava o eco da origem
            allow_methods=metodos,
            allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
        )
        print(f"[CORS]{' ' + nome if nome else ''} ABERTO para qualquer origem "
              f"(CORS_ORIGENS=*). Só use assim se souber por quê.")
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origens,
        allow_origin_regex=LOCALHOST,
        allow_credentials=False,
        allow_methods=metodos,
        allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
    )
    extras = ", ".join(origens) if origens else "nenhuma"
    print(f"[CORS]{' ' + nome if nome else ''} localhost (qualquer porta) "
          f"+ {extras}")
