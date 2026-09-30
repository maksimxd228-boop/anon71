import os, asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Anon 71 bot alive!"

targets = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Это анонимка 71 школы. Просто напиши сюда — улетит в канал анонимно.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id == ADMIN_ID and ADMIN_ID in targets:
            tid = targets.pop(ADMIN_ID)
            await context.bot.send_message(tid, f"💬 Ответ из 71 школы:\n\n{update.message.text}")
            await update.message.reply_text("✅ Ответ отправлен")
            return
        txt = update.message.text
        await context.bot.send_message(CHANNEL_ID, f"📩 Аноним 71:\n\n{txt}")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить", callback_data=f"r:{update.effective_user.id}")]])
        await context.bot.send_message(ADMIN_ID, f"📩 Аноним 71:\n\n{txt}\n\nID: <code>{update.effective_user.id}</code>", parse_mode="HTML", reply_markup=kb)
        await update.message.reply_text("✅ Отправлено анонимно!")
    except Exception as e:
        print(f"ERROR: {e}")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    targets[q.from_user.id] = int(q.data.split(":")[1])
    await q.message.reply_text("Напиши ответ — следующее сообщение улетит анонимно.")

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    # Фикс для Render: создаем event loop для бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn, pattern="^r:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
