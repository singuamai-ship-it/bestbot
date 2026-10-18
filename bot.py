import asyncio
import io
import logging
import random
import datetime
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
# CONFIGURATION & VARIABLES
# ==========================================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
ADMIN_ID = 123456789  # Replace with your numeric Telegram User ID

# Dynamic Variables
CURRENT_UPI = "haaland78@ybl"
SUPPORT_TG_URL = "https://t.me/xylerigcc"

# User Tracking DB (In-Memory for simplicity)
USER_IDS = set()

# Plan Definitions (10 Plans + 1 VIP Plan)
PLANS = {
    "p1": {"name": "Plan 1 - Basic", "amount": 50, "demos": []},
    "p2": {"name": "Plan 2 - Starter", "amount": 99, "demos": []},
    "p3": {"name": "Plan 3 - Silver", "amount": 149, "demos": []},
    "p4": {"name": "Plan 4 - Gold", "amount": 199, "demos": []},
    "p5": {"name": "Plan 5 - Platinum", "amount": 249, "demos": []},
    "p6": {"name": "Plan 6 - Diamond", "amount": 299, "demos": []},
    "p7": {"name": "Plan 7 - Master", "amount": 349, "demos": []},
    "p8": {"name": "Plan 8 - Ultra", "amount": 399, "demos": []},
    "p9": {"name": "Plan 9 - Pro", "amount": 449, "demos": []},
    "p10": {"name": "Plan 10 - Ultimate", "amount": 499, "demos": []},
    "vip": {"name": "ALL VIP PLANS 👑", "amount": 999, "demos": []}
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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
    # 10 Regular Danger Plans
    for key, data in PLANS.items():
        if key != "vip":
            buttons.append([InlineKeyboardButton(text=f"🚨 {data['name']} - ₹{data['amount']}", callback_data=f"select_plan:{key}")])
    
    # VIP Plan at bottom
    buttons.append([InlineKeyboardButton(text=f"🔥 ALL VIP PLANS - ₹{PLANS['vip']['amount']} 🔥", callback_data="select_plan:vip")])
    
    # Bottom Row: How to Use (Blue) & Support (Green)
    buttons.append([
        InlineKeyboardButton(text="📘 How To Use", callback_data="how_to_use"),
        InlineKeyboardButton(text="🟢 Support 24/7", url=SUPPORT_TG_URL)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==========================================
# USER HANDLERS
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    USER_IDS.add(message.from_user.id)
    
    caption_text = (
        "🔥 **WELCOME TO PREMIUM VIP STORE** 🔥\n\n"
        "⚡ Choose your desired plan from below to get instant access.\n"
        "⚡ Watch exclusive demo videos before purchasing.\n"
        "⚡ Instant approval & auto delivery system enabled.\n"
        "⚡ 100% safe, verified & high quality content guaranteed.\n"
        "⚡ 24/7 Active support available for all users.\n\n"
        "👇 **Select a plan below to continue:**"
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
    
    # Clear previous menu / messages
    if "last_menu_id" in data:
        await safe_delete_message(callback.message.chat.id, data["last_menu_id"])
    
    # VIP Direct QR flow
    if plan_key == "vip":
        await show_payment_qr(callback.message.chat.id, plan_key, state)
        await callback.answer()
        return

    # Regular Plan Demo Flow
    demo_msg_ids = []
    
    # Send Demo Media Group if available
    if plan_data["demos"]:
        media_group = []
        for media in plan_data["demos"]:
            if media["type"] == "photo":
                media_group.append(InputMediaPhoto(media=media["file_id"], has_spoiler=True))
            elif media["type"] == "video":
                media_group.append(InputMediaVideo(media=media["file_id"], has_spoiler=True))
        
        sent_medias = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
        demo_msg_ids.extend([m.message_id for m in sent_medias])
    else:
        info_msg = await callback.message.answer("ℹ️ *Demo media for this plan will be added soon.*", parse_mode="Markdown")
        demo_msg_ids.append(info_msg.message_id)

    # Demo Bottom Caption & Buttons
    demo_caption = (
        f"🌟 **{plan_data['name']} - Demo Content**\n\n"
        f"✅ Full High Quality Unlocked Course Material.\n"
        f"✅ Unlimited Streaming & Lifetime Downloads Access.\n"
        f"✅ Total Price: ₹{plan_data['amount']}\n\n"
        f"👇 Click **Buy Now** below to proceed with payment!"
    )
    
    demo_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🟢 Buy Now - ₹{plan_data['amount']}", callback_data=f"buy_now:{plan_key}")],
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
    
    # Delete demo messages and caption
    if "demo_msg_ids" in data:
        await safe_delete_messages(callback.message.chat.id, data["demo_msg_ids"])
    
    await show_payment_qr(callback.message.chat.id, plan_key, state)
    await callback.answer()


async def show_payment_qr(chat_id: int, plan_key: str, state: FSMContext):
    plan_data = PLANS[plan_key]
    txn_id = generate_txn_id(plan_key)
    
    qr_buf = generate_upi_qr(CURRENT_UPI, plan_data["amount"])
    qr_file = BufferedInputFile(qr_buf.getvalue(), filename="qr.png")
    
    pay_caption = (
        f"🔥 **Pay To Get Paid Access**\n\n"
        f"🆔 **TXN:** `{txn_id}`\n"
        f"💎 **UPI ID:** `{CURRENT_UPI}` (tap to copy)\n"
        f"📦 **Plan:** {plan_data['name']}\n"
        f"💰 **Amount:** ₹{plan_data['amount']}\n\n"
        f"📲 Scan the QR or copy the UPI ID above and pay the exact amount."
    )
    
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Verify Payment", callback_data=f"verify_pay:{plan_key}:{txn_id}")],
        [InlineKeyboardButton(text="🔴 Cancel Purchase", callback_data="back_to_main")]
    ])
    
    qr_msg = await bot.send_photo(
        chat_id=chat_id,
        photo=qr_file,
        caption=pay_caption,
        reply_markup=pay_kb,
        parse_mode="Markdown"
    )
    await state.update_data(qr_msg_id=qr_msg.message_id)


@dp.callback_query(F.data.startswith("verify_pay:"))
async def handle_verify_pay(callback: types.CallbackQuery, state: FSMContext):
    _, plan_key, txn_id = callback.data.split(":")
    data = await state.get_data()
    
    # Delete QR code message
    if "qr_msg_id" in data:
        await safe_delete_message(callback.message.chat.id, data["qr_msg_id"])
    
    # Prompt for Screenshot
    screen_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Back", callback_data="back_to_main")]
    ])
    
    prompt_msg = await callback.message.answer(
        text="📸 **Please send the payment screenshot now for verification:**",
        reply_markup=screen_kb,
        parse_mode="Markdown"
    )
    
    await state.set_state(BotStates.waiting_for_screenshot)
    await state.update_data(
        pending_plan_key=plan_key,
        pending_txn_id=txn_id,
        prompt_msg_id=prompt_msg.message_id
    )
    await callback.answer()


