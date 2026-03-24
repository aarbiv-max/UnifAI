from datetime import datetime, timezone
from mas.resources.models import Resource, ResourceQuery
from mas.resources.repository.base import ResourceRepository
from mas.blueprints.repository.repository import BlueprintRepository
from mas.resources.errors import ResourceInUseError
from typing import List, Tuple, Dict, Any
from mas.core.dto import GroupedCount
from mas.core.ref import RefRemapper
from mas.core.enums import ResourceCategory


_CATALOGUE_KEYS = tuple(c.value for c in ResourceCategory)


class ResourcesRegistry:
    """Low-level CRUD + business rules (no Pydantic parsing)."""

    def __init__(
            self,
            repo: ResourceRepository,
            bp_repo: BlueprintRepository,  # for delete guard
    ):
        self._repo = repo
        self._bp_repo = bp_repo

    # ---------- write ----------
    def create(self, doc: Resource) -> Resource:
        # uniqueness guard
        if self._repo.find_by_name(doc.user_id, doc.category, doc.type, doc.name):
            raise ValueError(f"{doc.category}:{doc.type}:{doc.name} exists for user")
        self._repo.save(doc)
        return doc

    def update(self, doc: Resource) -> Resource:
        # Guard against name conflicts with other resources
        existing_with_name = self._repo.find_by_name(doc.user_id, doc.category, doc.type, doc.name)
        if existing_with_name and existing_with_name.rid != doc.rid:
            raise ValueError(f"{doc.category}:{doc.type}:{doc.name} exists for user")
        
        doc.version += 1
        doc.updated = datetime.now(timezone.utc)
        self._repo.update(doc)
        return doc

    def check_usage(self, rid: str) -> tuple[list, list]:
        """Return (blueprint_ids, resource_ids) that reference *rid*."""
        direct_bps = self._bp_repo.list_direct_usage(rid)
        nested_res = self._repo.list_nested_usage(rid)
        return direct_bps, nested_res

    def delete(self, rid: str) -> None:
        direct_bps, nested_res = self.check_usage(rid)

        if direct_bps or nested_res:
            raise ResourceInUseError(by_blueprints=direct_bps,
                                     by_resources=nested_res)
        self._repo.delete(rid)

    # ---------- force-delete variants ----------
    def replace_and_delete(self, rid: str, replacement_rid: str) -> None:
        """Replace all references to rid with replacement_rid, then delete rid."""
        if not self._repo.exists(replacement_rid):
            raise KeyError(f"Replacement resource not found: {replacement_rid}")

        mapping = {rid: replacement_rid}

        for dep_rid in self._repo.list_nested_usage(rid):
            doc = self._repo.get(dep_rid)
            doc.cfg_dict = RefRemapper.remap(doc.cfg_dict, mapping)
            doc.nested_refs = list({replacement_rid if r == rid else r for r in doc.nested_refs})
            doc.version += 1
            doc.updated = datetime.now(timezone.utc)
            self._repo.update(doc)

        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._update_blueprint_refs(bp_id, remap=mapping)

        self._repo.delete(rid)

    def detach_and_delete(self, rid: str) -> None:
        """Remove all references to rid from dependents, then delete rid."""
        for dep_rid in self._repo.list_nested_usage(rid):
            doc = self._repo.get(dep_rid)
            doc.cfg_dict = _remove_ref_from_dict(doc.cfg_dict, rid)
            doc.nested_refs = [r for r in doc.nested_refs if r != rid]
            doc.version += 1
            doc.updated = datetime.now(timezone.utc)
            self._repo.update(doc)

        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._update_blueprint_refs(bp_id, remove_rid=rid)

        self._repo.delete(rid)

    def cascade_delete(self, rid: str) -> None:
        """Delete the resource and all blueprints that reference it."""
        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._bp_repo.delete(bp_id)

        for dep_rid in self._repo.list_nested_usage(rid):
            doc = self._repo.get(dep_rid)
            doc.cfg_dict = _remove_ref_from_dict(doc.cfg_dict, rid)
            doc.nested_refs = [r for r in doc.nested_refs if r != rid]
            doc.version += 1
            doc.updated = datetime.now(timezone.utc)
            self._repo.update(doc)

        self._repo.delete(rid)

    def _update_blueprint_refs(
        self,
        bp_id: str,
        *,
        remap: Dict[str, str] | None = None,
        remove_rid: str | None = None,
    ) -> None:
        """
        Update a blueprint's spec_dict and rid_refs after a ref change.
        Operates on the raw spec dict to avoid Pydantic validation failures
        caused by legacy fields in stored blueprints.
        """
        bp_doc = self._bp_repo.load(bp_id)
        spec = bp_doc.spec_dict

        if remap:
            spec = RefRemapper.remap(spec, remap)
            spec = _dedup_catalogue(spec)

        if remove_rid:
            spec = _remove_ref_from_catalogue(spec, remove_rid)

        rid_refs = list(_extract_ref_ids(spec))
        self._bp_repo.update_raw(blueprint_id=bp_id, spec_dict=spec, rid_refs=rid_refs)

    # ---------- read ----------
    def get(self, rid: str) -> Resource:
        return self._repo.get(rid)

    def find_resources(self, query: ResourceQuery) -> Tuple[List[Resource], int]:
        """Find resources with pagination info."""
        resources = self._repo.find_resources(query)
        total_count = self._repo.count_resources(query)
        return resources, total_count

    def raw_config(self, rid: str) -> dict:
        return self.get(rid).cfg_dict

    def meta(self, rid: str) -> tuple[str, str]:
        return self._repo.meta(rid)

    def exists(self, rid: str) -> bool:
        return self._repo.exists(rid)

    # ---------- statistics ----------
    def count(self, user_id: str, filter: Dict[str, Any] = None) -> int:
        """Count resources matching filter criteria for a user."""
        return self._repo.count(user_id, filter or {})

    def group_count(
        self, 
        user_id: str, 
        group_by: List[str],
        filter: Dict[str, Any] = None
    ) -> List[GroupedCount]:
        """
        Group resources by specified fields and return counts.
        Performs efficient server-side grouping via the repository.
        
        Args:
            user_id: The user ID to filter by
            group_by: List of field names to group by (e.g., ["category", "type"])
            filter: Optional additional filter criteria
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
        """
        return self._repo.group_count(user_id, group_by, filter)


