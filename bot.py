import os
import time
import schedule
import asyncio # New: Required for modern bot versions
from telegram import Bot
import openai
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE SECTION ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# ---------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    prompt = "Create 5 short spoken Hindi phrases with English meanings for beginners."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return f"🗣️ *Spoken Hindi – {today}*\n\n{response.choices[0].message.content}"

# Change 1: Added 'async' to the function
async def send_hindi_lesson():
    try:
        lesson = generate_hindi_lesson()
        # Change 2: Added 'await' before send_message
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        print(f"Message sent successfully at {time.ctime()}")
    except Exception as e:
        print(f"Error sending message: {e}")

# Change 3: Helper to run async function inside the synchronous schedule
def run_async_task():
    asyncio.run(send_hindi_lesson())

# 16:00 UTC = 09:30 PM IST
schedule.every().day.at("16:31").do(run_async_task)

if __name__ == "__main__":
    keep_alive()
    print("🤖 Bot is starting up...")
    
    # Optional: Send a test message immediately to verify fix
    run_async_task() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)