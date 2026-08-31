"""O teto por IP vale para o servidor inteiro, não para cada worker.

O defeito, encontrado em 24/08/2026 lendo o Dockerfile: o contêiner sobe com
`uvicorn --workers 2`, e os dois contadores do site viviam num dicionário na
memória do processo. Cada worker tinha o seu. Com o balanceamento alternando
entre eles, o limite REAL era o dobro do escrito:

    anti-spam   3 envios por IP  ->  aceitava 6
    login       6 tentativas     ->  aceitava 12

Não aparecia em teste nenhum, porque a suíte roda num processo só. E era
sempre a favor de quem ataca.

Estes testes rodam contadores em PROCESSOS DE VERDADE, com `subprocess`, para
que a garantia não dependa do desenho interno continuar sendo o que é hoje.
"""
import subprocess
import sys
import textwrap

from app.config import settings
from app.services import limite

# Duas chamadas ao mesmo teto, de dois interpretadores diferentes, apontando
# para o mesmo DATA_DIR. É a reprodução mais próxima dos dois workers.
PROGRAMA = textwrap.dedent("""
    import json, os, sys
    sys.path.insert(0, os.environ["RAIZ"])
    from app.services import limite
    respostas = [limite.permitir("teste:ip", 3, 900, 1000.0 + i)
                 for i in range(int(sys.argv[1]))]
    print(json.dumps(respostas))
""")


def _processo(quantas: int) -> list[bool]:
    import json
    import os
    from app.config import BASE_DIR
    ambiente = dict(os.environ, DATA_DIR=str(settings.data_dir),
                    RAIZ=str(BASE_DIR))
    saida = subprocess.run([sys.executable, "-c", PROGRAMA, str(quantas)],
                           capture_output=True, text=True, env=ambiente,
                           cwd=str(BASE_DIR))
    assert saida.returncode == 0, saida.stderr
    return json.loads(saida.stdout)


def test_dois_processos_dividem_o_mesmo_teto():
    """Dois envios num processo e dois no outro dão QUATRO, e o teto é três.
    Antes desta mudança os quatro passavam, porque cada processo contava do
    zero."""
    limite.limpar()
    primeiro = _processo(2)
    segundo = _processo(2)
    assert primeiro == [True, True], primeiro
    assert segundo == [True, False], \
        f"o segundo processo contou do zero: {segundo}"
    assert limite.quantos("teste:ip", 900, 1000.0) == 3


def test_o_contador_sobrevive_ao_reinicio_do_processo():
    """Reiniciar o worker não devolve cota a quem estava bloqueado. Com o
    dicionário em memória, `docker compose restart` zerava o bloqueio."""
    limite.limpar()
    _processo(3)
    assert _processo(1) == [False]


def test_bloqueado_nao_empurra_a_janela_para_frente():
    """Tentativa recusada não é gravada. Se fosse, cada nova tentativa
    esticaria o bloqueio, e quem bate na porta sem parar ficaria preso para
    sempre em vez de pelos 15 minutos combinados."""
    limite.limpar()
    for i in range(3):
        assert limite.permitir("teste:janela", 3, 900, 1000.0 + i)
    for i in range(20):
        assert not limite.permitir("teste:janela", 3, 900, 1010.0 + i)
    assert limite.quantos("teste:janela", 900, 1000.0) == 3
    # e libera quando a janela original passa, não 20 tentativas depois
    assert limite.permitir("teste:janela", 3, 900, 1000.0 + 901)


def test_chaves_diferentes_nao_se_misturam():
    limite.limpar()
    assert limite.permitir("envio:1.1.1.1", 1, 900, 1000.0)
    assert not limite.permitir("envio:1.1.1.1", 1, 900, 1001.0)
    assert limite.permitir("envio:2.2.2.2", 1, 900, 1002.0)
    assert limite.permitir("login:1.1.1.1", 1, 900, 1003.0)


def test_os_dois_limites_do_site_usam_o_contador_compartilhado():
    """Falha se alguém devolver um dicionário em memória para qualquer um dos
    dois — que é como o defeito nasceu e como ele voltaria."""
    from app.config import BASE_DIR
    for caminho in ("app/services/anti_spam.py", "app/auth.py"):
        fonte = (BASE_DIR / caminho).read_text(encoding="utf-8")
        assert "limite." in fonte, caminho
        assert "dict[str, list[float]]" not in fonte, \
            f"{caminho} voltou a contar na memória do processo"
