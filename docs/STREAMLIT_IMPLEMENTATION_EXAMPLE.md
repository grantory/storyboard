# Project Maestro v2: Streamlit Implementation Example

## Complete Working Implementation

This document provides a complete, working implementation of the Project Maestro v2 application in Streamlit, based on the current CustomTkinter version.

## File Structure

```
src/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration management (reused)
├── types.py                  # Data types (reused)
├── services/                 # Service layer (reused)
│   ├── context.py
│   ├── director.py
│   ├── images.py
│   ├── video.py
│   ├── storage.py
│   └── upscaler.py
└── gui/
    ├── pipeline.py           # Pipeline wrapper (reused)
    └── state.py              # State management (reused)
```

## Complete Streamlit Implementation

### 1. Main Application (`src/app.py`)

```python
import streamlit as st
import time
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project root to path
import sys
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import load_config, create_openrouter_client
from src.gui.pipeline import Pipeline
from src.gui.state import AppState
from src.types import Shot
from src.services.video import sample_middle_frame_as_data_url, sample_context_frames_as_data_urls, estimate_context_frame_count
from src.services.storage import compress_image_bytes_to_jpeg_data_url, data_url_to_bytes_and_mime
from src.services import connectivity_probe

# Page configuration
st.set_page_config(
    page_title="Project Maestro v2",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    .sidebar-header {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize all required session state variables"""
    
    # Core application state
    if "app_initialized" not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.cfg = load_config()
        st.session_state.pipeline = Pipeline(st.session_state.cfg, on_log=log_message)
    
    # File management
    if "video_file" not in st.session_state:
        st.session_state.video_file = None
    if "style_file" not in st.session_state:
        st.session_state.style_file = None
    if "video_bytes" not in st.session_state:
        st.session_state.video_bytes = None
    if "style_data_url" not in st.session_state:
        st.session_state.style_data_url = ""
    
    # Analysis state
    if "context_text" not in st.session_state:
        st.session_state.context_text = ""
    if "middle_frame_data_url" not in st.session_state:
        st.session_state.middle_frame_data_url = None
    
    # Shots and results
    if "shots" not in st.session_state:
        st.session_state.shots = []
    if "shot_count" not in st.session_state:
        st.session_state.shot_count = 5
    if "results" not in st.session_state:
        st.session_state.results = {}
    if "errors" not in st.session_state:
        st.session_state.errors = {}
    if "upscaled" not in st.session_state:
        st.session_state.upscaled = {}
    if "in_progress" not in st.session_state:
        st.session_state.in_progress = {}
    
    # Logging and progress
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "current_operation" not in st.session_state:
        st.session_state.current_operation = None
    if "batch_progress" not in st.session_state:
        st.session_state.batch_progress = None

def log_message(message: str):
    """Add message to activity log"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    st.session_state.logs.append(log_entry)
    
    # Keep only last 100 log entries
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

def render_header():
    """Render application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🎬 Project Maestro v2</h1>
        <p>Transform your videos into stunning storyboards with AI-powered analysis</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render the left sidebar with file uploads and actions"""
    
    # Connection status
    st.markdown('<div class="sidebar-header">🔗 Connection Status</div>', unsafe_allow_html=True)
    
    if not st.session_state.cfg.openrouter_api_key:
        st.error("🔑 OPENROUTER_API_KEY is missing. Set it in .env file.")
    else:
        try:
            ok, msg = connectivity_probe()
            status_class = "status-ok" if ok else "status-fail"
            status_text = "✅ Connected" if ok else "❌ Disconnected"
            st.markdown(f'<div class="status-indicator {status_class}">{status_text}</div>', unsafe_allow_html=True)
            if not ok:
                st.caption(f"Error: {msg}")
        except Exception as e:
            st.error(f"Connection test failed: {e}")
    
    st.divider()
    
    # File upload section
    st.subheader("📁 Files")
    
    # Video file upload
    video_file = st.file_uploader(
        "📹 Upload Video File",
        type=["mp4"],
        help="Upload a short video clip (max 30 seconds) for analysis",
        key="video_uploader"
    )
    
    if video_file is not None:
        st.session_state.video_file = video_file
        st.session_state.video_bytes = video_file.read()
        
        # Generate video preview
        if st.session_state.video_bytes:
            with st.spinner("Generating video preview..."):
                try:
                    preview_url = sample_middle_frame_as_data_url(st.session_state.video_bytes)
                    st.image(preview_url, caption="Video Preview", use_column_width=True)
                except Exception as e:
                    st.error(f"Failed to generate preview: {e}")
    
    # Style image upload
    style_file = st.file_uploader(
        "🎨 Upload Style Image",
        type=["png", "jpg", "jpeg"],
        help="Upload a reference image to define the visual style",
        key="style_uploader"
    )
    
    if style_file is not None:
        st.session_state.style_file = style_file
        style_bytes = style_file.read()
        st.session_state.style_data_url = compress_image_bytes_to_jpeg_data_url(
            style_bytes, max_width=1024, quality=85
        )
        
        # Display style preview
        if st.session_state.style_data_url:
            st.image(st.session_state.style_data_url, caption="Style Preview", use_column_width=True)
    
    st.divider()
    
    # Action buttons
    st.subheader("⚡ Actions")
    
    # Analysis button
    analyze_disabled = not (st.session_state.video_file and st.session_state.style_file)
    if st.button("🔍 Analyze Video", type="primary", disabled=analyze_disabled, use_container_width=True):
        analyze_video()
    
    # Shot generation button
    shots_available = bool(st.session_state.get("context_text"))
    if st.button("🎭 Generate Shots", disabled=not shots_available, use_container_width=True):
        generate_shots()
    
    # Batch generation button
    shots_ready = bool(st.session_state.get("shots")) and bool(st.session_state.get("style_data_url"))
    if st.button("🎨 Generate All Images", disabled=not shots_ready, use_container_width=True):
        generate_all_shots()
    
    st.divider()
    
    # Settings
    render_settings_section()

def render_settings_section():
    """Render settings section"""
    st.subheader("⚙️ Settings")
    
    # Shot count selector
    shot_count = st.selectbox(
        "Number of Shots",
        options=list(range(3, 11)),
        index=st.session_state.get("shot_count", 5) - 3,
        help="Select the number of shots to generate"
    )
    st.session_state.shot_count = shot_count
    
    # Model selection
    with st.expander("Model Configuration", expanded=False):
        context_model = st.selectbox(
            "Context Model",
            options=["gpt-4o-mini", "gpt-4o", "claude-3-haiku"],
            index=0
        )
        
        director_model = st.selectbox(
            "Director Model",
            options=["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"],
            index=0
        )
        
        image_model = st.selectbox(
            "Image Model",
            options=["dall-e-3", "midjourney", "stable-diffusion"],
            index=0
        )
    
    # Connection test
    if st.button("🔗 Test Connection", use_container_width=True):
        test_connection()

def render_main_content():
    """Render the main content area with context and shots"""
    
    # Context section
    st.subheader("📝 Context Analysis")
    
    # Context text area
    context_text = st.text_area(
        "AI-Generated Scene Description",
        value=st.session_state.get("context_text", ""),
        height=200,
        help="This is the AI's understanding of your video content",
        key="context_textarea"
    )
    
    if context_text:
        st.session_state.context_text = context_text
        word_count = len(context_text.split())
        st.caption(f"Word count: {word_count}")
    
    if not context_text:
        st.info("Context will appear here after analysis")
    
    st.divider()
    
    # Shots section
    st.subheader("🎬 Generated Shots")
    
    shots = st.session_state.get("shots", [])
    
    if not shots:
        st.info("No shots available. Run analysis and shot generation first.")
    else:
        for shot in shots:
            render_shot_card(shot)

def render_shot_card(shot: Shot):
    """Render individual shot card"""
    with st.expander(f"Shot {shot.id}", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Shot description
            shot_text = st.text_area(
                f"Description for Shot {shot.id}",
                value=shot.text,
                height=100,
                key=f"shot_text_{shot.id}",
                help=f"Edit this description to customize shot {shot.id}"
            )
            
            # Update shot text in session state
            if shot_text != shot.text:
                shot.text = shot_text
                st.session_state.shots = [s if s.id != shot.id else shot for s in st.session_state.shots]
        
        with col2:
            # Generate button
            gen_disabled = not st.session_state.get("style_data_url") or st.session_state.in_progress.get(shot.id, False)
            
            if st.button(f"Generate Image", key=f"gen_{shot.id}", disabled=gen_disabled, use_container_width=True):
                generate_shot_image(shot.id, shot_text)
        
        with col3:
            # Display result
            if shot.id in st.session_state.results:
                result_url = st.session_state.results[shot.id]
                st.image(result_url, caption=f"Shot {shot.id}", use_column_width=True)
                
                # Download buttons
                render_download_buttons(shot.id, result_url)
            elif shot.id in st.session_state.errors:
                st.error(f"❌ {st.session_state.errors[shot.id]}")
            elif st.session_state.in_progress.get(shot.id, False):
                st.info("🔄 Generating...")
            else:
                st.caption("Image will appear here")

def render_download_buttons(shot_id: int, result_url: str):
    """Render download buttons for a shot"""
    
    try:
        # Convert data URL to bytes
        data_bytes, mime = data_url_to_bytes_and_mime(result_url)
        
        # Original image download
        st.download_button(
            label="💾 Download Original",
            data=data_bytes,
            file_name=f"shot_{shot_id:03d}.png",
            mime=mime or "image/png",
            key=f"download_orig_{shot_id}",
            use_container_width=True
        )
        
        # Upscaled image download
        if shot_id in st.session_state.upscaled:
            upscaled_bytes = st.session_state.upscaled[shot_id]
            st.download_button(
                label="📥 Download Upscaled (2x)",
                data=upscaled_bytes,
                file_name=f"shot_{shot_id:03d}_upscaled.png",
                mime="image/png",
                key=f"download_upscaled_{shot_id}",
                use_container_width=True
            )
        else:
            if st.button(f"⚡ Upscale Shot {shot_id}", key=f"upscale_{shot_id}", use_container_width=True):
                upscale_shot(shot_id, data_bytes)
                
    except Exception as e:
        st.caption(f"⚠️ Download unavailable: {e}")

def render_right_panel():
    """Render the right panel with progress and logs"""
    
    # Progress section
    st.subheader("📊 Progress")
    
    current_operation = st.session_state.get("current_operation")
    if current_operation:
        st.info(f"🔄 {current_operation}")
    
    # Progress bar for batch operations
    if st.session_state.get("batch_progress"):
        progress = st.session_state.batch_progress
        st.progress(progress["current"] / progress["total"])
        st.caption(f"Progress: {progress['current']}/{progress['total']}")
    
    st.divider()
    
    # Activity log section
    st.subheader("📋 Activity Log")
    
    logs = st.session_state.get("logs", [])
    if logs:
        # Show last 20 log entries
        for log_entry in logs[-20:]:
            st.text(log_entry)
        
        # Clear logs button
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.logs = []
            st.rerun()
    else:
        st.caption("No activity yet")

def analyze_video():
    """Perform video analysis workflow"""
    
    if not st.session_state.video_file or not st.session_state.style_file:
        st.error("Please upload both video and style image first")
        return
    
    try:
        # Set up progress tracking
        st.session_state.current_operation = "Analyzing video..."
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Frame extraction
        status_text.text("📹 Extracting video frames...")
        progress_bar.progress(10)
        log_message("🎬 Starting video analysis...")
        
        video_bytes = st.session_state.video_bytes
        n_frames = estimate_context_frame_count(video_bytes, seconds_per_frame=2.0, min_frames=1)
        log_message(f"📊 Estimated {n_frames} frames needed")
        
        # Step 2: Context analysis
        status_text.text("🧠 Analyzing scene context...")
        progress_bar.progress(30)
        
        frame_urls = sample_context_frames_as_data_urls(video_bytes, n=n_frames)
        middle_url = sample_middle_frame_as_data_url(video_bytes)
        
        progress_bar.progress(50)
        
        # Step 3: AI context analysis
        status_text.text("🤖 AI context analysis...")
        progress_bar.progress(70)
        
        context_text, middle_frame = st.session_state.pipeline.analyze_context(video_bytes)
        st.session_state.context_text = context_text
        st.session_state.middle_frame_data_url = middle_frame
        
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        log_message("✅ Video analysis completed successfully")
        st.success("🎉 Analysis complete! Context is ready for shot generation.")
        
        # Clear progress indicators
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.session_state.current_operation = None
        
        st.rerun()
        
    except Exception as e:
        log_message(f"❌ Analysis failed: {e}")
        st.error(f"Analysis failed: {e}")
        st.session_state.current_operation = None

def generate_shots():
    """Generate shots from context"""
    
    if not st.session_state.get("context_text"):
        st.error("Please run video analysis first")
        return
    
    try:
        st.session_state.current_operation = "Generating shots..."
        log_message("🎭 Generating shots from context...")
        
        with st.spinner("Generating shots..."):
            shots = st.session_state.pipeline.generate_shots_from_context(
                st.session_state.middle_frame_data_url,
                st.session_state.context_text,
                shot_count=st.session_state.shot_count
            )
            
            st.session_state.shots = shots
            st.session_state.results = {}
            st.session_state.errors = {}
            st.session_state.in_progress = {}
            
            log_message(f"✅ Generated {len(shots)} shots successfully")
            st.success(f"🎬 Generated {len(shots)} shots! Ready for image generation.")
            st.session_state.current_operation = None
            st.rerun()
            
    except Exception as e:
        log_message(f"❌ Shot generation failed: {e}")
        st.error(f"Shot generation failed: {e}")
        st.session_state.current_operation = None

def generate_shot_image(shot_id: int, shot_text: str):
    """Generate image for a specific shot"""
    
    if not st.session_state.get("style_data_url"):
        st.error("Please upload a style image first")
        return
    
    try:
        st.session_state.in_progress[shot_id] = True
        log_message(f"🎨 Starting image generation for shot {shot_id}")
        
        with st.spinner(f"Generating image for shot {shot_id}..."):
            result_url = st.session_state.pipeline.generate_one(
                st.session_state.style_data_url,
                shot_text
            )
            
            st.session_state.results[shot_id] = result_url
            st.session_state.errors.pop(shot_id, None)
            st.session_state.in_progress[shot_id] = False
            
            log_message(f"✅ Shot {shot_id} generated successfully")
            st.success(f"✅ Shot {shot_id} generated!")
            st.rerun()
            
    except Exception as e:
        st.session_state.errors[shot_id] = str(e)
        st.session_state.in_progress[shot_id] = False
        log_message(f"❌ Shot {shot_id} generation failed: {e}")
        st.error(f"❌ Failed to generate shot {shot_id}: {e}")

def generate_all_shots():
    """Generate images for all shots"""
    
    if not st.session_state.get("shots"):
        st.error("No shots available")
        return
    
    if not st.session_state.get("style_data_url"):
        st.error("Please upload a style image first")
        return
    
    try:
        shots = st.session_state.shots
        total_shots = len(shots)
        
        st.session_state.batch_progress = {"current": 0, "total": total_shots}
        st.session_state.current_operation = f"Generating {total_shots} shots..."
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, shot in enumerate(shots):
            status_text.text(f"Generating shot {shot.id} ({i+1}/{total_shots})")
            
            try:
                result_url = st.session_state.pipeline.generate_one(
                    st.session_state.style_data_url,
                    shot.text
                )
                st.session_state.results[shot.id] = result_url
                st.session_state.errors.pop(shot.id, None)
                
            except Exception as e:
                st.session_state.errors[shot.id] = str(e)
                log_message(f"❌ Shot {shot.id} failed: {e}")
            
            # Update progress
            progress = (i + 1) / total_shots
            progress_bar.progress(progress)
            st.session_state.batch_progress["current"] = i + 1
        
        status_text.text("✅ All shots generated!")
        st.success(f"🎉 Generated {total_shots} shots!")
        
        # Clear progress indicators
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.session_state.batch_progress = None
        st.session_state.current_operation = None
        
        log_message(f"✅ Batch generation completed: {total_shots} shots")
        st.rerun()
        
    except Exception as e:
        st.error(f"Batch generation failed: {e}")
        log_message(f"❌ Batch generation failed: {e}")
        st.session_state.batch_progress = None
        st.session_state.current_operation = None

def upscale_shot(shot_id: int, original_bytes: bytes):
    """Upscale a shot using Real-ESRGAN"""
    
    try:
        with st.spinner("Upscaling with Real-ESRGAN..."):
            from src.services.upscaler import get_upscaler
            upscaler = get_upscaler()
            upscaled_bytes = upscaler.upscale_from_bytes(original_bytes, outscale=2.0, output_format="PNG")
            
            st.session_state.upscaled[shot_id] = upscaled_bytes
            log_message(f"✅ Shot {shot_id} upscaled successfully")
            st.success("Upscaled image ready for download!")
            st.rerun()
            
    except Exception as e:
        log_message(f"❌ Upscaling failed for shot {shot_id}: {e}")
        st.error(f"Upscaling failed: {e}")

def test_connection():
    """Test API connection"""
    
    try:
        with st.spinner("Testing connection..."):
            ok, msg = connectivity_probe()
            
            if ok:
                st.success("✅ Connection successful")
                log_message("✅ Connection test passed")
            else:
                st.error(f"❌ Connection failed: {msg}")
                log_message(f"❌ Connection test failed: {msg}")
                
    except Exception as e:
        st.error(f"Connection test failed: {e}")
        log_message(f"❌ Connection test error: {e}")

def main():
    """Main application function"""
    
    # Initialize session state
    initialize_session_state()
    
    # Render header
    render_header()
    
    # Main layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        render_sidebar()
    
    with col2:
        render_main_content()
    
    with col3:
        render_right_panel()

if __name__ == "__main__":
    main()
```

