from typing import TypeVar, Any
from pydantic import BaseModel
from core.enums import ResourceCategory
from core.ref.models import Ref
from core.ref import RefWalker
from .models.blueprint import (
    Resource,
    ResourceSpec,
    BlueprintDraft,
    BlueprintSpec
)
from resources.registry import ResourcesRegistry
from catalog.element_registry import ElementRegistry

T = TypeVar("T", bound=BaseModel)


class BlueprintResolver:
    def __init__(self,
                 resource_registry: ResourcesRegistry,
                 element_registry: ElementRegistry):
        self.resource_registry = resource_registry
        self.element_registry = element_registry
        self._visited: set[str] = set()
        self._bucket: dict[str, list] = {}

    def resolve(self, draft: BlueprintDraft) -> BlueprintSpec:
        self._bucket: dict[str, list] = {}
        self._visited: set[str] = set()

        # --- walk every catalogue in the draft ---------------------------
        for cat in list(ResourceCategory):
            for res in getattr(draft, cat.value):
                raw_rid = res.rid.ref if isinstance(res.rid, Ref) else res.rid

                external_ref = isinstance(res.rid, Ref) and res.rid.is_external_ref()

                if not external_ref:
                    # inline resource → keep its config in the bucket
                    self._stash_inline(cat, res)
                else:  # ← LIVE REF
                    # external Ref → fetch from registry
                    self._walk_live(raw_rid, res.name)

        # --- build executable spec ---------------------------------------
        return BlueprintSpec(
            **{cat.value: self._bucket.get(cat.value, []) for cat in list(ResourceCategory)},
            plan=draft.plan,
            name=draft.name,
            description=draft.description,
        )

    # --------------------------------------------------------------------
    # helpers
    # --------------------------------------------------------------------
    def _stash_inline(self, cat: ResourceCategory, res: Resource):
        """Put an inline/frozen entry straight into the bucket."""
        concrete = res.config  # already a validated Pydantic model
        self._bucket.setdefault(cat.value, []).append(
            ResourceSpec[type(concrete)](
                rid=res.rid, name=res.name, type=res.type, config=concrete
            )
        )
        # still inspect it for nested rids
        self._scan_nested(concrete)

    def _walk_live(self, rid: str, name: str | None):
        """Fetch a live resource and recurse through its config."""
        if rid in self._visited:
            return
        self._visited.add(rid)

        cat, tp = self.resource_registry.meta(rid)
        raw = self.resource_registry.raw_config(rid)
        model_cls = self.element_registry.get_schema(ResourceCategory(cat), tp)
        obj = model_cls(**raw)

        if name is None:
            # fallback to registry name, or obj.name if available
            name = self.resource_registry.get(rid).name

        self._bucket.setdefault(cat, []).append(
            ResourceSpec[type(obj)](rid=rid, name=name, type=tp, config=obj)
        )
        self._scan_nested(obj)

    def _scan_nested(self, node: Any):
        """
        Recursively walk any BaseModel, dict, list/tuple or Ref.
        Whenever we hit an external Ref, call _walk_live.
        """
        for child_rid in RefWalker.external_rids(node):
            self._walk_live(child_rid, None)
