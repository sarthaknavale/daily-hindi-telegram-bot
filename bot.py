import json, asyncio, os, html, pytz, random
import pandas as pd
from datetime import time as dt_time
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
FILE_NAME = "lessons.xlsx" 
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- CORE LESSON ENGINE ---
async def get_day_data(day):
    if not os.path.exists(FILE_NAME): return None
    try:
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        df.columns = df.columns.str.strip()
        day_rows = df[df['Day'] == day].head(5)
        return day_rows if not day_rows.empty else None
    except Exception as e:
        print(f"Excel Error: {e}")
        return None

async def send_daily_bundle(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    day = users.get(uid, {}).get("day", 1)
    
    data = await get_day_data(day)
    if data is not None:
        header = f"📖 <b>DAY {day}: TODAY'S 5 SENTENCES</b>"
        msg = f"{header}\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for _, row in data.iterrows():
            eng = html.escape(str(row['English Sentence']))
            h_m = html.escape(str(row['Hindi (Male)']))
            h_f = html.escape(str(row['Hindi (Female)']))
            note = html.escape(str(row.get('Note', '')))
            
            msg += f"🇬🇧 <b>{eng}</b>\n👨 {h_m}\n👩 {h_f}\n"
            if note and note.lower() != "nan": msg += f"📝 <i>{note}</i>\n"
            msg += "\n"
        
        msg += "━━━━━━━━━━━━━━━━━━"
        
        # NAVIGATION BUTTONS
        keyboard = [
            [InlineKeyboardButton("📝 Take Quick Test", callback_data=f"quiz_{day}")],
            [InlineKeyboardButton("⏭️ Skip to Next Day", callback_data="next_day")]
        ]
        
        await context.bot.send_message(
            chat_id=chat_id, 
            text=msg, 
            parse_mode="HTML", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return True
    else:
        if is_manual:
            await context.bot.send_message(chat_id=chat_id, text="✨ You have completed all available lessons!")
        return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1}
        save_users(users)
    await u.message.reply_html("🚀 <b>Learning Bot Active!</b>\n\n- Daily 5 sentences at 10:10 AM.\n- Use /test to practice now.\n- Use the buttons to move faster!")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_daily_bundle(u.effective_chat.id, c, is_manual=True)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    data_parts = query.data.split("_")
    action = data_parts[0]
    
    await query.answer()

    if action == "next": # Next Day logic
        users = load_users()
        users[uid]["day"] = users.get(uid, {}).get("day", 1) + 1
        save_users(users)
        await query.message.reply_text(f"✅ Progressed to Day {users[uid]['day']}!")
        await send_daily_bundle(u.effective_chat.id, c, is_manual=True)

    elif action == "quiz":
        day = int(data_parts[1])
        data = await get_day_data(day)
        if data is not None:
            random_row = data.sample(n=1).iloc[0]
            question = random_row['English Sentence']
            # Store the index in callback to reveal later
            keyboard = [[InlineKeyboardButton("👁 Reveal Answer", callback_data=f"reveal_{day}_{random_row.name}")]]
            await query.message.reply_html(f"<b>QUIZ: Translate this!</b>\n\n🇬🇧 <code>{question}</code>", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "reveal":
        day = int(data_parts[1])
        row_idx = int(data_parts[2])
        # Re-read to get correct row
        df = pd.read_excel(FILE_NAME) if FILE_NAME.endswith('.xlsx') else pd.read_csv(FILE_NAME)
        row = df.iloc[row_idx]
        
        ans_msg = f"✅ <b>Answer:</b>\n\n👨 {row['Hindi (Male)']}\n👩 {row['Hindi (Female)']}\n\n<i>Ready for tomorrow?</i>"
        keyboard = [[InlineKeyboardButton("⏭️ Start Next Day Now", callback_data="next_day")]]
        await query.message.reply_html(ans_msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- BROADCAST ENGINE ---
async def daily_job(c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    for uid in list(users.keys()):
        success = await send_daily_bundle(int(uid), c)
        if success:
            users[uid]["day"] += 1
            save_users(users)
        await asyncio.sleep(0.05) 

if __name__ == "__main__":
    if not BOT_TOKEN: exit(1)
    Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    IST = pytz.timezone('Asia/Kolkata')
    application.job_queue.run_daily(daily_job, time=dt_time(hour=10, minute=10, tzinfo=IST))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_cmd))
    application.add_handler(CallbackQueryHandler(callback_handler))

    application.run_polling(drop_pending_updates=True)