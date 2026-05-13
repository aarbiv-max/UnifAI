#!/usr/bin/env python3
"""
Upsert template JSON seed files into the MongoDB templates collection.

Reads every *.json file under scripts/template-seeds/ and upserts each one
by template_id (insert if absent, replace if present).

Usage:
    # Dry run — show what would be upserted without writing
    python seed_templates.py

    # Apply changes
    python seed_templates.py --apply
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymongo

MONGODB_IP = os.environ.get("MONGODB_IP", "localhost")
MONGODB_PORT = os.environ.get("MONGODB_PORT", "27017")
DB_NAME = "UnifAI"
COLLECTION = "templates"

SEEDS_DIR = Path(__file__).parent / "template-seeds"


def load_seed_files() -> list:
    """Load all JSON files from the template-seeds directory."""
    if not SEEDS_DIR.exists():
        print(f"ERROR: Seeds directory not found: {SEEDS_DIR}", file=sys.stderr)
        sys.exit(1)

    seeds = []
    for path in sorted(SEEDS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"WARNING: Skipping {path.name} — invalid JSON: {exc}")
                continue

        if "template_id" not in data:
            print(f"WARNING: Skipping {path.name} — missing 'template_id' field")
            continue

        seeds.append((path.name, data))

    return seeds


def seed_templates(db: Any, dry_run: bool = True) -> dict:
    """Upsert template seed documents into MongoDB."""
    collection = db[COLLECTION]
    seeds = load_seed_files()

    stats = {"scanned": len(seeds), "inserted": 0, "updated": 0, "errors": []}

    print(f"\n{'=' * 60}")
    print(f"COLLECTION: {COLLECTION}")
    print(f"Seeds directory: {SEEDS_DIR}")
    print(f"{'=' * 60}")
    print(f"Found {len(seeds)} seed file(s)")

    for filename, doc in seeds:
        template_id = doc["template_id"]
        name = doc.get("draft", {}).get("name", "unnamed")

        existing = collection.find_one({"template_id": template_id})
        action = "Would update" if existing else "Would insert"
        stat_key = "updated" if existing else "inserted"

        print(f"\n  [{template_id}] {name}")
        print(f"    File: {filename}")
        print(f"    Action: {action}")

        if dry_run:
            stats[stat_key] += 1
            print("    [DRY RUN] No changes made")
            continue

        now = datetime.now(tz=timezone.utc).isoformat()
        doc["updated_at"] = now
        if not existing:
            doc.setdefault("created_at", now)

        try:
            collection.replace_one(
                {"template_id": template_id},
                doc,
                upsert=True,
            )
            stats[stat_key] += 1
            print("    ✓ Done")
        except Exception as exc:
            stats["errors"].append(f"{template_id}: {exc}")
            print(f"    ✗ Error: {exc}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upsert template seed JSON files into MongoDB"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    mongo_uri = f"mongodb://{MONGODB_IP}:{MONGODB_PORT}/"
    print(f"Connecting to MongoDB: {mongo_uri}")
    print(f"Database: {DB_NAME}")

    mode = "DRY RUN MODE — No changes will be made" if dry_run else "APPLYING CHANGES"
    print(f"\n{'=' * 60}")
    print(mode)
    if dry_run:
        print("Use --apply to actually apply changes")
    print(f"{'=' * 60}")

    client = pymongo.MongoClient(mongo_uri)
    db = client[DB_NAME]

    stats = seed_templates(db, dry_run)

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    verb = "Would insert" if dry_run else "Inserted"
    print(f"  Scanned:  {stats['scanned']}")
    print(f"  {verb}:  {stats['inserted']}")
    verb = "Would update" if dry_run else "Updated"
    print(f"  {verb}:   {stats['updated']}")
    if stats["errors"]:
        print(f"  Errors:   {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"    - {err}")

    if dry_run:
        print("\nThis was a DRY RUN. Use --apply to make changes.")
    else:
        print("\nSeeding complete!")

    client.close()


if __name__ == "__main__":
    main()