@dp.message(BotStates.waiting_for_screenshot, F.photo)
async def process_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data["pending_plan_key"]
    txn_id = data["pending_txn_id"]
    plan_data = PLANS[plan_key]
    
    # Delete prompt message
    if "prompt_msg_id" in data:
        await safe_delete_message(message.chat.id, data["prompt_msg_id"])
    
    # Notify User
    await message.answer("⌛ **Screenshot received! Waiting for admin approval...**", parse_mode="Markdown")
    
    # Forward to Admin for approval
    photo_file_id = message.photo[-1].file_id
    admin_caption = (
        f"📥 **NEW PAYMENT PROOF RECEIVED**\n\n"
        f"👤 **User:** {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"📦 **Plan:** {plan_data['name']}\n"
        f"💰 **Amount:** ₹{plan_data['amount']}\n"
        f"🆔 **TXN:** `{txn_id}`"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Approve", callback_data=f"admin_app:{message.from_user.id}:{plan_key}:{txn_id}"),
            InlineKeyboardButton(text="🔴 Reject", callback_data=f"admin_rej:{message.from_user.id}:{txn_id}")
        ]
    ])
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=admin_caption,
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    await state.clear()


@dp.callback_query(F.data == "how_to_use")
async def handle_how_to_use(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "last_menu_id" in data:
        await safe_delete_message(callback.message.chat.id, data["last_menu_id"])
    
    how_to_text = (
        "📘 **HOW TO USE THIS BOT:**\n\n"
        "\n\n\n\n\n\n\n"  # 7 Blank lines requested
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 BACK TO PLANS", callback_data="back_to_main")]
    ])
    
    msg = await callback.message.answer(text=how_to_text, reply_markup=kb, parse_mode="Markdown")
    await state.update_data(last_menu_id=msg.message_id)
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await cmd_start(callback.message, state)


# ==========================================
# ADMIN HANDLERS
# ==========================================

