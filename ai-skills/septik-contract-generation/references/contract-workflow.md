# Contract workflow

## Purpose

Create a reliable contract flow:

```text
latest confirmed КП -> identity/requisites -> contract_data -> DOCX/PDF -> permanent storage -> montage row -> КП cleanup
```

## Roles

- `se.contract_master`: validates contract inputs and prepares `contract_data`.
- `se.render_worker`: renders DOCX/PDF.
- `se.document_keeper`: stores final files permanently.
- `se.montage_planner`: creates/updates Google Sheets montage row.
- `se.amocrm_operator`: links contract and tasks in amoCRM.

## Flow

1. Receive request:
   - explicit client;
   - search text;
   - latest proposal;
   - identity data;
   - montage date;
   - template.

2. Find client:
   - by `client_id`;
   - by `amo_lead_id`;
   - by phone;
   - by name + address.

3. Find proposal:
   - prefer explicit `proposal_id`;
   - else latest `approved_for_render`, `rendered`, `stored`, or `used_for_contract`;
   - reject old drafts unless `owner_override=true`.

4. Validate identity:
   - individual: full name, passport series/number, issued by, issue date, optional department code, birth date, registration address if required;
   - company: legal name, short name, INN/KPP, OGRN, legal address, bank requisites, signer and authority.

5. Prepare `contract_data`:
   - seller;
   - buyer;
   - contract number/date;
   - object address;
   - materials and works from КП;
   - totals;
   - payment terms;
   - montage terms;
   - appendices.

6. Render:
   - primary: DOCX template -> PDF;
   - fallback: ReportLab PDF.

7. Store:
   - contracts are permanent;
   - save DOCX and PDF if available;
  - save links in `_client-index.json` and Google Таблицу "Реестр документов";
  - link in amoCRM.

8. Montage:
   - create Google Sheets row with date, client, address, equipment, sum, manager, measurer, links.

9. Cleanup:
   - when signed, schedule КП cleanup for `signed_at + 7 days`;
   - never delete contracts.

## Statuses

- `needs_data`
- `ready_for_review`
- `ready_for_render`
- `rendering`
- `rendered`
- `issued`
- `signed`
- `stored`
- `error`

## Human approval

Require owner/manager approval before issuing contract if:

- client match is ambiguous;
- identity data is incomplete;
- proposal is not confirmed;
- sum differs from proposal;
- montage date conflicts;
- template is uncertain.
