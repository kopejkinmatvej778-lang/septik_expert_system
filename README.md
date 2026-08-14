# Septik Expert System

Рабочий репозиторий MVP-системы Septik Expert.

## Что где лежит

- `septik-control-panel/` — сайт-панель: клиенты, КП PNG, договоры, монтажи, продажи из amoCRM.
- `telegram-kp-bot/` — backend/Telegram-бот: генерация КП, Google Drive/Sheets, amoCRM sync, systemd-деплой.
- `ai-agents/` — инструкции AI-агентов для процессов продаж, замеров, КП, договоров и монтажа.
- `ai-skills/` — навыки генерации КП и договоров.

## Сайт-панель

Код сайта уже выгружен в `septik-control-panel/`.

```bash
cd septik-control-panel
pnpm install
pnpm run build
pnpm run dev
```

Панель не является обычным статическим HTML-сайтом для GitHub Pages: у нее есть API, база и серверная часть. Для живой ссылки нужен деплой на VPS, Cloudflare/Sites, Vercel или другой серверный хостинг.

## Backend / бот

Код backend и бота лежит в `telegram-kp-bot/`.

```bash
cd telegram-kp-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m septik_kp_bot
```

Боевые секреты не хранятся в GitHub. На сервере отдельно нужны `.env` и `secrets/google-service-account.json`.
