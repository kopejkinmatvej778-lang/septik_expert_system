# Septik Expert Telegram КП Bot

Telegram-бот для MVP-цепочки КП: принимает замер, готовит черновик, рендерит PNG и при наличии сервисных доступов сохраняет результат в Google Drive / Google Sheets / панель.

## Что умеет

- принимает текстовый отчет по замеру;
- принимает голосовой отчет и расшифровывает его через OpenAI;
- собирает черновик КП;
- принимает правки человека;
- после кнопки `Ок` генерирует PNG по фирменному шаблону;
- сохраняет JSON заявки и PNG локально в `storage/proposals`;
- опционально загружает PNG в Google Drive в папку клиента;
- опционально дописывает строку в Google Таблицу `Документы`;
- опционально отправляет запись в диспетчерскую панель.

## Запуск

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python -m septik_kp_bot
```

## Команды

- `/start` - краткая инструкция.
- `/new` - начать новое КП.
- `/cancel` - отменить ввод правок.

Для работы отправьте боту текст или голос:

```text
Клиент Иван, телефон +79990000000, адрес Нагаево.
Аэролос Био 4, труба 8 м, песок 10 т, монтаж станции, доставка.
```

Бот вернет черновик и кнопки `Ок`, `Внести правки`, `Отмена`.

## Google Drive / Sheets

Чтобы включить сохранение КП в Google Drive, нужен service account JSON. Папки и таблицу нужно расшарить на email сервисного аккаунта с правами редактора.

Где взять Google API-доступ:

1. Откройте Google Cloud Console: https://console.cloud.google.com/
2. Создайте проект `Septik Expert` или выберите существующий.
3. Включите API:
   - `Google Drive API`;
   - `Google Sheets API`.
4. Откройте `IAM & Admin` -> `Service Accounts`.
5. Создайте service account, например `septik-expert-sync`.
6. Внутри service account откройте `Keys` -> `Add key` -> `Create new key` -> `JSON`.
7. Скачанный файл положите на VPS в `telegram-kp-bot/secrets/google-service-account.json`.
8. Скопируйте email service account из JSON или из Cloud Console.
9. Расшарьте на этот email с правами редактора:
   - старую таблицу `Монтажи 2026`;
   - новую таблицу-реестр;
   - папку `Клиенты`;
   - папки КП, договоров, замеров/фото.

Созданная структура:

- `Септик Эксперт CRM`
- `КП PNG`
- `Договоры PDF`
- `Замеры и фото`
- `Клиенты`
- `Реестры и таблицы`
- Google Таблица `Септик Эксперт — реестр документов и монтажей`

После добавления `GOOGLE_SERVICE_ACCOUNT_FILE`, `GOOGLE_CLIENTS_FOLDER_ID` и `GOOGLE_REGISTRY_SHEET_ID` бот начнет создавать папки клиентов, класть туда PNG-КП и писать строки в реестр.

## Импорт старой таблицы

Заполненную таблицу `Монтажи 2026` можно разложить по нормальным вкладкам реестра одной командой:

```bash
python -m septik_kp_bot.sheet_import \
  --source-sheet-id 1u86aaLma67nYqVJVx4kJB1yFNe1gDPBzlYshZaxL9Bo \
  --target-sheet-id 1IUjancmUE0pxa0CTEzg50hmFHqj2Ghh4iZs-ExgLNyM \
  --include-local-documents ../output \
  --write
```

Без `--write` команда только соберет CSV в `tmp/sheets-import/structured`, ничего не меняя в Google Таблице.

## amoCRM -> Google Sheets

Продажи, воронки и активные задачи всех менеджеров на завтра выгружаются так:

```bash
python -m septik_kp_bot.crm_sync \
  --target-sheet-id 1IUjancmUE0pxa0CTEzg50hmFHqj2Ghh4iZs-ExgLNyM \
  --write
```

Команда пишет реальные данные amoCRM во вкладки `Продажи`, `Задачи`, `Воронки`. Нужны переменные `AMOCRM_BASE_URL`, `AMOCRM_ACCESS_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_FILE`, `GOOGLE_CLIENTS_FOLDER_ID`, `GOOGLE_REGISTRY_SHEET_ID`. Токены и JSON-ключ не коммитятся.

## Общая синхронизация

Проверить, чего не хватает в доступах:

```bash
python -m septik_kp_bot.sync_all --check
```

Создать недостающие вкладки и заголовки в новой Google Таблице:

```bash
python -m septik_kp_bot.sync_all --init-tabs
```

Привести все вкладки к аккуратному виду:

```bash
python -m septik_kp_bot.sync_all --format
```

Собрать старую таблицу и amoCRM в CSV без записи в Google:

```bash
python -m septik_kp_bot.sync_all
```

Обновить новую Google Таблицу:

```bash
python -m septik_kp_bot.sync_all --write
```

На VPS можно включить регулярный запуск:

```bash
sudo cp deploy/septik-sync.service /etc/systemd/system/
sudo cp deploy/septik-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now septik-sync.timer
```
