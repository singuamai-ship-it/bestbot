import os
import asyncio
import io
import logging
import random
import datetime
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
    InputMediaPhoto,
    InputMediaVideo
)
import qrcode

# ==========================================
# CONFIGURATION & DATABASE SETUP
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE").strip()
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "123456789").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 123456789

if not BOT_TOKEN or BOT_TOKEN == "8959940152:AAHLJQY2wBGgGL-NCmgmXjbtKez9HcATfgs":
    raise ValueError("❌ BOT_TOKEN missing! Please add BOT_TOKEN in your Railway variables.")

DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS demos (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_key TEXT, media_type TEXT, file_id TEXT)")
    conn.commit()
    
    cursor.execute("SELECT value FROM settings WHERE key='current_upi'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('current_upi', 'haaland78@ybl')")
        conn.commit()
    conn.close()

init_db()

SUPPORT_TG_URL = "https://t.me/xylerigcc"

# Plan Definitions (10 Plans + 1 VIP Plan)
PLANS = {
    "p1": {"name": "Plan 1 - Basic", "amount": 50},
    "p2": {"name": "Plan 2 - Starter", "amount": 99},
    "p3": {"name": "Plan 3 - Silver", "amount": 149},
    "p4": {"name": "Plan 4 - Gold", "amount": 199},
    "p5": {"name": "Plan 5 - Platinum", "amount": 249},
    "p6": {"name": "Plan 6 - Diamond", "amount": 299},
    "p7": {"name": "Plan 7 - Master", "amount": 349},
    "p8": {"name": "Plan 8 - Ultra", "amount": 399},
    "p9": {"name": "Plan 9 - Pro", "amount": 449},
    "p10": {"name": "Plan 10 - Ultimate", "amount": 499},
    "vip": {"name": "ALL VIP PLANS 👑", "amount": 999}
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==========================================
# DATABASE HELPER FUNCTIONS
# ==========================================
def get_current_upi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='current_upi'")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "haaland78@ybl"

def set_current_upi(new_upi):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value=? WHERE key='current_upi'", (new_upi,))
    conn.commit()
    conn.close()

def add_user_db(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_plan_demos(plan_key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT media_type, file_id FROM demos WHERE plan_key=?", (plan_key,))
    demos = [{"type": row[0], "file_id": row[1]} for row in cursor.fetchall()]
    conn.close()
    return demos

def add_demo_db(plan_key, media_type, file_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO demos (plan_key, media_type, file_id) VALUES (?, ?, ?)", (plan_key, media_type, file_id))
    conn.commit()
    conn.close()

def clear_plan_demos(plan_key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM demos WHERE plan_key=?", (plan_key,))
    conn.commit()
    conn.close()

# ==========================================
# STATES (FSM)
# ==========================================
class BotStates(StatesGroup):
    waiting_for_screenshot = State()
    waiting_new_upi = State()
    waiting_broadcast = State()
    waiting_demo_plan = State()
    waiting_demo_media = State()
    waiting_getid_media = State()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def generate_upi_qr(upi_id: str, amount: float, payee_name: str = "VIP Access") -> io.BytesIO:
    upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount:.2f}&cu=INR"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def generate_txn_id(plan_key: str) -> str:
    date_str = datetime.datetime.now().strftime("%y%m%d")
    rand_str = f"{random.randint(1000, 9999)}"
    return f"TXN-{date_str}-{plan_key}-{rand_str}"

async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def safe_delete_messages(chat_id: int, message_ids: list):
    for msg_id in message_ids:
        await safe_delete_message(chat_id, msg_id)

# ==========================================
# KEYBOARDS
# ==========================================
def get_main_menu_keyboard():
    buttons = []
    for key, data in PLANS.items():
        if key != "vip":
            buttons.append([InlineKeyboardButton(text=f"🔴 {data['name']} - ₹{data['amount']}", callback_data=f"select_plan:{key}")])

    buttons.append([InlineKeyboardButton(text=f"🔥 ALL VIP PLANS - ₹{PLANS['vip']['amount']} 🔥", callback_data="select_plan:vip")])

    buttons.append([
        InlineKeyboardButton(text="🔵 How To Use", callback_data="how_to_use"),
        InlineKeyboardButton(text="🟢 Support 24/7", url=SUPPORT_TG_URL)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==========================================
# USER HANDLERS
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    add_user_db(message.from_user.id)

    caption_text = (
        "🔥 **WELCOME TO THE ULTIMATE VIP STORE** 🔥\n\n"
        "⚡ Get instant access to premium verified courses & materials.\n"
        "⚡ Watch exclusive high-quality demo videos before purchasing.\n"
        "⚡ Fast automatic verification and instant order delivery.\n"
        "⚡ 100% secure payment gateway with instant QR generation.\n"
        "⚡ Unlimited streaming and lifetime cloud downloads access.\n"
        "⚡ Regular daily updates included with zero extra hidden costs.\n"
        "⚡ Trusted by thousands of happy learners worldwide.\n"
        "⚡ Professional 24/7 active customer support team ready to help.\n"
        "⚡ Choose any plan below to check demos and start learning.\n\n"
        "👇 **Select your plan from the menu below:**"
    )

    msg = await message.answer(
        text=caption_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await state.update_data(last_menu_id=msg.message_id)


@dp.callback_query(F.data.startswith("select_plan:"))
async def handle_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split(":")[1]
    plan_data = PLANS[plan_key]
    data = await state.get_data()

    if "last_menu_id" in data:
        await safe_delete_message(callback.message.chat.id, data["last_menu_id"])

    if plan_key == "vip":
        await show_payment_qr(callback.message.chat.id, plan_key, state)
        await callback.answer()
        return

    demo_msg_ids = []
    demos = get_plan_demos(plan_key)

    if demos:
        media_group = []
        for media in demos:
            if media["type"] == "photo":
                media_group.append(InputMediaPhoto(media=media["file_id"], has_spoiler=True))
            elif media["type"] == "video":
                media_group.append(InputMediaVideo(media=media["file_id"], has_spoiler=True))

        sent_medias = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
        demo_msg_ids.extend([m.message_id for m in sent_medias])
    else:
        info_msg = await callback.message.answer("ℹ️ *Demo media for this plan will be added soon by admin.*", parse_mode="Markdown")
        demo_msg_ids.append(info_msg.message_id)

    demo_caption = (
        f"🌟 **{plan_data['name']} - Exclusive Preview**\n\n"
        f"✅ Full unlocked HD video lectures & downloadable study materials.\n"
        f"✅ Step-by-step masterclass modules designed for fast learning.\n"
        f"✅ Lifetime membership access with all future updates included.\n"
        f"✅ Total Price: ₹{plan_data['amount']}\n\n"
        f"👇 Click **Buy Now** to generate your secure payment QR code!"
    )

    demo_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🟢 𝘽𝙐𝙔 𝙉𝙊𝙒 — ₹{plan_data['amount']}", callback_data=f"buy_now:{plan_key}")],
        [InlineKeyboardButton(text="🔵 BACK TO PLANS", callback_data="back_to_main")]
    ])

    caption_msg = await callback.message.answer(text=demo_caption, reply_markup=demo_kb, parse_mode="Markdown")
    demo_msg_ids.append(caption_msg.message_id)

    await state.update_data(demo_msg_ids=demo_msg_ids)
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_now:"))
async def handle_buy_now(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split(":")[1]
    data = await state.get_data()

    if "demo_msg_ids" in data:
        await safe_delete_messages(callback.message.chat.id, data["demo_msg_ids"])

    await show_payment_qr(callback.message.chat.id, plan_key, state)
    await callback.answer()


async def show_payment_qr(chat_id: int, plan_key: str, state: FSMContext):
    plan_data = PLANS[plan_key]
    txn_id = generate_txn_id(plan_key)
    current_upi = get_current_upi()

    qr_buffer = generate_upi_qr(current_upi, plan_data["amount"])
    qr_file = BufferedInputFile(qr_buffer.getvalue(), filename="payment_qr.png")

    caption = (
        f"🔥 **Pay To Get Paid Access**\n\n"
        f"🆔 **TXN:** `{txn_id}`\n"
        f"💎 **UPI:** `{current_upi}` (tap to copy)\n"
        f"📦 **Plan:** {plan_data['name']}\n"
        f"💰 **Amount:** ₹{plan_data['amount']}\n\n"
        f"📲 Scan the QR or copy the UPI ID above and pay the exact amount."
    )

    payment_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Verify Payment", callback_data=f"verify_payment:{plan_key}:{txn_id}")],
        [InlineKeyboardButton(text="🔴 Cancel Purchase", callback_data="back_to_main")]
    ])

    msg = await bot.send_photo(
        chat_id=chat_id,
        photo=qr_file,
        caption=caption,
        reply_markup=payment_kb,
        parse_mode="Markdown"
    )

    await state.update_data(
        current_plan=plan_key,
        txn_id=txn_id,
        payment_msg_id=msg.message_id
    )


@dp.callback_query(F.data.startswith("verify_payment:"))
async def handle_verify_payment(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    plan_key = parts[1]
    txn_id = parts[2]

    await state.set_state(BotStates.waiting_for_screenshot)
    await state.update_data(current_plan=plan_key, txn_id=txn_id)

    screen_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Back", callback_data="back_to_main")]
    ])

    await callback.message.answer(
        "📸 **Please send your payment screenshot now as a photo for verification:**",
        reply_markup=screen_kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(BotStates.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("current_plan")
    txn_id = data.get("txn_id")

    if not plan_key or not txn_id:
        await message.answer("❌ Payment session expired. Please start again with /start.")
        await state.clear()
        return

    plan_data = PLANS[plan_key]
    screenshot_id = message.photo[-1].file_id

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 APPROVE PAYMENT", callback_data=f"admin_approve:{message.from_user.id}:{plan_key}:{txn_id}")],
        [InlineKeyboardButton(text="🔴 REJECT PAYMENT", callback_data=f"admin_reject:{message.from_user.id}:{txn_id}")]
    ])

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=screenshot_id,
        caption=(
            f"📥 **NEW PAYMENT PROOF RECEIVED**\n\n"
            f"👤 User: {message.from_user.full_name}\n"
            f"🆔 User ID: `{message.from_user.id}`\n"
            f"📦 Plan: {plan_data['name']}\n"
            f"💰 Amount: ₹{plan_data['amount']}\n"
            f"🆔 TXN: `{txn_id}`"
        ),
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )

    await message.answer("⌛ **Screenshot received! Waiting for admin approval...**", parse_mode="Markdown")
    await state.clear()


@dp.callback_query(F.data.startswith("admin_approve:"))
async def handle_admin_approve(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ You are not authorized.", show_alert=True)
        return

    parts = callback.data.split(":")
    user_id = int(parts[1])
    plan_key = parts[2]
    txn_id = parts[3]
    plan_data = PLANS[plan_key]

    try:
        await bot.send_message(
            user_id,
            f"✅ **Payment Verified! Successfully purchased {plan_data['name']}.**",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Could not notify user {user_id}: {e}")

    screenshot_id = callback.message.photo[-1].file_id if callback.message.photo else None

    broadcast_caption = (
        f"🎉 **NEW SUCCESSFUL PURCHASE** 🎉\n\n"
        f"📦 **Plan:** {plan_data['name']}\n"
        f"💰 **Amount:** ₹{plan_data['amount']}\n"
        f"🟢 **STATUS - SUCCESSFULLY PURCHASED**\n\n"
        f"👇 **Explore all plans below:**"
    )

    all_users = get_all_users()
    for uid in all_users:
        try:
            if screenshot_id:
                await bot.send_photo(
                    chat_id=uid,
                    photo=screenshot_id,
                    caption=broadcast_caption,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=broadcast_caption,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="Markdown"
                )
        except Exception:
            pass

    await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n🟢 **APPROVED & BROADCASTED**")
    await callback.answer("Payment approved & broadcasted!")


@dp.callback_query(F.data.startswith("admin_reject:"))
async def handle_admin_reject(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ You are not authorized.", show_alert=True)
        return

    parts = callback.data.split(":")
    user_id = int(parts[1])

    try:
        await bot.send_message(
            user_id,
            "❌ **Payment Verification Failed or Rejected by Admin.** Please contact support if you paid.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Could not notify user {user_id}: {e}")

    await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n🔴 **REJECTED BY ADMIN**")
    await callback.answer("Payment rejected!")


@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    
    msg = await callback.message.answer(
        "👇 **Select your plan from the menu below:**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await state.update_data(last_menu_id=msg.message_id)
    await callback.answer()


@dp.callback_query(F.data == "how_to_use")
async def handle_how_to_use(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "last_menu_id" in data:
        await safe_delete_message(callback.message.chat.id, data["last_menu_id"])

    how_to_text = (
        "📘 **HOW TO USE THIS BOT:**\n\n"
        "\n\n\n\n\n\n\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 BACK TO PLANS", callback_data="back_to_main")]
    ])

    msg = await callback.message.answer(
        text=how_to_text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.update_data(last_menu_id=msg.message_id)
    await callback.answer()


# ==========================================
# ADMIN COMMANDS
# ==========================================

@dp.message(Command("upi"), F.from_user.id == ADMIN_ID)
async def cmd_set_upi(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_new_upi)
    await message.answer("✍️ **Send the new UPI ID:**", parse_mode="Markdown")


@dp.message(BotStates.waiting_new_upi, F.from_user.id == ADMIN_ID)
async def process_new_upi(message: types.Message, state: FSMContext):
    new_upi = message.text.strip()
    if "@" not in new_upi:
        await message.answer("❌ Invalid UPI ID. Please send a valid UPI ID.")
        return

    set_current_upi(new_upi)
    await message.answer(f"✅ **UPI ID updated successfully to:** `{new_upi}`", parse_mode="Markdown")
    await state.clear()


@dp.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def cmd_broadcast(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_broadcast)
    await message.answer("📢 **Send the message you want to broadcast to all users:**", parse_mode="Markdown")


@dp.message(BotStates.waiting_broadcast, F.from_user.id == ADMIN_ID)
async def process_broadcast(message: types.Message, state: FSMContext):
    sent_count = 0
    failed_count = 0
    all_users = get_all_users()

    for user_id in all_users:
        try:
            await message.copy_to(chat_id=user_id)
            sent_count += 1
        except Exception as e:
            logging.error(f"Broadcast failed for {user_id}: {e}")
            failed_count += 1

    await message.answer(
        f"✅ **Broadcast complete.**\nSent: {sent_count}\nFailed: {failed_count}",
        parse_mode="Markdown"
    )
    await state.clear()


@dp.message(Command("setdemo"), F.from_user.id == ADMIN_ID)
async def cmd_set_demo(message: types.Message, state: FSMContext):
    buttons = []
    for key, data in PLANS.items():
        buttons.append([
            InlineKeyboardButton(
                text=data["name"],
                callback_data=f"set_demo_plan:{key}"
            )
        ])

    await message.answer(
        "⚙️ **Choose the plan to add demo media to:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("set_demo_plan:"), F.from_user.id == ADMIN_ID)
async def handle_set_demo_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split(":")[1]
    await state.update_data(demo_plan_key=plan_key)
    await state.set_state(BotStates.waiting_demo_media)

    await callback.message.answer(
        f"📸 **Send photo/video for plan '{PLANS[plan_key]['name']}':**\n"
        "You can send multiple media items one by one. Use /done when finished.",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(BotStates.waiting_demo_media, F.from_user.id == ADMIN_ID, F.photo | F.video)
async def process_demo_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("demo_plan_key")

    if not plan_key:
        await message.answer("❌ No plan selected. Start again with /setdemo.")
        await state.clear()
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        add_demo_db(plan_key, "photo", file_id)
    else:
        file_id = message.video.file_id
        add_demo_db(plan_key, "video", file_id)

    total_demos = len(get_plan_demos(plan_key))
    await message.answer(
        f"✅ **Demo added to {PLANS[plan_key]['name']}! (Total: {total_demos})**\n"
        "Send more media or use /done when finished.",
        parse_mode="Markdown"
    )


@dp.message(Command("removedemo"), F.from_user.id == ADMIN_ID)
async def cmd_remove_demo(message: types.Message, state: FSMContext):
    buttons = []
    for key, data in PLANS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 Clear {data['name']}",
                callback_data=f"clear_demo_plan:{key}"
            )
        ])

    await message.answer(
        "🗑 **Choose the plan whose demos you want to remove:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("clear_demo_plan:"), F.from_user.id == ADMIN_ID)
async def handle_clear_demo_plan(callback: types.CallbackQuery):
    plan_key = callback.data.split(":")[1]
    clear_plan_demos(plan_key)
    await callback.message.edit_text(f"✅ **All demos for {PLANS[plan_key]['name']} have been successfully cleared!**", parse_mode="Markdown")
    await callback.answer()


@dp.message(Command("done"), F.from_user.id == ADMIN_ID)
async def cmd_done(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BotStates.waiting_demo_media.state:
        await state.clear()
        await message.answer("✅ **Demo media setup completed successfully.**", parse_mode="Markdown")
    else:
        await message.answer("No active setup to finish.")


@dp.message(Command("getid"), F.from_user.id == ADMIN_ID)
async def cmd_get_id(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_getid_media)
    await message.answer("📹 **Send any Photo or Video to get its File ID:**", parse_mode="Markdown")


@dp.message(BotStates.waiting_getid_media, F.from_user.id == ADMIN_ID, F.photo | F.video)
async def process_getid_media(message: types.Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        await message.answer(f"🖼 **Photo File ID:**\n`{file_id}`", parse_mode="Markdown")
    elif message.video:
        file_id = message.video.file_id
        await message.answer(f"🎥 **Video File ID:**\n`{file_id}`", parse_mode="Markdown")
    await state.clear()


# ==========================================
# BOT STARTUP
# ==========================================
async def main():
    print("🚀 VIP Store Bot is starting successfully...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
