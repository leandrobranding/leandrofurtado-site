"""O site sobe sem o Nodal, e sem a vitrine dele ligada (24/08/2026).

Duas garantias diferentes, e as duas nasceram no mesmo dia:

1. SEM O MÓDULO. `app/nodal/` pode não existir. A cópia pública do projeto no
   GitHub não leva o produto: ele não foi lançado e o modelo de negócio é do
   dono. Um produto embutido que impede o hospedeiro de subir não é produto
   embutido, é acoplamento.

2. SEM A VITRINE. Com o módulo presente, o painel administrativo do Nodal
   fica ligado (é onde ele é construído) e a vitrine pública fica DESLIGADA
   por padrão. Era o que a branch de produção fazia na prática antes do merge,
   registrando só o router do admin; aqui virou decisão explícita.

Estes testes falham no dia em que alguém reintroduzir a dependência — que é o
tipo de coisa que volta sozinha num import distraído.
"""
import ast
import re
from pathlib import Path

from app.config import BASE_DIR, Settings

APP = BASE_DIR / "app"


def test_o_site_nao_importa_o_nodal_fora_de_um_guarda():
    """Todo `import` do Nodal fora da própria pasta tem que estar protegido:
    dentro de `if TEM_NODAL`, de um `try`, ou dentro de uma função."""
    solto = []
    for arquivo in sorted(APP.rglob("*.py")):
        if "nodal" in arquivo.parts:
            continue
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.Import, ast.ImportFrom)):
                continue
            nomes = [a.name for a in no.names]
            modulo = getattr(no, "module", "") or ""
            if "nodal" not in modulo and not any("nodal" in n for n in nomes):
                continue
            # aceita se estiver indentado (dentro de if/try/função)
            if no.col_offset > 0:
                continue
            solto.append(f"{arquivo.relative_to(BASE_DIR)}:{no.lineno}")
    assert not solto, "import do Nodal no nível do módulo: " + ", ".join(solto)


def test_a_vitrine_publica_nasce_desligada():
    """O padrão vale para quem clona e para o servidor. Ligar é decisão
    explícita, por variável de ambiente, no dia do lançamento."""
    # o PADRÃO da classe, não uma instância: o conftest liga a variável de
    # ambiente para a suíte, e `Settings()` a leria de volta.
    assert Settings.model_fields["nodal_publico"].default is False


def test_o_conftest_liga_a_vitrine_para_a_suite():
    """A suíte é o único lugar onde o produto existe por inteiro. Se alguém
    tirar isto, 6 testes do Nodal passam a pular em silêncio."""
    texto = (BASE_DIR / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert 'os.environ.setdefault("NODAL_PUBLICO", "true")' in texto
    # e antes de qualquer import de `app`, senão a configuração já foi lida
    assert texto.index("NODAL_PUBLICO") < texto.index("from app.database")


def test_os_testes_acoplados_ao_nodal_pulam_por_importabilidade():
    """Quatro arquivos fora de tests/nodal/ importam o módulo. Eles pulam
    quando ele não existe, e religam sozinhos quando ele volta — por
    `importorskip`, nunca por marca fixa que alguém precisa lembrar de tirar."""
    acoplados = ["test_admin_settings.py", "test_pdf_privado_live.py",
                 "test_migrations.py", "test_sitemap.py"]
    for nome in acoplados:
        texto = (BASE_DIR / "tests" / nome).read_text(encoding="utf-8")
        assert 'pytest.importorskip("app.nodal"' in texto, nome
        # a guarda vem ANTES do import, senão a coleta estoura primeiro
        assert texto.index("importorskip") < texto.index("from app.nodal")


def test_formatar_reais_saiu_do_produto_para_os_servicos():
    """Era a única razão de `app/main.py` importar do Nodal."""
    from app.services.formato import ErroDeValidacao, formatar_reais
    assert formatar_reais(19700) == "R$ 197,00"
    assert issubclass(ErroDeValidacao, ValueError)
    principal = (APP / "main.py").read_text(encoding="utf-8")
    assert "from .services.formato import" in principal
    assert "from .nodal.rotas_admin import" not in principal


def test_o_sitemap_nao_anuncia_rota_que_devolve_404():
    """Achado em produção, em 24/08/2026, minutos depois do merge: o sitemap
    listava /nodal enquanto a rota respondia 404. A guarda olhava só para a
    EXISTÊNCIA do módulo, e existir não é estar no ar — quem decide isso é
    `settings.nodal_publico`. Sitemap que aponta para 404 é sinal de site mal
    cuidado para o buscador, e some do índice junto com o resto.
    """
    fonte = (APP / "routers" / "public.py").read_text(encoding="utf-8")
    # as duas guardas (sitemap.xml e /mapa-do-site) checam as DUAS condições
    guardas = re.findall(r"if TEM_NODAL[^\n:]*:", fonte)
    assert guardas, "as guardas do Nodal sumiram de public.py"
    for guarda in guardas:
        assert "settings.nodal_publico" in guarda, \
            f"guarda sem a chave da vitrine: {guarda}"
