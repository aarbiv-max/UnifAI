from dataclasses import dataclass, field
from typing import Dict

from blueprints.models.blueprint import StepMeta
from core.models import ElementCard


# @dataclass(frozen=True, slots=True) slots once we migrate to Python ≥3.10
@dataclass(frozen=True)
class StepContext:
    """Immutable context object injected into nodes / conditions at runtime."""

    # Identity & author metadata
    uid: str
    metadata: StepMeta = field(default_factory=StepMeta)

    # All adjacent nodes (both direct and conditional) - uid → ElementCard
    adjacent_nodes: Dict[str, ElementCard] = field(default_factory=dict)
    
    # Branching logic (outcome → uid)
    branches: Dict[str, str] = field(default_factory=dict)
