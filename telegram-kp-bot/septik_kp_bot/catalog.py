from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


MONEY_KINDS = {"money"}
ZERO_KINDS = {"gift", "customer", "fact", "dash"}


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_catalog(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for item_id, item in catalog.get("items", {}).items():
        price = item.get("standard_price")
        if price is None and item.get("standard_price_from") is not None:
            price = f"от {item['standard_price_from']}"
        items.append(
            {
                "id": item_id,
                "category": item.get("category"),
                "name": item.get("name"),
                "aliases": item.get("aliases", [])[:6],
                "unit": item.get("unit"),
                "standard_price": price,
            }
        )
    return items


def format_rub(value: int | Decimal | None) -> str:
    if value is None:
        return "—"
    amount = int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{amount:,}".replace(",", " ") + " р."


def normalize_quantity(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("1")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return Decimal("1")
    return Decimal(match.group(0))


def display_quantity(value: Any) -> str:
    qty = normalize_quantity(value)
    if qty == qty.to_integral():
        return str(int(qty))
    return str(qty.normalize()).replace(".", ",")


def _display_for_kind(kind: str) -> str:
    if kind == "gift":
        return "В подарок"
    if kind == "customer":
        return "от заказчика"
    if kind == "fact":
        return "По факту"
    return "—"


def resolve_rows(rows: list[dict[str, Any]], catalog: dict[str, Any], section: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    items = catalog.get("items", {})

    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("catalog_item_id") or row.get("price_item_id") or "").strip()
        item = items.get(item_id) if item_id else None
        price_kind = str(row.get("price_kind") or "money").strip()
        if price_kind not in MONEY_KINDS | ZERO_KINDS:
            price_kind = "money"

        quantity = normalize_quantity(row.get("quantity"))
        display_qty = display_quantity(row.get("quantity"))
        name = str(row.get("name") or (item or {}).get("name") or "").strip()
        unit = str(row.get("unit") or (item or {}).get("unit") or "шт").strip()
        note = row.get("note")
        manual_price = row.get("manual_unit_price")
        price_source = "manual_override" if manual_price not in (None, "") else "price_catalog"

        if item:
            name = str(item.get("name") or name)
            unit = str(item.get("unit") or unit)
            standard_price = item.get("standard_price")
            if manual_price in (None, ""):
                manual_price = standard_price
        elif manual_price in (None, "") and price_kind == "money":
            warnings.append(
                {
                    "type": "missing_price_request",
                    "section": section,
                    "item_name": name or "Неизвестная позиция",
                    "category": "materials" if section == "materials" else "works",
                    "blocking": True,
                }
            )
            price_kind = "fact"
            price_source = "missing"

        if price_kind == "money" and manual_price not in (None, ""):
            unit_price = int(Decimal(str(manual_price)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            total = int((Decimal(unit_price) * quantity).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            display_unit_price = format_rub(unit_price)
            display_total = format_rub(total)
        else:
            unit_price = None
            total = 0
            display_unit_price = _display_for_kind(price_kind)
            display_total = _display_for_kind(price_kind)

        resolved.append(
            {
                "number": index,
                "name": name or "Позиция требует уточнения",
                "unit": unit,
                "quantity": display_qty,
                "unit_price": unit_price,
                "total": total,
                "display_unit_price": display_unit_price,
                "display_total": display_total,
                "price_kind": price_kind,
                "price_source": price_source,
                "price_item_id": item_id or None,
                "note": note,
            }
        )

    return resolved, warnings


def build_payload(ai_payload: dict[str, Any], catalog: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    materials, mat_warnings = resolve_rows(ai_payload.get("materials", []), catalog, "materials")
    works, work_warnings = resolve_rows(ai_payload.get("works", []), catalog, "works")
    materials_total = sum(int(row.get("total") or 0) for row in materials if row.get("price_kind") == "money")
    works_total = sum(int(row.get("total") or 0) for row in works if row.get("price_kind") == "money")
    client = ai_payload.get("client") or {}
    flags = ai_payload.get("flags") or {}

    payload = {
        "client": {
            "name": str(client.get("name") or "—"),
            "address": str(client.get("address") or "—"),
            "phone": str(client.get("phone") or "—"),
            "date": str(client.get("date") or ""),
        },
        "materials": materials,
        "works": works,
        "totals": {
            "materials": materials_total,
            "works": works_total,
            "grand_total": materials_total + works_total,
        },
        "flags": {
            "preliminary": bool(flags.get("preliminary", True)),
            "needs_layout_review": len(materials) > 12 or len(works) > 8,
            "client_delivery_allowed": False,
            "keep_forever": False,
        },
    }
    return payload, mat_warnings + work_warnings


def calculation_text(payload: dict[str, Any], missing_data: list[str], warnings: list[dict[str, Any]]) -> str:
    client = payload["client"]
    totals = payload["totals"]
    lines = [
        "Черновик КП",
        "",
        f"Клиент: {client.get('name') or '—'}",
        f"Адрес: {client.get('address') or '—'}",
        f"Телефон: {client.get('phone') or '—'}",
        "",
        "Материалы:",
    ]
    for row in payload["materials"]:
        lines.append(f"{row['number']}. {row['name']} — {row['quantity']} {row['unit']} — {row['display_total']}")

    lines.extend(["", f"Итого материалы: {format_rub(totals['materials'])}", "", "Работы:"])
    for row in payload["works"]:
        lines.append(f"{row['number']}. {row['name']} — {row['quantity']} {row['unit']} — {row['display_total']}")

    lines.extend(
        [
            "",
            f"Итого работы: {format_rub(totals['works'])}",
            f"Итого по текущим данным: {format_rub(totals['grand_total'])}",
        ]
    )

    if missing_data:
        lines.extend(["", "Нужно уточнить:"])
        lines.extend(f"- {item}" for item in missing_data)

    blocking = [item for item in warnings if item.get("blocking")]
    if blocking:
        lines.extend(["", "Позиции без цены:"])
        lines.extend(f"- {item.get('item_name')}" for item in blocking)

    lines.append("")
    lines.append("Проверь расчет. После кнопки Ок я сделаю PNG.")
    return "\n".join(lines)
