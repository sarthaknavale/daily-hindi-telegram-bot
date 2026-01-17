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
TOKEN = "8450562900:AAFMHSXkewWDqzpbxmCLKZokbL-2JlqNsoA" 
MY_ID = 753500208  # Your numeric Telegram ID
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
    
    data = await get_day_data(user["day"])
    if data is not None and not data.empty:
        # Update streak if they manually practiced
        if is_manual:
            now = datetime.now(IST)
            today_str = now.strftime('%Y-%m-%d')
            last_date_str = user.get("last_learned", "")
            if last_date_str != today_str:
                last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date() if last_date_str else None
                yesterday = (now - timedelta(days=1)).date()
                user["streak"] = user.get("streak", 0) + 1 if last_date == yesterday else 1
                user["last_learned"] = today_str
                users[uid] = user
                save_users(users)

        msg = f"🔥 <b>STREAK: {user.get('streak', 0)} DAYS</b>\n📖 <b>DAY {user['day']}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for _, row in data.iterrows():
            msg += f"🇬🇧 <b>{html.escape(str(row['English Sentence']))}</b>\n👨 {html.escape(str(row['Hindi (Male)']))}\n👩 {html.escape(str(row['Hindi (Female)']))}\n\n"
        
        btns = [[InlineKeyboardButton("📝 Test", callback_data=f"quiz_{user['day']}")], [InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
        return True
    return False

# --- SYSTEM HEALTH CHECK (ADMIN ONLY) ---
async def status(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.effective_user.id != MY_ID: return
    
    users = load_users()
    excel_ok = os.path.exists(FILE_NAME)
    
    status_msg = "🖥 <b>SYSTEM HEALTH CHECK</b>\n━━━━━━━━━━━━━━━━━━\n"
    status_msg += f"✅ <b>Bot Token:</b> Valid\n"
    status_msg += f"{'✅' if excel_ok else '❌'} <b>Excel File:</b> {'Found' if excel_ok else 'NOT FOUND'}\n"
    status_msg += f"👥 <b>Total Users:</b> {len(users)}\n"
    status_msg += f"⏰ <b>Server Time:</b> {datetime.now(IST).strftime('%H:%M:%S')}\n"
    
    if excel_ok:
        try:
            df = pd.read_excel(FILE_NAME)
            status_msg += f"📊 <b>Total Days in Excel:</b> {df['Day'].max()}\n"
        except: status_msg += "⚠️ <b>Excel Error:</b> Cannot read rows.\n"
        
    await u.message.reply_html(status_msg)

# --- STANDARD HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "last_learned": "", "time": "10:10", "name": u.effective_user.first_name}
        save_users(users)
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\n/test - Start\n/profile - Progress")

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
        df = pd.read_excel(FILE_NAME)
        row = df.iloc[int(row_idx)]
        await query.message.reply_html(f"✅ <b>Answer</b>\n👨 {row['Hindi (Male)']}\n👩 {row['Hindi (Female)']}", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))

# --- SCHEDULER ---
async def global_scheduler(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    now_time = datetime.now(IST).strftime("%H:%M")
    for uid, data in users.items():
        if data.get("time", "10:10") == now_time:
            if await send_lesson(int(uid), context):
                data["day"] += 1
    save_users(users)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.job_queue.run_repeating(global_scheduler, interval=60, first=10)
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_lesson(u.effective_chat.id, c, True)))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    
    app_bot.run_polling()