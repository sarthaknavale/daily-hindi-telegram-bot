import os
import time
import schedule
from telegram import Bot
import openai
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE SECTION ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run_web_server():
    # Render provides a PORT environment variable automatically
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# ---------------------------------

# CORRECT WAY: We use the NAME of the variable, not the secret itself
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize Bot and OpenAI
bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")
    prompt = """
    You are a Hindi teacher.
    Create 5 short SPOKEN Hindi phrases for daily conversation.
    Include Hindi (Devanagari) and English meaning.
    Keep it beginner friendly.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    lesson = response.choices[0].message.content
    return f"🗣️ *Spoken Hindi – {today}*\n\n{lesson}\n\n📌 Speak aloud today!"

def send_hindi_lesson():
    try:
        lesson = generate_hindi_lesson()
        bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        print(f"Lesson sent successfully at {time.ctime()}")
    except Exception as e:
        print(f"Error: {e}")

# Schedule the task (2:00 AM UTC)
schedule.every().day.at("03:05").do(send_hindi_lesson)

if __name__ == "__main__":
    keep_alive() # Mandatory for Render Free Tier
    print("🤖 Bot is running...")
    while True:
        schedule.run_pending()
        time.sleep(1)