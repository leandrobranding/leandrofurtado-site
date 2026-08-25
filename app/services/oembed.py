"""Transforma URLs coladas no admin em embeds ricos.

Suporta: posts e reels do Instagram, YouTube, Vimeo, e qualquer matéria/link
da web (vira um cartão rico com OG title/imagem/descrição).
"""
import html
import re

import httpx

UA = {"User-Agent": "Mozilla/5.0 (compatible; LFPortfolio/1.0; +https://leandrofurtado.com.br)"}

IG_RE = re.compile(r"instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_\-]+)")
YT_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_\-]{6,})")
VIMEO_RE = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


async def resolve_embed(url: str) -> dict:
    """Retorna meta dict: {provider, embed_url | og fields}."""
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("URL inválida")

    if m := IG_RE.search(url):
        code = m.group(1)
        kind = "reel" if "/reel" in url else "p"
        return {
            "provider": "instagram",
            "ig_kind": kind,
            "embed_url": f"https://www.instagram.com/{'reel' if kind == 'reel' else 'p'}/{code}/embed/",
            "url": url,
        }
    if m := YT_RE.search(url):
        return {
            "provider": "youtube",
            "embed_url": f"https://www.youtube-nocookie.com/embed/{m.group(1)}",
            "url": url,
        }
    if m := VIMEO_RE.search(url):
        return {
            "provider": "vimeo",
            "embed_url": f"https://player.vimeo.com/video/{m.group(1)}",
            "url": url,
        }

    # Matéria / link genérico → cartão rico com metadados OG
    meta = {"provider": "article", "url": url, "title": url, "description": "", "image": "", "site": ""}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers=UA) as client:
            resp = await client.get(url)
            text = resp.text[:400_000]
        for prop, key in (("og:title", "title"), ("og:description", "description"),
                          ("og:image", "image"), ("og:site_name", "site")):
            m = re.search(
                rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']', text
            ) or re.search(
                rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']', text
            )
            if m:
                meta[key] = html.unescape(m.group(1)).strip()
        if meta["title"] == url:
            if t := re.search(r"<title[^>]*>(.*?)</title>", text, re.S):
                meta["title"] = html.unescape(t.group(1)).strip()[:200]
    except Exception:
        pass  # sem rede/site fora do ar: o cartão mostra a URL mesmo
    return meta
