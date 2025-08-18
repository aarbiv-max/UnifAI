from typing import Set, List, Tuple, AbstractSet
from graph.graph_plan import GraphPlan
from ..models import ValidationMessage, MessageSeverity, MessageCode
from .models import RequiredNodeIssue, NodePosition


class RequiredNodesChecker:
    """Business logic for checking required node types."""

    def __init__(self, required_start_nodes: Set[str] = None, 
                 required_end_nodes: Set[str] = None, 
                 required_any_nodes: Set[str] = None):
        self._required_start_nodes = set(required_start_nodes or set())
        self._required_end_nodes = set(required_end_nodes or set())
        self._required_any_nodes = set(required_any_nodes or set())

    def check_required_nodes(self, plan: GraphPlan) -> Tuple[List[RequiredNodeIssue], List[ValidationMessage]]:
        """Check that required node types are present."""
        messages = []
        required_node_issues = []

        # Get node type sets
        root_types = {s.type_key for s in plan.get_roots()}
        leaf_types = {s.type_key for s in plan.get_leaves()}
        all_types = {s.type_key for s in plan.steps}

        # Check each group
        self._check_nodes(
            self._required_start_nodes,
            root_types,
            NodePosition.START,
            MessageCode.MISSING_START_NODE,
            messages,
            required_node_issues
        )

        self._check_nodes(
            self._required_end_nodes,
            leaf_types,
            NodePosition.END,
            MessageCode.MISSING_END_NODE,
            messages,
            required_node_issues
        )

        self._check_nodes(
            self._required_any_nodes,
            all_types,
            NodePosition.ANY,
            MessageCode.MISSING_REQUIRED_NODE,
            messages,
            required_node_issues
        )

        return required_node_issues, messages



    def _check_nodes(self, required_specs: AbstractSet[str], available_specs: AbstractSet[str],
                    node_type: NodePosition, error_code: MessageCode, messages: List[ValidationMessage],
                    required_node_issues: List[RequiredNodeIssue]) -> None:
        """Check for missing required nodes."""
        for spec in required_specs - available_specs:
            required_node_issues.append(
                RequiredNodeIssue(
                    node_type=node_type,
                    expected=spec,
                    actual=None if not available_specs else next(iter(available_specs)),
                )
            )

            verb = {"start": "start with", "end": "end with", "any": "contain"}[node_type]
            messages.append(
                ValidationMessage(
                    text=f"Graph must {verb} '{spec}' node",
                    severity=MessageSeverity.ERROR,
                    code=error_code,
                    context={"expected": spec, "available": list(available_specs)}
                )
            ) 