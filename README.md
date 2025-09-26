Project Maestro v2 – GUI Storyboard Generator

Overview

Project Maestro v2 is a desktop GUI app (CustomTkinter) that generates storyboard shots from short videos using OpenRouter models. It includes auto-upscaling with Real‑ESRGAN and saves results to the `output/` folder.

Features

- Video + style image inputs
- Context analysis, Director shot generation, per‑shot image generation
- Select number of shots (3–10)
- Automatic upscaling and autosave
- Accessibility: theme toggle (Light/Dark), UI text scaling

Quick Start (Windows)

1) Unzip the folder anywhere (e.g., Desktop)
2) Double‑click `launch.bat`
   - Creates `.venv`, installs dependencies, prepares `.env`, and launches the app
3) If prompted, open `.env` and paste your OpenRouter key after `OPENROUTER_API_KEY=`

Packaged Real‑ESRGAN

- This zip includes `weights/realesr-general-x4v3.pth`. The launcher sets `REAL_ESRGAN_WEIGHTS_DIR` to the local `weights/` folder so no download is required.
- If the weights file is missing, the app will try to download it at runtime. To stay offline, ensure the file exists before launch.

Environment (.env)

- Copy `env.example` to `.env` if not already created
- Set:
  - `OPENROUTER_API_KEY=sk‑...` (required)
  - Optional: `V2_OPENROUTER_*` to override model choices/timeouts

Run Manually (advanced)

1) `python -m venv .venv` and activate it
2) `pip install -r requirements.txt`
3) `python -m src.gui.main`

Troubleshooting

- First run may download Real‑ESRGAN weights to `weights/`. If download fails, place `realesr-general-x4v3.pth` into `weights/` manually and re‑launch.
- If models reject images or time out, adjust `V2_REQUEST_TIMEOUT_SEC` in `.env`.

License

Part of the Lovelife AI ecosystem. See project-level license terms.
