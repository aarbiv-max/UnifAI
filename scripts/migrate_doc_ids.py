#!/usr/bin/env python3
"""
Migration Script: Convert doc_ids field from string array to object array.

Old:
    doc_ids: ["id1", "id2"]

New:
    doc_ids: [{"id": "id1", "name": "Document 1"}, ...]
"""

import argparse
import sys
import json
import os
from datetime import datetime
from typing import List, Dict
import pymongo


# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

MONGODB_IP = os.environ.get("MONGODB_IP", "localhost")
MONGODB_PORT = os.environ.get("MONGODB_PORT", "27017")

RETRIEVERS_DB = "UnifAI"
SOURCES_DB = "data_sources"

RETRIEVERS_COLLECTION = "resources"
SOURCES_COLLECTION = "sources"

RETRIEVER_TYPE = "docs_dataflow"
CATEGORY = "retrievers"


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def needs_migration(cfg: dict) -> bool:
    """
    Determine whether the configuration's "doc_ids" list contains any string entries that need migration.
    
    Parameters:
        cfg (dict): Retriever configuration which may include a "doc_ids" key mapping to a list of document identifiers or objects.
    
    Returns:
        `true` if any element in `cfg["doc_ids"]` is a string, `false` otherwise.
    
    Notes:
        Treats missing or falsy `doc_ids` as an empty list.
    """
    for d in cfg.get("doc_ids", []) or []:
        if isinstance(d, str):
            return True
    return False


def convert_doc_ids(old: list, docs_map: dict) -> list:
    """
    Convert a list of document identifiers (which may be strings or dicts) into a normalized list of objects each containing `id` and `name`.
    
    Parameters:
        old (list): List of document entries where each entry is either a string document id or a dict containing at least an `"id"` key.
        docs_map (dict): Mapping from document id to display name used to populate the `name` field when missing.
    
    Returns:
        list: A list of dicts where each dict has keys `"id"` and `"name"`. For string entries, `id` is the string and `name` is taken from `docs_map` or falls back to the id. For dict entries, an existing `"name"` is preserved; if missing, it is populated from `docs_map` or set to the id.
    """
    out = []
    for d in old or []:
        if isinstance(d, str):
            out.append({"id": d, "name": docs_map.get(d, d)})
        elif isinstance(d, dict) and "id" in d:
            if "name" not in d:
                d["name"] = docs_map.get(d["id"], d["id"])
            out.append(d)
    return out


def fetch_sources(db, ids: List[str]) -> Dict[str, str]:
    """
    Build a mapping from source IDs to their display names by querying the data_sources.sources collection.
    
    Parameters:
        ids (List[str]): Iterable of source IDs to resolve.
    
    Returns:
        Dict[str, str]: A mapping where each key is a source_id and each value is the corresponding source_name from the database; if a name is missing, the source_id is used as the value.
    """
    if not ids:
        return {}

    print(f"Resolving {len(ids)} documents from Mongo data_sources.sources…")
    col = db[SOURCES_COLLECTION]

    result = {}
    for src in col.find({"source_id": {"$in": ids}}, {"source_id": 1, "source_name": 1}):
        result[src["source_id"]] = src.get("source_name", src["source_id"])

    return result


# ────────────────────────────────────────────────────────────────
# Migration
# ────────────────────────────────────────────────────────────────

def migrate(dry_run: bool):
    """
    Migrate retriever configurations' doc_ids from string arrays to object arrays in the MongoDB retrievers collection.
    
    Resolves document names from the data_sources.sources collection, transforms each retriever's cfg_dict.doc_ids into the new object form, and updates the retriever documents when not running in dry-run mode. Prints progress to stdout and returns a summary of processed records.
    
    Parameters:
        dry_run (bool): If True, simulate the migration without writing changes to the database.
    
    Returns:
        dict: A stats dictionary with keys "checked", "migrated", and "skipped" indicating the number of retrievers inspected, migrated (or would be migrated in dry run), and skipped.
    """
    client = pymongo.MongoClient(f"mongodb://{MONGODB_IP}:{MONGODB_PORT}/")

    retrievers_db = client[RETRIEVERS_DB]
    sources_db = client[SOURCES_DB]

    retrievers = retrievers_db[RETRIEVERS_COLLECTION]
    sources = sources_db[SOURCES_COLLECTION]

    query = {"category": CATEGORY, "type": RETRIEVER_TYPE}
    resources = list(retrievers.find(query))

    print(f"Found {len(resources)} retrievers")

    needed_ids = set()
    for r in resources:
        if needs_migration(r.get("cfg_dict", {})):
            for d in r.get("cfg_dict", {}).get("doc_ids", []):
                if isinstance(d, str):
                    needed_ids.add(d)

    docs_map = {}
    if needed_ids:
        print(f"Need to resolve {len(needed_ids)} doc_ids")
        for src in sources.find(
            {"source_id": {"$in": list(needed_ids)}},
            {"source_id": 1, "source_name": 1}
        ):
            docs_map[src["source_id"]] = src.get("source_name", src["source_id"])

    stats = {"checked": 0, "migrated": 0, "skipped": 0}

    for r in resources:
        stats["checked"] += 1
        rid = r.get("rid", r["_id"])
        name = r.get("name", "unnamed")
        cfg = r.get("cfg_dict", {})

        print(f"\n[{rid}] {name}")

        if not needs_migration(cfg):
            print("  Skipped")
            stats["skipped"] += 1
            continue

        old_ids = cfg.get("doc_ids", [])
        new_ids = convert_doc_ids(old_ids, docs_map)

        print(f"  Old: {old_ids}")
        print(f"  New: {new_ids}")

        if dry_run:
            print("  [DRY RUN] Would update")
            stats["migrated"] += 1
            continue

        retrievers.update_one(
            {"_id": r["_id"]},
            {"$set": {"cfg_dict.doc_ids": new_ids, "updated": datetime.utcnow()}}
        )

        print("  ✓ Migrated")
        stats["migrated"] += 1

    client.close()
    return stats


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    """
    CLI entry point that runs the doc_ids migration for retriever configurations.
    
    Parses the --apply flag from command-line arguments to determine whether to perform a real migration or a dry run (default). Executes the migration, prints a summary of statistics, and—when running as a dry run—prints a reminder to re-run with --apply to commit changes.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply

    if dry_run:
        print("\n*** DRY RUN MODE ***\n")

    stats = migrate(dry_run)

    print("\nSummary")
    print(stats)

    if dry_run:
        print("\nRun with --apply to commit changes.")


if __name__ == "__main__":
    main()