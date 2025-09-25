Project Maestro v2 – Architecture

Goals

- Single-page Streamlit app, self-contained under v2/
- Two GPT‑5 mini calls for ANALYZE; Gemini image model for generation
- Concurrent image generation for responsiveness

High-Level Flow

1) Uploads
   - Video: mp4, <= 30s (validated client-side and server-side)
   - Style Image: png/jpg (no extra validation required)
2) ANALYZE
   - Step 1: Context (GPT‑5 mini): sample 5 evenly spaced frames; infer concise scene context
   - Step 2: Director (GPT‑5 mini): send 1 representative frame + context + fixed prompt; return 5 structured shots as SHOT 1..5
3) UI Population
   - One row per shot: editable text, Generate, Preview, Save
4) GENERATE
   - Model: google/gemini-2.5-flash-image-preview (via OpenRouter)
   - Parallel requests; each row can generate independently

Modules (v2/src)

- app.py: Streamlit UI and orchestration
- services/video.py: frame extraction utilities (OpenCV optional; fallback to moviepy if needed)
- services/context.py: Context step (GPT‑5 mini)
- services/director.py: Director step (GPT‑5 mini)
- services/images.py: Gemini image generation via OpenRouter; concurrent execution helpers
- services/storage.py: temporary file handling and downloads
- config.py: load env vars (OpenRouter API key, models, limits)
- types.py: dataclasses for Context, Shot, and GenerationResult

Data Model

- Context: { setting: str, main_action: str, emotional_tone: list[str], summary: str }
- Shot (Director output): { id: int, text: str }
- GenerationResult: { shot_id: int, image_data_url: str, created_at: float }

Frame Sampling

- Compute N=5 frames: indices = round((i/(N+1))*total_frames) for i=1..N
- Extract as PNG in-memory; pass as data URLs to GPT‑5 mini
- For Director, pick middle frame (index ~ total_frames/2)

Concurrency Strategy

- Use ThreadPoolExecutor for per-shot image generation
- Bound parallelism by MAX_CONCURRENT_REQUESTS
- Each generation updates its own state key in st.session_state

Caching

- Optional: simple in-memory cache keyed by (video hash, context prompt), off by default in v2 for simplicity

Error Handling

- API failures: show inline error on the row, non-blocking for others
- Timeouts: per-request timeout; user can retry without losing edits

Security

- No keys in client code; read OPENROUTER_API_KEY from environment
- Inputs are transient; files stored in v2/.cache/ during session


