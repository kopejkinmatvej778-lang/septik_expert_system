# Identity and requisites

## Rule

Never invent identity data.

If a required field is missing, return `missing_data`.

## Individual buyer fields

Required by default:

- `full_name`
- `passport_series`
- `passport_number`
- `issued_by`
- `issued_at`

Recommended/conditional:

- `department_code`
- `birth_date`
- `birth_place`
- `registration_address`
- `phone`

## Company buyer fields

Required by default:

- `full_name`
- `short_name`
- `inn`
- `kpp` if applicable;
- `ogrn`
- `legal_address`
- `signer_full_name`
- `signer_short_name`
- `signer_position`
- `signer_basis`

Recommended:

- `bank_name`
- `bik`
- `settlement_account`
- `correspondent_account`
- `contact_name`
- `contact_phone`

## Extraction prompt

```text
Извлеки данные покупателя для договора ООО "Септик Эксперт".

Вход:
{{identity_data_raw}}

Верни JSON:
{
  "buyer_type": "individual|company|unknown",
  "individual": {
    "full_name": "",
    "short_name": "",
    "passport_series": "",
    "passport_number": "",
    "issued_by": "",
    "issued_at": "",
    "department_code": "",
    "birth_date": "",
    "birth_place": "",
    "registration_address": "",
    "phone": ""
  },
  "company": {
    "full_name": "",
    "short_name": "",
    "inn": "",
    "kpp": "",
    "ogrn": "",
    "legal_address": "",
    "signer_full_name": "",
    "signer_short_name": "",
    "signer_position": "",
    "signer_basis": "",
    "bank_name": "",
    "bik": "",
    "settlement_account": "",
    "correspondent_account": "",
    "contact_name": "",
    "contact_phone": ""
  },
  "missing_data": []
}

Не придумывай отсутствующие поля.
```

## Validation

For individual:

```text
missing if full_name, passport_series, passport_number, issued_by, issued_at are empty
```

For company:

```text
missing if full_name, short_name, inn, ogrn, legal_address, signer_full_name, signer_position, signer_basis are empty
```

If passport data is visible only to owner/manager, mask it in logs and dashboard:

```text
92 17 123456 -> 92 ** ***456
```
