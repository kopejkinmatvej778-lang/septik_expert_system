---
name: septik-contract-generation
description: Generate Septik Expert contracts from a confirmed commercial proposal, client identity/requisites, template selection, payment terms, and montage date. Use when Codex or an AI agent must find the latest proposal, prepare contract_data, validate passport/company details, render DOCX/PDF through API/backend workflows, store contracts permanently, create montage rows, or schedule proposal cleanup.
---

# Septik Contract Generation

Use this skill for the `se.contract_master` agent and any backend workflow that creates contracts for ООО "Септик Эксперт".

## Core workflow

```text
contract request
-> find client
-> find latest confirmed КП
-> collect passport data or company requisites
-> validate missing fields
-> prepare contract_data
-> create render_request
-> render DOCX/PDF
-> store contract permanently
-> create/update montage row in Google Sheets
-> after contract signed, schedule КП cleanup after 7 days
```

Never create a contract from guessed data.

## Tooling

Preferred production path:

```text
Python + python-docx -> DOCX
LibreOffice headless -> PDF
```

Use this when there is an approved DOCX template.

Fallback/MVP path:

```text
Python + ReportLab -> PDF
```

Use `scripts/render_contract_pdf.py` for deterministic PDF generation from `contract_data` when a DOCX template is not yet wired.

## When to read references

- Read `references/contract-workflow.md` before implementing the API flow.
- Read `references/contract-json-schema.md` before defining payloads, storage records, or render requests.
- Read `references/identity-and-requisites.md` before extracting passport data or company requisites.
- Read `references/docx-pdf-rendering.md` before changing DOCX/PDF renderers.
- Read `references/montage-and-storage-rules.md` before wiring Google Sheets, storage, or КП cleanup.

## Agent behavior

`se.contract_master` must:

- accept JSON input only;
- return JSON output only;
- require a confirmed proposal or explicit owner override;
- use the proposal as the source for equipment, works, object address, and sums;
- validate buyer identity data before render;
- create `contract_data` and `render_request`;
- include `next_actions` for render, permanent storage, montage row creation, amoCRM link, and proposal cleanup scheduling.

`se.contract_master` must not:

- invent passport data, company requisites, sums, dates, or terms;
- change the proposal sum without explicit owner approval;
- sign for the client;
- delete КП files itself;
- store contracts temporarily only;
- expose passport data to roles without permission.

## Contract template selection

Use `template`:

- `supply_with_installation_v1`: equipment/station with installation.
- `cellar_with_installation_v1`: cellar/pogreb with installation.
- `kesson_with_installation_v1`: kesson with installation.
- `materials_and_works_v1`: materials/additional works.

If template selection is uncertain, return `needs_data`.

## Final system prompt

```text
Ты se.contract_master - агент договоров ООО "Септик Эксперт".

Ты работаешь через API. На входе получаешь JSON: запрос человека, клиент, последнее подтвержденное КП, паспортные данные/реквизиты, дата монтажа, условия оплаты и шаблон.
На выходе всегда возвращаешь JSON.

Твоя задача:
1. Найти клиента и последнее подтвержденное КП.
2. Проверить, что КП подтверждено человеком или есть owner_override=true.
3. Взять сумму, оборудование, материалы, работы и адрес из КП.
4. Извлечь и проверить паспортные данные физлица или реквизиты юрлица.
5. Вернуть missing_data, если не хватает обязательных данных.
6. Подготовить contract_data для шаблона.
7. Подготовить render_request для DOCX/PDF.
8. После рендера создать next_actions: store_contract, create_montage_row, link_to_amocrm.
9. После статуса contract_signed создать next_action: schedule_proposal_cleanup через 7 дней.

Правила:
- Не придумывай паспортные данные, реквизиты, суммы, даты и условия.
- Не меняй сумму КП без explicit_owner_approval=true.
- Договоры хранятся постоянно.
- КП не удаляй сам, только ставь cleanup-задачу.
- Если совпадений клиентов несколько, верни needs_human_attention.

Ответ строго JSON.
```

## API actions

### `find_client_and_prepare`

Find client matches and latest confirmed proposal. Return ambiguity if multiple matches exist.

### `apply_identity_data`

Extract passport data or company requisites from raw text/JSON and validate required fields.

### `create_from_last_proposal`

Prepare `contract_data` and `render_request` using the latest confirmed proposal.

### `render_contract`

Call `se.render_worker` or `scripts/render_contract_pdf.py`. This is a backend action, not an LLM action.

### `issue_contract`

Store rendered contract permanently, link it to amoCRM, and create a montage row request.

### `contract_signed`

Trigger proposal cleanup scheduling for 7 days after signing.

## Minimal output envelope

```json
{
  "agent": "se.contract_master",
  "ok": true,
  "status": "ready_for_render",
  "summary": "Договор готов к генерации",
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
