from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from .integrations import GoogleSync


CLIENT_HEADERS = [
    "Клиент",
    "Телефон",
    "Адрес",
    "amo contact id",
    "amo lead id",
    "Папка клиента",
    "Последнее КП",
    "Последний договор",
    "Статус",
    "Комментарий",
]

MONTAGE_HEADERS = [
    "Дата монтажа",
    "Статус",
    "Клиент",
    "Телефон",
    "Адрес",
    "Оборудование",
    "Сумма договора",
    "Аванс",
    "Остаток",
    "Бригада",
    "Договор PDF",
    "КП PNG",
    "Папка клиента",
    "Комментарий",
]

MEASUREMENT_HEADERS = [
    "Дата создания",
    "Дата замера",
    "Клиент",
    "Телефон",
    "Адрес",
    "Источник",
    "Статус",
    "Грунт",
    "УГВ",
    "Глубина трубы",
    "Расстояния",
    "Рекомендованное оборудование",
    "Фото",
    "amo lead id",
    "telegram chat id",
    "Папка",
    "Заметки",
    "КП",
]

DOCUMENT_HEADERS = [
    "Дата создания",
    "Клиент",
    "Телефон",
    "Адрес",
    "Тип",
    "Статус",
    "Сумма",
    "Оборудование",
    "Файл PNG/PDF",
    "Папка клиента",
    "Источник",
    "amo lead id",
    "Ответственный",
    "Комментарий",
]

TARGET_HEADERS = {
    "Клиенты": CLIENT_HEADERS,
    "Монтажи": MONTAGE_HEADERS,
    "Замеры": MEASUREMENT_HEADERS,
    "Документы": DOCUMENT_HEADERS,
}


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("8"):
        return "+7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+" + digits
    if len(digits) == 10:
        return "+7" + digits
    return clean(value)


def normalize_date(value: Any) -> str:
    text = clean(value)
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date().isoformat()
        except ValueError:
            pass
    return text


def money(value: Any) -> str:
    numbers = [int(item) for item in re.findall(r"\d+", str(value or ""))]
    return str(max(numbers)) if numbers else ""


def public_csv_url(spreadsheet_id: str, gid: str | None = None) -> str:
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    if gid:
        url += f"&gid={gid}"
    return url


def fetch_public_csv(spreadsheet_id: str, gid: str | None = None) -> list[dict[str, str]]:
    with urllib.request.urlopen(public_csv_url(spreadsheet_id, gid), timeout=30) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def build_from_montage_rows(source_rows: list[dict[str, str]]) -> dict[str, list[list[Any]]]:
    clients: dict[str, list[Any]] = {}
    montages: list[list[Any]] = []
    measurements: list[list[Any]] = []

    for row_index, row in enumerate(source_rows, start=2):
        if not any(clean(value) for value in row.values()):
            continue

        client = clean(row.get("Имя")) or clean(row.get("Адрес")) or f"Строка {row_index}"
        phone = normalize_phone(row.get("Телефон"))
        address = clean(row.get("Адрес"))
        equipment = " | ".join(
            item for item in [clean(row.get("Станция")), clean(row.get("ЖБИ"))] if item
        )
        source = clean(row.get("Источник")) or "Монтажи 2026"
        responsible = clean(row.get("Замеры"))
        comment = "; ".join(
            item
            for item in [
                f"Отзыв: {clean(row.get('Отзыв'))}" if clean(row.get("Отзыв")) else "",
                f"Старая строка: {row_index}",
                f"Источник: {source}",
            ]
            if item
        )

        client_key = phone or f"{client}|{address}"
        clients.setdefault(
            client_key,
            [
                client,
                phone,
                address,
                "",
                "",
                "",
                "",
                "",
                "Из старой таблицы",
                f"Источник: Монтажи 2026; строка {row_index}",
            ],
        )

        montages.append(
            [
                normalize_date(row.get("Дата")),
                "Из старой таблицы",
                client,
                phone,
                address,
                equipment,
                money(row.get("Цена")),
                "",
                "",
                responsible,
                "",
                "",
                "",
                comment,
            ]
        )
        measurements.append(
            [
                normalize_date(row.get("Дата")),
                "",
                client,
                phone,
                address,
                "Старая таблица Монтажи 2026",
                "Импортировано",
                "",
                "",
                "",
                "",
                equipment,
                0,
                "",
                "",
                "",
                comment,
                "",
            ]
        )

    return {
        "Клиенты": list(clients.values()),
        "Монтажи": montages,
        "Замеры": measurements,
    }


