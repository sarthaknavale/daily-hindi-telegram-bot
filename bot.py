import threading
import time
import asyncio
import schedule
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= BOT CONFIG =================
# NOTE: Free tier – token stored directly (NOT recommended for production)
BOT_TOKEN = "8450562900:AAEVvTV_Yx_4QstbnnwAUsgiKEWLWng8cUQ"
CHAT_ID = "753500208"

bot = Bot(token=BOT_TOKEN)

# ================= DAILY LESSON =================
async def send_hindi_lesson():
    lesson = (
        "🗣️ *Spoken Hindi – Daily Lesson*\n\n"
        "1️⃣ कैसे हो? – How are you?\n"
        "2️⃣ क्या कर रहे हो? – What are you doing?\n"
        "3️⃣ कहाँ जा रहे हो? – Where are you going?\n"
        "4️⃣ थोड़ा रुको – Wait a little\n"
        "5️⃣ कोई बात नहीं – No problem\n\n"
        "📌 Speak aloud today!"
    )

    await bot.send_message(
        chat_id=CHAT_ID,
        text=lesson,
        parse_mode="Markdown"
    )

def scheduled_job():
    asyncio.run(send_hindi_lesson())

# Send daily at 08:45 UTC
schedule.every().day.at("08:45").do(scheduled_job)

def scheduler_loop():
    print("⏰ Scheduler started")
    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= /start COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome!*\n\n"
        "You’ll receive *daily Hindi lessons* here.\n"
        "⏰ Every day at *08:45 UTC*",
        parse_mode="Markdown"
    )

async def telegram_polling():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    await app.run_polling()

def telegram_thread():
    asyncio.run(telegram_polling())

# ================= HTTP SERVER (ANTI-SLEEP) =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        return  # silence logs

def start_http_server():
    port = int(os.environ.get("PORT", 10000))  # Render-required
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🌐 HTTP server running on port {port}")
    server.serve_forever()

# ================= MAIN =================
if __name__ == "__main__":
    print("🤖 Hindi Bot Starting...")

    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=telegram_thread, daemon=True).start()

    start_http_server()
