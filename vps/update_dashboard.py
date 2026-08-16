#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


BOT_ROOT = Path("/opt/septik-kp-bot")
EXPORT_ROOT = Path("/var/lib/septik-panel/sync")
SITE_ROOT = Path("/var/www/septik-panel")
DASHBOARD_FILE = SITE_ROOT / "dashboard.json"


def read_csv(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"headers": [], "rows": []}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {"headers": reader.fieldnames or [], "rows": list(reader)}


def previous_sheet(name: str) -> dict[str, object]:
    if not DASHBOARD_FILE.exists():
        return {"headers": [], "rows": []}
    try:
        data = json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"headers": [], "rows": []}
    return (data.get("sheets") or {}).get(name) or {"headers": [], "rows": []}


def top(rows: list[dict[str, str]], key: str, limit: int = 8) -> list[list[object]]:
    counter = Counter((row.get(key) or "Не указано").strip() or "Не указано" for row in rows)
    return [[name, count] for name, count in counter.most_common(limit)]


def money(value: str) -> int:
    raw = "".join(char for char in str(value or "") if char.isdigit())
    return int(raw or 0)


def build_dashboard() -> dict[str, object]:
    legacy = EXPORT_ROOT / "legacy"
    crm = EXPORT_ROOT / "crm"

    sheets = {
        "Клиенты": read_csv(legacy / "Клиенты.csv"),
        "Документы": read_csv(legacy / "Документы.csv"),
        "Монтажи": read_csv(legacy / "Монтажи.csv"),
        "Замеры": read_csv(legacy / "Замеры.csv"),
        "Продажи": read_csv(crm / "Продажи.csv"),
        "Задачи": read_csv(crm / "Задачи.csv"),
        "Воронки": read_csv(crm / "Воронки.csv"),
        "Справочники": read_csv(legacy / "Справочники.csv"),
    }

    if not sheets["Документы"]["rows"]:
        sheets["Документы"] = previous_sheet("Документы")

    sales_rows = sheets["Продажи"]["rows"]
    summary = {
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "clients": len(sheets["Клиенты"]["rows"]),
        "montages": len(sheets["Монтажи"]["rows"]),
        "measurements": len(sheets["Замеры"]["rows"]),
        "documents": len(sheets["Документы"]["rows"]),
        "sales": len(sales_rows),
        "tasks": len(sheets["Задачи"]["rows"]),
        "funnels": len(sheets["Воронки"]["rows"]),
        "sales_amount": sum(money(row.get("Бюджет", "")) for row in sales_rows),
        "top_statuses": top(sales_rows, "Статус"),
        "top_pipelines": top(sales_rows, "Воронка"),
        "top_sources": top(sales_rows, "Источник/канал"),
        "top_responsibles": top(sales_rows, "Ответственный"),
    }

    return {"summary": summary, "sheets": sheets}


def run_sync() -> None:
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    command = [
        str(BOT_ROOT / ".venv" / "bin" / "python"),
        "-m",
        "septik_kp_bot.sync_all",
        "--export-dir",
        str(EXPORT_ROOT),
        "--no-format",
    ]
    subprocess.run(command, cwd=str(BOT_ROOT), check=True)


def main() -> None:
    run_sync()
    dashboard = build_dashboard()
    tmp = DASHBOARD_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dashboard, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DASHBOARD_FILE)
    sheets = dashboard["sheets"]
    print(json.dumps({name: len(sheet["rows"]) for name, sheet in sheets.items()}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"dashboard update failed: {exc}", file=sys.stderr)
        raise
