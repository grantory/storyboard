from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment
load_dotenv()

from src.config import load_config  # noqa: E402
from src.gui.pipeline import Pipeline  # noqa: E402
from src.gui.state import AppState  # noqa: E402
from src.types import Shot  # noqa: E402
from src.services import connectivity_probe  # noqa: E402
from src.services.storage import (  # noqa: E402
    compress_image_bytes_to_jpeg_data_url,
    data_url_to_bytes_and_mime,
)
from src.services.video import (  # noqa: E402
    sample_middle_frame_as_data_url,
    estimate_context_frame_count,
    sample_context_frames_as_data_urls,
)


# Fixed thumbnail widths for minimal, stable layout
SIDEBAR_THUMB_WIDTH = 180
SHOT_THUMB_WIDTH = 280


# --------------------------
# Page configuration & Styles
# --------------------------
st.set_page_config(
    page_title="Project Maestro v2",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.25rem 1rem; border-radius: 10px; margin-bottom: 1.25rem; text-align: center; }
  .main-header h1 { margin: 0; font-size: 2.25rem; font-weight: 700; }
  .status-indicator { padding: 0.35rem 0.75rem; border-radius: 16px; font-size: 0.85rem; font-weight: 600; display: inline-block; }
  .status-ok { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
  .status-fail { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
  .log-container { background: #2d3748; color: #e2e8f0; border-radius: 8px; padding: 0.75rem; font-family: 'Monaco','Menlo','Ubuntu Mono',monospace; font-size: 0.85rem; max-height: 320px; overflow-y: auto; }
  .log-container { font-size: 0.75rem; }
  .hint { color: #6b7280; font-size: 0.85rem; }
  .soft { background: rgba(102,126,234,0.05); border: 1px solid rgba(102,126,234,0.15); border-radius: 10px; padding: 0.75rem; }
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------
# Session State & Utilities
# --------------------------
def _log(message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {message}"
    st.session_state.logs.append(entry)


def _init_session() -> None:
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.cfg = load_config()
        st.session_state.logs = []  # type: List[str]
        st.session_state.app_state = AppState(cfg=st.session_state.cfg)
        st.session_state.pipeline = Pipeline(st.session_state.cfg, on_log=_log)

        # Files & bytes
        st.session_state.video_file = None
        st.session_state.video_bytes = None  # type: Optional[bytes]
        st.session_state.style_file = None
        st.session_state.style_data_url = ""

        # Analysis
        st.session_state.context_text = ""
        st.session_state.middle_frame_data_url = None  # type: Optional[str]

        # Shots & results
        st.session_state.shots = []  # type: List[Shot]
        st.session_state.shot_count = 5
        st.session_state.results = {}  # type: Dict[int, str]
        st.session_state.errors = {}  # type: Dict[int, str]
        st.session_state.upscaled = {}  # type: Dict[int, bytes]
        st.session_state.in_progress = {}  # type: Dict[int, bool]

        # Progress
        st.session_state.current_operation = None
        st.session_state.batch_progress = None


def _header() -> None:
    st.markdown(
        """
        <div class="main-header">
            <h1>🎬 Project Maestro v2</h1>
            <p>Transform your videos into stunning storyboards with AI-powered analysis</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------
# Sidebar: Files & Actions
# --------------------------
def _sidebar() -> None:
    st.subheader("🔗 Connection")
    cfg = st.session_state.cfg
    if not cfg.openrouter_api_key:
        st.error("OPENROUTER_API_KEY is missing. Add it to your environment or .env.")
    else:
        ok, msg = connectivity_probe()
        klass = "status-ok" if ok else "status-fail"
        label = "✅ Connected" if ok else "❌ Disconnected"
        st.markdown(f'<div class="status-indicator {klass}">{label}</div>', unsafe_allow_html=True)
        if not ok:
            st.caption(f"Error: {msg}")

    st.divider()

    st.subheader("📁 Files")
    video_file = st.file_uploader("Video (mp4, ≤30s)", type=["mp4"], key="video_uploader", help="Upload a short clip (≤30s). We'll extract representative frames.")
    if video_file is not None:
        st.session_state.video_file = video_file
        try:
            video_file.seek(0)
        except Exception:
            pass
        st.session_state.video_bytes = video_file.read()
        # Preview
        try:
            if st.session_state.video_bytes:
                preview = sample_middle_frame_as_data_url(st.session_state.video_bytes)
                st.image(preview, caption="Video Preview", width=SIDEBAR_THUMB_WIDTH)
        except Exception as e:  # noqa: BLE001
            st.caption(f"Preview unavailable: {e}")

    style_file = st.file_uploader("Style Image (png/jpg)", type=["png", "jpg", "jpeg"], key="style_uploader", help="Reference image to drive the visual style of generated frames.")
    if style_file is not None:
        st.session_state.style_file = style_file
        try:
            style_file.seek(0)
        except Exception:
            pass
        try:
            st.session_state.style_data_url = compress_image_bytes_to_jpeg_data_url(style_file.read(), max_width=1024, quality=85)
            st.image(st.session_state.style_data_url, caption="Style Preview", width=SIDEBAR_THUMB_WIDTH)
        except Exception as e:  # noqa: BLE001
            st.caption(f"Style preview unavailable: {e}")

    st.divider()

    st.subheader("⚙️ Settings")
    st.session_state.shot_count = st.selectbox(
        "Number of Shots",
        options=list(range(3, 11)),
        index=st.session_state.get("shot_count", 5) - 3,
        help="Select how many shots to generate",
    )

    col_reset, col_clear = st.columns(2)
    with col_reset:
        if st.button("♻️ Reset App", use_container_width=True, help="Clear session state and restart the app."):
            _reset_app()
    with col_clear:
        if st.button("🧹 Clear Results", use_container_width=True, help="Remove generated shots and images."):
            _clear_results()


# --------------------------
# Main Content
# --------------------------
def _main_content() -> None:
    # Top toolbar for primary actions
    st.markdown("**Quick Actions**")
    col_a1, col_a2, col_a3 = st.columns([1, 1, 1])
    cfg = st.session_state.cfg
    analyze_disabled = not (st.session_state.video_bytes and st.session_state.style_data_url and cfg.openrouter_api_key)
    with col_a1:
        st.button("🔍 Analyze", type="primary", disabled=analyze_disabled, use_container_width=True, help="Run context analysis", on_click=_analyze_video)
    with col_a2:
        shots_ready = bool(st.session_state.get("context_text"))
        st.button("🎭 Generate Shots", disabled=not shots_ready, use_container_width=True, help="Create shot descriptions", on_click=_generate_shots)
    with col_a3:
        all_ready = bool(st.session_state.get("shots")) and bool(st.session_state.get("style_data_url"))
        st.button("🎨 Generate All", disabled=not all_ready, use_container_width=True, help="Render all shot images", on_click=_generate_all_shots)

    st.subheader("📝 Context Analysis")
    context_text = st.text_area(
        "AI-Generated Scene Description",
        value=st.session_state.get("context_text", ""),
        height=180,
        key="context_textarea",
        help="This is the AI's understanding of your video content",
    )
    if context_text != st.session_state.get("context_text", ""):
        st.session_state.context_text = context_text
    with st.expander("Tips to improve context", expanded=False):
        st.markdown("- Be concise but specific about characters, actions, and mood.\n- Include camera angle and lighting cues for better framing.\n- Remove irrelevant details to focus the model.")
    if not context_text:
        st.caption("Context will appear here after analysis")

    st.divider()

    st.subheader("🎬 Generated Shots")
    shots: List[Shot] = st.session_state.get("shots", [])
    if not shots:
        st.info("No shots yet. Run analysis and generate shots.")
        return

    for shot in shots:
        _render_shot_card(shot)


def _render_shot_card(shot: Shot) -> None:
    with st.expander(f"Shot {shot.id}", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            new_text = st.text_area(
                f"Description for Shot {shot.id}",
                value=shot.text,
                height=100,
                key=f"shot_text_{shot.id}",
            )
            if new_text != shot.text:
                shot.text = new_text
                st.session_state.shots = [s if s.id != shot.id else shot for s in st.session_state.shots]

        with col2:
            disabled = not st.session_state.get("style_data_url") or st.session_state.in_progress.get(shot.id, False)
            if st.button("Generate", key=f"gen_{shot.id}", disabled=disabled, use_container_width=True, help="Render this shot using the style image"):
                _generate_shot_image(shot.id, new_text)

        with col3:
            if shot.id in st.session_state.results:
                url = st.session_state.results[shot.id]
                st.image(url, caption=f"Shot {shot.id}", use_container_width=True)
                _render_downloads(shot.id, url)
            elif shot.id in st.session_state.errors:
                st.error(f"❌ {st.session_state.errors[shot.id]}")
            elif st.session_state.in_progress.get(shot.id, False):
                st.info("🔄 Generating…")
            else:
                st.caption("Image will appear here")


def _render_downloads(shot_id: int, url: str) -> None:
    try:
        data_bytes, mime = data_url_to_bytes_and_mime(url)
        st.download_button(
            label="💾 Download Original",
            data=data_bytes,
            file_name=f"shot_{shot_id:03d}.png",
            mime=mime or "image/png",
            key=f"dl_orig_{shot_id}",
            use_container_width=True,
        )

        if shot_id in st.session_state.upscaled:
            st.download_button(
                label="📥 Download Upscaled (2x)",
                data=st.session_state.upscaled[shot_id],
                file_name=f"shot_{shot_id:03d}_upscaled.png",
                mime="image/png",
                key=f"dl_up_{shot_id}",
                use_container_width=True,
            )
        else:
            if st.button("⚡ Upscale (2x)", key=f"upscale_{shot_id}", use_container_width=True, help="Use Real-ESRGAN to upscale the generated image"):
                _upscale_shot(shot_id, data_bytes)
    except Exception as e:  # noqa: BLE001
        st.caption(f"⚠️ Downloads unavailable: {e}")


# --------------------------
# Right Panel: Progress & Logs
# --------------------------
def _right_panel() -> None:
    st.subheader("📊 Progress")
    if st.session_state.get("current_operation"):
        st.info(f"🔄 {st.session_state.current_operation}")
    else:
        st.caption("Idle")

    st.subheader("📋 Activity Log")
    logs: List[str] = st.session_state.get("logs", [])
    if logs:
        st.markdown("<div class=\"log-container\">" + "<br>".join(logs[-40:]) + "</div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.logs = []
    else:
        st.caption("No activity yet")


# --------------------------
# Actions
# --------------------------
def _analyze_video() -> None:
    if not st.session_state.video_bytes or not st.session_state.style_data_url:
        st.error("Please upload both video and style image first")
        return

    try:
        st.session_state.current_operation = "Analyzing video…"
        progress = st.progress(0)
        status = st.empty()

        # Step 1: Frames
        status.text("📹 Extracting frames…")
        progress.progress(10)
        video_bytes = st.session_state.video_bytes
        n_frames = estimate_context_frame_count(video_bytes, seconds_per_frame=2.0, min_frames=1)
        _log(f"📊 Estimated {n_frames} frames")
        frame_urls = sample_context_frames_as_data_urls(video_bytes, n=n_frames)
        middle = sample_middle_frame_as_data_url(video_bytes)
        progress.progress(50)

        # Step 2: Context
        status.text("🧠 Analyzing scene context…")
        context_text, middle_frame = st.session_state.pipeline.analyze_context(video_bytes)
        st.session_state.context_text = context_text
        st.session_state.middle_frame_data_url = middle_frame or middle
        progress.progress(100)
        status.text("✅ Analysis complete!")
        time.sleep(0.5)
        progress.empty()
        status.empty()
        st.session_state.current_operation = None
        st.success("🎉 Analysis complete! Context ready for shot generation.")
    except Exception as e:  # noqa: BLE001
        _log(f"❌ Analysis failed: {e}")
        st.error(f"Analysis failed: {e}")
        st.session_state.current_operation = None


def _reset_app() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_session()
    st.success("App reset.")


def _clear_results() -> None:
    st.session_state.results = {}
    st.session_state.errors = {}
    st.session_state.upscaled = {}
    st.session_state.shots = []
    st.success("Cleared generated content.")


def _generate_shots() -> None:
    if not st.session_state.get("context_text"):
        st.error("Please run analysis first")
        return
    try:
        st.session_state.current_operation = "Generating shots…"
        with st.spinner("Generating shots…"):
            shots = st.session_state.pipeline.generate_shots_from_context(
                st.session_state.middle_frame_data_url or "",
                st.session_state.context_text,
                shot_count=st.session_state.shot_count,
            )
        st.session_state.shots = shots
        st.session_state.results = {}
        st.session_state.errors = {}
        st.session_state.in_progress = {}
        st.session_state.current_operation = None
        _log(f"✅ Generated {len(shots)} shots")
        st.success(f"🎬 Generated {len(shots)} shots!")
    except Exception as e:  # noqa: BLE001
        _log(f"❌ Shot generation failed: {e}")
        st.error(f"Shot generation failed: {e}")
        st.session_state.current_operation = None


def _generate_shot_image(shot_id: int, shot_text: str) -> None:
    if not st.session_state.get("style_data_url"):
        st.error("Please upload a style image first")
        return
    try:
        st.session_state.in_progress[shot_id] = True
        with st.spinner(f"Generating image for shot {shot_id}…"):
            url = st.session_state.pipeline.generate_one(st.session_state.style_data_url, shot_text)
        st.session_state.results[shot_id] = url
        st.session_state.errors.pop(shot_id, None)
        st.session_state.in_progress[shot_id] = False
        _log(f"✅ Shot {shot_id} generated")
        st.success(f"✅ Shot {shot_id} generated!")
    except Exception as e:  # noqa: BLE001
        st.session_state.errors[shot_id] = str(e)
        st.session_state.in_progress[shot_id] = False
        _log(f"❌ Shot {shot_id} generation failed: {e}")
        st.error(f"❌ Failed to generate shot {shot_id}: {e}")


def _generate_all_shots() -> None:
    shots: List[Shot] = st.session_state.get("shots", [])
    if not shots:
        st.error("No shots available")
        return
    if not st.session_state.get("style_data_url"):
        st.error("Please upload a style image first")
        return
    try:
        total = len(shots)
        st.session_state.current_operation = f"Generating {total} shots…"
        progress = st.progress(0)
        status = st.empty()
        for i, shot in enumerate(shots):
            status.text(f"Generating shot {shot.id} ({i+1}/{total})")
            try:
                url = st.session_state.pipeline.generate_one(st.session_state.style_data_url, shot.text)
                st.session_state.results[shot.id] = url
                st.session_state.errors.pop(shot.id, None)
            except Exception as e:  # noqa: BLE001
                st.session_state.errors[shot.id] = str(e)
                _log(f"❌ Shot {shot.id} failed: {e}")
            progress.progress((i + 1) / total)
        status.text("✅ All shots generated!")
        time.sleep(0.5)
        progress.empty()
        status.empty()
        st.session_state.current_operation = None
        _log(f"✅ Batch generated: {total} shots")
        st.success(f"🎉 Generated {total} shots!")
    except Exception as e:  # noqa: BLE001
        st.error(f"Batch generation failed: {e}")
        _log(f"❌ Batch generation failed: {e}")
        st.session_state.current_operation = None


def _upscale_shot(shot_id: int, original_bytes: bytes) -> None:
    try:
        with st.spinner("Upscaling with Real-ESRGAN…"):
            from src.services.upscaler import get_upscaler

            upscaler = get_upscaler()
            up_bytes = upscaler.upscale_from_bytes(original_bytes, outscale=2.0, output_format="PNG")
            st.session_state.upscaled[shot_id] = up_bytes
            _log(f"✅ Shot {shot_id} upscaled")
            st.success("Upscaled image ready for download!")
            st.rerun()
    except Exception as e:  # noqa: BLE001
        _log(f"❌ Upscaling failed for shot {shot_id}: {e}")
        st.error(f"Upscaling failed: {e}")


# --------------------------
# Entry Point
# --------------------------
def main() -> None:
    _init_session()
    _header()

    # Narrow left and right columns; widen center for main content
    col1, col2, col3 = st.columns([0.9, 2.8, 0.7])
    with col1:
        _sidebar()
    with col2:
        _main_content()
    with col3:
        _right_panel()


if __name__ == "__main__":
    main()


