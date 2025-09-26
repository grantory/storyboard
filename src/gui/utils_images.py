from __future__ import annotations

import base64
import io
from typing import Optional, Tuple

from PIL import Image
import customtkinter as ctk
import requests


def _normalize_data_url(value: str) -> str:
    s = (value or "").strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    if "data:image/" in s and not s.startswith("data:"):
        i = s.find("data:image/")
        s = s[i:]
    return s


def data_url_to_bytes(data_url: str) -> bytes:
    if not isinstance(data_url, str) or "," not in data_url:
        raise ValueError("Invalid data URL")
    _header, b64 = data_url.split(",", 1)
    return base64.b64decode(b64)


def data_url_to_pil_image(data_url: str) -> Image.Image:
    s = _normalize_data_url(data_url)
    if s.startswith("http://") or s.startswith("https://"):
        r = requests.get(s, timeout=30)
        raw = r.content
    else:
        raw = data_url_to_bytes(s)
    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    return img


def _fit_size(width: int, height: int, max_width: Optional[int]) -> Tuple[int, int]:
    if not max_width or width <= max_width:
        return width, height
    new_height = int(height * (max_width / width))
    return max_width, new_height


def data_url_to_ctkimage(data_url: str, max_width: Optional[int] = None) -> ctk.CTkImage:
    img = data_url_to_pil_image(data_url)
    w, h = _fit_size(img.width, img.height, max_width)
    if (w, h) != (img.width, img.height):
        img = img.resize((w, h), Image.LANCZOS)
    # Use same image for light/dark; CTk handles scaling for HiDPI
    return ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))


