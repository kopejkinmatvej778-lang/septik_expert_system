# Proposal JSON schema

Use these shapes for API contracts and agent outputs.

## Request

```json
{
  "action": "make_text_calculation",
  "proposal_id": "optional-uuid",
  "source": "telegram|web|amocrm|internal",
  "requester": {
    "user_id": "internal-id",
    "role": "owner|manager|measurer",
    "telegram_chat_id": "optional"
  },
  "client": {
    "client_id": "optional",
    "amo_lead_id": 123456,
    "amo_contact_id": 123456,
    "name": "Иван",
    "phone": "+79990000000",
    "address": "Нагаево"
  },
  "measurement": {
    "measurement_id": "optional",
    "summary": "...",
    "recommended_equipment": "Аэролос Био 4",
    "soil": "глина",
    "groundwater": "высокая",
    "pipe_depth": "не указано",
    "distances": {},
    "risks": [],
    "photos": []
  },
  "price_rules": {
    "version": "2026-08-13",
    "catalog_path": "references/price-catalog.json",
    "allow_discount": false,
    "items": [],
    "manual_overrides": [
      {
        "item_name": "optional",
        "custom_price": 0,
        "discount": 0,
        "gift": false,
        "approved_by": "owner|manager"
      }
    ]
  },
  "previous_calculation_text": "",
  "human_correction": "",
  "approved_by_human": false
}
```

## Response

```json
{
  "agent": "se.proposal_master",
  "ok": true,
  "status": "draft_text|needs_human_correction|approved_for_render|rendering|rendered|error",
  "summary": "...",
  "data": {
    "proposal_id": "uuid",
    "proposal_version_id": "uuid",
    "calculation_text": "...",
    "proposal_payload": {},
    "render_request": null,
    "missing_data": [],
    "missing_price_request": null,
    "price_catalog_update_request": null
  },
  "next_actions": [],
  "warnings": [],
  "errors": []
}
```

## Proposal payload

```json
{
  "client": {
    "name": "Иван",
    "address": "Нагаево",
    "phone": "+79990000000",
    "date": "2026-08-13"
  },
  "materials": [
    {
      "number": 1,
      "name": "Станция «АЭРОЛОС БИО 4»",
      "unit": "шт",
      "quantity": "1",
      "unit_price": 156000,
      "total": 156000,
      "display_unit_price": "156 000 р.",
      "display_total": "156 000 р.",
      "price_kind": "money",
      "price_source": "price_catalog|manual_override|previous_confirmed_proposal",
      "price_item_id": "station_aerolos_bio_4",
      "note": null
    }
  ],
  "works": [
    {
      "number": 1,
      "name": "Земляные работы экскаватором",
      "unit": "услуга",
      "quantity": "1",
      "unit_price": 21000,
      "total": 21000,
      "display_unit_price": "21 000 р.",
      "display_total": "21 000 р.",
      "price_kind": "money",
      "note": null
    }
  ],
  "totals": {
    "materials": 0,
    "works": 0,
    "grand_total": 0
  },
  "flags": {
    "preliminary": false,
    "needs_layout_review": false,
    "client_delivery_allowed": false,
    "keep_forever": false
  }
}
```

## Missing price request

If a requested line is absent from `references/price-catalog.json`, return this shape and do not invent a price:

```json
{
  "type": "missing_price_request",
  "item_name": "Новая позиция",
  "category": "equipment|materials|works",
  "unit": "шт",
  "quantity": 1,
  "context": "Нужно для КП по клиенту ...",
  "blocking": true
}
```

After a human supplies the ordinary price, return:

```json
{
  "type": "price_catalog_update_request",
  "item_name": "Новая позиция",
  "category": "materials",
  "unit": "шт",
  "standard_price": 10000,
  "aliases": ["Новая позиция"],
  "source": "human_input",
  "approved_by": "owner|manager"
}
```

## Render request

```json
{
  "render_engine": "pillow_png_template",
  "template": "septik_expert_kp_v1",
  "proposal_id": "uuid",
  "payload": {}
}
```

## Next actions

```json
[
  {
    "type": "enqueue_job",
    "queue": "proposal.render_png",
    "payload": {}
  },
  {
    "type": "send_telegram_photo",
    "after": "rendered",
    "chat_id": "..."
  },
  {
    "type": "store_document",
    "after": "rendered"
  },
  {
    "type": "link_to_amocrm",
    "after": "stored"
  }
]
```
