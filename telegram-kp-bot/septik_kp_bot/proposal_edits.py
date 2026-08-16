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
REMOVE_PREFIX_RE = re.compile(r"^(?:убери|убрать|удали|удалить|без)\s+", re.IGNORECASE)
REPLACE_RE = re.compile(r"(?:замени|заменить|поменяй|поменять)\s+(?P<old>.+?)\s+на\s+(?P<new>.+)", re.IGNORECASE)
PRICE_RE = re.compile(r"(?:по|цена|стоимость|за|на)\s*(\d[\d\s]{2,})(?:\s*(?:р|руб|₽))?", re.IGNORECASE)
QTY_RE = re.compile(r"(\d+(?:[,.]\d+)?)\s*(м|метр(?:а|ов)?|шт|штук[аи]?|рейс(?:а|ов)?|тонн[аы]?|т|услуг[ауы]?|меш(?:ок|ка|ков)?)\b", re.IGNORECASE)
DIAMETER_RE = re.compile(r"(?:d\s*=?\s*)?(\d+(?:[,.]\d+)?)\s*(?:м|метр(?:а|ов)?)\b", re.IGNORECASE)


def _copy(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", " ", text.lower().replace("ё", "е")).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in _norm(text).split() if len(token) > 1]


def _token_matches(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.isdigit() or right.isdigit():
        return False
    if len(left) >= 4 and len(right) >= 4 and left[:5] == right[:5]:
        return True
    return len(left) >= 6 and len(right) >= 6 and (left.startswith(right) or right.startswith(left))


def _score_match(needle: str, text: str) -> tuple[int, int]:
    query_tokens = _tokens(text)
    score = 0
    alpha_score = 0
    for token in _tokens(needle):
        if any(_token_matches(token, query_token) for query_token in query_tokens):
            score += 1
            if not token.isdigit():
                alpha_score += 1
    return score, alpha_score


def _parse_money(value: str) -> int:
    return int(Decimal(re.sub(r"\D", "", value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _row_item_id(row: dict[str, Any]) -> str:
    return str(row.get("catalog_item_id") or row.get("price_item_id") or "").strip()


def _row_name(row: dict[str, Any], catalog: dict[str, Any]) -> str:
    item = catalog.get("items", {}).get(_row_item_id(row))
    return str(row.get("name") or (item or {}).get("name") or "").strip()


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
        scored = []
        query_token_count = len([token for token in _tokens(text) if token not in {"добавь", "добавить", "замени", "поменяй", "на"}])
        query_numbers = {token for token in _tokens(text) if token.isdigit()}
        threshold = 1 if query_token_count <= 1 else 2
        for item in _catalog_candidates(catalog):
            item_numbers = {token for token in _tokens(item["needle"]) if token.isdigit()}
            if item_numbers and query_numbers and item_numbers.isdisjoint(query_numbers):
                continue
            score, alpha_score = _score_match(item["needle"], text)
            if alpha_score and score >= threshold:
                unmatched = max(len(_tokens(item["needle"])) - score, 0)
                scored.append((score, unmatched, item["length"], item))
        matches = [item for _, _, _, item in sorted(scored, key=lambda row: (-row[0], row[1], row[2]))]
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
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        name = _row_name(row, catalog)
        if not name:
            continue
        score, alpha_score = _score_match(name, text)
        if alpha_score:
            scored.append((score, row))
    return max(scored, key=lambda item: item[0])[1] if scored else None


def _find_row_with_section(payload: dict[str, Any], text: str, catalog: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for section in ("materials", "works"):
        row = _find_row(payload.setdefault(section, []), text, catalog)
        if row:
            return section, row
    return None


def _section_for_item(item: dict[str, Any] | None, text: str) -> str:
    normalized = _norm(text)
    if item and item.get("category") == "works":
        return "works"
    if any(word in normalized for word in ("работ", "монтаж", "проклад", "копк", "доставк", "экскаватор")):
        return "works"
    return "materials"


def _clear_resolved_fields(row: dict[str, Any]) -> None:
    for key in ("price_item_id", "number", "unit_price", "total", "display_unit_price", "display_total", "price_source"):
        row.pop(key, None)


def _format_size(value: str) -> str:
    return value.replace(".", ",")


def _manual_name_for_attribute(row: dict[str, Any], catalog: dict[str, Any], text: str) -> str:
    source_name = _row_name(row, catalog)
    diameter = DIAMETER_RE.search(text)
    if diameter and "кольц" in _norm(source_name):
        return f"ЖБИ кольцо D = {_format_size(diameter.group(1).replace(',', '.'))} м"
    if diameter and "крышк" in _norm(source_name):
        return f"ЖБИ крышка D = {_format_size(diameter.group(1).replace(',', '.'))} м"
    return text.strip(" .,:;") or source_name or "Позиция требует уточнения"


def _manual_name_from_clause(clause: str) -> str:
    diameter = DIAMETER_RE.search(clause)
    normalized = _norm(clause)
    if diameter and "кольц" in normalized:
        return f"ЖБИ кольцо D = {_format_size(diameter.group(1).replace(',', '.'))} м"
    if diameter and "крышк" in normalized:
        return f"ЖБИ крышка D = {_format_size(diameter.group(1).replace(',', '.'))} м"
    return ADD_PREFIX_RE.sub("", clause).strip(" .,:;") or "Новая позиция"


def _set_catalog_row(row: dict[str, Any], item: dict[str, Any], quantity: str | None = None, manual_price: int | None = None) -> None:
    _clear_resolved_fields(row)
    row["catalog_item_id"] = item["id"]
    row["name"] = item["name"]
    row["unit"] = item["unit"]
    if quantity is not None:
        row["quantity"] = quantity
    elif item["category"] == "equipment":
        row["quantity"] = "1"
    row["price_kind"] = "money"
    row["manual_unit_price"] = manual_price
    row["note"] = "Правка человека: позиция заменена"


def _set_manual_row(row: dict[str, Any], name: str, unit: str, quantity: str, manual_price: int | None, note: str) -> None:
    _clear_resolved_fields(row)
    row["catalog_item_id"] = ""
    row["name"] = name
    row["unit"] = unit
    row["quantity"] = quantity
    row["price_kind"] = "money"
    row["manual_unit_price"] = manual_price
    row["note"] = note


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
    is_ring_diameter = item is None and "кольц" in _norm(clause) and qty_match and qty_match.group(2).lower().startswith(("м", "метр"))
    quantity = "1" if is_ring_diameter else (qty_match.group(1).replace(",", ".") if qty_match else "1")
    unit = "шт" if is_ring_diameter else (qty_match.group(2) if qty_match else (item or {}).get("unit") or "шт")
    if item and str(item["id"]).startswith(("sand_delivery_", "gravel_")):
        quantity = "1"
        unit = item["unit"]
    if item and item["category"] == "equipment":
        quantity = "1"
        unit = item["unit"]

    price = _parse_money(price_match.group(1)) if price_match else (item or {}).get("price")
    price_kind = "money"
    manual_price = price if price not in (None, "") else None

    if existing:
        existing["quantity"] = quantity
        if manual_price not in (None, ""):
            existing["manual_unit_price"] = manual_price
        existing["price_kind"] = price_kind
        existing["note"] = "Правка человека: позиция обновлена"
        return True

    clean_name = _manual_name_from_clause(clause)
    if price_match:
        clean_name = _manual_name_from_clause(PRICE_RE.sub("", ADD_PREFIX_RE.sub("", clause), count=1).strip(" .,:;"))
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


def _apply_remove_line(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> dict[str, Any] | None:
    if not REMOVE_PREFIX_RE.search(correction):
        return None
    target_text = REMOVE_PREFIX_RE.sub("", correction, count=1).strip() or correction
    found = _find_row_with_section(payload, target_text, catalog)
    if not found:
        return None
    section, row = found
    payload[section] = [candidate for candidate in payload.get(section, []) if candidate is not row]
    return {"type": "remove_item", "section": section, "item_name": _row_name(row, catalog)}


def _apply_replace_item(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> dict[str, Any] | None:
    match = REPLACE_RE.search(correction)
    if not match:
        return None
    old_text = match.group("old").strip()
    new_text = match.group("new").strip()
    found = _find_row_with_section(payload, old_text, catalog)
    if not found:
        return None
    section, row = found
    price_match = PRICE_RE.search(new_text)
    manual_price = _parse_money(price_match.group(1)) if price_match else None
    qty_match = QTY_RE.search(new_text)
    quantity = qty_match.group(1).replace(",", ".") if qty_match and not qty_match.group(2).lower().startswith(("м", "метр")) else row.get("quantity", "1")
    old_item = catalog.get("items", {}).get(_row_item_id(row)) or {}
    preferred_category = str(old_item.get("category") or section)
    item = _find_catalog_item(new_text, catalog, prefer=preferred_category)
    if item:
        _set_catalog_row(row, item, str(quantity), manual_price)
        return {"type": "replace_item", "section": section, "from": old_text, "to": item["name"]}

    unit = str(row.get("unit") or "шт")
    name = _manual_name_for_attribute(row, catalog, new_text)
    _set_manual_row(row, name, unit, str(quantity), manual_price, "Правка человека: замена требует цены из прайса")
    return {"type": "replace_item", "section": section, "from": old_text, "to": name, "needs_price": manual_price is None}


def _apply_attribute_change(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> dict[str, Any] | None:
    normalized = _norm(correction)
    if "кольц" not in normalized or not DIAMETER_RE.search(correction):
        return None
    found = _find_row_with_section(payload, "кольцо", catalog)
    if not found:
        return None
    section, row = found
    name = _manual_name_for_attribute(row, catalog, correction)
    if name == _row_name(row, catalog):
        return None
    _set_manual_row(
        row,
        name,
        str(row.get("unit") or "шт"),
        str(row.get("quantity") or "1"),
        None,
        "Правка человека: изменение атрибута требует цены из прайса",
    )
    return {"type": "change_attribute", "section": section, "item_name": name, "needs_price": True}


def _apply_quantity_change(payload: dict[str, Any], catalog: dict[str, Any], correction: str) -> dict[str, Any] | None:
    if any(word in _norm(correction) for word in ("скидк", "цен", "стоим")):
        return None
    qty_match = QTY_RE.search(correction)
    if not qty_match:
        return None
    found = _find_row_with_section(payload, correction, catalog)
    if not found:
        return None
    section, row = found
    requested_unit = qty_match.group(2).lower()
    row_unit = str(row.get("unit") or "").lower()
    if requested_unit.startswith(("м", "метр")) and row_unit not in ("м", "метр", "метров"):
        return None
    row["quantity"] = str(normalize_quantity(qty_match.group(1)))
    row["note"] = "Правка человека: изменено количество"
    return {"type": "change_quantity", "section": section, "item_name": _row_name(row, catalog), "quantity": row["quantity"]}


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
    edits: list[dict[str, Any]] = []
    replace_edit = _apply_replace_item(payload, catalog, correction_text)
    if replace_edit:
        applied.append("replace_item")
        edits.append(replace_edit)

    remove_edit = _apply_remove_line(payload, catalog, correction_text)
    if remove_edit:
        applied.append("remove_item")
        edits.append(remove_edit)

    attribute_edit = None if replace_edit else _apply_attribute_change(payload, catalog, correction_text)
    if attribute_edit:
        applied.append("change_attribute")
        edits.append(attribute_edit)

    for clause in [part.strip() for part in ADD_SPLIT_RE.split(correction_text) if part.strip()]:
        if ADD_PREFIX_RE.search(clause) and _append_or_update_row(payload, catalog, clause):
            applied.append("add_or_update_line")
            edits.append({"type": "add_item", "text": ADD_PREFIX_RE.sub("", clause).strip(" .,:;")})

    if _apply_price_change(payload, catalog, correction_text):
        applied.append("manual_price")
        edits.append({"type": "change_price"})

    if _apply_discount(payload, catalog, correction_text):
        applied.append("discount")
        edits.append({"type": "apply_discount"})

    quantity_edit = _apply_quantity_change(payload, catalog, correction_text)
    if quantity_edit:
        applied.append("change_quantity")
        edits.append(quantity_edit)

    warnings = [{"type": "human_correction_applied", "rules": sorted(set(applied)), "edits": edits}] if applied else []
    return payload, warnings
