import os
import time
import schedule
import asyncio
from telegram import Bot
from groq import Groq  # NEW: Using Groq for free speed
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE & STATUS SECTION ---
app = Flask('')
last_status = "Initializing..."

@app.route('/')
def home(): 
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Bot Status: <span style="color: green;">LIVE</span></h1>
            <p><b>Target Chat ID:</b> {CHAT_ID}</p>
            <p><b>Last Status:</b> {last_status}</p>
            <p><b>Engine:</b> Groq (Llama 3.3 70B - Free)</p>
            <p><b>Interval:</b> Every 60 Minutes</p>
        </body>
    </html>
    """

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# ------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
client = Groq(api_key=GROQ_KEY)

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    prompt = "Create 5 short spoken Hindi phrases with English meanings for beginners. Format with bullet points."
    
    # Using Llama-3.3-70b via Groq (Fast and Free)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return f"🗣️ *Spoken Hindi – {today}*\n\n{completion.choices[0].message.content}"

async def send_hindi_lesson():
    global last_status
    try:
        print(f"DEBUG: Generating lesson via Groq at {time.ctime()}")
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        last_status = f"Success at {time.ctime()}"
        print("✅ SUCCESS: Message sent via Groq.")
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

# INTERVAL: Set to 60 minutes for stability
schedule.every(60).minutes.do(run_async_task)

if __name__ == "__main__":
    # Start Keep-Alive
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
    
    # Immediate test message
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)