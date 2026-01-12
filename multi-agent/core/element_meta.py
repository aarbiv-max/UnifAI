"""
core/element_meta.py

Universal metadata for element configurations.

Used by:
- Card building (ElementCardService)
- Validation (ElementValidationService)
- Any service that needs to process element configs
"""

from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel

from core.enums import ResourceCategory


@dataclass
class ElementConfigMeta:
    """
    Universal metadata about an element configuration.
    
    This is a plain data object that any module can create from its own
    data structures (BlueprintSpec, ResourceDoc, SessionRegistry, etc.)
    
    Used as input for:
    - ElementCardService.build_all_cards()
    - ElementValidationService.validate_ordered()
    
    Attributes:
        rid: Resource ID (unique identifier)
        category: Element category (NODE, TOOL, LLM, etc.)
        type_key: Element type (e.g., "custom_agent", "openai_llm")
        name: User-defined display name
        config: The Pydantic config model instance
        dependency_rids: Pre-computed list of referenced element rids
    """
    rid: str
    category: ResourceCategory
    type_key: str
    name: str
    config: BaseModel
    dependency_rids: List[str] = field(default_factory=list)
