#!/usr/bin/env bash
# Backup que roda NO servidor, pelo cron, como root.
#
# Instalar:  scp deploy/backup-servidor.sh root@IP:/root/backup-servidor.sh
#            ssh root@IP "chmod +x /root/backup-servidor.sh"
# Cron:      0 4 * * * /root/backup-servidor.sh >> /var/log/backup-site.log 2>&1
#
# ----------------------------------------------------------------------------
# Por que este script existe (22/08/2026)
#
# O cron antigo era uma linha só:
#
#     0 4 * * * tar -czf /root/backup-site-$(date +%u).tar.gz -C /opt/... data
#
# Ele tinha três problemas, e o terceiro era o caro:
#
# 1. Copiava o `site.db` com `tar`, no meio da operação do site. Um SQLite em
#    WAL guarda parte do conteúdo no `-wal` ao lado; um `tar` não é atômico e
#    pode pegar os dois em instantes diferentes. Aqui o banco sai pela API de
#    backup do SQLite, que espera a transação em curso e resolve o WAL.
#
# 2. Guardava SETE cópias completas rotativas (`$(date +%u)` = dia da semana).
#    Com 1,3 GB de mídia isso eram 7,2 GB parados no disco de 48 GB — e o
#    Leandro ainda vai cadastrar muita coisa. A conta piora sozinha: cada 1 GB
#    de mídia nova custava 7 GB.
#
# 3. Recomprimia 1,3 GB de mídia TODA NOITE num servidor de 1 vCPU, para
#    guardar sete vezes o mesmo arquivo que quase nunca muda.
#
# A troca: o banco (~700 KB, onde está toda a mudança real — cases, clientes,
# leads, ajustes) passa a ser copiado todo dia, com sete dias de histórico por
# ~5 MB. A mídia, que é grande e estável, ganha UMA cópia completa, refeita aos
# domingos e sobrescrita.
#
# Cópia de verdade continua sendo a que sai da máquina: ver deploy/atualizar.sh
# e deploy/baixar-backup.sh, que trazem o pacote para o Mac.
# ----------------------------------------------------------------------------
set -euo pipefail

RAIZ=/opt/leandrofurtado-site
DESTINO=/root/backups
DIA=$(date +%u)          # 1 (segunda) .. 7 (domingo)

mkdir -p "$DESTINO"

# ---------- todo dia: o banco ------------------------------------------------
DIA="$DIA" python3 - <<'PY'
import os, sqlite3
dia = os.environ["DIA"]
origem = sqlite3.connect("/opt/leandrofurtado-site/data/site.db")
copia = sqlite3.connect(f"/root/backups/banco-{dia}.db")
with copia:
    origem.backup(copia)
copia.close()
origem.close()
PY
gzip -f "$DESTINO/banco-$DIA.db"
echo "$(date '+%F %T')  banco-$DIA.db.gz  $(du -h "$DESTINO/banco-$DIA.db.gz" | cut -f1)"

# ---------- domingo: uma cópia completa, sobrescrita -------------------------
# Escreve num nome temporário e só então substitui: se o tar falhar no meio
# (disco cheio, queda), a cópia boa da semana passada continua de pé em vez de
# virar um arquivo truncado com cara de backup.
# O que NÃO entra na cópia completa, e por quê (medido em 24/08/2026, quando
# o arquivo chegou a 1,2 GB):
#
#   data/geo               125 MB de base de geolocalização (DB-IP Lite), que
#                          o deploy baixa sozinho. Guardar cópia de algo que
#                          se rebaixa é gastar 10% do backup com nada.
#   data/*.db-wal, -shm    diário do SQLite. O banco já sai daqui pela API de
#                          backup, atômico e íntegro; copiar o WAL junto só
#                          traz um estado parcial que ninguém vai usar.
#   data/site.db.antes-*   cópias manuais soltas de antes de alguma mudança.
#
# O RESTO FICA, e é a maior parte: 685 MB de vídeo e 358 MB de foto originais.
# Não são regeneráveis, e são o trabalho de dez anos. O backup é grande porque
# o acervo é grande, e isso está certo.
if [ "$DIA" = "7" ]; then
  tar -czf "$DESTINO/completo.tar.gz.parcial" -C "$RAIZ" \
    --exclude='data/geo' \
    --exclude='data/*.db-wal' \
    --exclude='data/*.db-shm' \
    --exclude='data/site.db.antes-*' \
    data
  tar -tzf "$DESTINO/completo.tar.gz.parcial" > /dev/null
  mv -f "$DESTINO/completo.tar.gz.parcial" "$DESTINO/completo.tar.gz"
  echo "$(date '+%F %T')  completo.tar.gz  $(du -h "$DESTINO/completo.tar.gz" | cut -f1)"
fi

# ---------- aviso de disco ---------------------------------------------------
# O disco encher em silêncio derruba o site inteiro, e o primeiro sintoma seria
# o SQLite falhando a escrita. 85% é cedo o bastante para dar tempo de agir.
USO=$(df --output=pcent / | tail -1 | tr -dc '0-9')
if [ "$USO" -ge 85 ]; then
  echo "$(date '+%F %T')  ATENÇÃO: disco em ${USO}%. Hora de limpar mídia antiga ou os backups."
fi
