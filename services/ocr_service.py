import logging
from typing import Callable, Iterable, List, Tuple

from services.tesseract_adapter import TesseractAdapter
from services.pdf_service import PDFService
from services.preprocess import auto_rotate, deskew, binarize

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self, config=None):
        self.tesseract = TesseractAdapter()
        self.pdf = PDFService()

    def ocr_image(self, image, langs: List[str] = None) -> Tuple[str, float]:
        # Preprocess
        image = auto_rotate(image)
        image = deskew(image)
        image = binarize(image)
        text, conf = self.tesseract.ocr(image, langs=langs)
        return text, conf

    def ocr_pdf(self, pdf_path: str, langs: List[str] = None, progress_callback: Callable[[int, int], None] = None) -> Tuple[str, float]:
        if self.pdf.has_text_layer(pdf_path):
            text = self.pdf.extract_text_layer(pdf_path)
            return text, 100.0

        pages = []
        for page_num, image in self.pdf.render_all_pages(pdf_path):
            if progress_callback:
                progress_callback(page_num, None)
            t, conf = self.ocr_image(image, langs=langs)
            pages.append(f"--- Page {page_num} ---\n" + t)
        return "\n".join(pages), 0.0
