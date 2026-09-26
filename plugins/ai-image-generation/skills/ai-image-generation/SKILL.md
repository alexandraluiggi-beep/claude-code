---
name: AI Image Generation
description: This skill should be used when the user asks to "generate an image", "create an AI image", "integrate image generation", "call the OpenAI Images API", "use Stability AI" or "Replicate for images", "write a script to generate images", or needs guidance on prompt engineering for image models, choosing an image generation provider, or handling generated image output safely.
version: 0.1.0
---

# AI Image Generation

This skill provides guidance for integrating AI-powered image generation into
applications, scripts, and pipelines. It covers picking a provider, calling
its API correctly, engineering effective prompts, and handling keys, input,
and output safely. It does not generate images itself — Claude has no
built-in image generation capability — it writes and wires up code that
calls an external image generation service on the user's behalf.

## Choosing a Provider

Ask which provider the user wants only if it is not already implied by their
stack (an existing API key, SDK, or dependency in the project). Otherwise
default to the option that best fits the request:

| Provider | Good for | Auth |
|---|---|---|
| OpenAI Images (`gpt-image-1`) | General-purpose generation and edits, simplest integration | `OPENAI_API_KEY` |
| Stability AI | Fine-grained control (samplers, style presets, image-to-image) | `STABILITY_API_KEY` |
| Replicate | Access to many open models (SDXL, Flux, etc.) behind one API | `REPLICATE_API_TOKEN` |

See `references/providers.md` for exact endpoints, request/response shapes,
and provider-specific parameters (sizes, formats, strength, seeds).

## Workflow

1. **Confirm the provider and check for existing credentials.** Search the
   project for an existing SDK dependency or `.env` reference before adding
   a new one. Never hardcode an API key in source — read it from an
   environment variable and fail with a clear error if it is missing.
2. **Write the integration as a small, focused function** (e.g.
   `generate_image(prompt, **options) -> bytes | path`), not inline in a
   route handler or script body, so it can be reused and tested.
3. **Handle the response correctly for the provider**: OpenAI and Stability
   typically return base64-encoded image data or a URL; Replicate is
   asynchronous and requires polling a prediction until it completes. See
   `references/providers.md` for the exact shape.
4. **Handle failure modes explicitly**:
   - Content-policy rejections (the prompt was flagged) — surface a clear
     message to the caller rather than a raw stack trace.
   - Rate limiting / `429` — the caller should decide whether to retry with
     backoff or fail fast; don't add silent infinite retries.
   - Timeouts on long-running (async) generations — set an explicit poll
     timeout for Replicate-style APIs.
5. **Store or return the result appropriately**: write to disk with a
   collision-safe filename, upload to the project's existing storage layer,
   or stream bytes back to the caller — follow whatever pattern the rest of
   the codebase already uses for file/blob output.

`scripts/generate_image_openai.py` is a complete, runnable reference
implementation of steps 2-5 for the OpenAI Images API; adapt it rather than
writing the request logic from scratch.

## Prompt Engineering

Image model prompts differ from chat prompts — they describe a single scene,
not a conversation. When writing or improving a prompt on the user's behalf:

- Lead with the subject, then style, then composition/lighting/camera
  details: `"a red fox sitting in snow, watercolor illustration, soft
  morning light, shallow depth of field"`.
- Be specific about style (photo, illustration, 3D render, watercolor, etc.)
  — omitting it lets the model default inconsistently.
- Keep negative constraints ("no text", "no watermark") explicit if the
  provider supports a negative prompt parameter; otherwise fold them into
  the main prompt.
- For programmatic/templated prompts (e.g. generating product images from a
  database), keep a fixed style suffix and only vary the subject, so output
  stays visually consistent across calls.
- If a generation is rejected by content moderation, do not try to route
  around the filter — tell the user which part of the prompt likely
  triggered it and suggest a rephrase.

## Security and Safety Notes

- Treat any user-supplied text that reaches an image prompt as untrusted
  input: pass it to the provider as data, never interpolate it into a shell
  command or file path.
- Never log full API keys; if debugging a failed request, log the status
  code and error body only.
- When saving generated images from user-supplied filenames or prompts,
  sanitize the derived filename (no path traversal, no arbitrary
  extensions) before writing to disk.
- Respect the provider's usage policy — do not build workarounds for
  content-moderation rejections.

## Additional Resources

### Reference Files

- **`references/providers.md`** — endpoint URLs, request/response JSON
  shapes, and key parameters for OpenAI Images, Stability AI, and Replicate.

### Example Scripts

- **`scripts/generate_image_openai.py`** — minimal, dependency-light script
  that generates an image from a prompt via the OpenAI Images API, handles
  errors, and saves the result to disk.
