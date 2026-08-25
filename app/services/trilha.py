"""Breadcrumb do painel: onde estou, agora.

Um caminho legível montado do endereço, para o header dizer em toda tela em que
parte do admin a pessoa está e permitir voltar um nível sem procurar. Sai daqui
e não de cada template porque é a mesma pergunta em todas as telas, e repetir a
resposta em vinte arquivos é como um deles fica desatualizado.
"""

from __future__ import annotations

# raiz de cada área: o primeiro degrau depois do Dashboard
AREAS = {
    "cases": ("Central de cases", "/admin/cases"),
    "newsletter": ("Central de e-mail", "/admin/newsletter"),
    "avisos": ("Notificações", "/admin/avisos"),
    "brands": ("Marcas & Clientes", "/admin/brands"),
    "linkedin": ("LinkedIn", "/admin/linkedin"),
    "profile": ("Perfil & CV", "/admin/profile"),
    "leads": ("Leads & Clientes", "/admin/leads"),
    "messages": ("Mensagens", "/admin/messages"),
    "seguranca": ("Segurança", "/admin/seguranca"),
    "settings": ("Configurações", "/admin/settings"),
}

# segundo degrau, por área
FOLHAS = {
    "cases": {
        "lista": "Cases", "new": "Novo case", "insights": "Números",
        "comentarios": "Comentários", "categorias": "Categorias",
    },
    "newsletter": {
        "nova": "Nova newsletter", "campanhas": "Campanhas", "leads": "Contatos",
        "temas": "Temas", "config": "Configurações", "preview": "Prévia",
    },
}


def montar(caminho: str, titulo_extra: str = "") -> list[dict]:
    """[{nome, url, atual}] do Dashboard até onde a pessoa está."""
    partes = [p for p in caminho.strip("/").split("/") if p]
    trilha = [{"nome": "Dashboard", "url": "/admin", "atual": len(partes) <= 1}]
    if len(partes) <= 1:
        return trilha

    area = partes[1]
    nome, url = AREAS.get(area, (area.replace("-", " ").title(), f"/admin/{area}"))
    trilha.append({"nome": nome, "url": url, "atual": len(partes) == 2})

    if len(partes) > 2:
        chave = partes[2]
        # id numérico: o título do que está aberto vale mais que o número
        rotulo = FOLHAS.get(area, {}).get(chave)
        if not rotulo:
            rotulo = titulo_extra or (chave if not chave.isdigit() else "Editar")
        trilha.append({"nome": rotulo, "url": caminho, "atual": True})
        trilha[-2]["atual"] = False
    return trilha
