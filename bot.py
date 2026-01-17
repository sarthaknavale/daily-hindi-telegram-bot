import json, asyncio, os, html, pytz, time
import google.generativeai as genai
from datetime import datetime
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
GEMINI_API_KEY = "AIzaSyD6qw18ecUshcqPRNFWWTTliFEmdVHd7ZQ"
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
USERS_FILE = "users.json"
IST = pytz.timezone('Asia/Kolkata')

def load_users():
    if not os.path.exists(USERS_FILE): return {}
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- AI ENGINE ---
async def fetch_ai_lesson(day):
    prompt = (f"Act as an English teacher. Create a beginner lesson for Day {day}. "
              "Provide 5 sentences with English, Phonetic pronunciation, Hindi Male, and Hindi Female. "
              "Return ONLY a JSON object: "
              '{"grammar": "tip", "sentences": [{"eng": "Sentence", "say": "pronunciation", "male": "Hindi", "female": "Hindi"}]}')
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except:
        return None

# --- UI DELIVERY ---
async def send_lesson_ui(chat_id, context, data, day, streak):
    msg = f"🔥 <b>STREAK: {streak} DAYS</b>\n📖 <b>DAY {day}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, item in enumerate(data.get('sentences', [])):
        msg += f"{i+1}. 🇬🇧 <b>{item['eng']}</b>\n🗣️ <i>{item['say']}</i>\n👨 {item['male']}\n👩 {item['female']}\n\n"
    msg += f"💡 <b>Grammar:</b> {data.get('grammar', 'Keep practicing!')}"
    
    btns = [[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

# --- COMMANDS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    users = load_users()
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\nType /test to start.")
    
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "last_learned": "", "current_lesson": None}
        save_users(users)

async def status_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Admin tool to check bot health"""
    start_time = time.time()
    ai_check = await fetch_ai_lesson(0) # Test ping
    latency = round(time.time() - start_time, 2)
    
    status = (
        "🖥 <b>SYSTEM STATUS</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>AI Connection:</b> {'✅ Online' if ai_check else '❌ Offline'}\n"
        f"⚡ <b>AI Latency:</b> {latency}s\n"
        f"📁 <b>Database:</b> {'✅ Ready' if os.path.exists(USERS_FILE) else '⚠️ Empty'}\n"
        f"⏰ <b>Server Time:</b> {datetime.now(IST).strftime('%H:%M:%S')}"
    )
    await u.message.reply_html(status)

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    users = load_users()
    user = users.get(uid, {"day": 1, "streak": 0, "last_learned": "", "current_lesson": None})

    # AUTO-REPAIR
    if not user.get("current_lesson"):
        wait = await u.message.reply_text("🛠 <b>Generating initial data...</b>", parse_mode="HTML")
        user["current_lesson"] = await fetch_ai_lesson(user['day'])
        users[uid] = user
        save_users(users)
        await c.bot.delete_message(chat_id=uid, message_id=wait.message_id)

    if user["current_lesson"]:
        await send_lesson_ui(uid, c, user["current_lesson"], user["day"], user["streak"])
    else:
        await u.message.reply_text("❌ AI is busy. Try /test again in 10 seconds.")

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    users = load_users()
    user = users.get(uid)
    await query.answer()

    if query.data == "next_day":
        user["day"] += 1
        wait = await c.bot.send_message(chat_id=uid, text="⏳ <i>Loading Day " + str(user['day']) + "...</i>", parse_mode="HTML")
        user["current_lesson"] = await fetch_ai_lesson(user["day"])
        save_users(users)
        await c.bot.delete_message(chat_id=uid, message_id=wait.message_id)
        await send_lesson_ui(uid, c, user["current_lesson"], user["day"], user["streak"])

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("status", status_cmd))
    app_bot.add_handler(CommandHandler("test", test_cmd))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.run_polling(drop_pending_updates=True)