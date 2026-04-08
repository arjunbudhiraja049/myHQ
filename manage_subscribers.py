"""
CLI tool to manage newsletter subscribers.

Usage:
  python manage_subscribers.py add
  python manage_subscribers.py import-csv data/sample_subscribers.csv
  python manage_subscribers.py list [--region delhi_ncr]
  python manage_subscribers.py remove <email>
  python manage_subscribers.py stats
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from newsletter.config import REGIONS
from newsletter.subscriber_manager import SubscriberManager


def cmd_add(sm: SubscriberManager):
    print("\n--- Add New Subscriber ---")
    name = input("Full name: ").strip()
    email = input("Email address: ").strip()

    print("\nAvailable regions:")
    for k, v in REGIONS.items():
        print(f"  {k:25s} → {v['display']}")
    region = input("Region key: ").strip()

    if region not in REGIONS:
        print(f"❌ Invalid region. Choose from: {', '.join(REGIONS.keys())}")
        sys.exit(1)

    print(f"\nAreas for {REGIONS[region]['display']}:")
    for a in REGIONS[region]["areas"]:
        print(f"  • {a}")
    area = input("Their focus area (press Enter to skip): ").strip()

    company = input("Company (optional): ").strip()
    role = input("Role/Designation (optional): ").strip()

    ok = sm.add_subscriber(name, email, region, area, company, role)
    if ok:
        print(f"\n✅ Added {name} ({email}) to {REGIONS[region]['display']}")
    else:
        print(f"\n⚠️  {email} already exists in the database")


def cmd_import_csv(sm: SubscriberManager, csv_path: str):
    if not Path(csv_path).exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)
    added, skipped = sm.import_csv(csv_path)
    print(f"✅ Imported: {added} added, {skipped} skipped (duplicates)")


def cmd_list(sm: SubscriberManager, region: str | None):
    if region:
        subs = sm.get_active_subscribers(region)
        print(f"\n--- Active subscribers for {REGIONS[region]['display']} ({len(subs)}) ---")
    else:
        subs = sm.get_all_subscribers()
        print(f"\n--- All subscribers ({len(subs)}) ---")

    if not subs:
        print("  (none)")
        return

    for s in subs:
        status = "✓" if s["is_active"] else "✗"
        area_str = f" [{s['area']}]" if s["area"] else ""
        print(
            f"  {status} {s['name']:<25s} {s['email']:<35s} "
            f"{s['region']:<20s}{area_str}"
        )


def cmd_remove(sm: SubscriberManager, email: str):
    ok = sm.deactivate_subscriber(email)
    if ok:
        print(f"✅ Deactivated {email}")
    else:
        print(f"⚠️  Email not found: {email}")


def cmd_stats(sm: SubscriberManager):
    print("\n--- Subscriber Statistics ---")
    total = sm.count()
    print(f"  Total active subscribers: {total}")
    for region_key, region in REGIONS.items():
        n = sm.count(region_key)
        print(f"  {region['display']:<25s}: {n}")


def main():
    parser = argparse.ArgumentParser(description="myHQ Subscriber Manager")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("add", help="Interactively add a subscriber")

    p_import = sub.add_parser("import-csv", help="Bulk import from CSV")
    p_import.add_argument("csv_path", help="Path to CSV file")

    p_list = sub.add_parser("list", help="List subscribers")
    p_list.add_argument("--region", choices=list(REGIONS.keys()), help="Filter by region")

    p_remove = sub.add_parser("remove", help="Deactivate a subscriber by email")
    p_remove.add_argument("email")

    sub.add_parser("stats", help="Show subscriber counts")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    sm = SubscriberManager()

    if args.command == "add":
        cmd_add(sm)
    elif args.command == "import-csv":
        cmd_import_csv(sm, args.csv_path)
    elif args.command == "list":
        cmd_list(sm, getattr(args, "region", None))
    elif args.command == "remove":
        cmd_remove(sm, args.email)
    elif args.command == "stats":
        cmd_stats(sm)


if __name__ == "__main__":
    main()
