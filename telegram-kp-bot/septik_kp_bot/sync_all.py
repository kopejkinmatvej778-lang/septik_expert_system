from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .config import load_settings
from .crm_sync import collect_crm_rows, write_tab as write_crm_tab
from .crm_sync import PIPELINE_HEADERS, SALES_HEADERS, TASK_HEADERS
from .integrations import AmoCrmClient, GoogleSync
from .sheet_format import format_sheet
from .sheet_import import (
    TARGET_HEADERS,
    build_from_montage_rows,
    build_local_documents,
    export_local_csv,
    fetch_public_csv,
    write_tab as write_legacy_tab,
)


DEFAULT_SOURCE_SHEET_ID = "1u86aaLma67nYqVJVx4kJB1yFNe1gDPBzlYshZaxL9Bo"
DEFAULT_TARGET_SHEET_ID = "1IUjancmUE0pxa0CTEzg50hmFHqj2Ghh4iZs-ExgLNyM"


def integration_status() -> dict[str, Any]:
    settings = load_settings(require_bot=False)
    google = GoogleSync(settings)
    amo = AmoCrmClient(settings)
    google_key = settings.google_service_account_file
    return {
        "google": {
            "enabled": google.enabled,
            "reason": google.disabled_reason(),
            "service_account_file": str(google_key) if google_key else "",
            "service_account_file_exists": bool(google_key and google_key.exists()),
            "registry_sheet_id": settings.google_registry_sheet_id or "",
            "clients_folder_id": settings.google_clients_folder_id or "",
        },
        "amocrm": {
            "enabled": amo.enabled,
            "reason": amo.disabled_reason(),
            "base_url": settings.amocrm_base_url or "",
            "access_token_present": bool(settings.amocrm_access_token),
        },
    }


def print_status() -> None:
    print(json.dumps(integration_status(), ensure_ascii=False, indent=2))


def init_tabs(target_sheet_id: str) -> None:
    settings = load_settings(require_bot=False)
    google = GoogleSync(settings)
    if not google.enabled:
        raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")

    service = google.sheets().spreadsheets().values()
    headers_by_tab = {
        **TARGET_HEADERS,
        "Продажи": SALES_HEADERS,
        "Задачи": TASK_HEADERS,
        "Воронки": PIPELINE_HEADERS,
    }
    for tab, headers in headers_by_tab.items():
        google.ensure_sheet_tab(target_sheet_id, tab)
        current = service.get(spreadsheetId=target_sheet_id, range=f"'{tab}'!A1:Z1").execute().get("values", [])
        if not current:
            service.update(
                spreadsheetId=target_sheet_id,
                range=f"'{tab}'!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [headers]},
            ).execute()


def sync_legacy(args: argparse.Namespace) -> dict[str, int]:
    settings = load_settings(require_bot=False)
    source_rows = fetch_public_csv(args.source_sheet_id, args.source_gid)
    rows_by_tab = build_from_montage_rows(source_rows)
    if args.include_local_documents:
        rows_by_tab["Документы"] = build_local_documents(Path(args.include_local_documents))

    legacy_export_dir = Path(args.export_dir) / "legacy"
    export_local_csv(rows_by_tab, legacy_export_dir)

    if args.write:
        google = GoogleSync(settings)
        if not google.enabled:
            raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")
        for tab, rows in rows_by_tab.items():
            write_legacy_tab(google, args.target_sheet_id, tab, rows, replace=True)

    return {tab: len(rows) for tab, rows in rows_by_tab.items()}


async def sync_crm(args: argparse.Namespace) -> dict[str, int]:
    settings = load_settings(require_bot=False)
    rows_by_tab = await collect_crm_rows()
    crm_export_dir = Path(args.export_dir) / "crm"
    crm_export_dir.mkdir(parents=True, exist_ok=True)
    summary = {}

    import csv

    for tab, (headers, rows) in rows_by_tab.items():
        summary[tab] = len(rows)
        with (crm_export_dir / f"{tab}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    (crm_export_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.write:
        google = GoogleSync(settings)
        if not google.enabled:
            raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")
        for tab, (headers, rows) in rows_by_tab.items():
            write_crm_tab(google, args.target_sheet_id, tab, headers, rows)

    return summary


async def run() -> None:
    parser = argparse.ArgumentParser(description="Run Septik Expert legacy Sheet and amoCRM synchronization.")
    parser.add_argument("--source-sheet-id", default=DEFAULT_SOURCE_SHEET_ID)
    parser.add_argument("--source-gid", default=None)
    parser.add_argument("--target-sheet-id", default=DEFAULT_TARGET_SHEET_ID)
    parser.add_argument("--include-local-documents", default="../output")
    parser.add_argument("--export-dir", default="../tmp/sheets-import/sync-all")
    parser.add_argument("--write", action="store_true", help="Write to Google Sheets. Without this, only exports CSV.")
    parser.add_argument("--check", action="store_true", help="Only print integration status.")
    parser.add_argument("--init-tabs", action="store_true", help="Create required Google Sheet tabs and headers.")
    parser.add_argument("--format", action="store_true", help="Only format the target Google Sheet.")
    parser.add_argument("--no-format", action="store_true", help="Skip formatting after Google Sheets writes.")
    parser.add_argument("--skip-legacy", action="store_true")
    parser.add_argument("--skip-crm", action="store_true")
    args = parser.parse_args()

    if args.check:
        print_status()
        return

    if args.init_tabs:
        init_tabs(args.target_sheet_id)
        print(json.dumps({"init_tabs": "ok"}, ensure_ascii=False, indent=2))
        return

    if args.format:
        print(json.dumps(format_sheet(args.target_sheet_id), ensure_ascii=False, indent=2))
        return

    result: dict[str, dict[str, int]] = {}
    if not args.skip_legacy:
        result["legacy"] = sync_legacy(args)
    if not args.skip_crm:
        result["crm"] = await sync_crm(args)
    if args.write and not args.no_format:
        result["format"] = format_sheet(args.target_sheet_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
