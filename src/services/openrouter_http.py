from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


def chat_completions(
    *,
    api_key: str,
    model: str,
    messages: list,
    timeout_sec: int,
    extra_body: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Call OpenRouter /chat/completions via requests.

    Returns parsed JSON dict. Raises requests.HTTPError on non-2xx.
    """
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("V2_HTTP_REFERER", "http://localhost"),
        "X-Title": os.getenv("V2_APP_TITLE", "Project Maestro v2"),
    }
    if extra_headers:
        headers.update(extra_headers)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if extra_body:
        # Merge additional parameters (e.g., modalities) into the top-level payload
        # while avoiding overwriting required fields.
        for k, v in extra_body.items():
            if k not in ("model", "messages"):
                payload[k] = v

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout_sec,
    )
    if not resp.ok:
        try:
            detail = resp.text[:500]
        except Exception:  # noqa: BLE001
            detail = "<no body>"
        resp.raise_for_status()
    return resp.json()


