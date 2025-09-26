from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Callable, Dict, List, Optional, Union
import os
import requests

from openai import OpenAI

from src.config import V2Config
from src.services import with_backoff
from src.types import GenerationResult
from src.services.openrouter_http import chat_completions
from src.services.storage import bytes_to_data_url


IMAGE_SYSTEM_PROMPT = (
    "Generate a single cinematic still that matches the description and maintains the visual style of the provided "
    "style image. Return the image as a data URL if possible."
)


def build_image_messages(style_image_data_url: str, shot_text: str) -> List[dict]:
    content = [
        {"type": "text", "text": f"{IMAGE_SYSTEM_PROMPT}\n\nInstruction: {shot_text}"},
        {"type": "image_url", "image_url": {"url": style_image_data_url}},
    ]
    return [{"role": "user", "content": content}]


def _find_data_or_http_image_in_obj(obj) -> Optional[str]:
    try:
        # Direct string containing data URL or embedded data:image URL
        if isinstance(obj, str):
            if obj.startswith("data:image"):
                return obj
            if obj.startswith("http://") or obj.startswith("https://"):
                return obj
            if "data:image/" in obj:
                s = obj.find("data:image/")
                e = len(obj)
                for sep in ["\n", " ", ")", "]", '"', "'"]:
                    ix = obj.find(sep, s)
                    if ix != -1:
                        e = min(e, ix)
                return obj[s:e]
        if isinstance(obj, dict):
            # explicit content item
            if obj.get("type") == "image_url":
                url = obj.get("image_url", {}).get("url")
                if isinstance(url, str) and url.startswith("data:image"):
                    return url
                if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                    return url
                if isinstance(url, str) and "data:image/" in url:
                    return _find_data_or_http_image_in_obj(url)
            # direct url or image_url nesting
            url = obj.get("url") or obj.get("image_url")
            if isinstance(url, str) and url.startswith("data:image/"):
                return url
            if isinstance(url, dict):
                inner = url.get("url")
                if isinstance(inner, str) and inner.startswith("data:image/"):
                    return inner
            for v in obj.values():
                found = _find_data_or_http_image_in_obj(v)
                if found:
                    return found
        if isinstance(obj, list):
            for it in obj:
                found = _find_data_or_http_image_in_obj(it)
                if found:
                    return found
    except Exception:
        return None
    return None


def extract_image_data_url_from_response(resp: Union[dict, object]) -> Optional[str]:
    """Extract a data URL from either OpenAI SDK object or HTTP JSON dict."""
    # Normalize to dict when possible
    if hasattr(resp, "choices"):
        choices = resp.choices
        if not choices:
            return None
        choice = choices[0]
        msg = choice.message
        content = getattr(msg, "content", None)
        # 1) images array (OpenRouter extension)
        images = getattr(msg, "images", None)
        if images and len(images) > 0:
            first = images[0]
            if hasattr(first, "image_url") and hasattr(first.image_url, "url"):
                url = first.image_url.url
                if isinstance(url, str):
                    if url.startswith("data:"):
                        return url
                    if url.startswith("http://") or url.startswith("https://"):
                        try:
                            resp = requests.get(url, timeout=30)
                            mime = resp.headers.get("content-type", "image/png")
                            return bytes_to_data_url(resp.content, mime=mime)
                        except Exception:
                            return None
                    if "data:image/" in url:
                        return _find_data_image_in_obj(url)
        # 2) content list items
        if isinstance(content, list):
            candidate = _find_data_or_http_image_in_obj(content)
            if candidate:
                if isinstance(candidate, str) and (candidate.startswith("http://") or candidate.startswith("https://")):
                    try:
                        resp2 = requests.get(candidate, timeout=30)
                        mime2 = resp2.headers.get("content-type", "image/png")
                        return bytes_to_data_url(resp2.content, mime=mime2)
                    except Exception:
                        return None
                return candidate
        # 3) fallback to plain content string
        if isinstance(content, str):
            if content.startswith("data:"):
                return content
            if content.startswith("http://") or content.startswith("https://"):
                try:
                    resp2 = requests.get(content, timeout=30)
                    mime2 = resp2.headers.get("content-type", "image/png")
                    return bytes_to_data_url(resp2.content, mime=mime2)
                except Exception:
                    pass
            deep = _find_data_or_http_image_in_obj(content)
            if deep:
                if isinstance(deep, str) and (deep.startswith("http://") or deep.startswith("https://")):
                    try:
                        r3 = requests.get(deep, timeout=30)
                        mime3 = r3.headers.get("content-type", "image/png")
                        return bytes_to_data_url(r3.content, mime=mime3)
                    except Exception:
                        return None
                return deep
        # Final attempt: convert SDK object to dict and reuse dict path
        try:
            if hasattr(resp, "model_dump"):
                dct = resp.model_dump()  # type: ignore[attr-defined]
                return extract_image_data_url_from_response(dct)
        except Exception:
            pass
        return None
    elif isinstance(resp, dict):
        choices = resp.get("choices", [])
        if not choices:
            return None
        msg = choices[0].get("message", {})
        # 1) images array
        images = msg.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            url = None
            if isinstance(first, dict):
                url = first.get("image_url", {}).get("url")
            if isinstance(url, str):
                if url.startswith("data:"):
                    return url
                if url.startswith("http://") or url.startswith("https://"):
                    try:
                        r = requests.get(url, timeout=30)
                        mime = r.headers.get("content-type", "image/png")
                        return bytes_to_data_url(r.content, mime=mime)
                    except Exception:
                        pass
                if "data:image/" in url:
                    deep = _find_data_image_in_obj(url)
                    if deep:
                        return deep
        # 2) content list
        content = msg.get("content")
        candidate = _find_data_or_http_image_in_obj(content)
        if candidate:
            if isinstance(candidate, str) and (candidate.startswith("http://") or candidate.startswith("https://")):
                try:
                    r2 = requests.get(candidate, timeout=30)
                    mime2 = r2.headers.get("content-type", "image/png")
                    return bytes_to_data_url(r2.content, mime=mime2)
                except Exception:
                    return None
            return candidate
        # 3) deep scan of entire response as last resort
        deep2 = _find_data_or_http_image_in_obj(resp)
        if isinstance(deep2, str) and (deep2.startswith("http://") or deep2.startswith("https://")):
            try:
                r4 = requests.get(deep2, timeout=30)
                mime4 = r4.headers.get("content-type", "image/png")
                return bytes_to_data_url(r4.content, mime=mime4)
            except Exception:
                return None
        return deep2
    else:
        return None


