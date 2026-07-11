"""
Оплата товаров через Telegram Stars (валюта XTR).
Поток:
1. Mini App вызывает Telegram.WebApp.sendData({"action": "buy", "item_id": ...})
2. Бот получает это как message.web_app_data, достаёт товар и шлёт invoice
3. Telegram присылает pre_checkout_query -> отвечаем ok=True (или отказ, если товара нет)
4. После оплаты приходит successful_payment -> подтверждаем покупку в backend
   и выдаём предмет пользователю.

Никакого элемента случайности здесь нет: цена и товар фиксированы заранее.
"""
import json

import httpx
from aiogram import Router, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery

from config import BACKEND_URL, INTERNAL_API_KEY

router = Router()

# В реальном проекте лучше запрашивать актуальный каталог у backend,
# здесь для простоты MVP держим короткий кэш в памяти процесса бота.
_items_cache: dict[str, dict] = {}


async def _fetch_shop_items() -> dict[str, dict]:
    global _items_cache
    if _items_cache:
        return _items_cache
    async with httpx.AsyncClient() as client:
        # /api/shop требует initData для авторизации пользователя, но каталог
        # можно вынести и в отдельный публичный эндпоинт — упрощаем для MVP.
        resp = await client.get(f"{BACKEND_URL}/api/shop")
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            _items_cache = {i["item_id"]: i for i in items}
    return _items_cache


@router.message(F.web_app_data)
async def handle_webapp_buy(message: Message):
    try:
        payload = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, AttributeError):
        await message.answer("Некорректные данные от Mini App.")
        return

    if payload.get("action") != "buy":
        return

    item_id = payload.get("item_id")
    items = await _fetch_shop_items()
    item = items.get(item_id)
    if not item:
        await message.answer("Такого товара нет в магазине.")
        return

    price = item["price_stars"]
    await message.answer_invoice(
        title=item["title"],
        description=f"{item['emoji']} {item['title']} — коллекционный предмет",
        payload=json.dumps({"item_id": item_id}),
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=item["title"], amount=price)],
        provider_token="",  # для Stars всегда пустая строка
    )


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно перепроверить наличие товара; для MVP всегда подтверждаем.
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payment = message.successful_payment
    payload = json.loads(payment.invoice_payload)
    item_id = payload["item_id"]

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BACKEND_URL}/api/internal/confirm-purchase",
            headers={"X-Internal-Key": INTERNAL_API_KEY},
            json={
                "user_id": message.from_user.id,
                "item_id": item_id,
                "price_stars": payment.total_amount,
                "telegram_payment_charge_id": payment.telegram_payment_charge_id,
            },
        )

    await message.answer("✅ Покупка подтверждена! Предмет добавлен в твою коллекцию.")
