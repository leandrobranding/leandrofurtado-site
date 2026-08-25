#!/usr/bin/env bash
# Deploy completo do leandrofurtado.com.br num VPS Ubuntu 24.04 limpo.
#
#   ./deploy/subir.sh IP_DO_VPS
#
# Roda do Mac. É idempotente: pode rodar de novo à vontade que ele só refaz o que falta.
# Faz tudo menos o que depende de painel de terceiro (contratar o VPS e apontar o DNS).

set -euo pipefail

IP="${1:-}"
DOMINIO="leandrofurtado.com.br"
CHAVE="${CHAVE_SSH:-$HOME/.ssh/id_ed25519}"
LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTO="/opt/leandrofurtado-site"

if [ -z "$IP" ]; then
  echo "uso: $0 IP_DO_VPS" >&2
  exit 1
fi

# Opções de conexão em um lugar só.
#
# `ServerAliveInterval` existe porque o deploy caiu duas vezes no mesmo padrão:
# comando curto passa, operação longa morre. Instalar pacote e enviar código são
# justamente os trechos em que a conexão fica minutos sem tráfego de volta, e aí
# algum equipamento no caminho a derruba por ociosidade. O keepalive mantém a
# sessão viva; `ServerAliveCountMax` derruba de vez só depois de 60s sem resposta,
# em vez de esperar o timeout do sistema.
#
# `ControlMaster` é o que faz o deploy inteiro caber numa conexão só. O script
# abre uma por passo, e a queda que atrapalhou por horas acontecia justo em
# conexões novas abertas em sequência: um SSH manual passava, o passo seguinte
# do script morria. Multiplexando, tudo passa pelo túnel já aberto e não há
# rajada de conexões nova nenhuma para limitador de taxa reagir.
SOQUETE="${TMPDIR:-/tmp}/lf-deploy-%r@%h:%p"
SSH_OPTS=(-i "$CHAVE" -o StrictHostKeyChecking=accept-new
          -o ServerAliveInterval=15 -o ServerAliveCountMax=4
          -o ConnectTimeout=25 -o TCPKeepAlive=yes
          -o ControlMaster=auto -o "ControlPath=$SOQUETE" -o ControlPersist=180)

# fecha o túnel ao terminar, com erro ou sem
encerrar_tunel() { ssh -O exit -o "ControlPath=$SOQUETE" "root@$IP" 2>/dev/null || true; }
trap encerrar_tunel EXIT

ssh_() { ssh "${SSH_OPTS[@]}" "root@$IP" "$@"; }

# ---------------------------------------------------------------------------
# Progresso visível para quem estiver no site durante o deploy
#
# O container reinicia no passo 3 e o site fica alguns segundos fora. Quem
# entrasse nesse instante via a tela de erro do nginx. Agora vê a tela de
# atualização, e ela mostra em que etapa o deploy está: cada `titulo` daqui
# escreve uma linha em /var/www/lf-manutencao/estado.json, que o nginx serve do
# disco enquanto a aplicação não responde.
#
# Escrever é melhor esforço: um deploy não pode falhar porque não conseguiu
# contar o que estava fazendo.
# ---------------------------------------------------------------------------
ETAPAS_TOTAL=12
ETAPA_N=0
DEPLOY_INICIO="$(date +%s)"
PAINEL="/var/www/lf-manutencao"
# preenchidos pelo passo 2, com o que o rsync de fato transferiu
DEPLOY_ARQUIVOS=0
DEPLOY_BYTES=0

