import json, asyncio, os, html, pytz
import google.generativeai as genai
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from flask import Flask
from threading import Thread
from gtts import gTTS

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
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- INSTANT AI ENGINE ---
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
    except: return None

# --- UI DELIVERY ---
async def send_lesson_ui(chat_id, context, data, day, streak, is_review=False):
    tag = "⏮️ <b>REVIEW: DAY " if is_review else "📖 <b>DAY "
    msg = f"🔥 <b>STREAK: {streak} DAYS</b>\n{tag}{day}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, item in enumerate(data['sentences']):
        msg += f"{i+1}. 🇬🇧 <b>{item['eng']}</b>\n🗣️ <i>{item['say']}</i>\n👨 {item['male']}\n👩 {item['female']}\n\n"

    msg += f"💡 <b>Grammar:</b> {data['grammar']}"
    
    btns = []
    # Add Bookmark Buttons for each sentence (1-5)
    row1 = [InlineKeyboardButton(f"🔖 Save {i+1}", callback_data=f"save_{i}") for i in range(5)]
    btns.append(row1)
    
    if not is_review:
        btns.append([InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")])
        btns.append([InlineKeyboardButton("⏮️ Review Yesterday", callback_data="review_prev")])
    else:
        btns.append([InlineKeyboardButton("🔙 Back to Today", callback_data="back_today")])

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        wait = await u.message.reply_text("⏳ Initializing Instant Lessons...")
        curr, nxt = await asyncio.gather(fetch_ai_lesson(1), fetch_ai_lesson(2))
        users[uid] = {
            "day": 1, "streak": 0, "last_learned": "", "vocab": [],
            "current_lesson": curr, "next_lesson": nxt, "prev_lesson": None
        }
        save_users(users)
        await c.bot.delete_message(chat_id=u.effective_chat.id, message_id=wait.message_id)
    await u.message.reply_html(f"🚀 <b>Welcome!</b>\n/test - Instant Lesson\n/vocabulary - Saved items")

async def vocab_command(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = users.get(str(u.effective_chat.id), {})
    vocab = user.get("vocab", [])
    if not vocab:
        return await u.message.reply_text("Your vocabulary list is empty. Save sentences using the 🔖 buttons!")
    
    msg = "📂 <b>MY VOCABULARY</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for item in vocab[-10:]: # Show last 10
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
        sentence_data = user["current_lesson"]["sentences"][idx]
        entry = {"eng": sentence_data["eng"], "hin": sentence_data["male"]}
        if entry not in user["vocab"]:
            user["vocab"].append(entry)
            save_users(users)
            await c.bot.send_message(chat_id=u.effective_chat.id, text=f"✅ Saved: {entry['eng']}")

    elif query.data == "next_day":
        user["prev_lesson"], user["current_lesson"] = user["current_lesson"], user["next_lesson"]
        user["day"] += 1
        save_users(users)
        await send_lesson_ui(u.effective_chat.id, c, user["current_lesson"], user["day"], user["streak"])
        # Background fetch
        user["next_lesson"] = await fetch_ai_lesson(user["day"] + 1)
        save_users(users)

    elif query.data == "review_prev":
        if user.get("prev_lesson"):
            await send_lesson_ui(u.effective_chat.id, c, user["prev_lesson"], user["day"]-1, user["streak"], True)

    elif query.data == "back_today":
        await send_lesson_ui(u.effective_chat.id, c, user["current_lesson"], user["day"], user["streak"])

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("vocabulary", vocab_command))
    app_bot.add_handler(CommandHandler("test", lambda u,c: asyncio.run_coroutine_threadsafe(send_lesson_ui(u.effective_chat.id, c, load_users()[str(u.effective_chat.id)]["current_lesson"], load_users()[str(u.effective_chat.id)]["day"], load_users()[str(u.effective_chat.id)]["streak"]), asyncio.get_event_loop())))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.run_polling(drop_pending_updates=True)