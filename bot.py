import json, asyncio, os, html, pytz, random
import pandas as pd
from datetime import time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "BOT_ONLINE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 12345678  # 👈 REPLACE WITH YOUR TELEGRAM ID (Find it via @userinfobot)
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- CORE LESSON ENGINE ---
async def get_day_data(day):
    if not os.path.exists(FILE_NAME): return None
    try:
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        df.columns = df.columns.str.strip()
        day_rows = df[df['Day'] == day].head(5)
        return day_rows if not day_rows.empty else None
    except Exception as e:
        print(f"Excel Error: {e}")
        return None

async def send_daily_bundle(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    day = users.get(uid, {}).get("day", 1)
    
    data = await get_day_data(day)
    if data is not None:
        header = f"📖 <b>DAY {day}: TODAY'S 5 SENTENCES</b>"
        msg = f"{header}\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for _, row in data.iterrows():
            eng = html.escape(str(row['English Sentence']))
            h_m = html.escape(str(row['Hindi (Male)']))
            h_f = html.escape(str(row['Hindi (Female)']))
            note = html.escape(str(row.get('Note', '')))
            
            msg += f"🇬🇧 <b>{eng}</b>\n👨 {h_m}\n👩 {h_f}\n"
            if note and note.lower() != "nan": msg += f"📝 <i>{note}</i>\n"
            msg += "\n"
        
        msg += "━━━━━━━━━━━━━━━━━━"
        
        keyboard = [
            [InlineKeyboardButton("📝 Take Quick Test", callback_data=f"quiz_{day}")],
            [InlineKeyboardButton("⏭️ Skip to Next Day", callback_data="next_day")]
        ]
        
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    else:
        if is_manual:
            await context.bot.send_message(chat_id=chat_id, text="✨ No more lessons available in the sheet!")
        return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1}
        save_users(users)
    await u.message.reply_html("🚀 <b>Bot Active!</b>\n\n- 5 Sentences daily @ 10:10 AM\n- /test for current lesson\n- Use buttons to progress faster.")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_daily_bundle(u.effective_chat.id, c, is_manual=True)

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Admin only: /broadcast Your Message Here"""
    if u.effective_user.id != ADMIN_ID: return
    
    text = " ".join(c.args)
    if not text:
        await u.message.reply_text("Please provide a message. Example: /broadcast Hello everyone!")
        return

    users = load_users()
    count = 0
    for uid in users.keys():
        try:
            await c.bot.send_message(chat_id=int(uid), text=f"📢 <b>ANNOUNCEMENT</b>\n\n{text}", parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await u.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    data_parts = query.data.split("_")
    
    await query.answer()

    if "next_day" in query.data:
        users = load_users()
        users[uid]["day"] = users.get(uid, {}).get("day", 1) + 1
        save_users(users)
        await query.message.reply_text(f"✅ Level up! You are now on Day {users[uid]['day']}.")
        await send_daily_bundle(u.effective_chat.id, c, is_manual=True)

    elif data_parts[0] == "quiz":
        day = int(data_parts[1])
        data = await get_day_data(day)
        if data is not None:
            random_row = data.sample(n=1).iloc[0]
            question = random_row['English Sentence']
            keyboard = [[InlineKeyboardButton("👁 Reveal Answer", callback_data=f"reveal_{day}_{random_row.name}")]]
            await query.message.reply_html(f"<b>QUIZ: Translate this!</b>\n\n🇬🇧 <code>{question}</code>", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data_parts[0] == "reveal":
        day = int(data_parts[1])
        row_idx = int(data_parts[2])
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        row = df.iloc[row_idx]
        ans = f"✅ <b>Answer:</b>\n\n👨 {row['Hindi (Male)']}\n👩 {row['Hindi (Female)']}"
        await query.message.reply_html(ans, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))

# --- BROADCAST ENGINE ---
async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in list(users.keys()):
        success = await send_daily_bundle(int(uid), c)
        if success:
            users[uid]["day"] += 1
            save_users(users)
        await asyncio.sleep(0.05)

if __name__ == "__main__":
    if not BOT_TOKEN: exit(1)
    Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    IST = pytz.timezone('Asia/Kolkata')
    application.job_queue.run_daily(daily_job, time=dt_time(hour=10, minute=10, tzinfo=IST))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(callback_handler))

    application.run_polling(drop_pending_updates=True)