from typing import Set, List, Tuple
from graph.graph_plan import GraphPlan
from ..models import ValidationMessage, MessageSeverity, MessageCode


class OrphanDetector:
    """Detects orphaned steps with no connections."""
    
    def detect_orphans(self, plan: GraphPlan) -> Tuple[Set[str], List[ValidationMessage]]:
        """Find steps with no dependencies or dependents."""
        orphaned_steps = set()
        messages = []
        
        all_nodes = {step.uid for step in plan.steps}
        connected_nodes = self._find_connected_nodes(plan)
        
        orphaned_steps = all_nodes - connected_nodes
        
        for orphan in orphaned_steps:
            messages.append(ValidationMessage(
                text=f"Step '{orphan}' is orphaned (no dependencies or dependents)",
                severity=MessageSeverity.WARNING,
                code=MessageCode.ORPHANED_STEP,
                context={"step_id": orphan}
            ))
        
        return orphaned_steps, messages
    
    def _find_connected_nodes(self, plan: GraphPlan) -> Set[str]:
        """Find all nodes that have dependencies or dependents."""
        connected = set()
        
        for step in plan.steps:
            # Has dependencies (incoming connections)
            if step.after:
                connected.add(step.uid)
                # Also add the dependencies as connected
                connected.update(step.after)
            
            # Has branch targets (outgoing connections)
            if step.branches:
                connected.add(step.uid)
                connected.update(step.branches.values())
            
            # Is a dependency of other steps (outgoing connections)
            for other in plan.steps:
                if step.uid in other.after:
                    connected.add(step.uid)
                    connected.add(other.uid)
        
        return connected 