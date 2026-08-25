"""O detector de marca reversa (logos.reversa) — nascido de um caso real.

A Pravaler entrou pelo painel com a palavra em #fffdf1 (branco quente) sobre o
shape laranja, e o detector respondeu False: o regex de branco só reconhecia
branco puro. Sem o rótulo de chapa, o site aplicou o tratamento padrão
(brightness 0 + invert), que pinta palavra e shape da mesma cor — e a marca
virou um retângulo sem letras na fileira de clientes da home, no ar.

Branco de marca quase nunca é #ffffff: exportador entrega #fffdf1, #fefefe,
fundo "off-white" de manual. O detector passa a aceitar quase-branco (todos os
canais ≥ 240), que continua longe de qualquer cinza de desenho.
"""
from pathlib import Path

from app.services.logos import reversa


def _svg(tmp_path: Path, corpo: str) -> Path:
    arquivo = tmp_path / "logo.svg"
    arquivo.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" '
                       f'viewBox="0 0 100 40">{corpo}</svg>')
    return arquivo


def test_branco_puro_sobre_cor_e_reversa(tmp_path):
    assert reversa(_svg(tmp_path, '<path fill="#ffffff" d="M0 0h10v10z"/>'
                                  '<path fill="#ec6607" d="M0 0h99v39z"/>'))


def test_branco_quente_sobre_cor_e_reversa(tmp_path):
    """O caso Pravaler: #fffdf1 é branco para quem olha, e era invisível para
    o regex de branco puro."""
    assert reversa(_svg(tmp_path, '<path style="fill: #fffdf1;" d="M0 0h10v10z"/>'
                                  '<path style="fill: #ec6607;" d="M0 0h99v39z"/>'))


def test_quase_branco_de_verdade_tem_piso(tmp_path):
    """#e0e0e0 é cinza claro, não branco: traço legítimo de desenho. Chamar
    isso de reversa mandaria logotipos cinzentos comuns para o tratamento
    errado."""
    assert not reversa(_svg(tmp_path, '<path fill="#e0e0e0" d="M0 0h10v10z"/>'
                                      '<path fill="#ec6607" d="M0 0h99v39z"/>'))


def test_colorido_sem_branco_nao_e_reversa(tmp_path):
    assert not reversa(_svg(tmp_path, '<path fill="#ec6607" d="M0 0h99v39z"/>'))


def test_monocromatico_com_branco_nao_e_reversa(tmp_path):
    """Branco sobre preto é desenho monocromático, não vazado sobre campo de
    cor — o tratamento padrão resolve."""
    assert not reversa(_svg(tmp_path, '<path fill="#ffffff" d="M0 0h10v10z"/>'
                                      '<path fill="#111111" d="M0 0h99v39z"/>'))
