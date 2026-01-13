"""
validation/models.py

Models for validation orchestration (service-level).
Element-level models live in elements/common/validator.py
"""

from dataclasses import dataclass, field
from typing import Dict

from elements.common.validator import ElementValidationResult


@dataclass
class BlueprintValidationResult:
    """Result of validating an entire blueprint."""
    blueprint_id: str
    is_valid: bool
    element_results: Dict[str, ElementValidationResult] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "blueprint_id": self.blueprint_id,
            "is_valid": self.is_valid,
            "element_results": {
                rid: r.to_dict() for rid, r in self.element_results.items()
            },
        }
