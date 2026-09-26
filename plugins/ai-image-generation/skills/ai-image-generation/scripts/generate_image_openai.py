#!/usr/bin/env python3
"""Generate an image from a text prompt using the OpenAI Images API.

Usage:
    OPENAI_API_KEY=sk-... python generate_image_openai.py "a red fox in snow" out.png
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"


def generate_image(prompt: str, size: str = "1024x1024") -> bytes:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    payload = json.dumps(
        {"model": MODEL, "prompt": prompt, "size": size, "n": 1}
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        error_body = json.loads(exc.read() or b"{}")
        code = error_body.get("error", {}).get("code")
        message = error_body.get("error", {}).get("message", str(exc))
        if code == "content_policy_violation":
            raise RuntimeError(f"Prompt rejected by content policy: {message}") from exc
        if exc.code == 429:
            raise RuntimeError("Rate limited by OpenAI Images API; retry with backoff") from exc
        raise RuntimeError(f"OpenAI Images API request failed: {message}") from exc

    b64_image = body["data"][0]["b64_json"]
    return base64.b64decode(b64_image)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <prompt> <output-path>", file=sys.stderr)
        sys.exit(1)

    prompt, output_path = sys.argv[1], sys.argv[2]
    image_bytes = generate_image(prompt)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"Wrote {len(image_bytes)} bytes to {output_path}")


if __name__ == "__main__":
    main()
