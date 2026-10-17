
import os
import io
import time
import sqlite3
import logging
import urllib.parse

import telebot
import qrcode
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_RAW = os.getenv("ADMIN_ID", "").strip()
UPI_ID = os.getenv("UPI_ID", "").strip()
PAYEE_NAME = os.getenv("PAYEE_NAME", "Plan Store").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")
DB_PATH = os.getenv("DB_PATH", "orders.db")

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN")
if not ADMIN_RAW.isdigit():
    raise RuntimeError("Set numeric ADMIN_ID")
if not UPI_ID:
    raise RuntimeError("Set UPI_ID")

ADMIN_ID = int(ADMIN_RAW)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("plans_bot")
bot = telebot.TeleBot(TOKEN)

# ==========================================
# PLANS — edit names, prices and demo IDs
# ==========================================
PLANS = [
    {
        "id": 1,
        "name": "Plan 1",
        "price": 49,
        "validity": "30 days",
        "description": (
            "✨ Premium collection included.\n"
            "🎬 Multiple demo videos available.\n"
            "📱 Easy access on Telegram.\n"
            "🔄 New content as described.\n"
            "⚡ Simple and quick ordering.\n"
            "🆘 Contact support for assistance."
        ),
        "media": [
            {"type": "video", "id": "PLAN1_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN1_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN1_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN1_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN1_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN1_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 2,
        "name": "Plan 2",
        "price": 59,
        "validity": "30 days",
        "description": (
            "🌟 Explore the Plan 2 collection.\n"
            "🎬 Preview the available demo media.\n"
            "📦 Details are provided before purchase.\n"
            "📱 Access information is shared after approval.\n"
            "💳 Pay the amount shown at checkout.\n"
            "🆘 Support is available for order questions."
        ),
        "media": [
            {"type": "video", "id": "PLAN2_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN2_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN2_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN2_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN2_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN2_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 3,
        "name": "Plan 3",
        "price": 69,
        "validity": "30 days",
        "description": (
            "🔥 Welcome to the Plan 3 collection.\n"
            "🎥 Check the demo previews before ordering.\n"
            "📋 Review the plan details carefully.\n"
            "💰 The displayed price is the payable amount.\n"
            "✅ Payment confirmation requires admin review.\n"
            "🆘 Contact support if you need help."
        ),
        "media": [
            {"type": "video", "id": "PLAN3_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN3_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN3_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN3_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN3_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN3_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 4,
        "name": "Plan 4",
        "price": 79,
        "validity": "30 days",
        "description": (
            "💎 Discover the Plan 4 collection.\n"
            "🎬 Demo media helps you preview the plan.\n"
            "📱 Follow the instructions shown by the bot.\n"
            "🧾 Submit your payment screenshot as a photo.\n"
            "⏳ Wait while the admin reviews your payment.\n"
            "🆘 Contact support for order assistance."
        ),
        "media": [
            {"type": "video", "id": "PLAN4_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN4_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN4_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN4_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN4_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN4_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 5,
        "name": "Plan 5",
        "price": 89,
        "validity": "30 days",
        "description": (
            "🚀 Take a look at the Plan 5 collection.\n"
            "🎥 Watch the available previews first.\n"
            "📦 Check the validity and price before paying.\n"
            "💳 Use the QR generated for this plan.\n"
            "✅ Admin will review your payment submission.\n"
            "🆘 Support can help with common issues."
        ),
        "media": [
            {"type": "video", "id": "PLAN5_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN5_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN5_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN5_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN5_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN5_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 6,
        "name": "Plan 6",
        "price": 99,
        "validity": "30 days",
        "description": (
            "🎯 Welcome to the Plan 6 collection.\n"
            "🎬 Preview demo items before selecting Buy Now.\n"
            "📋 Read the plan information before checkout.\n"
            "💰 Pay only the amount shown in the QR flow.\n"
            "📸 Submit your payment screenshot for review.\n"
            "🆘 Contact support if anything goes wrong."
        ),
        "media": [
            {"type": "video", "id": "PLAN6_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN6_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN6_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN6_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN6_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN6_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 7,
        "name": "Plan 7",
        "price": 109,
        "validity": "30 days",
        "description": (
            "🌈 Explore the Plan 7 collection.\n"
            "🎥 Demo media is available for preview.\n"
            "📱 Follow the bot's checkout instructions.\n"
            "💳 Confirm the plan before making payment.\n"
            "⏳ Payment status updates after admin review.\n"
            "🆘 Contact support for any questions."
        ),
        "media": [
            {"type": "video", "id": "PLAN7_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN7_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN7_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN7_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN7_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN7_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 8,
        "name": "Plan 8",
        "price": 119,
        "validity": "30 days",
        "description": (
            "⭐ Check out the Plan 8 collection.\n"
            "🎬 View the demo previews before purchasing.\n"
            "📦 Confirm the included details and validity.\n"
            "💰 The QR uses this plan's listed amount.\n"
            "📸 Send a screenshot after completing payment.\n"
            "🆘 Reach support if you need assistance."
        ),
        "media": [
            {"type": "video", "id": "PLAN8_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN8_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN8_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN8_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN8_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN8_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 9,
        "name": "Plan 9",
        "price": 129,
        "validity": "30 days",
        "description": (
            "💫 Discover the Plan 9 collection.\n"
            "🎥 Preview available demo media first.\n"
            "📋 Read the plan description carefully.\n"
            "💳 Verify the amount before completing payment.\n"
            "✅ Your submission will be checked by admin.\n"
            "🆘 Contact support for payment-related questions."
        ),
        "media": [
            {"type": "video", "id": "PLAN9_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN9_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN9_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN9_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN9_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN9_VIDEO_6_FILE_ID"},
        ],
    },
    {
        "id": 10,
        "name": "Plan 10",
        "price": 149,
        "validity": "30 days",
        "description": (
            "🏆 Welcome to the Plan 10 collection.\n"
            "🎬 Preview the demos before making a choice.\n"
            "📦 Check the plan price and validity.\n"
            "💳 Use the generated UPI QR to pay.\n"
            "⏳ Wait for admin payment verification.\n"
            "🆘 Support is available for order questions."
        ),
        "media": [
            {"type": "video", "id": "PLAN10_VIDEO_1_FILE_ID"},
            {"type": "video", "id": "PLAN10_VIDEO_2_FILE_ID"},
            {"type": "video", "id": "PLAN10_VIDEO_3_FILE_ID"},
            {"type": "video", "id": "PLAN10_VIDEO_4_FILE_ID"},
            {"type": "photo", "id": "PLAN10_PHOTO_5_FILE_ID"},
            {"type": "video", "id": "PLAN10_VIDEO_6_FILE_ID"},
        ],
    },
]

# ==========================================
# DATABASE
# ==========================================

def db():
    return sqlite3.connect(DB_PATH, timeout=30)

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()

def create_order(user_id, plan):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO orders
            (user_id, plan_id, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, plan["id"], plan["price"],
             "awaiting_screenshot", time.time())
        )
        conn.commit()
        return cur.lastrowid

def get_order(order_id):
    with db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        ).fetchone()
        return dict(row) if row else None

def set_order_status(order_id, status):
    with db() as conn:
        conn.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (status, order_id)
        )
        conn.commit()

def get_plan(plan_id):
    return next(
        (p for p in PLANS
         if p["id"] == plan_id and p.get("active")),
        None
    )

waiting_screenshot = {}

# ==========================================
# BUTTONS
# ==========================================

def button(text, callback=None, url=None):
    args = {"text": text}
    if callback is not None:
        args["callback_data"] = callback
    if url is not None:
        args["url"] = url
    return InlineKeyboardButton(**args)

def support_button(kb):
    if SUPPORT_USERNAME:
        kb.add(button(
            "🆘 Support",
            url=f"https://t.me/{xylerigcc}"
        ))

def home_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for p in PLANS:
        if p.get("active"):
            kb.add(button(
                f" {p['name']} · ₹{p['price']}",
                f"plan:{p['id']}"
            ))
    kb.add(
        button("🎬 Demo", "demo_menu"),
        button("📖 How to use", "howto")
    )
    support_button(kb)
    return kb

def plan_keyboard(plan):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        button("🥵 Demo", f"demo:{plan['id']}"),
        button(" BUY NOW", f"buy:{plan['id']}")
    )
    kb.add(button(" Back", "home"))
    support_button(kb)
    return kb

def demo_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for p in PLANS:
        if p.get("active"):
            kb.add(button(
                f"🎬 {p['name']}", f"demo:{p['id']}"
            ))
    kb.add(button("🔙 Back", "home"))
    return kb

# ==========================================
# AUTOMATIC UPI QR
# ==========================================

def make_upi_qr(plan, order_id):
    params = {
        "pa": UPI_ID,
        "pn": PAYEE_NAME,
        "am": f"{plan['price']:.2f}",
        "cu": "INR",
        "tn": f"Order {order_id} - {plan['name']}"
    }
    uri = "upi://pay?" + urllib.parse.urlencode(params)

    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(uri)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    stream = io.BytesIO()
    stream.name = f"payment_{order_id}.png"
    image.save(stream, format="PNG")
    stream.seek(0)
    return stream

# ==========================================
# MENUS AND PLAN DETAILS
# ==========================================

def send_home(chat_id):
    bot.send_message(
        chat_id,
        "👋 Welcome!\n\n"
        "1. Neeche se plan select karein.\n"
        "2. Demo aur details dekhein.\n"
        "3. BUY NOW se QR generate karein.\n"
        "4. Payment ke baad screenshot bhejein.",
        reply_markup=home_keyboard()
    )

def send_plan(chat_id, plan):
    caption = (
        f"📦 {plan['name']}\n\n"
        f"💰 Price: ₹{plan['price']}\n"
        f"🗓 Validity: {plan['validity']}\n"
        f"🎞 Videos: {plan['videos']}\n\n"
        f"{plan['description']}"
    )
    if plan.get("image"):
        try:
            bot.send_photo(
                chat_id, plan["image"],
                caption=caption,
                reply_markup=plan_keyboard(plan)
            )
            return
        except Exception:
            log.exception("Plan image failed")
    bot.send_message(
        chat_id, caption,
        reply_markup=plan_keyboard(plan)
    )

def send_demo(chat_id, plan):
    demos = [
        d for d in plan.get("demos", [])
        if d.get("id") and not d["id"].startswith("PASTE_")
    ]
    if not demos:
        bot.send_message(
            chat_id,
            f"🎬 {plan['name']} demo\n\n"
            "Demo file ID abhi set nahi hai. PLANS mein "
            "demos ke id field mein Telegram file_id daalein.",
            reply_markup=plan_keyboard(plan)
        )
        return

    for item in demos:
        try:
            if item["type"] == "video":
                bot.send_video(
                    chat_id, item["id"], has_spoiler=True
                )
            elif item["type"] == "photo":
                bot.send_photo(
                    chat_id, item["id"], has_spoiler=True
                )
            else:
                bot.send_document(chat_id, item["id"])
        except Exception:
            log.exception("Demo media failed")
            bot.send_message(
                chat_id, "Demo send nahi hua. File ID check karein."
            )

    send_plan(chat_id, plan)

# ==========================================
# BUY NOW -> GENERATE AND SEND QR
# ==========================================

def send_payment(chat_id, user_id, plan):
    order_id = create_order(user_id, plan)
    waiting_screenshot[user_id] = order_id
    qr_image = make_upi_qr(plan, order_id)

    caption = (
        f"💳 Payment: {plan['name']}\n"
        f"Amount: ₹{plan['price']}\n"
        f"Order ID: #{order_id}\n\n"
        "1. QR scan karein.\n"
        "2. Exact amount pay karein.\n"
        "3. Payment screenshot photo ke roop mein bhejein.\n\n"
        "Admin payment manually verify karega."
    )
    try:
        bot.send_photo(chat_id, qr_image, caption=caption)
        bot.send_message(
            chat_id,
            "Payment ke baad screenshot bhejein:",
            reply_markup=InlineKeyboardMarkup().add(
                button("❌ Cancel / Home", "home")
            )
        )
    except Exception:
        log.exception("QR send failed")
        set_order_status(order_id, "qr_send_failed")
        waiting_screenshot.pop(user_id, None)
        bot.send_message(
            chat_id, "QR send nahi hua. UPI settings check karein."
        )

# ==========================================
# COMMANDS
# ==========================================

@bot.message_handler(commands=["start", "plans"])
def start(message):
    waiting_screenshot.pop(message.from_user.id, None)
    send_home(message.chat.id)

@bot.message_handler(commands=["id"])
def show_id(message):
    bot.reply_to(
        message, f"Your Telegram user ID: {message.from_user.id}"
    )

# ==========================================
# CALLBACKS
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data == "home")
def home_callback(call):
    bot.answer_callback_query(call.id)
    waiting_screenshot.pop(call.from_user.id, None)
    send_home(call.message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "demo_menu")
def demo_menu_callback(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Demo ke liye plan select karein:",
        reply_markup=demo_keyboard()
    )

@bot.callback_query_handler(func=lambda c: c.data == "howto")
def howto_callback(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📖 HOW TO USE\n\n"
        "1. Plan select karein.\n"
        "2. Demo dekhein.\n"
        "3. BUY NOW dabayein.\n"
        "4. QR se exact amount pay karein.\n"
        "5. Screenshot photo bhejein.\n"
        "6. Admin verify karke status bhejega.",
        reply_markup=InlineKeyboardMarkup().add(
            button("🔙 Back", "home")
        )
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("plan:"))
def plan_callback(call):
    bot.answer_callback_query(call.id)
    try:
        plan = get_plan(int(call.data.split(":")[1]))
    except (ValueError, IndexError):
        plan = None
    if plan:
        send_plan(call.message.chat.id, plan)
    else:
        bot.send_message(call.message.chat.id, "Plan nahi mila.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("demo:"))
def demo_callback(call):
    bot.answer_callback_query(call.id)
    try:
        plan = get_plan(int(call.data.split(":")[1]))
    except (ValueError, IndexError):
        plan = None
    if plan:
        send_demo(call.message.chat.id, plan)
    else:
        bot.send_message(call.message.chat.id, "Plan nahi mila.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy:"))
def buy_callback(call):
    try:
        plan = get_plan(int(call.data.split(":")[1]))
    except (ValueError, IndexError):
        plan = None
    if not plan:
        bot.answer_callback_query(
            call.id, "Plan nahi mila.", show_alert=True
        )
        return
    bot.answer_callback_query(call.id)
    send_payment(
        call.message.chat.id, call.from_user.id, plan
    )

# ==========================================
# USER SENDS PAYMENT SCREENSHOT
# ==========================================

@bot.message_handler(content_types=["photo"])
def screenshot_handler(message):
    user_id = message.from_user.id
    order_id = waiting_screenshot.get(user_id)
    if not order_id:
        return

    order = get_order(order_id)
    if not order or order["status"] != "awaiting_screenshot":
        waiting_screenshot.pop(user_id, None)
        bot.reply_to(message, "Screenshot pending nahi hai. /start dabayein.")
        return

    plan = get_plan(order["plan_id"])
    if not plan:
        bot.reply_to(message, "Plan details nahi mili.")
        return

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        button("✅ Approve", f"review:approve:{order_id}"),
        button("❌ Reject", f"review:reject:{order_id}")
    )

    try:
        bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=(
                "💳 PAYMENT SCREENSHOT\n\n"
                f"Order: #{order_id}\n"
                f"User ID: {user_id}\n"
                f"Plan: {plan['name']}\n"
                f"Amount: ₹{order['amount']}\n\n"
                "UPI app mein payment verify karke hi approve karein."
            ),
            reply_markup=kb
        )
        set_order_status(order_id, "under_review")
        waiting_screenshot.pop(user_id, None)
        bot.reply_to(
            message,
            "✅ Screenshot admin ko bhej diya. Verification ke baad link milega."
        )
    except Exception:
        log.exception("Admin notification failed")
        bot.reply_to(message, "Submit nahi hua. Dobara try karein.")

@bot.message_handler(content_types=["text", "document"])
def other_message_handler(message):
    if message.from_user.id in waiting_screenshot:
        bot.reply_to(message, "Screenshot ko photo ke roop mein bhejein.")

# ==========================================
# ADMIN APPROVE / REJECT
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("review:"))
def review_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id, "Not allowed", show_alert=True
        )
        return

    parts = call.data.split(":")
    if len(parts) != 3 or parts[1] not in ("approve", "reject"):
        bot.answer_callback_query(call.id, "Invalid action", show_alert=True)
        return

    action = parts[1]
    try:
        order_id = int(parts[2])
    except ValueError:
        bot.answer_callback_query(call.id, "Invalid order", show_alert=True)
        return

    order = get_order(order_id)
    if not order:
        bot.answer_callback_query(call.id, "Order not found", show_alert=True)
        return
    if order["status"] != "under_review":
        bot.answer_callback_query(
            call.id, "Order already reviewed", show_alert=True
        )
        return

    if action == "approve":
        set_order_status(order_id, "approved")
        message = f"✅ Payment approved!\nOrder: #{order_id}"
        result = "approved"
    else:
        set_order_status(order_id, "rejected")
        message = f"❌ Payment screenshot rejected for order #{order_id}.\nContact support if needed."
        result = "rejected"

    try:
        bot.send_message(order["user_id"], message)
    except Exception:
        log.exception("Could not notify user")

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"Order {result}")
    bot.send_message(
        ADMIN_ID, f"Order #{order_id} {result}. User {order['user_id']}."
    )

# ==========================================
# START BOT
# ==========================================

if __name__ == "__main__":
    init_db()
    log.info("Starting Telegram plans bot")
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )
