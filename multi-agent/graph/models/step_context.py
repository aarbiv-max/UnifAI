from dataclasses import dataclass, field
from typing import Dict

from blueprints.models.blueprint import StepMeta
from .adjacency import AdjacentNodes
from ..topology.models import StepTopology


# @dataclass(frozen=True, slots=True) slots once we migrate to Python ≥3.10
@dataclass(frozen=True)
class StepContext:
    """Immutable context object injected into nodes / conditions at runtime."""

    # Identity & author metadata
    uid: str
    metadata: StepMeta = field(default_factory=StepMeta)

    # All adjacent nodes (both direct and conditional) - clean Pydantic model
    adjacent_nodes: AdjacentNodes = field(default_factory=AdjacentNodes.empty)
    
    # Branching logic (outcome → uid)
    branches: Dict[str, str] = field(default_factory=dict)
    
    # Topology information about adjacent nodes and their paths to important destinations
    topology: StepTopology = field(default_factory=StepTopology)
