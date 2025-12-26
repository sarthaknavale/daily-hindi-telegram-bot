import json, asyncio, os, html, pytz
import pandas as pd
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- PRO STEP 1: RENDER PORT BINDING ---
app = Flask('')
@app.route('/')
def home(): return "BOT_READY", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Your file is CSV content inside an .xlsx extension
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- MULTI-ROW LESSON SENDER ---
async def send_lesson(chat_id, context):
    users = load_users()
    uid = str(chat_id)
    if uid not in users: users[uid] = {"day": 1}
    
    try:
        # Read file as CSV (since content is CSV)
        df = pd.read_csv(FILE_NAME)
        day = users[uid].get("day", 1)
        
        # PRO FIX: Get ALL rows for that day
        rows = df[df['Day'] == day]
        
        if not rows.empty:
            full_msg = f"<b>📅 Day {day} Lessons</b>\n"
            full_msg += "━━━━━━━━━━━━━━━\n\n"
            
            for _, row in rows.iterrows():
                h_m = html.escape(str(row['Hindi (Male)']))
                h_f = html.escape(str(row['Hindi (Female)']))
                eng = html.escape(str(row['English']))
                topic = html.escape(str(row['Topic']))
                
                full_msg += f"<b>Topic: {topic}</b>\n"
                full_msg += f"🇬🇧 <b>Eng:</b> {eng}\n"
                full_msg += f"👨 <b>Hin (M):</b> {h_m}\n"
                full_msg += f"👩 <b>Hin (F):</b> {h_f}\n\n"
            
            await context.bot.send_message(chat_id=chat_id, text=full_msg, parse_mode="HTML")
            return True
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ No lessons found for Day {day}")
    except Exception as e:
        print(f"File Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ Error reading lesson file.")
    return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users[str(u.effective_chat.id)] = {"day": 1}
    save_users(users)
    await u.message.reply_text("🚀 **PRO Bot Active.**\n\nLessons will be sent daily at 5:10 PM IST.\nUse /test to see today's lesson!")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_lesson(u.effective_chat.id, c)

async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in users:
        # Send lessons and only increment day if successful
        if await send_lesson(int(uid), c):
            users[uid]["day"] += 1
    save_users(users)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found!")
        exit(1)

    # Start Health Check Server for Render
    Thread(target=run_flask, daemon=True).start()
    
    # Initialize Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Schedule: 17:45 (6:45 PM) IST
    IST = pytz.timezone('Asia/Kolkata')
    target_time = dt_time(hour=17, minute=45, second=0, tzinfo=IST)
    application.job_queue.run_daily(daily_job, time=target_time, days=(0,1,2,3,4,5,6))

    # Add Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_cmd))

    # PRO Conflict Fix: drop_pending_updates=True
    print("🤖 Bot is starting...")
    application.run_polling(drop_pending_updates=True)