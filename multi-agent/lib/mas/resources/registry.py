from datetime import datetime, timezone
from mas.resources.models import Resource, ResourceQuery
from mas.resources.repository.base import ResourceRepository
from mas.blueprints.repository.repository import BlueprintRepository
from mas.resources.errors import ResourceInUseError
from typing import List, Tuple, Dict, Any
from mas.core.dto import GroupedCount
from mas.core.ref import RefRemapper
from mas.core.ref.raw_blueprint_spec import (
    dedupe_blueprint_catalogue,
    extract_ref_ids_from_raw_spec,
    remove_resource_ref_from_catalogue,
    remove_resource_ref_from_nested_dict,
)
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

    def check_usage(self, rid: str) -> Tuple[List[str], List[str]]:
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
        if replacement_rid == rid:
            raise ValueError("Replacement cannot be the same as the resource")

        original = self._repo.get(rid)
        replacement = self._repo.get(replacement_rid)

        if original.category != replacement.category:
            raise ValueError(
                f"Replacement must be the same category "
                f"(got {replacement.category}, expected {original.category})"
            )

        mapping = {rid: replacement_rid}

        for dep_rid in self._repo.list_nested_usage(rid):
            doc = self._repo.get(dep_rid)
            doc.cfg_dict = RefRemapper.remap(doc.cfg_dict, mapping)
            doc.nested_refs = list({replacement_rid if r == rid else r for r in doc.nested_refs})
            self._bump_and_save(doc)

        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._update_blueprint_refs(bp_id, remap=mapping)

        self._repo.delete(rid)

    def detach_and_delete(self, rid: str) -> None:
        """Remove all references to rid from dependents, then delete rid."""
        self._strip_ref_from_dependents(rid)
        self._repo.delete(rid)

    def cascade_delete(self, rid: str) -> None:
        """Delete the resource and all blueprints that reference it."""
        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._bp_repo.delete(bp_id)

        self._strip_ref_from_dependents(rid)
        self._repo.delete(rid)

    def _bump_and_save(self, doc: Resource) -> None:
        """Increment version, stamp updated-at, and persist."""
        doc.version += 1
        doc.updated = datetime.now(timezone.utc)
        self._repo.update(doc)

    def _strip_ref_from_dependents(self, rid: str) -> None:
        """Remove all references to *rid* from nested resources and blueprints."""
        for dep_rid in self._repo.list_nested_usage(rid):
            doc = self._repo.get(dep_rid)
            doc.cfg_dict = remove_resource_ref_from_nested_dict(doc.cfg_dict, rid)
            doc.nested_refs = [r for r in doc.nested_refs if r != rid]
            self._bump_and_save(doc)

        for bp_id in self._bp_repo.list_direct_usage(rid):
            self._update_blueprint_refs(bp_id, remove_rid=rid)

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
            spec = dedupe_blueprint_catalogue(spec)

        if remove_rid:
            spec = remove_resource_ref_from_catalogue(spec, remove_rid)
            spec = remove_resource_ref_from_nested_dict(spec, remove_rid)

        rid_refs = list(extract_ref_ids_from_raw_spec(spec))
        self._bp_repo.update_raw(blueprint_id=bp_id, spec_dict=spec, rid_refs=rid_refs)

    def get_blueprint_summary(self, bp_id: str) -> dict:
        """Return {id, name} for a blueprint."""
        bp_doc = self._bp_repo.load(bp_id)
        return {"id": bp_id, "name": bp_doc.spec_dict.get("name", bp_id)}

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
