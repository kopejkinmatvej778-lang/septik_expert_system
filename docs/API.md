# Septik Expert static panel API

Статическая панель из `docs/index.html` работает без сборки. Живые данные подключаются через VPS API.

## Настройка фронта

В панели нажать `API` и указать адрес backend:

```text
https://example.ru/septik-api
```

Фронт будет обращаться к:

```text
GET  /dashboard
POST /measurements
```

Секреты amoCRM, Google Sheets, Telegram и OpenAI нельзя класть в HTML/JS. Они должны храниться только на VPS.

## GET /dashboard

Ответ:

```json
{
  "ok": true,
  "data": {
    "measurements": [],
    "montages": [],
    "clients": [],
    "sales": [],
    "tasks": [],
    "agentEvents": []
  }
}
```

## POST /measurements

Запрос:

```json
{
  "client": "Айрат",
  "phone": "+7 917 000-21-44",
  "address": "Нагаево, ул. Сосновая, 18",
  "measurer": "Виталий",
  "dueAt": "2026-08-16T15:00:00.000Z",
  "note": "Проверить подъезд техники"
}
```

Ответ:

```json
{
  "ok": true
}
```

## CORS для GitHub Pages

Backend должен разрешить:

```http
Access-Control-Allow-Origin: https://kopejkinmatvej778-lang.github.io
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: GET, POST, OPTIONS
```
