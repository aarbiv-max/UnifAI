from abc import ABC, abstractmethod
from typing import Any, Callable, Dict
from graph.rt_graph_plan import RTGraphPlan
from engine.executor.interfaces import GraphExecutor


class BaseGraphBuilder(ABC):
    """
    Abstract interface for any graph execution engine.

    Subclasses must implement node/edge wiring and entry/exit.
    """

    @abstractmethod
    def add_node(self, uid: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Register a node in the engine under `uid` with its execution function.
        """
        ...

    @abstractmethod
    def add_edge(self, from_node: str, to_node: str) -> None:
        """
        Add an unconditional edge: from_node → to_node.
        """
        ...

    @abstractmethod
    def add_conditional_edge(
            self,
            from_node: str,
            condition: Callable[[Dict[str, Any]], Any],
            branches: Dict[Any, str]
    ) -> None:
        """
        Add one or more edges out of `from_node` guarded by `condition`.
        `branches` maps condition-output → next‐node uid.
        """
        ...

    @abstractmethod
    def set_entry(self, uid: str) -> None:
        """
        Mark `uid` as the graph’s entry point.
        """
        ...

    @abstractmethod
    def set_exit(self, uid: str) -> None:
        """
        Mark `uid` as the graph’s exit / finish point.
        """
        ...

    @abstractmethod
    def build_executor(self) -> GraphExecutor:
        """
        Compile and return the engine’s executable graph object.
        """
        ...

    def compile_from_plan(
            self,
            plan: RTGraphPlan) -> GraphExecutor:
        """
        Default helper: wires up all steps, dependencies, conditionals,
        and identifies entry/exit, then builds.
        """
        # 1) add every node
        for step in plan.steps:
            self.add_node(step.uid, step.func)

        # 2) add dependencies and conditionals
        for step in plan.steps:
            # unconditional dependencies
            for dep in step.after:
                self.add_edge(dep, step.uid)

            # conditional branches (cycles or forks)
            if step.exit_condition and step.branches:
                self.add_conditional_edge(step.uid, step.exit_condition, step.branches)

        # 3) pick a single entry & exit (you could relax to multiple)
        roots = plan.get_roots()
        leaves = plan.get_leaves()
        if not roots:
            raise ValueError("Plan has no root steps.")
        if not leaves:
            raise ValueError("Plan has no leaf steps.")
        self.set_entry(roots[0].uid)
        self.set_exit(leaves[0].uid)

        # 4) compile
        return self.build_executor()
