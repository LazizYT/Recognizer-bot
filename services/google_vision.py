import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class GoogleVisionAdapter:
    def __init__(self, credentials_json: str = None):
        try:
            from google.cloud import vision
            self.client = vision.ImageAnnotatorClient()
        except Exception as e:
            logger.warning("Google Vision client not available: %s", e)
            self.client = None

    def ocr(self, image_bytes: bytes, languages: List[str] = None) -> Tuple[str, float]:
        """Return (text, avg_confidence). Requires google-cloud-vision installed and credentials set."""
        if not self.client:
            raise RuntimeError("Google Vision client not configured")
        from google.cloud import vision
        img = vision.Image(content=image_bytes)
        response = self.client.document_text_detection(image=img)
        if response.error.message:
            raise RuntimeError(response.error.message)
        text = response.full_text_annotation.text
        # confidence aggregation (pages -> blocks -> paragraphs -> words)
        confs = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for par in block.paragraphs:
                    for word in par.words:
                        if word.confidence is not None:
                            confs.append(word.confidence)
        avg_conf = float(sum(confs)) / len(confs) if confs else 0.0
        return text, avg_conf
