"""Publicação automática no Instagram via Meta Graph API (conta profissional).

Requer nas Configurações do admin:
  - ig_user_id: ID da conta profissional do Instagram
  - ig_access_token: token de longa duração (Meta for Developers)

Fluxo oficial: cria um container de mídia e depois publica.
A imagem precisa estar acessível publicamente — usamos a URL do site em produção.
"""
import httpx

GRAPH = "https://graph.facebook.com/v21.0"


class InstagramError(Exception):
    pass


async def publish_image(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """Publica uma imagem. Retorna o ID da publicação."""
    if not ig_user_id or not access_token:
        raise InstagramError("Configure o ID da conta e o token do Instagram nas Configurações.")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{GRAPH}/{ig_user_id}/media",
            data={"image_url": image_url, "caption": caption[:2200], "access_token": access_token},
        )
        data = r.json()
        if "id" not in data:
            raise InstagramError(str(data.get("error", data))[:900])
        container_id = data["id"]

        r = await client.post(
            f"{GRAPH}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": access_token},
        )
        data = r.json()
        if "id" not in data:
            raise InstagramError(str(data.get("error", data))[:900])
        return data["id"]


async def fetch_feed(ig_user_id: str, access_token: str, limit: int = 4) -> list[dict]:
    """Últimos posts (imagem/capa) da conta profissional, para o feed da home."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{GRAPH}/{ig_user_id}/media",
            params={"fields": "media_url,thumbnail_url,permalink,media_type",
                    "limit": limit * 2, "access_token": access_token},
        )
        data = r.json().get("data", [])
    feed = []
    for item in data:
        url = item.get("thumbnail_url") or item.get("media_url")
        if url:
            feed.append({"img": url, "link": item.get("permalink", "")})
        if len(feed) >= limit:
            break
    return feed


def build_caption(title: str, subtitle: str, tags: list[str], link: str) -> str:
    parts = [title]
    if subtitle:
        parts.append(subtitle)
    parts.append(f"Case completo: {link}")
    if tags:
        parts.append(" ".join("#" + t.replace("-", "").replace(" ", "") for t in tags[:15]))
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# SAÚDE DO TOKEN
#
# Token de usuário expira em 60 dias e, quando morre, o feed congela e a
# publicação falha sem erro visível. Token de Página derivado de um token de
# usuário de longa duração não expira nunca, e serve para as mesmas chamadas.
# Por isso a estratégia aqui não é renovar periodicamente: é trocar uma vez por
# um token que não vence, e vigiar para o caso de ele ser revogado.
# ---------------------------------------------------------------------------

async def estado_do_token(ig_user_id: str, token: str) -> dict:
    """Diz se o token está de pé, de que tipo é e quando vence."""
    import datetime as dt
    if not (ig_user_id and token):
        return {"ok": False, "erro": "Sem ID da conta ou token."}
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"{GRAPH}/debug_token",
                                 params={"input_token": token, "access_token": token})
            d = r.json().get("data", {})
        except Exception as exc:
            return {"ok": False, "erro": f"Não consegui falar com a Meta: {exc}"}

    if not d.get("is_valid"):
        motivo = (d.get("error") or {}).get("message", "Token inválido ou revogado.")
        return {"ok": False, "erro": motivo}

    exp = d.get("expires_at") or 0
    tipo = d.get("type", "")
    # Cuidado: token de usuário devolve expires_at 0 enquanto o app está em modo
    # Desenvolvimento. Isso não é garantia nenhuma, some no dia que o app for
    # publicado. Só token de Página é permanente de verdade.
    dados = {
        "ok": True,
        "tipo": tipo,
        "permanente": tipo == "PAGE",
        "sem_prazo_agora": not exp,
        "escopos": d.get("scopes", []),
        "checado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if exp:
        vence = dt.datetime.fromtimestamp(exp, dt.timezone.utc)
        dados["expira_em"] = vence.isoformat()
        dados["dias"] = (vence - dt.datetime.now(dt.timezone.utc)).days

    # Prazo separado e menos conhecido: passado ele, a Meta corta o acesso aos dados
    # até a pessoa autorizar de novo, mesmo com o token "válido".
    acesso = d.get("data_access_expires_at") or 0
    if acesso:
        limite = dt.datetime.fromtimestamp(acesso, dt.timezone.utc)
        dados["acesso_expira_em"] = limite.isoformat()
        dados["acesso_dias"] = (limite - dt.datetime.now(dt.timezone.utc)).days
    return dados


async def token_de_pagina(ig_user_id: str, user_token: str) -> tuple[str, str]:
    """Troca o token de usuário pelo token da Página ligada a esta conta.

    Retorna (token, "") em caso de sucesso, ou ("", motivo) quando não dá.
    """
    if not (ig_user_id and user_token):
        return "", "Sem ID da conta ou token."
    async with httpx.AsyncClient(timeout=25) as client:
        try:
            r = await client.get(
                f"{GRAPH}/me/accounts",
                params={"fields": "id,name,access_token,instagram_business_account{id}",
                        "access_token": user_token})
            dados = r.json()
        except Exception as exc:
            return "", f"Não consegui falar com a Meta: {exc}"

    if "data" not in dados:
        return "", str(dados.get("error", dados))[:200]

    for pagina in dados["data"]:
        ig = pagina.get("instagram_business_account") or {}
        if ig.get("id") == ig_user_id and pagina.get("access_token"):
            return pagina["access_token"], ""
    return "", ("Nenhuma Página do Facebook ligada a esta conta do Instagram. "
                "Confira o vínculo nas configurações do Instagram.")


async def garantir_token_permanente(ig_user_id: str, token: str) -> tuple[str, str]:
    """Devolve o melhor token possível: o da Página, que não expira.

    Se o token já for de Página, fica como está. Retorna (token, aviso).
    """
    estado = await estado_do_token(ig_user_id, token)
    if not estado.get("ok"):
        return token, estado.get("erro", "Token inválido.")
    if estado.get("tipo") == "PAGE":
        return token, ""     # já é o permanente de verdade

    novo, erro = await token_de_pagina(ig_user_id, token)
    if not novo:
        return token, erro
    conferido = await estado_do_token(ig_user_id, novo)
    if conferido.get("ok") and conferido.get("permanente"):
        return novo, ""
    return token, "O token da Página veio, mas não passou na conferência."
