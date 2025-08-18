from datetime import datetime
from resources.models import ResourceDoc, ResourceQuery
from resources.repository.base import ResourceRepository
from blueprints.repository.repository import BlueprintRepository
from resources.errors import ResourceInUseError
from typing import List, Tuple


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
    def create(self, doc: ResourceDoc) -> ResourceDoc:
        # uniqueness guard
        if self._repo.find_by_name(doc.user_id, doc.category, doc.type, doc.name):
            raise ValueError(f"{doc.category}:{doc.type}:{doc.name} exists for user")
        self._repo.save(doc)
        return doc

    def update(self, doc: ResourceDoc) -> ResourceDoc:
        if self._repo.find_by_name(doc.user_id, doc.category, doc.type, doc.name):
            if self._repo.get(doc.rid).name != doc.name:
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

    # ---------- read ----------
    def get(self, rid: str) -> ResourceDoc:
        return self._repo.get(rid)

    def find_resources(self, query: ResourceQuery) -> Tuple[List[ResourceDoc], int]:
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
