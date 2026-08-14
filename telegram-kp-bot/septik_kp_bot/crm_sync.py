from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .config import load_settings
from .integrations import AmoCrmClient, GoogleSync


MOSCOW = ZoneInfo("Europe/Moscow")

SALES_HEADERS = [
    "amo lead id",
    "Дата создания",
    "Дата обновления",
    "Название сделки",
    "Воронка",
    "Статус",
    "Ответственный",
    "Бюджет",
    "Источник/канал",
    "Клиент",
    "Телефон",
    "Теги",
    "Ссылка",
]

TASK_HEADERS = [
    "amo task id",
    "Дата выполнения",
    "Завтра",
    "Статус",
    "Ответственный",
    "Тип",
    "Текст",
    "entity type",
    "entity id",
    "Ссылка",
]

PIPELINE_HEADERS = [
    "pipeline id",
    "Воронка",
    "status id",
    "Статус",
    "Сортировка",
    "Цвет",
]


def from_unix(value: Any) -> str:
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value), tz=MOSCOW).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def tomorrow_bounds() -> tuple[int, int, str]:
    now = datetime.now(MOSCOW)
    tomorrow = (now + timedelta(days=1)).date()
    start = datetime.combine(tomorrow, datetime.min.time(), tzinfo=MOSCOW)
    end = start + timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp()) - 1, tomorrow.isoformat()


def account_base(settings_base_url: str | None) -> str:
    return (settings_base_url or "").rstrip("/")


