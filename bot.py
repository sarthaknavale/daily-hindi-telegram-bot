import json, asyncio, os, html, pytz, random
import google.generativeai as genai
from datetime import time as dt_time, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
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

# Configure Gemini
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

# --- GEMINI CONTENT ENGINES ---
async def generate_lesson_content(day):
    prompt = f"Act as an English teacher. Create a beginner lesson for Day {day}. Provide 5 sentences with English, Phonetic pronunciation, Hindi Male, and Hindi Female translations. Include one short Grammar Focus tip. Output strictly as JSON: {{'grammar': 'explanation', 'sentences': [{{'eng': '', 'say': '', 'male': '', 'female': ''}}]}}"
    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned)
    except: return None

async def generate_quiz(day):
    prompt = f"Based on English lesson Day {day}, generate one translation challenge. Provide the English sentence and the correct Hindi translation. Output strictly as JSON: {{'question': 'English sentence', 'answer': 'Hindi translation'}}"
    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned)
    except: return None

async def correct_user_sentence(text):
    prompt = f"Act as a grammar coach. Check this: '{text}'. Output strictly as JSON: {{'is_correct': true/false, 'correction': '', 'explanation': '', 'pro_tip': ''}}"
    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned)
    except: return None

# --- CORE LOGIC ---
async def send_lesson(chat_id, context, is_manual=False):
    users = load_users()
    uid = str(chat_id)
    user = users.get(uid, {"day": 1, "streak": 0})
    
    load_msg = await context.bot.send_message(chat_id=chat_id, text="🗣️ <i>Gemini is preparing your lesson...</i>", parse_mode="HTML")
    data = await generate_lesson_content(user["day"])
    await context.bot.delete_message(chat_id=chat_id, message_id=load_msg.message_id)

    if data:
        if is_manual:
            now = datetime.now(IST)
            today_str = now.strftime('%Y-%m-%d')
            user["streak"] = user.get("streak", 0) + 1 if user.get("last_learned") != today_str else user["streak"]
            user["last_learned"] = today_str
            users[uid] = user
            save_users(users)

        msg = f"🔥 <b>STREAK: {user['streak']} DAYS</b>\n📖 <b>DAY {user['day']}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for item in data['sentences']:
            msg += f"🇬🇧 <b>{html.escape(item['eng'])}</b>\n🗣️ <i>{html.escape(item['say'])}</i>\n👨 {html.escape(item['male'])}\n👩 {html.escape(item['female'])}\n\n"
        msg += f"💡 <b>GRAMMAR:</b> <i>{html.escape(data['grammar'])}</i>"
        
        btns = [[InlineKeyboardButton("📝 Take Quiz", callback_data=f"quiz_{user['day']}")], [InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
        return True
    return False

# --- HANDLERS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    uid = str(u.effective_chat.id)
    if uid not in users:
        users[uid] = {"day": 1, "streak": 0, "last_learned": "", "time": "10:10", "name": u.effective_user.first_name}
        save_users(users)
    await u.message.reply_html(f"🚀 <b>Hi {u.effective_user.first_name}!</b>\n\n- /test : Daily Lesson\n- Send any English sentence for AI correction!")

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
        day = query.data.split("_")[1]
        quiz_data = await generate_quiz(day)
        if quiz_data:
            msg = f"<b>QUIZ TIME!</b>\n\nHow do you translate this?\n🇬🇧 <code>{quiz_data['question']}</code>"
            btns = [[InlineKeyboardButton("👁 Reveal Answer", callback_data=f"ans_{quiz_data['answer'][:20]}")]]
            # Note: Storing full answer in button callback is limited, we use a simple reveal logic
            c.user_data['last_ans'] = quiz_data['answer']
            await query.message.reply_html(msg, reply_markup=InlineKeyboardMarkup(btns))

    elif "ans_" in query.data:
        ans = c.user_data.get('last_ans', 'Answer hidden')
        await query.message.reply_html(f"✅ <b>Answer:</b>\n{ans}\n\nReady for the next day?", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Next Day", callback_data="next_day")]]))

async def handle_correction(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.message.text.startswith('/'): return
    wait_msg = await u.message.reply_html("🔍 <i>Checking...</i>")
    result = await correct_user_sentence(u.message.text)
    await c.bot.delete_message(chat_id=u.effective_chat.id, message_id=wait_msg.message_id)
    if result:
        res = f"📝 <b>CHECK</b>\n{'✅ Correct!' if result['is_correct'] else '❌ Correction: ' + result['correction']}\n\n💡 {result['explanation']}\n🌟 Pro Tip: {result['pro_tip']}"
        await u.message.reply_html(res)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("test", lambda u, c: send_lesson(u.effective_chat.id, c, True)))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_correction))
    app_bot.run_polling()