def generate_image(client: OpenAI, cfg: V2Config, style_image_data_url: str, shot_text: str, on_log: Optional[Callable[[str], None]] = None) -> str:
    messages = build_image_messages(style_image_data_url, shot_text)
    headers = {
        "HTTP-Referer": os.getenv("V2_HTTP_REFERER", "http://localhost"),
        "X-Title": os.getenv("V2_APP_TITLE", "Project Maestro v2"),
    }
    if on_log:
        on_log(f"Images: calling {cfg.image_model}…")
    resp = None
    try:
        resp = with_backoff(
            lambda: client.chat.completions.create(
                model=cfg.image_model,
                messages=messages,
                extra_headers=headers,
                extra_body={"modalities": ["image", "text"]},
                stream=False,
                timeout=cfg.request_timeout_sec,
            ),
            on_log=on_log,
        )
    except Exception:
        if on_log:
            on_log("Images: OpenAI client failed; falling back to HTTP requests…")
        resp = with_backoff(
            lambda: chat_completions(
                api_key=cfg.openrouter_api_key,
                model=cfg.image_model,
                messages=messages,
                timeout_sec=cfg.request_timeout_sec,
                extra_body={"modalities": ["image", "text"], "stream": False},
                extra_headers=headers,
            ),
            on_log=on_log,
        )
    data_url = extract_image_data_url_from_response(resp)
    if not data_url:
        raise RuntimeError("No image returned by provider")
    if on_log:
        try:
            on_log(f"Images: received image data url length={len(data_url)}")
        except Exception:
            pass
    return data_url


def generate_images_concurrently(
    client: OpenAI,
    cfg: V2Config,
    style_image_data_url: str,
    shot_id_to_text: Dict[int, str],
    on_progress: Optional[Callable[[int, Optional[str], Optional[Exception]], None]] = None,
) -> Dict[int, GenerationResult]:
    results: Dict[int, GenerationResult] = {}
    lock = threading.Lock()
    start = time.time()

    def task(shot_id: int, text: str) -> None:
        try:
            if on_progress:
                on_progress(shot_id, None, None)
            img_url = generate_image(client, cfg, style_image_data_url, text, on_progress if on_progress else None)
            with lock:
                results[shot_id] = GenerationResult(
                    shot_id=shot_id,
                    image_data_url=img_url,
                    created_at=time.time(),
                )
            if on_progress:
                on_progress(shot_id, img_url, None)
        except Exception as e:  # noqa: BLE001
            if on_progress:
                on_progress(shot_id, None, e)

    # Limit to one at a time per new requirement
    for sid, text in shot_id_to_text.items():
        if not text.strip():
            continue
        task(sid, text)
    return results


