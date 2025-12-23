import os
import tempfile
from pathlib import Path

import fakeredis # pyright: ignore[reportMissingImports]
import redis # pyright: ignore[reportMissingImports]

from tasks import worker_rq
from storage.cache import Cache
from utils.hashing import sha256_file


def test_process_image_job(monkeypatch):
    # Use fake redis for cache and queue
    fake = fakeredis.FakeStrictRedis()

    # Use injected fake redis for Cache
    cache = Cache(conn=fake)
    # Ensure worker uses our fake cache
    worker_rq.cache = cache

    # Monkeypatch send_message and send_file to capture calls
    messages = []
    files_sent = []

    def fake_send_message(chat_id, text):
        messages.append((chat_id, text))

    def fake_send_file(chat_id, file_path, caption=None):
        files_sent.append((chat_id, file_path, caption))

    monkeypatch.setattr(worker_rq, 'send_message', fake_send_message)
    monkeypatch.setattr(worker_rq, 'send_file', fake_send_file)

    # Fake OCR backend to avoid requiring tesseract and external services
    class FakePDF:
        def has_text_layer(self, path):
            return False

        def extract_text_layer(self, path):
            return ""

        def render_all_pages(self, path):
            from PIL import Image    # pyright: ignore[reportMissingImports]
            img = Image.open('input.jpg')
            yield (1, img)

    class FakeOCR:
        def __init__(self):
            self.pdf = FakePDF()

        def ocr_image(self, image, langs=None):
            return ("dummy OCR text", 0.9)

    monkeypatch.setattr(worker_rq, 'OCRService', lambda: FakeOCR())

    # Prepare a small image file
    src = Path('input.jpg')
    assert src.exists(), "input.jpg test asset missing"
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, 'test.jpg')
    with open(src, 'rb') as r, open(tmpfile, 'wb') as w:
        w.write(r.read())

    # Ensure cache empty
    file_hash = sha256_file(tmpfile)
    assert not cache.exists(file_hash)

    # Run worker job (cloud_ocr disabled to avoid external calls)
    worker_rq.process_file_job_rq(tmpfile, 'image/jpeg', 9999, {'cloud_ocr': False, 'langs': ['eng']})

    # After processing, cache should exist
    assert cache.exists(file_hash)
    payload = cache.get(file_hash)
    assert 'txt_path' in payload
    txt_path = payload['txt_path']
    assert os.path.exists(txt_path)
    with open(txt_path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    assert len(content) > 0

    # Messages should include a Done summary
    assert any('Done.' in m[1] for m in messages)
    # File should have been sent
    assert any(f[1] == txt_path for f in files_sent)


def test_process_pdf_job(monkeypatch):
    # Setup fake redis again
    fake = fakeredis.FakeStrictRedis()

    cache = Cache(conn=fake)
    # Ensure worker uses our fake cache
    worker_rq.cache = cache

    messages = []
    files_sent = []

    def fake_send_message(chat_id, text):
        messages.append((chat_id, text))

    def fake_send_file(chat_id, file_path, caption=None):
        files_sent.append((chat_id, file_path, caption))

    monkeypatch.setattr(worker_rq, 'send_message', fake_send_message)
    monkeypatch.setattr(worker_rq, 'send_file', fake_send_file)

    # Fake OCR backend to avoid requiring tesseract and external services
    class FakePDF:
        def has_text_layer(self, path):
            return False

        def extract_text_layer(self, path):
            return ""

        def render_all_pages(self, path):
            from PIL import Image   # pyright: ignore[reportMissingImports]
            img = Image.open('input.jpg')
            yield (1, img)

    class FakeOCR:
        def __init__(self):
            self.pdf = FakePDF()

        def ocr_image(self, image, langs=None):
            return ("dummy OCR text", 0.9)

    monkeypatch.setattr(worker_rq, 'OCRService', lambda: FakeOCR())

    # Create a sample PDF from input.jpg
    from PIL import Image    # pyright: ignore[reportMissingImports]
    src = Path('input.jpg')
    assert src.exists(), "input.jpg test asset missing"
    tmpdir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmpdir, 'test.pdf')
    img = Image.open(src)
    img.save(pdf_path, 'PDF')

    file_hash = sha256_file(pdf_path)
    assert not cache.exists(file_hash)

    worker_rq.process_file_job_rq(pdf_path, 'application/pdf', 8888, {'cloud_ocr': False, 'langs': ['eng']})

    assert cache.exists(file_hash)
    payload = cache.get(file_hash)
    txt_path = payload['txt_path']
    assert os.path.exists(txt_path)
    with open(txt_path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    assert len(content) > 0
    assert any('Done' in m[1] or 'Extracted' in m[1] for m in messages)
