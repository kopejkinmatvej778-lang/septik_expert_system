#!/usr/bin/env bash
set -euo pipefail

SITE_ROOT="/var/www/septik-panel"
APP_ROOT="/opt/septik-panel"
ARCHIVE="/tmp/septik-panel-deploy.tar.gz"

mkdir -p "$SITE_ROOT" "$APP_ROOT"

backup="/root/septik-panel-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cp -a "$SITE_ROOT"/. "$backup"/ 2>/dev/null || true

python3 - <<'PY'
from pathlib import Path
import html as html_lib
import json
import re

root = Path("/var/www/septik-panel")
index = root / "index.html"
out = root / "dashboard.json"

try:
    if not index.exists():
        print("old index missing")
        raise SystemExit

    text = index.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'<script id="data" type="application/json">([\s\S]*?)</script>', text)
    if not match:
        print("old index has no embedded data")
        raise SystemExit

    payload = html_lib.unescape(match.group(1))
    data = json.loads(payload)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    sheets = data.get("sheets", {})
    print("saved dashboard.json:", {key: len(value.get("rows", [])) for key, value in sheets.items()})
except Exception as exc:
    print("old dashboard extraction skipped:", exc)
PY

workdir="/tmp/septik-panel-upload-$(date +%s)"
mkdir -p "$workdir"
tar -xzf "$ARCHIVE" -C "$workdir"
cp -a "$workdir/site/." "$SITE_ROOT"/
cp "$workdir/service/septik_panel_server.py" "$APP_ROOT/septik_panel_server.py"
if [ -f "$workdir/data/dashboard.json" ]; then
  cp "$workdir/data/dashboard.json" "$SITE_ROOT/dashboard.json"
fi
chmod +x "$APP_ROOT/septik_panel_server.py"

if [ ! -f "$SITE_ROOT/dashboard.json" ] && [ -f "$backup/dashboard.json" ]; then
  cp "$backup/dashboard.json" "$SITE_ROOT/dashboard.json"
fi

if [ ! -f "$SITE_ROOT/local_measurements.json" ]; then
  printf '[]' > "$SITE_ROOT/local_measurements.json"
fi

cat > /etc/systemd/system/septik-panel.service <<'EOF'
[Unit]
Description=Septik Expert static panel and API
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/septik-panel
ExecStart=/usr/bin/python3 /opt/septik-panel/septik_panel_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
pkill -f "python3 -m http.server 80 --bind 0.0.0.0" 2>/dev/null || true
systemctl enable septik-panel.service >/dev/null
systemctl restart septik-panel.service
sleep 1

systemctl --no-pager --lines=12 status septik-panel.service
printf '\n-- health --\n'
curl -sS http://127.0.0.1/health
printf '\n-- dashboard counts --\n'
curl -sS http://127.0.0.1/dashboard | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); s=d.get('sheets',{}); print({k: len(v.get('rows',[])) for k,v in s.items()}); print('manual_measurements', len(d.get('measurements', [])))"
printf '\n-- files --\n'
ls -lah "$SITE_ROOT" | sed -n '1,40p'
