"""
Renders and sends the newsletter via SMTP.

Personalisation per subscriber:
  - Greeting with their name
  - Area spotlight matching their area (or nearest match from newsletter.area_spotlights)
  - Personalised intro line noting their focus area
"""

import logging
import os
import smtplib
import difflib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)


def _find_area_spotlight(subscriber_area: str, area_spotlights: dict) -> str:
    """
    Find the best matching area spotlight for a subscriber.
    Uses fuzzy matching on area name.
    """
    if not subscriber_area or not area_spotlights:
        return ""

    # Exact match first
    if subscriber_area in area_spotlights:
        return area_spotlights[subscriber_area]

    # Case-insensitive match
    lower_map = {k.lower(): v for k, v in area_spotlights.items()}
    if subscriber_area.lower() in lower_map:
        return lower_map[subscriber_area.lower()]

    # Fuzzy match (e.g., "Gurgaon" ≈ "Gurgaon Cyber City")
    keys = list(area_spotlights.keys())
    matches = difflib.get_close_matches(subscriber_area, keys, n=1, cutoff=0.4)
    if matches:
        return area_spotlights[matches[0]]

    return ""


def render_html(newsletter: dict, subscriber: dict) -> str:
    """Render the Jinja2 template for one subscriber."""
    template = _jinja_env.get_template("newsletter.html")

    area_spotlight = _find_area_spotlight(
        subscriber.get("area", ""),
        newsletter.get("area_spotlights", {}),
    )

    return template.render(
        newsletter=newsletter,
        subscriber_name=subscriber.get("name", "there"),
        subscriber_area=subscriber.get("area", ""),
        area_spotlight=area_spotlight,
        year=datetime.now().year,
    )


def send_newsletter(
    newsletter: dict,
    subscribers: list[dict],
    dry_run: bool = False,
) -> dict:
    """
    Send the newsletter to all subscribers.

    dry_run=True → renders HTML and logs it but does not connect to SMTP.
    Returns {"sent": N, "failed": N, "skipped": N}
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)
    from_name = os.environ.get("FROM_NAME", "myHQ Market Insights")

    sent = failed = skipped = 0
    region_display = newsletter.get("region_display", "")
    edition = newsletter.get("edition", "")
    subject = f"[myHQ] {region_display} Market Insights | {edition}"

    # Attempt a single SMTP connection for all recipients
    smtp_conn = None
    if not dry_run:
        try:
            smtp_conn = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            smtp_conn.ehlo()
            smtp_conn.starttls()
            smtp_conn.login(smtp_user, smtp_pass)
            logger.info("SMTP connected: %s:%d", smtp_host, smtp_port)
        except Exception as exc:
            logger.error("SMTP connection failed: %s", exc)
            return {"sent": 0, "failed": len(subscribers), "skipped": 0}

    try:
        for sub in subscribers:
            email = sub.get("email", "").strip()
            if not email:
                skipped += 1
                continue

            try:
                html_body = render_html(newsletter, sub)

                if dry_run:
                    logger.info(
                        "[DRY RUN] Would send to %s (%s)", sub.get("name"), email
                    )
                    # Print first 300 chars of rendered HTML to confirm it works
                    logger.debug("Preview:\n%s…", html_body[:300])
                    sent += 1
                    continue

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{from_email}>"
                msg["To"] = email
                msg.attach(MIMEText(html_body, "html"))

                smtp_conn.sendmail(from_email, [email], msg.as_string())
                logger.info("Sent to %s (%s)", sub.get("name"), email)
                sent += 1

            except Exception as exc:
                logger.error("Failed to send to %s: %s", email, exc)
                failed += 1

    finally:
        if smtp_conn:
            try:
                smtp_conn.quit()
            except Exception:
                pass

    logger.info(
        "Send complete for %s: sent=%d failed=%d skipped=%d",
        region_display,
        sent,
        failed,
        skipped,
    )
    return {"sent": sent, "failed": failed, "skipped": skipped}
