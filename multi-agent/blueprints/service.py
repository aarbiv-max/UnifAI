from typing import Any, Dict, List, Mapping
from .models.blueprint import BlueprintSpec, BlueprintDraft
from .repository.repository import BlueprintRepository
from .resolver import BlueprintResolver
from core.ref import RefWalker


class BlueprintService:
    def __init__(self, repo: BlueprintRepository, resolver: BlueprintResolver):
        self._repo = repo
        self._resolver = resolver

    # ────────── Write ──────────
    def save_draft(self, *, user_id: str, draft_dict: dict) -> str:
        draft_bp = BlueprintDraft(**draft_dict)
        rid_refs = list(RefWalker.external_rids(draft_bp))
        return self._repo.save(user_id=user_id, spec=draft_bp, rid_refs=rid_refs)

    # ────────── Single-blueprint reads (ID is globally unique) ──────────
    def load_draft(self, blueprint_id: str) -> BlueprintDraft:
        doc = self._repo.load(blueprint_id)
        return BlueprintDraft(**doc["spec_dict"])

    def update_draft(self, *, blueprint_id: str, draft_dict: dict) -> bool:  # NEW
        draft = BlueprintDraft(**draft_dict)
        rid_refs = list(RefWalker.external_rids(draft))
        return self._repo.update(
            blueprint_id=blueprint_id, spec=draft, rid_refs=rid_refs
        )

    def load_resolved(self, blueprint_id: str) -> BlueprintSpec:
        return self._resolver.resolve(self.load_draft(blueprint_id))

    def load_draft_from_dict(self, draft_dict: dict) -> BlueprintDraft:
        """Load a BlueprintDraft from a dictionary without saving to database."""
        return BlueprintDraft(**draft_dict)

    def resolve_draft_dict(self, draft_dict: dict) -> BlueprintSpec:
        """Resolve a draft dictionary directly to BlueprintSpec without saving to database."""
        draft_bp = BlueprintDraft(**draft_dict)
        return self._resolver.resolve(draft_bp)

    def to_dict(self, blueprint_id: str) -> Dict[str, Any]:
        """Draft → JSON-serialisable dict (no meta)."""
        return self.load_draft(blueprint_id).model_dump(mode="json")

    def exists(self, blueprint_id: str) -> bool:
        return self._repo.exists(blueprint_id)

    def delete(self, blueprint_id: str) -> bool:
        return self._repo.delete(blueprint_id)

    # ────────── Bulk listing / counting (optionally per user) ──────────
    def list_ids(self, *, user_id: str | None = None, **pg) -> List[str]:
        return self._repo.list_ids(user_id=user_id, **pg)

    def list_draft_dicts(
            self, *, user_id: str | None = None, **pg
    ) -> List[Dict[str, Any]]:
        """
        Return pure-dict drafts (as saved) in one DB round-trip.
        """
        docs = self._repo.list_docs(user_id=user_id, **pg)
        return [doc["spec_dict"] for doc in docs]

    def list_draft_docs(
            self, *, user_id: str | None = None, **pg
    ) -> List[Mapping[str, Any]]:
        """
        Return pure-dict drafts (as saved) in one DB round-trip.
        """
        docs = self._repo.list_docs(user_id=user_id, **pg)
        return [doc for doc in docs]

    def count(self, *, user_id: str | None = None) -> int:
        return self._repo.count(user_id=user_id)

    @staticmethod
    def get_draft_schema() -> Dict[str, Any]:
        """
        Return the JSON schema of the BlueprintDraft model.
        """
        return BlueprintDraft.model_json_schema()
