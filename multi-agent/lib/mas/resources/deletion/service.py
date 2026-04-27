from __future__ import annotations

from typing import Optional

from mas.blueprints.ref_service import BlueprintRefService
from mas.core.enums import ResourceCategory
from mas.resources.deletion.context import DeletionContext
from mas.resources.deletion.mode import DeleteMode
from mas.resources.deletion.models import (
    BlueprintUsageDetail,
    ResourceUsageDetail,
    UsageCheckResult,
)
from mas.resources.deletion.strategies import DeleteStrategy
from mas.resources.errors import ResourceInUseError
from mas.resources.registry import ResourcesRegistry


class ResourceDeletionService:
    """
    Orchestrates force-deletion of in-use resources and enriched usage checks.

    Strategies are auto-discovered from DeleteStrategy subclasses
    via build_strategy_map().
    """

    def __init__(
        self,
        registry: ResourcesRegistry,
        bp_refs: BlueprintRefService,
    ):
        self._registry = registry
        self._bp_refs = bp_refs
        self._strategies = DeleteStrategy.build_strategy_map()

    def check_usage(self, rid: str) -> UsageCheckResult:
        """Check whether a resource is in use and how it can be force-deleted."""
        resource = self._registry.get(rid)
        bp_ids, res_ids = self._registry.check_usage(rid)

        if not bp_ids and not res_ids:
            return UsageCheckResult(in_use=False)

        strategy = self._strategy_for(ResourceCategory(resource.category))
        return UsageCheckResult(
            in_use=True,
            category=resource.category,
            allowed_mode=strategy.mode,
            blueprints=self._enrich_blueprints(bp_ids),
            resources=self._enrich_resources(res_ids),
        )

    def usage_payload_for_in_use(self, rid: str, err: ResourceInUseError) -> UsageCheckResult:
        """
        Build a UsageCheckResult for a 409 response, merging live usage data
        with IDs from ResourceInUseError when enrichment is incomplete.
        """
        try:
            base = self.check_usage(rid)
        except KeyError:
            base = None

        if base is None or not base.in_use:
            return self._usage_from_in_use_error(rid, err)

        bp_by_id = {b.id: b for b in base.blueprints}
        res_by_id = {r.id: r for r in base.resources}

        for bid in err.by_blueprints:
            if bid not in bp_by_id:
                try:
                    summary = self._bp_refs.get_summary(bid)
                    bp_by_id[bid] = BlueprintUsageDetail(**summary)
                except KeyError:
                    bp_by_id[bid] = BlueprintUsageDetail(id=bid, name=bid)

        for rsid in err.by_resources:
            if rsid not in res_by_id:
                try:
                    r = self._registry.get(rsid)
                    res_by_id[rsid] = ResourceUsageDetail(
                        id=rsid,
                        name=r.name,
                        category=r.category,
                        type=r.type,
                    )
                except KeyError:
                    res_by_id[rsid] = ResourceUsageDetail(id=rsid, name=rsid)

        return UsageCheckResult(
            in_use=True,
            category=base.category,
            allowed_mode=base.allowed_mode,
            blueprints=list(bp_by_id.values()),
            resources=list(res_by_id.values()),
        )

    def force_delete(
        self,
        rid: str,
        mode: str,
        replacement_rid: Optional[str] = None,
    ) -> None:
        """Validate mode against category policy, then execute strategy."""
        requested_mode = self._parse_mode(mode)
        resource = self._registry.get(rid)
        strategy = self._strategy_for(ResourceCategory(resource.category))

        if requested_mode != strategy.mode:
            raise ValueError(
                f"Mode '{mode}' is not permitted for {resource.category} "
                f"resources. Use '{strategy.mode.value}' instead."
            )

        bp_ids, res_ids = self._registry.check_usage(rid)
        ctx = DeletionContext(
            resource=resource,
            replacement_rid=replacement_rid,
            blueprint_ids=bp_ids,
            resource_ids=res_ids,
            registry=self._registry,
            bp_refs=self._bp_refs,
        )

        strategy.validate(ctx)
        strategy.execute(ctx)

    def _strategy_for(self, category: ResourceCategory) -> DeleteStrategy:
        if category not in self._strategies:
            raise ValueError(f"No delete strategy registered for category: {category.value}")
        return self._strategies[category]

    @staticmethod
    def _parse_mode(mode: str) -> DeleteMode:
        try:
            return DeleteMode(mode)
        except ValueError:
            raise ValueError(
                f"Unknown mode: {mode}. "
                f"Must be one of: {', '.join(m.value for m in DeleteMode)}"
            ) from None

    def _usage_from_in_use_error(self, rid: str, err: ResourceInUseError) -> UsageCheckResult:
        category: Optional[str] = None
        allowed_mode: Optional[DeleteMode] = None
        try:
            resource = self._registry.get(rid)
            category = resource.category
            allowed_mode = self._strategy_for(ResourceCategory(category)).mode
        except (KeyError, ValueError):
            pass

        return UsageCheckResult(
            in_use=True,
            category=category,
            allowed_mode=allowed_mode,
            blueprints=[
                BlueprintUsageDetail(id=bid, name=bid) for bid in err.by_blueprints
            ],
            resources=[
                ResourceUsageDetail(id=r, name=r, category=None, type=None)
                for r in err.by_resources
            ],
        )

    def _enrich_blueprints(self, bp_ids: list) -> list[BlueprintUsageDetail]:
        result: list[BlueprintUsageDetail] = []
        for bp_id in bp_ids:
            try:
                summary = self._bp_refs.get_summary(bp_id)
                result.append(BlueprintUsageDetail(**summary))
            except KeyError:
                result.append(BlueprintUsageDetail(id=bp_id, name=bp_id))
        return result

    def _enrich_resources(self, res_ids: list) -> list[ResourceUsageDetail]:
        result: list[ResourceUsageDetail] = []
        for res_id in res_ids:
            try:
                res = self._registry.get(res_id)
                result.append(
                    ResourceUsageDetail(
                        id=res_id,
                        name=res.name,
                        category=res.category,
                        type=res.type,
                    )
                )
            except KeyError:
                result.append(ResourceUsageDetail(id=res_id, name=res_id))
        return result
