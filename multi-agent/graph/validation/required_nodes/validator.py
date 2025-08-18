from typing import Set
from graph.graph_plan import GraphPlan
from ..interfaces import ValidationProvider
from ..models import ValidationReport
from ..settings import ValidationSettings
from .checker import RequiredNodesChecker


class RequiredNodesValidator(ValidationProvider):
    """Validates that required node types are present in the graph."""

    def __init__(self, settings: ValidationSettings = None, *args, **kwargs):
        settings = settings or ValidationSettings()
        self._checker = RequiredNodesChecker(
            required_start_nodes=settings.required_start_nodes,
            required_end_nodes=settings.required_end_nodes,
            required_any_nodes=settings.required_any_nodes
        )

    def validate(self, plan: GraphPlan) -> ValidationReport:
        issues, messages = self._checker.check_required_nodes(plan)
        
        return ValidationReport(
            validator_name=self.name,
            is_valid=len(issues) == 0,
            messages=messages,
            details={"required_node_issues": [issue.model_dump() for issue in issues]}
        ) 