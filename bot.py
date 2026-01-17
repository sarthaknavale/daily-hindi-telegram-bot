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
ADMIN_ID = 12345678  # 👈 REPLACE WITH YOUR TELEGRAM ID
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

def update_streak(user_data):
    """Logic to handle daily learning streaks"""
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    today_str = now.strftime('%Y-%m-%d')
    last_date_str = user_data.get("last_learned", "")
    
    if last_date_str == today_str:
        return user_data # Already updated today
    
    # Check if last update was yesterday
    last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date() if last_date_str else None
    yesterday = (now - timedelta(days=1)).date()
    
    if last_date == yesterday:
        user_data["streak"] = user_data.get("streak", 0) + 1
    else:
        user_data["streak"] = 1 # Reset if they missed a day
        
    user_data["last_learned"] = today_str
    return user_data

# --- CORE LESSON ENGINE ---
async def get_day_data(day):
    if not os.path.exists(FILE_NAME): return None
    try:
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        df.columns = df.columns.str.strip()
        return df[df['Day'] == day].head(5)
    except: return None

async def send_daily_bundle(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user_info = users.get(uid, {"day": 1, "streak": 0})
    day = user_info["day"]
    
    data = await get_day_data(day)
    if data is not None and not data.empty:
        # Update streak for manual learning
        if is_manual:
            users[uid] = update_streak(user_info)
            save_users(users)

        header = f"🔥 <b>STREAK: {users[uid].get('streak', 0)} DAYS</b>\n📖 <b>DAY {day}: 5 SENTENCES</b>"
        msg = f"{header}\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for _, row in data.iterrows():
            eng, h_m, h_f = html.escape(str(row['English Sentence'])), html.escape(str(row['Hindi (Male)'])), html.escape(str(row['Hindi (Female)']))
            note = html.escape(str(row.get('Note', '')))
            msg += f"🇬🇧 <b>{eng}</b>\n👨 {h_m}\n👩 {h_f}\n"
            if note and note.lower() != "nan": msg += f"📝 <i>{note}</i>\n"
            msg += "\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Take Quick Test", callback_data=f"quiz_{day}")],
            [InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]
        ]
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "last_learned": ""}
        save_users(users)
    await u.message.reply_html("🚀 <b>Learning Bot Active!</b>\n\n- /test : Start today's lesson\n- /profile : See your progress")

async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = users.get(str(u.effective_chat.id), {"day": 1, "streak": 0})
    msg = (f"👤 <b>YOUR PROGRESS</b>\n━━━━━━━━━━━━━━━━━━\n"
           f"📅 Current Day: {user['day']}\n"
           f"🔥 Learning Streak: {user['streak']} Days\n"
           f"━━━━━━━━━━━━━━━━━━")
    await u.message.reply_html(msg)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    await query.answer()

    if "next_day" in query.data:
        users = load_users()
        users[uid]["day"] += 1
        # Also update streak when they manually progress
        users[uid] = update_streak(users[uid])
        save_users(users)
        await send_daily_bundle(u.effective_chat.id, c, is_manual=True)

    elif "quiz_" in query.data:
        day = int(query.data.split("_")[1])
        data = await get_day_data(day)
        if data is not None:
            row = data.sample(n=1).iloc[0]
            await query.message.reply_html(f"<b>QUIZ: Translate this!</b>\n\n🇬🇧 <code>{row['English Sentence']}</code>", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👁 Reveal", callback_data=f"reveal_{day}_{row.name}")]]))

    elif "reveal_" in query.data:
        _, day, row_idx = query.data.split("_")
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        row = df.iloc[int(row_idx)]
        await query.message.reply_html(f"✅ <b>Answer:</b>\n\n👨 {row['Hindi (Male)']}\n👩 {row['Hindi (Female)']}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))

async def broadcast(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != ADMIN_ID: return
    text = " ".join(c.args)
    users = load_users()
    for uid in users.keys():
        try:
            await c.bot.send_message(chat_id=int(uid), text=f"📢 <b>ANNOUNCEMENT</b>\n\n{text}", parse_mode="HTML")
            await asyncio.sleep(0.05)
        except: continue

async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in list(users.keys()):
        if await send_daily_bundle(int(uid), c):
            users[uid]["day"] += 1
            # Auto-broadcast does NOT update streak automatically (user must interact)
            save_users(users)
        await asyncio.sleep(0.05)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    IST = pytz.timezone('Asia/Kolkata')
    app_bot.job_queue.run_daily(daily_job, time=dt_time(hour=10, minute=10, tzinfo=IST))
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("profile", profile))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_daily_bundle(u.effective_chat.id, c, True)))
    app_bot.add_handler(CommandHandler("broadcast", broadcast))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.run_polling(drop_pending_updates=True)