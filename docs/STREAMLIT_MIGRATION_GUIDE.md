# Project Maestro v2: CustomTkinter to Streamlit Migration Guide

## Overview

This document provides a comprehensive guide for reimplementing the Project Maestro v2 AI Storyboard Generator from CustomTkinter to Streamlit. The current implementation is a desktop application with a sophisticated GUI, and this guide will help you create an equivalent web-based version using Streamlit.

## Current Architecture Analysis

### Core Components

The current CustomTkinter implementation consists of:

1. **Main Application (`src/gui/app.py`)**
   - `MaestroApp` class extending `ctk.CTk`
   - Complex UI layout with sidebar, main content, and right panel
   - Event-driven architecture with threading
   - State management through `AppState` class

2. **State Management (`src/gui/state.py`)**
   - `AppState` dataclass with session data
   - Video/audio file handling
   - Results and error tracking
   - Configuration management

3. **Pipeline Integration (`src/gui/pipeline.py`)**
   - `Pipeline` class wrapping service functions
   - Configuration and client lifecycle management
   - Logging and error handling

4. **UI Utilities (`src/gui/utils_images.py`)**
   - Image processing and display utilities
   - Data URL handling
   - CustomTkinter image conversion

### Key Features to Replicate

1. **File Upload & Preview**
   - Video file selection with preview
   - Style image selection with preview
   - Real-time thumbnail generation

2. **Analysis Workflow**
   - Video context analysis
   - Shot generation from context
   - Progress tracking and status updates

3. **Image Generation**
   - Individual shot image generation
   - Batch processing capabilities
   - Real-time progress feedback

4. **Results Management**
   - Image preview and display
   - Save/download functionality
   - Upscaling with Real-ESRGAN

5. **Settings & Configuration**
   - API key management
   - Model selection
   - Connection testing

## Streamlit Implementation Strategy

### 1. Application Structure

```python
# Main Streamlit app structure
import streamlit as st
from src.config import load_config, create_openrouter_client
from src.gui.pipeline import Pipeline
from src.gui.state import AppState

# Page configuration
st.set_page_config(
    page_title="Project Maestro v2",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded"
)
```

### 2. State Management Migration

**Current CustomTkinter State:**
```python
@dataclass
class AppState:
    video_path: Optional[str] = None
    video_bytes: Optional[bytes] = None
    style_path: Optional[str] = None
    style_data_url: str = ""
    context_text: str = ""
    middle_frame_data_url: Optional[str] = None
    shots: List[Shot] = field(default_factory=list)
    shot_count: int = 5
    results: Dict[int, str] = field(default_factory=dict)
    errors: Dict[int, str] = field(default_factory=dict)
    upscaled: Dict[int, bytes] = field(default_factory=dict)
    saved_paths: Dict[int, str] = field(default_factory=dict)
    in_progress: Dict[int, bool] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    cfg: Optional[V2Config] = None
    cancel_event: Event = field(default_factory=Event)
```

**Streamlit Session State:**
```python
# Initialize session state
if "app_state" not in st.session_state:
    st.session_state.app_state = AppState(cfg=load_config())

# Key session state variables
if "video_file" not in st.session_state:
    st.session_state.video_file = None
if "style_file" not in st.session_state:
    st.session_state.style_file = None
if "shots" not in st.session_state:
    st.session_state.shots = []
if "results" not in st.session_state:
    st.session_state.results = {}
if "in_progress" not in st.session_state:
    st.session_state.in_progress = {}
```

### 3. UI Layout Migration

#### Current CustomTkinter Layout:
```
┌─────────────────────────────────────────────────────────────┐
│ [Sidebar] [Main Content] [Right Panel]                      │
│ ┌─────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│ │ Files  │ │ Context & Analysis │ │ Progress & Logs    │   │
│ │ Actions│ │                     │ │                     │   │
│ │ Preview│ │ Generated Shots     │ │                     │   │
│ └─────────┘ └─────────────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### Streamlit Layout:
```python
# Main layout with columns
col1, col2, col3 = st.columns([1, 2, 1])

