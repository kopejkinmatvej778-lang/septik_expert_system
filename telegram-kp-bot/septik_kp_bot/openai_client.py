from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .catalog import build_payload, calculation_text, compact_catalog
from .proposal_edits import apply_human_correction_rules


PROPOSAL_SYSTEM_PROMPT = """Ты se.proposal_master для ООО "Септик Эксперт".

Нужно разобрать текст/транскрипт замера и вернуть строго JSON для черновика КП.

Правила:
- Не придумывай цены. Для обычных позиций выбирай catalog_item_id из каталога.
- Если человек явно написал цену, можно вернуть manual_unit_price.
- Если человек написал скидку в процентах, ручную цену, "добавь позицию", "замени цену", обязательно отрази это в строках расчета.
- Если позиция есть, но цену нельзя определить, верни ее без catalog_item_id и без manual_unit_price.
- Разделяй materials и works.
- Для станции автономной канализации по умолчанию включай работы `earthworks_station` и `station_installation`, если человек явно не написал, что котлован готов, земляные работы не нужны или монтаж не требуется.
- Если во входе есть previous_payload и human_correction, считай previous_payload текущей версией КП. Примени human_correction и верни полную новую версию, сохранив остальные позиции.
- Не добавляй скидки и подарки, если человек явно не попросил.
- Скидку можно применять только при явной просьбе человека. Если скидка общая, добавь отдельную денежную строку со знаком минус. Если скидка относится к конкретной позиции, измени цену этой позиции.
- Если не хватает имени, адреса, телефона или важных технических данных, добавь это в missing_data.
- Дату ставь из current_date.

Верни JSON такой формы:
{
  "client": {"name": "", "address": "", "phone": "", "date": "YYYY-MM-DD"},
  "materials": [
    {
      "catalog_item_id": "id из каталога или пусто",
      "name": "название",
      "unit": "шт|м|услуга|...",
      "quantity": "1",
      "price_kind": "money|gift|customer|fact|dash",
      "manual_unit_price": null,
      "note": null
    }
  ],
  "works": [],
  "missing_data": [],
  "flags": {"preliminary": true}
}
"""


NEGATIVE_EARTHWORKS_PHRASES = (
    "готовый котлован",
    "котлован готов",
    "без земляных",
    "без земляных работ",
    "земляные не нужны",
    "экскаватор не нужен",
    "без экскаватора",
    "в готовый котлован",
)


def _has_catalog_item(rows: list[dict[str, Any]], item_id: str) -> bool:
    return any(str(row.get("catalog_item_id") or row.get("price_item_id") or "") == item_id for row in rows)


def _has_station(rows: list[dict[str, Any]]) -> bool:
    return any(str(row.get("catalog_item_id") or row.get("price_item_id") or "").startswith("station_") for row in rows)


def apply_business_defaults(ai_payload: dict[str, Any], source_text: str, correction: str | None) -> dict[str, Any]:
    payload = json.loads(json.dumps(ai_payload, ensure_ascii=False))
    materials = payload.setdefault("materials", [])
    works = payload.setdefault("works", [])
    combined_text = f"{source_text}\n{correction or ''}".lower()
    has_station = _has_station(materials)
    skip_earthworks = any(phrase in combined_text for phrase in NEGATIVE_EARTHWORKS_PHRASES)

    if has_station and not skip_earthworks and not _has_catalog_item(works, "earthworks_station"):
        works.insert(
            0,
            {
                "catalog_item_id": "earthworks_station",
                "name": "Земляные работы экскаватором",
                "unit": "услуга",
                "quantity": "1",
                "price_kind": "money",
                "manual_unit_price": None,
                "note": "Добавлено по стандартному составу работ для станции",
            },
        )

    if has_station and not _has_catalog_item(works, "station_installation"):
        works.append(
            {
                "catalog_item_id": "station_installation",
                "name": "Монтаж станции",
                "unit": "услуга",
                "quantity": "1",
                "price_kind": "money",
                "manual_unit_price": None,
                "note": "Добавлено по стандартному составу работ для станции",
            },
        )

    return payload


async def openai_chat_json(api_key: str, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


async def transcribe_audio(api_key: str, model: str, audio_path: Path) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        with audio_path.open("rb") as fh:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": model, "language": "ru", "response_format": "json"},
                files={"file": (audio_path.name, fh, "audio/ogg")},
            )
    response.raise_for_status()
    data = response.json()
    return str(data.get("text") or "").strip()


async def make_proposal(
    api_key: str,
    model: str,
    catalog: dict[str, Any],
    source_text: str,
    previous: dict[str, Any] | None = None,
    correction: str | None = None,
) -> dict[str, Any]:
    current_date = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
    catalog_items = compact_catalog(catalog)
    user_payload = {
        "current_date": current_date,
        "catalog_items": catalog_items,
        "source_text": source_text,
        "previous_payload": previous.get("payload") if previous else None,
        "previous_draft_text": previous.get("calculation_text") if previous else None,
        "human_correction": correction or "",
    }
    ai_payload = await openai_chat_json(
        api_key,
        model,
        [
            {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    ai_payload = apply_business_defaults(ai_payload, source_text, correction)
    ai_payload, correction_warnings = apply_human_correction_rules(ai_payload, catalog, correction)
    payload, warnings = build_payload(ai_payload, catalog)
    missing_data = [str(item) for item in ai_payload.get("missing_data", []) if str(item).strip()]
    draft_text = calculation_text(payload, missing_data, warnings)
    return {
        "payload": payload,
        "calculation_text": draft_text,
        "missing_data": missing_data,
        "warnings": correction_warnings + warnings,
        "ai_payload": ai_payload,
    }
