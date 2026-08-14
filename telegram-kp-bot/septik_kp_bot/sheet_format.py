from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from .config import load_settings
from .integrations import GoogleSync


@dataclass(frozen=True)
class TabStyle:
    title: str
    color: dict[str, float]


TAB_STYLES = [
    TabStyle("Документы", {"red": 0.18, "green": 0.36, "blue": 0.74}),
    TabStyle("Клиенты", {"red": 0.12, "green": 0.55, "blue": 0.42}),
    TabStyle("Замеры", {"red": 0.85, "green": 0.49, "blue": 0.18}),
    TabStyle("Монтажи", {"red": 0.74, "green": 0.25, "blue": 0.22}),
    TabStyle("Продажи", {"red": 0.25, "green": 0.31, "blue": 0.59}),
    TabStyle("Задачи", {"red": 0.58, "green": 0.31, "blue": 0.12}),
    TabStyle("Воронки", {"red": 0.39, "green": 0.41, "blue": 0.48}),
    TabStyle("Справочники", {"red": 0.34, "green": 0.34, "blue": 0.34}),
    TabStyle("Пульт", {"red": 0.12, "green": 0.12, "blue": 0.12}),
]


def sheet_ids(google: GoogleSync, spreadsheet_id: str) -> dict[str, int]:
    spreadsheet = (
        google.sheets()
        .spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties(sheetId,title)")
        .execute()
    )
    return {
        str(sheet["properties"]["title"]): int(sheet["properties"]["sheetId"])
        for sheet in spreadsheet.get("sheets", [])
    }


def format_sheet(spreadsheet_id: str) -> dict[str, int | str]:
    settings = load_settings(require_bot=False)
    google = GoogleSync(settings)
    if not google.enabled:
        raise RuntimeError(google.disabled_reason() or "Google Drive/Sheets sync is disabled")

    ids = sheet_ids(google, spreadsheet_id)
    requests = []
    formatted = 0
    for style in TAB_STYLES:
        sheet_id = ids.get(style.title)
        if sheet_id is None:
            continue
        formatted += 1
        requests.extend(
            [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "tabColor": style.color,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "tabColor,gridProperties.frozenRowCount",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 26,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": style.color,
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "WRAP",
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 10,
                                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 26,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "WRAP",
                                "textFormat": {"fontSize": 10},
                            }
                        },
                        "fields": "userEnteredFormat(verticalAlignment,wrapStrategy,textFormat.fontSize)",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": 0,
                            "endIndex": 1,
                        },
                        "properties": {"pixelSize": 38},
                        "fields": "pixelSize",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 26,
                        }
                    }
                },
                {
                    "setBasicFilter": {
                        "filter": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "startColumnIndex": 0,
                                "endColumnIndex": 26,
                            }
                        }
                    }
                },
            ]
        )

    if requests:
        google.sheets().spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()
    return {"formatted_tabs": formatted, "spreadsheet_id": spreadsheet_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Format Septik Expert Google Sheet tabs.")
    parser.add_argument("--target-sheet-id", default=None)
    args = parser.parse_args()

    settings = load_settings(require_bot=False)
    spreadsheet_id = args.target_sheet_id or settings.google_registry_sheet_id
    if not spreadsheet_id:
        raise RuntimeError("target sheet id is required")
    print(json.dumps(format_sheet(spreadsheet_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
