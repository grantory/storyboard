Project Maestro v2 – Configuration

Environment Variables (v2/.env)

- OPENROUTER_API_KEY: required for GPT‑5 mini and Gemini image via OpenRouter
- V2_OPENROUTER_CONTEXT_MODEL: default gpt-5-mini
- V2_OPENROUTER_DIRECTOR_MODEL: default gpt-5-mini
- V2_OPENROUTER_IMAGE_MODEL: default google/gemini-2.5-flash-image-preview
- V2_MAX_CONCURRENT_REQUESTS: default 5
- V2_REQUEST_TIMEOUT_SEC: default 60

Files

- v2/env.example – template to copy to v2/.env
- v2/requirements.txt – minimal dependencies for v2

Notes

- Keep keys out of code; load via dotenv
- For production, proxy requests server-side if needed