with col1:  # Left sidebar
    # File uploads
    # Action buttons
    # Previews

with col2:  # Main content
    # Context analysis
    # Generated shots

with col3:  # Right panel
    # Progress tracking
    # Activity logs
    # Settings
```

### 4. Component-by-Component Migration

#### A. File Upload & Preview

**Current CustomTkinter:**
```python
def _open_video(self) -> None:
    from tkinter.filedialog import askopenfilename
    path = askopenfilename(filetypes=[("Video", "*.mp4")])
    if not path:
        return
    # Process video file
```

**Streamlit Implementation:**
```python
# Video file upload
video_file = st.file_uploader(
    "📹 Upload Video File",
    type=["mp4"],
    help="Upload a short video clip (max 30 seconds) for analysis"
)

# Style image upload
style_file = st.file_uploader(
    "🎨 Upload Style Image",
    type=["png", "jpg", "jpeg"],
    help="Upload a reference image to define the visual style"
)

# Preview generation
if video_file:
    with st.spinner("Generating video preview..."):
        try:
            video_bytes = video_file.read()
            preview_url = sample_middle_frame_as_data_url(video_bytes)
            st.image(preview_url, caption="Video Preview", use_column_width=True)
        except Exception as e:
            st.error(f"Failed to generate preview: {e}")
```

#### B. Analysis Workflow

**Current CustomTkinter:**
```python
def _analyze(self) -> None:
    self._on_log("🎬 Analyzing video for context...")
    # Update UI state
    self.btn_analyze.configure(state="disabled", text="🔄 Analyzing...")
    # Start background thread
    threading.Thread(target=worker, daemon=True).start()
```

**Streamlit Implementation:**
```python
# Analysis button
if st.button("🔍 Analyze Video", type="primary", use_container_width=True):
    if not video_file or not style_file:
        st.error("Please upload both video and style image")
    else:
        with st.spinner("Analyzing video..."):
            try:
                # Process video
                video_bytes = video_file.read()
                context_text, middle_frame = pipeline.analyze_context(video_bytes)
                
                # Update session state
                st.session_state.context_text = context_text
                st.session_state.middle_frame = middle_frame
                
                st.success("Analysis complete!")
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
```

#### C. Shot Generation

**Current CustomTkinter:**
```python
def _generate_shots_from_context(self) -> None:
    # Generate shots using context
    shots = self.pipeline.generate_shots_from_context(
        self.app_state.middle_frame_data_url,
        context_text,
        shot_count=self.app_state.shot_count
    )
    self._render_shots()
```

**Streamlit Implementation:**
```python
# Shot generation
if st.button("🎭 Generate Shots", type="primary"):
    if not st.session_state.get("context_text"):
        st.error("Please run analysis first")
    else:
        with st.spinner("Generating shots..."):
            try:
                shots = pipeline.generate_shots_from_context(
                    st.session_state.middle_frame,
                    st.session_state.context_text,
                    shot_count=st.session_state.get("shot_count", 5)
                )
                st.session_state.shots = shots
                st.success(f"Generated {len(shots)} shots!")
                st.rerun()
            except Exception as e:
                st.error(f"Shot generation failed: {e}")
```

#### D. Image Generation

**Current CustomTkinter:**
```python
def _generate_one(self, shot_id: int, txt_widget: ctk.CTkTextbox) -> None:
    # Update UI state
    widgets = self.shot_widgets.get(shot_id)
    if widgets:
        btn_gen = widgets.get("btn_gen")
        if btn_gen:
            btn_gen.configure(state="disabled", text="⏳ Generating...")
    
    # Start background thread
    threading.Thread(target=worker, daemon=True).start()
