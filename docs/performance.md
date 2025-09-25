Project Maestro v2 – Performance & Concurrency

Objectives

- Keep UI responsive during ANALYZE and per-shot GENERATE
- Allow parallel image generations with bounded concurrency

Techniques

- Use ThreadPoolExecutor with V2_MAX_CONCURRENT_REQUESTS
- Non-blocking Streamlit updates per row using session state keys
- Minimal payloads in prompts; avoid verbose context carryover

Time Budgets

- ANALYZE: < 10s typical per call on gpt-5-mini
- GENERATE: < 30–60s per image; multiple in parallel

Retries

- Simple exponential backoff on 429/5xx
- Limit to 2–3 retries per request


