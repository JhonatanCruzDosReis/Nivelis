"""
=============================================================
  NIVELIS — Autenticação Firebase
=============================================================

  Este módulo cuida de identificar o usuário em cada request.

  COMO USAR NA API:
    from auth import obter_usuario_atual

    @app.get("/minha_rota")
    def minha_rota(usuario: dict = Depends(obter_usuario_atual)):
        user_id = usuario["uid"]
        ...

  COMO O APP DEVE CHAMAR:
    O app React Native pega o token JWT do Firebase Auth e envia
    no header Authorization de cada request:

      Authorization: Bearer <id_token_do_firebase>

  MODO DEV:
    Se a chamada vier sem token MAS com header `X-Dev-User-Id`,
    aceita esse ID como usuário (útil para testar via /docs).
    Em produção, defina a variável DESABILITAR_MODO_DEV=true no .env

=============================================================
"""

import os
import firebase_admin
from firebase_admin import auth as firebase_auth
from fastapi        import Header, HTTPException
from typing         import Optional


# ──────────────────────────────────────────────────────────────────────────
#  MODO DEV — agora FECHADO por padrão
# ──────────────────────────────────────────────────────────────────────────
#
# Antes era `os.getenv("DESABILITAR_MODO_DEV", "false") != "true"`: variável
# não definida deixava o modo dev LIGADO. E o render.yaml não listava essa
# variável, então o estado normal do deploy era o inseguro. Nesse modo o
# header X-Dev-User-Id vale como identidade, e qualquer um lê o histórico de
# qualquer usuário trocando o uid.
#
# A regra agora é a inversa: esquecer a variável deixa a API SEGURA. Ligar o
# modo dev exige dizer sim, por escrito, e o kill switch antigo continua
# valendo para quem já o configurou.
MODO_DEV_ATIVO = (
    os.getenv("MODO_DEV", "false").lower() == "true"
    and os.getenv("DESABILITAR_MODO_DEV", "false").lower() != "true"
)

if MODO_DEV_ATIVO:
    print("=" * 66)
    print("  ⚠️  MODO DEV LIGADO — o header X-Dev-User-Id vale como login.")
    print("      Qualquer pessoa pode se passar por qualquer usuário.")
    print("      NUNCA deixe assim em produção: remova MODO_DEV do ambiente.")
    print("=" * 66)


# ──────────────────────────────────────────────────────────────────────────
#  SEGREDO DE ADMINISTRAÇÃO
# ──────────────────────────────────────────────────────────────────────────
#
# Rotas que apagam coisas ou gastam cota paga do Gemini não são para usuário
# nenhum — nem logado. Elas pedem um segredo separado, no header
# X-Admin-Token.
#
# Sem ADMIN_SEGREDO configurado, essas rotas ficam FECHADAS para todo mundo.
# É de propósito: a alternativa seria ficarem abertas quando a variável
# falta, que é exatamente o defeito que o modo dev tinha.
ADMIN_SEGREDO = os.getenv("ADMIN_SEGREDO", "").strip()


def exigir_admin(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> bool:
    """Trava das rotas de administração e de extração de prova."""
    if not ADMIN_SEGREDO:
        raise HTTPException(
            status_code=503,
            detail="Rota de administração desligada: ADMIN_SEGREDO não está "
                   "configurado no servidor.",
        )
    # Comparação em tempo constante: evita descobrir o segredo medindo
    # quanto tempo o servidor leva para recusar.
    import hmac
    if not x_admin_token or not hmac.compare_digest(x_admin_token, ADMIN_SEGREDO):
        raise HTTPException(
            status_code=403,
            detail="Esta rota exige o header X-Admin-Token.",
        )
    return True


def obter_usuario_atual(
    authorization: Optional[str] = Header(default=None),
    x_dev_user_id: Optional[str] = Header(default=None, alias="X-Dev-User-Id"),
) -> dict:
    """
    Identifica o usuário a partir do token JWT do Firebase Auth.

    Caminho 1 (produção):
      Header: Authorization: Bearer <id_token>
      Valida o token contra o Firebase e retorna info do usuário.

    Caminho 2 (dev):
      Header: X-Dev-User-Id: <qualquer-string>
      Retorna esse ID como uid. Útil para testar via Swagger.

    Retorna um dict com:
      {
        "uid":      str,         # ID único do usuário
        "email":    str | None,
        "nome":     str | None,
        "modo":     "auth" | "dev"
      }

    Lança HTTPException 401 se nenhuma das duas vias for válida.
    """

    # ─── Caminho 1 — Firebase Auth (produção) ───
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            decoded = firebase_auth.verify_id_token(token)
            return {
                "uid":   decoded["uid"],
                "email": decoded.get("email"),
                "nome":  decoded.get("name") or decoded.get("display_name"),
                "modo":  "auth",
            }
        except firebase_auth.InvalidIdTokenError:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")
        except firebase_auth.ExpiredIdTokenError:
            raise HTTPException(status_code=401, detail="Token expirado, faça login de novo")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Erro ao validar token: {e}")

    # ─── Caminho 2 — Modo Dev ───
    if MODO_DEV_ATIVO and x_dev_user_id:
        return {
            "uid":   x_dev_user_id,
            "email": None,
            "nome":  f"dev_{x_dev_user_id}",
            "modo":  "dev",
        }

    # ─── Nenhuma autenticação válida ───
    raise HTTPException(
        status_code=401,
        detail={
            "erro": "Não autenticado",
            "como_resolver": [
                "Envie o header 'Authorization: Bearer <id_token_firebase>' (produção)",
                "Ou envie 'X-Dev-User-Id: <qualquer_id>' (modo dev, para testar)",
            ],
        },
    )


def obter_usuario_opcional(
    authorization: Optional[str] = Header(default=None),
    x_dev_user_id: Optional[str] = Header(default=None, alias="X-Dev-User-Id"),
) -> Optional[dict]:
    """
    Versão opcional: retorna usuário se autenticado, senão None.
    Útil para rotas públicas que podem personalizar SE houver login.
    """
    try:
        return obter_usuario_atual(authorization, x_dev_user_id)
    except HTTPException:
        return None
