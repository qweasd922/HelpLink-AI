import io
import pytest
from PIL import Image
from services.validation import validate_image, validate_report_input


def png() -> bytes:
    b = io.BytesIO(); Image.new("RGB", (4, 4)).save(b, "PNG"); return b.getvalue()


def test_valid_image_ok():
    validate_image(png(), "image/png")


@pytest.mark.parametrize("data,mime", [(png(), "application/pdf"), (b"", "image/png"), (b"not an image", "image/png"),
                                       (b"x" * (5 * 1024 * 1024 + 1), "image/png")])
def test_invalid_images_rejected(data, mime):
    with pytest.raises(ValueError):
        validate_image(data, mime)


def test_report_input():
    validate_report_input("Bin full", "Canteen", None, None)
    for args in [("", "x", None, None), ("Bin", "", None, None), ("Bin", "x", 13.0, None), ("Bin", "x", 99.0, 100.0)]:
        with pytest.raises(ValueError):
            validate_report_input(*args)
