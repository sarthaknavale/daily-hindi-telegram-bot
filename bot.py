import os
import time
import schedule
import asyncio
from telegram import Bot
import openai
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE & STATUS SECTION ---
app = Flask('')

# Global variable to track the last successful message time
last_sent_time = "Never"

@app.route('/')
def home(): 
    return f"""
    <html>
        <head><title>Bot Status</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Bot Status: <span style="color: green;">LIVE</span></h1>
            <p><b>Target Chat ID:</b> {CHAT_ID}</p>
            <p><b>Last Successful Message:</b> {last_sent_time}</p>
            <p><b>Current Server Time:</b> {time.ctime()}</p>
            <hr width="50%">
            <p style="color: gray;">If the Chat ID above is wrong, update your Render Environment Variables.</p>
        </body>
    </html>
    """

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# ------------------------------------------

# Environment Variable Loading
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
    global last_sent_time
    try:
        print(f"DEBUG: Attempting to send message at {time.ctime()}")
        # Prevent blocking the async loop with OpenAI call
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        
        last_sent_time = time.ctime()
        print(f"✅ SUCCESS: Message sent to {CHAT_ID}")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        last_sent_time = f"FAILED Error: {error_msg}"
        print(f"❌ ERROR: {error_msg}")

def run_async_task():
    """Fresh event loop for every scheduled task to prevent crashes on Render"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_hindi_lesson())
    finally:
        loop.close()

# Schedule: Every 5 minutes
schedule.every(5).minutes.do(run_async_task)

if __name__ == "__main__":
    keep_alive()
    print("🤖 Bot Service starting up...")
    
    # Send one message immediately to verify everything is correct
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)