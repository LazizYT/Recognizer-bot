import logging
import os
import tempfile
from typing import Optional

from telegram import Bot

from services.ocr_service import OCRService
from storage.cache import Cache
from utils.hashing import sha256_file

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("8509561542:AAEOZiF2ymGxLOo2MA-roUucB_kDq-gJjw4")
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Use a module-level cache instance; allow overriding in tests by setting `worker_rq.cache`.
cache = Cache(redis_url)


def send_message(chat_id: int, text: str):
    if not BOT_TOKEN:
        logger.warning("Bot token not set; cannot send message")
        return
    bot = Bot(token=BOT_TOKEN)
    bot.send_message(chat_id=chat_id, text=text)


def send_file(chat_id: int, file_path: str, caption: Optional[str] = None):
    if not BOT_TOKEN:
        logger.warning("Bot token not set; cannot send file")
        return
    bot = Bot(token=BOT_TOKEN)
    with open(file_path, "rb") as fh:
        bot.send_document(chat_id=chat_id, document=fh, filename=os.path.basename(file_path), caption=caption)


def process_file_job_rq(file_path: str, mime_type: str, chat_id: int, opts: dict):
    """RQ worker entrypoint. Handles cache and progress updates."""
    logger.info("RQ worker started for %s (chat=%s)", file_path, chat_id)

    file_hash = sha256_file(file_path)
    if cache.exists(file_hash):
        payload = cache.get(file_hash)
        send_message(chat_id, "Found cached result; sending...")
        send_file(chat_id, payload["txt_path"], "Cached OCR result")
        return

    # Check running jobs for this user
    running_key = f"tgocr:running:{chat_id}"
    running = cache.conn.incr(running_key)
    if running == 1:
        cache.conn.expire(running_key, 3600)  # safety TTL

    try:
        max_concurrent = int(os.environ.get("MAX_CONCURRENT_JOBS", 3))
        if running > max_concurrent:
            send_message(chat_id, f"Too many concurrent jobs (>{max_concurrent}). Requeued in 60s.")
            # requeue in 60s
            from tasks.queue_manager import q
            q.enqueue_in(60, 'tasks.worker_rq.process_file_job_rq', file_path, mime_type, chat_id, opts)
            return

        send_message(chat_id, "Starting OCR processing...")

        ocr = OCRService()

        def progress_callback(page_idx, total_pages):
            try:
                send_message(chat_id, f"Processing page {page_idx}/{total_pages or '?'}...")
            except Exception:
                pass

        if mime_type == "application/pdf" or file_path.lower().endswith('.pdf'):
            # PDF flow
            pdf = ocr.pdf
            if pdf.has_text_layer(file_path):
                text = pdf.extract_text_layer(file_path)
                conf = 100.0
                # write and send
                out_path = os.path.join(tempfile.gettempdir(), f"ocr_result_{file_hash}.txt")
                with open(out_path, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                cache.set(file_hash, {"txt_path": out_path, "confidence": conf}, ttl=24 * 3600)
                send_message(chat_id, "Extracted selectable text from PDF.")
                send_file(chat_id, out_path, caption="Full extracted text")
                return

            # Scanned PDF: render per page and OCR
            page_texts = []
            partial_every = 5
            total_pages = len(list(pdf.render_all_pages(file_path)))
            sent_partial = 0
            for page_idx, image in pdf.render_all_pages(file_path):
                progress_callback(page_idx, total_pages)
                # Try cloud OCR first if enabled
                txt = None
                conf = 0.0
                if opts.get('cloud_ocr'):
                    try:
                        from services.google_vision import GoogleVisionAdapter
                        gv = GoogleVisionAdapter()
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
                            image.save(tf.name)
                            with open(tf.name, 'rb') as fh:
                                img_bytes = fh.read()
                        txt, conf = gv.ocr(img_bytes, languages=opts.get('langs'))
                    except Exception:
                        txt = None
                if not txt:
                    t, conf = ocr.ocr_image(image, langs=opts.get('langs'))
                    txt = t
                page_texts.append(f"--- Page {page_idx} ---\n" + txt)

                # send partial
                if page_idx % partial_every == 0:
                    partial_text = "\n".join(page_texts[sent_partial:page_idx])
                    summary = partial_text[:300]
                    send_message(chat_id, f"Partial result pages {sent_partial+1}-{page_idx}:\n{summary}")
                    sent_partial = page_idx

            full_text = "\n".join(page_texts)
            out_path = os.path.join(tempfile.gettempdir(), f"ocr_result_{file_hash}.txt")
            with open(out_path, 'w', encoding='utf-8') as fh:
                fh.write(full_text)
            cache.set(file_hash, {"txt_path": out_path, "confidence": 0.0}, ttl=24 * 3600)
            send_message(chat_id, "Done processing PDF.")
            send_file(chat_id, out_path, caption="Full extracted text")

        else:
            from PIL import Image   # pyright: ignore[reportMissingImports]
            img = Image.open(file_path)
            # Try cloud first
            txt = None
            conf = 0.0
            if opts.get('cloud_ocr'):
                try:
                    from services.google_vision import GoogleVisionAdapter
                    gv = GoogleVisionAdapter()
                    with open(file_path, 'rb') as fh:
                        bytes_data = fh.read()
                    txt, conf = gv.ocr(bytes_data, languages=opts.get('langs'))
                except Exception:
                    txt = None
            if not txt:
                txt, conf = ocr.ocr_image(img, langs=opts.get('langs'))

            out_path = os.path.join(tempfile.gettempdir(), f"ocr_result_{file_hash}.txt")
            with open(out_path, 'w', encoding='utf-8') as fh:
                fh.write(txt)
            cache.set(file_hash, {"txt_path": out_path, "confidence": conf}, ttl=24 * 3600)
            summary = txt[:400].strip()
            send_message(chat_id, f"Done. Summary:\n{summary}")
            send_file(chat_id, out_path, caption="Full extracted text")
    except Exception as e:
        logger.exception("Error in RQ job: %s", e)
        send_message(chat_id, "Error processing file: %s" % str(e))
    finally:
        try:
            # decrement running counter
            cache.conn.decr(running_key)
        except Exception:
            pass
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
