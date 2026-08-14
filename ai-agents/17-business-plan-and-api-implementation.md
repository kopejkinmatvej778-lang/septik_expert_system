# Бизнес-план и API-first реализация

## Цель

Построить единую систему управления продажами и монтажами ООО "Септик Эксперт": amoCRM, телефония, Telegram, КП, договоры, Google Drive, Google Таблицы и кабинет руководителя.

## Принцип реализации

Не используем n8n. Все делается кодом:

```text
VPS + GitHub + backend API + queue + workers + Telegram Bot API + amoCRM API + Google Drive/Sheets API + telephony API + AI API
```

## Бизнес-модель процесса

1. Заявка попадает в amoCRM.
2. Менеджер звонит клиенту.
3. Телефония отдает запись звонка.
4. AI расшифровывает и анализирует звонок.
5. amoCRM получает заметку, задачу и безопасные поля.
6. Клиент закрывается на замер или удаленный расчет по фото.
7. Замерщик отправляет голос/фото/текст через Telegram.
8. AI собирает текстовый расчет КП.
9. Человек правит и нажимает `Ок`.
10. Renderer создает PNG КП.
11. PNG уходит в Telegram и сохраняется в папку клиента.
12. По последнему КП создается договор DOCX/PDF.
13. Договор сохраняется постоянно.
14. Монтаж добавляется в Google Таблицу.
15. Через 7 дней после заключения договора КП удаляется/архивируется по правилу.
16. Руководитель видит все в кабинете.

## Базовые API endpoint

### Webhooks

```text
POST /api/webhooks/amocrm
POST /api/webhooks/telephony
POST /api/webhooks/telegram
POST /api/webhooks/google-sheets
```

### AI и агенты

```text
POST /api/agents/dispatch
POST /api/agents/transcribe
POST /api/agents/analyze-call
POST /api/agents/check-script
POST /api/agents/prepare-proposal
POST /api/agents/prepare-contract
```

### Рендер

```text
POST /api/render/proposal-png
POST /api/render/contract
```

### Документы

```text
POST /api/documents/client-folder
POST /api/documents/store
POST /api/documents/schedule-cleanup
GET /api/documents/search
```

### Монтажи

```text
POST /api/montages/from-contract
PATCH /api/montages/{id}
GET /api/montages
POST /api/google-sheets/sync-montages
```

### Руководитель

```text
GET /api/dashboard/today
GET /api/dashboard/calls
GET /api/dashboard/montages
GET /api/dashboard/money
GET /api/dashboard/people
```

## Очереди задач

Минимальные очереди:

- `calls.transcribe`
- `calls.analyze`
- `crm.update`
- `proposal.prepare`
- `proposal.render_png`
- `contract.prepare`
- `contract.render`
- `documents.store`
- `montage.sync_sheet`
- `cleanup.proposals`
- `owner.digest`

## Модель данных без Postgres

Google Drive и Google Sheets являются источником данных. Backend на VPS не хранит отдельную SQL-базу, а читает/пишет через Google API.

### Google Drive

- `Клиенты/` - корневая папка всех клиентов.
- `Клиенты/{client-folder}/_client-index.json` - карточка клиента, связи, список документов, статусы, cleanup-даты.
- `Клиенты/{client-folder}/КП/` - КП PNG и исходные render payload.
- `Клиенты/{client-folder}/Договоры/` - DOCX/PDF договоров, хранить постоянно.
- `Клиенты/{client-folder}/Фото замера/` - фото и отчеты замерщика.
- `Клиенты/{client-folder}/Звонки/` - записи звонков, транскрипты и анализ.

### Google Sheets

- `Монтажи` - источник монтажей для команды и кабинета.
- `Реестр документов` - быстрый поиск по КП, договорам, актам, фото, звонкам и ссылкам на папки.
- `Табель/Выплаты` - рабочий источник занятости, смен, начислений и расчетов.
- `Agent events` - служебный журнал idempotency, webhook-событий, ошибок и cleanup-задач.

### Backend cache

Допустим только технический краткоживущий cache на VPS: Redis/файловый cache для очередей, idempotency locks и ускорения интерфейса. Он не является источником истины.

## Минимальный MVP

1. GitHub repo + VPS + Docker Compose.
2. Backend API без SQL-базы: Google Drive/Sheets как source of truth.
3. Telegram bot для КП.
4. PNG КП через Python + Pillow.
5. DOCX/PDF договор через python-docx + LibreOffice.
6. Google Drive папки клиентов + `_client-index.json`.
7. Google Sheets монтажи + реестр документов.
8. amoCRM webhook и обновление задач/заметок.
9. Телефония webhook + транскрипция.
10. Кабинет руководителя: сегодня, звонки, КП, договоры, монтажи.

## Definition of Done

Система считается рабочей, если можно пройти цепочку:

```text
заявка/клиент
-> голос/текст для КП
-> текстовый расчет
-> правка
-> кнопка "Ок"
-> PNG КП в Telegram
-> файл в папке клиента
-> договор DOCX/PDF
-> договор в папке клиента
-> монтаж в Google Таблице
-> карточка/ссылки в кабинете
```
