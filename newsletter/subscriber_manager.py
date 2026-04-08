"""
SQLite-backed subscriber management.

Schema:
  subscribers(id, name, email, region, area, company, role, is_active, created_at)

Usage:
  sm = SubscriberManager()
  sm.add_subscriber("Arjun", "arjun@example.com", "delhi_ncr", area="Gurgaon Cyber City")
  subs = sm.get_active_subscribers("delhi_ncr")
"""

import csv
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "subscribers.db"


class SubscriberManager:
    def __init__(self, db_path: Path = DB_PATH):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT    NOT NULL,
                    email      TEXT    UNIQUE NOT NULL,
                    region     TEXT    NOT NULL,
                    area       TEXT,
                    company    TEXT,
                    role       TEXT,
                    is_active  INTEGER DEFAULT 1,
                    created_at TEXT    DEFAULT (datetime('now'))
                )
                """
            )
            conn.commit()
        logger.debug("Database initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_subscriber(
        self,
        name: str,
        email: str,
        region: str,
        area: str = "",
        company: str = "",
        role: str = "",
    ) -> bool:
        """
        Add a new subscriber. Returns True on success, False if email already exists.

        region must be one of: bangalore | delhi_ncr | chennai_hyderabad | mumbai_pune
        area   is the micro-market they cover (e.g. "Gurgaon Cyber City")
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO subscribers (name, email, region, area, company, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, email.lower().strip(), region, area, company, role),
                )
                conn.commit()
            logger.info("Added subscriber %s (%s) for %s", name, email, region)
            return True
        except sqlite3.IntegrityError:
            logger.warning("Subscriber %s already exists", email)
            return False

    def deactivate_subscriber(self, email: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE subscribers SET is_active = 0 WHERE email = ?",
                (email.lower().strip(),),
            )
            conn.commit()
        return cur.rowcount > 0

    def import_csv(self, csv_path: str) -> tuple[int, int]:
        """
        Bulk-import subscribers from a CSV file.

        Expected columns: name, email, region, area, company, role
        Returns (added, skipped) counts.
        """
        added = skipped = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ok = self.add_subscriber(
                    name=row.get("name", "").strip(),
                    email=row.get("email", "").strip(),
                    region=row.get("region", "").strip(),
                    area=row.get("area", "").strip(),
                    company=row.get("company", "").strip(),
                    role=row.get("role", "").strip(),
                )
                if ok:
                    added += 1
                else:
                    skipped += 1
        logger.info("CSV import: %d added, %d skipped", added, skipped)
        return added, skipped

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_active_subscribers(self, region: str) -> list[dict]:
        """Return all active subscribers for the given region."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM subscribers WHERE region = ? AND is_active = 1",
                (region,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all_subscribers(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM subscribers").fetchall()
        return [dict(r) for r in rows]

    def count(self, region: str | None = None) -> int:
        with self._connect() as conn:
            if region:
                return conn.execute(
                    "SELECT COUNT(*) FROM subscribers WHERE region = ? AND is_active = 1",
                    (region,),
                ).fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM subscribers WHERE is_active = 1"
            ).fetchone()[0]
