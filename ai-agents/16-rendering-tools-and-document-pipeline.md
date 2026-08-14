# Инструменты генерации PNG, DOCX и PDF

Этот файл фиксирует, какими инструментами агенты создают КП-картинки и договоры. Логика должна быть такой же, как уже делались КП в этом проекте: структурированные данные -> скрипт генерации -> готовый файл.

## Технический агент

Боевой ID: `se.render_worker`.

`se.render_worker` не продает, не считает цены и не принимает бизнес-решения. Он получает JSON payload от `se.proposal_master` или `se.contract_master`, вызывает нужный генератор и возвращает файл.

## PNG коммерческого предложения

### Инструмент MVP

```text
Python + Pillow
```

Почему именно так:

- в проекте уже есть рабочие скрипты КП через `PIL.Image`, `ImageDraw`, `ImageFont`;
- есть фирменный PNG-шаблон КП;
- результат сразу подходит для отправки в Telegram как фото;
- легко контролировать таблицы, суммы, координаты и внешний вид.

### API-схема

```text
POST /api/render/proposal-png
```

Вход:

```json
{
  "proposal_id": "uuid",
  "template": "septik_expert_kp_v1",
  "client": {
    "name": "Иван",
    "address": "Нагаево",
    "phone": "+79990000000",
    "date": "2026-08-13"
  },
  "materials": [],
  "works": [],
  "totals": {
    "materials": 0,
    "works": 0,
    "grand_total": 0
  }
}
```

Выход:

```json
{
  "ok": true,
  "file_type": "proposal_png",
  "local_path": "/app/storage/rendered/proposals/...",
  "width": 1080,
  "height": 1527,
  "sha256": "...",
  "warnings": []
}
```

Правила:

- рендерить только после статуса `approved_for_render`;
- renderer не пересчитывает цену, только проверяет арифметику и предупреждает;
- если строки не помещаются в шаблон, вернуть `needs_layout_review`;
- после рендера файл передается `se.document_keeper`;
- в Telegram отправлять как фото.

## DOCX/PDF договора

### Основной инструмент

```text
Python + python-docx -> DOCX
LibreOffice headless -> PDF
```

Почему:

- договор должен сохраняться редактируемым DOCX и финальным PDF;
- можно использовать существующий юридический шаблон;
- на VPS LibreOffice конвертирует DOCX в PDF автоматически.

### Резервный инструмент

```text
Python + ReportLab -> PDF
```

Использовать для типовых PDF, актов и случаев, когда DOCX-шаблон не нужен.

### API-схема

```text
POST /api/render/contract
```

Вход:

```json
{
  "contract_id": "uuid",
  "template": "supply_with_installation_v1",
  "output_formats": ["docx", "pdf"],
  "contract_data": {
    "contract_number": "82",
    "contract_date": "2026-08-13",
    "seller": {},
    "buyer": {},
    "object_address": "Нагаево",
    "materials": [],
    "works": [],
    "totals": {
      "materials": 0,
      "works": 0,
      "grand_total": 0,
      "grand_total_words": ""
    },
    "payment_terms": {},
    "montage_terms": {}
  }
}
```

Выход:

```json
{
  "ok": true,
  "docx_path": "/app/storage/rendered/contracts/...",
  "pdf_path": "/app/storage/rendered/contracts/...",
  "sha256_docx": "...",
  "sha256_pdf": "...",
  "warnings": []
}
```

## Что поставить на VPS

```text
python3
python3-venv
Pillow
python-docx
reportlab
LibreOffice headless
poppler-utils
Times-compatible fonts
```

## Контроль качества

### PNG КП

- файл создан;
- размер не 0;
- открывается через Pillow;
- суммы в payload совпадают с суммами в metadata;
- нет `needs_layout_review`;
- файл загружен в Google Drive;
- ссылка записана в `_client-index.json` и/или Google Таблицу "Реестр документов";
- Telegram получил фото.

### DOCX/PDF договор

- DOCX создан;
- PDF создан;
- PDF открывается;
- текст PDF содержит номер договора, клиента, сумму и адрес;
- страницы не пустые;
- файл загружен в Google Drive;
- ссылка записана в `_client-index.json` и/или Google Таблицу "Реестр документов";
- строка монтажа создана или обновлена.

## Итоговый системный промт `se.render_worker`

```text
Ты se.render_worker - технический воркер генерации файлов ООО "Септик Эксперт".

Ты не считаешь цену, не продаешь, не меняешь CRM и не принимаешь бизнес-решения.
Ты получаешь структурированный render_request и создаешь файл указанным инструментом.

Для КП:
- используй Python + Pillow;
- рендерь PNG по фирменному шаблону;
- не меняй утвержденные данные;
- проверь, помещаются ли строки в шаблон;
- верни предупреждение, если нужен ручной контроль макета.

Для договора:
- основной путь: python-docx заполняет DOCX-шаблон, LibreOffice headless конвертирует DOCX в PDF;
- резервный путь: ReportLab генерирует PDF по программному шаблону;
- не придумывай недостающие данные;
- проверь, что номер договора, клиент, сумма и адрес попали в PDF.

Ответ строго JSON с путями файлов, checksum и предупреждениями.
```
