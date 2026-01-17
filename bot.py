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
#        CONFIG (STRICTLY USE FLASH)
# ==========================================
TOKEN = "8450562900:AAFMHSXkewWDqzpbxmCLKZokbL-2JlqNsoA" 
GEMINI_API_KEY = "AIzaSyD6qw18ecUshcqPRNFWWTTliFEmdVHd7ZQ"
USERS_FILE = "users.json"
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- BACKUP LESSONS (Used only if AI is totally dead) ---
OFFLINE_LESSONS = {
    1: {"sentences": [{"eng": "The weather is nice today.", "hin": "आज मौसम अच्छा है।"}, {"eng": "I am learning English.", "hin": "मैं अंग्रेजी सीख रहा हूँ।"}]},
    2: {"sentences": [{"eng": "Where is the nearest station?", "hin": "सबसे पास का स्टेशन कहाँ है?"}, {"eng": "I need some help.", "hin": "मुझे कुछ मदद चाहिए।"}]}
}

def load_db():
    if not os.path.exists(USERS_FILE): return {}
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(USERS_FILE, "w") as f: json.dump(data, f, indent=2)

# --- THE STUBBORN ENGINE WITH OFFLINE FALLBACK ---
async def fetch_ai_lesson(day, retries=5):
    prompt = (f"English Teacher. Day {day} lesson. 5 beginner sentences. "
              "Return ONLY JSON: {'sentences': [{'eng': '', 'hin': ''}]}")
    
    for i in range(retries):
        try:
            # Short timeout to prevent hanging
            response = await asyncio.wait_for(asyncio.to_thread(model.generate_content, prompt), timeout=10)
            clean_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_text)
        except Exception:
            await asyncio.sleep((i + 1) * 2)
            continue
    
    # --- FALLBACK ---
    print(f"AI Failed after 5 tries. Using Offline Backup for Day {day}.")
    return OFFLINE_LESSONS.get(day, OFFLINE_LESSONS[1])

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    db = load_db()
    if uid not in db:
        db[uid] = {"day": 1, "next_lesson": None}
        save_db(db)
    await u.message.reply_html("🚀 <b>Bot Active!</b>\nUse /test for an instant lesson.")

async def test_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = str(u.effective_chat.id)
    db = load_db()
    user = db.get(uid, {"day": 1, "next_lesson": None})

    if user.get("next_lesson"):
        data = user["next_lesson"]
        user["next_lesson"] = None
        is_cached = True
    else:
        msg = await u.message.reply_text("⏳ <i>Connecting to Gemini AI...</i>", parse_mode="HTML")
        data = await fetch_ai_lesson(user['day'])
        await c.bot.delete_message(chat_id=uid, message_id=msg.message_id)
        is_cached = False

    if data:
        txt = f"📖 <b>DAY {user['day']}</b>\n\n"
        for s in data['sentences']:
            txt += f"🇬🇧 <code>{html.escape(s['eng'])}</code>\n🇮🇳 {html.escape(s['hin'])}\n\n"
        
        btns = [[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
        await u.message.reply_html(txt, reply_markup=InlineKeyboardMarkup(btns))
        
        user['day'] += 1
        db[uid] = user
        save_db(db)
        
        # Pre-fetch for tomorrow (Quietly)
        asyncio.create_task(background_prefetch(uid, user['day']))

async def background_prefetch(uid, day):
    db = load_db()
    if uid in db:
        lesson = await fetch_ai_lesson(day)
        db = load_db() # Refresh db before saving
        db[uid]["next_lesson"] = lesson
        save_db(db)

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    if query.data == "next_day":
        await test_cmd(u, c)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("test", test_cmd))
    bot.add_handler(CallbackQueryHandler(callback_handler))
    bot.run_polling(drop_pending_updates=True)