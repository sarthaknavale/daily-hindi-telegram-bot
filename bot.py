import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- RENDER PORT BINDING FIX ---
# Render expects a web server to listen on a port. We use Flask for this.
app = Flask('')

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    # Render automatically assigns a PORT; defaults to 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Python 3.14 Event Loop Compatibility ---
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ---------------- CONFIG ----------------
# Use Environment Variable for security to avoid GitHub Push Protection blocks
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_FALLBACK_TOKEN_HERE")
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
    # Start the Flask web server in a background thread
    Thread(target=run_flask, daemon=True).start()

    # Create Telegram Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Define 5:10 PM (17:10) in India Standard Time
    IST = pytz.timezone('Asia/Kolkata')
    # Change: hour=17, minute=10
    target_time = dt_time(hour=17, minute=10, second=0, tzinfo=IST)

    # Schedule the daily job (days 0-6 = Every day)
    application.job_queue.run_daily(
        send_daily_lesson, 
        time=target_time,
        days=(0, 1, 2, 3, 4, 5, 6)
    )

    # Handlers
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Bot Active! Lessons at 5:10 PM IST.")))
    
    print("🤖 Bot Active. Flask listening on Port. Lessons at 5:10 PM IST.")
    application.run_polling()