import json, asyncio, os, html, pytz, random
import pandas as pd
from datetime import time as dt_time, datetime, timedelta
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
ADMIN_ID = 12345678  # 👈 REPLACE WITH YOUR ID
USERS_FILE = "users.json"
FILE_NAME = "lessons.xlsx"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- CORE LOGIC ---
async def get_day_data(day):
    if not os.path.exists(FILE_NAME): return None
    try:
        df = pd.read_excel(FILE_NAME)
        df.columns = df.columns.str.strip()
        return df[df['Day'] == day].head(5)
    except: return None

async def send_lesson(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user = users.get(uid, {"day": 1, "lang": "Hindi", "streak": 0})
    lang = user.get("lang", "Hindi")
    day = user["day"]

    data = await get_day_data(day)
    if data is not None and not data.empty:
        msg = f"🌍 <b>LANGUAGE: {lang}</b> | 🔥 <b>STREAK: {user.get('streak', 0)}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in data.iterrows():
            eng = html.escape(str(row['English Sentence']))
            male = html.escape(str(row.get(f'{lang} (Male)', 'N/A')))
            female = html.escape(str(row.get(f'{lang} (Female)', 'N/A')))
            msg += f"🇬🇧 {eng}\n👨 {male}\n👩 {female}\n\n"
        
        keyboard = [[InlineKeyboardButton("📝 Test", callback_data=f"quiz_{day}")], [InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    return False

# --- HANDLERS ---
async def set_time(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Usage: /settime 08:30"""
    try:
        t_str = c.args[0]
        datetime.strptime(t_str, "%H:%M") # Validate format
        users = load_users()
        users[str(u.effective_chat.id)]["time"] = t_str
        save_users(users)
        await u.message.reply_text(f"⏰ Daily lesson time set to {t_str} IST!")
    except:
        await u.message.reply_text("❌ Use format: /settime HH:MM (e.g., /settime 09:15)")

async def language_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Hindi", callback_data="setlang_Hindi"), 
         InlineKeyboardButton("Spanish", callback_data="setlang_Spanish")]
    ]
    await u.message.reply_text("🌐 Choose your target language:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    await query.answer()

    if "setlang_" in query.data:
        lang = query.data.split("_")[1]
        users = load_users()
        users[uid]["lang"] = lang
        save_users(users)
        await query.edit_message_text(f"✅ Language set to {lang}!")
    
    elif "next_day" in query.data:
        users = load_users()
        users[uid]["day"] += 1
        save_users(users)
        await send_lesson(u.effective_chat.id, c, True)

# --- PER-USER SCHEDULER ---
async def check_and_send(context: ContextTypes.DEFAULT_TYPE):
    """Runs every minute to see who needs a message now"""
    users = load_users()
    now_ist = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M")
    
    for uid, data in users.items():
        user_time = data.get("time", "10:10") # Default
        if now_ist == user_time:
            await send_lesson(int(uid), context)
            data["day"] += 1
    save_users(users)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Check every minute for custom times
    app_bot.job_queue.run_repeating(check_and_send, interval=60, first=10)

    app_bot.add_handler(CommandHandler("start", start)) # reuse previous start
    app_bot.add_handler(CommandHandler("settime", set_time))
    app_bot.add_handler(CommandHandler("language", language_cmd))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    
    app_bot.run_polling()