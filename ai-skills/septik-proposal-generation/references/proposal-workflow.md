# Proposal workflow

## Purpose

Create a reliable КП flow for Septik Expert:

```text
Telegram/web/amoCRM data -> AI text calculation -> human corrections -> "Ок" -> PNG render -> Telegram photo -> storage -> CRM link
```

## Roles

- `se.measurement_engineer`: extracts object data from voice/text/photos.
- `se.proposal_master`: builds and updates the proposal calculation.
- `se.render_worker`: renders PNG with Python + Pillow.
- `se.document_keeper`: stores final PNG and metadata.
- `se.amocrm_operator`: writes links/notes/tasks to amoCRM.

## Flow

1. Receive source data:
   - client name;
   - phone;
   - address;
   - measurement report;
   - desired equipment;
   - materials/works;
   - price rules;
   - photos if available.

2. Normalize:
   - map phone to normalized format;
   - map client to internal `client_id`;
   - map amoCRM lead/contact if known;
   - attach measurement/task ID.

3. Create draft:
   - return text calculation;
   - include `missing_data`;
   - include structured `proposal_payload`.

4. Human review:
   - Telegram shows text calculation and buttons: `Ок`, `Внести правки`, `Отмена`;
   - corrections create a new version;
   - only `Ок` sets `approved_by_human=true`.

5. Render:
   - create `render_request`;
   - enqueue `proposal.render_png`;
   - render with Pillow template.

6. Deliver and store:
   - send PNG to Telegram requester;
  - store through Google Drive;
  - update `_client-index.json` and Google Таблицу "Реестр документов";
  - add note/link in amoCRM.

## Statuses

- `draft_text`: text calculation exists.
- `needs_human_correction`: human requested edits.
- `approved_for_render`: human pressed `Ок`.
- `rendering`: PNG job is running.
- `rendered`: local PNG created.
- `sent_to_telegram`: Telegram received the photo.
- `stored`: PNG is stored and indexed.
- `scheduled_for_deletion`: contract signed, cleanup date set.
- `deleted_after_contract`: removed/archived by cleanup rule.
- `error`: failed step.

## Human permissions

- Measurer/manager can create draft and request render after review if role policy allows.
- Owner can override, approve, rerender, keep forever, and force archive.
- Client delivery requires explicit command, not automatic render.
