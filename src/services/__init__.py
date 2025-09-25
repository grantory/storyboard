import time
from typing import Callable, Optional, Tuple

import requests


def connectivity_probe(url: str = "https://openrouter.ai/api/v1", timeout_sec: int = 5) -> tuple[bool, str]:
    try:
        resp = requests.get(url, timeout=timeout_sec)
        return (resp.ok, f"HTTP {resp.status_code}")
    except Exception as e:  # noqa: BLE001
        return (False, str(e))


def with_backoff(
    func: Callable[[], any],
    *,
    retries: int = 2,
    base_delay: float = 0.8,
    on_log: Optional[Callable[[str], None]] = None,
):
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt == retries:
                break
            delay = base_delay * (2 ** attempt)
            if on_log:
                on_log(f"Retrying after error: {e} (sleep {delay:.1f}s)…")
            time.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError("with_backoff: exhausted retries")


def openrouter_models_probe(api_key: str, timeout_sec: int = 8) -> Tuple[bool, str]:
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_sec,
        )
        if resp.ok:
            return True, f"HTTP {resp.status_code}, {len(resp.json().get('data', []))} models"
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def openrouter_chat_probe(api_key: str, model: str, timeout_sec: int = 12) -> Tuple[bool, str]:
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "ping"}]}],
        }
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "Project Maestro v2",
            },
            json=payload,
            timeout=timeout_sec,
        )
        if resp.ok:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)



