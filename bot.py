import sys
import time
import telebot
from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from handlers.admin import register_admin_handlers
from handlers.post_creator import register_post_creator_handlers
from scheduler import start_scheduler

def main():
    print("========================================")
    print("🤖 TELEGRAM AUTO-POSTING BOT STARTING...")
    print("========================================")

    # 1. Database Initialize
    print("[1/4] Initializing SQLite Database...")
    init_db()

    # 2. Telegram Bot Instance Initialize
    print("[2/4] Initializing Bot Engine...")
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

    # 3. Register Handlers
    print("[3/4] Registering Admin & Post Handlers...")
    register_admin_handlers(bot)
    register_post_creator_handlers(bot)

    # 4. Start Background Scheduler
    print("[4/4] Starting Background Scheduler...")
    scheduler = start_scheduler(bot)

    print("----------------------------------------")
    print(f"🚀 Bot Online & Ready! Admin ID: {ADMIN_ID}")
    print("👉 Telegram me jakar /admin bhej kar control karein.")
    print("========================================")

    # Auto-Reconnect Resilient Polling Loop
    while True:
        try:
            bot.polling(non_stop=True, timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"⚠️ Network fluctuation detected ({e}), reconnecting in 3 seconds...")
            time.sleep(3)

if __name__ == "__main__":
    main()