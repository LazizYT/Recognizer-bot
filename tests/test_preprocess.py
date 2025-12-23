from services.preprocess import auto_rotate, deskew, binarize
from PIL import Image


def test_preprocess_pipeline():
    img = Image.open('input.jpg')
    r1 = auto_rotate(img)
    assert isinstance(r1, Image.Image)
    r2 = deskew(r1)
    assert isinstance(r2, Image.Image)
    r3 = binarize(r2)
    assert isinstance(r3, Image.Image)