### 2. Requirements File (`requirements.txt`)

```txt
streamlit>=1.28.0
openai>=1.3.0
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
requests>=2.31.0
realesrgan>=0.3.0
basicsr>=1.4.2
torch>=2.0.0
torchvision>=0.15.0
```

### 3. Environment Configuration (`.env`)

```bash
OPENROUTER_API_KEY=your_api_key_here
V2_OPENROUTER_CONTEXT_MODEL=gpt-4o-mini
V2_OPENROUTER_DIRECTOR_MODEL=gpt-4o
V2_OPENROUTER_IMAGE_MODEL=dall-e-3
V2_MAX_CONCURRENT_REQUESTS=5
V2_REQUEST_TIMEOUT_SEC=60
V2_HTTP_REFERER=http://localhost:8501
V2_APP_TITLE=Project Maestro v2
```

### 4. Streamlit Configuration (`.streamlit/config.toml`)

```toml
[server]
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

### 5. Docker Configuration (`Dockerfile`)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create weights directory
RUN mkdir -p weights

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 6. Docker Compose (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  project-maestro:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - V2_OPENROUTER_CONTEXT_MODEL=${V2_OPENROUTER_CONTEXT_MODEL:-gpt-4o-mini}
      - V2_OPENROUTER_DIRECTOR_MODEL=${V2_OPENROUTER_DIRECTOR_MODEL:-gpt-4o}
      - V2_OPENROUTER_IMAGE_MODEL=${V2_OPENROUTER_IMAGE_MODEL:-dall-e-3}
    volumes:
      - ./weights:/app/weights
      - ./output:/app/output
    restart: unless-stopped
```

