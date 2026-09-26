# Image Generation Provider Reference

Details for the three providers covered by this skill. Use whichever section
matches the project's existing dependency or the user's stated preference.

## OpenAI Images API

- **Endpoint**: `POST https://api.openai.com/v1/images/generations`
- **Auth**: `Authorization: Bearer $OPENAI_API_KEY`
- **Model**: `gpt-image-1`
- **Request body**:
  ```json
  {
    "model": "gpt-image-1",
    "prompt": "a red fox sitting in snow, watercolor illustration",
    "size": "1024x1024",
    "n": 1
  }
  ```
  Valid `size` values: `1024x1024`, `1024x1536`, `1536x1024`, `auto`.
- **Response**: `data[].b64_json` — base64-encoded PNG. Decode and write to
  disk; there is no URL field for this model.
- **Edits/variations**: `POST /v1/images/edits` accepts `multipart/form-data`
  with an `image` file, optional `mask`, and a `prompt`.
- **Errors**: a rejected prompt returns HTTP 400 with
  `error.code == "content_policy_violation"`. Rate limits return HTTP 429
  with a `Retry-After` header.

## Stability AI

- **Endpoint**: `POST https://api.stability.ai/v2beta/stable-image/generate/core`
  (or `/ultra`, `/sd3` for other model tiers)
- **Auth**: `Authorization: Bearer $STABILITY_API_KEY`
- **Request**: `multipart/form-data` with fields `prompt`, `output_format`
  (`png`/`jpeg`/`webp`), optional `negative_prompt`, `aspect_ratio`, `seed`,
  `style_preset` (e.g. `photographic`, `digital-art`, `anime`).
- **Response**: raw image bytes when `Accept: image/*` is sent; otherwise a
  JSON body with `image` as base64 and a `finish_reason` field — check that
  `finish_reason == "SUCCESS"` (a value of `CONTENT_FILTERED` means the
  output was filtered and should be surfaced to the caller, not silently
  discarded).
- **Image-to-image**: same endpoint family accepts an `image` file plus a
  `strength` parameter (0-1) controlling how much the input is preserved.

## Replicate

Replicate is asynchronous: creating a prediction returns immediately with a
`status` of `starting`, and the caller must poll until it reaches a terminal
state.

- **Create**: `POST https://api.replicate.com/v1/predictions`
  - **Auth**: `Authorization: Bearer $REPLICATE_API_TOKEN`
  - **Body**:
    ```json
    {
      "version": "<model-version-id>",
      "input": { "prompt": "a red fox sitting in snow" }
    }
    ```
- **Poll**: `GET https://api.replicate.com/v1/predictions/{id}` until
  `status` is `succeeded`, `failed`, or `canceled`. On success, `output` is
  typically a list of image URLs to download.
- **Recommended polling**: exponential backoff starting at ~1s, capped
  around 5s, with an overall timeout (e.g. 60-120s depending on the model) —
  do not poll in a tight loop.
- **Model selection**: Replicate hosts many third-party models (SDXL, Flux,
  etc.); the caller must know the specific model `version` id to use, found
  on the model's Replicate page.

## Choosing Size / Aspect Ratio

Match the output dimensions to where the image will be used (thumbnail,
hero banner, square social post) rather than always requesting the largest
size — larger images cost more and take longer to generate.
