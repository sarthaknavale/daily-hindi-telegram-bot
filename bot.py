import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- PORT BINDING FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "RUNNING", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Based on your file upload, it is a CSV but named with .xlsx
# Ensure this matches the exact filename in your GitHub repo
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

async def send_lesson(chat_id, context):
    users = load_users()
    uid = str(chat_id)
    if uid not in users: users[uid] = {"day": 1}
    
    try:
        # PRO FIX: Use read_csv because your file content is CSV format
        df = pd.read_csv(FILE_NAME)
        day = users[uid].get("day", 1)
        row = df[df['Day'] == day]
        
        if not row.empty:
            # Matches your columns: "Hindi (Male)" and "English"
            hindi = html.escape(str(row.iloc[0]['Hindi (Male)']))
            english = html.escape(str(row.iloc[0]['English']))
            
            msg = f"<b>📅 Day {day} Lesson</b>\n\n<b>Hindi:</b> {hindi}\n<b>English:</b> {english}"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False

# --- COMMANDS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("✅ Bot setup complete. 5:10 PM IST schedule active.")

async def test(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_lesson(u.effective_chat.id, c)

async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in users:
        if await send_lesson(int(uid), c):
            users[uid]["day"] += 1
    save_users(users)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    
    # Initialize with the new token from environment variables
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Time: 17:20 IST
    IST = pytz.timezone('Asia/Kolkata')
    target_time = dt_time(hour=17, minute=20, second=0, tzinfo=IST)
    application.job_queue.run_daily(daily_job, time=target_time)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test))

    # CRITICAL: drop_pending_updates=True stops the Conflict Error
    application.run_polling(drop_pending_updates=True)