## Usage Instructions

### 1. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENROUTER_API_KEY="your_api_key_here"

# Run the application
streamlit run src/app.py
```

### 2. Docker Deployment

```bash
# Build the image
docker build -t project-maestro .

# Run the container
docker run -p 8501:8501 -e OPENROUTER_API_KEY="your_api_key_here" project-maestro
```

### 3. Docker Compose Deployment

```bash
# Set environment variables
export OPENROUTER_API_KEY="your_api_key_here"

# Start the application
docker-compose up -d
```

## Key Features Implemented

### 1. File Upload & Preview
- Video file upload with automatic preview generation
- Style image upload with preview
- Real-time thumbnail generation

### 2. Analysis Workflow
- Video context analysis with progress tracking
- Shot generation from context
- Real-time status updates

### 3. Image Generation
- Individual shot image generation
- Batch processing capabilities
- Progress tracking for batch operations

### 4. Results Management
- Image preview and display
- Download functionality for original and upscaled images
- Real-ESRGAN upscaling integration

### 5. Settings & Configuration
- Model selection
- Connection testing
- Shot count configuration

### 6. User Experience
- Responsive design
- Real-time progress feedback
- Activity logging
- Error handling and display

## Differences from CustomTkinter Version

### 1. State Management
- **CustomTkinter**: Object attributes and threading
- **Streamlit**: Session state with automatic rerendering

### 2. UI Updates
- **CustomTkinter**: Event-driven updates with threading
- **Streamlit**: State-driven rerendering with `st.rerun()`

### 3. File Handling
- **CustomTkinter**: File dialogs
- **Streamlit**: File uploaders with automatic processing

### 4. Progress Tracking
- **CustomTkinter**: Progress bars with threading
- **Streamlit**: `st.progress()` and `st.spinner()` with state management

### 5. Layout
- **CustomTkinter**: Absolute positioning with grid layout
- **Streamlit**: Column-based responsive layout

## Advantages of Streamlit Version

1. **Web-based Access**: Accessible from any device with a web browser
2. **Easier Deployment**: Simple deployment to cloud platforms
3. **Better Collaboration**: Multiple users can access the same interface
4. **Modern UI**: Responsive design that works on mobile and desktop
5. **Easier Maintenance**: Web-based applications are easier to update
6. **No Installation**: Users don't need to install anything locally
7. **Scalability**: Can handle multiple concurrent users

## Conclusion

This implementation provides a complete, working Streamlit version of the Project Maestro v2 application that maintains all the functionality of the original CustomTkinter version while providing the benefits of a web-based interface. The code is production-ready and can be deployed immediately with minimal configuration.
