### Generate Keyframe with Gemini 2.5 Flash (Image)

This document specifies the end-to-end flow to improve a composed keyframe using Google's Gemini 2.5 Flash Image model (via OpenRouter). It covers the UX flow, UI/data responsibilities, image preparation (9:16 crop, optional cinematic processing), API contract, and implementation tasks.

---

### Goals
- Compose a vertical keyframe (9:16) from layered assets.
- Optionally apply a cinematic grade to the composition.
- Send the resulting image + user prompt to Gemini 2.5 Flash (image model) and get back a transformed image.
- Show the AI result in the preview and allow exporting to project keyframes.

---

### User Flow
1) User composes a keyframe (background + layered characters/items).
2) Optional: User applies a cinematic preset to the composed image.
3) User writes a prompt describing desired changes.
4) User presses Generate.
5) App sends the 9:16 image (cinematic version if present, otherwise the raw composition) + prompt to Gemini 2.5 Flash.
6) App receives an image result and displays it in the preview.
7) User can Export the generated image to the project `KEYFRAMES` folder.

---

### Architecture Overview (Files and Responsibilities)
- `app/src/main.tsx`
  - `ComposeKeyframe` UI: assembling background and layers; cinematic controls.
  - `KeyframeGenerator` UI: prompt input, Generate button, AI preview, Export button.
  - Uses helpers to draw layers to a 1080×1920 canvas.
- `app/src/services/assetServices.ts`
  - `cropImageTo9x16(imageDataUrl)`: ensures portrait 9:16 output.
  - `makeCinematicFromDataUrl(dataUrl, preset)`: applies real-time cinematic grading (WebGL) and returns a data URL.
  - `generateImageWithGemini(imageDataUrl, prompt, apiKey)`: calls OpenRouter Gemini 2.5 Flash Image; parses image output.
- `app/src/services/config.ts`
  - Contains `OPENROUTER_API_KEY` (dev only; must be moved to secure config for production).
- `app/vite.config.ts`
  - Dev middleware endpoints: `/api/save` to store images in `public/exports/...`, `/api/list-exports` to list saved assets.
- `app/src/services/sequenceService.ts`
  - Loads saved keyframes (used by the Animate section) from `KEYFRAMES` via `/api/list-exports`.

---

### End-to-End Flow (Sequence)
- Compose (client)
  - Draw background + layers to an offscreen canvas sized 1080×1920.
  - If cinematic is requested, run `makeCinematicFromDataUrl()` over the composition and keep `cinematicPreview` (data URL).
  - For generating: choose input = `cinematicPreview ?? composedDataUrl`.
  - Ensure `input9x16 = cropImageTo9x16(input)` so we always send 9:16.
- Generate (client → OpenRouter)
  - Call `generateImageWithGemini(input9x16, prompt)`.
  - On success, set the returned image data URL into preview.
  - On failure, surface error and keep previous preview.
- Export (client → dev server)
  - POST `/api/save` with `{ userName, projectName, category: 'KEYFRAMES', fileName, dataUrl, episode }`.
  - Server writes file under `public/exports/.../KEYFRAMES` and returns a served path.
- Animate (client)
  - `sequenceService.loadSequence()` loads saved keyframes from `/api/list-exports` and shows them in the Animate page.

---

### Client Implementation Details

#### 1) Building the 9:16 Input Image
- Canvas size: 1080×1920.
- Draw order: background (if set), then each layer in Z order.
- Flip handling: if `layer.flipped`, draw with a horizontal scale of -1.
- After drawing, if cinematic was applied earlier, use `cinematicPreview`; else use the raw composition.
- Run `cropImageTo9x16()` on the chosen image to guarantee portrait 9:16.

Key helper: `cropImageTo9x16(imageDataUrl)` in `assetServices.ts`.
- Computes source crop based on aspect ratios.
- Outputs a PNG data URL of 1080×1920.

#### 2) Optional Cinematic
- `makeCinematicFromDataUrl(dataUrl, preset)` uses a WebGL pipeline to apply:
  - Desaturation, tone curve, split toning, vignette, bloom, shallow DoF, grain, and letterbox as configured.
- Result is a data URL used in place of the raw composition when generating.

#### 3) Generate with Gemini 2.5 Flash
- Use `generateImageWithGemini(imageDataUrl: string, userPrompt: string)` from `assetServices.ts`.
- This function:
  - Converts input (if needed) to a data URL suitable for OpenRouter.
  - Calls `POST https://openrouter.ai/api/v1/chat/completions` with:
    - `model: "google/gemini-2.5-flash-image-preview"`
    - `modalities: ["image", "text"]`
    - `messages: [{ role: "user", content: [{ type: "text", text: system+user prompt }, { type: "image_url", image_url: { url: <dataUrl> } }] }]`
    - `Authorization: Bearer <OPENROUTER_API_KEY>`
    - `extra_headers` for Referer and Title.
  - Parses the response and returns `{ success: true, imageUrl: dataUrl }` on success or `{ success: false, error }` on failure.

