from __future__ import annotations

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .catalog import build_payload, normalize_quantity


DISCOUNT_WORD_RE = re.compile(r"(скидк|скинуть|сниз|минус)", re.IGNORECASE)
PERCENT_DISCOUNT_RE = re.compile(r"(?:скидк\w*|скинуть|сниз\w*|минус)\D{0,24}(\d+(?:[,.]\d+)?)\s*%", re.IGNORECASE)
MONEY_DISCOUNT_RE = re.compile(r"(?:скидк\w*|скинуть|сниз\w*|минус)\D{0,24}(\d[\d\s]{2,})(?:\s*(?:р|руб|₽))?", re.IGNORECASE)
ADD_SPLIT_RE = re.compile(r"(?=(?:^|[;,.]\s*|\s+и\s+)(?:добавь|добавить|добавляем|добавим)\b)", re.IGNORECASE)
ADD_PREFIX_RE = re.compile(r"^(?:[;,.]\s*|\s+и\s+)?(?:добавь|добавить|добавляем|добавим)\s+", re.IGNORECASE)
PRICE_RE = re.compile(r"(?:по|цена|стоимость|за|на)\s*(\d[\d\s]{2,})(?:\s*(?:р|руб|₽))?", re.IGNORECASE)
QTY_RE = re.compile(r"(\d+(?:[,.]\d+)?)\s*(м|метр(?:а|ов)?|шт|штук[аи]?|рейс(?:а|ов)?|тонн[аы]?|т|услуг[ауы]?|меш(?:ок|ка|ков)?)\b", re.IGNORECASE)


