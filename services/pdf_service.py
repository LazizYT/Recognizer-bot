import logging
from typing import List

from PIL import Image
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFService:
    def __init__(self, render_dpi: int = 300):
        self.render_dpi = render_dpi

    def has_text_layer(self, pdf_path: str) -> bool:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                return True
        return False

    def extract_text_layer(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        texts = []
        for i, page in enumerate(doc, start=1):
            txt = page.get_text("text")
            texts.append(f"--- Page {i} ---\n" + txt)
        return "\n".join(texts)

    def render_page(self, pdf_path: str, page_number: int) -> Image.Image:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        zoom = self.render_dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        return img

    def render_all_pages(self, pdf_path: str, callback=None):
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            img = self.render_page(pdf_path, i)
            if callback:
                callback(i + 1, len(doc), img)
            else:
                yield i + 1, img
