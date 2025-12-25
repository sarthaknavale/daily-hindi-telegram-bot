import os
import time
import schedule
from telegram import Bot
import openai
from datetime import date

# Load secrets
BOT_TOKEN = os.environ.get("8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ")
CHAT_ID = os.environ.get("753500208")
OPENAI_API_KEY = os.environ.get("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")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def generate_hindi_lesson():
    today = date.today().strftime("%d %B %Y")

    prompt = f"""
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

    final_message = f"""
🗣️ *Spoken Hindi – {today}*

{lesson}

📌 Speak aloud today!
"""
    return final_message

def send_hindi_lesson():
    lesson = generate_hindi_lesson()
    bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")

# ⏰ 8:45 AM IST = 03:15 UTC
schedule.every().day.at("02:00").do(send_hindi_lesson)

print("🤖 Auto Hindi Teacher Bot Running...")

while True:
    schedule.run_pending()
    time.sleep(1)
