import os
import io
import time
import sqlite3
import logging
import urllib.parse
import telebot
import qrcode

from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==========================================
# CONFIG — Railway Variables
# ==========================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_RAW = os.getenv("ADMIN_ID", "").strip()
UPI_ID = os.getenv("UPI_ID", "").strip()
PAYEE_NAME = os.getenv("PAYEE_NAME", "Course Store").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip()
DB_PATH = os.getenv("DB_PATH", "orders.db")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

if not ADMIN_RAW.isdigit():
    raise RuntimeError("ADMIN_ID must be numeric")

if not UPI_ID:
    raise RuntimeError("UPI_ID missing")

ADMIN_ID = int(ADMIN_RAW)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram_store")

bot = telebot.TeleBot(TOKEN)

# ==========================================
# PLANS — apni details yahan edit karna
# Media file IDs Telegram se milte hain.
# ==========================================

PLANS = [
    {
        "id": 1,
        "name": "PLAN 1",
        "price": 90,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 1 ki details yahan likho.",
        "image": "",
        "demos": [
            {"type": "video", "id": ""},
            {"type": "video", "id": ""},
            {"type": "video", "id": ""},
            {"type": "video", "id": ""},
            {"type": "video", "id": ""}
        ],
        "active": True
    },
    {
        "id": 2,
        "name": "PLAN 2",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 2 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 3,
        "name": "PLAN 3",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 3 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 4,
        "name": "PLAN 4",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 4 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 5,
        "name": "PLAN 5",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 5 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 6,
        "name": "PLAN 6",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 6 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 7,
        "name": "PLAN 7",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 7 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 8,
        "name": "youtube viral shorts 🔥",
        "price": 58,
        "validity": "180 days",
        "videos": "30000+",
        "description": (
            "1. Gallery mein save kar sakte ho ✅\n"
            "2. No ads ❌\n"
            "3. High quality videos 😍\n"
            "4. New videos every Friday ✅"
        ),
        "image": "",
        "demos": [
            {
                "type": "video",
                "id": "BAACAgUAAxkBAAI06GrHM2QUeiT0Q6J5yEopeA96Aim1AAJKIwACv685VjMk0xUgmBWJPQQ"
            }
        ],
        "active": True
    },
    {
        "id": 9,
        "name": "PLAN 9",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 9 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    },
    {
        "id": 10,
        "name": "PLAN 10",
        "price": 99,
        "validity": "180 days",
        "videos": "30000+",
        "description": "Plan 10 ki details yahan likho.",
        "image": "",
        "demos": [],
        "active": True
    }
]

# ==========================================
# DATABASE
# ==========================================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_screenshot',
                created_at REAL NOT NULL
            )
        """)
        conn.commit()


def create_order(user_id, plan):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO orders
            (user_id, plan_id, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                plan["id"],
                plan["price"],
                "awaiting_screenshot",
                time.time()
            )
        )
        conn.commit()
        return cur.lastrowid


def get_order(order_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()
        return dict(row) if row else None


def set_order_status(order_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        conn.commit()


def get_plan(plan_id):
    return next(
        (
            p for p in PLANS
            if p["id"] == plan_id and p.get("active")
        ),
        None
    )


# ==========================================
# BUTTON HELPERS
# ==========================================

def btn(text, callback=None, url=None):
    args = {"text": text}

    if callback is not None:
        args["callback_data"] = callback

    if url is not None:
        args["url"] = url

    return InlineKeyboardButton(**args)


def add_support_button(kb):
    if SUPPORT_USERNAME:
        username = SUPPORT_USERNAME.lstrip("@")
        kb.add(
            btn("🆘 Support", url=f"https://t.me/{username}")
        )


# ==========================================
# UPI QR GENERATOR
# ==========================================

def make_upi_qr(plan, order_id):
    params = {
        "pa": UPI_ID,
        "pn": PAYEE_NAME,
        "am": f"{plan['price']:.2f}",
        "cu": "INR",
        "tn": f"Order {order_id} Plan {plan['id']}"
    }

    upi_link = "upi://pay?" + urllib.parse.urlencode(params)

    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=3
    )
    qr.add_data(upi_link)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    output = io.BytesIO()
    output.name = "payment_qr.png"
    image.save(output, format="PNG")
    output.seek(0)

    return output
