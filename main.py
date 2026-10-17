import os, io, sqlite3, logging
from datetime import datetime, timezone
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_RAW = os.getenv("ADMIN_ID", "").strip()
UPI_ID = os.getenv("UPI_ID", "").strip()
PAYEE_NAME = os.getenv("PAYEE_NAME", "My Store")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "YOUR_SUPPORT_USERNAME").lstrip("@")
DB_PATH = os.getenv("DB_PATH", "bot_data.sqlite3")

if not TOKEN: raise RuntimeError("Set BOT_TOKEN")
if not ADMIN_RAW.isdigit(): raise RuntimeError("Set ADMIN_ID to numeric Telegram user ID")
if not UPI_ID: raise RuntimeError("Set UPI_ID, e.g. name@upi")
ADMIN_ID = int(ADMIN_RAW)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("plansbot")
bot = telebot.TeleBot(TOKEN)

# Replace sample values and add Telegram media file_ids.
# Media items: {"type":"photo","id":"file_id"} or {"type":"video","id":"file_id"}
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
DB = sqlite3.connect
waiting = {}

def conn():
    c = DB(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    return c

with conn() as c:
    c.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_id INTEGER, amount INTEGER,
      status TEXT, created_at TEXT, admin_message_id INTEGER)""")

def remember(u):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO users VALUES(?,?,?)", (u.id, u.first_name or "", u.username or ""))

def plan(pid):
    return next((p for p in PLANS if p["id"] == pid), None)

def btn(text, data=None, url=None, style=None):
    kw={"text":text}
    if data is not None: kw["callback_data"]=data
    if url: kw["url"]=url
    if style: kw["style"]=style
    try: return InlineKeyboardButton(**kw)
    except (TypeError, ValueError):
        kw.pop("style", None)
        return InlineKeyboardButton(**kw)

def home_kb():
    k=InlineKeyboardMarkup(row_width=2)
    for p in PLANS: k.add(btn(f" {p['name']} · ₹{p['price']}", f"plan:{p['id']}", style="danger"))
    k.row(btn("📘 How to use","howto",style="primary"), btn("🆘 Support",url=f"https://t.me/{SUPPORT_USERNAME}",style="primary"))
    return k

def back_kb(pid):
    k=InlineKeyboardMarkup(row_width=2)
    k.row(btn(" BUY NOW",f"buy:{pid}",style="success"),btn(" Back","home",style="primary"))
    return k

def upi_uri(p):
    from urllib.parse import quote
    return f"upi://pay?pa={quote(UPI_ID,safe='@._-')}&pn={quote(PAYEE_NAME)}&am={p['price']}&cu=INR&tn={quote(p['name']+' order')}"

def qr_image(p):
    f=io.BytesIO()
    qrcode.make(upi_uri(p)).save(f,format="PNG")
    f.name="upi_qr.png"; f.seek(0)
    return f

def send_home(chat_id):
    text=("👋 Welcome!\n━━━━━━━━━━━━━━━━━━\n📦 Choose a plan below.\n🎬 Open the demo previews.\n🔎 Demos are spoiler-hidden where supported.\n💳 Tap Buy Now to continue.\n📲 Scan the UPI QR to pay.\n🧾 Pay the exact amount shown.\n📸 Tap Verify Payment.\n📤 Send your payment screenshot as a photo.\n⏳ Admin will review the transaction.\n✅ You’ll be notified after review.\n🆘 Use Support if you need help.\n━━━━━━━━━━━━━━━━━━")
    bot.send_message(chat_id,text,reply_markup=home_kb())

@bot.message_handler(commands=["start","menu"])
def start(m):
    remember(m.from_user); waiting.pop(m.from_user.id,None); send_home(m.chat.id)

@bot.callback_query_handler(func=lambda c:c.data=="home")
def go_home(c):
    bot.answer_callback_query(c.id); remember(c.from_user); send_home(c.message.chat.id)

@bot.callback_query_handler(func=lambda c:c.data=="howto")
def howto(c):
    bot.answer_callback_query(c.id)
    k=InlineKeyboardMarkup().add(btn("🔙 Back","home",style="primary"))
    bot.send_message(c.message.chat.id,"HOW TO USE\n\n1. Select a plan.\n2. Preview the spoiler-hidden demos.\n3. Tap BUY NOW, then Confirm.\n4. Pay the exact amount using the QR.\n5. Tap Verify Payment.\n6. Send the screenshot as a photo.\n7. Wait for admin review.\n\nA screenshot is not automatic proof of payment.",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("plan:"))
def show_plan(c):
    bot.answer_callback_query(c.id)
    try: pid=int(c.data.split(":")[1])
    except: return
    p=plan(pid)
    if not p: return
    for item in p["media"][:6]:
        fid=str(item.get("id","")).strip()
        if not fid or fid.startswith("PASTE_"): continue
        try:
            if item.get("type")=="video": bot.send_video(c.message.chat.id,fid,has_spoiler=True,protect_content=True)
            else: bot.send_photo(c.message.chat.id,fid,has_spoiler=True,protect_content=True)
        except Exception: log.exception("Demo media send failed")
    bot.send_message(c.message.chat.id,f"📦 {p['name']}\n💰 Price: ₹{p['price']}\n🗓 Validity: {p['validity']}\n\n{p['description']}\n\nTap a spoiler to reveal demo media.",reply_markup=back_kb(pid))

@bot.callback_query_handler(func=lambda c:c.data.startswith("buy:"))
def buy(c):
    bot.answer_callback_query(c.id)
    try: pid=int(c.data.split(":")[1])
    except: return
    p=plan(pid)
    if not p:return
    k=InlineKeyboardMarkup(row_width=2)
    k.row(btn("✅ Confirm",f"confirm:{pid}",style="success"),btn("🔵 Back",f"plan:{pid}",style="primary"))
    bot.send_message(c.message.chat.id,f"Confirm your selection:\n\nPlan: {p['name']}\nAmount: ₹{p['price']}\nValidity: {p['validity']}",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("confirm:"))
def confirm(c):
    bot.answer_callback_query(c.id)
    try: pid=int(c.data.split(":")[1])
    except: return
    p=plan(pid)
    if not p:return
    k=InlineKeyboardMarkup(row_width=2)
    k.row(btn("📸 Verify Payment",f"verify:{pid}",style="success"),btn("🔵 Back",f"plan:{pid}",style="primary"))
    img=qr_image(p)
    bot.send_photo(c.message.chat.id,img,caption=f"💳 PAYMENT DETAILS\nPlan: {p['name']}\nAmount: ₹{p['price']}\nUPI ID: {UPI_ID}\nPayee: {PAYEE_NAME}\n\nScan the QR, verify the payee and amount, then pay. Payment is pending until admin review.",reply_markup=k)
    img.close()

@bot.callback_query_handler(func=lambda c:c.data.startswith("verify:"))
def verify(c):
    try: pid=int(c.data.split(":")[1])
    except: bot.answer_callback_query(c.id,"Invalid plan",show_alert=True); return
    p=plan(pid)
    if not p:return
    with conn() as db:
        cur=db.execute("INSERT INTO orders(user_id,plan_id,amount,status,created_at) VALUES(?,?,?,?,?)",(c.from_user.id,pid,p["price"],"awaiting_screenshot",datetime.now(timezone.utc).isoformat()))
        oid=cur.lastrowid
    waiting[c.from_user.id]=oid
    bot.answer_callback_query(c.id,"Send screenshot as a photo")
    bot.send_message(c.message.chat.id,f"📸 Send your payment screenshot as a photo now.\nOrder: #{oid}\nPlan: {p['name']} · ₹{p['price']}\nUse /cancel to cancel.")

@bot.message_handler(commands=["cancel"])
def cancel(m):
    waiting.pop(m.from_user.id,None); bot.reply_to(m,"Cancelled. Use /start to return to plans.")

@bot.message_handler(content_types=["photo"])
def screenshot(m):
    uid=m.from_user.id; oid=waiting.get(uid)
    if not oid:return
    with conn() as db: order=db.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
    if not order or order["user_id"]!=uid:
        waiting.pop(uid,None); bot.reply_to(m,"Order expired. Use /start."); return
    p=plan(order["plan_id"])
    k=InlineKeyboardMarkup(row_width=2)
    k.row(btn("✅ Approve",f"review:approve:{oid}",style="success"),btn("❌ Reject",f"review:reject:{oid}",style="danger"))
    caption=(f"🧾 PAYMENT REVIEW\n\nUser ID: {uid}\nUsername: @{m.from_user.username or 'not set'}\nPlan: {p['name']}\nAmount: ₹{order['amount']}\nOrder: #{oid}\nStatus: PENDING REVIEW")
    try:
        sent=bot.send_photo(ADMIN_ID,m.photo[-1].file_id,caption=caption,reply_markup=k)
        with conn() as db: db.execute("UPDATE orders SET status='pending_review',admin_message_id=? WHERE id=?",(sent.message_id,oid))
        waiting.pop(uid,None)
        bot.reply_to(m,"✅ Screenshot sent to admin. You’ll be notified after review.")
    except Exception:
        log.exception("Admin notification failed"); bot.reply_to(m,"Submission failed. Please try again.")

@bot.message_handler(content_types=["text","document","video","audio","voice"])
def non_photo(m):
    if m.from_user.id in waiting: bot.reply_to(m,"Please send screenshot as a photo. Use /cancel to cancel.")

@bot.callback_query_handler(func=lambda c:c.data.startswith("review:"))
def review(c):
    if c.from_user.id!=ADMIN_ID:
        bot.answer_callback_query(c.id,"Admin only",show_alert=True); return
    parts=c.data.split(":")
    if len(parts)!=3 or parts[1] not in ("approve","reject"):
        bot.answer_callback_query(c.id,"Invalid action",show_alert=True); return
    action=parts[1]
    try: oid=int(parts[2])
    except: bot.answer_callback_query(c.id,"Invalid order",show_alert=True); return
    with conn() as db:
        order=db.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
        if not order: bot.answer_callback_query(c.id,"Order not found",show_alert=True); return
        if order["status"] in ("verified","rejected"):
            bot.answer_callback_query(c.id,"Already reviewed",show_alert=True); return
        status="verified" if action=="approve" else "rejected"
        db.execute("UPDATE orders SET status=? WHERE id=?",(status,oid))
    p=plan(order["plan_id"]); name=p["name"] if p else f"Plan {order['plan_id']}"
    if action=="approve":
        user_text=f"✅ PAYMENT VERIFIED\n\nPlan: {name}\nAmount: ₹{order['amount']}\nStatus: VERIFIED\nOrder: #{oid}\n\nThank you!"
    else:
        user_text=f"❌ PAYMENT NOT VERIFIED\n\nPlan: {name}\nAmount: ₹{order['amount']}\nStatus: REJECTED\nOrder: #{oid}\nPlease contact support if this is a mistake."
    try: bot.send_message(order["user_id"],user_text)
    except Exception: log.exception("Could not notify user")
    try: bot.edit_message_reply_markup(c.message.chat.id,c.message.message_id,reply_markup=None)
    except Exception: pass
    bot.answer_callback_query(c.id,status.title())
    bot.send_message(ADMIN_ID,f"{status.upper()} · Order #{oid} · user {order['user_id']} · {name} · ₹{order['amount']}")
    # Do not broadcast private payment screenshots or user IDs to all users.

if __name__=="__main__":
    log.info("Bot started")
    bot.infinity_polling(skip_pending=True,timeout=30,long_polling_timeout=30)
