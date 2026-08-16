from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import Settings, load_settings
from .crm_sync import account_base, from_unix, paginated, users_by_id
from .integrations import AmoCrmClient


MOSCOW = ZoneInfo("Europe/Moscow")
CLOSED_STATUS_IDS = {142, 143}


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
    base = account_base(base_url)
    return f"{base}/leads/detail/{lead_id}" if base and lead_id else ""


def _tomorrow_due_timestamp(hour: int) -> int:
    safe_hour = min(max(int(hour or 11), 8), 20)
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)
    due = datetime.combine(tomorrow, datetime.min.time(), tzinfo=MOSCOW).replace(hour=safe_hour)
    return int(due.timestamp())


def is_open_lead(lead: dict[str, Any]) -> bool:
    status_id = int(lead.get("status_id") or 0)
    return bool(lead.get("id")) and status_id not in CLOSED_STATUS_IDS and not lead.get("is_deleted")


def active_task_lead_ids(tasks: list[dict[str, Any]]) -> set[int]:
    return {
        int(task["entity_id"])
        for task in tasks
        if task.get("entity_id")
        and str(task.get("entity_type") or "") == "leads"
        and not task.get("is_completed")
    }


def leads_without_active_tasks(leads: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    busy_leads = active_task_lead_ids(tasks)
    return [lead for lead in leads if is_open_lead(lead) and int(lead.get("id") or 0) not in busy_leads]


def note_text(note: dict[str, Any]) -> str:
    params = note.get("params") or {}
    return str(params.get("text") or params.get("text_before") or params.get("text_after") or "").strip()


def contact_summary(contacts: list[dict[str, Any]]) -> tuple[str, str]:
    if not contacts:
        return "", ""
    contact = contacts[0]
    return str(contact.get("name") or ""), _custom_field_text(contact, ("телефон", "phone"))


def build_deal_analysis(card: dict[str, Any], users: dict[int, str], base_url: str) -> dict[str, str]:
    lead = card["lead"]
    notes = card.get("notes") or []
    contacts = card.get("contacts") or []
    contact_name, phone = contact_summary(contacts)
    lead_id = lead.get("id") or ""
    responsible = users.get(int(lead.get("responsible_user_id") or 0), str(lead.get("responsible_user_id") or ""))
    recent_notes = "\n".join(note_text(note) for note in notes[:5] if note_text(note))
    notes_lc = recent_notes.lower()
    price = int(lead.get("price") or 0)

    if not contacts and not phone:
        next_step = "Найти или уточнить контакт клиента, затем зафиксировать телефон в карточке."
    elif "кп" in notes_lc or "коммерчес" in notes_lc or "предлож" in notes_lc:
        next_step = "Связаться с клиентом по отправленному КП: получил ли, есть ли вопросы, какой следующий шаг."
    elif price > 0:
        next_step = "Уточнить решение по сделке и договориться о следующем действии: КП, договор, замер или монтаж."
    else:
        next_step = "Позвонить клиенту, уточнить потребность, адрес, систему и зафиксировать следующий шаг."

    task_text = (
        f"Следующий шаг: {next_step} "
        f"Клиент: {contact_name or lead.get('name') or 'не указан'}. "
        f"Телефон: {phone or 'не указан'}. "
        f"Ответственный: {responsible or 'не указан'}."
    )
    report_line = (
        f"- {lead.get('name') or 'Сделка'} | {contact_name or 'контакт не указан'} | "
        f"{phone or 'телефон не указан'} | {responsible or 'ответственный не указан'} | "
        f"{_lead_link(base_url, lead_id)}\n  Задача: {next_step}"
    )
    note = "\n".join(
        [
            "Контроль сделки без активной задачи.",
            f"Проверено: {datetime.now(MOSCOW).strftime('%Y-%m-%d %H:%M')}",
            f"Ответственный: {responsible or 'не указан'}",
            f"Контакт: {contact_name or 'не указан'}",
            f"Телефон: {phone or 'не указан'}",
            f"Бюджет: {price or 0} руб.",
            f"Последняя активность: {from_unix(lead.get('updated_at')) or 'не указана'}",
            "",
            f"Следующий шаг: {next_step}",
        ]
    )
    return {
        "lead_id": str(lead_id),
        "task_text": task_text[:1000],
        "note_text": note[:4096],
        "report_line": report_line,
        "next_step": next_step,
    }


async def build_full_card(client: AmoCrmClient, lead: dict[str, Any]) -> dict[str, Any]:
    lead_id = lead["id"]
    detailed = await client.get_lead(lead_id, "contacts,tags")
    embedded_contacts = (detailed.get("_embedded") or {}).get("contacts") or []
    contacts = []
    for contact in embedded_contacts[:3]:
        contact_id = contact.get("id")
        if not contact_id:
            continue
        try:
            contacts.append(await client.get_contact(contact_id))
        except Exception:
            contacts.append(contact)
    notes = await client.lead_notes(lead_id, limit=20)
    return {"lead": detailed, "contacts": contacts, "notes": notes}


async def send_telegram_report(settings: Settings, text: str) -> None:
    chat_ids = settings.amocrm_task_report_chat_ids or settings.owner_telegram_user_ids
    if not settings.telegram_bot_token or not chat_ids:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    chunks = [text[index : index + 3900] for index in range(0, len(text), 3900)] or [text]
    async with httpx.AsyncClient(timeout=20) as client:
        for chat_id in chat_ids:
            for chunk in chunks:
                await client.post(url, json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True})


