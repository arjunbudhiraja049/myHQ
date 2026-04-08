"""
AI content pipeline powered by Google Gemini (free tier).

Two-step process:
  1. vet_articles()       — filters raw RSS articles to only relevant ones
  2. generate_newsletter() — writes the full newsletter JSON
"""

import json
import logging
import os
import re

import google.generativeai as genai

from .config import REGIONS

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


# ---------------------------------------------------------------------------
# STEP 1 — Vetting
# ---------------------------------------------------------------------------

def vet_articles(articles: list[dict], region_key: str) -> list[dict]:
    """
    Send raw articles to Gemini and get back only those relevant
    to office/commercial real estate in the given region.
    Returns filtered list with a "category" key added to each article.
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

    model = _get_model()
    logger.info("Vetting %d articles for %s …", len(articles), region_key)

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

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
    """
    Ask Gemini to write the full newsletter from vetted articles.
    Returns a structured dict ready for HTML template rendering.
    """
    region_display = REGIONS[region_key]["display"]
    areas = REGIONS[region_key]["areas"]

    # Group articles by category
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
They are time-poor senior professionals. Tone: sharp, confident, market-intelligent.
Not dry. Engaging enough they read it end to end.

Source articles:
{articles_text if articles_text else "Limited news this fortnight."}

Sub-areas for spotlight: {areas_list}

Write the newsletter as a single valid JSON object. No markdown, no code fences, just JSON.

{{
  "region_display": "{region_display}",
  "edition": "Edition #{edition_number} | {date_range}",
  "intro": "<2-3 sentence punchy intro — what is the big story this fortnight>",
  "market_pulse": "<3-4 sentences on overall office market health — vacancy, absorption, rent trend>",
  "transactions": [
    {{
      "headline": "<deal headline>",
      "body": "<2-3 sentences: company, sq ft, location, terms>",
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
- Ground every insight in the source articles — do not fabricate.
- Return ONLY the JSON object."""

    model = _get_model()
    logger.info("Generating newsletter for %s (edition #%d) …", region_key, edition_number)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )

    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        newsletter = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw:\n%s", exc, raw[:400])
        newsletter = {
            "region_display": region_display,
            "edition": f"Edition #{edition_number} | {date_range}",
            "intro": f"Your fortnightly market update for {region_display} is here.",
            "market_pulse": "Market data is being compiled. Full update in next edition.",
            "transactions": [],
            "developer_updates": [],
            "people_movement": [],
            "quick_bytes": ["Newsletter content processing. Please check again shortly."],
            "area_spotlights": {},
            "outro": "More insights coming in the next fortnight. Stay tuned.",
        }

    logger.info("Newsletter generated for %s", region_key)
    return newsletter
