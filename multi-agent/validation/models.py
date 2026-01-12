"""
validation/models.py

Models for validation orchestration (service-level).
Element-level models live in elements/common/validator.py

Note: ConfigMeta has been replaced by ElementConfigMeta in core/element_meta.py
This file now only contains validation-specific result models.
"""

from dataclasses import dataclass, field
from typing import Dict

from elements.common.validator import ElementValidationResult

# Re-export ElementConfigMeta for backwards compatibility
from core.element_meta import ElementConfigMeta

# Alias for backwards compatibility - prefer using ElementConfigMeta directly
ConfigMeta = ElementConfigMeta


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
