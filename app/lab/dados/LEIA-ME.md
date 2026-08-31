# O material colhido do site do cliente

Este diretório guarda o que foi **colhido de um site real**, do jeito que ele
estava no dia da colheita. Ele não é código e não é configuração: é a FONTE
que prova que a peça não inventou nada.

`grupoom-cases.json` são os dezoito cases que `grupoom.com.br` publicava em
26/08/2026, cada um com título, empresa que assina, categoria, data, imagem e
o texto real.

## Por que ele mora aqui, e não no rascunho da tarefa

Porque um teste depende dele. `tests/test_redesign_grupoom.py` não confere o
módulo Python contra o próprio módulo Python: ele abre este arquivo e compara.
É a única forma de "nada é inventado" virar uma regra que a máquina confere,
em vez de uma promessa no comentário.

Enquanto ele viveu no diretório de trabalho da tarefa, que é ignorado pelo
git, a suíte passava na máquina de quem colheu e quebrava em qualquer
checkout limpo. Foi assim que a fusão para a `main` reprovou.

## Regra

Quem mexer nos dados de um case mexe aqui primeiro, e só então no módulo.
O contrário deixa o teste verde por acidente.
