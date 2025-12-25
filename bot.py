import os
import time
import schedule
from telegram import Bot
import openai
from datetime import date
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE SECTION ---
# This creates a tiny web server so Render doesn't shut down the bot.
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()
# ---------------------------------

# Load secrets from Environment Variables (Set these in Render Dashboard)
BOT_TOKEN = os.environ.get("8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ")
CHAT_ID = os.environ.get("753500208")
OPENAI_API_KEY = os.environ.get("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")

# Initialize Bot and OpenAI
bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")

    prompt = """
    You are a Hindi teacher.
    Create 5 short SPOKEN Hindi phrases for daily conversation.
    Include:
    - Hindi (Devanagari)
    - English meaning
    - Very simple, natural phrases
    Keep it beginner friendly.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    lesson = response.choices[0].message.content

    final_message = f"🗣️ *Spoken Hindi – {today}*\n\n{lesson}\n\n📌 Speak aloud today!"
    return final_message

def send_hindi_lesson():
    try:
        lesson = generate_hindi_lesson()
        bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")
        print(f"Lesson sent successfully at {time.ctime()}")
    except Exception as e:
        print(f"Error sending message: {e}")

# Schedule the task
schedule.every().day.at("02:00").do(send_hindi_lesson)

if __name__ == "__main__":
    # 1. Start the web server to stay alive on Render
    keep_alive()
    
    print("🤖 Auto Hindi Teacher Bot Running...")
    
    # 2. Start the infinite loop for the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)