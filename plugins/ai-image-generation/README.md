# AI Image Generation Plugin

Helps integrate AI-powered image generation into applications and scripts.

## What It Does

Claude automatically uses this skill when a task involves generating images with
an AI model — writing code that calls an image generation API, choosing between
providers, engineering prompts, or handling generated image output.

Covers:

- Provider APIs: OpenAI Images (`gpt-image-1`), Stability AI, Replicate
- Authentication, request/response shapes, and error handling for each provider
- Prompt engineering guidance for image models
- Safe handling of API keys, user-supplied prompts, and generated output
- A runnable example script for calling the OpenAI Images API

## Usage

```
"Add an endpoint that generates a product thumbnail from a text prompt"
"Write a script that batch-generates images with the OpenAI Images API"
"Help me pick between Stability AI and Replicate for image generation"
"My image generation calls keep failing with a content policy error, why?"
```

## Contents

- `skills/ai-image-generation/SKILL.md` — core guidance and workflow
- `skills/ai-image-generation/references/providers.md` — per-provider API details
- `skills/ai-image-generation/scripts/generate_image_openai.py` — example script
