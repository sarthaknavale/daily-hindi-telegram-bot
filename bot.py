import json, asyncio, os, html, pytz, random
import google.generativeai as genai
from datetime import time as dt_time, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
from threading import Thread
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

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

# --- CERTIFICATE GENERATOR ---
def create_certificate(name, day):
    # Create a simple certificate image
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Draw a gold border
    d.rectangle([20, 20, 780, 580], outline=(212, 175, 55), width=10)
    
    # Add text (Note: In a real server, ensure you have a .ttf font file path)
    d.text((400, 150), "CERTIFICATE OF ACHIEVEMENT", fill=(0, 0, 0), anchor="mm")
    d.text((400, 250), "This is proudly presented to", fill=(0, 0, 0), anchor="mm")
    d.text((400, 320), name.upper(), fill=(18, 52, 86), anchor="mm")
    d.text((400, 400), f"For completing {day} Days of English Learning", fill=(0, 0, 0), anchor="mm")
    d.text((400, 500), f"Date: {datetime.now(IST).strftime('%d %b %Y')}", fill=(0, 0, 0), anchor="mm")
    
    cert_path = f"cert_{name}.png"
    img.save(cert_path)
    return cert_path

# --- CORE LOGIC ---
async def send_lesson(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user = users.get(uid, {"day": 1, "streak": 0, "total_learned": 0, "name": "Learner"})
    
    # Check for Certificate at Day 30
    if user['day'] == 30 and not user.get('cert_sent'):
        cert_file = create_certificate(user['name'], 30)
        await context.bot.send_photo(chat_id=chat_id, photo=open(cert_file, 'rb'), 
                                     caption="🎓 <b>CONGRATULATIONS!</b>\nYou have reached Day 30. Here is your certificate!")
        user['cert_sent'] = True
        save_users(users)
        os.remove(cert_file)

    prompt = f"English teacher. Day {user['day']} lesson. 5 sentences. JSON format: {{'grammar': '', 'sentences': [{{'eng': '', 'male': '', 'female': ''}}]}}"
    try:
        response = model.generate_content(prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        
        if is_manual:
            now = datetime.now(IST)
            if user.get("last_learned") != now.strftime('%Y-%m-%d'):
                user["streak"] = user.get("streak", 0) + 1
                user["total_learned"] = user.get("total_learned", 0) + 5
                user["last_learned"] = now.strftime('%Y-%m-%d')
                users[uid] = user
                save_users(users)

        msg = f"📖 <b>DAY {user['day']}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        voice_text = ""
        for item in data['sentences']:
            msg += f"🇬🇧 <b>{item['eng']}</b>\n👨 {item['male']}\n👩 {item['female']}\n\n"
            voice_text += item['eng'] + ". "
        
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", 
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))
        
        v_file = f"v_{chat_id}.mp3"
        gTTS(text=voice_text, lang='en').save(v_file)
        with open(v_file, 'rb') as v: await context.bot.send_voice(chat_id=chat_id, voice=v)
        os.remove(v_file)
        return True
    except: return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "total_learned": 0, "time": "10:10", "name": u.effective_user.first_name}
        save_users(users)
    await u.message.reply_html(f"🚀 <b>Welcome {u.effective_user.first_name}!</b>\nReach Day 30 to earn your certificate! 🎓")

async def callback_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    query = u.callback_query
    await query.answer()
    if query.data == "next_day":
        users = load_users()
        users[str(u.effective_chat.id)]["day"] += 1
        save_users(users)
        await send_lesson(u.effective_chat.id, c, True)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_lesson(u.effective_chat.id, c, True)))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.run_polling()