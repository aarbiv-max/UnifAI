from enum import Enum
from dataclasses import dataclass
from typing import List


class Identifier(str, Enum):
    """Machine-readable key for the Builder Agent node."""
    TYPE = "builder_node"


class BuilderPhase(str, Enum):
    """Phases of the builder agent workflow."""
    ANALYZE = "analyze"
    SEARCH = "search"
    DESIGN = "design"
    VALIDATE = "validate"
    COMPLETE = "complete"


@dataclass(frozen=True)
class Meta:
    """Human-readable metadata about the element."""
    name: str
    description: str
    tags: List[str]


META = Meta(
    name="Builder Agent Node",
    description="Multi-phase agent that creates workflows based on user requirements. "
                "Analyzes requests, searches for available resources, designs workflows, "
                "and validates before presenting for approval.",
    tags=[
        "agent",
        "node",
        "builder",
        "workflow",
        "automation",
        "multi-phase",
    ],
)

