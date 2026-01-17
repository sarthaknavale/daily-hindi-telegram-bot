import json, asyncio, os, html, pytz
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
    prompt = (f"English teacher. Day {day} lesson. 5 sentences. "
              "Return ONLY JSON: {'grammar': 'tip', 'sentences': [{'eng': '..', 'say': '..', 'male': '..', 'female': '..'}]}")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except: return None

# --- UI DELIVERY ---
async def send_lesson_ui(chat_id, context, data, day, streak, is_review=False):
    tag = "⏮️ <b>REVIEW: DAY " if is_review else "📖 <b>DAY "
    msg = f"🔥 <b>STREAK: {streak} DAYS</b>\n{tag}{day}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, item in enumerate(data.get('sentences', [])):
        msg += f"{i+1}. 🇬🇧 <b>{item['eng']}</b>\n🗣️ <i>{item['say']}</i>\n👨 {item['male']}\n👩 {item['female']}\n\n"

    msg += f"💡 <b>Grammar:</b> {data.get('grammar', 'Keep practicing!')}"
    
    btns = [
        [InlineKeyboardButton(f"🔖 Save {i+1}", callback_data=f"save_{i}") for i in range(5)],
        [InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")],
        [InlineKeyboardButton("⏮️ Review Yesterday", callback_data="review_prev")]
    ]
    if is_review:
        btns = [[InlineKeyboardButton("🔙 Back to Today", callback_data="back_today")]]

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

# --- COMMANDS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    users = load_users()
    
    # Always send a welcome message immediately
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\nPreparing your AI lessons...")

    if uid not in users or not users[uid].get("current_lesson"):
        curr = await fetch_ai_lesson(1)
        users[uid] = {
            "day": 1, "streak": 0, "last_learned": "", "vocab": [],
            "current_lesson": curr, "next_lesson": None, "prev_lesson": None,
            "name": u.effective_user.first_name
        }
        save_users(users)
    
    await u.message.reply_html("✅ <b>Ready!</b>\nUse /test for your lesson.\nUse /vocabulary for saved sentences.")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    users = load_users()
    user = users.get(uid)
    
    if not user or not user.get("current_lesson"):
        await u.message.reply_text("❌ Data not found. Please type /start first.")
        return

    # Update streak
    now = datetime.now(IST).strftime('%Y-%m-%d')
    if user.get("last_learned") != now:
        user["streak"] = user.get("streak", 0) + 1
        user["last_learned"] = now
        save_users(users)

    await send_lesson_ui(u.effective_chat.id, c, user["current_lesson"], user["day"], user["streak"])

async def vocab_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = users.get(str(u.effective_chat.id), {})
    vocab = user.get("vocab", [])
    
    if not vocab:
        await u.message.reply_text("🔖 Your vocabulary list is empty. Use the Save buttons in a lesson!")
        return
    
    msg = "📂 <b>MY VOCABULARY (Last 10)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for item in vocab[-10:]:
        msg += f"• 🇬🇧 {item['eng']}\n  🇮🇳 {item['hin']}\n\n"
    await u.message.reply_html(msg)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    uid = str(u.effective_chat.id)
    users = load_users()
    user = users.get(uid)
    await query.answer()

    if "save_" in query.data:
        idx = int(query.data.split("_")[1])
        sentence = user["current_lesson"]["sentences"][idx]
        entry = {"eng": sentence["eng"], "hin": sentence["male"]}
        if entry not in user["vocab"]:
            user["vocab"].append(entry)
            save_users(users)
            await c.bot.send_message(chat_id=uid, text=f"✅ Saved to /vocabulary: {entry['eng']}")

    elif query.data == "next_day":
        user["prev_lesson"] = user["current_lesson"]
        user["day"] += 1
        save_users(users)
        
        # Pre-fetch and send
        new_lesson = await fetch_ai_lesson(user["day"])
        user["current_lesson"] = new_lesson
        save_users(users)
        await send_lesson_ui(uid, c, user["current_lesson"], user["day"], user["streak"])

    elif query.data == "review_prev":
        if user.get("prev_lesson"):
            await send_lesson_ui(uid, c, user["prev_lesson"], user["day"]-1, user["streak"], True)
        else:
            await c.bot.send_message(chat_id=uid, text="No previous lesson to show!")

    elif query.data == "back_today":
        await send_lesson_ui(uid, c, user["current_lesson"], user["day"], user["streak"])

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("test", test_cmd))
    app_bot.add_handler(CommandHandler("vocabulary", vocab_cmd))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    
    print("Bot is polling...")
    app_bot.run_polling(drop_pending_updates=True)