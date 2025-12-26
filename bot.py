import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- RENDER PORT BINDING (Flask) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is live!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Python 3.14 Event Loop Fix ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LESSON_FILE = "lessons.xlsx"
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# --- CORE LESSON SENDER ---
async def send_lesson_to_user(chat_id, context):
    users = load_users()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in users:
        users[chat_id_str] = {"day": 1, "paused": False}
    
    try:
        df = pd.read_excel(LESSON_FILE)
        day = users[chat_id_str].get("day", 1)
        day_data = df[df['Day'] == day]
        
        if not day_data.empty:
            row = day_data.iloc[0]
            h = html.escape(str(row['Hindi']))
            e = html.escape(str(row['English']))
            msg = f"<b>📅 Day {day} Lesson</b>\n\n<b>Hindi:</b> {h}\n<b>English:</b> {e}"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users[str(update.effective_chat.id)] = {"day": 1, "paused": False}
    save_users(users)
    await update.message.reply_text("✅ Bot Started! You will get lessons daily at 5:10 PM IST.\n\nUse /test to see a lesson now!")

async def test_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Sending test lesson...")
    success = await send_lesson_to_user(update.effective_chat.id, context)
    if not success:
        await update.message.reply_text("❌ Error: Could not read Excel file.")

# --- AUTOMATED DAILY JOB ---
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for chat_id in users:
        if not users[chat_id].get("paused", False):
            await send_lesson_to_user(int(chat_id), context)
            users[chat_id]["day"] += 1
    save_users(users)

# --- MAIN ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ CRITICAL ERROR: BOT_TOKEN is missing in Render Environment Variables!")
    else:
        # Start Web Server thread
        Thread(target=run_flask, daemon=True).start()

        # Build App
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        # Set Schedule: 5:10 PM IST
        IST = pytz.timezone('Asia/Kolkata')
        target_time = dt_time(hour=17, minute=55, second=0, tzinfo=IST)

        application.job_queue.run_daily(
            daily_job, 
            time=target_time, 
            days=(0, 1, 2, 3, 4, 5, 6)
        )

        # Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("test", test_now))

        print("🤖 Bot is live. Waiting for 5:55 PM IST...")
        # drop_pending_updates kills the Conflict error
        application.run_polling(drop_pending_updates=True)