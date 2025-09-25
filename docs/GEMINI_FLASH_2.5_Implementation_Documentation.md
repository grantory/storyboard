# GEMINI FLASH 2.5 Implementation Documentation

## Overview

This document provides comprehensive documentation about how the NanoBanana v2 project implements and integrates with Google's GEMINI FLASH 2.5 model through the OpenRouter API. The implementation focuses on image generation, retrieval, and decoding from the model's responses.

## Architecture Overview

The GEMINI FLASH 2.5 implementation uses a multi-layered approach:

1. **OpenRouter API Integration**: Routes requests through OpenRouter to access GEMINI 2.5 Flash Image Preview
2. **OpenAI SDK Compatibility**: Uses the OpenAI SDK with custom base URL routing
3. **Robust Response Parsing**: Handles multiple response formats and fallback mechanisms
4. **Streaming Support**: Real-time image generation with status updates

## Core Components

### 1. OpenRouterClient Class

The main client class that handles all GEMINI FLASH 2.5 interactions:

**Location**: `src/core/api_client.py`, `keyframev2.py`, `keyframev3.py`, `outfit_swap.py`

**Key Features**:
- Thread-friendly synchronous client
- Supports single or multiple input images
- Handles both streaming and non-streaming responses
- Robust error handling with retry mechanisms

### 2. Model Configuration

```python
# Default model configuration
model = "google/gemini-2.5-flash-image-preview:free"  # Free tier
model = "google/gemini-2.5-flash-image-preview"       # Paid tier

# API endpoint
base_url = "https://openrouter.ai/api/v1"
```

## Image Response Retrieval and Decoding

### Response Structure Handling

The implementation handles multiple response formats from the GEMINI model through a sophisticated parsing system:

#### 1. OpenRouter Extension Format (Primary)
```python
# Path A: OpenRouter extension `message.images`
images = message.get("images") or []
if isinstance(images, list) and images:
    first = images[0] or {}
    image_url_obj = first.get("image_url") or {}
    url = image_url_obj.get("url")
    if url:
        return OpenRouterClient._decode_image_url_to_bytes(url)
```

#### 2. Multimodal Content Array (Secondary)
```python
# Path B: Multimodal content array (list of parts)
content = message.get("content")
if isinstance(content, list):
    for item in content:
        if isinstance(item, dict) and item.get("type") == "image_url":
            url = (item.get("image_url") or {}).get("url")
            if url:
                return OpenRouterClient._decode_image_url_to_bytes(url)
```

#### 3. String Content as Data URL (Fallback)
```python
# Path C: String content as a data URL (rare, but guard it)
if isinstance(content, str) and content.startswith("data:"):
    return OpenRouterClient._decode_image_url_to_bytes(content)
```

#### 4. Deep Scan for Nested Data URLs (Final Fallback)
```python
# Path D: Deep scan for any data:image/* URL in nested structures
deep_url = OpenRouterClient._find_first_data_url_in_obj(message)
if deep_url:
    return OpenRouterClient._decode_image_url_to_bytes(deep_url)
```

### Base64 Decoding Process

The core decoding mechanism converts data URLs to image bytes:

```python
@staticmethod
def _decode_image_url_to_bytes(url: str) -> bytes:
    """
    Decode a data URL to bytes.
    """
    if not isinstance(url, str):
        raise RuntimeError("Unexpected image URL type.")
    if not url.startswith("data:"):
        raise RuntimeError("Unexpected image URL format (expected data: URL).")
    try:
        b64 = url.split(",", 1)[1]
    except Exception as e:
        raise RuntimeError(f"Malformed data URL: {e}") from e
    return base64.b64decode(b64)
```

### Deep URL Search Algorithm

For complex nested responses, the implementation includes a recursive search:

```python
@staticmethod
def _find_first_data_url_in_obj(obj: Any) -> Optional[str]:
    """
    Recursively search for the first string that looks like a data:image/* URL
    within a nested dict/list structure.
    """
    try:
        if isinstance(obj, str):
            if "data:image/" in obj:
                # Extract data URL from embedded string
                start = obj.find("data:image/")
                end = len(obj)
                for sep in ["\n", " ", ")", "]", "\"", "'"]:
                    ix = obj.find(sep, start)
                    if ix != -1:
                        end = min(end, ix)
                return obj[start:end]
            return None
        
        if isinstance(obj, dict):
            # Direct url field fast-path
            url = obj.get("url") or obj.get("image_url")
            if isinstance(url, str) and url.startswith("data:image/"):
                return url
            if isinstance(url, dict):
                inner = url.get("url")
                if isinstance(inner, str) and inner.startswith("data:image/"):
                    return inner
            # Recursively search all values
            for v in obj.values():
                found = OpenRouterClient._find_first_data_url_in_obj(v)
                if found:
                    return found
            return None
        
        if isinstance(obj, list) or isinstance(obj, tuple):
            for item in obj:
                found = OpenRouterClient._find_first_data_url_in_obj(item)
                if found:
                    return found
            return None
    except Exception:
        return None
    return None
```

