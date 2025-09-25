from __future__ import annotations

import base64
import io
from typing import List, Tuple, Optional

import cv2  # type: ignore
import numpy as np
from PIL import Image
import math


def _frame_indices(total_frames: int, n: int) -> List[int]:
    n = max(1, n)
    return [max(0, min(total_frames - 1, round((i / (n + 1)) * total_frames))) for i in range(1, n + 1)]


def extract_frames_as_images(video_bytes: bytes, n: int = 5) -> List[Image.Image]:
    arr = np.frombuffer(video_bytes, dtype=np.uint8)
    video = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if video is not None:
        # imdecode isn't suitable for videos; fallback to VideoCapture from buffer via temp file
        pass
    # Use temp file for VideoCapture as OpenCV does not open from memory reliably
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp.flush()
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise RuntimeError("Failed to open video")
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        indices = _frame_indices(total_frames, n)
        images: List[Image.Image] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            # Downscale to reduce payload size; keep aspect ratio, max width 768
            max_width = 768
            if img.width > max_width:
                new_height = int(img.height * (max_width / img.width))
                img = img.resize((max_width, new_height), Image.LANCZOS)
            images.append(img)
        cap.release()
    if not images:
        raise RuntimeError("No frames extracted")
    return images


def image_to_data_url(img: Image.Image, *, format: str = "JPEG", quality: int = 85) -> str:
    buffer = io.BytesIO()
    fmt = format.upper()
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        # Ensure RGB and use sane quality settings for smaller payloads
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs.update({"quality": quality, "optimize": True})
    img.save(buffer, **save_kwargs)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    return f"data:{mime};base64,{b64}"


def estimate_context_frame_count(
    video_bytes: bytes,
    *,
    seconds_per_frame: float = 2.0,
    min_frames: int = 1,
    max_frames: Optional[int] = None,
) -> int:
    """Estimate the number of context frames to sample based on video duration.

    Strategy: one frame every `seconds_per_frame` seconds, rounded up.
    Falls back conservatively if FPS metadata is unavailable.
    """
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp.flush()
            cap = cv2.VideoCapture(tmp.name)
            if not cap.isOpened():
                return max(1, min_frames)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            cap.release()
    except Exception:
        return max(1, min_frames)

    duration_sec = 0.0
    if fps and fps > 0 and total_frames > 0:
        duration_sec = total_frames / fps
    elif total_frames > 0:
        # Heuristic fallback when FPS is missing: assume 30 fps
        duration_sec = total_frames / 30.0

    if duration_sec <= 0.0:
        return max(1, min_frames)

    n = int(math.ceil(duration_sec / max(0.001, seconds_per_frame)))
    if max_frames is not None:
        n = min(n, max_frames)
    return max(min_frames, n)


def sample_context_frames_as_data_urls(video_bytes: bytes, n: int = 5) -> List[str]:
    images = extract_frames_as_images(video_bytes, n=n)
    return [image_to_data_url(img, format="JPEG", quality=85) for img in images]


def sample_middle_frame_as_data_url(video_bytes: bytes) -> str:
    images = extract_frames_as_images(video_bytes, n=5)
    middle = images[len(images) // 2]
    return image_to_data_url(middle, format="JPEG", quality=85)


