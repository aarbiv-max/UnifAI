from dataclasses import dataclass
from typing import Any, Dict, Set
from core.enums import ResourceCategory


@dataclass(frozen=True)
class ElementCard:
    """
    Runtime element card: Complete view of an element for node communication.
    
    Cross-cutting data structure used by graph, session, and engine layers.
    Represents the composition of static spec info + runtime element data.
    """
    # Identity
    uid: str
    category: ResourceCategory
    type_key: str
    
    # Static info (from spec)
    name: str
    description: str
    capabilities: Set[str]
    reads: Set[str]
    writes: Set[str]
    
    # Runtime info
    instance: Any
    config: Any

    # Computed skills
    skills: Dict[str, Any]

    # StepMeta for graph context
    metadata: Any = None
    
    def __repr__(self) -> str:
        """Clean, LLM-friendly representation of the element card."""
        lines = []
        lines.append(f"Node: {self.name}")
        lines.append(f"UID: {self.uid}")
        lines.append(f"Type: {self.type_key}")
        lines.append(f"Description: {self.description}")
        
        # Capabilities
        if self.capabilities:
            lines.append(f"Capabilities: {', '.join(sorted(self.capabilities))}")
        
        # Channels
        # if self.reads:
        #     lines.append(f"Reads: {', '.join(sorted(self.reads))}")
        # if self.writes:
        #     lines.append(f"Writes: {', '.join(sorted(self.writes))}")
        
        # Skills (what this node can actually do)
        if self.skills:
            lines.append("Skills:")
            for skill_type, skill_data in self.skills.items():
                if skill_type == 'config':
                    if skill_data:
                        lines.append(f"  Configuration: {self._format_config(skill_data)}")
                elif isinstance(skill_data, list):
                    lines.append(f"  {skill_type.title()}s: {len(skill_data)} available")
                    for item in skill_data:  # Show ALL items, no limit
                        if isinstance(item, dict) and 'name' in item:
                            lines.append(f"    - {item['name']}: {item.get('description', 'No description')}")
                elif isinstance(skill_data, dict) and 'name' in skill_data:
                    lines.append(f"  {skill_type.title()}: {skill_data['name']} - {skill_data.get('description', 'No description')}")
                else:
                    lines.append(f"  {skill_type.title()}: {skill_data}")
        
        return "\n".join(lines)
    
    def _format_config(self, config: Dict[str, Any]) -> str:
        """Format config dict for readable display."""
        items = []
        for key, value in config.items():
            if isinstance(value, str) and len(value) > 1000:
                items.append(f"{key}='{value[:1000]}...'")
            else:
                items.append(f"{key}={repr(value)}")
        return "{" + ", ".join(items) + "}"