import tempfile
from PIL import Image
from services.pdf_service import PDFService


def test_pdf_render_and_textlayer(tmp_path):
    img = Image.open('input.jpg')
    pdf_path = tmp_path / 'sample.pdf'
    img.save(str(pdf_path), 'PDF')

    pdf = PDFService()
    # The saved PDF from an image should not have a selectable text layer
    assert not pdf.has_text_layer(str(pdf_path))

    # rendering should produce at least one page image
    page_img = pdf.render_page(str(pdf_path), 0)
    assert isinstance(page_img, Image.Image)