# ---------- pure helpers for ref extraction & manipulation on raw dicts ----------

_REF_PREFIX = "$ref:"


def _extract_ref_ids(node: Any) -> set[str]:
    """Extract all resource IDs from $ref:xxx strings in a raw spec dict."""
    bucket: set[str] = set()
    _scan_refs(node, bucket)
    return bucket


def _scan_refs(node: Any, bucket: set[str]) -> None:
    if isinstance(node, str):
        if node.startswith(_REF_PREFIX):
            bucket.add(node[len(_REF_PREFIX):])
    elif isinstance(node, dict):
        for v in node.values():
            _scan_refs(v, bucket)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _scan_refs(v, bucket)

def _remove_ref_from_dict(d: dict, rid: str) -> dict:
    """Remove $ref:rid from a raw config dict — nullify scalars, filter from lists."""
    ref_str = f"$ref:{rid}"

    def walk(node):
        if isinstance(node, str):
            return None if node == ref_str else node
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node if not (isinstance(v, str) and v == ref_str)]
        return node

    return walk(d)


def _remove_ref_from_catalogue(spec_dict: dict, rid: str) -> dict:
    """Remove catalogue entries whose rid matches from a blueprint spec_dict."""
    ref_str = f"$ref:{rid}"
    result = dict(spec_dict)
    for cat_key in _CATALOGUE_KEYS:
        entries = result.get(cat_key)
        if isinstance(entries, list):
            result[cat_key] = [
                e for e in entries
                if not (isinstance(e, dict) and e.get("rid") == ref_str)
            ]
    return result


def _dedup_catalogue(spec_dict: dict) -> dict:
    """Remove duplicate catalogue entries (same rid) from a blueprint spec_dict."""
    result = dict(spec_dict)
    for cat_key in _CATALOGUE_KEYS:
        entries = result.get(cat_key)
        if isinstance(entries, list):
            seen: set = set()
            deduped = []
            for entry in entries:
                rid = entry.get("rid") if isinstance(entry, dict) else None
                if rid and rid in seen:
                    continue
                if rid:
                    seen.add(rid)
                deduped.append(entry)
            result[cat_key] = deduped
    return result
