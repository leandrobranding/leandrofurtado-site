#!/usr/bin/env bash
# Baixa o backup do site para o Mac.
#
#   ./deploy/baixar-backup.sh IP_DO_VPS
#
# O cron do servidor guarda 7 dias rotativos, mas dentro da própria máquina: se o VPS
# morrer, o backup morre junto. Este script tira a cópia de lá e traz para cá, que é o
# que faz dela um backup de verdade.
#
# Guarda em ~/Backups/leandrofurtado/ e mantém as 30 cópias mais recentes.

set -euo pipefail

IP="${1:-}"
CHAVE="${CHAVE_SSH:-$HOME/.ssh/id_ed25519}"
DESTINO="$HOME/Backups/leandrofurtado"
REMOTO="/opt/leandrofurtado-site"
CARIMBO="$(date +%Y-%m-%d-%H%M)"

if [ -z "$IP" ]; then
  echo "uso: $0 IP_DO_VPS" >&2
  exit 1
fi

mkdir -p "$DESTINO"

echo "Gerando o pacote no servidor..."
ssh -i "$CHAVE" -o StrictHostKeyChecking=accept-new "root@$IP" \
  "tar -czf /tmp/lf-backup.tar.gz -C $REMOTO data && du -h /tmp/lf-backup.tar.gz"

echo "Trazendo para o Mac..."
scp -i "$CHAVE" "root@$IP:/tmp/lf-backup.tar.gz" "$DESTINO/site-$CARIMBO.tar.gz"
ssh -i "$CHAVE" "root@$IP" "rm -f /tmp/lf-backup.tar.gz"

# confere que o arquivo não veio truncado antes de considerar o backup bom
if ! tar -tzf "$DESTINO/site-$CARIMBO.tar.gz" > /dev/null 2>&1; then
  echo "ERRO: o pacote baixado está corrompido. Não apaguei nada." >&2
  exit 1
fi

# mantém as 30 cópias mais recentes
ls -1t "$DESTINO"/site-*.tar.gz 2>/dev/null | tail -n +31 | while read -r velho; do
  rm -f "$velho"
  echo "removido antigo: $(basename "$velho")"
done

echo
echo "Backup ok: $DESTINO/site-$CARIMBO.tar.gz"
echo "Cópias guardadas: $(ls -1 "$DESTINO"/site-*.tar.gz 2>/dev/null | wc -l | tr -d ' ')"
echo
echo "Para restaurar num servidor novo:"
echo "  scp -i $CHAVE $DESTINO/site-$CARIMBO.tar.gz root@NOVO_IP:/tmp/"
echo "  ssh -i $CHAVE root@NOVO_IP 'cd $REMOTO && tar -xzf /tmp/site-$CARIMBO.tar.gz && chown -R 1000:1000 data && docker compose restart'"
