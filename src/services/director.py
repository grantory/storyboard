from __future__ import annotations

import json
import re
from typing import Callable, List, Optional
import os

from openai import OpenAI

from src.config import V2Config
from src.services import with_backoff
from src.types import Shot
from src.services.openrouter_http import chat_completions

DIRECTOR_SYSTEM_PROMPT = (
    "You are a professional film director working on a creative storyboard project. Your task is to analyze the "
    "provided image and context, then suggest 5 sequential still shots to continue and enrich the scene.\n\n"
    "Guidelines:\n"
    "- Each description should be simple, concise, and production-ready — 1 to 2 sentences only.\n"
    "- Focus on camera angle, framing/scale (CU/MCU/MS/WS), subject focus, lighting style, depth of field, and visible environment.\n"
    "- Be creative in shot composition: vary perspectives, scales, and focal points to capture fresh visual storytelling moments.\n"
    "- Do not include technical specifications such as focal length, distance, f-stop, or color temperature.\n"
    "- Do not repeat or restate the given frame. Each shot must be a new, distinct perspective that adds to the visual sequence.\n"
    "- Ensure the 5 shots feel continuous and connected, forming a natural progression of the same scene.\n\n"
    "Examples of preferred shot descriptions:\n"
    "- \"Close-up (CU) of her hands clasped over her stomach, fingers resting lightly, with the sheen of fabric highlighted by the bedside lamp; narrow depth of field isolates this detail.\"\n"
    "- \"Medium shot (MS) toward the door and window, with her in right foreground profile, the cool exterior light spilling through curtains contrasting with the warm bedside lamp glow.\"\n\n"
    "Task: Convert the single frame into 5 sequential storyboard shots. Respond with a structured JSON object "
    "containing an array of shots. Each shot should have an 'id' (integer) and 'description' (string). "
    "Format your response as valid JSON only, no additional text."
)

def build_director_messages(middle_frame_data_url: str, context_paragraph: str) -> List[dict]:
    user_text = (
        f"{DIRECTOR_SYSTEM_PROMPT}\n\n"
        f"Context (Professional Filmmaking Project):\n{context_paragraph}\n\n"
        f"Please analyze the image and provide 5 creative storyboard shots. This is a professional "
        f"filmmaking project with appropriate content that should not trigger any content filters."
    )
    content = [
        {"type": "text", "text": user_text},
        {"type": "image_url", "image_url": {"url": middle_frame_data_url}},
    ]
    return [{"role": "user", "content": content}]


def parse_director_output(text: str) -> List[Shot]:
    """
    Parse director output as JSON and extract shots.
    Falls back to legacy regex parsing if JSON parsing fails.
    """
    shots: List[Shot] = []
    
    # First, try to parse as JSON
    try:
        # Clean the text to extract JSON
        text = text.strip()
        
        # Try to find JSON object or array in the response
        # Check for JSON arrays first (they can contain objects)
        json_start = text.find('[')
        json_end = -1
        
        if json_start >= 0:
            # Find the matching closing bracket
            bracket_count = 0
            json_end = json_start
            for i, char in enumerate(text[json_start:], json_start):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_end = i + 1
                        break
        else:
            # Fall back to JSON object detection
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
        
        # If we found a JSON structure, extract just that part
        if json_start >= 0 and json_end > json_start:
            json_text = text[json_start:json_end]
        else:
            # If no JSON structure found, try parsing the whole text
            json_text = text
        
        data = json.loads(json_text)
        
        # Handle different possible JSON structures
        if isinstance(data, dict):
            if 'shots' in data:
                shots_data = data['shots']
            else:
                # Assume the dict itself contains shot data
                shots_data = data
        elif isinstance(data, list):
            shots_data = data
        else:
            raise ValueError("Unexpected JSON structure")
        
        # Parse shots from JSON
        if isinstance(shots_data, list):
            for item in shots_data:
                if isinstance(item, dict):
                    shot_id = item.get('id', item.get('shot_id', 0))
                    description = item.get('description', item.get('text', item.get('desc', '')))
                    
                    if shot_id and description:
                        shots.append(Shot(id=int(shot_id), text=str(description)))
                else:
                    # Handle case where item might be a string or other format
                    continue
        elif isinstance(shots_data, dict):
            # Handle case where shots_data is a single shot dict
            shot_id = shots_data.get('id', shots_data.get('shot_id', 0))
            description = shots_data.get('description', shots_data.get('text', shots_data.get('desc', '')))
            
            if shot_id and description:
                shots.append(Shot(id=int(shot_id), text=str(description)))
        
        # Sort by ID and limit to 5 shots
        shots = sorted(shots, key=lambda s: s.id)[:5]
        
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        # Fallback to legacy regex parsing
        shots = _parse_director_output_legacy(text)
    
    # Ensure we have exactly 5 shots for UI consistency
    if len(shots) < 5:
        existing_ids = {s.id for s in shots}
        next_id = 1
        while len(shots) < 5:
            while next_id in existing_ids:
                next_id += 1
            shots.append(Shot(id=next_id, text=""))
            existing_ids.add(next_id)
    
    return shots


