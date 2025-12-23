import os
import threading
import time
import asyncio
import schedule
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= ENV =================

BOT_TOKEN = os.environ["8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ"]
CHAT_ID = os.environ["753500208"]

bot = Bot(token=BOT_TOKEN)

# ================= DAILY MESSAGE =================

async def send_hindi_lesson():
    lesson = """
🗣️ *Spoken Hindi – Daily Lesson*

1️⃣ कैसे हो? – How are you?
2️⃣ क्या कर रहे हो? – What are you doing?
3️⃣ कहाँ जा रहे हो? – Where are you going?
4️⃣ थोड़ा रुको – Wait a little
5️⃣ कोई बात नहीं – No problem

📌 Speak aloud today!
"""
    await bot.send_message(chat_id=753500208, text=lesson, parse_mode="Markdown")

def scheduled_job():
    asyncio.run(send_hindi_lesson())

schedule.every().day.at("08:45").do(scheduled_job)

def scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= /start COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nYou’ll receive daily Hindi lessons here.\n⏰ 08:45 UTC",
        parse_mode="Markdown"
    )

async def telegram_polling():
    app = ApplicationBuilder().token(8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ).build()
    app.add_handler(CommandHandler("start", start))
    await app.run_polling()

def telegram_thread():
    asyncio.run(telegram_polling())

# ================= PORT BINDER (CRITICAL) =================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# ================= MAIN =================

if __name__ == "__main__":
    print("🤖 Bot starting...")

    # Start background work FIRST
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=telegram_thread, daemon=True).start()

    # Bind PORT IMMEDIATELY (Render requirement)
    start_http_server()
