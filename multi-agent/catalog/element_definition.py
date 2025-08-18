from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class ElementDefinition:
    """
    Pure UI DTO for element information.
    
    Contains only what the UI needs to display and work with element specs.
    No longer contains factory or schema references - those are handled
    by the ElementRegistry and BaseElementSpec.
    """
    category: str
    type_key: str
    display_name: str
    description: str
    version: str
    tags: List[str]
    dependencies: List[str]  # category names this element depends on
    schema_json: Dict[str, Any]  # JSON schema for dynamic form generation
