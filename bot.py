import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Логи
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("BOT_TOKEN и CHANNEL_ID должны быть заданы!")

# Flask для Render - теперь отдает 0 байт, чтобы cron-job не ругался
app = Flask(__name__)

@app.route('/')
def home():
    return '', 204

@app.route('/ping')
def ping():
    return 'ok', 200

def run_flask():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host='0.0.0.0', port=port)

# Telegram Bot
application = Application.builder().token(BOT_TOKEN).build()

# Хранилище
pending_posts = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or update.message.caption or ""

    # Определяем что прислал
    file_id = None
    content_type = "text"

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        content_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        content_type = "video"
    elif update.message.sticker:
        file_id = update.message.sticker.file_id
        content_type = "sticker"

    # Сохраняем
    msg_id = update.message.message_id
    pending_posts[msg_id] = {
        "text": text,
        "file_id": file_id,
        "type": content_type,
        "user_id": user.id,
        "username": user.username
    }

    # Кнопки админу
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{msg_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{msg_id}")
        ]
    ]

    preview = f"📩 Новая анонимка (ID: {msg_id})\nОт: @{user.username or user.id}\n\n"
    if text:
        preview += f"{text[:1000]}"
    else:
        preview += f"[{content_type}]"

    try:
        if content_type == "photo":
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption=preview,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif content_type == "video":
            await context.bot.send_video(
                chat_id=ADMIN_ID,
                video=file_id,
                caption=preview,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=preview,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        await update.message.reply_text("✅ Отправлено на модерацию! Скоро появится в канале.")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
        await update.message.reply_text("❌ Ошибка, попробуй позже.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    msg_id = int(data.split("_")[1])
    post = pending_posts.get(msg_id)

    if not post:
        await query.edit_message_text("❌ Пост уже удален или не найден.")
        return

    if data.startswith("approve_"):
        try:
            if post["type"] == "photo":
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=post["file_id"],
                    caption=post["text"] if post["text"] else None
                )
            elif post["type"] == "video":
                await context.bot.send_video(
                    chat_id=CHANNEL_ID,
                    video=post["file_id"],
                    caption=post["text"] if post["text"] else None
                )
            else:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=post["text"]
                )

            await query.edit_message_caption(caption=f"✅ Одобрено и выложено в канал.\n\n{query.message.caption}") if post["type"] in ["photo","video"] else await query.edit_message_text(f"✅ Одобрено и выложено в канал.\n\n{query.message.text}")
            del pending_posts[msg_id]
        except Exception as e:
            logging.error(f"Ошибка публикации: {e}")
            await query.edit_message_text(f"❌ Ошибка публикации: {e}")

    elif data.startswith("reject_"):
        del pending_posts[msg_id]
        await query.edit_message_text(f"❌ Отклонено.\n\n{query.message.text or query.message.caption}")

application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(handle_callback))

# Запуск бота в отдельном потоке (фикс для Render)
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    logging.info("Flask запущен, запускаем бота...")
    run_bot()
