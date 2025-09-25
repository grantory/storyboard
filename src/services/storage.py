import base64
import io
import os
import time
from typing import Tuple

from PIL import Image


CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def image_to_data_url(image: Image.Image, format: str = "PNG") -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def bytes_to_data_url(data: bytes, mime: str = "image/png") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def save_data_url_png(data_url: str, prefix: str = "image") -> str:
    if "," not in data_url:
        raise ValueError("Invalid data URL")
    header, b64 = data_url.split(",", 1)
    data = base64.b64decode(b64)
    ts = int(time.time() * 1000)
    path = os.path.join(CACHE_DIR, f"{prefix}_{ts}.png")
    with open(path, "wb") as f:
        f.write(data)
    return path


def compress_image_bytes_to_jpeg_data_url(data: bytes, *, max_width: int = 1024, quality: int = 85) -> str:
    """
    Convert raw image bytes to a reasonably sized JPEG data URL.

    - Ensures RGB colorspace
    - Resizes to max_width while preserving aspect ratio
    - Uses JPEG quality and optimization for smaller payloads
    """
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_width:
        new_height = int(img.height * (max_width / img.width))
        img = img.resize((max_width, new_height), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"



def data_url_to_bytes_and_mime(data_url: str) -> Tuple[bytes, str]:
    """
    Convert a data URL (data:<mime>;base64,...) to raw bytes and mime type.
    """
    if "," not in data_url:
        raise ValueError("Invalid data URL")
    header, b64 = data_url.split(",", 1)
    # Extract mime type from header
    mime = "image/png"
    try:
        if header.startswith("data:") and ";" in header:
            mime = header[5: header.index(";")]
    except Exception:
        pass
    return base64.b64decode(b64), mime


def save_data_url_png_to_dir(data_url: str, directory: str, prefix: str = "image") -> str:
    """
    Save a data URL to a specific directory on the server (PNG extension).
    Creates the directory if it does not exist.
    """
    os.makedirs(directory, exist_ok=True)
    _, _ = os.path.split(directory)
    ts = int(time.time() * 1000)
    path = os.path.join(directory, f"{prefix}_{ts}.png")
    if "," not in data_url:
        raise ValueError("Invalid data URL")
    _, b64 = data_url.split(",", 1)
    data = base64.b64decode(b64)
    with open(path, "wb") as f:
        f.write(data)
    return path
