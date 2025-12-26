import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- RENDER PORT BINDING ---
app = Flask('')
@app.route('/')
def home(): return "STABLE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Python 3.14 Fix ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# PRO TIP: The file name in your repo might be 'lessons.xlsx' or 'lessons.csv'
LESSON_FILE = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- IMPROVED EXCEL/CSV READER ---
async def fetch_and_send(chat_id, context):
    users = load_users()
    uid = str(chat_id)
    if uid not in users: users[uid] = {"day": 1}
    
    # Check for file existence
    if not os.path.exists(LESSON_FILE):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {LESSON_FILE} not found!")
        return False
    
    try:
        # PRO FIX: Automatically detect if it's CSV or XLSX
        if LESSON_FILE.endswith('.csv'):
            df = pd.read_csv(LESSON_FILE)
        else:
            df = pd.read_excel(LESSON_FILE)

        day = users[uid].get("day", 1)
        # Filters by 'Day' column
        row = df[df['Day'] == day]
        
        if not row.empty:
            # Using your specific column names: 'Hindi (Male)' and 'English'
            h = html.escape(str(row.iloc[0]['Hindi (Male)']))
            e = html.escape(str(row.iloc[0]['English']))
            
            text = f"<b>📖 Day {day} Lesson</b>\n\n<b>Hindi:</b> {h}\n<b>English:</b> {e}"
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            return True
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ No lesson found for Day {day}")
    except Exception as err:
        print(f"File Read Error: {err}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error reading file: {str(err)}")
    return False

# --- COMMANDS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🚀 **PRO Bot Active.**\nDaily: 6:10 PM IST.\nUse /test to check now.")

async def test(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await fetch_and_send(u.effective_chat.id, c)

async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in users:
        success = await fetch_and_send(int(uid), c)
        if success: users[uid]["day"] += 1
    save_users(users)

if __name__ == "__main__":
    if not BOT_TOKEN: exit(1)

    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    # Schedule for 6:10 PM IST
    IST = pytz.timezone('Asia/Kolkata')
    t = dt_time(hour=18, minute=10, second=0, tzinfo=IST)
    app_bot.job_queue.run_daily(daily_job, time=t, days=(0,1,2,3,4,5,6))

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("test", test))

    # Conflict Killer
    app_bot.run_polling(drop_pending_updates=True)