#!/usr/bin/env bash
set -euo pipefail

mkdir -p /opt/septik-kp-bot /opt/septik-panel /var/lib/septik-panel/sync

if [ -d /opt/septik-kp-bot/septik_kp_bot ]; then
  cp -a /opt/septik-kp-bot "/root/septik-kp-bot-backup-$(date +%Y%m%d-%H%M%S)"
fi

tar -xzf /tmp/telegram-kp-bot-live.tar.gz --strip-components=1 -C /opt/septik-kp-bot
tar -xzf /tmp/septik-panel-vps-scripts.tar.gz -C /opt/septik-panel

python3 -m venv /opt/septik-kp-bot/.venv
/opt/septik-kp-bot/.venv/bin/python -m pip install --upgrade pip >/dev/null
/opt/septik-kp-bot/.venv/bin/pip install -r /opt/septik-kp-bot/requirements.txt >/dev/null

cp /opt/septik-panel/septik-dashboard-sync.service /etc/systemd/system/septik-dashboard-sync.service
cp /opt/septik-panel/septik-dashboard-sync.timer /etc/systemd/system/septik-dashboard-sync.timer
systemctl daemon-reload

cd /opt/septik-kp-bot
.venv/bin/python -m septik_kp_bot.sync_all --check
/usr/bin/python3 /opt/septik-panel/update_dashboard.py

systemctl enable --now septik-dashboard-sync.timer >/dev/null
systemctl --no-pager --lines=12 status septik-dashboard-sync.timer
