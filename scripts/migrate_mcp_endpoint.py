#!/usr/bin/env python3
"""
Rename 'sse_endpoint' to 'mcp_url' inside cfg_dict for MCP servers.

Usage:
    # Dry run (default query)
    python migrate_mcp_url.py

    # Dry run with custom query
    python migrate_mcp_url.py --query '{"type": "mcp_server"}'

    # Specify collection
    python migrate_mcp_url.py --collection resources

    # Apply changes
    python migrate_mcp_url.py --apply
"""

import os
import json
import argparse
from datetime import datetime
import pymongo


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MONGODB_IP = os.environ.get("MONGODB_IP", "localhost")
MONGODB_PORT = os.environ.get("MONGODB_PORT", "27017")
DB_NAME = "UnifAI"

DEFAULT_COLLECTION = "resources"
DEFAULT_QUERY = {"category": "providers", "type": "mcp_server"}


# ─────────────────────────────────────────────────────────────────────────────
# Migration
# ─────────────────────────────────────────────────────────────────────────────

def migrate(db, collection_name: str, query: dict, dry_run: bool = True) -> dict:
    """
    Find and update documents matching the query.

    Renames:
        cfg_dict.sse_endpoint → cfg_dict.mcp_url
    """
    collection = db[collection_name]

    docs = list(collection.find(query))

    stats = {"found": len(docs), "updated": 0, "errors": []}

    print(f"\n{'='*60}")
    print(f"COLLECTION: {collection_name}")
    print(f"QUERY: {json.dumps(query)}")
    print(f"{'='*60}")
    print(f"Found {len(docs)} document(s)")

    for doc in docs:
        rid = doc.get("rid", doc.get("_id"))
        name = doc.get("name", "unnamed")
        user_id = doc.get("user_id", "unknown")
        cfg = doc.get("cfg_dict", {})

        print(f"\n  [{rid}] {name} (user: {user_id})")
        print(f"    Current cfg_dict: {cfg}")

        try:
            if "sse_endpoint" not in cfg:
                print("    ✗ No sse_endpoint field found — skipping")
                continue

            old_value = cfg["sse_endpoint"]

            print(f"    Will rename:")
            print(f"      sse_endpoint → mcp_url")
            print(f"      Value: {old_value}")

            if not dry_run:
                result = collection.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "cfg_dict.mcp_url": old_value,
                            "updated": datetime.utcnow(),
                        },
                        "$unset": {
                            "cfg_dict.sse_endpoint": ""
                        }
                    }
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
            stats["errors"].append(f"{rid}: {str(e)}")
            print(f"    ✗ Error: {e}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rename sse_endpoint to mcp_url in cfg_dict"
    )
    parser.add_argument(
        "--collection", "-c",
        default=DEFAULT_COLLECTION,
        help=f"Collection name (default: {DEFAULT_COLLECTION})"
    )
    parser.add_argument(
        "--query", "-q",
        default=None,
        help=f"MongoDB query as JSON string (default: {json.dumps(DEFAULT_QUERY)})"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)"
    )

    args = parser.parse_args()

    # Parse query
    if args.query:
        try:
            query = json.loads(args.query)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON query: {e}")
            return
    else:
        query = DEFAULT_QUERY

    dry_run = not args.apply

    mongo_uri = f"mongodb://{MONGODB_IP}:{MONGODB_PORT}/"
    print(f"Connecting to MongoDB: {mongo_uri}")
    print(f"Database: {DB_NAME}")

    client = pymongo.MongoClient(mongo_uri)
    db = client[DB_NAME]

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No changes will be made")
        print("Use --apply to actually apply changes")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("APPLYING CHANGES")
        print("="*60)

    stats = migrate(db, args.collection, query, dry_run)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Collection: {args.collection}")
    print(f"  Found: {stats['found']}")
    print(f"  {'Would update' if dry_run else 'Updated'}: {stats['updated']}")
    if stats["errors"]:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"    - {err}")

    if dry_run:
        print("\nThis was a DRY RUN. Use --apply to make changes.")
    else:
        print("\nMigration complete!")

    client.close()


if __name__ == "__main__":
    main()
