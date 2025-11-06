from typing import List, Dict, Optional, Iterator, Any
from session.session_registry import SessionRegistry
from core.element_card_builder import ElementCardBuilder
from core.models import ElementCard
from core.enums import ResourceCategory
from .graph_plan import GraphPlan
from .models import Step, RTStep
from .models import StepContext


class RTGraphPlan:
    """
    Runtime-enabled GraphPlan wrapper.

    Composes a logical GraphPlan and provides the same interface
    but with RTStep objects containing bound callables.
    """

    def __init__(self, logical_plan: GraphPlan, session_registry: SessionRegistry):
        self._logical_plan = logical_plan
        self._session = session_registry
        self._card_builder = ElementCardBuilder(session_registry)
        self._rt_steps: Dict[str, RTStep] = {}
        self._build_runtime_steps()

    @property
    def steps(self) -> List[RTStep]:
        """Get all runtime steps."""
        return list(self._rt_steps.values())

    def get_step(self, uid: str) -> Optional[RTStep]:
        """Get runtime step by uid."""
        return self._rt_steps.get(uid)

    def get_roots(self) -> List[RTStep]:
        """Get steps with no dependencies."""
        return [self._rt_steps[s.uid] for s in self._logical_plan.get_roots()]

    def get_leaves(self) -> List[RTStep]:
        """Get steps with no dependents."""
        return [self._rt_steps[s.uid] for s in self._logical_plan.get_leaves()]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for debugging (delegates to logical plan)."""
        return self._logical_plan.to_dict()

    def add_step(self, step: RTStep) -> None:
        """Add step (for interface compatibility if needed)."""
        raise NotImplementedError("RTGraphPlan is immutable after construction")

    def remove_step(self, uid: str) -> None:
        """Remove step (for interface compatibility if needed)."""
        raise NotImplementedError("RTGraphPlan is immutable after construction")

    def pretty_print(self) -> None:
        """Print plan structure (delegates to logical plan)."""
        self._logical_plan.pretty_print()

    def __iter__(self) -> Iterator[RTStep]:
        """Iterate over runtime steps."""
        return iter(self.steps)

    def __len__(self) -> int:
        """Number of steps."""
        return len(self._rt_steps)

    # ------------------------------------------------------------------ #
    #  Private Implementation
    # ------------------------------------------------------------------ #

    def _build_runtime_steps(self) -> None:
        """Build all runtime steps from logical steps."""
        for logical_step in self._logical_plan.steps:
            rt_step = self._create_runtime_step(logical_step)
            self._rt_steps[logical_step.uid] = rt_step

    def _create_runtime_step(self, step: Step) -> RTStep:
        """Create a runtime step from a logical step."""
        # ------------------------------------------------------------------ #
        # 1. Build rich StepContext (adjacent nodes + branching logic + topology)
        # ------------------------------------------------------------------ #
        from .models import AdjacentNodes
        from .topology.finalizer_analyzer import FinalizerAnalyzer
        
        adjacent_nodes_dict = {}
        
        # Find direct connections: steps that have this step in their 'after' list
        for other_step in self._logical_plan.steps:
            if step.uid in other_step.after:
                # This other_step executes directly after current step
                card = self._card_builder.build_card(
                    ResourceCategory.NODE, 
                    other_step.rid,
                    uid=other_step.uid, 
                    metadata=other_step.meta
                )
                adjacent_nodes_dict[other_step.uid] = card
        
        # Add conditional connections (branches from this step)
        branches: Dict[str, str] = step.branches or {}
        for outcome, next_uid in branches.items():
            tgt = self._logical_plan.get_step(next_uid)
            if tgt is not None:
                card = self._card_builder.build_card(
                    ResourceCategory.NODE,
                    tgt.rid,
                    uid=tgt.uid,
                    metadata=tgt.meta
                )
                adjacent_nodes_dict[next_uid] = card

        # Create clean Pydantic model
        adjacent_nodes = AdjacentNodes.from_dict(adjacent_nodes_dict)
        
        # ------------------------------------------------------------------ #
        # 2. Analyze topology (paths to finalizers with cycle prevention)
        # ------------------------------------------------------------------ #
        analyzer = FinalizerAnalyzer(output_channel="output")  # Channel.OUTPUT maps to "output"
        adjacent_node_uids = list(adjacent_nodes_dict.keys())
        
        topology = analyzer.analyze_node_topology(
            plan=self._logical_plan,
            from_node_uid=step.uid,
            adjacent_node_uids=adjacent_node_uids
        )

        step_context = StepContext(
            uid=step.uid,
            metadata=step.meta,
            adjacent_nodes=adjacent_nodes,
            branches=branches,
            topology=topology,
        )

        # ------------------------------------------------------------------ #
        # 3. Bind node & condition callables + inject context
        # ------------------------------------------------------------------ #

        node_func = self._session.get_instance(ResourceCategory.NODE, step.rid)
        if hasattr(node_func, "set_context"):
            node_func.set_context(step_context)

        condition_func = None
        if step.condition:
            condition_func = self._session.get_instance(ResourceCategory.CONDITION, step.condition.rid)
            if hasattr(condition_func, "set_context"):
                condition_func.set_context(step_context)

        return RTStep(
            step=step,
            func=node_func,
            exit_condition=condition_func,
        )
