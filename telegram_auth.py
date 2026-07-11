"""
Проверка initData, которую Telegram Mini App присылает на бэкенд.
Это ОБЯЗАТЕЛЬНЫЙ шаг: без проверки подписи любой человек может подделать
запрос и назвать себя другим user_id. Алгоритм из официальной документации:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InvalidInitData(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    """Возвращает dict с данными пользователя, либо кидает InvalidInitData."""
    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("Отсутствует hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InvalidInitData("Подпись не совпадает")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > max_age_seconds:
        raise InvalidInitData("initData устарела")

    user_raw = parsed.get("user")
    if not user_raw:
        raise InvalidInitData("Нет данных пользователя")

    return json.loads(user_raw)
