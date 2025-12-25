import os
import time
import schedule
import asyncio
from telegram import Bot
from groq import Groq
from datetime import date
from flask import Flask
from threading import Thread
import html # Added for safe character handling

# --- RENDER KEEP-ALIVE ---
app = Flask('')
last_status = "Initializing..."

@app.route('/')
def home(): 
    return f"<h1>Bot Status: LIVE</h1><p>Last Status: {last_status}</p>"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BOT CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
client = Groq(api_key=GROQ_KEY)

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    # We ask for a simple format to keep it safe
    prompt = "Create 5 short spoken Hindi phrases with English meanings. Format as a simple list."
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    # This cleans the AI text so characters like '<' or '&' don't break HTML
    safe_content = html.escape(completion.choices[0].message.content)
    return f"<b>🗣️ Spoken Hindi – {today}</b>\n\n{safe_content}"

async def send_hindi_lesson():
    global last_status
    try:
        lesson_text = await asyncio.to_thread(generate_hindi_lesson)
        # SWITCHED: parse_mode is now HTML
        await bot.send_message(chat_id=CHAT_ID, text=lesson_text, parse_mode="HTML")
        last_status = f"Success at {time.ctime()}"
    except Exception as e:
        last_status = f"Error: {e}"
        print(f"❌ ERROR: {e}")

def run_async_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_hindi_lesson())
    finally:
        loop.close()

schedule.every(60).minutes.do(run_async_task)

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
    
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)