async def run_agent(settings: Settings, dry_run: bool = False, limit: int = 50, send_report: bool = True) -> dict[str, Any]:
    amo = AmoCrmClient(settings)
    if not amo.enabled:
        raise RuntimeError(amo.disabled_reason() or "amoCRM sync is disabled")

    users_task = asyncio.create_task(paginated(amo, "/api/v4/users", "users"))
    leads_task = asyncio.create_task(paginated(amo, "/api/v4/leads", "leads", {"with": "contacts,tags"}))
    tasks_task = asyncio.create_task(
        paginated(
            amo,
            "/api/v4/tasks",
            "tasks",
            {
                "filter[is_completed]": 0,
            },
        )
    )

    users = users_by_id(await users_task)
    leads = await leads_task
    tasks = await tasks_task
    target_leads = leads_without_active_tasks(leads, tasks)[: max(0, limit)]
    base_url = account_base(settings.amocrm_base_url)
    due_at = _tomorrow_due_timestamp(settings.amocrm_task_due_hour)

    processed = []
    errors = []
    for lead in target_leads:
        lead_id = lead.get("id")
        try:
            card = await build_full_card(amo, lead)
            analysis = build_deal_analysis(card, users, base_url)
            if not dry_run:
                await amo.add_lead_note(lead_id, analysis["note_text"])
                await amo.add_task(
                    lead_id,
                    analysis["task_text"],
                    complete_till=due_at,
                    responsible_user_id=card["lead"].get("responsible_user_id"),
                )
            processed.append(analysis)
        except Exception as exc:
            errors.append({"lead_id": lead_id, "error": str(exc)})

    report_lines = [
        "Ежедневный контроль сделок без задач",
        f"Дата: {datetime.now(MOSCOW).strftime('%Y-%m-%d %H:%M')}",
        f"Найдено без активных задач: {len(target_leads)}",
        f"Поставлено задач: {0 if dry_run else len(processed)}",
        "",
    ]
    if processed:
        report_lines.append("Сделки:")
        report_lines.extend(item["report_line"] for item in processed)
    if errors:
        report_lines.extend(["", "Ошибки:"])
        report_lines.extend(f"- {item['lead_id']}: {item['error']}" for item in errors)
    report = "\n".join(report_lines).strip()
    if send_report:
        await send_telegram_report(settings, report)

    return {
        "dry_run": dry_run,
        "found_without_tasks": len(target_leads),
        "tasks_created": 0 if dry_run else len(processed),
        "processed_leads": [item["lead_id"] for item in processed],
        "errors": errors,
        "report": report,
    }


async def run() -> None:
    parser = argparse.ArgumentParser(description="Analyze amoCRM leads without active tasks and create next-step tasks.")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and report without writing notes or tasks.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--no-telegram-report", action="store_true")
    args = parser.parse_args()

    settings = load_settings(require_bot=False)
    result = await run_agent(settings, dry_run=args.dry_run, limit=args.limit, send_report=not args.no_telegram_report)
    printable = {key: value for key, value in result.items() if key != "report"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
