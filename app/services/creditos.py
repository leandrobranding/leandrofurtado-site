"""Liga a experiência profissional aos cases feitos em cada lugar.

O currículo diz "iOn live, Mar 2024 a Fev 2026" e o portfólio diz "Junte Seus
Heróis Marvel, 2024". São a mesma história contada em duas páginas que nunca se
falavam: quem lê o currículo não vê o trabalho, e quem vê o trabalho não sabe por
onde ele passou.

O elo já existe escrito, na ficha técnica do case. Agência não é campo de
cadastro, é crédito: o mesmo cliente aparece por casas diferentes ao longo de uma
carreira, e é a ficha que registra isso. Então em vez de criar mais um campo no
formulário, este módulo lê a linha que já está lá e cruza com as empresas do
currículo.

Regra do cruzamento: o valor da linha de crédito, sem acento e sem caixa, tem que
bater com o nome da empresa na experiência. "iOn live" e "iON Live" são a mesma
casa; "Ion" e "iOn live" não são, e é melhor não ligar do que ligar errado.
"""

from __future__ import annotations



# rótulos de ficha técnica que significam "a casa por onde este trabalho passou"
ROTULOS = {"agencia", "agency", "estudio", "studio", "produtora", "casa"}


def chave(texto: str) -> str:
    """Nome comparável, na mesma forma que vira endereço.

    É o `slugify` do site de propósito: assim "iOn live", "iON Live" e o
    "ion-live" que chega pela querystring são a mesma chave, e o filtro do
    portfólio compara exatamente o que o link escreveu.
    """
    from .images import slugify

    return slugify(str(texto or ""))


def agencia_do_case(case) -> str:
    """O crédito de agência escrito na ficha técnica. String vazia se não houver."""
    for bloco in case.media or []:
        if bloco.kind != "ficha":
            continue
        for linha in (bloco.meta or {}).get("linhas") or []:
            if chave(linha.get("rotulo")) in ROTULOS:
                valor = str(linha.get("valor") or "").strip()
                if valor:
                    return valor
    return ""


def empresas(db) -> list[dict]:
    """As casas do currículo, na ordem em que ele as conta."""
    from ..models import Profile

    perfil = db.get(Profile, 1)
    dados = (perfil.data if perfil else None) or {}
    saida = []
    for xp in dados.get("experience") or []:
        nome = str(xp.get("company") or "").strip()
        if nome:
            saida.append({"nome": nome, "chave": chave(nome), "periodo": xp.get("period") or ""})
    return saida


def cases_por_empresa(db) -> dict[str, list]:
    """Chave da empresa -> cases publicados creditados a ela.

    Só entram empresas que estão no currículo. Crédito a uma casa por onde ele
    não passou como profissional (uma parceira, um fornecedor) continua aparecendo
    na ficha do case, mas não vira link de carreira.
    """
    from ..routers.public import published_cases

    conhecidas = {e["chave"] for e in empresas(db)}
    mapa: dict[str, list] = {}
    for case in published_cases(db).all():
        k = chave(agencia_do_case(case))
        if k and k in conhecidas:
            mapa.setdefault(k, []).append(case)
    return mapa


def contagem(db) -> dict[str, int]:
    """Quantos cases publicados cada casa do currículo tem. Para os selos."""
    return {k: len(v) for k, v in cases_por_empresa(db).items()}
