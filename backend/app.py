"""
API для Mini App. Отдаёт каталог, обрабатывает бесплатный спин колеса,
принимает подтверждение оплаты (вызывается ботом после успешного платежа
через Telegram Stars — см. bot/handlers/payments.py).
"""
import os
import random
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

import database as db
from telegram_auth import validate_init_data, InvalidInitData

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "change-me")


def get_authenticated_user():
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        return None, ("Нет initData", 401)
    try:
        user = validate_init_data(init_data, BOT_TOKEN)
    except InvalidInitData as e:
        return None, (str(e), 401)
    db.ensure_user(user["id"], user.get("username"))
    return user["id"], None


@app.route("/api/shop", methods=["GET"])
def shop():
    user_id, err = get_authenticated_user()
    if err:
        return jsonify({"error": err[0]}), err[1]
    return jsonify({"items": db.get_shop_items()})


@app.route("/api/wheel/status", methods=["GET"])
def wheel_status():
    user_id, err = get_authenticated_user()
    if err:
        return jsonify({"error": err[0]}), err[1]

    last_spin = db.get_last_spin_time(user_id)
    now = int(time.time())
    if last_spin is None:
        seconds_left = 0
    else:
        elapsed = now - last_spin
        seconds_left = max(0, db.WHEEL_SPIN_COOLDOWN_SECONDS - elapsed)

    return jsonify({
        "can_spin": seconds_left == 0,
        "seconds_left": seconds_left,
        "possible_items": db.get_wheel_items(),
    })


@app.route("/api/wheel/spin", methods=["POST"])
def wheel_spin():
    user_id, err = get_authenticated_user()
    if err:
        return jsonify({"error": err[0]}), err[1]

    last_spin = db.get_last_spin_time(user_id)
    now = int(time.time())
    if last_spin is not None and now - last_spin < db.WHEEL_SPIN_COOLDOWN_SECONDS:
        seconds_left = db.WHEEL_SPIN_COOLDOWN_SECONDS - (now - last_spin)
        return jsonify({"error": "Спин ещё недоступен", "seconds_left": seconds_left}), 429

    items = db.get_wheel_items()
    won_item = random.choice(items)
    db.record_spin(user_id, won_item["item_id"])

    return jsonify({"won_item": won_item})


@app.route("/api/inventory", methods=["GET"])
def inventory():
    user_id, err = get_authenticated_user()
    if err:
        return jsonify({"error": err[0]}), err[1]
    return jsonify({"inventory": db.get_inventory(user_id)})


@app.route("/api/internal/confirm-purchase", methods=["POST"])
def confirm_purchase():
    if request.headers.get("X-Internal-Key") != INTERNAL_API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True)
    user_id = data["user_id"]
    item_id = data["item_id"]
    price_stars = data["price_stars"]
    charge_id = data["telegram_payment_charge_id"]

    item = db.get_item(item_id)
    if not item:
        return jsonify({"error": "item not found"}), 404

    db.record_purchase(user_id, item_id, price_stars, charge_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=8000, debug=True)
