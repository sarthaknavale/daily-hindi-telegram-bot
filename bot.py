import json, os, html, asyncio, time
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# ==========================================
#        CONFIG (FILL THESE)
# ==========================================
TOKEN = "8450562900:AAFMHSXkewWDqzpbxmCLKZokbL-2JlqNsoA" 
GEMINI_API_KEY = "AIzaSyD6qw18ecUshcqPRNFWWTTliFEmdVHd7ZQ"
USERS_FILE = "users.json"
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)
# Using 'gemini-1.5-flash' - it is much more stable for bots
model = genai.GenerativeModel('gemini-1.5-flash')

def load_db():
    if not os.path.exists(USERS_FILE): return {}
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(USERS_FILE, "w") as f: json.dump(data, f, indent=2)

async def get_ai_lesson(day):
    # Instructions to Gemini to be extremely strict with JSON
    prompt = (f"Provide a beginner English lesson for Day {day}. "
              "Include 5 sentences with Hindi translations. "
              "Return ONLY valid JSON. No text before or after. "
              "Format: {'sentences': [{'eng': 'Hello', 'hin': 'नमस्ते'}]}")
    
    # TRY 3 TIMES BEFORE GIVING ERROR
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            # Clean JSON from markdown
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)
        except:
            await asyncio.sleep(2) # Wait 2 seconds before retrying
            continue
    return None

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🚀 Bot Ready! Type /test to get your lesson.")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    db = load_db()
    user = db.get(uid, {"day": 1})
    
    # 1. Immediate Feedback
    msg = await u.message.reply_text("⏳ AI is thinking...")
    
    # 2. Fetch with Retries
    data = await get_ai_lesson(user['day'])
    
    if data:
        txt = f"📖 <b>DAY {user['day']}</b>\n\n"
        for s in data['sentences']:
            txt += f"🇬🇧 <code>{html.escape(s['eng'])}</code>\n🇮🇳 {html.escape(s['hin'])}\n\n"
        
        await c.bot.edit_message_text(chat_id=uid, message_id=msg.message_id, text=txt, parse_mode="HTML")
        
        # Update Progress
        user['day'] += 1
        db[uid] = user
        save_db(db)
    else:
        # If all 3 retries fail
        await c.bot.edit_message_text(chat_id=uid, message_id=msg.message_id, 
                                     text="❌ AI is busy or rate-limited. Please wait 30 seconds and try /test again.")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("test", test_cmd))
    print("Bot started...")
    bot.run_polling(drop_pending_updates=True)