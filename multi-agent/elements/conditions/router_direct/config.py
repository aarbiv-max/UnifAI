from typing import Literal, Optional
from pydantic import Field
from elements.conditions.common.base_config import BaseConditionConfig
from .identifiers import Identifier


class RouterDirectConditionConfig(BaseConditionConfig):
    """
    Configuration for the router direct condition that reads target_branch and returns it directly.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    default_target: Optional[str] = Field(
        None,
        description="Default branch to return if target_branch is not found in state"
    )