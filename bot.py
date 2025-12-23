from telegram import Bot
import schedule
import time

BOT_TOKEN = "8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ"
CHAT_ID = "753500208"

bot = Bot(token=BOT_TOKEN)

def send_hindi_lesson():
    lesson = """
🗣️ *Spoken Hindi – Daily Lesson*

1️⃣ कैसे हो? – How are you?
2️⃣ क्या कर रहे हो? – What are you doing?
3️⃣ कहाँ जा रहे हो? – Where are you going?
4️⃣ थोड़ा रुको – Wait a little
5️⃣ कोई बात नहीं – No problem

📌 Speak aloud today!
"""
    bot.send_message(chat_id=CHAT_ID, text=lesson, parse_mode="Markdown")

# ⏰ SET YOUR TIME (UTC)
schedule.every().day.at("08:45").do(send_hindi_lesson)

print("🤖 Hindi Bot Running...")

while True:
    schedule.run_pending()
    time.sleep(1)
