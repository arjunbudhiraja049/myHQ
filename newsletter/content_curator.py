"""
AI content pipeline using Gemini REST API directly via requests.
No google-generativeai package needed — avoids all version conflicts.
"""

import json
import logging
import os
import re

import requests

from .config import REGIONS

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _call_gemini(prompt: str) -> str:
    """Send a prompt to Gemini and return the response text. Retries on 429."""
    import time
    api_key = os.environ["GEMINI_API_KEY"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
    }
    for attempt in range(5):
        response = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=90,
        )
        if response.status_code == 429:
            wait = 30 * (attempt + 1)
            logger.info("Rate limited by Gemini. Waiting %ds before retry %d/5 …", wait, attempt + 1)
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("Gemini API rate limit not resolved after 5 retries.")


def _clean_json(text: str) -> str:
    """Strip markdown code fences if Gemini wraps output in them."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# STEP 1 — Vetting
# ---------------------------------------------------------------------------

def vet_articles(articles: list[dict], region_key: str) -> list[dict]:
    """
    Send raw articles to Gemini — get back only the relevant ones
    with a category tag on each.
    """
    if not articles:
        return []

    region_display = REGIONS[region_key]["display"]
    numbered = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']} | {a['summary'][:200]}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a senior research analyst at myHQ, India's leading managed office platform.

Filter the following {len(articles)} news items. Keep ONLY articles directly relevant to
office and commercial real estate in {region_display}.

RELEVANT: office leasing deals, commercial real estate supply/demand, new office parks,
developer news, senior leadership moves in real estate, market data on office rentals/vacancy.

NOT RELEVANT: residential, retail/mall, pure macro economy (unless office angle), international news.

For each RELEVANT article assign one category:
  transactions | developer_updates | people_movement | market_trends | quick_bytes

Return ONLY a JSON array, no explanation, no markdown:
[{{"index": 1, "category": "transactions"}}, ...]

Articles:
{numbered}"""

    logger.info("Vetting %d articles for %s …", len(articles), region_key)
    text = _clean_json(_call_gemini(prompt))

    try:
        selections = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        selections = json.loads(match.group(0)) if match else []

    vetted = []
    for sel in selections:
        idx = sel.get("index", 0) - 1
        if 0 <= idx < len(articles):
            article = dict(articles[idx])
            article["category"] = sel.get("category", "quick_bytes")
            vetted.append(article)

    logger.info("Vetted to %d relevant articles", len(vetted))
    return vetted


# ---------------------------------------------------------------------------
# STEP 2 — Newsletter generation
# ---------------------------------------------------------------------------

def generate_newsletter(
    vetted_articles: list[dict],
    region_key: str,
    edition_number: int,
    date_range: str,
) -> dict:
    """Write the full newsletter from vetted articles. Returns structured dict."""
    region_display = REGIONS[region_key]["display"]
    areas = REGIONS[region_key]["areas"]

    grouped: dict[str, list[str]] = {}
    for a in vetted_articles:
        cat = a.get("category", "quick_bytes")
        grouped.setdefault(cat, []).append(
            f"• [{a['source']}] {a['title']} — {a['summary'][:300]}"
        )

    articles_text = ""
    for cat, items in grouped.items():
        if items:
            articles_text += f"\n\n=== {cat.upper()} ===\n" + "\n".join(items)

    areas_list = ", ".join(areas)

    prompt = f"""You are the lead analyst writing the fortnightly myHQ Market Insights newsletter
for real estate professionals in {region_display}.

Edition #{edition_number} | {date_range}

Audience: CRE brokers, corporate real estate heads, business POCs making leasing decisions.
Tone: sharp, confident, market-intelligent. Not dry. Engaging enough they read it end to end.

Source articles:
{articles_text if articles_text else "Limited news this fortnight."}

Sub-areas for spotlight: {areas_list}

Write the newsletter as a single valid JSON object. No markdown, no code fences, just JSON.

{{
  "region_display": "{region_display}",
  "edition": "Edition #{edition_number} | {date_range}",
  "intro": "<2-3 sentence punchy intro>",
  "market_pulse": "<3-4 sentences on office market health — vacancy, absorption, rent trend>",
  "transactions": [
    {{
      "headline": "<deal headline>",
      "body": "<2-3 sentences>",
      "takeaway": "<1 sentence market signal>"
    }}
  ],
  "developer_updates": [
    {{
      "headline": "<headline>",
      "body": "<2-3 sentences>",
      "takeaway": "<1 sentence>"
    }}
  ],
  "people_movement": [
    {{
      "headline": "<person + role change>",
      "body": "<1-2 sentences>",
      "takeaway": "<1 sentence why it matters>"
    }}
  ],
  "quick_bytes": ["<one crisp sentence per item, 4-6 bullets>"],
  "area_spotlights": {{
    "<area_name>": "<2-3 sentences on what is happening in this area>"
  }},
  "outro": "<1-2 sentences signing off, forward-looking>"
}}

Rules:
- Only include sections with real content. Empty arrays [] are fine.
- area_spotlights: pick top 3-4 most newsworthy areas from: {areas_list}
- Ground every insight in the source articles. Do not fabricate.
- Return ONLY the JSON object, nothing else."""

    logger.info("Generating newsletter for %s (edition #%d) …", region_key, edition_number)
    text = _clean_json(_call_gemini(prompt))

    try:
        newsletter = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw:\n%s", exc, text[:400])
        newsletter = {
            "region_display": region_display,
            "edition": f"Edition #{edition_number} | {date_range}",
            "intro": f"Your fortnightly market update for {region_display}.",
            "market_pulse": "Market data is being compiled.",
            "transactions": [],
            "developer_updates": [],
            "people_movement": [],
            "quick_bytes": ["Newsletter processing. Please check again shortly."],
            "area_spotlights": {},
            "outro": "More insights in the next edition.",
        }

    logger.info("Newsletter generated for %s", region_key)
    return newsletter
