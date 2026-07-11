import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# URL, где захостен webapp/index.html (обязательно HTTPS — Telegram требует)
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com/webapp/")

# URL backend API (тот же, что слушает backend/app.py)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Должен совпадать с INTERNAL_API_KEY в backend/app.py
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "change-me")
