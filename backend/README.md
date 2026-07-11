# Коллекция подарков — Telegram Mini App (MVP)

Бот + магазин (фиксированные цены за Telegram Stars) + бесплатное колесо
раз в 24 часа. **Без денежных ставок и без вывода/перепродажи призов** —
это осознанное ограничение, не баг.

## Структура

```
bot/        — Telegram-бот (aiogram 3), команда /start и приём платежей
backend/    — Flask API для Mini App (каталог, колесо, инвентарь)
webapp/     — сам Mini App (HTML/CSS/JS), открывается кнопкой в боте
```

## 1. Создай бота

1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot`, получи токен.
2. `/mybots` → твой бот → **Bot Settings → Configure Mini App / Menu Button**,
   чтобы позже привязать URL из шага 3.
3. Убедись, что у бота включены платежи Stars (по умолчанию доступны всем ботам,
   отдельный provider_token не нужен — для валюты `XTR` он всегда пустая строка).

## 2. Разверни backend

```bash
cd backend
pip install -r requirements.txt
export INTERNAL_API_KEY="сгенерируй-длинную-случайную-строку"
python app.py
```

По умолчанию слушает `0.0.0.0:8000`. Для продакшена — задеплой на любой
хостинг с HTTPS (Render, Railway, VPS + nginx + certbot и т.д.), Telegram
требует HTTPS для Mini App и для webhook.

База — SQLite (`bulkster.db`), создаётся автоматически при первом запуске.
Каталог товаров редактируется в `backend/database.py` (`DEFAULT_ITEMS`).

## 3. Задеплой webapp

Открой `webapp/app.js` и замени:
```js
const API_BASE = "https://YOUR-BACKEND-DOMAIN.example.com";
```
на реальный адрес backend из шага 2.

Залей папку `webapp/` на любой статический хостинг с HTTPS
(GitHub Pages, Vercel, Netlify, Cloudflare Pages — подойдёт любой).
Запомни итоговый URL, например `https://username.github.io/webapp/`.

## 4. Настрой и запусти бота

```bash
cd bot
pip install -r requirements.txt
export BOT_TOKEN="токен-от-BotFather"
export WEBAPP_URL="https://username.github.io/webapp/"   # из шага 3
export BACKEND_URL="https://YOUR-BACKEND-DOMAIN.example.com"  # из шага 2
export INTERNAL_API_KEY="та-же-строка-что-в-backend"
python main.py
```

Напиши боту `/start` — появится кнопка «Открыть магазин».

## Как это работает

- **Покупка**: Mini App просит бота выставить счёт (`sendData` → бот вызывает
  `answer_invoice` с фиксированной ценой и currency `XTR`). Никакого рандома —
  что выбрал, то и получил, сразу за фиксированные Stars.
- **Бесплатный тираж**: раз в 24 часа (проверяется на backend, не обойти через
  клиент) можно бесплатно "крутить" и получить случайный предмет из общего
  списка. Деньги нигде не участвуют — ни на входе, ни на выходе. Выигранные
  предметы нельзя продать или вывести, это просто пункт в коллекции аккаунта.
- **Коллекция**: и купленные, и выигранные предметы отображаются вместе —
  UI показывает источник каждого («Куплено» / «Выиграно в тираже»).

## Что стоит добавить перед реальным запуском

- Возврат/отмену покупки (`refundStarPayment` в Bot API).
- Rate-limiting на `/api/wheel/spin`, чтобы не долбили эндпоинт мимо кулдауна
  (сейчас кулдаун серверный и это уже защищает от накрутки, но лишним не будет).
- Логирование и алерты на backend.
- Тесты на `telegram_auth.py` — это единственное, что защищает API от подделки
  чужого user_id, ошибка здесь критична.
- Продовый WSGI-сервер вместо `flask run` (gunicorn/uvicorn + nginx).
