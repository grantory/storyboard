from __future__ import annotations

from typing import Callable, List, Optional
import os

from openai import OpenAI

from src.config import V2Config
from src.services import with_backoff
from src.services.openrouter_http import chat_completions


CONTEXT_SYSTEM_PROMPT = (
    "You are a concise film analyst. You will receive a small set of evenly spaced frames from a short video. "
    "Infer what the scene is about in 3–5 short sentences. Mention setting, subject/action, and "
    "emotional tone without over-describing. Keep it brief and evocative."
)


def build_context_messages(frame_data_urls: List[str], instructions: str = CONTEXT_SYSTEM_PROMPT):
    content: List[dict] = [{"type": "text", "text": instructions}]
    for url in frame_data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return [{"role": "user", "content": content}]


def fetch_context_paragraph(
    client: OpenAI,
    cfg: V2Config,
    frame_data_urls: List[str],
    on_log: Optional[Callable[[str], None]] = None,
) -> str:
    headers = {
        "HTTP-Referer": os.getenv("V2_HTTP_REFERER", "http://localhost"),
        "X-Title": os.getenv("V2_APP_TITLE", "Project Maestro v2"),
    }
    messages = build_context_messages(frame_data_urls)
    # Log approximate payload size to help diagnose connection resets
    if on_log:
        total_bytes = sum(len(url) for url in frame_data_urls)
        on_log(f"Context: payload size ~{total_bytes/1024:.1f} KB across {len(frame_data_urls)} frames")
    try:
        if on_log:
            on_log(f"Context: calling {cfg.context_model} with {len(frame_data_urls)} frames (timeout {cfg.request_timeout_sec}s)…")
        try:
            resp = with_backoff(
                lambda: client.chat.completions.create(
                    model=cfg.context_model,
                    messages=messages,
                    extra_headers=headers,
                    extra_body={"modalities": ["image", "text"]},
                    timeout=cfg.request_timeout_sec,
                ),
                on_log=on_log,
            )
        except Exception:
            # HTTP fallback
            if on_log:
                on_log("Context: OpenAI client failed; falling back to HTTP requests…")
            resp = with_backoff(
                lambda: chat_completions(
                    api_key=cfg.openrouter_api_key,
                    model=cfg.context_model,
                    messages=messages,
                    timeout_sec=cfg.request_timeout_sec,
                    extra_body={"modalities": ["image", "text"]},
                    extra_headers=headers,
                ),
                on_log=on_log,
            )
    except Exception as e:
        # Fallback to a vision-capable model if the default model rejects images
        if on_log:
            on_log(f"Context: primary model failed with error: {str(e)}; retrying with {cfg.context_vision_model} (vision)…")
        try:
            resp = with_backoff(
                lambda: client.chat.completions.create(
                    model=cfg.context_vision_model,
                    messages=messages,
                    extra_headers=headers,
                    extra_body={"modalities": ["image", "text"]},
                    timeout=cfg.request_timeout_sec,
                ),
                on_log=on_log,
            )
        except Exception:
            if on_log:
                on_log("Context: OpenAI client failed; falling back to HTTP requests (vision)…")
            resp = with_backoff(
                lambda: chat_completions(
                    api_key=cfg.openrouter_api_key,
                    model=cfg.context_vision_model,
                    messages=messages,
                    timeout_sec=cfg.request_timeout_sec,
                    extra_body={"modalities": ["image", "text"]},
                    extra_headers=headers,
                ),
                on_log=on_log,
            )
    # Support both OpenAI client object and HTTP JSON dict
    text = ""
    if resp is not None:
        if hasattr(resp, "choices"):
            text = (resp.choices[0].message.content or "") if resp.choices else ""
        elif isinstance(resp, dict):
            choices = resp.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                text = msg.get("content", "") or ""
    if on_log:
        on_log(f"Context: received {len(text)} characters")
    return text.strip() or ""


