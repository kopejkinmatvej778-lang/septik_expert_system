# Septik Expert Control Panel

Минималистичная рабочая панель Septik Expert.

## Разделы

- Клиенты: карточка клиента, КП как PNG-фотографии, договоры отдельно как PDF.
- Договоры: реестр PDF-договоров из системы.
- Замеры: заявки и замеры из Telegram/amoCRM/таблиц.
- Монтажи: дата, состав заказа, песок, гравий, кольца, напоминание.
- Продажи: реальные сделки, воронки, статусы, каналы и задачи из amoCRM.
- Задачи: активные задачи менеджеров из amoCRM.

## Источники данных

Панель не создает демо-клиентов и не подставляет выдуманную аналитику. Данные приходят из:

- Telegram-бота через `/api/dashboard`;
- Google Drive и Google Таблиц через синхронизацию бота;
- amoCRM через API `/api/v4`.

## Environment

```bash
AMOCRM_BASE_URL=https://septikkzn.amocrm.ru
AMOCRM_ACCESS_TOKEN=
```

`AMOCRM_ACCESS_TOKEN` должен быть OAuth access token созданной интеграции. Секреты не коммитить.

## Commands

```bash
pnpm install
pnpm run build
pnpm run lint
node --test tests/rendered-html.test.mjs
```
