from typing import List, Set, Dict, Tuple
from collections import deque
from graph.graph_plan import GraphPlan
from ..models import ValidationMessage, MessageSeverity, MessageCode
from .models import CycleInfo


class CycleDetector:
    """Detects cycles in graph execution flow."""

    def detect_cycles(self, plan: GraphPlan) -> Tuple[List[CycleInfo], List[ValidationMessage]]:
        """Detect all cycles using comprehensive graph traversal."""
        cycles = []
        messages = []

        # Build complete adjacency graph including edge type metadata
        adjacency, edge_types = self._build_execution_graph(plan)

        # Pre-compute terminal (exit) nodes: nodes with no outgoing edges
        terminal_nodes = {node for node, neighbours in adjacency.items() if not neighbours}

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()

        for node in adjacency:
            if node not in visited:
                found_cycles = self._dfs_cycle_detection(node, adjacency, visited, rec_stack, [])
                cycles.extend(found_cycles)

        # Filter cycles based on edge types and exit paths
        filtered_cycles: List[CycleInfo] = []
        for cycle in cycles:
            if self._is_dangerous_cycle(cycle, adjacency, edge_types, terminal_nodes):
                filtered_cycles.append(cycle)

        # Create messages for each dangerous cycle
        for cycle in filtered_cycles:
            messages.append(ValidationMessage(
                text=f"Graph contains cycle: {' -> '.join(cycle.cycle_path)}",
                severity=MessageSeverity.ERROR,
                code=MessageCode.CYCLE_DETECTED,
                context={
                    "cycle_path": cycle.cycle_path,
                    "cycle_length": cycle.cycle_length
                }
            ))

        return filtered_cycles, messages

    def _build_execution_graph(self, plan: GraphPlan) -> Tuple[Dict[str, Set[str]], Dict[Tuple[str, str], str]]:
        """Build execution graph plus edge-type mapping."""
        adjacency: Dict[str, Set[str]] = {}
        edge_types: Dict[Tuple[str, str], str] = {}

        for step in plan.steps:
            adjacency[step.uid] = set()

        # First, handle dependency edges (after): parent -> child
        for child in plan.steps:
            for parent_uid in child.after:
                if parent_uid not in adjacency:
                    # Skip missing references; DependencyChecker will flag them.
                    continue
                adjacency[parent_uid].add(child.uid)
                edge_types[(parent_uid, child.uid)] = "after"

        # Now, handle branch edges
        for step in plan.steps:
            for target in step.branches.values():
                adjacency[step.uid].add(target)
                edge_types[(step.uid, target)] = "branch"

        return adjacency, edge_types

    def _is_dangerous_cycle(
            self,
            cycle: CycleInfo,
            adjacency: Dict[str, Set[str]],
            edge_types: Dict[Tuple[str, str], str],
            terminal_nodes: Set[str],
    ) -> bool:
        """Determine if the given cycle is inescapable or unconditional."""

        # Normalize cycle path (last element duplicates the first)
        path = cycle.cycle_path
        if len(path) > 1 and path[0] == path[-1]:
            path = path[:-1]

        cycle_nodes = set(path)

        # Rule 1: unconditional edge inside cycle?
        for u, v in zip(path, path[1:] + [path[0]]):
            if edge_types.get((u, v)) == "after":
                return True  # unconditional loop -> dangerous

        # Rule 2: all edges are branch; check for exit path
        return not self._cycle_has_exit(cycle_nodes, adjacency, terminal_nodes)

    def _cycle_has_exit(
            self,
            cycle_nodes: Set[str],
            adjacency: Dict[str, Set[str]],
            terminal_nodes: Set[str],
    ) -> bool:
        """Return True if a path exists from the cycle to any terminal node."""
        q = deque(cycle_nodes)
        visited = set(cycle_nodes)

        while q:
            node = q.popleft()
            for neighbor in adjacency.get(node, set()):
                if neighbor in visited:
                    continue
                if neighbor in terminal_nodes:
                    return True  # Found an exit path
                visited.add(neighbor)
                q.append(neighbor)

        return False  # No exits found

    def _dfs_cycle_detection(self, node: str, adjacency: Dict[str, Set[str]],
                             visited: Set[str], rec_stack: Set[str],
                             path: List[str]) -> List[CycleInfo]:
        """DFS-based cycle detection."""
        visited.add(node)
        rec_stack.add(node)
        current_path = path + [node]
        cycles = []

        for neighbor in adjacency.get(node, set()):
            if neighbor not in visited:
                cycles.extend(self._dfs_cycle_detection(
                    neighbor, adjacency, visited, rec_stack, current_path
                ))
            elif neighbor in rec_stack:
                # Found cycle - extract cycle path
                try:
                    cycle_start_idx = current_path.index(neighbor)
                    cycle_path = current_path[cycle_start_idx:] + [neighbor]
                    cycles.append(CycleInfo(cycle_path=cycle_path))
                except ValueError:
                    # Handle edge case where neighbor not in current path
                    cycle_path = current_path + [neighbor]
                    cycles.append(CycleInfo(cycle_path=cycle_path))

        rec_stack.remove(node)
        return cycles
