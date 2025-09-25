from __future__ import annotations

import os
import time
from typing import Dict, List

import streamlit as st
import sys
from dotenv import load_dotenv
import logging

# Ensure v2 folder is on sys.path so we can import "src.*" without touching v1
V2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if V2_DIR not in sys.path:
    sys.path.insert(0, V2_DIR)

# Load environment strictly from v2/.env
ENV_PATH = os.path.join(V2_DIR, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

from src.config import create_openrouter_client, load_config
from src.services.context import fetch_context_paragraph
from src.services.director import fetch_director_shots
from src.services.images import generate_images_concurrently, generate_image
from src.services.storage import bytes_to_data_url, save_data_url_png, compress_image_bytes_to_jpeg_data_url, data_url_to_bytes_and_mime
from src.services.video import sample_context_frames_as_data_urls, sample_middle_frame_as_data_url, estimate_context_frame_count
from src.types import Shot
from src.services import connectivity_probe, openrouter_models_probe, openrouter_chat_probe

# Enhanced page configuration
st.set_page_config(
    page_title="Project Maestro v2",
    layout="centered",
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .status-indicator {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-ok {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-fail {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .shot-container {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    .shot-container:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    .shot-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-weight: 600;
        font-size: 1.1rem;
    }
    .sidebar-header {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .progress-container {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .log-container {
        background: #2d3748;
        color: #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
    }
    .main-content {
        padding: 1rem 0;
    }
    .sidebar-content {
        padding: 0.5rem 0;
    }
    .footer-info {
        text-align: center;
        margin-top: 2rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        border-top: 3px solid #667eea;
    }
    .expander-header {
        font-weight: 600;
        color: #495057;
    }
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #2196f3;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }

    /* Responsive design improvements */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        .main-header p {
            font-size: 1rem;
        }
        .footer-info .grid {
            grid-template-columns: 1fr;
        }
        .shot-container {
            margin: 0.25rem 0;
        }
        /* Stack columns on mobile */
        .mobile-stack {
            flex-direction: column !important;
        }
        .mobile-stack > div {
            margin-bottom: 1rem;
        }
    }

    @media (max-width: 480px) {
        .main-header {
            padding: 1rem 0.5rem;
            margin-bottom: 1rem;
        }
        .main-header h1 {
            font-size: 1.5rem;
        }
        .sidebar-header {
            padding: 0.75rem;
        }
        .shot-header {
            font-size: 1rem;
            padding: 0.5rem;
        }
        /* Make buttons full width on very small screens */
        .mobile-full-width {
            width: 100% !important;
        }
    }

    /* Better spacing for containers */
    .content-container {
        margin-bottom: 1.5rem;
    }

    /* Improved button hover effects */
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Better focus states for accessibility */
    .stTextArea textarea:focus,
    .stButton button:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }

    /* Centered page container */
    .page-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 0 1rem 2rem;
    }

    /* Subtle section wrapper to improve UX without heavy frames */
    .section-block {
        background: rgba(102, 126, 234, 0.05);
        border: 1px solid rgba(102, 126, 234, 0.15);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* Constrain Streamlit's main content width */
    .block-container {
        max-width: 800px;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Widen the sidebar (container and inner content) */
    section[data-testid="stSidebar"] {
        width: 360px !important;
        min-width: 360px !important;
        max-width: 360px !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 360px !important;
    }
</style>
""", unsafe_allow_html=True)

# Enhanced title section
st.markdown("""
<div class="main-header">
    <h1>🎬 Project Maestro v2</h1>
    <p>Transform your videos into stunning storyboards with AI-powered analysis</p>
</div>
""", unsafe_allow_html=True)

logging.basicConfig(level=logging.INFO, format="[v2] %(asctime)s %(levelname)s: %(message)s")


if "shots" not in st.session_state:
    st.session_state["shots"] = []  # type: List[Shot]
if "context_paragraph" not in st.session_state:
    st.session_state["context_paragraph"] = ""
if "results" not in st.session_state:
    st.session_state["results"] = {}  # type: Dict[int, str]
if "errors" not in st.session_state:
    st.session_state["errors"] = {}  # type: Dict[int, str]
if "logs" not in st.session_state:
    st.session_state["logs"] = []  # type: List[str]
if "in_progress" not in st.session_state:
    st.session_state["in_progress"] = {}  # type: Dict[int, bool]
if "style_data_url" not in st.session_state:
    st.session_state["style_data_url"] = ""
if "upscaled" not in st.session_state:
    st.session_state["upscaled"] = {}  # type: Dict[int, bytes]


cfg = load_config()
client = create_openrouter_client(cfg.openrouter_api_key)


with st.sidebar:

    # Connection status with improved styling
    if not cfg.openrouter_api_key:
        st.error("🔑 OPENROUTER_API_KEY is missing. Set it in v2/.env and restart.")
    else:
        ok, msg = connectivity_probe()
        status_class = "status-ok" if ok else "status-fail"
        status_text = "✅ Connected" if ok else "❌ Disconnected"
        st.markdown(f'<div class="status-indicator {status_class}">{status_text}</div>', unsafe_allow_html=True)
        if not ok:
            st.caption(f"Error: {msg}")

    # Uploaders
    st.markdown("### 📹 Media Files")
    video_file = st.file_uploader(
        "Video File (mp4, ≤30s)",
        type=["mp4"],
        accept_multiple_files=False,
        help="Upload a short video clip (max 30 seconds) for analysis"
    )

    style_image_file = st.file_uploader(
        "Style Image (png/jpg)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=False,
        help="Upload a reference image to define the visual style"
    )

    # Thumbnails preview
    try:
        if video_file is not None:
            # Cache video thumbnail to avoid recompute on every rerun
            if st.session_state.get("_video_thumb_src_name") != getattr(video_file, "name", None):
                try:
                    video_file.seek(0)
                except Exception:
                    pass
                try:
                    st.session_state["video_thumb_data_url"] = sample_middle_frame_as_data_url(video_file.read())
                except Exception:
                    st.session_state["video_thumb_data_url"] = None
                st.session_state["_video_thumb_src_name"] = getattr(video_file, "name", None)

        if style_image_file is not None:
            # Cache style image thumbnail
            if st.session_state.get("_style_thumb_src_name") != getattr(style_image_file, "name", None):
                try:
                    style_image_file.seek(0)
                except Exception:
                    pass
                try:
                    st.session_state["style_thumb_data_url"] = compress_image_bytes_to_jpeg_data_url(style_image_file.read(), max_width=320, quality=70)
                except Exception:
                    st.session_state["style_thumb_data_url"] = None
                st.session_state["_style_thumb_src_name"] = getattr(style_image_file, "name", None)

        if st.session_state.get("video_thumb_data_url") or st.session_state.get("style_thumb_data_url"):
            st.markdown("### 📑 Previews")
        if st.session_state.get("video_thumb_data_url"):
            st.image(st.session_state["video_thumb_data_url"], caption="Video", use_container_width=True)
        if st.session_state.get("style_thumb_data_url"):
            st.image(st.session_state["style_thumb_data_url"], caption="Style Image", use_container_width=True)
    except Exception:
        pass

    # Analyze button
    analyze_disabled = not (video_file and style_image_file)
    if analyze_disabled:
        st.info("💡 Upload both video and style image to enable analysis")

    analyze_btn = st.button(
        "🎬 ANALYZE VIDEO",
        type="primary",
        use_container_width=True,
        disabled=analyze_disabled,
        help="Start AI analysis to create storyboard shots"
    )

    # Help text
    if video_file and style_image_file:
        st.success("✅ Ready to analyze! Click the button above to begin.")
    else:
        st.caption("📋 **Quick Start:** Upload a video and style image, then click ANALYZE to create your storyboard.")


def log_line(msg: str) -> None:
    st.session_state["logs"].append(msg)
    logging.info(msg)


def do_analyze(video_bytes: bytes) -> None:
    # Enhanced progress tracking with better visual feedback
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Frame extraction
        status_text.text("📹 Extracting video frames...")
        progress_bar.progress(10)
        n_frames = estimate_context_frame_count(video_bytes, seconds_per_frame=2.0, min_frames=1)
        msg = f"🔄 Sampling {n_frames} evenly spaced frames for context analysis..."
        log_line(msg)

        try:
            frame_urls = sample_context_frames_as_data_urls(video_bytes, n=n_frames)
            progress_bar.progress(30)
        except Exception as e:  # noqa: BLE001
            msg = f"❌ Frame extraction failed: {e}"
            st.error(msg)
            log_line(msg)
            progress_bar.empty()
            status_text.empty()
            return

        msg = "🔄 Sampling middle frame for director analysis..."
        log_line(msg)
        try:
            middle_url = sample_middle_frame_as_data_url(video_bytes)
            progress_bar.progress(50)
        except Exception as e:  # noqa: BLE001
            msg = f"❌ Middle frame extraction failed: {e}"
            st.error(msg)
            log_line(msg)
            progress_bar.empty()
            status_text.empty()
            return

        # Step 2: Context analysis
        status_text.text("🧠 Analyzing scene context...")
        progress_bar.progress(60)
        msg = f"🤖 Context Analysis: Using {cfg.context_model} with vision fallback..."
        log_line(msg)

        try:
            context_text = fetch_context_paragraph(client, cfg, frame_urls, on_log=log_line)
            progress_bar.progress(80)
        except Exception as e:  # noqa: BLE001
            msg = f"❌ Context analysis failed: {e}"
            st.error(msg)
            log_line(msg)
            progress_bar.empty()
            status_text.empty()
            return

        # Step 3: Director analysis
        status_text.text("🎬 Generating storyboard shots...")
        progress_bar.progress(90)
        msg = f"🎯 Director Analysis: Using {cfg.director_model} with vision fallback..."
        log_line(msg)

        try:
            shots = fetch_director_shots(client, cfg, middle_url, context_text, on_log=log_line)
            progress_bar.progress(100)
        except Exception as e:  # noqa: BLE001
            msg = f"❌ Director analysis failed: {e}"
            st.error(msg)
            log_line(msg)
            progress_bar.empty()
            status_text.empty()
            return

        # Success completion
        status_text.text("✅ Analysis complete! Ready to generate images.")
        st.session_state["context_paragraph"] = context_text
        st.session_state["shots"] = shots
        st.session_state["results"] = {}
        st.session_state["errors"] = {}

        # Clear progress indicators after a delay
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

        st.success("🎉 Analysis complete! Your storyboard shots are ready below.")
        st.balloons()

    except Exception as e:  # noqa: BLE001
        msg = f"💥 Unexpected error during analysis: {e}"
        st.error(msg)
        log_line(msg)
        progress_bar.empty()
        status_text.empty()


st.markdown('<div class="page-container">', unsafe_allow_html=True)

# Context section (top)
st.markdown('<div class="section-block">', unsafe_allow_html=True)
st.subheader("📝 Context Analysis")

# Analysis trigger
if analyze_btn and video_file is not None:
    with st.container():
        try:
            video_file.seek(0)
        except Exception:
            pass
        do_analyze(video_file.read())

# Context display
context_text = st.text_area(
    "AI-Generated Scene Description",
    key="context_paragraph",
    height=200,
    help="This is the AI's understanding of your video content"
)

if not context_text:
    st.caption("Context will appear here after analysis")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Storyboard section (below)
st.markdown('<div class="section-block">', unsafe_allow_html=True)
st.subheader("🎬 Storyboard Shots")

shots: List[Shot] = st.session_state.get("shots", [])
if not shots:
    st.info("📤 Upload your media files and click ANALYZE to generate storyboard shots.")
else:
    # Persist style image in session to avoid read-pointer issues
    if style_image_file is not None:
        try:
            style_image_file.seek(0)
        except Exception:
            pass
        st.session_state["style_data_url"] = compress_image_bytes_to_jpeg_data_url(
            style_image_file.read(),
            max_width=1024,
            quality=85,
        )
    style_data_url: str = st.session_state.get("style_data_url", "")

    edited_texts: Dict[int, str] = {}
    for shot in shots:
        st.markdown(f'**Shot {shot.id}**')

        edited = st.text_area(
            f"Shot {shot.id} Description",
            value=shot.text,
            key=f"shot_text_{shot.id}",
            height=100,
            help=f"Edit this description to customize shot {shot.id}"
        )
        edited_texts[shot.id] = edited

        cols = st.columns([1, 1.2, 0.8])
        with cols[0]:
            gen_disabled = not style_data_url
            if gen_disabled:
                st.warning("⚠️ Please upload a style image first")

            if st.button(
                "Generate Image",
                key=f"gen_{shot.id}",
                disabled=gen_disabled,
                type="secondary",
                use_container_width=True,
                help="Create an AI-generated image for this shot"
            ):
                st.session_state["in_progress"][shot.id] = True
                with st.spinner(f"🎨 Creating shot {shot.id}..."):
                    try:
                        url = generate_image(
                            client,
                            cfg,
                            style_data_url,
                            edited,
                            on_log=log_line,
                        )
                        st.session_state["results"][shot.id] = url
                        st.session_state["errors"].pop(shot.id, None)
                        st.success(f"✅ Shot {shot.id} generated successfully!")
                    except Exception as e:  # noqa: BLE001
                        st.session_state["errors"][shot.id] = str(e)
                        st.error(f"❌ Failed to generate shot {shot.id}")
                st.session_state["in_progress"][shot.id] = False
                st.rerun()

        with cols[1]:
            if st.session_state["in_progress"].get(shot.id):
                st.info("Generating image...")
            elif shot.id in st.session_state["results"]:
                img_url = st.session_state["results"][shot.id]
                st.image(
                    img_url,
                    caption=f"Shot {shot.id}",
                    use_container_width=True,
                    output_format="PNG"
                )
            elif shot.id in st.session_state["errors"]:
                st.error(f"❌ {st.session_state['errors'][shot.id]}")
            else:
                st.caption("Image preview will appear here")

        with cols[2]:
            if shot.id in st.session_state["results"]:
                st.markdown("**Save**")
                try:
                    # Save Original
                    data_bytes, mime = data_url_to_bytes_and_mime(st.session_state["results"][shot.id])
                    st.download_button(
                        label="💾 Save Original (PNG)",
                        data=data_bytes,
                        file_name=f"storyboard_shot_{shot.id:03d}.png",
                        mime=mime,
                        key=f"save_orig_{shot.id}",
                        use_container_width=True,
                        help="Download the generated image as-is"
                    )

                    # Save Upscaled (2x)
                    upscaled_map = st.session_state.get("upscaled", {})
                    upscaled_ready = shot.id in upscaled_map and isinstance(upscaled_map[shot.id], (bytes, bytearray))

                    if not upscaled_ready:
                        if st.button(
                            "⚡ Save Upscaled (2x)",
                            key=f"btn_upscale_{shot.id}",
                            use_container_width=True,
                            help="Upscale with Real-ESRGAN and prepare download"
                        ):
                            with st.spinner("Upscaling with Real-ESRGAN… this may take a moment"):
                                try:
                                    # Lazy import to avoid ImportError unless feature is used
                                    from src.services.upscaler import get_upscaler
                                    upscaler = get_upscaler()
                                    src_bytes, _src_mime = data_url_to_bytes_and_mime(st.session_state["results"][shot.id])
                                    up_bytes = upscaler.upscale_from_bytes(src_bytes, outscale=2.0, output_format="PNG")
                                    st.session_state["upscaled"][shot.id] = up_bytes
                                    upscaled_ready = True
                                    st.success("Upscaled image ready. Click to download.")
                                except Exception as e:  # noqa: BLE001
                                    st.error(f"Upscaling failed: {e}")
                    if upscaled_ready:
                        st.download_button(
                            label="📥 Download Upscaled (2x)",
                            data=st.session_state["upscaled"][shot.id],
                            file_name=f"storyboard_shot_{shot.id:03d}_upscaled.png",
                            mime="image/png",
                            key=f"save_up_{shot.id}",
                            use_container_width=True,
                            help="Download the upscaled image"
                        )
                except Exception as e:
                    st.caption(f"⚠️ Save unavailable: {e}")
            else:
                st.caption("Generate image first")

        st.divider()

st.markdown('</div>', unsafe_allow_html=True)
    # Right column removed: batch ops, system info, logs, tips footer

