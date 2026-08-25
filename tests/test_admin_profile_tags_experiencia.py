"""Fast-follow do pacote de lançamento (19/08): achado da revisão em
app/routers/admin.py — profile_save reconstruía data["experience"] só com os
6 campos do formulário. Não havia campo de tags no admin, e o zip() não fazia
merge: o PRIMEIRO salvamento qualquer do Admin → Perfil (trocar um e-mail,
por exemplo) apagava xp.tags de TODAS as experiências em silêncio.

Antes disso era inofensivo — tags só apareciam no antigo /cv, que ninguém
editava por ali. Agora elas aparecem na timeline de /about, a página que o
Leandro vai mandar para empresas — apagar em silêncio deixou de ser
aceitável.

Correção escolhida: (a) o form ganhou um campo `exp_tags` por experiência
(texto separado por vírgula, mesmo padrão de `skill_items`), e o save lê e
grava esse campo. zip_longest (não zip) garante que a ausência do campo
nunca trunca as OUTRAS colunas da experiência.
"""
import asyncio

from app.models import Profile
from app.routers.admin import profile_save

from ._multipart_de_verdade import post_multipart

EXPERIENCIA_COM_TAGS = {
    "company": "Gosh", "role_pt": "Diretor de Arte Sênior", "role_en": "Senior Art Director",
    "period": "Mar 2026 — Ago 2026", "desc_pt": "", "desc_en": "",
    "tags": ["Key Visual", "IA Generativa", "Direção de Arte"],
}


def _campos_do_form(email: str, tags: str) -> dict:
    """Simula o que o próprio admin/profile.html manda: o campo de tags vem
    preenchido com o que já está salvo (o form é servido pré-preenchido),
    não vazio — é assim que um resave "sem mexer em nada" se parece de
    verdade num navegador."""
    return {
        "csrf": "teste-csrf",
        "name": "Leandro Furtado", "email": email,
        "title_pt": "", "title_en": "", "location_pt": "", "location_en": "",
        "summary_pt": "", "summary_en": "", "highlight_pt": "", "highlight_en": "",
        "link_linkedin": "", "link_instagram": "", "link_whatsapp": "",
        "exp_company": EXPERIENCIA_COM_TAGS["company"],
        "exp_role_pt": EXPERIENCIA_COM_TAGS["role_pt"],
        "exp_role_en": EXPERIENCIA_COM_TAGS["role_en"],
        "exp_period": EXPERIENCIA_COM_TAGS["period"],
        "exp_desc_pt": "", "exp_desc_en": "",
        "exp_tags": tags,
        "clients": "",
    }


def _seed_profile(db) -> None:
    db.add(Profile(id=1, data={
        "name": "Leandro Furtado", "email": "contatoleandrofurtado@gmail.com",
        "experience": [dict(EXPERIENCIA_COM_TAGS)],
    }))
    db.commit()


def test_resave_identico_preserva_as_tags_da_experiencia(db):
    """Reproduz o cenário do revisor: salvar de novo sem mudar nada não pode
    apagar as tags."""
    _seed_profile(db)
    request = post_multipart(
        "/admin/profile",
        _campos_do_form("contatoleandrofurtado@gmail.com", "Key Visual, IA Generativa, Direção de Arte"),
        {},
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert prof.data["experience"][0]["tags"] == ["Key Visual", "IA Generativa", "Direção de Arte"]


def test_trocar_so_o_email_preserva_as_tags(db):
    """A formulação exata do achado: "o PRIMEIRO salvamento qualquer... trocar
    um e-mail... apaga xp.tags"."""
    _seed_profile(db)
    request = post_multipart(
        "/admin/profile",
        _campos_do_form("novo-email@example.com", "Key Visual, IA Generativa, Direção de Arte"),
        {},
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert prof.data["email"] == "novo-email@example.com"
    assert prof.data["experience"][0]["tags"] == ["Key Visual", "IA Generativa", "Direção de Arte"]


def test_campo_de_tags_vazio_zera_as_tags_por_escolha_do_admin(db):
    """O oposto também precisa funcionar: se o Leandro apagar o campo de
    tags de propósito e salvar, o save respeita — não é bug esconder tags
    que ele mandou remover."""
    _seed_profile(db)
    request = post_multipart(
        "/admin/profile",
        _campos_do_form("contatoleandrofurtado@gmail.com", ""),
        {},
    )
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert prof.data["experience"][0]["tags"] == []


def test_form_sem_o_campo_exp_tags_nao_trunca_as_outras_colunas(db):
    """Guarda contra a causa raiz do achado: um formulário (em cache, ou de
    algum outro cliente da rota) que não manda exp_tags nenhum não pode
    truncar as demais colunas da experiência — zip() cru faria isso porque
    a lista de tags ficaria vazia e mais curta que as outras."""
    _seed_profile(db)
    campos = _campos_do_form("contatoleandrofurtado@gmail.com", "")
    del campos["exp_tags"]
    request = post_multipart("/admin/profile", campos, {})
    asyncio.run(profile_save(request, db, None))

    prof = db.get(Profile, 1)
    assert len(prof.data["experience"]) == 1
    assert prof.data["experience"][0]["company"] == "Gosh"
    assert prof.data["experience"][0]["tags"] == []
