"""
AI content pipeline powered by Claude (claude-opus-4-6).

Two-step process:
  1. vet_articles()      — filters raw RSS articles to only relevant ones
  2. generate_newsletter() — writes the full newsletter JSON

The newsletter JSON schema:
{
    "region_display": str,
    "edition": str,
    "intro": str,
    "market_pulse": str,
    "transactions": [{"headline": str, "body": str, "takeaway": str}],
    "developer_updates": [{"headline": str, "body": str, "takeaway": str}],
    "people_movement": [{"headline": str, "body": str, "takeaway": str}],
    "quick_bytes": [str],
    "area_spotlights": {area_name: str},
    "outro": str,
}
"""

import json
import logging
import os
from datetime import datetime

import anthropic

from .config import REGIONS

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


# ---------------------------------------------------------------------------
# STEP 1 — Vetting
# ---------------------------------------------------------------------------

def vet_articles(articles: list[dict], region_key: str) -> list[dict]:
    """
    Send raw articles to Claude and get back only those that are relevant
    to office / commercial real estate in the given region.

    Returns a filtered list with an added "category" key on each article.
    """
    if not articles:
        return []

    region_display = REGIONS[region_key]["display"]

    # Build a compact representation for Claude to evaluate
    numbered = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']} | {a['summary'][:200]}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a senior research analyst at myHQ, India's leading managed office platform.

I need you to filter and categorise the following {len(articles)} news items to only keep articles
that are **directly relevant** to office and commercial real estate in **{region_display}**.

RELEVANT includes:
- Office leasing deals, transactions, pre-leases
- Commercial real estate supply/demand data
- New office park / IT park announcements or completions
- Developer news (launch, delivery, acquisition of office assets)
- Senior leadership moves in real estate or occupier companies
- Market commentary: rentals, vacancy, absorption for office/commercial

NOT RELEVANT (exclude):
- Residential real estate
- Retail / mall / hospitality news (unless it explicitly impacts office)
- Pure macro economy news with no office angle
- International news with no India/regional relevance

For each RELEVANT article, also assign exactly one category from:
  transactions | developer_updates | people_movement | market_trends | quick_bytes

"quick_bytes" is for genuine news items but shorter/less impactful pieces.

Return ONLY a JSON array with this exact structure (no markdown, no explanation):
[
  {{"index": 1, "category": "transactions"}},
  {{"index": 3, "category": "people_movement"}},
  ...
]

Articles to evaluate:
{numbered}
"""

    client = _get_client()
    logger.info("Vetting %d articles for region %s …", len(articles), region_key)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(
        (b.text for b in response.content if b.type == "text"), "[]"
    )

    try:
        selections = json.loads(text.strip())
    except json.JSONDecodeError:
        # Fallback: try to extract JSON array from text
        import re
        match = re.search(r"\[.*\]", text, re.DOTALL)
        selections = json.loads(match.group(0)) if match else []

    # Map back to original articles
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
    Given vetted articles, ask Claude to write the full newsletter.
    Returns a structured dict ready for template rendering.

    Also generates area-specific spotlights for each major area in the region.
    """
    region_display = REGIONS[region_key]["display"]
    areas = REGIONS[region_key]["areas"]

    # Group articles by category for the prompt
    grouped: dict[str, list[str]] = {
        "transactions": [],
        "developer_updates": [],
        "people_movement": [],
        "market_trends": [],
        "quick_bytes": [],
    }
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

    prompt = f"""You are the lead analyst writing the fortnightly **myHQ Market Insights** newsletter
for real estate professionals and business decision-makers covering **{region_display}**.

Edition #{edition_number} | {date_range}

Your audience is:
- CRE brokers, property consultants, and developers
- Corporate real estate heads and business POCs making leasing decisions
- They are time-poor senior professionals who value sharp, data-backed insights
- They want to know: what's happening, what it means for their portfolio / decisions

Tone: confident, sharp, market-intelligent — like a smart colleague giving you the real picture.
Not dry. Not salesy. Engaging enough that they read it end to end.

---
Source articles (already filtered for relevance):
{articles_text if articles_text else "Limited news this fortnight — write a brief but useful market summary."}

---
Sub-areas for spotlight consideration: {areas_list}

---
Write the newsletter as a **single valid JSON object** (no markdown, no code fences).

Schema:
{{
  "region_display": "{region_display}",
  "edition": "Edition #{edition_number} | {date_range}",
  "intro": "<2-3 sentence punchy intro — what's the big story this fortnight?>",
  "market_pulse": "<3-4 sentences on overall office market health in {region_display} — vacancy, absorption, rent trend, demand signals>",
  "transactions": [
    {{
      "headline": "<deal headline, factual and specific>",
      "body": "<2-3 sentences with details: company, sq ft, location, deal terms if known>",
      "takeaway": "<1 sentence: what this signals for the market>"
    }}
  ],
  "developer_updates": [
    {{
      "headline": "<project/developer headline>",
      "body": "<2-3 sentences>",
      "takeaway": "<1 sentence market signal>"
    }}
  ],
  "people_movement": [
    {{
      "headline": "<person + role change>",
      "body": "<1-2 sentences on the move and its context>",
      "takeaway": "<1 sentence on why this matters>"
    }}
  ],
  "quick_bytes": [
    "<One crisp sentence per item — 4 to 6 short bullets of other relevant news>"
  ],
  "area_spotlights": {{
    "<area_name>": "<2-3 sentences on what's happening specifically in this area this fortnight>"
  }},
  "outro": "<1-2 sentences signing off — forward-looking, what to watch in the next fortnight>"
}}

Rules:
- Only include sections where you have real content from the articles. Empty arrays [] are fine.
- area_spotlights: pick the TOP 3-5 most newsworthy areas from {areas_list} based on the articles.
- Every insight must be grounded in the source articles — do not fabricate deals or numbers.
- If data is thin for a section, write less but keep it accurate.
- Return ONLY the JSON object. No preamble, no explanation.
"""

    client = _get_client()
    logger.info("Generating newsletter for %s (edition #%d) …", region_key, edition_number)

    # Stream for long output — get final message
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    raw = next(
        (b.text for b in response.content if b.type == "text"), "{}"
    )

    # Strip any accidental code fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        newsletter = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw output:\n%s", exc, raw[:500])
        # Return a minimal fallback structure
        newsletter = {
            "region_display": region_display,
            "edition": f"Edition #{edition_number} | {date_range}",
            "intro": f"Here is your fortnightly market update for {region_display}.",
            "market_pulse": "Market data is being compiled. Check back for the full update.",
            "transactions": [],
            "developer_updates": [],
            "people_movement": [],
            "quick_bytes": ["Newsletter content is being processed. Please check again shortly."],
            "area_spotlights": {},
            "outro": "Stay tuned for more insights in the next edition.",
        }

    logger.info("Newsletter generated for %s", region_key)
    return newsletter