async def paginated(client: AmoCrmClient, path: str, embedded_key: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = {"limit": 250, "page": page, **(params or {})}
        separator = "&" if "?" in path else "?"
        data = await client._request("GET", f"{path}{separator}{urlencode(query, doseq=True)}")
        batch = list((data.get("_embedded") or {}).get(embedded_key) or [])
        rows.extend(batch)
        if not batch or not ((data.get("_links") or {}).get("next")):
            break
        page += 1
    return rows


def users_by_id(users: list[dict[str, Any]]) -> dict[int, str]:
    return {int(user["id"]): str(user.get("name") or user.get("email") or user["id"]) for user in users if user.get("id")}


def pipeline_maps(pipelines: list[dict[str, Any]]) -> tuple[dict[int, str], dict[int, str]]:
    pipelines_map: dict[int, str] = {}
    statuses_map: dict[int, str] = {}
    for pipeline in pipelines:
        pipeline_id = int(pipeline.get("id") or 0)
        if pipeline_id:
            pipelines_map[pipeline_id] = str(pipeline.get("name") or pipeline_id)
        for status in (pipeline.get("_embedded") or {}).get("statuses") or []:
            status_id = int(status.get("id") or 0)
            if status_id:
                statuses_map[status_id] = str(status.get("name") or status_id)
    return pipelines_map, statuses_map


def custom_field_text(row: dict[str, Any], names: tuple[str, ...]) -> str:
    wanted = tuple(name.lower() for name in names)
    for field in row.get("custom_fields_values") or []:
        field_name = str(field.get("field_name") or "").lower()
        if not any(name in field_name for name in wanted):
            continue
        values = []
        for value in field.get("values") or []:
            raw = value.get("value")
            if raw is not None:
                values.append(str(raw))
        if values:
            return ", ".join(values)
    return ""


def lead_contact_text(lead: dict[str, Any]) -> tuple[str, str]:
    contacts = (lead.get("_embedded") or {}).get("contacts") or []
    if not contacts:
        return "", ""
    contact = contacts[0]
    return str(contact.get("name") or ""), custom_field_text(contact, ("телефон", "phone"))


def lead_source(lead: dict[str, Any]) -> str:
    return custom_field_text(
        lead,
        (
            "источник",
            "канал",
            "utm_source",
            "source",
            "roistat",
        ),
    )


def lead_tags(lead: dict[str, Any]) -> str:
    tags = (lead.get("_embedded") or {}).get("tags") or []
    return ", ".join(str(tag.get("name") or "") for tag in tags if tag.get("name"))


def build_sales_rows(
    leads: list[dict[str, Any]],
    pipelines: dict[int, str],
    statuses: dict[int, str],
    users: dict[int, str],
    base_url: str,
) -> list[list[Any]]:
    rows = []
    for lead in leads:
        lead_id = lead.get("id") or ""
        contact_name, phone = lead_contact_text(lead)
        rows.append(
            [
                lead_id,
                from_unix(lead.get("created_at")),
                from_unix(lead.get("updated_at")),
                lead.get("name") or "",
                pipelines.get(int(lead.get("pipeline_id") or 0), str(lead.get("pipeline_id") or "")),
                statuses.get(int(lead.get("status_id") or 0), str(lead.get("status_id") or "")),
                users.get(int(lead.get("responsible_user_id") or 0), str(lead.get("responsible_user_id") or "")),
                lead.get("price") or "",
                lead_source(lead),
                contact_name,
                phone,
                lead_tags(lead),
                f"{base_url}/leads/detail/{lead_id}" if base_url and lead_id else "",
            ]
        )
    return rows


def build_pipeline_rows(pipelines: list[dict[str, Any]]) -> list[list[Any]]:
    rows = []
    for pipeline in pipelines:
        pipeline_id = pipeline.get("id") or ""
        pipeline_name = pipeline.get("name") or ""
        for status in (pipeline.get("_embedded") or {}).get("statuses") or []:
            rows.append(
                [
                    pipeline_id,
                    pipeline_name,
                    status.get("id") or "",
                    status.get("name") or "",
                    status.get("sort") or "",
                    status.get("color") or "",
                ]
            )
    return rows


def build_task_rows(tasks: list[dict[str, Any]], users: dict[int, str], base_url: str, tomorrow_label: str) -> list[list[Any]]:
    rows = []
    for task in tasks:
        task_id = task.get("id") or ""
        entity_id = task.get("entity_id") or ""
        entity_type = task.get("entity_type") or ""
        rows.append(
            [
                task_id,
                from_unix(task.get("complete_till")),
                tomorrow_label,
                "Завершена" if task.get("is_completed") else "Активна",
                users.get(int(task.get("responsible_user_id") or 0), str(task.get("responsible_user_id") or "")),
                task.get("task_type_id") or "",
                task.get("text") or "",
                entity_type,
                entity_id,
                f"{base_url}/todo/list/" if base_url else "",
            ]
        )
    return rows


def export_csv(rows_by_tab: dict[str, tuple[list[str], list[list[Any]]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for tab, (headers, rows) in rows_by_tab.items():
        summary[tab] = len(rows)
        with (output_dir / f"{tab}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def write_tab(google: GoogleSync, spreadsheet_id: str, tab: str, headers: list[str], rows: list[list[Any]]) -> None:
    google.ensure_sheet_tab(spreadsheet_id, tab)
    service = google.sheets().spreadsheets().values()
    service.clear(spreadsheetId=spreadsheet_id, range=f"'{tab}'!A:Z", body={}).execute()
    service.update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [headers, *rows]},
    ).execute()


async def collect_crm_rows() -> dict[str, tuple[list[str], list[list[Any]]]]:
    settings = load_settings(require_bot=False)
    amo = AmoCrmClient(settings)
    if not amo.enabled:
        raise RuntimeError(amo.disabled_reason() or "amoCRM sync is disabled")

    start, end, tomorrow_label = tomorrow_bounds()
    pipelines_task = asyncio.create_task(paginated(amo, "/api/v4/leads/pipelines", "pipelines"))
    users_task = asyncio.create_task(paginated(amo, "/api/v4/users", "users"))
    leads_task = asyncio.create_task(paginated(amo, "/api/v4/leads", "leads", {"with": "contacts,tags"}))
    tasks_task = asyncio.create_task(
        paginated(
            amo,
            "/api/v4/tasks",
            "tasks",
            {
                "filter[is_completed]": 0,
                "filter[complete_till][from]": start,
                "filter[complete_till][to]": end,
            },
        )
    )

    pipelines = await pipelines_task
    users = users_by_id(await users_task)
    pipelines_map, statuses_map = pipeline_maps(pipelines)
    base_url = account_base(settings.amocrm_base_url)

    return {
        "Продажи": (
            SALES_HEADERS,
            build_sales_rows(await leads_task, pipelines_map, statuses_map, users, base_url),
        ),
        "Задачи": (
            TASK_HEADERS,
            build_task_rows(await tasks_task, users, base_url, tomorrow_label),
        ),
        "Воронки": (
            PIPELINE_HEADERS,
            build_pipeline_rows(pipelines),
        ),
    }


async def run() -> None:
    parser = argparse.ArgumentParser(description="Sync amoCRM sales analytics and tomorrow tasks to Google Sheets.")
    parser.add_argument("--target-sheet-id", default=None)
    parser.add_argument("--export-dir", default="tmp/sheets-import/crm-sync")
    parser.add_argument("--write", action="store_true", help="Write rows to Google Sheets. Without this, only exports CSV.")
    args = parser.parse_args()

    settings = load_settings(require_bot=False)
    rows_by_tab = await collect_crm_rows()
    export_csv(rows_by_tab, Path(args.export_dir))
    print(json.dumps({tab: len(rows) for tab, (_, rows) in rows_by_tab.items()}, ensure_ascii=False, indent=2))

    if not args.write:
        return

    target_sheet_id = args.target_sheet_id or settings.google_registry_sheet_id
    if not target_sheet_id:
        raise RuntimeError("target sheet id is required")
    google = GoogleSync(settings)
    if not google.enabled:
        raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")
    for tab, (headers, rows) in rows_by_tab.items():
        write_tab(google, target_sheet_id, tab, headers, rows)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
