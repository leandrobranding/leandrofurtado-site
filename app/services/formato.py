"""Formatação de moeda e o erro de validação que o admin mostra ao usuário.

Nasceram dentro de `app/nodal/rotas_admin.py`, que é onde foram usados
primeiro. Saíram de lá em 24/08/2026 por um motivo de arquitetura: eram a
ÚNICA razão de `app/main.py` importar do módulo do Nodal, e o site não deve
depender de um produto que roda dentro dele. Com a mudança o Nodal pode ser
removido do projeto sem que o site pare de subir.

Nenhuma regra mudou. `app/nodal/rotas_admin.py` reexporta os dois nomes, então
o código do Nodal continua importando de onde sempre importou.
"""


class ErroDeValidacao(ValueError):
    """Entrada recusada, com mensagem em português pronta pro admin ler."""


def formatar_reais(centavos: int, com_simbolo: bool = True) -> str:
    """Inteiro em centavos para texto em real brasileiro.

    Um lugar só pra regra de moeda — milhar com ponto, decimal com vírgula —
    porque a mesma tela não pode mostrar R$ 197.00 na lista e R$ 197,00 no
    formulário logo abaixo.
    """
    centavos = int(centavos or 0)
    sinal = "-" if centavos < 0 else ""
    inteiro, resto = divmod(abs(centavos), 100)
    milhar = f"{inteiro:,}".replace(",", ".")
    valor = f"{sinal}{milhar},{resto:02d}"
    return f"R$ {valor}" if com_simbolo else valor