```

**Streamlit Implementation:**
```python
# Individual shot image generation
for shot in st.session_state.shots:
    with st.expander(f"Shot {shot.id}", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Shot description
            shot_text = st.text_area(
                f"Description for Shot {shot.id}",
                value=shot.text,
                height=100,
                key=f"shot_text_{shot.id}"
            )
        
        with col2:
            # Generate button
            if st.button(f"Generate Image", key=f"gen_{shot.id}"):
                st.session_state.in_progress[shot.id] = True
                with st.spinner(f"Generating shot {shot.id}..."):
                    try:
                        result_url = pipeline.generate_one(
                            st.session_state.style_data_url,
                            shot_text
                        )
                        st.session_state.results[shot.id] = result_url
                        st.session_state.in_progress[shot.id] = False
                        st.success(f"Shot {shot.id} generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {e}")
                        st.session_state.in_progress[shot.id] = False
        
        with col3:
            # Display result
            if shot.id in st.session_state.results:
                st.image(
                    st.session_state.results[shot.id],
                    caption=f"Shot {shot.id}",
                    use_column_width=True
                )
```

#### E. Progress Tracking & Logging

**Current CustomTkinter:**
```python
def _on_log(self, msg: str) -> None:
    self.app_state.logs.append(msg)
    self.txt_logs.insert("end", msg + os.linesep)
    self.txt_logs.see("end")
    self._set_status(msg)
```

**Streamlit Implementation:**
```python
# Progress tracking
progress_bar = st.progress(0)
status_text = st.empty()

# Logging
if st.session_state.get("logs"):
    with st.expander("📊 Activity Log", expanded=False):
        for log_entry in st.session_state.logs[-20:]:  # Show last 20 entries
            st.text(log_entry)

# Real-time status updates
def update_progress(step: int, total: int, message: str):
    progress_bar.progress(step / total)
    status_text.text(message)
```

#### F. Settings & Configuration

**Current CustomTkinter:**
```python
def _open_settings(self) -> None:
    win = ctk.CTkToplevel(self)
    win.title("Settings")
    # Settings form
```

**Streamlit Implementation:**
```python
# Settings sidebar
with st.sidebar:
    st.subheader("⚙️ Settings")
    
    # API Key
    api_key = st.text_input(
        "OpenRouter API Key",
        value=st.session_state.get("api_key", ""),
        type="password"
    )
    
    # Model selection
    context_model = st.selectbox(
        "Context Model",
        options=["gpt-4o-mini", "gpt-4o", "claude-3-haiku"],
        index=0
    )
    
    # Connection test
    if st.button("Test Connection"):
        with st.spinner("Testing connection..."):
            try:
                ok, msg = connectivity_probe()
                if ok:
                    st.success("✅ Connection successful")
                else:
                    st.error(f"❌ Connection failed: {msg}")
            except Exception as e:
                st.error(f"Test failed: {e}")
```

### 5. Advanced Features Migration

#### A. Real-time Updates

**Current CustomTkinter:**
```python
def _drain_events(self) -> None:
    try:
        while True:
            evt = self.events.get_nowait()
            # Process events
    except queue.Empty:
        pass
    self.after(50, self._drain_events)
```

**Streamlit Implementation:**
```python
# Auto-refresh for real-time updates
if st.session_state.get("auto_refresh", False):
    time.sleep(1)
    st.rerun()

# Manual refresh button
if st.button("🔄 Refresh Status"):
    st.rerun()
```

#### B. Batch Operations

**Current CustomTkinter:**
```python
def _generate_all_shots(self) -> None:
    # Generate all shots at once
    for shot in self.app_state.shots:
        self._generate_one(shot.id, None)
```

**Streamlit Implementation:**
```python
# Batch generation
if st.button("🎭 Generate All Shots", type="primary"):
    if not st.session_state.get("shots"):
        st.error("No shots available")
    else:
        progress_bar = st.progress(0)
        total_shots = len(st.session_state.shots)
        
        for i, shot in enumerate(st.session_state.shots):
            with st.spinner(f"Generating shot {shot.id}..."):
                try:
                    result_url = pipeline.generate_one(
                        st.session_state.style_data_url,
                        shot.text
                    )
                    st.session_state.results[shot.id] = result_url
                    progress_bar.progress((i + 1) / total_shots)
                except Exception as e:
                    st.error(f"Failed to generate shot {shot.id}: {e}")
        
        st.success("All shots generated!")
```

#### C. File Management

**Current CustomTkinter:**
```python
def _save_original(self, shot_id: int) -> None:
    from tkinter.filedialog import asksaveasfilename
    path = asksaveasfilename(defaultextension=".png")
    # Save file
```

**Streamlit Implementation:**
```python
# Download functionality
if shot.id in st.session_state.results:
    result_url = st.session_state.results[shot.id]
    
    # Convert to bytes for download
    data_bytes, mime = data_url_to_bytes_and_mime(result_url)
    
    st.download_button(
        label="💾 Download Original",
        data=data_bytes,
        file_name=f"shot_{shot.id:03d}.png",
        mime=mime,
        key=f"download_{shot.id}"
    )
    
    # Upscaled version
    if st.button(f"⚡ Upscale Shot {shot.id}"):
        with st.spinner("Upscaling with Real-ESRGAN..."):
            try:
                from src.services.upscaler import get_upscaler
                upscaler = get_upscaler()
                upscaled_bytes = upscaler.upscale_from_bytes(data_bytes, outscale=2.0)
                st.session_state.upscaled[shot.id] = upscaled_bytes
                st.success("Upscaled image ready!")
            except Exception as e:
                st.error(f"Upscaling failed: {e}")
```

### 6. Error Handling & User Experience

#### A. Error Display

**Current CustomTkinter:**
```python
def show_toast(self, message: str, *, duration_ms: int = 2500) -> None:
    toast = ctk.CTkToplevel(self)
    # Show toast notification
```

**Streamlit Implementation:**
```python
# Error handling
try:
    # Operation
    st.success("Operation completed successfully!")
except Exception as e:
    st.error(f"Operation failed: {e}")
    st.exception(e)  # Show full traceback in expander

# Toast-like notifications
if st.session_state.get("show_notification"):
    st.info(st.session_state.notification_message)
    st.session_state.show_notification = False
```

#### B. Loading States

**Current CustomTkinter:**
```python
self.progress.start()
self.progress.configure(progress_color="#6366f1")
```

**Streamlit Implementation:**
```python
# Loading states
with st.spinner("Processing..."):
    # Long-running operation
    pass

# Progress bars
progress_bar = st.progress(0)
for i in range(100):
    progress_bar.progress(i + 1)
    time.sleep(0.01)
```

### 7. Performance Optimizations

#### A. Caching

```python
@st.cache_data
def process_video(video_bytes: bytes) -> tuple[str, str]:
    """Cache video processing results"""
    return context_text, middle_frame

@st.cache_data
def generate_shot_image(style_url: str, shot_text: str) -> str:
    """Cache generated images"""
    return result_url
```

#### B. Session State Management

```python
# Efficient session state updates
def update_session_state(key: str, value):
    st.session_state[key] = value
    st.rerun()

# Batch updates
def batch_update_session_state(updates: dict):
    for key, value in updates.items():
        st.session_state[key] = value
    st.rerun()
```

### 8. Deployment Considerations

#### A. Environment Setup

```python
# Environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_CONFIG = {
    "context_model": os.getenv("CONTEXT_MODEL", "gpt-4o-mini"),
    "director_model": os.getenv("DIRECTOR_MODEL", "gpt-4o"),
    "image_model": os.getenv("IMAGE_MODEL", "dall-e-3")
}
```

#### B. Streamlit Configuration

```toml
# .streamlit/config.toml
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
```

### 9. Complete Implementation Example

Here's a complete Streamlit implementation structure:

```python
import streamlit as st
import time
from typing import List, Dict
from src.config import load_config, create_openrouter_client
from src.gui.pipeline import Pipeline
from src.gui.state import AppState
from src.types import Shot

