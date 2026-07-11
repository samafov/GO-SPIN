"""
Слой работы с базой данных (SQLite).
Хранит: пользователей, каталог товаров, инвентарь (полученные предметы),
историю бесплатных спинов колеса.
"""
import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "bulkster.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    emoji TEXT NOT NULL,
    price_stars INTEGER NOT NULL,   -- фиксированная цена, 0 = недоступно для покупки (только с колеса)
    category TEXT NOT NULL          -- 'shop' или 'wheel_only'
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    source TEXT NOT NULL,           -- 'purchase' или 'wheel'
    obtained_at INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    price_stars INTEGER NOT NULL,
    telegram_payment_charge_id TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS wheel_spins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    spun_at INTEGER NOT NULL
);
"""

# Стартовый каталог. price_stars > 0 -> можно купить напрямую в магазине.
# category = wheel_only -> предмет выпадает ТОЛЬКО с бесплатного колеса, купить нельзя.
DEFAULT_ITEMS = [
    ("christmas_tree", "Christmas Tree", "🎄", 35, "shop"),
    ("christmas_bear", "Christmas Bear", "🧸", 35, "shop"),
    ("valentine_heart", "Valentine Heart", "💝", 35, "shop"),
    ("valentine_bear", "Valentine Bear", "🐻", 35, "shop"),
    ("march_bear", "March Bear", "🌸", 35, "shop"),
    ("patrick_bear", "Patrick Bear", "🍀", 35, "shop"),
    ("golden_star", "Golden Star", "⭐", 0, "wheel_only"),
    ("lucky_clover", "Lucky Clover", "🍀", 0, "wheel_only"),
    ("mystery_box", "Mystery Box", "🎁", 0, "wheel_only"),
]

WHEEL_SPIN_COOLDOWN_SECONDS = 24 * 60 * 60  # 24 часа, как в референсе


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        for item_id, title, emoji, price, category in DEFAULT_ITEMS:
            conn.execute(
                """INSERT INTO items (item_id, title, emoji, price_stars, category)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(item_id) DO NOTHING""",
                (item_id, title, emoji, price, category),
            )


def ensure_user(user_id: int, username: str | None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username, created_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username = excluded.username""",
            (user_id, username, int(time.time())),
        )


def get_shop_items():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM items WHERE category = 'shop' ORDER BY title"
        ).fetchall()
        return [dict(r) for r in rows]


def get_wheel_items():
    """Всё, что может выпасть с колеса: и shop-предметы, и wheel_only."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM items ORDER BY title").fetchall()
        return [dict(r) for r in rows]


def get_item(item_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        return dict(row) if row else None


def record_purchase(user_id: int, item_id: str, price_stars: int, charge_id: str):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO purchases (user_id, item_id, price_stars, telegram_payment_charge_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, item_id, price_stars, charge_id, int(time.time())),
        )
        conn.execute(
            """INSERT INTO inventory (user_id, item_id, source, obtained_at)
               VALUES (?, ?, 'purchase', ?)""",
            (user_id, item_id, int(time.time())),
        )


def get_last_spin_time(user_id: int) -> int | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT spun_at FROM wheel_spins WHERE user_id = ? ORDER BY spun_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return row["spun_at"] if row else None


def record_spin(user_id: int, item_id: str):
    with get_db() as conn:
        now = int(time.time())
        conn.execute(
            "INSERT INTO wheel_spins (user_id, item_id, spun_at) VALUES (?, ?, ?)",
            (user_id, item_id, now),
        )
        conn.execute(
            """INSERT INTO inventory (user_id, item_id, source, obtained_at)
               VALUES (?, ?, 'wheel', ?)""",
            (user_id, item_id, now),
        )


def get_inventory(user_id: int):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT inv.id, inv.source, inv.obtained_at, it.item_id, it.title, it.emoji
               FROM inventory inv JOIN items it ON it.item_id = inv.item_id
               WHERE inv.user_id = ? ORDER BY inv.obtained_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