@dp.callback_query(F.data.startswith("admin_app:"))
async def handle_admin_approve(callback: types.CallbackQuery):
    _, user_id, plan_key, txn_id = callback.data.split(":")
    user_id = int(user_id)
    plan_data = PLANS[plan_key]
    
    # Notify User
    await bot.send_message(
        chat_id=user_id,
        text=f"✅ **Payment Verified! Successfully purchased {plan_data['name']}.**",
        parse_mode="Markdown"
    )
    
    # Broadcast to ALL Users
    broadcast_msg = (
        f"🎉 **NEW SUCCESSFUL PURCHASE** 🎉\n\n"
        f"📦 **Plan:** {plan_data['name']}\n"
        f"💰 **Amount:** ₹{plan_data['amount']}\n"
        f" STATUS - SUCCESSFULLY PURCHASED\n\n"
        f"👇 **Explore all plans below:**"
    )
    
    for uid in list(USER_IDS):
        try:
            await bot.send_message(chat_id=uid, text=broadcast_msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        except Exception:
            pass
            
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **APPROVED BY ADMIN**")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_rej:"))
async def handle_admin_reject(callback: types.CallbackQuery):
    _, user_id, txn_id = callback.data.split(":")
    user_id = int(user_id)
    
    await bot.send_message(
        chat_id=user_id,
        text="❌ **Payment Verification Failed or Rejected by Admin.** Please contact support if you paid.",
        parse_mode="Markdown"
    )
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **REJECTED BY ADMIN**")
    await callback.answer()


@dp.message(Command("upi"), F.from_user.id == ADMIN_ID)
async def cmd_upi_change(message: types.Message, state: FSMContext):
    await message.answer("✍️ **Send the new UPI ID:**", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_new_upi)


@dp.message(BotStates.waiting_new_upi, F.from_user.id == ADMIN_ID)
async def process_new_upi(message: types.Message, state: FSMContext):
    global CURRENT_UPI
    CURRENT_UPI = message.text.strip()
    await message.answer(f"✅ **UPI ID updated successfully to:** `{CURRENT_UPI}`", parse_mode="Markdown")
    await state.clear()


@dp.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def cmd_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 **Send the message you want to broadcast to all users:**", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_broadcast)


@dp.message(BotStates.waiting_broadcast, F.from_user.id == ADMIN_ID)
async def process_broadcast(message: types.Message, state: FSMContext):
    count = 0
    for uid in list(USER_IDS):
        try:
            await message.copy_to(chat_id=uid)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ **Broadcast sent to {count} users.**", parse_mode="Markdown")
    await state.clear()


@dp.message(Command("add_demo"), F.from_user.id == ADMIN_ID)
async def cmd_add_demo(message: types.Message, state: FSMContext):
    buttons = []
    for key, data in PLANS.items():
        buttons.append([InlineKeyboardButton(text=data['name'], callback_data=f"set_demo_plan:{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("⚙️ **Select plan to add demo media:**", reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("set_demo_plan:"), F.from_user.id == ADMIN_ID)
async def handle_set_demo_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split(":")[1]
    await callback.message.answer(f"📸 **Send photo/video for plan '{PLANS[plan_key]['name']}':**", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_demo_media)
    await state.update_data(target_demo_plan=plan_key)
    await callback.answer()


@dp.message(BotStates.waiting_demo_media, F.from_user.id == ADMIN_ID)
async def process_demo_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data["target_demo_plan"]
    
    media_obj = None
    if message.photo:
        media_obj = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        media_obj = {"type": "video", "file_id": message.video.file_id}
        
    if media_obj:
        PLANS[plan_key]["demos"].append(media_obj)
        await message.answer(f"✅ **Demo added to {PLANS[plan_key]['name']}! (Total: {len(PLANS[plan_key]['demos'])})**", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Please send a Photo or Video.")
    await state.clear()


@dp.message(Command("getid"), F.from_user.id == ADMIN_ID)
async def cmd_getid(message: types.Message, state: FSMContext):
    await message.answer("📹 **Send any Photo or Video to get its File ID:**", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_getid_media)


@dp.message(BotStates.waiting_getid_media, F.from_user.id == ADMIN_ID)
async def process_getid_media(message: types.Message, state: FSMContext):
    if message.photo:
        fid = message.photo[-1].file_id
        await message.answer(f"🖼 **Photo File ID:**\n`{fid}`", parse_mode="Markdown")
    elif message.video:
        fid = message.video.file_id
        await message.answer(f"🎥 **Video File ID:**\n`{fid}`", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Send a photo or video.")
    await state.clear()

# ==========================================
# MAIN EXECUTION
# ==========================================
async def main():
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
