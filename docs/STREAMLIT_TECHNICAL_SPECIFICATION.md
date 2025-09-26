# Project Maestro v2: Streamlit Technical Specification

## Executive Summary

This document provides a detailed technical specification for reimplementing the Project Maestro v2 AI Storyboard Generator from CustomTkinter to Streamlit. The specification covers architecture, component mapping, data flow, and implementation details.

## Current System Analysis

### Architecture Overview

The current CustomTkinter implementation follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │   Sidebar   │ │  Main Content   │ │  Right Panel    │    │
│  │   (Files)   │ │  (Context &     │ │  (Progress &    │    │
│  │   (Actions) │ │   Shots)        │ │   Logs)         │    │
│  │   (Preview) │ │                 │ │                 │    │
│  └─────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
│                    Application Layer                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              MaestroApp (Main Controller)               │ │
│  │  • UI Management    • Event Handling    • State Mgmt   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
│                      Business Layer                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Pipeline (Service Wrapper)               │ │
│  │  • Configuration    • Client Lifecycle    • Logging     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
│                      Service Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   Context  │ │  Director  │ │   Images   │ │  Video  │ │
│  │  Service   │ │  Service   │ │  Service   │ │ Service │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Components Analysis

#### 1. MaestroApp Class (Main Controller)

**Current Implementation:**
```python
class MaestroApp(ctk.CTk):
    def __init__(self):
        self.app_state = AppState(cfg=load_config())
        self.pipeline = Pipeline(self.app_state.cfg, on_log=self._on_log)
        self.events = queue.Queue()
        self._build_ui()
        self._setup_keyboard_shortcuts()
```

**Responsibilities:**
- UI layout management
- Event handling and threading
- State synchronization
- User interaction coordination

#### 2. AppState Class (State Management)

**Current Implementation:**
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

**Responsibilities:**
- Session data persistence
- Configuration management
- Progress tracking
- Error state management

#### 3. Pipeline Class (Service Integration)

**Current Implementation:**
```python
class Pipeline:
    def __init__(self, cfg: Optional[V2Config] = None, on_log: Optional[Callable[[str], None]] = None):
        self.cfg = cfg or load_config()
        self.client = create_openrouter_client(self.cfg.openrouter_api_key)
    
    def analyze_context(self, video_bytes: bytes, cancel: Optional[Event] = None) -> Tuple[str, str]:
        # Context analysis workflow
    
    def generate_shots_from_context(self, middle_frame_data_url: str, context_text: str, cancel: Optional[Event] = None, *, shot_count: int = 5) -> List[Shot]:
        # Shot generation workflow
    
    def generate_one(self, style_data_url: str, shot_text: str) -> str:
        # Individual image generation
```

**Responsibilities:**
- Service orchestration
- Configuration management
- Error handling and logging
- API client lifecycle

## Streamlit Architecture Design

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                      │
│  ┌─────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │   Sidebar   │ │  Main Content   │ │  Right Panel    │    │
│  │   (Files)   │ │  (Context &     │ │  (Progress &    │    │
│  │   (Actions) │ │   Shots)        │ │   Logs)         │    │
│  │   (Preview) │ │                 │ │                 │    │
│  └─────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
│                    Session State Layer                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Streamlit Session State                   │ │
│  │  • File Data    • Results    • Progress    • Config     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
│                    Application Logic Layer                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Streamlit App Functions                 │ │
│  │  • UI Rendering    • Event Handling    • State Mgmt     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
│                      Service Layer                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Pipeline (Reused)                       │ │
│  │  • Configuration    • Client Lifecycle    • Logging     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Mapping

#### 1. UI Components Mapping

| CustomTkinter Component | Streamlit Equivalent | Implementation Notes |
|------------------------|---------------------|---------------------|
| `ctk.CTkScrollableFrame` | `st.sidebar` | Use sidebar for file uploads and actions |
| `ctk.CTkTextbox` | `st.text_area` | For context and shot descriptions |
| `ctk.CTkButton` | `st.button` | Action buttons with state management |
| `ctk.CTkProgressBar` | `st.progress` | Progress tracking with st.spinner |
| `ctk.CTkImage` | `st.image` | Image display with caching |
| `ctk.CTkOptionMenu` | `st.selectbox` | Model and configuration selection |
| `ctk.CTkLabel` | `st.text` / `st.markdown` | Text display and status |

#### 2. State Management Mapping

| CustomTkinter State | Streamlit Session State | Migration Strategy |
|--------------------|-------------------------|-------------------|
| `self.app_state.video_bytes` | `st.session_state.video_file` | File uploader bytes |
| `self.app_state.style_data_url` | `st.session_state.style_data_url` | Processed style image |
| `self.app_state.context_text` | `st.session_state.context_text` | Direct mapping |
| `self.app_state.shots` | `st.session_state.shots` | List of Shot objects |
| `self.app_state.results` | `st.session_state.results` | Dict[int, str] mapping |
| `self.app_state.in_progress` | `st.session_state.in_progress` | Dict[int, bool] tracking |
| `self.app_state.logs` | `st.session_state.logs` | List of log messages |

