from typing import Any, Dict, Iterable, Mapping
from .category_builder import CategoryBuilder, BlueprintSpec
from core.enums import ResourceCategory
from elements.nodes.types import NodeSpec
from elements.common.exceptions import PluginConfigurationError
from core.ref.models import Ref
from core.contracts import SessionRegistry


class NodeBuilder(CategoryBuilder):
    """
    Injects resolved dependencies (llm / retriever / tools) into node
    constructors.  The only thing you need to maintain is `_inject_cat`.
    """
    category = ResourceCategory.NODE
    depends_on = {
        ResourceCategory.TOOL,
        ResourceCategory.LLM,
        ResourceCategory.RETRIEVER,
        ResourceCategory.PROVIDER
    }

    # attr name → category  (cardinality inferred at runtime)
    _inject_cat: Mapping[str, ResourceCategory] = {
        "llm": ResourceCategory.LLM,
        "retriever": ResourceCategory.RETRIEVER,
        "tools": ResourceCategory.TOOL,
        "provider": ResourceCategory.PROVIDER
    }

    def _iter_specs(self, bp: BlueprintSpec) -> Iterable[NodeSpec]:
        return bp.nodes

    def _extra_kwargs(self, cfg: NodeSpec, reg: SessionRegistry) -> Dict[str, Any]:
        """Resolve llm / retriever / tools and return constructor kwargs."""
        kwargs: Dict[str, Any] = {attr: None for attr in self._inject_cat}

        for attr, category in self._inject_cat.items():
            value = getattr(cfg, attr, None)

            if value is None:
                continue

            if isinstance(value, list):  # ← plural case
                if not all(isinstance(r, Ref) for r in value):
                    self._raise_type(cfg, attr, "list[Ref]", value)

                kwargs[attr] = [
                    self._resolve_dependency(attr, category, r.ref, cfg, reg)
                    for r in value
                ]

            else:  # ← singular case
                if not isinstance(value, Ref):
                    self._raise_type(cfg, attr, "Ref", value)

                kwargs[attr] = self._resolve_dependency(
                    attr, category, value.ref, cfg, reg
                )

        return kwargs

    @staticmethod
    def _raise_type(cfg: NodeSpec, attr: str, expected: str, got_obj: Any) -> None:
        raise PluginConfigurationError(
            f"Node {cfg.name!r}: expected {expected} for {attr!r}, got {type(got_obj).__name__}",
            cfg.dict(),
        )

    def _resolve_dependency(
            self,
            attr_name: str,
            category: ResourceCategory,
            rid: str,
            cfg: NodeSpec,
            reg: SessionRegistry,
    ) -> Any:
        try:
            return reg.get_instance(category=category, rid=rid)
        except KeyError as exc:
            raise PluginConfigurationError(
                f"Node config: {cfg!r}: unknown {attr_name!r} rid={rid!r} "
                f"in category={category.value}"
            ) from exc
