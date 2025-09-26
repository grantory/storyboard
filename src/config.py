import os
from dataclasses import dataclass
from typing import Optional, Dict

from openai import OpenAI

# Local desktop app - no Streamlit dependencies
_SECRETS = {}

def _get_secret_or_env(key: str, default: str = "") -> str:
    # Local desktop app - use environment variables only
    return str(os.getenv(key, default))


@dataclass(frozen=True)
class V2Config:
    openrouter_api_key: str
    context_model: str
    context_vision_model: str
    director_model: str
    director_vision_model: str
    image_model: str
    max_concurrent_requests: int
    request_timeout_sec: int


def load_config() -> V2Config:
    # Accept broader env names and fall back to V2_* where present
    api_key = _get_secret_or_env("OPENROUTER_API_KEY", "")
    context_model = _get_secret_or_env("V2_OPENROUTER_CONTEXT_MODEL") or _get_secret_or_env("OPENROUTER_VIDEO_MODEL", "gpt-5-mini")
    director_model = _get_secret_or_env("V2_OPENROUTER_DIRECTOR_MODEL", "openai/gpt-5")
    image_model = _get_secret_or_env("V2_OPENROUTER_IMAGE_MODEL") or _get_secret_or_env("OPENROUTER_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
    max_conc = int(_get_secret_or_env("V2_MAX_CONCURRENT_REQUESTS") or _get_secret_or_env("MAX_CONCURRENT_REQUESTS", "5"))
    timeout_sec = int(_get_secret_or_env("V2_REQUEST_TIMEOUT_SEC") or _get_secret_or_env("REQUEST_TIMEOUT_SECONDS", "60"))

    return V2Config(
        openrouter_api_key=api_key,
        context_model=context_model,
        context_vision_model=_get_secret_or_env("V2_OPENROUTER_CONTEXT_VISION_MODEL", "openai/gpt-4o-mini"),
        director_model=director_model,
        director_vision_model=_get_secret_or_env("V2_OPENROUTER_DIRECTOR_VISION_MODEL", "openai/gpt-4o-mini"),
        image_model=image_model,
        max_concurrent_requests=max_conc,
        request_timeout_sec=timeout_sec,
    )


def create_openrouter_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key or _get_secret_or_env("OPENROUTER_API_KEY", "")
    # OpenRouter recommends sending HTTP-Referer and X-Title
    default_headers: Dict[str, str] = {
        "HTTP-Referer": _get_secret_or_env("V2_HTTP_REFERER", "http://localhost"),
        "X-Title": _get_secret_or_env("V2_APP_TITLE", "Project Maestro v2"),
    }
    client = OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=default_headers,
    )
    return client


