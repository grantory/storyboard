Project Maestro v2 – API Contracts

Providers

- OpenRouter Chat Completions endpoint
  - Context/Director: text+image for Director; text+5 images for Context
  - Image: google/gemini-2.5-flash-image-preview with modalities ["image","text"]

Context (gpt-5-mini)

Request (conceptual):

messages: [
  { role: "user", content: [
      { type: "text", text: <context instructions> },
      { type: "image_url", image_url: { url: <dataUrl-frame-1> } },
      ... x5 frames ...
  ]}
]

Response: short paragraph string (we accept freeform text)

Director (gpt-5-mini)

messages: [
  { role: "user", content: [
      { type: "text", text: <director instructions + context paragraph> },
      { type: "image_url", image_url: { url: <dataUrl-middle-frame> } }
  ]}
]

Response: 5 lines formatted as:

SHOT 1: ...
SHOT 2: ...
...

Image Generation (google/gemini-2.5-flash-image-preview)

messages: [
  { role: "user", content: [
      { type: "text", text: <concise image generation instruction> },
      { type: "image_url", image_url: { url: <dataUrl-style-image> } }
  ]}
], extra_body: { modalities: ["image","text"] }

Response: image data URL in choices[0].message.images[0].image_url.url or within choices[0].message.content items

Errors

- 400/401/429/5xx → Show inline error; allow retry
- Timeouts → cancel just that row; others continue


