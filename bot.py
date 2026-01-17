import json, os, html, pytz
import google.generativeai as genai
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "BOT_ALIVE", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# ==========================================
#        HIDDEN CONFIGURATIONS
# ==========================================
TOKEN = "8450562900:AAFMHSXkewWDqzpbxmCLKZokbL-2JlqNsoA" 
MY_ID = 753500208  # Your numeric Telegram ID
GEMINI_API_KEY = "AIzaSyD6qw18ecUshcqPRNFWWTTliFEmdVHd7ZQ"
USERS_FILE = "users.json"
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def load_db():
    if not os.path.exists(USERS_FILE): return {}
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(USERS_FILE, "w") as f: json.dump(data, f, indent=2)

async def get_ai_lesson(day):
    """Fetches lesson from Gemini with JSON cleaning."""
    prompt = (f"Provide an English lesson for Day {day}. 5 sentences with Hindi translation. "
              "Return ONLY valid JSON: {'sentences': [{'eng': '', 'hin': ''}]}")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(text)
    except: return None

async def test(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    db = load_db()
    user = db.get(uid, {"day": 1})
    
    # 1. Direct Feedback
    prog_msg = await u.message.reply_text("⏳ *AI is fetching your lesson...*", parse_mode="Markdown")
    
    # 2. Get Lesson
    data = await get_ai_lesson(user['day'])
    
    if data:
        output = f"📖 *DAY {user['day']}*\n\n"
        for s in data['sentences']:
            output += f"🇬🇧 `{s['eng']}`\n🇮🇳 {s['hin']}\n\n"
        
        await c.bot.edit_message_text(chat_id=uid, message_id=prog_msg.message_id, text=output, parse_mode="Markdown")
        
        # 3. Update DB
        user['day'] += 1
        db[uid] = user
        save_db(db)
    else:
        await c.bot.edit_message_text(chat_id=uid, message_id=prog_msg.message_id, text="❌ AI Busy. Please try /test again.")

if __name__ == "__main__":
    # Start Keep-Alive Server
    Thread(target=run_flask).start()
    
    # Start Bot
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("test", test))
    bot.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🚀 Bot Started! Type /test")))
    
    print("Bot is running...")
    bot.run_polling(drop_pending_updates=True)