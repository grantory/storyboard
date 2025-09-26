Project Maestro v2 – Development

Structure

- v2/src/app.py – Streamlit UI and orchestration
- v2/src/services/
  - video.py – frame extraction (OpenCV if available)
  - context.py – Context step (GPT‑5 mini)
  - director.py – Director step (GPT‑5 mini)
  - images.py – Gemini image generation via OpenRouter
  - storage.py – temp files, downloads
  - config.py – env loading
  - types.py – dataclasses

Implementation Notes

- Frame Sampling: 5 evenly spaced frames; 1 middle frame for Director
- Parsing Director Output: regex on lines starting with "SHOT <n>:"
- Concurrency: ThreadPoolExecutor bounded by V2_MAX_CONCURRENT_REQUESTS
- State: st.session_state for per-row status and results

Run Locally

1) pip install -r requirements.txt
2) Streamlit UI: `streamlit run src/app.py`
3) Desktop GUI: `python -m src.gui.main` (loads `.env` from project root)

Testing

- Unit-test frame extraction and parsing logic
- Mock API calls for CI

Packaging (Windows)

- One-folder build with PyInstaller:
  - `pyinstaller --noconfirm --clean --name MaestroV2 --onedir --add-data "weights;weights" --hidden-import cv2 --hidden-import basicsr --hidden-import realesrgan src/gui/main.py`
  - Include `weights/realesr-general-x4v3.pth` in the build directory


