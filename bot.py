import os
import time
import schedule
import asyncio
from telegram import Bot
import openai
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE SECTION ---
app = Flask('')
@app.route('/')
def home(): 
    return "Bot is LIVE and sending messages every 5 minutes!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# ---------------------------------

# SECURE LOADING: Fetching keys from Render Environment Variables
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

async def send_hindi_lesson():
    try:
        print(f"DEBUG: Task started at {time.ctime()}")
        # Using a thread for the OpenAI call keeps the async bot connection stable
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        print("✅ SUCCESS: 5-minute message sent.")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def run_async_task():
    """Professional Bridge: Handles the async Telegram call for the scheduler"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_hindi_lesson())
    loop.close()

# TRIGGER: Every 5 minutes instead of a fixed time
schedule.every(5).minutes.do(run_async_task)

if __name__ == "__main__":
    keep_alive() # Start the Flask server for Render liveness
    print("🤖 Bot is starting. Interval set to 5 Minutes.")
    
    # Send one message immediately on startup to verify live-ness
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)