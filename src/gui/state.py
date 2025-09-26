from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Dict, List, Optional

from src.config import V2Config
from src.types import Shot


@dataclass
class AppState:
    video_path: Optional[str] = None
    video_bytes: Optional[bytes] = None

    style_path: Optional[str] = None
    style_data_url: str = ""

    context_text: str = ""
    middle_frame_data_url: Optional[str] = None
    shots: List[Shot] = field(default_factory=list)

    # User-configurable number of shots to generate
    shot_count: int = 5

    results: Dict[int, str] = field(default_factory=dict)
    errors: Dict[int, str] = field(default_factory=dict)
    upscaled: Dict[int, bytes] = field(default_factory=dict)
    saved_paths: Dict[int, str] = field(default_factory=dict)
    in_progress: Dict[int, bool] = field(default_factory=dict)

    logs: List[str] = field(default_factory=list)

    cfg: Optional[V2Config] = None
    cancel_event: Event = field(default_factory=Event)


