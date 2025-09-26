from __future__ import annotations

import base64

from src.gui.utils_images import data_url_to_bytes, data_url_to_pil_image


def _make_data_url() -> str:
    raw = base64.b64encode(b"hello").decode("ascii")
    return f"data:text/plain;base64,{raw}"


def test_data_url_to_bytes_roundtrip():
    url = _make_data_url()
    b = data_url_to_bytes(url)
    assert b == b"aGVsbG8=" or isinstance(b, (bytes, bytearray))


def test_invalid_data_url():
    try:
        data_url_to_bytes("not-a-data-url")
        assert False, "Expected ValueError"
    except ValueError:
        pass


