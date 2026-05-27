"""
Step 1: Send a local image to GPT-4o-mini and get structured listing JSON back.
"""

import base64
import json
import sys
from pathlib import Path

from openai import OpenAI

import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

STOP_WORDS_BLOCK = ", ".join(f'"{w}"' for w in config.AMAZON_STOP_WORDS)

SYSTEM_PROMPT = f"""You are an expert Amazon Merch on Demand copywriter.
Your job: analyze the image and produce a JSON listing for a print-on-demand product.

STRICT AMAZON RULES — violations will get the listing rejected:
- FORBIDDEN words/phrases: {STOP_WORDS_BLOCK}
- Never mention the product type ("shirt", "tee", "apparel", "clothing", "wear", "garment")
- No superlatives: no "best", "perfect", "amazing", "unique", "one of a kind"
- No claims about quality, materials, or sustainability
- No calls to action: "buy", "shop", "order", "get yours", "click"
- No references to other people, brands, or copyrighted characters

CHARACTER LIMITS — count carefully, do not exceed:
- title: max {config.TITLE_MAX_CHARS} characters (aim for 80–100, keyword-rich)
- bullet_1 … bullet_5: max {config.BULLET_MAX_CHARS} characters each
- description: max {config.DESCRIPTION_MAX_CHARS} characters
- brand: max {config.BRAND_MAX_CHARS} characters
- keywords: comma-separated, max {config.KEYWORDS_MAX_CHARS} characters total, no repeats from title

OUTPUT FORMAT — return ONLY valid JSON, no markdown, no explanation:
{{
  "title": "...",
  "bullet_1": "...",
  "bullet_2": "...",
  "bullet_3": "...",
  "bullet_4": "...",
  "bullet_5": "...",
  "description": "...",
  "keywords": "word1, word2, word3, ..."
}}"""

USER_PROMPT = (
    "Analyze this image. Write a commercial listing for it following the rules above. "
    "Return only the JSON object."
)


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_listing_from_image(image_path: str | Path) -> dict:
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = image_path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    b64 = encode_image(image_path)

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    {"type": "text", "text": USER_PROMPT},
                ],
            },
        ],
        max_tokens=800,
        temperature=0.7,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if model wraps output anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    listing = json.loads(raw)
    listing["_image_file"] = image_path.name

    # Normalise keywords to string regardless of what model returns
    kw = listing.get("keywords", "")
    if isinstance(kw, list):
        kw = ", ".join(kw)
    listing["keywords"] = kw

    # Hard-truncate to Amazon limits (safety net — prompt should prevent this)
    listing = _enforce_limits(listing)
    return listing


def _enforce_limits(listing: dict) -> dict:
    limits = {
        "title":       config.TITLE_MAX_CHARS,
        "bullet_1":    config.BULLET_MAX_CHARS,
        "bullet_2":    config.BULLET_MAX_CHARS,
        "bullet_3":    config.BULLET_MAX_CHARS,
        "bullet_4":    config.BULLET_MAX_CHARS,
        "bullet_5":    config.BULLET_MAX_CHARS,
        "description": config.DESCRIPTION_MAX_CHARS,
        "keywords":    config.KEYWORDS_MAX_CHARS,
    }
    truncated = []
    for field, limit in limits.items():
        val = listing.get(field, "")
        if val and len(val) > limit:
            listing[field] = val[:limit].rsplit(" ", 1)[0]  # cut at word boundary
            truncated.append(field)
    if truncated:
        listing["_truncated"] = truncated
    return listing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_vision.py <path_to_image>")
        sys.exit(1)

    result = get_listing_from_image(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
