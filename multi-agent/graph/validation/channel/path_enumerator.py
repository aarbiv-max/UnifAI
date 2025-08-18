from typing import Dict, List, Set
from graph.graph_plan import GraphPlan


class PathEnumerator:
    """Enumerates all possible execution paths through a graph."""

    def enumerate_paths(self, plan: GraphPlan) -> Dict[str, List[str]]:
        """Generate all execution paths through the graph."""
        paths = {}
        path_counter = 1

        # Build adjacency for traversal
        adjacency = self._build_adjacency(plan)

        # DFS from each root
        for root in plan.get_roots():
            self._dfs(root.uid, [], adjacency, plan, paths, path_counter)

        return paths

    def _build_adjacency(self, plan: GraphPlan) -> Dict[str, Set[str]]:
        """Build adjacency map from plan dependencies."""
        adjacency = {}

        for step in plan.steps:
            adjacency[step.uid] = set()

            # Add normal successors
            for other in plan.steps:
                if step.uid in other.after:
                    adjacency[step.uid].add(other.uid)

            # Add branch targets
            adjacency[step.uid].update(step.branches.values())

        return adjacency

    def _dfs(self,
             current: str,
             path: List[str],
             adjacency: Dict[str, Set[str]],
             plan: GraphPlan,
             paths: Dict[str, List[str]],
             counter: int) -> None:
        """DFS traversal to enumerate paths."""
        current_path = path + [current]
        step = plan.get_step(current)

        if not adjacency[current]:
            # Terminal node
            path_id = f"path_{len(paths) + 1}"
            paths[path_id] = current_path
        elif step.branches:
            # Conditional branching
            for branch_target in step.branches.values():
                if branch_target in adjacency:
                    self._dfs(branch_target, current_path, adjacency, plan, paths, counter)
        else:
            # Normal progression
            for next_step in adjacency[current]:
                self._dfs(next_step, current_path, adjacency, plan, paths, counter) 