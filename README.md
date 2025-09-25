Project Maestro v2 – Streamlit Storyboard (Simplified)

Overview

Project Maestro v2 is a simplified, self-contained Streamlit app for fast storyboarding from short videos. It runs independently inside this v2 folder so it can be moved or deployed separately when ready.

User Flow

- Upload a video (mp4, <= 30s) and a style image (png/jpg)
- Click ANALYZE
  - Step 1: Context (GPT‑5 mini). Model receives 5 evenly sampled frames and returns a short scene context
  - Step 2: Director (GPT‑5 mini). Model receives 1 frame + context + fixed prompt and outputs 5 structured shots: "SHOT 1: ...", "SHOT 2: ..."
- The interface renders a row per shot with: editable director text, Generate button, preview thumbnail, and Save button
- Image generation uses google/gemini-2.5-flash-image-preview via OpenRouter; multiple shots can be generated concurrently

Key Principles

- Independence: all v2 code, docs, and requirements live under v2/
- Minimalism: small, focused code paths for analysis and generation
- Responsiveness: concurrent image generations and non-blocking UI
- Portability: one folder to move/deploy

Docs

- docs/architecture.md – v2 system design and data flow
- docs/prompts.md – prompts for Context and Director steps
- docs/user-guide.md – how to use the v2 app
- docs/configuration.md – environment variables and models
- docs/development.md – implementation details and local dev
- docs/api-contracts.md – request/response contracts
- docs/testing.md – test plan and scenarios
- docs/performance.md – concurrency and responsiveness
- docs/troubleshooting.md – common issues

Quick Start

1) Create and fill v2/.env from v2/env.example
2) Install deps: pip install -r v2/requirements.txt
3) Run: streamlit run v2/src/app.py

License

Part of the Lovelife AI ecosystem. See project-level license terms.


"# storyboard" 
