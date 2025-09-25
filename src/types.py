from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ContextSummary:
    setting: str
    main_action: str
    emotional_tone: List[str]
    summary: str


@dataclass
class Shot:
    id: int
    text: str


@dataclass
class GenerationResult:
    shot_id: int
    image_data_url: str
    created_at: float


