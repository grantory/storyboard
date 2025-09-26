from __future__ import annotations

from threading import Event
from typing import Callable, List, Optional, Tuple

from src.config import V2Config, create_openrouter_client, load_config
from src.services.context import fetch_context_paragraph
from src.services.director import fetch_director_shots
from src.services.images import generate_image
from src.services.storage import compress_image_bytes_to_jpeg_data_url
from src.services.video import (
    estimate_context_frame_count,
    sample_context_frames_as_data_urls,
    sample_middle_frame_as_data_url,
)
from src.types import Shot


class Pipeline:
    """Thin, GUI-oriented wrapper over existing service functions.

    Responsibilities:
    - Own `cfg` and OpenAI client lifecycle
    - Provide cancellation checkpoints for long-running steps
    - Centralize logging through an injected callback
    """

    def __init__(self, cfg: Optional[V2Config] = None, on_log: Optional[Callable[[str], None]] = None) -> None:
        self.on_log: Callable[[str], None] = on_log or (lambda _msg: None)
        self.on_log("🔧 Initializing Pipeline...")

        self.cfg: V2Config = cfg or load_config()
        self.on_log(f"📋 Loaded configuration: context_model={self.cfg.context_model}, director_model={self.cfg.director_model}")

        self.client = create_openrouter_client(self.cfg.openrouter_api_key) if self.cfg.openrouter_api_key else None
        if self.client:
            self.on_log("🔗 OpenRouter client initialized successfully")
        else:
            self.on_log("⚠️  OpenRouter client not initialized (no API key)")
        self.on_log("✅ Pipeline initialization complete")

    def set_logger(self, on_log: Optional[Callable[[str], None]]) -> None:
        old_logger = self.on_log
        self.on_log = on_log or (lambda _msg: None)
        if old_logger != self.on_log:
            self.on_log("📝 Logger callback updated")

    def reload_config(self, cfg: V2Config) -> None:
        self.on_log("🔄 Reloading pipeline configuration...")
        self.cfg = cfg
        self.on_log(f"📋 New configuration: context_model={self.cfg.context_model}, director_model={self.cfg.director_model}")
        old_client = self.client
        self.client = create_openrouter_client(self.cfg.openrouter_api_key) if self.cfg.openrouter_api_key else None
        if self.client and not old_client:
            self.on_log("🔗 OpenRouter client initialized")
        elif not self.client and old_client:
            self.on_log("⚠️  OpenRouter client disabled (no API key)")
        self.on_log("✅ Configuration reload complete")

    # ---------- Helpers ----------
    def build_style_preview(self, style_bytes: bytes, *, max_width: int = 320, quality: int = 70) -> str:
        self.on_log(f"🖼️  Building style preview (max_width={max_width}, quality={quality})...")
        result = compress_image_bytes_to_jpeg_data_url(style_bytes, max_width=max_width, quality=quality)
        self.on_log("✅ Style preview built successfully")
        return result

    # ---------- High level flows ----------
    def analyze(self, video_bytes: bytes, cancel: Optional[Event] = None) -> Tuple[str, List[Shot]]:
        """Legacy: Run full pipeline and return (context_text, shots)."""
        self.on_log("🎬 Starting video analysis pipeline...")
        cancel = cancel or Event()

        if cancel.is_set():
            self.on_log("❌ Analysis cancelled before starting")
            return "", []

        # Step 1: Frame count estimation
        self.on_log("📊 Estimating optimal frame count for context analysis...")
        try:
            n_frames = estimate_context_frame_count(video_bytes, seconds_per_frame=2.0, min_frames=1)
            self.on_log(f"📈 Estimated {n_frames} frames needed (2s per frame, min 1)")
        except Exception as e:
            self.on_log(f"❌ Frame count estimation failed: {e}")
            return "", []

        if cancel.is_set():
            self.on_log("❌ Analysis cancelled after frame estimation")
            return "", []

        # Step 2: Sample context frames
        self.on_log(f"🎥 Sampling {n_frames} evenly spaced frames for context...")
        try:
            frame_urls = sample_context_frames_as_data_urls(video_bytes, n=n_frames)
            self.on_log(f"✅ Sampled {len(frame_urls)} context frames successfully")
        except Exception as e:
            self.on_log(f"❌ Frame sampling failed: {e}")
            return "", []

        if cancel.is_set():
            self.on_log("❌ Analysis cancelled after frame sampling")
            return "", []

        # Step 3: Sample middle frame
        self.on_log("🎯 Sampling middle frame for director analysis...")
        try:
            middle_url = sample_middle_frame_as_data_url(video_bytes)
            self.on_log("✅ Middle frame sampled successfully")
        except Exception as e:
            self.on_log(f"❌ Middle frame sampling failed: {e}")
            return "", []

        if cancel.is_set():
            self.on_log("❌ Analysis cancelled after middle frame sampling")
            return "", []

        # Step 4: Fetch context
        self.on_log(f"🧠 Context analysis: calling {self.cfg.context_model}...")
        try:
            context_text = fetch_context_paragraph(self.client, self.cfg, frame_urls, on_log=self.on_log)
            context_length = len(context_text) if context_text else 0
            self.on_log(f"✅ Context analysis complete ({context_length} characters)")
        except Exception as e:
            self.on_log(f"❌ Context analysis failed: {e}")
            return "", []

        if cancel.is_set():
            self.on_log("❌ Analysis cancelled after context analysis")
            return "", []

        # Step 5: Fetch director shots
        self.on_log(f"🎬 Director analysis: calling {self.cfg.director_model}...")
        try:
            shots = fetch_director_shots(self.client, self.cfg, middle_url, context_text, on_log=self.on_log)
            self.on_log(f"✅ Director analysis complete ({len(shots)} shots generated)")
        except Exception as e:
            self.on_log(f"❌ Director analysis failed: {e}")
            return "", []

        self.on_log("🎉 Analysis pipeline completed successfully")
        return context_text, shots

    # --- New split flow ---
    def analyze_context(self, video_bytes: bytes, cancel: Optional[Event] = None) -> Tuple[str, str]:
        """Return (context_text, middle_frame_data_url) without generating shots."""
        self.on_log("🎬 Starting context-only analysis...")
        cancel = cancel or Event()

        # Frame steps
        try:
            n_frames = estimate_context_frame_count(video_bytes, seconds_per_frame=2.0, min_frames=1)
            frame_urls = sample_context_frames_as_data_urls(video_bytes, n=n_frames)
            middle_url = sample_middle_frame_as_data_url(video_bytes)
        except Exception as e:
            self.on_log(f"❌ Context pre-processing failed: {e}")
            return "", ""

        # Fetch context
        try:
            context_text = fetch_context_paragraph(self.client, self.cfg, frame_urls, on_log=self.on_log)
        except Exception as e:
            self.on_log(f"❌ Context analysis failed: {e}")
            return "", middle_url

        self.on_log("✅ Context-only analysis complete")
        return context_text, middle_url

    def generate_shots_from_context(self, middle_frame_data_url: str, context_text: str, cancel: Optional[Event] = None, *, shot_count: int = 5) -> List[Shot]:
        """Generate shots using user-edited context and a middle frame."""
        self.on_log("🎬 Generating shots from edited context...")
        try:
            shots = fetch_director_shots(self.client, self.cfg, middle_frame_data_url, context_text, on_log=self.on_log, shot_count=shot_count)
            self.on_log(f"✅ Director analysis complete ({len(shots)} shots generated)")
            return shots
        except Exception as e:
            self.on_log(f"❌ Director analysis failed: {e}")
            raise

    def generate_one(self, style_data_url: str, shot_text: str) -> str:
        shot_preview = shot_text[:50] + "..." if len(shot_text) > 50 else shot_text
        self.on_log(f"🎨 Starting image generation for shot: '{shot_preview}'")
        try:
            result = generate_image(self.client, self.cfg, style_data_url, shot_text, on_log=self.on_log)
            self.on_log("✅ Image generation completed successfully")
            return result
        except Exception as e:
            self.on_log(f"❌ Image generation failed: {e}")
            raise


