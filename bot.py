import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Anon 71 bot alive!"

targets = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Это анонимка 71 школы.\n\nПросто напиши сюда сообщение — оно улетит в канал анонимно.\nНикто не узнает кто ты.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Админ отвечает анониму
    if update.effective_user.id == ADMIN_ID:
        tid = targets.get(ADMIN_ID)
        if tid:
            try:
                await context.bot.send_message(tid, f"💬 Ответ из 71 школы:\n\n{update.message.text}")
                await update.message.reply_text("✅ Ответ отправлен анонимно")
            except:
                await update.message.reply_text("❌ Человек забанил бота")
            targets.pop(ADMIN_ID, None)
        return

    # Обычный юзер отправляет анонимку
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Ответить анонимно", callback_data=f"reply:{update.effective_user.id}")]])
    text = f"📩 <b>Аноним 71:</b>\n\n{update.message.text}"

    if CHANNEL_ID:
        await context.bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
    await context.bot.send_message(ADMIN_ID, text + f"\n\n<code>{update.effective_user.id}</code>", parse_mode="HTML", reply_markup=kb)
    await update.message.reply_text("✅ Отправлено анонимно в канал!")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    targets[q.from_user.id] = int(q.data.split(":")[1])
    await q.message.reply_text("Напиши ответ — следующее сообщение улетит анонимно этому человеку.")

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn, pattern="^reply:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
