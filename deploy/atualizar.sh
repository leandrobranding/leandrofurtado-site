#!/usr/bin/env bash
# Atualiza o site no VPS — SEMPRE com backup antes, e o backup vem para o Mac.
#
#   ./deploy/atualizar.sh SEU.IP.DO.VPS
#
# A ordem não é estética: backup primeiro, deploy depois, e o deploy só começa
# se o backup chegou inteiro aqui. Deploy que sobe antes de copiar é deploy que
# descobre o problema quando não há mais para onde voltar.
#
# Três coisas que este script faz e que o cron do servidor não faz:
#
# 1. O banco é copiado pela API de backup do SQLite, não pelo `cp`. Um SQLite em
#    WAL guarda parte do conteúdo num arquivo `-wal` ao lado, e copiar só o
#    `.db` traz um banco silenciosamente incompleto — isto já aconteceu neste
#    projeto e custou um case inteiro sem ninguém notar.
#
# 2. A cópia é BAIXADA para o Mac. O cron guarda sete dias rotativos dentro da
#    própria máquina que ele deveria proteger: se o VPS morrer, os sete morrem
#    junto.
#
# 3. O tamanho é conferido contra a cópia anterior. Em 11/08/2026 o backup do
#    servidor saiu com 353 KB contra 133 MB dos vizinhos, e nada acusou — os
#    uploads simplesmente não entraram. Encolhimento súbito agora interrompe.
set -euo pipefail

IP="${1:-}"
CHAVE="${CHAVE_SSH:-$HOME/.ssh/id_ed25519}"
REMOTO="/opt/leandrofurtado-site"
DESTINO="$HOME/Backups/leandrofurtado"
LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CARIMBO="$(date +%Y-%m-%d-%H%M)"
ENCOLHIMENTO_ACEITAVEL=70   # % do tamanho da cópia anterior

if [ -z "$IP" ]; then
  echo "uso: $0 IP_DO_VPS" >&2
  exit 1
fi

ssh_() { ssh -i "$CHAVE" -o StrictHostKeyChecking=accept-new "root@$IP" "$@"; }

echo "==> 1/5  Banco consistente no servidor"
# `.backup` da API do SQLite: espera a transação em curso e inclui o WAL. Sem
# isto, o arquivo copiado pode não abrir — ou pior, abrir faltando pedaço.
ssh_ "cd $REMOTO && python3 - <<'PY'
import sqlite3
origem = sqlite3.connect('data/site.db')
copia = sqlite3.connect('/tmp/site-consistente.db')
with copia:
    origem.backup(copia)
copia.close(); origem.close()
print('banco copiado com a API de backup, WAL incluído')
PY"

echo "==> 2/5  Empacotando data/ + banco consistente"
ssh_ "cd $REMOTO && tar -czf /tmp/lf-$CARIMBO.tar.gz data -C /tmp site-consistente.db && du -h /tmp/lf-$CARIMBO.tar.gz"

echo "==> 3/5  Trazendo para o Mac"
mkdir -p "$DESTINO"
scp -i "$CHAVE" "root@$IP:/tmp/lf-$CARIMBO.tar.gz" "$DESTINO/"
ssh_ "rm -f /tmp/lf-$CARIMBO.tar.gz /tmp/site-consistente.db"

ARQUIVO="$DESTINO/lf-$CARIMBO.tar.gz"
TAM=$(wc -c < "$ARQUIVO")
echo "    $ARQUIVO — $(du -h "$ARQUIVO" | cut -f1)"

# O backup precisa ABRIR, não só existir: arquivo truncado tem tamanho e não
# tem conteúdo, e a descoberta disso no dia da restauração é tarde demais.
tar -tzf "$ARQUIVO" > /dev/null || { echo "ERRO: o pacote não abre. Deploy cancelado." >&2; exit 1; }

ANTERIOR=$(ls -t "$DESTINO"/lf-*.tar.gz 2>/dev/null | sed -n 2p || true)
if [ -n "$ANTERIOR" ]; then
  TAM_ANT=$(wc -c < "$ANTERIOR")
  MINIMO=$(( TAM_ANT * ENCOLHIMENTO_ACEITAVEL / 100 ))
  if [ "$TAM" -lt "$MINIMO" ]; then
    echo "ERRO: o backup encolheu de $(du -h "$ANTERIOR" | cut -f1) para $(du -h "$ARQUIVO" | cut -f1)." >&2
    echo "      Foi assim que a cópia de 11/08 saiu com 353 KB sem ninguém notar." >&2
    echo "      Deploy cancelado. Confira antes de insistir." >&2
    exit 1
  fi
fi

# Rotação (pedido de 19/08): só os 2 backups mais novos ficam — o recém
# verificado (abriu E não encolheu) e um anterior de segurança. Sem isto o
# disco do Mac enche até alguém notar (encheu: 10,6 GB apagados à mão).
# A rotação SÓ roda depois das duas verificações acima passarem — um backup
# suspeito cancela o deploy antes de qualquer apagamento.
ls -t "$DESTINO"/lf-*.tar.gz 2>/dev/null | tail -n +3 | while read -r VELHO; do
  rm -f "$VELHO"
  echo "    rotação: apagado $(basename "$VELHO")"
done

# 30 cópias: com um deploy por dia é um mês de histórico, e a 348 MB por cópia
# cabe folgado no Mac. Apaga as mais velhas, nunca a recém-criada.
ls -t "$DESTINO"/lf-*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm --

echo "==> 4/5  Enviando o código (data/ e .env ficam de fora)"
rsync -az --delete --timeout=60 \
  --exclude '.venv' --exclude 'data' --exclude '.git' --exclude '.superpowers' \
  --exclude '.env' \
  --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.DS_Store' \
  -e "ssh -i $CHAVE" "$LOCAL/" "root@$IP:$REMOTO/"

echo "==> 5/5  Reconstruindo e conferindo"
ssh_ "cd $REMOTO && docker compose up -d --build"

for tentativa in 1 2 3 4 5 6 7 8 9 10; do
  sleep 3
  CODIGO=$(curl -s -o /dev/null -w '%{http_code}' "https://leandrofurtado.com.br/" || echo "000")
  [ "$CODIGO" = "200" ] && { echo "    site respondendo 200"; exit 0; }
  echo "    tentativa $tentativa: $CODIGO"
done

echo "ERRO: o site não voltou a responder 200. Últimas linhas do log:" >&2
ssh_ "cd $REMOTO && docker compose logs --tail 40 web" >&2
echo "Para voltar atrás: o backup desta execução está em $ARQUIVO" >&2
exit 1