def document_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png" and path.stem.startswith("КП"):
        return "КП PNG"
    if suffix == ".pdf":
        return "Договор PDF"
    if suffix == ".docx":
        return "Договор DOCX"
    return suffix.lstrip(".").upper()


def client_guess_from_title(title: str) -> str:
    cleaned = re.sub(
        r"^(КП|Договор поставки оборудования с монтажом|Договор поставки материалов с монтажом|Договор поставки погреба с монтажом)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )
    parts = cleaned.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else cleaned


def build_local_documents(output_dir: Path) -> list[list[Any]]:
    documents: list[list[Any]] = []
    for path in sorted(output_dir.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in {".png", ".pdf", ".docx"}:
            continue
        title = path.stem
        documents.append(
            [
                "",
                client_guess_from_title(title),
                "",
                "",
                document_type_for_path(path),
                "Локальный файл",
                "",
                "",
                str(path),
                "",
                "Локальный output",
                "",
                "",
                title,
            ]
        )
    return documents


def write_tab(google: GoogleSync, spreadsheet_id: str, tab: str, rows: list[list[Any]], replace: bool) -> None:
    google.ensure_sheet_tab(spreadsheet_id, tab)
    values = [TARGET_HEADERS[tab], *rows]
    service = google.sheets().spreadsheets().values()
    if replace:
        service.clear(spreadsheetId=spreadsheet_id, range=f"'{tab}'!A:Z", body={}).execute()
        service.update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        return

    service.append(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab}'!A:Z",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def export_local_csv(rows_by_tab: dict[str, list[list[Any]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for tab, rows in rows_by_tab.items():
        with (output_dir / f"{tab}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(TARGET_HEADERS[tab])
            writer.writerows(rows)
    summary = {tab: len(rows) for tab, rows in rows_by_tab.items()}
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import existing Septik Expert sheet data into the registry sheet.")
    parser.add_argument("--source-sheet-id", required=True)
    parser.add_argument("--source-gid", default=None)
    parser.add_argument("--target-sheet-id", default=None)
    parser.add_argument("--include-local-documents", default=None)
    parser.add_argument("--export-dir", default="tmp/sheets-import/structured")
    parser.add_argument("--write", action="store_true", help="Write to Google Sheets. Without this, only exports local CSV.")
    parser.add_argument("--append", action="store_true", help="Append rows instead of replacing target tabs.")
    args = parser.parse_args()

    source_rows = fetch_public_csv(args.source_sheet_id, args.source_gid)
    rows_by_tab = build_from_montage_rows(source_rows)
    if args.include_local_documents:
        rows_by_tab["Документы"] = build_local_documents(Path(args.include_local_documents))

    export_local_csv(rows_by_tab, Path(args.export_dir))
    print(json.dumps({tab: len(rows) for tab, rows in rows_by_tab.items()}, ensure_ascii=False, indent=2))

    if not args.write:
        return

    from .config import load_settings

    settings = load_settings(require_bot=False)
    target_sheet_id = args.target_sheet_id or settings.google_registry_sheet_id
    if not target_sheet_id:
        raise RuntimeError("target sheet id is required")

    google = GoogleSync(settings)
    if not google.enabled:
        raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")
    for tab, rows in rows_by_tab.items():
        write_tab(google, target_sheet_id, tab, rows, replace=not args.append)


if __name__ == "__main__":
    main()
