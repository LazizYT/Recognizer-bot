import asyncio
import logging
import mimetypes
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes



logger = logging.getLogger(__name__)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc = message.document

    # Download file to a temp path that persists until worker completes
    tmpdir = tempfile.mkdtemp()
    file_path = os.path.join(tmpdir, doc.file_name or "file")
    try:
        file_obj = await doc.get_file()
        await file_obj.download_to_drive(custom_path=file_path)
    except Exception as e:
        logger.exception("Failed to download document")
        await message.reply_text("Sorry, failed to download your file.")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Rate limiting
    from storage.rate_limiter import RateLimiter
    rl = RateLimiter()
    if not rl.allow(message.chat_id):
        remaining = rl.remaining(message.chat_id)
        await message.reply_text(
            f"Rate limit exceeded. Try again in {60} seconds. Remaining this minute: {remaining}"
        )
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Check cache by file hash
    from storage.cache import Cache
    from utils.hashing import sha256_file
    cache = Cache()
    file_hash = sha256_file(file_path)
    if cache.exists(file_hash):
        payload = cache.get(file_hash)
        await message.reply_text("Found cached result; sending...")
        from tasks.worker_rq import send_file, send_message
        send_message(message.chat_id, "Sending cached OCR result")
        send_file(message.chat_id, payload['txt_path'], caption="Cached OCR result")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    await message.reply_text(f"Received {doc.file_name}. Queued for processing.")

    # Enqueue job in Redis RQ
    from tasks.queue_manager import enqueue_job
    opts = {
        'langs': context.user_data.get('langs'),
        'cloud_ocr': context.user_data.get('cloud_ocr', True)
    }
    job = enqueue_job('tasks.worker_rq.process_file_job_rq', file_path, doc.mime_type, message.chat_id, opts)
    await message.reply_text(f"Job queued (id={job.id}).")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    photo = message.photo[-1]  # highest resolution

    tmpdir = tempfile.mkdtemp()
    file_path = os.path.join(tmpdir, f"photo_{photo.file_id}.jpg")
    try:
        file_obj = await photo.get_file()
        await file_obj.download_to_drive(custom_path=file_path)
    except Exception as e:
        logger.exception("Failed to download photo")
        await message.reply_text("Sorry, failed to download your photo.")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Rate limiting for photo
    from storage.rate_limiter import RateLimiter
    rl = RateLimiter()
    if not rl.allow(message.chat_id):
        remaining = rl.remaining(message.chat_id)
        await message.reply_text(
            f"Rate limit exceeded. Try again in {60} seconds. Remaining this minute: {remaining}"
        )
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    # Check cache
    from storage.cache import Cache
    from utils.hashing import sha256_file
    cache = Cache()
    file_hash = sha256_file(file_path)
    if cache.exists(file_hash):
        payload = cache.get(file_hash)
        await message.reply_text("Found cached result; sending...")
        from tasks.worker_rq import send_file, send_message
        send_message(message.chat_id, "Sending cached OCR result")
        send_file(message.chat_id, payload['txt_path'], caption="Cached OCR result")
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    await message.reply_text("Received photo. Queued for OCR.")

    from tasks.queue_manager import enqueue_job
    opts = {
        'langs': context.user_data.get('langs'),
        'cloud_ocr': context.user_data.get('cloud_ocr', True)
    }
    job = enqueue_job('tasks.worker_rq.process_file_job_rq', file_path, 'image/jpeg', message.chat_id, opts)
    await message.reply_text(f"Job queued (id={job.id}).")
