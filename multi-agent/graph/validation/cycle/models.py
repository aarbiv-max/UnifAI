from typing import List
from enum import Enum
from pydantic import BaseModel, ConfigDict, computed_field


class EdgeType(str, Enum):
    AFTER = "after"
    BRANCH = "branch"
    UNKNOWN = "unknown"


class CycleFixType(str, Enum):
    REMOVE_BRANCH = "remove_branch"
    REVIEW_BRANCHES = "review_branches"
    REMOVE_DEPENDENCY = "remove_dependency"
    ADD_EXIT_NODE = "add_exit_node"


class CycleInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    cycle_path: List[str]
    
    @computed_field
    @property
    def cycle_length(self) -> int:
        return len(self.cycle_path) 