def _copy(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", " ", text.lower().replace("ё", "е")).strip()


def _parse_money(value: str) -> int:
    return int(Decimal(re.sub(r"\D", "", value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _row_item_id(row: dict[str, Any]) -> str:
    return str(row.get("catalog_item_id") or row.get("price_item_id") or "").strip()


def _row_unit_price(row: dict[str, Any], catalog: dict[str, Any]) -> int | None:
    for key in ("manual_unit_price", "unit_price"):
        value = row.get(key)
        if value not in (None, ""):
            return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    item = catalog.get("items", {}).get(_row_item_id(row))
    price = (item or {}).get("standard_price")
    if price not in (None, ""):
        return int(Decimal(str(price)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return None


def _catalog_candidates(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item_id, item in catalog.get("items", {}).items():
        names = [str(item.get("name") or ""), *[str(alias) for alias in item.get("aliases", [])]]
        for name in names:
            normalized = _norm(name)
            if normalized:
                result.append(
                    {
                        "id": item_id,
                        "name": str(item.get("name") or name),
                        "unit": str(item.get("unit") or "шт"),
                        "category": str(item.get("category") or "materials"),
                        "price": item.get("standard_price"),
                        "needle": normalized,
                        "length": len(normalized),
                    }
                )
    return sorted(result, key=lambda item: item["length"], reverse=True)


def _find_catalog_item(text: str, catalog: dict[str, Any], prefer: str | None = None) -> dict[str, Any] | None:
    normalized = _norm(text)
    matches = [item for item in _catalog_candidates(catalog) if item["needle"] in normalized]
    if not matches:
        return None
    if prefer:
        preferred = [item for item in matches if item["category"] == prefer]
        if preferred:
            return preferred[0]
    if any(word in normalized for word in ("работ", "монтаж", "проклад", "копк", "доставк", "экскаватор")):
        work = [item for item in matches if item["category"] == "works"]
        if work:
            return work[0]
    non_work = [item for item in matches if item["category"] != "works"]
    return non_work[0] if non_work else matches[0]


def _find_row(rows: list[dict[str, Any]], text: str, catalog: dict[str, Any]) -> dict[str, Any] | None:
    item = _find_catalog_item(text, catalog)
    if item:
        for row in rows:
            if _row_item_id(row) == item["id"]:
                return row
    normalized = _norm(text)
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        name = _norm(str(row.get("name") or ""))
        if not name:
            continue
        tokens = [token for token in name.split() if len(token) > 3]
        score = sum(1 for token in tokens if token in normalized)
        if score:
            scored.append((score, row))
    return max(scored, key=lambda item: item[0])[1] if scored else None


def _section_for_item(item: dict[str, Any] | None, text: str) -> str:
    normalized = _norm(text)
    if item and item.get("category") == "works":
        return "works"
    if any(word in normalized for word in ("работ", "монтаж", "проклад", "копк", "доставк", "экскаватор")):
        return "works"
    return "materials"


def _remove_discount_rows(payload: dict[str, Any]) -> None:
    for section in ("materials", "works"):
        payload[section] = [
            row
            for row in payload.get(section, [])
            if "скидк" not in str(row.get("name") or "").lower()
            and str(row.get("note") or "") != "manual_global_discount"
        ]


def _append_or_update_row(payload: dict[str, Any], catalog: dict[str, Any], clause: str) -> bool:
    item = _find_catalog_item(clause, catalog)
    section = _section_for_item(item, clause)
    rows = payload.setdefault(section, [])
    existing = None
    if item:
        existing = next((row for row in rows if _row_item_id(row) == item["id"]), None)

    price_match = PRICE_RE.search(clause)
    qty_match = QTY_RE.search(clause)
    quantity = qty_match.group(1).replace(",", ".") if qty_match else "1"
    unit = qty_match.group(2) if qty_match else (item or {}).get("unit") or "шт"
    if item and str(item["id"]).startswith(("sand_delivery_", "gravel_")):
        quantity = "1"
        unit = item["unit"]
    if item and item["category"] == "equipment":
        quantity = "1"
        unit = item["unit"]

    price = _parse_money(price_match.group(1)) if price_match else (item or {}).get("price")
    if price in (None, "") and item is None:
        price_kind = "fact"
        manual_price = None
    else:
        price_kind = "money"
        manual_price = price if price not in (None, "") else None

    if existing:
        existing["quantity"] = quantity
        if manual_price not in (None, ""):
            existing["manual_unit_price"] = manual_price
        existing["price_kind"] = price_kind
        existing["note"] = "Правка человека: позиция обновлена"
        return True

    clean_name = ADD_PREFIX_RE.sub("", clause).strip(" .,:;")
    if price_match:
        clean_name = clean_name[: price_match.start()].strip(" .,:;")
    name = (item or {}).get("name") or clean_name or "Новая позиция"
    rows.append(
        {
            "catalog_item_id": (item or {}).get("id", ""),
            "name": name,
            "unit": unit,
            "quantity": quantity,
            "price_kind": price_kind,
            "manual_unit_price": manual_price,
            "note": "Правка человека: позиция добавлена",
        }
    )
    return True


def _apply_price_change(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> bool:
    if not any(word in _norm(correction) for word in ("цен", "стоим", "постав", "сдел", "замен", "измени")):
        return False
    price_match = PRICE_RE.search(correction)
    if not price_match:
        return False
    price = _parse_money(price_match.group(1))
    all_rows = payload.setdefault("materials", []) + payload.setdefault("works", [])
    row = _find_row(all_rows, correction, catalog)
    if not row:
        return False
    row["manual_unit_price"] = price
    row["price_kind"] = "money"
    row["note"] = "Правка человека: ручная цена"
    return True


def _apply_discount(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> bool:
    if not DISCOUNT_WORD_RE.search(correction):
        return False
    percent_match = PERCENT_DISCOUNT_RE.search(correction)
    money_match = MONEY_DISCOUNT_RE.search(correction)
    if not percent_match and not money_match:
        return False

    all_rows = payload.setdefault("materials", []) + payload.setdefault("works", [])
    target_row = _find_row(all_rows, correction, catalog)

    if percent_match and target_row:
        percent_value = Decimal(percent_match.group(1).replace(",", "."))
        old_price = _row_unit_price(target_row, catalog)
        if old_price is None:
            return False
        new_price = (Decimal(old_price) * (Decimal("100") - percent_value) / Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        target_row["manual_unit_price"] = int(new_price)
        target_row["price_kind"] = "money"
        target_row["note"] = f"Правка человека: скидка {percent_value.normalize()}%"
        return True

    _remove_discount_rows(payload)
    resolved, _ = build_payload(payload, catalog)
    base_total = int(resolved.get("totals", {}).get("grand_total") or 0)
    if base_total <= 0:
        return False

    if percent_match:
        percent_value = Decimal(percent_match.group(1).replace(",", "."))
        discount = int((Decimal(base_total) * percent_value / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        name = f"Скидка {percent_value.normalize()}%"
    else:
        discount = _parse_money(money_match.group(1)) if money_match else 0
        name = "Скидка"
    if discount <= 0:
        return False

    payload.setdefault("works", []).append(
        {
            "catalog_item_id": "",
            "name": name,
            "unit": "услуга",
            "quantity": "1",
            "price_kind": "money",
            "manual_unit_price": -discount,
            "note": "manual_global_discount",
        }
    )
    return True


def apply_human_correction_rules(
    ai_payload: dict[str, Any],
    catalog: dict[str, Any],
    correction: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _copy(ai_payload)
    correction_text = (correction or "").strip()
    if not correction_text:
        return payload, []

    applied: list[str] = []
    for clause in [part.strip() for part in ADD_SPLIT_RE.split(correction_text) if part.strip()]:
        if ADD_PREFIX_RE.search(clause) and _append_or_update_row(payload, catalog, clause):
            applied.append("add_or_update_line")

    if _apply_price_change(payload, catalog, correction_text):
        applied.append("manual_price")

    if _apply_discount(payload, catalog, correction_text):
        applied.append("discount")

    warnings = [{"type": "human_correction_applied", "rules": sorted(set(applied))}] if applied else []
    return payload, warnings