#### 3. Event Handling Mapping

| CustomTkinter Event | Streamlit Equivalent | Implementation |
|--------------------|---------------------|----------------|
| Button click events | `st.button` callbacks | Direct function calls |
| File dialog events | `st.file_uploader` | Automatic file handling |
| Progress updates | `st.progress` / `st.spinner` | Real-time progress display |
| Keyboard shortcuts | Not applicable | Web-based interaction |
| Threading events | `st.rerun()` | State-driven rerendering |

## Detailed Implementation Specification

### 1. Session State Management

#### A. State Initialization

```python
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
```

#### B. State Update Functions

```python
def update_session_state(key: str, value, trigger_rerun: bool = True):
    """Update session state with optional rerun trigger"""
    st.session_state[key] = value
    if trigger_rerun:
        st.rerun()

def batch_update_session_state(updates: dict, trigger_rerun: bool = True):
    """Update multiple session state variables at once"""
    for key, value in updates.items():
        st.session_state[key] = value
    if trigger_rerun:
        st.rerun()

def clear_session_state():
    """Clear all session state (reset application)"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
```

### 2. UI Layout Implementation

#### A. Main Layout Structure

```python
def render_main_layout():
    """Render the main application layout"""
    
    # Header
    render_header()
    
    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        render_sidebar()
    
    with col2:
        render_main_content()
    
    with col3:
        render_right_panel()
    
    # Footer
    render_footer()

def render_header():
    """Render application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🎬 Project Maestro v2</h1>
        <p>Transform your videos into stunning storyboards with AI</p>
    </div>
    """, unsafe_allow_html=True)
```

#### B. Sidebar Implementation

```python
def render_sidebar():
    """Render the left sidebar with file uploads and actions"""
    
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
    
    # Settings
    render_settings_section()
```

#### C. Main Content Implementation

```python
def render_main_content():
    """Render the main content area with context and shots"""
    
    # Context section
    render_context_section()
    
    # Shots section
    render_shots_section()

def render_context_section():
    """Render the context analysis section"""
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

def render_shots_section():
    """Render the shots section"""
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
```

#### D. Right Panel Implementation

```python
def render_right_panel():
    """Render the right panel with progress and logs"""
    
    # Progress section
    render_progress_section()
    
    # Activity log section
    render_log_section()
    
    # Settings section
    render_settings_panel()

def render_progress_section():
    """Render progress tracking"""
    st.subheader("📊 Progress")
    
    current_operation = st.session_state.get("current_operation")
    if current_operation:
        st.info(f"🔄 {current_operation}")
    
    # Progress bar for batch operations
    if st.session_state.get("batch_progress"):
        progress = st.session_state.batch_progress
        st.progress(progress["current"] / progress["total"])
        st.caption(f"Progress: {progress['current']}/{progress['total']}")

def render_log_section():
    """Render activity log"""
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

def render_settings_panel():
    """Render settings panel"""
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
```

### 3. Core Functionality Implementation

#### A. Video Analysis

```python
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
        
        context_text = st.session_state.pipeline.analyze_context(video_bytes)
        st.session_state.context_text = context_text
        st.session_state.middle_frame_data_url = middle_url
        
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
```

#### B. Shot Generation

```python
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
```

#### C. Image Generation

```python
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
```

#### D. Download Functionality

```python
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
```

### 4. Utility Functions

#### A. Logging System

```python
def log_message(message: str):
    """Add message to activity log"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    st.session_state.logs.append(log_entry)
    
    # Keep only last 100 log entries
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]
    
    # Also log to console for debugging
    print(log_entry)

def clear_logs():
    """Clear activity log"""
    st.session_state.logs = []
    log_message("🗑️ Activity log cleared")
```

#### B. Connection Testing

```python
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
```

#### C. Batch Operations

```python
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
```

### 5. Performance Optimizations

#### A. Caching Strategy

```python
@st.cache_data
def process_video_frames(video_bytes: bytes, n_frames: int) -> List[str]:
    """Cache video frame processing"""
    return sample_context_frames_as_data_urls(video_bytes, n=n_frames)

@st.cache_data
def process_style_image(style_bytes: bytes) -> str:
    """Cache style image processing"""
    return compress_image_bytes_to_jpeg_data_url(style_bytes, max_width=1024, quality=85)

@st.cache_data
def generate_shot_image_cached(style_url: str, shot_text: str, model_config: dict) -> str:
    """Cache generated images (with model config as cache key)"""
    # This would need to be implemented carefully to avoid cache pollution
    pass
```

