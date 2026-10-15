import io
from PIL import Image

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024


def validate_image(data: bytes, mime: str) -> None:
    """Raises ValueError for wrong type, too large, empty or corrupt images (checks real content, not just extension)."""
    if mime not in ALLOWED_MIME:
        raise ValueError("Unsupported image type. Use JPG, PNG or WebP.")
    if not data:
        raise ValueError("The image file is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("Image is larger than 5 MB.")
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise ValueError("The file is not a valid image.")


def validate_report_input(title: str, location: str, lat, lon) -> None:
    if len((title or "").strip()) < 3:
        raise ValueError("Please enter a title (at least 3 characters).")
    if len(title) > 120:
        raise ValueError("Title is too long (max 120).")
    if not (location or "").strip():
        raise ValueError("Please enter a location or nearby landmark.")
    if (lat is None) != (lon is None):
        raise ValueError("Enter both latitude and longitude, or neither.")
    if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude/longitude out of range.")
