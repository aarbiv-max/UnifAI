from datetime import datetime
from resources.models import Resource, ResourceQuery
from resources.repository.base import ResourceRepository
from blueprints.repository.repository import BlueprintRepository
from resources.errors import ResourceInUseError
from typing import List, Tuple, Dict, Any
from core.dto import GroupedCount


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
        doc.updated = datetime.utcnow()
        self._repo.update(doc)
        return doc

    def delete(self, rid: str) -> None:
        direct_bps = self._bp_repo.list_direct_usage(rid)
        nested_res = self._repo.list_nested_usage(rid)

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
            doc.updated = datetime.utcnow()
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
            doc.updated = datetime.utcnow()
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
            doc.updated = datetime.utcnow()
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
        Follows the same parse→walk→save pattern as BlueprintService.update_draft.
        """
        bp_doc = self._bp_repo.load(bp_id)
        spec = bp_doc.spec_dict

        if remap:
            spec = RefRemapper.remap(spec, remap)
            spec = _dedup_catalogue(spec)

        if remove_rid:
            spec = _remove_ref_from_catalogue(spec, remove_rid)

        draft = BlueprintDraft(**spec)
        rid_refs = list(RefWalker.external_rids(draft))
        self._bp_repo.update(blueprint_id=bp_id, spec=draft, rid_refs=rid_refs)

    # ---------- doc-in-retriever helpers ----------
    def find_doc_usage(self, doc_ids: list[str]) -> list[Resource]:
        """Return all retrievers (any user) whose docs list references any of the given doc IDs."""
        return self._repo.find_by_doc_ref(doc_ids)

    def remove_docs_from_retrievers(self, doc_ids: list[str]) -> int:
        """
        Remove doc entries from every retriever's cfg_dict.docs list
        where the doc id matches any of the given doc_ids.
        Returns the number of retrievers that were modified.
        """
        doc_id_set = set(doc_ids)
        affected = self._repo.find_by_doc_ref(doc_ids)
        modified = 0
        for res in affected:
            docs_list = res.cfg_dict.get("docs") or []
            cleaned = [d for d in docs_list if d.get("id") not in doc_id_set]
            if len(cleaned) == len(docs_list):
                continue
            res.cfg_dict["docs"] = cleaned or None
            res.version += 1
            res.updated = datetime.utcnow()
            self._repo.update(res)
            modified += 1
        return modified

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