# Page configuration
st.set_page_config(
    page_title="Project Maestro v2",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState(cfg=load_config())
    if "shots" not in st.session_state:
        st.session_state.shots = []
    if "results" not in st.session_state:
        st.session_state.results = {}
    if "in_progress" not in st.session_state:
        st.session_state.in_progress = {}

# Main application
def main():
    init_session_state()
    
    # Header
    st.title("🎬 Project Maestro v2")
    st.markdown("Transform your videos into stunning storyboards with AI")
    
    # Layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:  # Left sidebar
        render_sidebar()
    
    with col2:  # Main content
        render_main_content()
    
    with col3:  # Right panel
        render_right_panel()

def render_sidebar():
    st.subheader("📁 Files")
    
    # File uploads
    video_file = st.file_uploader("Video", type=["mp4"])
    style_file = st.file_uploader("Style Image", type=["png", "jpg", "jpeg"])
    
    # Previews
    if video_file:
        st.image(video_file, caption="Video Preview")
    if style_file:
        st.image(style_file, caption="Style Preview")
    
    # Actions
    st.subheader("⚡ Actions")
    
    if st.button("🔍 Analyze Video", type="primary"):
        analyze_video(video_file, style_file)
    
    if st.button("🎭 Generate Shots"):
        generate_shots()

def render_main_content():
    # Context section
    st.subheader("📝 Context Analysis")
    context_text = st.text_area(
        "AI-Generated Scene Description",
        value=st.session_state.get("context_text", ""),
        height=200
    )
    
    # Shots section
    st.subheader("🎬 Generated Shots")
    shots = st.session_state.get("shots", [])
    
    if not shots:
        st.info("No shots available. Run analysis first.")
    else:
        for shot in shots:
            render_shot(shot)

def render_shot(shot: Shot):
    with st.expander(f"Shot {shot.id}", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            shot_text = st.text_area(
                f"Description",
                value=shot.text,
                height=100,
                key=f"shot_text_{shot.id}"
            )
        
        with col2:
            if st.button(f"Generate", key=f"gen_{shot.id}"):
                generate_shot_image(shot.id, shot_text)
        
        with col3:
            if shot.id in st.session_state.results:
                st.image(
                    st.session_state.results[shot.id],
                    caption=f"Shot {shot.id}"
                )

def render_right_panel():
    st.subheader("📊 Progress")
    
    # Progress tracking
    if st.session_state.get("in_progress"):
        st.info("Processing...")
    
    # Activity log
    st.subheader("📋 Activity Log")
    logs = st.session_state.get("logs", [])
    for log in logs[-10:]:  # Show last 10 entries
        st.text(log)

# Main execution
if __name__ == "__main__":
    main()
```

### 10. Testing & Validation

#### A. Unit Tests

```python
import pytest
import streamlit as st
from unittest.mock import Mock, patch

def test_session_state_initialization():
    # Test session state setup
    pass

def test_file_upload_handling():
    # Test file upload functionality
    pass

def test_analysis_workflow():
    # Test analysis pipeline
    pass
```

#### B. Integration Tests

```python
def test_end_to_end_workflow():
    # Test complete workflow from upload to generation
    pass
```

## Conclusion

This migration guide provides a comprehensive roadmap for converting the CustomTkinter-based Project Maestro v2 application to Streamlit. The key differences are:

1. **State Management**: CustomTkinter uses object attributes, Streamlit uses session state
2. **UI Updates**: CustomTkinter uses event-driven updates, Streamlit uses rerun()
3. **Threading**: CustomTkinter uses background threads, Streamlit uses st.spinner()
4. **File Handling**: CustomTkinter uses file dialogs, Streamlit uses file uploaders
5. **Layout**: CustomTkinter uses absolute positioning, Streamlit uses column-based layout

The Streamlit version will provide the same functionality with a modern web interface, better accessibility, and easier deployment options.
