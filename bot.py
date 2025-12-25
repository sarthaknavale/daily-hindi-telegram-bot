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
last_sent_time = "Never"

@app.route('/')
def home(): 
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🤖 Bot Status: <span style="color: orange;">QUOTA LIMIT REACHED</span></h1>
            <p><b>Target Chat ID:</b> {CHAT_ID}</p>
            <p><b>Last Status:</b> {last_sent_time}</p>
            <p><b>Action Required:</b> Check your OpenAI Billing/Quota.</p>
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
        lesson = await asyncio.to_thread(generate_hindi_lesson)
        await bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        last_sent_time = f"Success at {time.ctime()}"
    except openai.error.RateLimitError:
        last_sent_time = "Error: OpenAI Quota Exceeded"
        await bot.send_message(chat_id=CHAT_ID, text="⚠️ *Bot Alert:* Your OpenAI API quota has been exceeded. Please check your billing at platform.openai.com.")
    except Exception as e:
        last_sent_time = f"Error: {e}"

def run_async_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_hindi_lesson())
    finally:
        loop.close()

# Keep it at 5 minutes for testing, but change to .day.at() for long-term use
schedule.every(5).minutes.do(run_async_task)

if __name__ == "__main__":
    keep_alive()
    Thread(target=run_async_task).start() 
    while True:
        schedule.run_pending()
        time.sleep(1)