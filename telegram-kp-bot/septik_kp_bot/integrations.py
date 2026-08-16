from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

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


def _phone_digits(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) == 11 and digits.startswith("8"):
        return "7" + digits[1:]
    return digits


def _custom_field_text(row: dict[str, Any], names: tuple[str, ...]) -> str:
    wanted = tuple(name.lower() for name in names)
    for field in row.get("custom_fields_values") or []:
        field_name = str(field.get("field_name") or "").lower()
        field_code = str(field.get("field_code") or "").lower()
        if not any(name in field_name or name in field_code for name in wanted):
            continue
        values = []
        for value in field.get("values") or []:
            raw = value.get("value")
            if raw is not None:
                values.append(str(raw))
        if values:
            return ", ".join(values)
    return ""


def _lead_link(base_url: str | None, lead_id: str | int) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}/leads/detail/{lead_id}" if base and lead_id else ""


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

    async def find_leads_by_name(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        query = str(name or "").strip()
        if not query or query == "Клиент":
            return []
        params = urlencode({"with": "contacts,tags", "query": query, "limit": max(1, min(limit, 50))})
        data = await self._request("GET", f"/api/v4/leads?{params}")
        return list((data.get("_embedded") or {}).get("leads") or [])

    async def find_contacts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        text = str(query or "").strip()
        if not text:
            return []
        params = urlencode({"with": "leads", "query": text, "limit": max(1, min(limit, 50))})
        data = await self._request("GET", f"/api/v4/contacts?{params}")
        return list((data.get("_embedded") or {}).get("contacts") or [])

    async def get_lead(self, lead_id: str | int, with_param: str = "contacts,tags") -> dict[str, Any]:
        params = urlencode({"with": with_param}) if with_param else ""
        suffix = f"?{params}" if params else ""
        return await self._request("GET", f"/api/v4/leads/{lead_id}{suffix}")

    async def get_contact(self, contact_id: str | int, with_param: str = "leads") -> dict[str, Any]:
        params = urlencode({"with": with_param}) if with_param else ""
        suffix = f"?{params}" if params else ""
        return await self._request("GET", f"/api/v4/contacts/{contact_id}{suffix}")

    async def add_contact(self, name: str, phone: str = "") -> dict[str, Any]:
        contact: dict[str, Any] = {"name": (name or "Клиент")[:255]}
        if phone:
            contact["custom_fields_values"] = [
                {
                    "field_code": "PHONE",
                    "values": [{"value": phone, "enum_code": "WORK"}],
                }
            ]
        data = await self._request("POST", "/api/v4/contacts", json=[contact])
        contacts = list((data.get("_embedded") or {}).get("contacts") or [])
        return contacts[0] if contacts else {}

    async def add_lead(
        self,
        name: str,
        price: int = 0,
        contact_id: str | int | None = None,
        source: str = "Telegram bot",
    ) -> dict[str, Any]:
        lead: dict[str, Any] = {
            "name": (name or "КП из Telegram")[:255],
            "_embedded": {"tags": [{"name": source}]},
        }
        if price > 0:
            lead["price"] = price
        if contact_id:
            lead["_embedded"]["contacts"] = [{"id": int(contact_id)}]
        data = await self._request("POST", "/api/v4/leads", json=[lead])
        leads = list((data.get("_embedded") or {}).get("leads") or [])
        return leads[0] if leads else {}

    async def update_lead_price(self, lead_id: str | int, price: int) -> dict[str, Any]:
        if price <= 0:
            return {}
        return await self._request("PATCH", f"/api/v4/leads/{lead_id}", json={"price": price})

    async def add_lead_note(self, lead_id: str | int, text: str) -> dict[str, Any]:
        payload = [
            {
                "note_type": "common",
                "params": {"text": text[:4096]},
            }
        ]
        return await self._request("POST", f"/api/v4/leads/{lead_id}/notes", json=payload)

    async def lead_notes(self, lead_id: str | int, limit: int = 25) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/api/v4/leads/{lead_id}/notes?limit={max(1, min(limit, 250))}")
        return list((data.get("_embedded") or {}).get("notes") or [])

    async def add_task(
        self,
        lead_id: str | int,
        text: str,
        complete_till: int,
        responsible_user_id: int | None = None,
        task_type_id: int = 1,
    ) -> dict[str, Any]:
        task: dict[str, Any] = {
            "entity_id": int(lead_id),
            "entity_type": "leads",
            "task_type_id": task_type_id,
            "text": text[:1000],
            "complete_till": int(complete_till),
        }
        if responsible_user_id:
            task["responsible_user_id"] = int(responsible_user_id)
        data = await self._request("POST", "/api/v4/tasks", json=[task])
        tasks = list((data.get("_embedded") or {}).get("tasks") or [])
        return tasks[0] if tasks else {}


def lead_contact_phone(lead: dict[str, Any]) -> str:
    contacts = (lead.get("_embedded") or {}).get("contacts") or []
    for contact in contacts:
        phone = _custom_field_text(contact, ("телефон", "phone"))
        if phone:
            return phone
    return ""


def exact_phone_leads(leads: list[dict[str, Any]], phone: str) -> list[dict[str, Any]]:
    wanted = _phone_digits(phone)
    if not wanted:
        return []
    exact = []
    for lead in leads:
        lead_phone = lead_contact_phone(lead)
        if not lead_phone or _phone_digits(lead_phone) == wanted:
            exact.append(lead)
    return exact


async def resolve_or_create_lead_for_proposal(client: AmoCrmClient, record: dict[str, Any]) -> dict[str, Any]:
    summary = _proposal_summary(record)
    existing_id = str(record.get("amo_lead_id") or record.get("payload", {}).get("amo_lead_id") or "").strip()
    if existing_id:
        return {"status": "existing", "lead_id": existing_id}

    candidates: list[dict[str, Any]] = []
    phone = summary["phone"]
    if phone:
        lead_matches = exact_phone_leads(await client.find_leads_by_phone(phone, limit=10), phone)
        contact_matches = await client.find_contacts(phone, limit=10)
        contact_lead_ids = {
            int(lead.get("id"))
            for contact in contact_matches
            for lead in ((contact.get("_embedded") or {}).get("leads") or [])
            if lead.get("id")
        }
        for lead in lead_matches:
            if lead.get("id"):
                contact_lead_ids.add(int(lead["id"]))
        for lead_id in sorted(contact_lead_ids):
            try:
                candidates.append(await client.get_lead(lead_id, "contacts,tags"))
            except Exception:
                logger.exception("Failed to fetch amoCRM lead candidate %s", lead_id)

        if not candidates and len(contact_matches) == 1:
            contact_id = contact_matches[0].get("id")
            lead = await client.add_lead(
                f"КП {summary['client_name']} {summary['address']}".strip(),
                summary["amount"],
                contact_id=contact_id,
            )
            lead_id = str(lead.get("id") or "")
            if lead_id:
                return {"status": "created_lead_for_contact", "lead_id": lead_id, "contact_id": str(contact_id or "")}
        if not candidates and len(contact_matches) > 1:
            return {
                "status": "ambiguous",
                "candidates": [
                    {
                        "id": contact.get("id"),
                        "name": contact.get("name") or "",
                        "entity": "contact",
                    }
                    for contact in contact_matches[:5]
                ],
            }

    if not candidates and summary["client_name"] and summary["client_name"] != "Клиент":
        candidates = await client.find_leads_by_name(summary["client_name"], limit=5)

    unique: dict[str, dict[str, Any]] = {}
    for lead in candidates:
        lead_id = str(lead.get("id") or "")
        if lead_id:
            unique[lead_id] = lead
    candidates = list(unique.values())

    if len(candidates) == 1:
        return {"status": "matched", "lead_id": str(candidates[0].get("id") or ""), "lead": candidates[0]}
    if len(candidates) > 1:
        return {
            "status": "ambiguous",
            "candidates": [
                {
                    "id": lead.get("id"),
                    "name": lead.get("name") or "",
                    "price": lead.get("price") or 0,
                    "link": _lead_link(client.settings.amocrm_base_url, lead.get("id") or ""),
                }
                for lead in candidates[:5]
            ],
        }

    contact = await client.add_contact(summary["client_name"], phone)
    lead = await client.add_lead(
        f"КП {summary['client_name']} {summary['address']}".strip(),
        summary["amount"],
        contact_id=contact.get("id"),
    )
    return {
        "status": "created_contact_and_lead",
        "lead_id": str(lead.get("id") or ""),
        "contact_id": str(contact.get("id") or ""),
    }


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
    resolved = await resolve_or_create_lead_for_proposal(client, record)
    if resolved.get("status") == "ambiguous":
        return {
            "sync_skipped": "amoCRM found multiple candidate leads",
            "matched_leads": resolved.get("candidates") or [],
        }
    lead_id = str(resolved.get("lead_id") or "").strip()
    if not lead_id:
        return {"sync_skipped": "amoCRM lead was not created or matched", "resolution": resolved}
    record["amo_lead_id"] = lead_id
    record.setdefault("payload", {})["amo_lead_id"] = lead_id

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
    if settings.amocrm_update_lead_price:
        await client.update_lead_price(lead_id, summary["amount"])
    return {"ok": True, "amo_lead_id": lead_id, "resolution": resolved}


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
