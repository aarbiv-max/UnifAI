from ..common.base_condition import BaseCondition
from ..common.models import ConditionOutputSchema, BranchType, DirectBranchDef
from graph.state.state_view import StateView
from graph.state.graph_state import Channel
from typing import Optional


class RouterDirectCondition(BaseCondition):
    """
    Router direct condition that reads target_branch from state and returns it directly.
    Returns node UIDs directly for branching.
    """
    
    # Declare what channels this condition reads
    READS = {Channel.TARGET_BRANCH}

    def __init__(self, default_target: Optional[str] = None):
        super().__init__()
        self.default_target = default_target

    def run(self, state: StateView) -> str:
        """
        Reads target_branch from state and returns it directly.
        Falls back to default_target if not found.
        """
        target_branch = state[Channel.TARGET_BRANCH]
        
        if target_branch is None:
            if self.default_target is not None:
                return self.default_target
            raise ValueError("target_branch not found in state and no default_target configured")
        
        return str(target_branch)

    def __repr__(self) -> str:
        return f"<RouterDirectCondition: target_branch -> direct routing (default: {self.default_target})>"

    @classmethod
    def get_output_schema(cls) -> ConditionOutputSchema:
        """
        RouterDirectCondition returns direct node UIDs for branching.
        """
        return ConditionOutputSchema(
            branch_type=BranchType.DIRECT,
            direct_config=DirectBranchDef(
                description="Routes directly to the target branch specified in state"
            ),
            description="Direct router condition that reads target_branch and routes to that node UID"
        )