Parsing paths supported by `parseGeminiImageResponse()`:
- Primary: `choices[0].message.images[0].image_url.url` (OpenRouter extension).
- Secondary: `choices[0].message.content[]` entries with `{ type: 'image_url', image_url: { url: dataUrl } }`.
- Fallbacks: content string data URL or deep search of nested objects for a `data:image/...` URL.

#### 4) Preview and Export
- Preview binds to the `generatedImage` data URL when present; otherwise shows cinematic or placeholder.
- Export posts to `/api/save` and alerts on success; also dispatches a `keyframe-exported` event.

---

### OpenRouter / Gemini API Contract

Request (concise example):
```json
{
  "model": "google/gemini-2.5-flash-image-preview",
  "modalities": ["image", "text"],
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "[system guidance + user prompt here]" },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]
    }
  ]
}
```

Response (shapes vary; two typical paths):
```json
{
  "choices": [
    {
      "message": {
        "images": [
          { "image_url": { "url": "data:image/png;base64,..." } }
        ],
        "content": [
          { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
        ]
      }
    }
  ]
}
```

Notes:
- Prefer the `message.images` array if present.
- Otherwise iterate `message.content` for items of type `image_url`.
- Some providers may embed the data URL as plain string content; the parser includes safe fallbacks.

---

### Dev Server Endpoints (Vite Middleware)
Defined in `app/vite.config.ts`:
- `POST /api/save`
  - Accepts JSON (or FormData) with `{ userName, projectName, category, fileName, dataUrl, episode }`.
  - Writes a PNG under `public/exports/<role>/<user>/<project>/<episode>/KEYFRAMES/<fileName>` (exact structure follows the middleware logic).
  - Responds `{ ok: true, path: <served-path> }`.
- `GET /api/list-exports?user=<u>&project=<p>&episode=<e>`
  - Returns a JSON structure containing arrays of exported assets, including `KEYFRAMES`.

---

### Security & Configuration
- API key: `OPENROUTER_API_KEY` is currently defined in `app/src/services/config.ts` for local dev only.
  - Move to environment variables and do not ship keys in client bundles.
  - Prefer a backend proxy endpoint that injects the API key server-side.
- Rate limiting and retries:
  - Implement exponential backoff on 429/5xx responses.
  - Surface user-friendly error messages; offer retry CTA.
- Content policy errors:
  - Show the provider’s message to the user with guidance to rephrase the prompt.
  - Do not auto-retry on hard policy rejections.

---

### Error Handling
- Generation timeout (client):
  - Show a timeout notice after a threshold (e.g., 60s) and provide Retry.
- Parse errors:
  - If no image is found in the response, show a clear error and log the response for diagnostics.
- Network errors:
  - Notify the user and allow retry without losing their prompt.

---

### Implementation Tasks (Checklist)
- Wire Generate to API
  - In `KeyframeGenerator.handleGenerate`:
    - Build composition canvas (1080×1920).
    - Choose `input = cinematicPreview ?? composedDataUrl`.
    - `input9x16 = await cropImageTo9x16(input)`.
    - `result = await generateImageWithGemini(input9x16, prompt)`.
    - On success: `setGeneratedImage(result.imageUrl)`.
    - On failure: show error.
- Export
  - Keep current `/api/save` payload; ensure category is `KEYFRAMES`.
  - Confirm saved images appear via `/api/list-exports` and in the Animate page.
- Config hardening
  - Move API key to env or server-only proxy.
  - Add retry/backoff in `generateImageWithGemini` for transient failures.

---

### Testing Checklist
- Composition
  - Layers draw correctly at various scales and flips.
  - 9:16 crop always results in 1080×1920.
- Cinematic
  - Presets apply and produce visually distinct outputs.
  - Generating with cinematic uses the cinematic image (not the raw composition).
- API
  - Valid prompt + valid input returns an image and populates preview.
  - Error paths: 400/401/429/5xx, network errors, parse failures.
  - Retry CTA works.
- Export & Animate
  - Exported keyframes appear in `public/exports/.../KEYFRAMES` and load in the Animate page.

---

### Future Enhancements
- Batch generate across multiple frames with queued requests.
- Server-side proxy for OpenRouter (secure API key, centralized logging, uniform error handling).
- Optional image upscaling/denoising pass.
- Project-level prompt presets and style locks.
- Caching of recent prompts and inputs to avoid re-sending identical requests.


