# Montage and storage rules

## Storage

Contracts are permanent.

Store:

- DOCX if available;
- PDF;
- source JSON/render payload;
- link to latest proposal;
- links in `_client-index.json` and Google Таблицу "Реестр документов";
- links in amoCRM.

Recommended folder:

```text
Клиенты/
  Иванов Иван +79990000000/
    2026-08-13 Договор/
```

File naming:

```text
YYYY-MM-DD__CLIENT__ADDRESS__Договор__SUM__contract-id.pdf
YYYY-MM-DD__CLIENT__ADDRESS__Договор__SUM__contract-id.docx
```

## Montage row

After contract is issued/signed, create or update a montage row.

Required columns:

- date;
- status;
- contract number;
- contract date;
- client;
- phone;
- address;
- equipment;
- contract sum;
- prepayment;
- balance;
- manager;
- measurer;
- brigade;
- comment;
- client folder link;
- contract link;
- proposal link.

If montage date is missing, return `needs_data`.

## Proposal cleanup

When contract status becomes `signed`:

```text
cleanup_at = signed_at + 7 days
```

Do:

- schedule cleanup job;
- mark proposal `scheduled_for_deletion`;
- preserve contract forever.

Do not:

- delete contracts;
- delete proposal immediately;
- delete proposal if `keep_forever=true`.
