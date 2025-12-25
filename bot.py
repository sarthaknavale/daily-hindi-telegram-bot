import os
import time
import schedule
import asyncio
from telegram import Bot
from google import genai  # NEW: Using the new unified SDK
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE & STATUS SECTION ---
app = Flask('')
last_sent_time = "Never"

@app.route('/')
def home(): 
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Bot Status: <span style="color: green;">LIVE</span></h1>
            <p><b>Target Chat ID:</b> {CHAT_ID}</p>
            <p><b>Last Status:</b> {last_sent_time}</p>
            <p><b>Engine:</b> Gemini 2.0 Flash (Fixed)</p>
            <p style="color: gray;">Render Port: {os.environ.get("PORT", 8080)}</p>
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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
# Initialize the NEW client
client = genai.Client(api_key=GEMINI_KEY)

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    prompt = "Create 5 short spoken Hindi phrases with English meanings for beginners. Use bullet points."
    
    # NEW: Using Gemini 2.0 Flash (stable free tier)
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=prompt
    )
    return f"🗣️ *Spoken Hindi – {today}*\n\n{response.text}"

async def send_hindi_lesson():
    global last_sent_time
    try:
        print(f"DEBUG: Generating lesson at {time.ctime()}")
        # Prevent blocking the loop
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        last_sent_time = f"Success at {time.ctime()}"
        print("✅ SUCCESS: Message sent.")
    except Exception as e:
        last_sent_time = f"Error: {e}"
        print(f"❌ ERROR: {e}")

def run_async_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_hindi_lesson())
    finally:
        loop.close()

schedule.every(5).minutes.do(run_async_task)

if __name__ == "__main__":
    keep_alive()
    # Immediate trigger for verification
    Thread(target=run_async_task).start() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)