## Streaming Implementation

### Real-time Image Generation

The streaming implementation processes events in real-time:

```python
def _stream_and_collect(self, payload: Dict[str, Any], update_status: Optional[Callable[[str], None]]) -> bytes:
    """
    Stream events; when an image delta appears, return it.
    """
    try:
        if update_status:
            update_status("Streaming…")
        stream = self.client.chat.completions.create(
            **payload,
            extra_headers=self.extra_headers,
            timeout=self.timeout_seconds,
        )
        
        # Iterate streaming events
        for event in stream:
            try:
                d = event.data.model_dump() if hasattr(event.data, "model_dump") else {}
                choices = d.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}

                # Image deltas (OpenRouter extension)
                imgs = delta.get("images") or []
                if imgs:
                    url = (imgs[0].get("image_url") or {}).get("url")
                    if url and isinstance(url, str) and url.startswith("data:"):
                        if update_status:
                            update_status("Receiving image…")
                        return self._decode_image_url_to_bytes(url)

                # Fallback: data URL within content or nested
                content_delta = delta.get("content")
                if isinstance(content_delta, str) and "data:image/" in content_delta:
                    if update_status:
                        update_status("Receiving image…")
                    return self._decode_image_url_to_bytes(
                        self._find_first_data_url_in_obj(content_delta) or content_delta
                    )
                
                deep_url = self._find_first_data_url_in_obj(delta)
                if isinstance(deep_url, str):
                    if update_status:
                        update_status("Receiving image…")
                    return self._decode_image_url_to_bytes(deep_url)

                # Optional: surface incremental text (status-ish)
                if update_status and isinstance(delta.get("content"), str):
                    update_status(delta["content"])
            except Exception:
                # Per-chunk issues vary by provider; ignore and continue
                pass

        raise RuntimeError("Stream ended without an image.")
    except Exception as e:
        raise self._handle_api_error(e)
```

## API Request Structure

### Request Payload

```python
payload: Dict[str, Any] = {
    "model": self.model,  # "google/gemini-2.5-flash-image-preview:free"
    "modalities": ["image", "text"],
    "messages": [{"role": "user", "content": content}],
    "stream": bool(stream),
}
```

### Multimodal Content Building

```python
def _build_mm_content(self, prompt: str, images: List[ImageWithMime]) -> List[Dict[str, Any]]:
    """
    Build the multimodal content array the API expects:
      - text part first (the instruction),
      - then N image_url parts (one per input image).
    """
    parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img_bytes, mime in images:
        parts.append({
            "type": "image_url",
            "image_url": {"url": self._to_data_url(img_bytes, mime)}
        })
    return parts
```

### Data URL Encoding

```python
@staticmethod
def _to_data_url(image_bytes: bytes, mime: str = "image/png") -> str:
    """
    Encode raw image bytes into a base64 data URL.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"
```

## Error Handling and Retry Logic

### Retry Mechanism

```python
# Non-streaming with retries/backoff
last_err: Optional[Exception] = None
for attempt in range(self.max_retries):
    try:
        if update_status:
            update_status("Submitting request…")
        resp = self.client.chat.completions.create(
            **payload,
            extra_headers=self.extra_headers,
            timeout=self.timeout_seconds,
        )
        if update_status:
            update_status("Decoding response…")
        return self._extract_image_bytes(resp)
    except Exception as e:
        last_err = e
        # Don't retry on 429 rate limit errors
        if "429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower():
            break
        if attempt >= self.max_retries - 1:
            break
        if update_status:
            update_status(f"Retrying… ({attempt + 1}/{self.max_retries - 1})")
        time.sleep(1.5 * (attempt + 1))

# Exhausted retries
raise self._handle_api_error(last_err or RuntimeError("Unknown API error."))
```

### Enhanced Error Mapping

```python
def _handle_api_error(self, error: Exception) -> Exception:
    msg = str(error)
    low = msg.lower()
    
    # Enhanced 429 handling with rate limit details
    if "429" in msg or "rate" in low or "quota" in low:
        rate_limit_info = self._extract_rate_limit_info(error)
        if rate_limit_info:
            return RuntimeError(f"Rate limited: {rate_limit_info}")
        return RuntimeError(f"Rate limited. Debug info: {debug_info}")
    
    if "401" in msg or "unauthorized" in low:
        return RuntimeError("Invalid or missing OpenRouter API key. Check your settings.")
    if "404" in msg or "not found" in low:
        return RuntimeError(f"Model not found: {self.model}. Verify the model name.")
    if "timeout" in low:
        return RuntimeError("Generation timed out. Try smaller/ fewer images or a shorter prompt.")
    if "safety" in low or "blocked" in low:
        return RuntimeError("Request blocked by safety filters. Adjust your prompt/content.")
    return RuntimeError(f"API error: {msg}")
```

