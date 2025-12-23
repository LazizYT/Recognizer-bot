from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me an image or PDF and I will extract the text for you. Use /help for more details."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Instructions:\n"
        "- Send an image (photo or screenshot) or a PDF.\n"
        "- Use /language to set preferred OCR languages, e.g., `/language en,ru,uz`.\n"
        "- Use /settings to toggle cloud OCR or set output format.\n"
        "- Results longer than a message will be attached as a .txt file.\n"
        "Privacy: files are stored only temporarily and removed after processing."
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /language en,ru,uz")
        return
    langs = [p.strip() for p in parts[1].split(',') if p.strip()]
    context.user_data['langs'] = langs
    await update.message.reply_text(f"Languages set to: {', '.join(langs)}")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simple settings stub
    cloud = context.user_data.get('cloud_ocr', True)
    await update.message.reply_text(f"Cloud OCR is {'enabled' if cloud else 'disabled'}. Use /togglecloud to switch.")


async def toggle_cloud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cloud = context.user_data.get('cloud_ocr', True)
    context.user_data['cloud_ocr'] = not cloud
    await update.message.reply_text(f"Cloud OCR is now {'enabled' if not cloud else 'disabled'}.")


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tasks.queue_manager import redis_conn
    try:
        info = redis_conn.info()
        qlen = redis_conn.llen('rq:queue:default')
        await update.message.reply_text(f"OK. Redis connected. Queue length: {qlen}")
    except Exception as e:
        await update.message.reply_text(f"Health check failed: {e}")
