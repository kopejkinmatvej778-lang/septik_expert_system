from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .storage import now_iso


logger = logging.getLogger(__name__)


def _safe_name(value: str, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", " ", value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:96] or fallback


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _proposal_summary(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") or {}
    client = payload.get("client") or {}
    totals = payload.get("totals") or {}
    materials = payload.get("materials") or []
    equipment = ""
    for item in materials:
        name = str(item.get("name") or "")
        if "аэролос" in name.lower() or "станц" in name.lower() or "погреб" in name.lower():
            equipment = name
            break
    return {
        "client_name": str(client.get("name") or "Клиент"),
        "phone": str(client.get("phone") or ""),
        "address": str(client.get("address") or ""),
        "equipment": equipment,
        "amount": int(totals.get("grand_total") or 0),
    }


class GoogleSync:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._drive = None
        self._sheets = None

    @property
    def enabled(self) -> bool:
        path = self.settings.google_service_account_file
        return bool(path and path.exists() and self.settings.google_clients_folder_id)

    def disabled_reason(self) -> str | None:
        path = self.settings.google_service_account_file
        if not path:
            return "GOOGLE_SERVICE_ACCOUNT_FILE не задан"
        if not path.exists():
            return f"Файл service account не найден: {path}"
        if not self.settings.google_clients_folder_id:
            return "GOOGLE_CLIENTS_FOLDER_ID не задан"
        if not self.settings.google_registry_sheet_id:
            return "GOOGLE_REGISTRY_SHEET_ID не задан, Drive загрузка возможна, таблица не обновится"
        return None

    def _credentials(self):
        from google.oauth2 import service_account

        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        return service_account.Credentials.from_service_account_file(
            str(self.settings.google_service_account_file),
            scopes=scopes,
        )

    def drive(self):
        if self._drive is None:
            from googleapiclient.discovery import build

            self._drive = build("drive", "v3", credentials=self._credentials(), cache_discovery=False)
        return self._drive

    def sheets(self):
        if self._sheets is None:
            from googleapiclient.discovery import build

            self._sheets = build("sheets", "v4", credentials=self._credentials(), cache_discovery=False)
        return self._sheets

    def ensure_sheet_tab(self, spreadsheet_id: str, tab: str) -> None:
        spreadsheet = (
            self.sheets()
            .spreadsheets()
            .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
            .execute()
        )
        existing = {
            str(sheet.get("properties", {}).get("title") or "")
            for sheet in spreadsheet.get("sheets", [])
        }
        if tab in existing:
            return
        self.sheets().spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        ).execute()

    def get_or_create_folder(self, parent_id: str, name: str) -> dict[str, str]:
        drive = self.drive()
        query = (
            f"'{_escape_drive_query(parent_id)}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            f"name = '{_escape_drive_query(name)}' and trashed = false"
        )
        found = (
            drive.files()
            .list(q=query, fields="files(id,name,webViewLink)", pageSize=1, supportsAllDrives=True)
            .execute()
            .get("files", [])
        )
        if found:
            return {"id": found[0]["id"], "url": found[0].get("webViewLink", "")}

        created = (
            drive.files()
            .create(
                body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
                fields="id,name,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        return {"id": created["id"], "url": created.get("webViewLink", "")}

    def upload_proposal_png(self, record: dict[str, Any], local_path: Path) -> dict[str, str]:
        from googleapiclient.http import MediaFileUpload

        summary = _proposal_summary(record)
        client_folder = self.get_or_create_folder(
            str(self.settings.google_clients_folder_id),
            _safe_name(f"{summary['client_name']} {summary['phone']}", "Клиент"),
        )
        proposal_folder = self.get_or_create_folder(client_folder["id"], "КП PNG")
        file_name = _safe_name(f"КП {summary['client_name']} {record['proposal_id']}.png", f"{record['proposal_id']}.png")
        media = MediaFileUpload(str(local_path), mimetype="image/png", resumable=False)
        created = (
            self.drive()
            .files()
            .create(
                body={"name": file_name, "parents": [proposal_folder["id"]]},
                media_body=media,
                fields="id,name,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        return {
            "file_id": created["id"],
            "file_url": f"https://drive.google.com/uc?export=view&id={created['id']}",
            "web_view_url": created.get("webViewLink", ""),
            "folder_id": client_folder["id"],
            "folder_url": client_folder["url"],
        }

    def append_document_row(self, record: dict[str, Any], upload: dict[str, str]) -> None:
        if not self.settings.google_registry_sheet_id:
            return
        summary = _proposal_summary(record)
        values = [[
            now_iso(),
            summary["client_name"],
            summary["phone"],
            summary["address"],
            "КП PNG",
            "Отправлено",
            summary["amount"],
            summary["equipment"],
            upload.get("file_url", ""),
            upload.get("folder_url", ""),
            "Telegram",
            "",
            "",
            f"proposal_id={record['proposal_id']}",
        ]]
        self.sheets().spreadsheets().values().append(
            spreadsheetId=self.settings.google_registry_sheet_id,
            range="'Документы'!A:N",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    def append_measurement_row(self, measurement: dict[str, Any]) -> None:
        if not self.settings.google_registry_sheet_id:
            return
        values = [[
            measurement.get("created_at") or now_iso(),
            measurement.get("measured_at") or "",
            measurement.get("client_name") or "",
            measurement.get("phone") or "",
            measurement.get("address") or "",
            measurement.get("source") or "Telegram",
            measurement.get("status") or "Новый",
            measurement.get("soil") or "",
            measurement.get("groundwater") or "",
            measurement.get("pipe_depth") or "",
            measurement.get("distances") or "",
            measurement.get("recommended_equipment") or "",
            measurement.get("photos_count") or 0,
            measurement.get("amo_lead_id") or "",
            measurement.get("telegram_chat_id") or "",
            measurement.get("folder_url") or "",
            measurement.get("notes") or "",
            measurement.get("proposal_url") or "",
        ]]
        self.sheets().spreadsheets().values().append(
            spreadsheetId=self.settings.google_registry_sheet_id,
            range="'Замеры'!A:R",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()


class AmoCrmClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.amocrm_base_url and self.settings.amocrm_access_token)

    def disabled_reason(self) -> str | None:
        if not self.settings.amocrm_base_url:
            return "AMOCRM_BASE_URL не задан"
        if not self.settings.amocrm_access_token:
            return "AMOCRM_ACCESS_TOKEN не задан"
        return None

    def _url(self, path: str) -> str:
        base = str(self.settings.amocrm_base_url or "").rstrip("/")
        return f"{base}{path if path.startswith('/') else '/' + path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError(self.disabled_reason() or "amoCRM is disabled")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.amocrm_access_token}",
            **kwargs.pop("headers", {}),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, self._url(path), headers=headers, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    async def account(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v4/account")

    async def recent_leads(self, limit: int = 25) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/api/v4/leads?with=contacts&limit={max(1, min(limit, 250))}&order[updated_at]=desc")
        return list((data.get("_embedded") or {}).get("leads") or [])

    async def find_leads_by_phone(self, phone: str, limit: int = 10) -> list[dict[str, Any]]:
        query = re.sub(r"[^\d+]+", "", phone)
        if not query:
            return []
        data = await self._request("GET", f"/api/v4/leads?with=contacts&query={query}&limit={max(1, min(limit, 50))}")
        return list((data.get("_embedded") or {}).get("leads") or [])

    async def add_lead_note(self, lead_id: str | int, text: str) -> dict[str, Any]:
        payload = [
            {
                "note_type": "common",
                "params": {"text": text[:4096]},
            }
        ]
        return await self._request("POST", f"/api/v4/leads/{lead_id}/notes", json=payload)


async def post_to_control_panel(settings: Settings, record: dict[str, Any], upload: dict[str, Any]) -> None:
    if not settings.control_panel_api_url:
        return

    summary = _proposal_summary(record)
    base = settings.control_panel_api_url.rstrip("/")
    url = base if base.endswith("/api/dashboard") else f"{base}/api/dashboard"
    headers = {"Content-Type": "application/json"}
    if settings.control_panel_api_token:
        headers["Authorization"] = f"Bearer {settings.control_panel_api_token}"
    async with httpx.AsyncClient(timeout=12) as client:
        await client.post(
            url,
            headers=headers,
            json={
                "clientName": summary["client_name"],
                "phone": summary["phone"],
                "address": summary["address"],
                "type": "proposal",
                "title": f"КП {summary['client_name']}",
                "status": "rendered",
                "amount": summary["amount"],
                "equipment": summary["equipment"],
                "fileUrl": upload.get("file_url", ""),
                "amoLeadId": str(record.get("amo_lead_id") or record.get("payload", {}).get("amo_lead_id") or ""),
            },
        )


async def sync_proposal_to_amocrm(settings: Settings, record: dict[str, Any], upload: dict[str, Any]) -> dict[str, Any]:
    client = AmoCrmClient(settings)
    if not client.enabled:
        return {"sync_skipped": client.disabled_reason() or "amoCRM sync is disabled"}

    summary = _proposal_summary(record)
    lead_id = str(record.get("amo_lead_id") or record.get("payload", {}).get("amo_lead_id") or "").strip()
    matched_leads: list[dict[str, Any]] = []
    if not lead_id and summary["phone"]:
        matched_leads = await client.find_leads_by_phone(summary["phone"], limit=3)
        if len(matched_leads) == 1:
            lead_id = str(matched_leads[0].get("id") or "")

    if not lead_id:
        return {
            "sync_skipped": "amoCRM lead not found",
            "matched_leads": [lead.get("id") for lead in matched_leads],
        }

    file_url = upload.get("file_url") or ""
    calculation_text = str(record.get("calculation_text") or "").strip()
    if len(calculation_text) > 3000:
        calculation_text = f"{calculation_text[:3000]}\n...текст КП обрезан, полный PNG в файле."
    note_lines = [
        "КП PNG сформировано в Telegram-боте.",
        f"Клиент: {summary['client_name']}",
        f"Адрес: {summary['address']}",
        f"Сумма: {summary['amount']} руб.",
    ]
    if file_url:
        note_lines.append(f"Файл: {file_url}")
    if calculation_text:
        note_lines.extend(["", "Текст КП:", calculation_text])
    await client.add_lead_note(lead_id, "\n".join(note_lines))
    return {"ok": True, "amo_lead_id": lead_id}


async def sync_rendered_proposal(settings: Settings, record: dict[str, Any], local_path: Path) -> dict[str, Any]:
    upload: dict[str, Any] = {}
    google = GoogleSync(settings)
    if google.enabled:
        try:
            upload = await asyncio.to_thread(google.upload_proposal_png, record, local_path)
            await asyncio.to_thread(google.append_document_row, record, upload)
        except Exception:
            logger.exception("Google Drive/Sheets proposal sync failed")
            upload["sync_error"] = "Google Drive/Sheets sync failed"
    else:
        reason = google.disabled_reason() or "Google Drive/Sheets sync is disabled"
        logger.warning("Google Drive/Sheets proposal sync skipped: %s", reason)
        upload["sync_skipped"] = reason

    try:
        await post_to_control_panel(settings, record, upload)
    except Exception:
        logger.exception("Control panel proposal sync failed")

    try:
        amo_result = await sync_proposal_to_amocrm(settings, record, upload)
        if amo_result:
            upload["amocrm"] = amo_result
    except Exception:
        logger.exception("amoCRM proposal sync failed")
        upload["amocrm_error"] = "amoCRM sync failed"

    return upload
