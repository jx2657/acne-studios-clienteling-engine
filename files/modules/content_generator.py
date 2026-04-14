"""
content_generator.py
Handles all AI content generation: blog posts, persona newsletters, image prompts.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from openai import OpenAI, OpenAIError

PERSONAS = {
    "VIP": {
        "label": "VIP Segment",
        "tone": "Exclusivity and prestige. Address this client as a long-standing, valued patron. "
                "Reference private previews, early access, and bespoke service. Formal, aspirational.",
    },
    "REGULAR": {
        "label": "Regular Segment",
        "tone": "Inspiration and style discovery. Warm, editorial, community-focused. "
                "Invite them deeper into the Acne Studios world.",
    },
    "AT_RISK": {
        "label": "At-Risk Segment",
        "tone": "Re-engagement and gentle urgency. Remind them what they loved. "
                "Use nostalgia and a compelling limited-time hook without being pushy.",
    },
}

HALLEROED_FALLBACK = (
    "https://images.unsplash.com/photo-1497366216548-37526070297c"
    "?auto=format&fit=crop&q=80&w=2069"
)

CONTENT_DIR = Path("data/content")
CONTENT_DIR.mkdir(parents=True, exist_ok=True)


def _require_client(client: OpenAI | None) -> OpenAI:
    """Raise a clear error if the API client is not initialised."""
    if client is None:
        raise ValueError("OpenAI client is not initialised. Please provide a valid API key.")
    return client


# ── Blog ──────────────────────────────────────────────────────────────────────

def generate_blog(product: str, client: OpenAI | None) -> str:
    """Generate a 400-word luxury editorial blog for the given product."""
    c = _require_client(client)
    system = (
        "You are the editorial director of Acne Studios. Write in a precise, poetic, "
        "Scandinavian minimalist voice. No fluff. No clichés."
    )
    user = (
        f"Write a luxury fashion editorial blog post about '{product}' for Acne Studios. "
        "Start with a 5-point outline, then write the full draft below it (400-600 words). "
        "Include: a compelling headline, the design philosophy behind the piece, "
        "how it fits into contemporary culture, and a closing that invites the reader into the brand world."
    )
    try:
        resp = c.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.75,
        )
        return resp.choices[0].message.content
    except OpenAIError as e:
        raise RuntimeError(f"Blog generation failed: {e}") from e


# ── Newsletters ───────────────────────────────────────────────────────────────

def generate_newsletters(blog: str, product: str, client: OpenAI | None) -> dict[str, str]:
    """
    Generate three persona-specific newsletter versions from the blog.
    Returns a dict keyed by persona code (VIP / REGULAR / AT_RISK).
    """
    c = _require_client(client)
    system = (
        "You are a CRM copywriter for Acne Studios. "
        "You write concise, on-brand email newsletters — never longer than 200 words."
    )
    results: dict[str, str] = {}
    for key, meta in PERSONAS.items():
        user = (
            f"Adapt the following editorial blog into a newsletter for the **{meta['label']}** customer segment.\n"
            f"Tone: {meta['tone']}\n"
            f"Product: {product}\n\n"
            "---\n"
            f"{blog}\n"
            "---\n\n"
            "Output format:\n"
            "Subject: <subject line>\n\n"
            "<email body — max 200 words>"
        )
        try:
            resp = c.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.7,
            )
            results[key] = resp.choices[0].message.content
        except OpenAIError as e:
            results[key] = f"[Generation failed: {e}]"
    return results


# ── Image ─────────────────────────────────────────────────────────────────────

def generate_editorial_image(product: str, client: OpenAI | None) -> str:
    """
    Generate a DALL-E 3 editorial image URL.
    Falls back to the Unsplash placeholder on any error.
    """
    c = _require_client(client)
    prompt = (
        f"A high-end artistic photograph of '{product}'. "
        "Brutalist minimalist Scandinavian gallery. Soft pink directional lighting, "
        "raw concrete background, high fashion editorial. No text, no logos."
    )
    try:
        res = c.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return res.data[0].url
    except OpenAIError as e:
        print(f"[WARN] Image generation failed ({e}). Using fallback.")
        return HALLEROED_FALLBACK


# ── Persistence ───────────────────────────────────────────────────────────────

def save_campaign_content(product: str, blog: str, newsletters: dict[str, str]) -> Path:
    """
    Save generated content to a structured JSON file in data/content/.
    Returns the file path.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    slug = product.lower().replace(" ", "_")[:40]
    filename = CONTENT_DIR / f"{timestamp}_{slug}.json"

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "product": product,
        "blog": blog,
        "newsletters": newsletters,
    }
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return filename


def load_recent_campaigns(n: int = 5) -> list[dict]:
    """Load the n most recent saved campaign content files."""
    files = sorted(CONTENT_DIR.glob("*.json"), reverse=True)[:n]
    campaigns = []
    for f in files:
        try:
            campaigns.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return campaigns
