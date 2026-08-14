# Contract JSON schema

Use these shapes for API contracts and agent outputs.

## Request

```json
{
  "action": "create_from_last_proposal",
  "contract_id": "optional-uuid",
  "source": "telegram|web|amocrm|internal",
  "requester": {
    "user_id": "internal-id",
    "role": "owner|manager",
    "telegram_chat_id": "optional"
  },
  "client_search": {
    "client_id": "optional",
    "amo_lead_id": 123456,
    "name": "Иван Иванов",
    "phone": "+79990000000",
    "address": "Нагаево"
  },
  "proposal": {
    "proposal_id": "uuid",
    "status": "stored",
    "approved_by_human": true,
    "payload": {}
  },
  "identity_data_raw": "optional raw text",
  "identity_data": {},
  "template": "supply_with_installation_v1",
  "contract_number": "optional",
  "contract_date": "2026-08-13",
  "montage_date": "2026-08-20",
  "payment_terms": {},
  "owner_override": false
}
```

## Response

```json
{
  "agent": "se.contract_master",
  "ok": true,
  "status": "ready_for_render|needs_data|needs_human_attention|error",
  "summary": "...",
  "data": {
    "contract_id": "uuid",
    "used_proposal_id": "uuid",
    "contract_data": {},
    "render_request": {},
    "missing_data": []
  },
  "next_actions": [],
  "warnings": [],
  "errors": []
}
```

## Contract data

```json
{
  "contract_number": "82",
  "contract_date": "2026-08-13",
  "contract_date_text": "«13» августа 2026 года",
  "template": "supply_with_installation_v1",
  "seller": {
    "short_name": "ООО «Септик Эксперт»",
    "full_name": "Общество с ограниченной ответственностью «Септик Эксперт»",
    "director": "Копейкин Егор Дмитриевич",
    "director_short": "Копейкин Е.Д.",
    "basis": "Устава",
    "requisites": {}
  },
  "buyer": {
    "type": "individual|company",
    "full_name": "Иванов Иван Иванович",
    "short_name": "Иванов И.И.",
    "passport": {},
    "company": {},
    "phone": "+79990000000"
  },
  "object_address": "Нагаево",
  "materials": [],
  "works": [],
  "totals": {
    "materials": 0,
    "works": 0,
    "grand_total": 0,
    "grand_total_display": "270 000,00 р.",
    "grand_total_words": "двести семьдесят тысяч"
  },
  "payment_terms": {
    "prepayment": null,
    "deadline": null,
    "text": "Оплата в размере 100% цены Договора..."
  },
  "montage_terms": {
    "montage_date": "2026-08-20",
    "deadline_text": "по согласованию сторон"
  },
  "appendices": {
    "materials_act": true,
    "works_act": true
  }
}
```

## Render request

```json
{
  "render_engine": "docx_template_to_pdf|reportlab_pdf",
  "template": "supply_with_installation_v1",
  "contract_id": "uuid",
  "output_formats": ["docx", "pdf"],
  "contract_data": {}
}
```

## Next actions

```json
[
  {
    "type": "enqueue_job",
    "queue": "contract.render",
    "payload": {}
  },
  {
    "type": "store_contract",
    "after": "rendered"
  },
  {
    "type": "create_montage_row",
    "after": "issued"
  },
  {
    "type": "link_to_amocrm",
    "after": "stored"
  }
]
```
