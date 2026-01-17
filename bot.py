import json, asyncio, os, html, pytz, random
import google.generativeai as genai
from datetime import time as dt_time, datetime, timedelta
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

# --- FAIL-SAFE DATA (Used if AI fails) ---
BACKUP_LESSONS = {
    1: {"grammar": "Greetings", "sentences": [{"eng": "Hello, how are you?", "say": "He-lo, hao are yu", "male": "नमस्ते, आप कैसे हैं?", "female": "नमस्ते, आप कैसी हैं?"}]},
    2: {"grammar": "Introductions", "sentences": [{"eng": "My name is John.", "say": "Ma-ai ne-m iz Jawn", "male": "मेरा नाम जॉन है।", "female": "मेरा नाम जॉन है।"}]},
}

def load_users():
    try:
        with open(USERS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)

# --- ROBUST AI ENGINE ---
async def generate_lesson_content(day):
    prompt = (f"Act as an English teacher. Create a lesson for Day {day}. "
              "Provide 5 beginner sentences with English, Phonetic pronunciation, Hindi Male, and Hindi Female. "
              "Return ONLY a JSON object. Format: "
              '{"grammar": "tip", "sentences": [{"eng": "Sentence", "say": "pronunciation", "male": "Hindi", "female": "Hindi"}]}')
    try:
        # Timeout safety for faster response
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- CORE LOGIC ---
async def send_lesson(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user = users.get(uid, {"day": 1, "streak": 0, "name": "Learner"})
    day = user['day']
    
    # Inform user immediately
    status = await context.bot.send_message(chat_id=chat_id, text="⏳ <b>Generating your lesson...</b>", parse_mode="HTML")
    
    # Try AI first
    data = await generate_lesson_content(day)
    
    # If AI fails, use Backup
    is_backup = False
    if not data:
        data = BACKUP_LESSONS.get(day % len(BACKUP_LESSONS) + 1)
        is_backup = True
        
    await context.bot.delete_message(chat_id=chat_id, message_id=status.message_id)

    if data:
        if is_manual:
            now = datetime.now(IST).strftime('%Y-%m-%d')
            user["streak"] = user.get("streak", 0) + 1 if user.get("last_learned") != now else user["streak"]
            user["last_learned"] = now
            users[uid] = user
            save_users(users)

        tag = "⚠️ (Fail-Safe Mode)" if is_backup else ""
        msg = f"🔥 <b>STREAK: {user['streak']} DAYS</b>\n📖 <b>DAY {day}</b> {tag}\n━━━━━━━━━━━━━━━━━━\n\n"
        voice_text = ""
        for item in data['sentences']:
            msg += f"🇬🇧 <b>{item['eng']}</b>\n🗣️ <i>{item['say']}</i>\n👨 {item['male']}\n👩 {item['female']}\n\n"
            voice_text += item['eng'] + ". "
        
        msg += f"💡 <b>Grammar:</b> {data['grammar']}"
        
        btns = [[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
        
        # Audio delivery
        try:
            v_file = f"v_{chat_id}.mp3"
            gTTS(text=voice_text, lang='en').save(v_file)
            with open(v_file, 'rb') as v: await context.bot.send_voice(chat_id=chat_id, voice=v)
            os.remove(v_file)
        except: pass
        return True
    
    await context.bot.send_message(chat_id=chat_id, text="❌ System Busy. Try /test again.")
    return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "last_learned": "", "time": "10:10", "name": u.effective_user.first_name}
        save_users(users)
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\n/test - Start Lesson")

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    if query.data == "next_day":
        uid = str(u.effective_chat.id)
        users = load_users()
        users[uid]["day"] = users.get(uid, {}).get("day", 1) + 1
        save_users(users)
        await send_lesson(u.effective_chat.id, c, True)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_lesson(u.effective_chat.id, c, True)))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.run_polling(drop_pending_updates=True)