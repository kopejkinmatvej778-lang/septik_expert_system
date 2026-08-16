#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/var/www/septik-panel")
DATA_FILE = ROOT / "dashboard.json"
LOCAL_MEASUREMENTS_FILE = ROOT / "local_measurements.json"


class SeptikPanelHandler(SimpleHTTPRequestHandler):
    server_version = "SeptikPanel/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store" if self.path.startswith(("/dashboard", "/measurements")) else "public, max-age=60")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/dashboard", "/api/dashboard"):
            self.send_json({"ok": True, "data": self.load_dashboard()})
            return
        if path == "/health":
            self.send_json({"ok": True})
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/measurements", "/api/measurements"):
            self.send_json({"ok": False, "message": "Unknown endpoint"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            saved = self.load_local_measurements()
            payload["id"] = payload.get("id") or f"vps-{len(saved) + 1}"
            payload["source"] = payload.get("source") or "manual"
            payload["status"] = payload.get("status") or "Ручная задача"
            saved.insert(0, payload)
            LOCAL_MEASUREMENTS_FILE.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_json({"ok": True, "measurement": payload})
        except Exception as exc:
            self.send_json({"ok": False, "message": str(exc)}, status=500)

    def load_dashboard(self):
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        else:
            data = {}
        data.setdefault("measurements", [])
        data["measurements"] = self.load_local_measurements() + data["measurements"]
        data.setdefault("montages", [])
        data.setdefault("clients", [])
        data.setdefault("sales", [])
        data.setdefault("tasks", [])
        data.setdefault("agentEvents", [])
        return data

    def load_local_measurements(self):
        if not LOCAL_MEASUREMENTS_FILE.exists():
            return []
        return json.loads(LOCAL_MEASUREMENTS_FILE.read_text(encoding="utf-8"))

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", 80), SeptikPanelHandler)
    server.serve_forever()
