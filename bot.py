import os
import time
import schedule
import asyncio
from telegram import Bot
from google import genai
from google.genai import errors # For handling quota errors
from datetime import date
from flask import Flask
from threading import Thread

# --- STATUS PAGE ---
app = Flask('')
last_sent_time = "Never"

@app.route('/')
def home(): 
    return f"<h1>Bot Status: LIVE</h1><p>Last Status: {last_sent_time}</p><p>Interval: 60 Minutes</p>"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    prompt = "Create 5 short spoken Hindi phrases with English meanings for beginners. Use bullet points."
    
    # Implementation of exponential backoff (Retry logic)
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt
            )
            return f"🗣️ *Spoken Hindi – {today}*\n\n{response.text}"
        except errors.ClientError as e:
            if "429" in str(e) and attempt < 2:
                wait = (attempt + 1) * 30
                print(f"Quota hit. Waiting {wait}s...")
                time.sleep(wait)
                continue
            raise e

async def send_hindi_lesson():
    global last_sent_time
    try:
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        last_sent_time = f"Success at {time.ctime()}"
        print("✅ Message sent.")
    except Exception as e:
        last_sent_time = f"Error: {e}"
        print(f"❌ Error: {e}")

def run_async_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_hindi_lesson())
    finally:
        loop.close()

# INCREASED TIME: Changed from 5 to 60 minutes
schedule.every(60).minutes.do(run_async_task)

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
    
    # Run once immediately on start
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)