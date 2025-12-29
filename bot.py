import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- RENDER WEB SERVER (Prevents Port Errors) ---
app = Flask('')
@app.route('/')
def home(): return "BOT_ONLINE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- CORE LESSON ENGINE ---
async def send_daily_bundle(chat_id, context):
    users = load_users()
    uid = str(chat_id)
    day = users.get(uid, {}).get("day", 1)
    
    if not os.path.exists(FILE_NAME):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {FILE_NAME} not found on server.")
        return False

    try:
        # PRO AUTO-DETECT: Try Excel, then CSV
        try:
            df = pd.read_excel(FILE_NAME)
        except:
            df = pd.read_csv(FILE_NAME)

        # Clean Column Names (Removes hidden spaces)
        df.columns = df.columns.str.strip()

        # Get all rows for the day
        day_rows = df[df['Day'] == day]
        
        if not day_rows.empty:
            msg = f"<b>📅 LESSON: DAY {day}</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━\n\n"
            
            for _, row in day_rows.iterrows():
                eng = html.escape(str(row['English']))
                h_m = html.escape(str(row['Hindi (Male)']))
                h_f = html.escape(str(row['Hindi (Female)']))
                
                msg += f"🇬🇧 <b>{eng}</b>\n"
                msg += f"👨 {h_m}\n"
                msg += f"👩 {h_f}\n\n"
            
            msg += "━━━━━━━━━━━━━━━━━━"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            return True
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ No lessons found for Day {day}")
    except Exception as e:
        print(f"Read Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ File Error: {str(e)}")
    return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users[str(u.effective_chat.id)] = {"day": 1}
    save_users(users)
    await u.message.reply_text("🚀 <b>Bot Active!</b>\nDaily lessons at 10:00 AM IST.\nUse /test to see today's 2 sentences.")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_daily_bundle(u.effective_chat.id, c)

async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in users:
        if await send_daily_bundle(int(uid), c):
            users[uid]["day"] += 1
    save_users(users)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("FATAL: BOT_TOKEN missing!")
        exit(1)

    Thread(target=run_flask, daemon=True).start()
    
    # Enable Job Queue for scheduling
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Time: 11:00 (11:00 AM) IST
    IST = pytz.timezone('Asia/Kolkata')
    target_time = dt_time(hour=11, minute=0, second=0, tzinfo=IST)
    application.job_queue.run_daily(daily_job, time=target_time)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_cmd))

    print("🤖 PRO Bot is starting...")
    # drop_pending_updates=True is the ULTIMATE fix for Conflict Errors
    application.run_polling(drop_pending_updates=True)