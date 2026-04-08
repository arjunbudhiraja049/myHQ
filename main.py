"""
myHQ Office Leasing Newsletter — Main Orchestrator

Run once (e.g., from cron or GitHub Actions):
  python main.py

Or for a specific region only:
  python main.py --region delhi_ncr

Or dry-run (no emails sent):
  python main.py --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything else
load_dotenv(Path(__file__).parent / ".env")

from newsletter.config import REGIONS
from newsletter.news_fetcher import fetch_region_news
from newsletter.content_curator import vet_articles, generate_newsletter
from newsletter.subscriber_manager import SubscriberManager
from newsletter.email_sender import send_newsletter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("newsletter.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def _edition_number() -> int:
    """
    Simple incrementing edition number based on fortnights since Jan 1 2025.
    """
    start = datetime(2025, 1, 1)
    now = datetime.now()
    delta_days = (now - start).days
    return max(1, delta_days // 14 + 1)


def _date_range() -> str:
    from datetime import timedelta
    now = datetime.now()
    start = now.replace(day=1) if now.day <= 14 else now.replace(day=15)
    end = start + timedelta(days=13)
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"


def run_newsletter_pipeline(
    regions: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Full pipeline: fetch → vet → generate → send for each region.

    regions: list of region keys to process. Defaults to all 4 regions.
    dry_run: if True, renders and logs but does not send emails.

    Returns a summary dict {region: {"sent": N, "failed": N, "skipped": N}}.
    """
    if regions is None:
        regions = list(REGIONS.keys())

    dry_run = dry_run or os.environ.get("DRY_RUN", "false").lower() == "true"
    edition = _edition_number()
    date_range = _date_range()
    subscriber_manager = SubscriberManager()

    summary = {}

    for region_key in regions:
        region_display = REGIONS[region_key]["display"]
        logger.info("=" * 60)
        logger.info("Processing region: %s", region_display)
        logger.info("=" * 60)

        # ---- 1. Fetch news ----
        logger.info("[1/4] Fetching news …")
        articles = fetch_region_news(region_key)
        if not articles:
            logger.warning("No articles fetched for %s — skipping region", region_display)
            summary[region_key] = {"sent": 0, "failed": 0, "skipped": 0, "note": "no articles"}
            continue

        # ---- 2. Vet with Claude ----
        logger.info("[2/4] Vetting %d articles with Claude …", len(articles))
        vetted = vet_articles(articles, region_key)
        if not vetted:
            logger.warning(
                "Zero relevant articles after vetting for %s — skipping", region_display
            )
            summary[region_key] = {"sent": 0, "failed": 0, "skipped": 0, "note": "no vetted articles"}
            continue

        # ---- 3. Generate newsletter ----
        logger.info("[3/4] Generating newsletter content …")
        newsletter = generate_newsletter(
            vetted_articles=vetted,
            region_key=region_key,
            edition_number=edition,
            date_range=date_range,
        )

        # ---- 4. Send emails ----
        logger.info("[4/4] Fetching subscribers and sending …")
        subscribers = subscriber_manager.get_active_subscribers(region_key)
        logger.info(
            "Found %d active subscribers for %s", len(subscribers), region_display
        )

        if not subscribers:
            logger.warning("No subscribers for %s — skipping send", region_display)
            summary[region_key] = {"sent": 0, "failed": 0, "skipped": 0, "note": "no subscribers"}
            continue

        result = send_newsletter(
            newsletter=newsletter,
            subscribers=subscribers,
            dry_run=dry_run,
        )
        summary[region_key] = result

    # ---- Final summary ----
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — Summary:")
    total_sent = total_failed = 0
    for rk, r in summary.items():
        logger.info(
            "  %s: sent=%s failed=%s skipped=%s %s",
            REGIONS[rk]["display"],
            r.get("sent", 0),
            r.get("failed", 0),
            r.get("skipped", 0),
            f"[{r['note']}]" if "note" in r else "",
        )
        total_sent += r.get("sent", 0)
        total_failed += r.get("failed", 0)
    logger.info("TOTAL: %d sent, %d failed", total_sent, total_failed)
    logger.info("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(description="myHQ Newsletter Pipeline")
    parser.add_argument(
        "--region",
        choices=list(REGIONS.keys()),
        help="Run only for this region (default: all regions)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render newsletters but do not send emails",
    )
    args = parser.parse_args()

    regions = [args.region] if args.region else None
    run_newsletter_pipeline(regions=regions, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
