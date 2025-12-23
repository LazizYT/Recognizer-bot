import logging
from typing import List, Tuple

from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class TesseractAdapter:
    def __init__(self, tesseract_cmd: str = None, tessdata_dir: str = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.tessdata_dir = tessdata_dir

    def ocr(self, image: Image.Image, langs: List[str] = None) -> Tuple[str, float]:
        """Run Tesseract OCR and return (text, avg_confidence)"""
        lang = "+".join(langs) if langs else "eng"
        config = f"-l {lang} --oem 1 --psm 3"
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(image, config=config)

        # compute average confidence from data['conf'] (strings, -1 ignored)
        confs = [int(c) for c in data.get("conf", []) if c and c.isdigit() and int(c) >= 0]
        avg_conf = float(sum(confs)) / len(confs) if confs else 0.0
        logger.debug("Tesseract OCR done, avg_conf=%s", avg_conf)
        return text, avg_conf
