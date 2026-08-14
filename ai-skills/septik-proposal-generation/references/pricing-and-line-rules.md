# Pricing and line rules

## General rules

- Never invent prices.
- Use `references/price-catalog.json` as the first price source.
- Use `standard_price` by default.
- Do not apply discounts, gifts, old КП prices, or manual reductions unless the current request explicitly includes `discount`, `gift`, `custom_price`, or `owner_override`.
- If a requested item is absent from the catalog, return `missing_price_request` and stop calculation for that line.
- Use approved price rules, explicit human input, or previous confirmed proposal data only when they are represented in the catalog or sent in the current request.
- If a value is not money, use `price_kind` and display fields.
- Always separate materials and works.
- Always compute totals from money rows only.

## Price catalog

Main file:

```text
references/price-catalog.json
```

Resolution order:

1. Match exact `item_id` if supplied.
2. Match item name by `aliases`.
3. Use `standard_price`.
4. If only `standard_price_from` exists, display `от ...` and add warning unless the human supplied exact price.
5. If the item has `warning`, include it in `warnings`.
6. If the item is not found, return `missing_price_request`.

When the human gives a missing price, return a catalog update request:

```json
{
  "type": "price_catalog_update_request",
  "item_name": "Новая позиция",
  "category": "materials",
  "unit": "шт",
  "standard_price": 10000,
  "source": "human_input",
  "approved_by": "owner|manager"
}
```

## Supported price kinds

- `money`: numeric `unit_price` and `total`.
- `gift`: display total is `В подарок`; total contribution is 0.
- `customer`: display total is `от заказчика`; total contribution is 0.
- `fact`: display total is `По факту`; total contribution is 0 unless a separate confirmed amount exists.
- `dash`: display as `—`; total contribution is 0.

## Common lines from existing КП

Materials:

- Станция «АЭРОЛОС БИО 4»
- Станция «АЭРОЛОС ПРО 4»
- Станция «АЭРОЛОС БИО 6»
- Насос дренажный Акварио
- Насос DAB Verty Nova 200M
- Песок с доставкой 10 т
- Гравий 3 тонны
- Геотекстиль
- Труба канализационная ПВХ D = 110 мм
- Кабель с гофротрубой
- Труба на выброс
- Греющий кабель
- Цемент
- ЖБИ кольцо D = 1,5 м
- ЖБИ крышка D = 1,5 м
- ЖБИ добор 30 см
- Люк канализационный

Works:

- Земляные работы экскаватором
- Земляные работы по монтажу станции
- Копка котлована под станцию и колодец
- Монтаж станции
- Монтаж станции в готовый котлован и пуско-наладка
- Монтаж бетонного колодца
- Монтаж ЖБ колодца
- Прокладка отводящих и подводящих труб
- Прокладка трубы на выброс
- Прокладка греющего кабеля
- Доставка станции до участка
- Доставка ЖБИ изделий
- Транспортировка песка заказчика

## Total calculation

For each row:

```text
if price_kind == money:
  row_total = numeric total
else:
  row_total = 0
```

Then:

```text
materials_total = sum(material money rows)
works_total = sum(work money rows)
grand_total = materials_total + works_total
```

If a provided total differs from calculated total, return warning:

```json
{
  "type": "total_mismatch",
  "section": "materials",
  "provided": 185900,
  "calculated": 180900
}
```

## Draft wording

Use clear language:

- "Предварительный расчет"
- "Итоговая сумма по текущим данным"
- "Требует уточнения"
- "В подарок"
- "По факту"
- "Материал от заказчика"

Do not hide uncertain items.
