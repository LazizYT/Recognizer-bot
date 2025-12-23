import logging
import os
import shutil
import tempfile

from services.ocr_service import OCRService

logger = logging.getLogger(__name__)

def process_file_job(file_path: str, mime_type: str, chat_id: int, opts: dict):
    """Process a file synchronously. Designed to be called from an executor."""
    ocr = OCRService()

    try:
        if mime_type == "application/pdf" or file_path.lower().endswith('.pdf'):
            text, conf = ocr.ocr_pdf(file_path, langs=opts.get('langs'))
        else:
            from PIL import Image
            img = Image.open(file_path)
            text, conf = ocr.ocr_image(img, langs=opts.get('langs'))

        # For now, write result to sidecar file and log
        out_path = file_path + ".txt"
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        logger.info("Processed file %s -> %s (chat_id=%s)", file_path, out_path, chat_id)
    except Exception as e:
        logger.exception("Error processing file %s: %s", file_path, e)
    finally:
        # cleanup if using a temp dir
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