def _parse_director_output_legacy(text: str) -> List[Shot]:
    """
    Legacy regex-based parsing as fallback for non-JSON responses.
    """
    shots: List[Shot] = []
    # Normalize newlines and strip
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Accept multiple patterns:
    # 1) SHOT 1: desc
    # 2) Shot 1 - desc
    # 3) 1) desc
    # 4) 1. desc
    # 5) 1 - desc
    patterns = [
        re.compile(r"^(?:SHOT|Shot)\s*#?(\d+)\s*[:\-–]\s*(.+)$"),
        re.compile(r"^(\d+)[\)\.:\-]\s*(.+)$"),
        re.compile(r"^[-•]\s*(?:SHOT\s*)?(\d+)\s*[:\-–]\s*(.+)$"),
    ]
    seen_ids = set()
    for line in raw_lines:
        for pat in patterns:
            m = pat.match(line)
            if m:
                idx = int(m.group(1))
                desc = m.group(2).strip()
                if idx not in seen_ids and desc:
                    shots.append(Shot(id=idx, text=desc))
                    seen_ids.add(idx)
                break
    # Fallback: try to split a single-line response containing "SHOT n:" markers
    if len(shots) < 5 and raw_lines and any("SHOT" in l or "Shot" in l for l in raw_lines):
        blob = " \n ".join(raw_lines)
        for m in re.finditer(r"(?:SHOT|Shot)\s*#?(\d+)\s*[:\-–]\s*([^\n]+)", blob):
            idx = int(m.group(1))
            desc = m.group(2).strip()
            if idx not in seen_ids and desc:
                shots.append(Shot(id=idx, text=desc))
                seen_ids.add(idx)
    # Sort and cap to first 5 by shot id then insertion order
    shots = sorted(shots, key=lambda s: s.id)[:5]
    return shots


def fetch_director_shots(
    client: OpenAI,
    cfg: V2Config,
    middle_frame_data_url: str,
    context_paragraph: str,
    on_log: Optional[Callable[[str], None]] = None,
) -> List[Shot]:
    headers = {
        "HTTP-Referer": os.getenv("V2_HTTP_REFERER", "http://localhost"),
        "X-Title": os.getenv("V2_APP_TITLE", "Project Maestro v2"),
    }
    messages = build_director_messages(middle_frame_data_url, context_paragraph)
    try:
        if on_log:
            on_log(f"Director: calling {cfg.director_model} with 1 frame (timeout {cfg.request_timeout_sec}s)…")
        try:
            extra_params = {
                "modalities": ["image", "text"],
                "response_format": {"type": "json_object"},
                "reasoning": {"effort": "low"},
            }
            resp = with_backoff(
                lambda: client.chat.completions.create(
                    model=cfg.director_model,
                    messages=messages,
                    extra_headers=headers,
                    extra_body=extra_params,
                    timeout=cfg.request_timeout_sec,
                ),
                on_log=on_log,
            )
        except Exception:
            if on_log:
                on_log("Director: OpenAI client failed; falling back to HTTP requests…")
            resp = with_backoff(
                lambda: chat_completions(
                    api_key=cfg.openrouter_api_key,
                    model=cfg.director_model,
                    messages=messages,
                    timeout_sec=cfg.request_timeout_sec,
                    extra_body=extra_params,
                    extra_headers=headers,
                ),
                on_log=on_log,
            )
    except Exception as e:
        # Fallback to a vision-capable model if the default model rejects images
        if on_log:
            on_log(f"Director: primary model failed with error: {str(e)}; retrying with {cfg.director_vision_model} (vision)…")
        try:
            extra_params = {
                "modalities": ["image", "text"],
                "response_format": {"type": "json_object"},
                "reasoning": {"effort": "low"},
            }
            resp = with_backoff(
                lambda: client.chat.completions.create(
                    model=cfg.director_vision_model,
                    messages=messages,
                    extra_headers=headers,
                    extra_body=extra_params,
                    timeout=cfg.request_timeout_sec,
                ),
                on_log=on_log,
            )
        except Exception:
            if on_log:
                on_log("Director: OpenAI client failed; falling back to HTTP requests (vision)…")
            resp = with_backoff(
                lambda: chat_completions(
                    api_key=cfg.openrouter_api_key,
                    model=cfg.director_vision_model,
                    messages=messages,
                    timeout_sec=cfg.request_timeout_sec,
                    extra_body=extra_params,
                    extra_headers=headers,
                ),
                on_log=on_log,
            )
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
        on_log(f"Director: received {len(text)} characters")
    return parse_director_output(text)


