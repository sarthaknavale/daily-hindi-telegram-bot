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

# ==========================================
#        HIDDEN CONFIGURATIONS (FILL HERE)
# ==========================================
TOKEN = "YOUR_BOT_TOKEN_HERE" 
MY_ID = 12345678  # Your numeric Telegram ID
# ==========================================

FILE_NAME = "lessons.xlsx"
USERS_FILE = "users.json"
IST = pytz.timezone('Asia/Kolkata')

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

def update_streak(user_data):
    now = datetime.now(IST)
    today_str = now.strftime('%Y-%m-%d')
    last_date_str = user_data.get("last_learned", "")
    if last_date_str == today_str: return user_data
    
    last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date() if last_date_str else None
    yesterday = (now - timedelta(days=1)).date()
    
    user_data["streak"] = user_data.get("streak", 0) + 1 if last_date == yesterday else 1
    user_data["last_learned"] = today_str
    return user_data

# --- CORE LOGIC ---
async def get_day_data(day):
    if not os.path.exists(FILE_NAME): return None
    try:
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        df.columns = df.columns.str.strip()
        return df[df['Day'] == day].head(5)
    except: return None

async def send_lesson(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user = users.get(uid, {"day": 1, "streak": 0})
    day = user["day"]

    data = await get_day_data(day)
    if data is not None and not data.empty:
        if is_manual:
            user = update_streak(user)
            users[uid] = user
            save_users(users)

        header = f"🔥 <b>STREAK: {user.get('streak', 0)} DAYS</b>\n📖 <b>DAY {day}</b>"
        msg = f"{header}\n━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in data.iterrows():
            eng = html.escape(str(row['English Sentence']))
            h_m = html.escape(str(row['Hindi (Male)']))
            h_f = html.escape(str(row['Hindi (Female)']))
            msg += f"🇬🇧 <b>{eng}</b>\n👨 {h_m}\n👩 {h_f}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Test", callback_data=f"quiz_{day}")],
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
        users[uid] = {"day": 1, "streak": 0, "last_learned": datetime.now(IST).strftime('%Y-%m-%d'), "time": "10:10", "name": u.effective_user.first_name}
        save_users(users)
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\n\n- /test : Start Lesson\n- /profile : See Streak\n- /leaderboard : Rankings")

async def set_time(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        t_str = c.args[0]
        datetime.strptime(t_str, "%H:%M")
        users = load_users()
        users[str(u.effective_chat.id)]["time"] = t_str
        save_users(users)
        await u.message.reply_text(f"✅ Time set to {t_str} IST!")
    except:
        await u.message.reply_text("❌ Use: /settime 08:30")

async def profile(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = users.get(str(u.effective_chat.id), {"day": 1, "streak": 0})
    await u.message.reply_html(f"👤 <b>PROFILE</b>\nDay: {user['day']}\nStreak: {user['streak']} Days")

async def leaderboard(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1].get('streak', 0), reverse=True)
    msg = "🏆 <b>TOP 10 LEARNERS</b>\n━━━━━━━━━━━━━━━━━━\n"
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        msg += f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else '🔹'} {data.get('name', 'User')} — <b>{data.get('streak', 0)} Days</b>\n"
    await u.message.reply_html(msg)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    await query.answer()

    if "next_day" in query.data:
        users = load_users()
        users[uid]["day"] += 1
        save_users(users)
        await send_lesson(u.effective_chat.id, c, True)
    
    elif "quiz_" in query.data:
        day = int(query.data.split("_")[1])
        data = await get_day_data(day)
        if data is not None:
            row = data.sample(n=1).iloc[0]
            await query.message.reply_html(f"<b>QUIZ</b>\n🇬🇧 <code>{row['English Sentence']}</code>", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👁 Reveal", callback_data=f"reveal_{day}_{row.name}")]]))

    elif "reveal_" in query.data:
        _, day, row_idx = query.data.split("_")
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        row = df.iloc[int(row_idx)]
        await query.message.reply_html(f"✅ <b>Answer:</b>\n👨 {row['Hindi (Male)']}\n👩 {row['Hindi (Female)']}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))

# --- SCHEDULER & REMINDERS ---
async def global_scheduler(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    now = datetime.now(IST)
    now_time = now.strftime("%H:%M")
    today_date = now.date()

    for uid, data in users.items():
        # 1. SEND DAILY LESSON
        if data.get("time", "10:10") == now_time:
            if await send_lesson(int(uid), context):
                data["day"] += 1
        
        # 2. SEND INACTIVE REMINDER (Check once a day at 6:00 PM)
        if now_time == "18:00":
            last_learned_str = data.get("last_learned", "")
            if last_learned_str:
                last_learned_date = datetime.strptime(last_learned_str, '%Y-%m-%d').date()
                days_inactive = (today_date - last_learned_date).days
                if days_inactive >= 2:
                    try:
                        await context.bot.send_message(chat_id=int(uid), 
                            text="⚠️ <b>Don't lose your streak!</b>\nYou haven't practiced in 2 days. Click /test to continue learning! 🔥", 
                            parse_mode="HTML")
                    except: pass
    save_users(users)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.job_queue.run_repeating(global_scheduler, interval=60, first=10)
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("settime", set_time))
    app_bot.add_handler(CommandHandler("profile", profile))
    app_bot.add_handler(CommandHandler("leaderboard", leaderboard))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_lesson(u.effective_chat.id, c, True)))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    
    app_bot.run_polling()