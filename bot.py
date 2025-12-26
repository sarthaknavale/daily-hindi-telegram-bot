import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Python 3.14 Event Loop Compatibility Fix ---
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ"
LESSON_FILE = "lessons.xlsx"
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ---------------- DAILY LESSON JOB ----------------
async def send_daily_lesson(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    try:
        df = pd.read_excel(LESSON_FILE)
    except Exception as e:
        print(f"Excel Error: {e}")
        return

    for chat_id, data in users.items():
        if not data.get("paused", False):
            day = data.get("day", 1)
            day_data = df[df['Day'] == day]
            
            if not day_data.empty:
                row = day_data.iloc[0]
                # Secure formatting for Telegram HTML mode
                h = html.escape(str(row['Hindi']))
                e = html.escape(str(row['English']))
                msg = f"<b>📅 Day {day} Lesson</b>\n\n<b>Hindi:</b> {h}\n<b>English:</b> {e}"
                
                try:
                    await context.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode="HTML")
                    users[chat_id]["day"] += 1
                except Exception as err:
                    print(f"Send Error ({chat_id}): {err}")
    
    save_users(users)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Create Application with JobQueue enabled
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Define 5:00 PM (17:00) in India Standard Time
    IST = pytz.timezone('Asia/Kolkata')
    target_time = dt_time(hour=17, minute=0, second=0, tzinfo=IST)

    # Schedule the daily job to run every day at 5:00 PM IST
    application.job_queue.run_daily(send_daily_lesson, time=target_time)

    # Handlers
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Namaste! Lessons scheduled daily at 5:00 PM IST.")))
    
    print("🤖 Bot Active. Next lesson scheduled for 5:00 PM IST.")
    application.run_polling()