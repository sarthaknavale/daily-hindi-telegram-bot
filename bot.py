import os
import threading
import time
import asyncio
import schedule
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= ENV VARIABLES =================
BOT_TOKEN = os.environ.get("8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ")
CHAT_ID = os.environ.get("753500208")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN or CHAT_ID environment variables are not set!")

bot = Bot(token=BOT_TOKEN)

# ================= DAILY HINDI LESSON =================
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
    await bot.send_message(
        chat_id=CHAT_ID,
        text=lesson,
        parse_mode="Markdown"
    )

def scheduled_job():
    asyncio.run(send_hindi_lesson())

# Schedule daily at 08:45 UTC
schedule.every().day.at("08:45").do(scheduled_job)

def scheduler_loop():
    print("⏰ Scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= /start COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nYou’ll receive daily spoken Hindi lessons here.\n⏰ Every day at 08:45 UTC",
        parse_mode="Markdown"
    )

async def telegram_polling():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    await app.run_polling()

def telegram_thread():
    asyncio.run(telegram_polling())

# ================= HTTP SERVER FOR RENDER FREE =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        # Encode Unicode to bytes (fix emoji issue)
        self.wfile.write("Bot is running 🚀".encode("utf-8"))

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🌐 HTTP server running on port {port}")
    server.serve_forever()

# ================= MAIN =================
if __name__ == "__main__":
    print("🤖 Hindi Bot Starting...")

    # Start scheduler and Telegram polling in background threads
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=telegram_thread, daemon=True).start()

    # Start HTTP server (Render Free requires a bound port)
    start_http_server()
