#!/usr/bin/env python3
"""
Rename 'sse_endpoint' → 'mcp_url' inside provider configs in the templates collection.

Walks each template document's draft.providers list and renames the key
wherever it appears, regardless of nesting depth.

Usage:
    # Dry run
    python migrate_templates_mcp_endpoint.py

    # Apply changes
    python migrate_templates_mcp_endpoint.py --apply
"""

import os
import copy
import argparse
from datetime import datetime
import pymongo


MONGODB_IP = os.environ.get("MONGODB_IP", "localhost")
MONGODB_PORT = os.environ.get("MONGODB_PORT", "27017")
DB_NAME = "UnifAI"
COLLECTION = "templates"


def rename_sse_in_dict(d: dict) -> bool:
    """
    Recursively walk a dict and rename every 'sse_endpoint' key to 'mcp_url'.
    Returns True if any rename was performed.
    """
    changed = False
    keys = list(d.keys())
    for key in keys:
        if key == "sse_endpoint" and "mcp_url" not in d:
            d["mcp_url"] = d.pop("sse_endpoint")
            changed = True
        elif isinstance(d[key], dict):
            if rename_sse_in_dict(d[key]):
                changed = True
        elif isinstance(d[key], list):
            for item in d[key]:
                if isinstance(item, dict) and rename_sse_in_dict(item):
                    changed = True
    return changed


def migrate_templates(db, dry_run: bool = True) -> dict:
    collection = db[COLLECTION]
    docs = list(collection.find({}))

    stats = {"scanned": len(docs), "updated": 0, "errors": []}

    print(f"\n{'='*60}")
    print(f"COLLECTION: {COLLECTION}")
    print(f"{'='*60}")
    print(f"Scanning {len(docs)} template(s)")

    for doc in docs:
        template_id = doc.get("template_id", str(doc.get("_id")))
        name = doc.get("draft", {}).get("name", "unnamed")
        providers = doc.get("draft", {}).get("providers", [])
        if not providers:
            continue

        patched_providers = copy.deepcopy(providers)
        changed = False
        for i, provider in enumerate(patched_providers):
            cfg = provider.get("config")
            if isinstance(cfg, dict) and rename_sse_in_dict(cfg):
                changed = True
                old_val = providers[i].get("config", {}).get("sse_endpoint", "?")
                print(f"\n  [{template_id}] {name}")
                print(f"    provider[{i}] (type={provider.get('type', '?')}): "
                      f"sse_endpoint → mcp_url  ({old_val})")

        if not changed:
            continue

        try:
            if not dry_run:
                result = collection.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "draft.providers": patched_providers,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
                if result.modified_count > 0:
                    stats["updated"] += 1
                    print("    ✓ Updated")
                else:
                    print("    ✗ No changes made")
            else:
                stats["updated"] += 1
                print("    [DRY RUN] Would update")
        except Exception as e:
            stats["errors"].append(f"{template_id}: {e}")
            print(f"    ✗ Error: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Rename sse_endpoint → mcp_url in templates collection"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply changes (default is dry-run)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    mongo_uri = f"mongodb://{MONGODB_IP}:{MONGODB_PORT}/"
    print(f"Connecting to MongoDB: {mongo_uri}")
    print(f"Database: {DB_NAME}")

    client = pymongo.MongoClient(mongo_uri)
    db = client[DB_NAME]

    mode = "DRY RUN MODE — No changes will be made" if dry_run else "APPLYING CHANGES"
    print(f"\n{'='*60}")
    print(mode)
    if dry_run:
        print("Use --apply to actually apply changes")
    print(f"{'='*60}")

    stats = migrate_templates(db, dry_run)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    action = "Would update" if dry_run else "Updated"
    print(f"  Scanned:  {stats['scanned']}")
    print(f"  {action}: {stats['updated']}")
    if stats["errors"]:
        print(f"  Errors:   {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"    - {err}")

    if dry_run:
        print("\nThis was a DRY RUN. Use --apply to make changes.")
    else:
        print("\nMigration complete!")

    client.close()


if __name__ == "__main__":
    main()