#### B. Memory Management

```python
def cleanup_session_state():
    """Clean up large objects from session state"""
    
    # Clear old logs
    if len(st.session_state.get("logs", [])) > 50:
        st.session_state.logs = st.session_state.logs[-50:]
    
    # Clear old results if too many
    if len(st.session_state.get("results", {})) > 20:
        # Keep only the most recent 20 results
        recent_results = dict(list(st.session_state.results.items())[-20:])
        st.session_state.results = recent_results
```

### 6. Error Handling & User Experience

#### A. Error Display

```python
def handle_error(error: Exception, context: str = ""):
    """Centralized error handling"""
    
    error_msg = f"Error in {context}: {str(error)}" if context else str(error)
    log_message(f"❌ {error_msg}")
    
    # Display user-friendly error
    st.error(f"❌ {error_msg}")
    
    # Show detailed error in expander for debugging
    with st.expander("🔍 Error Details", expanded=False):
        st.exception(error)
```

#### B. Loading States

```python
def show_loading_state(message: str):
    """Show loading state with message"""
    st.session_state.current_operation = message
    st.info(f"🔄 {message}")

def clear_loading_state():
    """Clear loading state"""
    st.session_state.current_operation = None
```

### 7. Configuration Management

#### A. Environment Setup

```python
def load_environment():
    """Load environment configuration"""
    
    # Load from .env file
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ["OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.stop()
    
    return True
```

#### B. Configuration UI

```python
def render_configuration_ui():
    """Render configuration interface"""
    
    with st.expander("⚙️ Configuration", expanded=False):
        
        # API Key
        api_key = st.text_input(
            "OpenRouter API Key",
            value=st.session_state.get("api_key", ""),
            type="password",
            help="Your OpenRouter API key"
        )
        
        if api_key:
            st.session_state.api_key = api_key
        
        # Model selection
        col1, col2 = st.columns(2)
        
        with col1:
            context_model = st.selectbox(
                "Context Model",
                options=["gpt-4o-mini", "gpt-4o", "claude-3-haiku"],
                index=0
            )
        
        with col2:
            director_model = st.selectbox(
                "Director Model",
                options=["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"],
                index=0
            )
        
        # Save configuration
        if st.button("💾 Save Configuration"):
            # Update configuration
            st.success("Configuration saved!")
```

## Testing Strategy

### 1. Unit Tests

```python
import pytest
import streamlit as st
from unittest.mock import Mock, patch

class TestStreamlitApp:
    
    def test_session_state_initialization(self):
        """Test session state initialization"""
        # Test that all required session state variables are initialized
        pass
    
    def test_file_upload_handling(self):
        """Test file upload functionality"""
        # Test video and style image upload
        pass
    
    def test_analysis_workflow(self):
        """Test video analysis workflow"""
        # Test complete analysis pipeline
        pass
    
    def test_shot_generation(self):
        """Test shot generation"""
        # Test shot generation from context
        pass
    
    def test_image_generation(self):
        """Test image generation"""
        # Test individual and batch image generation
        pass
```

### 2. Integration Tests

```python
def test_end_to_end_workflow():
    """Test complete workflow from upload to download"""
    
    # 1. Upload files
    # 2. Run analysis
    # 3. Generate shots
    # 4. Generate images
    # 5. Download results
    
    pass

def test_error_handling():
    """Test error handling scenarios"""
    
    # Test with invalid files
    # Test with network errors
    # Test with API failures
    
    pass
```

### 3. Performance Tests

```python
def test_performance_metrics():
    """Test performance under various loads"""
    
    # Test with large files
    # Test with many shots
    # Test memory usage
    
    pass
```

## Deployment Considerations

### 1. Streamlit Configuration

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

[browser]
gatherUsageStats = false
```

### 2. Environment Variables

```bash
# .env
OPENROUTER_API_KEY=your_api_key_here
CONTEXT_MODEL=gpt-4o-mini
DIRECTOR_MODEL=gpt-4o
IMAGE_MODEL=dall-e-3
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT_SECONDS=60
```

### 3. Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Conclusion

This technical specification provides a comprehensive roadmap for migrating the Project Maestro v2 application from CustomTkinter to Streamlit. The key advantages of the Streamlit implementation include:

1. **Web-based Interface**: Accessible from any device with a web browser
2. **Easier Deployment**: Simple deployment to cloud platforms
3. **Better Collaboration**: Multiple users can access the same interface
4. **Modern UI**: Streamlit provides a modern, responsive interface
5. **Easier Maintenance**: Web-based applications are easier to update and maintain

The migration maintains all core functionality while providing a more accessible and maintainable solution.
