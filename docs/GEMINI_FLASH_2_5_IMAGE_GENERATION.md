## GEMINI 2.5 Flash Image Generation in this Streamlit App

This document explains how the app sends an uploaded image and a prompt to Google Gemini 2.5 Flash Image Preview (via OpenRouter), how the image response is decoded, and how the app previews and enlarges results in Streamlit.

The implementation lives in `app.py` inside the `OpenRouterClient` class and the surrounding Streamlit UI.


### Model and Transport
- **Provider/Model**: `google/gemini-2.5-flash-image-preview:free` (via OpenRouter)
- **SDK**: `openai` Python SDK, routed to OpenRouter by setting `base_url="https://openrouter.ai/api/v1"`
- **Endpoint**: `chat.completions.create(...)` with `modalities=["image", "text"]`

Configuration is provided from Streamlit secrets (see `README.md`):

```toml
# .streamlit/secrets.toml
OPENROUTER_API_KEY = "..."
MODEL_NAME = "google/gemini-2.5-flash-image-preview:free"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"
GENERATION_TIMEOUT_SECONDS = "120"
APP_REFERER = "https://keyframe.streamlit.app/"
APP_TITLE = "Keyframe Generator"
```


## 1) How we send the image + prompt to the model

High-level flow:
1. The uploaded PIL image is compressed to bytes (PNG for transparency or JPEG for opaque) to minimize payload size while preserving dimensions.
2. The image bytes are encoded into a Base64 data URL `data:<mime>;base64,<...>`.
3. The prompt text is combined with one or more `image_url` parts into the Chat Completions `messages[0].content` array.
4. The request is posted to OpenRouter with `modalities=["image", "text"]`.

Key code paths in `app.py` (summarized and simplified for clarity):

```python
def _to_data_url(image_bytes: bytes, mime: str = "image/png") -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _build_mm_content(prompt: str, images: list[tuple[bytes, str]]) -> list[dict]:
    parts = [{"type": "text", "text": prompt}]
    for img_bytes, mime in images:
        parts.append({
            "type": "image_url",
            "image_url": {"url": _to_data_url(img_bytes, mime)}
        })
    return parts

payload = {
    "model": self.model,  # defaults to google/gemini-2.5-flash-image-preview:free
    "modalities": ["image", "text"],
    "messages": [{"role": "user", "content": content}],
    "stream": False,
}

resp = self.client.chat.completions.create(
    **payload,
    extra_headers=self.extra_headers,  # OpenRouter attribution headers
    timeout=self.timeout_seconds,
)
```

Notes:
- Multiple input images are supported. Inputs are normalized to a list of `(bytes, mime)` before building `content`.
- The app sets attribution headers `HTTP-Referer` and `X-Title` as recommended by OpenRouter.


## 2) How we decode the image response

OpenRouter (and different providers behind it) can return image data in a few shapes. The client handles all of these and decodes the first returned image:

Decoding steps:
1. Convert the SDK response to a plain `dict` using `.model_dump()` or `.to_dict()`.
2. Try the following paths in order until an image data URL is found:
   - `message.images[0].image_url.url`
   - `message.content` array with an item `{ "type": "image_url", "image_url": {"url": "data:image/..."} }`
   - `message.content` is a string data URL
   - Deep scan for any `data:image/*` URL nested inside the message object
3. Once a `data:image/*` URL is found, split at the first comma and `base64.b64decode(...)` the second part into bytes.

Key decoding helpers (simplified):

```python
def _decode_image_url_to_bytes(url: str) -> bytes:
    b64 = url.split(",", 1)[1]
    return base64.b64decode(b64)

def _extract_image_bytes_from_dict(data: dict) -> bytes:
    message = (data.get("choices") or [{}])[0].get("message", {})

    # A) OpenRouter extension
    images = message.get("images") or []
    if images:
        url = (images[0].get("image_url") or {}).get("url")
        if url:
            return _decode_image_url_to_bytes(url)

    # B) Multimodal content array
    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url")
                if url:
                    return _decode_image_url_to_bytes(url)

    # C) Content string as a data URL
    if isinstance(content, str) and content.startswith("data:"):
        return _decode_image_url_to_bytes(content)

    # D) Deep scan nested fields
    deep_url = _find_first_data_url_in_obj(message)
    if deep_url:
        return _decode_image_url_to_bytes(deep_url)

    raise RuntimeError("Model returned no images.")
```

The image bytes are then opened with Pillow for downstream use:

```python
from io import BytesIO
from PIL import Image

image = Image.open(BytesIO(image_bytes)).convert("RGBA")
```


## 3) How we preview the image in Streamlit

There are two preview points in the UI:

- Uploaded image preview (sidebar):

```python
st.image(image, caption="Uploaded Image", width='stretch')
```

- Generated keyframes (main area):

```python
image_data = st.session_state.generated_images[keyframe_id]
st.image(image_data, caption=f"Variation {keyframe_id}", width='stretch')
```

Implementation details:
- The app keeps generated results in `st.session_state.generated_images` and re-renders the preview area each run.
- Images are displayed in N columns (1–3) depending on the selected number of keyframes.
- A download button is provided for each generated image to save it as PNG.


## 4) How to enlarge the image (recommended patterns)

Streamlit doesn’t currently offer a built-in lightbox on click, but you have several practical options:

1) Modal (Streamlit 1.31+): show a larger image in a modal dialog.

```python
import streamlit as st
from io import BytesIO

img = st.session_state.generated_images.get("A")
if img is not None:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.image(img, caption="Variation A", use_column_width=True)
    with col2:
        if st.button("🔍 Enlarge A"):
            with st.modal("Variation A - Full Size"):
                st.image(img, caption="Variation A (Full)", use_column_width=True)
                st.button("Close")
```

2) Open in a new browser tab using a data URL (works on all supported versions):

```python
import base64
from io import BytesIO

def image_to_data_url(pil_image, mime="image/png") -> str:
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:{mime};base64,{b64}"

img = st.session_state.generated_images.get("A")
if img is not None:
    data_url = image_to_data_url(img)
    st.markdown(f"[Open full size in new tab]({data_url})", unsafe_allow_html=True)
```

3) Show a larger inline preview with an expander:

```python
img = st.session_state.generated_images.get("A")
if img is not None:
    with st.expander("🔎 Preview Large (A)", expanded=False):
        st.image(img, caption="Variation A (Large)", use_column_width=True)
```

Notes and tips:
- Prefer `use_column_width=True` for responsive layouts; it fills the container width.
- For pixel-exact previews, pass an integer to `width=<pixels>`.
- The app already provides a download button; users can save and open the image in any viewer.


## End-to-end sequence (Streamlit)
1. User uploads an image in the sidebar.
2. App compresses the image to bytes without changing dimensions.
3. App constructs a prompt based on Angle/Position/Emotion.
4. App encodes the image bytes into a Base64 data URL and builds the `messages[0].content` array.
5. App calls `chat.completions.create(...)` with `modalities=["image", "text"]`.
6. App decodes the first returned `data:image/*` URL to raw bytes, opens it with Pillow, and stores it.
7. App previews generated images in columns and provides download and optional enlarge actions.


## Troubleshooting
- 401/Unauthorized → Verify `OPENROUTER_API_KEY` in `.streamlit/secrets.toml`.
- 404/Model not found → Check `MODEL_NAME` is set to `google/gemini-2.5-flash-image-preview:free` or another valid model.
- 429/Rate limited → Wait and retry; consider plan limits.
- Timeout → Reduce image size/quality or increase `GENERATION_TIMEOUT_SECONDS`.
- “Model returned no images” → Adjust the prompt or input image; check safety filters.