# O tempo é contado no servidor e enviado pronto. A tela não pode calcular
# "agora menos início": o relógio de quem visita não é o mesmo do servidor, e o
# número que aparecia era o tempo que a página estava aberta, não o tempo do
# deploy. `decorrido` é a única medida honesta, e a tela interpola daí.
marco() {
  ETAPA_N=$((ETAPA_N + 1))
  local nome="$1" nome_en="${2:-}" detalhe="${3:-}" fim="${4:-0}"
  local agora decorrido
  agora="$(date +%s)"
  decorrido=$((agora - DEPLOY_INICIO))
  ssh_ "mkdir -p $PAINEL && cat > $PAINEL/estado.json <<'JSON'
{\"etapa\": \"$nome\", \"etapa_en\": \"$nome_en\", \"detalhe\": \"$detalhe\",
 \"indice\": $ETAPA_N, \"total\": $ETAPAS_TOTAL,
 \"decorrido\": $decorrido, \"carimbo\": $agora, \"fim\": $fim,
 \"arquivos\": $DEPLOY_ARQUIVOS, \"bytes\": $DEPLOY_BYTES}
JSON
chmod a+r $PAINEL/estado.json" >/dev/null 2>&1 || true
}

# O arquivo não é apagado: apagar deixava quem estivesse com a tela aberta sem
# nada para ler bem no fim, e a barra voltava a "conectando" no melhor momento.
# Ele passa a valer como concluído, e a própria tela o ignora quando envelhece —
# assim uma queda que não é deploy não herda o placar do deploy anterior.
marcar_fim() {
  ETAPA_N=$((ETAPAS_TOTAL - 1))
  marco "Concluído" "Done" "" "$(date +%s)"
}

titulo() { printf '\n\033[1m== %s\033[0m\n' "$1"; marco "$1" "${2:-}" "${3:-}"; }

titulo "0. Conferindo acesso e DNS" "Checking access and DNS"
ssh_ "echo conectado em \$(hostname)"

# Resolvedor público, não o do provedor de internet: cache local mente por horas.
resolver() { dig @1.1.1.1 +short "$2" "$1" 2>/dev/null | grep -v '^;' | tail -1; }

IPV6_VPS="$(ssh_ "ip -6 addr show scope global | sed -n 's/.*inet6 \([^/]*\).*/\1/p' | head -1" | tr -d '\r')"
DNS_A="$(resolver "$DOMINIO" A)"
DNS_AAAA="$(resolver "$DOMINIO" AAAA)"
DNS_OK=1

if [ "$DNS_A" != "$IP" ]; then
  echo "AVISO: registro A de $DOMINIO aponta para '${DNS_A:-nada}', não para $IP."
  DNS_OK=0
else
  echo "A ok: $DOMINIO -> $IP"
fi

# O Let's Encrypt prefere IPv6 quando existe AAAA. Um AAAA apontando para outro lugar
# faz o desafio bater no servidor errado e o certificado ser recusado, mesmo com o A certo.
if [ -n "$DNS_AAAA" ] && [ "$DNS_AAAA" != "$IPV6_VPS" ]; then
  echo "AVISO: registro AAAA aponta para '$DNS_AAAA', mas o VPS é '$IPV6_VPS'."
  echo "       O Let's Encrypt prefere IPv6: corrija ou apague o AAAA de @ e www."
  DNS_OK=0
elif [ -n "$DNS_AAAA" ]; then
  echo "AAAA ok: $DOMINIO -> $IPV6_VPS"
fi

[ "$DNS_OK" = 0 ] && echo "Sigo com o deploy e paro antes do certbot."

titulo "1. Sistema, firewall e fail2ban" "System and firewall"
ssh_ 'export DEBIAN_FRONTEND=noninteractive
      apt-get update -qq && apt-get upgrade -y -qq
      apt-get install -y -qq nginx certbot python3-certbot-nginx git ufw fail2ban rsync
      command -v docker >/dev/null || apt-get install -y -qq docker.io docker-compose-v2
      ufw --force default deny incoming
      ufw --force default allow outgoing
      ufw allow OpenSSH
      ufw allow "Nginx Full"
      ufw --force enable
      systemctl enable --now fail2ban
      echo "sistema pronto"'

titulo "2. Enviando o código" "Uploading the code"
# `--partial` guarda o que já subiu, para uma queda no meio não recomeçar do
# zero. Três tentativas porque a queda aqui é de rede, e rede volta.
RELATORIO="${TMPDIR:-/tmp}/lf-rsync-$$.txt"
enviar() {
  rsync -az --delete --partial --timeout=60 --stats \
    --exclude '.venv' --exclude 'data' --exclude '.git' --exclude '__pycache__' \
    --exclude '.DS_Store' --exclude '.claude' \
    -e "ssh ${SSH_OPTS[*]}" \
    "$LOCAL/" "root@$IP:$REMOTO/" | tee "$RELATORIO"
}
tentativa=1
until enviar; do
  tentativa=$((tentativa + 1))
  if [ "$tentativa" -gt 3 ]; then
    echo "não consegui enviar o código depois de 3 tentativas" >&2
    exit 1
  fi
  echo "conexão caiu, tentando de novo ($tentativa/3)..." >&2
  sleep 10
done
# o que subiu, em número: é isto que a tela de atualização mostra para quem
# estiver no site nesse instante
if [ -f "$RELATORIO" ]; then
  # o rsync da Apple (openrsync) escreve "Number of files transferred"; o GNU
  # escreve "Number of regular files transferred". O padrão aceita os dois.
  DEPLOY_ARQUIVOS="$(sed -n 's/^Number of \(regular \)\{0,1\}files transferred: *\([0-9,]*\).*/\2/p' "$RELATORIO" | tr -d ',' | head -1)"
  DEPLOY_BYTES="$(sed -n 's/^Total transferred file size: *\([0-9,]*\).*/\1/p' "$RELATORIO" | tr -d ',' | head -1)"
  rm -f "$RELATORIO"
fi
DEPLOY_ARQUIVOS="${DEPLOY_ARQUIVOS:-0}"
DEPLOY_BYTES="${DEPLOY_BYTES:-0}"
echo "código enviado ($DEPLOY_ARQUIVOS arquivos, $DEPLOY_BYTES bytes)"

# Entra ANTES do passo 3, que é onde o container reinicia e o site sai do ar.
# Instalar a tela depois da queda seria instalar um extintor depois do incêndio.
titulo "2.5 Tela de atualização" "Preparing the update screen"
ssh_ "mkdir -p $PAINEL
      cp $REMOTO/deploy/manutencao/atualizando.html $PAINEL/_atualizando.html
      cp $REMOTO/app/static/fonts/SpaceGrotesk.woff2 $PAINEL/
      cp $REMOTO/app/static/fonts/Montserrat.woff2 $PAINEL/
      chmod -R a+r $PAINEL
      # a config com o error_page só pode entrar se o certificado já existe,
      # senão o nginx -t falha e derruba a config que está funcionando
      if [ -f /etc/letsencrypt/live/$DOMINIO/fullchain.pem ]; then
        cp /etc/nginx/sites-available/$DOMINIO /tmp/nginx-anterior.conf 2>/dev/null || true
        cp $REMOTO/deploy/nginx.conf /etc/nginx/sites-available/$DOMINIO
        if nginx -t 2>/dev/null; then
          systemctl reload nginx && echo 'tela de atualização armada'
        else
          echo 'AVISO: nginx -t recusou a config nova; voltando para a anterior' >&2
          cp /tmp/nginx-anterior.conf /etc/nginx/sites-available/$DOMINIO 2>/dev/null || true
          nginx -t
        fi
      else
        echo 'sem certificado ainda: a tela entra no passo 6'
      fi"

titulo "3. Subindo a aplicação" "Restarting the application"
# uid 1000 = appuser do container; sem isso ele não grava o SQLite
ssh_ "cd $REMOTO && mkdir -p data && chown -R 1000:1000 data && docker compose up -d --build"
echo "aguardando o container responder..."
for i in $(seq 1 30); do
  if ssh_ "curl -fsS -o /dev/null http://127.0.0.1:8000" 2>/dev/null; then
    echo "aplicação de pé"
    break
  fi
  if [ "$i" = 30 ]; then
    echo "ERRO: a aplicação não respondeu. Últimas linhas do log:" >&2
    ssh_ "cd $REMOTO && docker compose logs --tail 40 web" >&2
    exit 1
  fi
  sleep 2
done

# O nginx.conf final aponta para certificados que só existem depois do certbot, então
# `nginx -t` falharia se ele entrasse agora. A ordem correta é: config só de HTTP →
# emitir certificado → instalar a config definitiva.
titulo "4. Nginx (provisório, só HTTP)" "Web server"
ssh_ "cat > /etc/nginx/sites-available/$DOMINIO <<'CONF'
server {
    listen 80;
    listen [::]:80;
    server_name $DOMINIO www.$DOMINIO;
    client_max_body_size 320M;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
CONF
      ln -sf /etc/nginx/sites-available/$DOMINIO /etc/nginx/sites-enabled/$DOMINIO
      rm -f /etc/nginx/sites-enabled/default
      nginx -t && systemctl reload nginx && echo 'nginx no ar em HTTP'"

if [ "$DNS_OK" = 1 ]; then
  titulo "5. Certificado HTTPS" "HTTPS certificate"
  # certonly não mexe na config: quem instala a definitiva é o passo 6
  ssh_ "certbot certonly --nginx -d $DOMINIO -d www.$DOMINIO \
          --non-interactive --agree-tos -m ${EMAIL_CERTBOT:?defina o e-mail do certbot}"

  titulo "6. Nginx definitivo (HTTPS, cache e gzip)" "Web server, final config"
  ssh_ "cp $REMOTO/deploy/nginx.conf /etc/nginx/sites-available/$DOMINIO
        nginx -t && systemctl reload nginx && echo 'HTTPS no ar'"
else
  titulo "5. Certificado HTTPS — PULADO" "HTTPS certificate — skipped"
  echo "O domínio ainda não aponta para $IP. O site já responde em HTTP pelo IP."
  echo "Assim que o DNS propagar, rode este script de novo que ele emite o certificado."
fi

titulo "7. Backup diário" "Daily backup"
ssh_ "grep -q backup-site /var/spool/cron/crontabs/root 2>/dev/null || \
      (crontab -l 2>/dev/null; echo '0 4 * * * tar -czf /root/backup-site-\$(date +\\%u).tar.gz -C $REMOTO data') | crontab -
      echo 'backup agendado para as 4h'"

titulo "8. Base de geolocalização" "Geolocation database"
# DB-IP Lite (CC-BY): mostra a cidade de quem visita e escolhe o idioma. Fica
# fora do git por causa do tamanho, e é atualizada quando o arquivo do mês muda.
ssh_ "mkdir -p $REMOTO/data/geo
      MES=\$(date +%Y-%m)
      ATUAL=$REMOTO/data/geo/cidades.mmdb
      MARCA=$REMOTO/data/geo/.mes
      if [ ! -f \"\$ATUAL\" ] || [ \"\$(cat \$MARCA 2>/dev/null)\" != \"\$MES\" ]; then
        echo \"baixando a base de \$MES...\"
        if curl -sfL --max-time 600 \"https://download.db-ip.com/free/dbip-city-lite-\$MES.mmdb.gz\" | gunzip > \$ATUAL.novo 2>/dev/null && [ -s \$ATUAL.novo ]; then
          mv \$ATUAL.novo \$ATUAL && echo \$MES > \$MARCA
          chown 1000:1000 \$ATUAL
          echo \"base atualizada (\$(du -h \$ATUAL | cut -f1))\"
        else
          rm -f \$ATUAL.novo
          echo \"base do mês ainda não publicada; a anterior continua valendo\"
        fi
      else
        echo \"base já está no mês corrente\"
      fi"

titulo "9. Prévias dos sites" "Site previews"
# Um site muda sem avisar. Domingo de madrugada, depois do backup, o container
# recaptura o que estiver com mais de uma semana.
ssh_ "grep -q renovar-previas /var/spool/cron/crontabs/root 2>/dev/null || \
      (crontab -l 2>/dev/null; echo '30 4 * * 0 cd $REMOTO && docker compose exec -T web python -m app.services.previas # renovar-previas') | crontab -
      echo 'prévias renovam domingo às 4h30'"

titulo "10. Limpeza diária do Lab de Demos" "Lab de Demos daily cleanup"
# Sandbox de visitante vive 24h (§4/§8 da spec do Lab). Todo dia de madrugada,
# antes das prévias de domingo, apaga quem já venceu — mesmo padrão de
# renovar-previas: script com __main__ chamado via `python -m`.
ssh_ "grep -q lab-limpeza-sandboxes /var/spool/cron/crontabs/root 2>/dev/null || \
      (crontab -l 2>/dev/null; echo '15 4 * * * cd $REMOTO && docker compose exec -T web python -m app.lab.sandbox # lab-limpeza-sandboxes') | crontab -
      echo 'limpeza do Lab agendada para as 4h15'"

titulo "Pronto" "Done"
marcar_fim
ssh_ "cat $REMOTO/data/ADMIN_CREDENTIALS.txt 2>/dev/null || echo '(senha do admin já foi trocada)'"
if [ "$DNS_OK" = 1 ]; then
  echo "Site: https://$DOMINIO"
  echo "Painel: https://$DOMINIO/admin"
else
  echo "Site (sem HTTPS ainda): http://$IP"
fi
