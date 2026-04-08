"""
Fetches office leasing news from Google News RSS and curated real estate feeds.
Returns a flat list of raw article dicts for a given region.
"""

import feedparser
import requests
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from .config import REGIONS, FIXED_RSS_FEEDS, GOOGLE_NEWS_RSS, NEWSLETTER_SETTINGS

logger = logging.getLogger(__name__)

_LOOKBACK = timedelta(days=NEWSLETTER_SETTINGS["lookback_days"])


def _parse_feed(url: str) -> list[dict]:
    """Parse an RSS feed URL and return raw entry dicts."""
    try:
        feed = feedparser.parse(url)
        entries = []
        for e in feed.entries:
            published = None
            if hasattr(e, "published_parsed") and e.published_parsed:
                published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
            entries.append(
                {
                    "title": e.get("title", "").strip(),
                    "summary": e.get("summary", "").strip(),
                    "link": e.get("link", ""),
                    "source": feed.feed.get("title", url),
                    "published": published,
                }
            )
        logger.info("Fetched %d entries from %s", len(entries), url[:80])
        return entries
    except Exception as exc:
        logger.warning("Failed to parse feed %s: %s", url[:80], exc)
        return []


def _is_recent(entry: dict) -> bool:
    """Return True if the article was published within the lookback window."""
    if not entry.get("published"):
        return True  # include if we can't tell
    cutoff = datetime.now(timezone.utc) - _LOOKBACK
    return entry["published"] >= cutoff


def fetch_region_news(region_key: str) -> list[dict]:
    """
    Fetch all news relevant to *region_key* from:
      1. Google News RSS (one feed per region search term)
      2. Fixed Indian real estate RSS feeds

    Returns deduplicated articles published in the last 14 days,
    capped at NEWSLETTER_SETTINGS["max_articles_per_region"].
    """
    region = REGIONS[region_key]
    all_articles: list[dict] = []

    # --- Google News per search term ---
    for term in region["search_terms"]:
        url = GOOGLE_NEWS_RSS.format(query=quote_plus(term))
        all_articles.extend(_parse_feed(url))

    # --- Fixed real estate feeds ---
    for url in FIXED_RSS_FEEDS:
        all_articles.extend(_parse_feed(url))

    # Deduplicate by title (case-insensitive)
    seen: set[str] = set()
    unique: list[dict] = []
    for a in all_articles:
        key = a["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    # Keep only recent articles
    recent = [a for a in unique if _is_recent(a)]

    cap = NEWSLETTER_SETTINGS["max_articles_per_region"]
    logger.info(
        "Region %s: %d unique recent articles (capped at %d)",
        region_key,
        len(recent),
        cap,
    )
    return recent[:cap]