## Usage Examples

### Basic Image Generation

```python
# Initialize client
client = OpenRouterClient(
    api_key="your_openrouter_api_key",
    model="google/gemini-2.5-flash-image-preview:free"
)

# Generate image from text prompt
image_bytes = client.generate_image(
    image_inputs=[],
    prompt="Create a beautiful landscape with mountains and a lake",
    update_status=lambda msg: print(f"Status: {msg}")
)
```

### Image-to-Image Transformation

```python
# Load input image
with open("input.jpg", "rb") as f:
    input_image_bytes = f.read()

# Transform image
result = client.generate_image_with_text(
    image_inputs=input_image_bytes,
    prompt="Transform this into a watercolor painting",
    update_status=lambda msg: print(f"Status: {msg}")
)

# Save result
with open("output.png", "wb") as f:
    f.write(result.image_bytes)
```

### Streaming with Status Updates

```python
def status_callback(message: str):
    print(f"Generation status: {message}")

# Streaming generation
image_bytes = client.generate_image(
    image_inputs=input_image_bytes,
    prompt="Create a futuristic cityscape",
    stream=True,
    update_status=status_callback
)
```

## Configuration and Environment

### Required Environment Variables

```bash
OPENROUTER_API_KEY=your_api_key_here
MODEL_NAME=google/gemini-2.5-flash-image-preview:free
OPENROUTER_API_URL=https://openrouter.ai/api/v1
GENERATION_TIMEOUT_SECONDS=120
APP_REFERER=https://yourapp.example
APP_TITLE=AI Image Transformer
```

### Model Selection

- **Free Tier**: `google/gemini-2.5-flash-image-preview:free`
- **Paid Tier**: `google/gemini-2.5-flash-image-preview`

## Key Features and Capabilities

### 1. Multi-Image Support
- Single image input: `bytes`
- Multiple images: `List[bytes]`
- Typed images: `List[Tuple[bytes, str]]` (with MIME types)

### 2. Robust Response Parsing
- Handles OpenRouter-specific extensions
- Falls back to standard multimodal content
- Deep recursive search for nested data URLs
- String-based data URL extraction

### 3. Streaming Support
- Real-time status updates
- Incremental image delivery
- Graceful error handling during streaming

### 4. Error Recovery
- Exponential backoff retry logic
- Rate limit detection and handling
- Detailed error information extraction
- Safety filter detection

### 5. Performance Optimizations
- Efficient base64 encoding/decoding
- Minimal memory footprint for large images
- Timeout handling for long-running requests
- Connection pooling through OpenAI SDK

## Integration Points

### 1. Keyframe Generation (`keyframev2.py`, `keyframev3.py`)
- Architectural keyframe generation
- Video frame analysis and transformation
- Batch processing capabilities

### 2. Outfit Swapping (`outfit_swap.py`)
- Fashion image transformation
- Style transfer applications
- Clothing item replacement

### 3. Core API Client (`src/core/api_client.py`)
- Centralized API management
- Shared configuration
- Common error handling

## Best Practices

### 1. Image Input Optimization
- Resize large images before sending
- Use appropriate MIME types
- Compress images for faster transmission

### 2. Error Handling
- Always implement status callbacks
- Handle rate limits gracefully
- Provide user-friendly error messages

### 3. Performance Considerations
- Use streaming for long operations
- Implement proper timeout handling
- Cache results when appropriate

### 4. Security
- Never expose API keys in code
- Use environment variables
- Implement proper input validation

## Troubleshooting

### Common Issues

1. **Rate Limiting**: Implement exponential backoff
2. **Timeout Errors**: Increase timeout or reduce image size
3. **Safety Filters**: Adjust prompts to avoid blocked content
4. **Authentication**: Verify API key and model access

### Debug Information

The implementation includes extensive debug logging:
- Response structure analysis
- Content type detection
- Image URL extraction paths
- Error context preservation

## Future Enhancements

### Planned Improvements
1. **Batch Processing**: Multiple image generation in single request
2. **Caching**: Response caching for repeated requests
3. **Metrics**: Performance monitoring and analytics
4. **Custom Models**: Support for fine-tuned models

### API Evolution
- Monitor OpenRouter API changes
- Adapt to new GEMINI model versions
- Implement new response formats
- Enhanced error reporting

## Conclusion

The GEMINI FLASH 2.5 implementation in NanoBanana v2 provides a robust, production-ready solution for image generation and transformation. The multi-layered response parsing ensures compatibility with various API response formats, while the streaming support enables real-time user feedback. The comprehensive error handling and retry mechanisms make the system resilient to network issues and API limitations.

The implementation successfully abstracts the complexity of the OpenRouter API and GEMINI model integration, providing a clean, Pythonic interface for image generation tasks across multiple application domains.
