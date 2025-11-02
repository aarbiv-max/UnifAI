"""
Tool for listing adjacent nodes.
"""

from typing import Dict, Any, Callable
from pydantic import BaseModel
from elements.tools.common.base_tool import BaseTool
from elements.nodes.common.agent.constants import ToolNames

class ListAdjacentNodeArgs(BaseModel):
    pass


class ListAdjacentNodesTool(BaseTool):
    """List all adjacent nodes with their capabilities."""
    
    name = ToolNames.TOPOLOGY_LIST_ADJACENT
    description = "Get a list of all adjacent nodes with their capabilities and skills"
    args_schema = ListAdjacentNodeArgs  # No arguments needed
    
    def __init__(self, get_adjacent_nodes: Callable[[], Dict[str, Any]]):
        """
        Initialize with adjacency accessor.
        
        Args:
            get_adjacent_nodes: Function to get adjacent nodes dict
        """
        self._get_adjacent_nodes = get_adjacent_nodes
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """List adjacent nodes."""
        adjacent_nodes = self._get_adjacent_nodes()
        
        if not adjacent_nodes:
            return {
                "adjacent_count": 0,
                "nodes": []
            }
        
        # Extract key information from each ElementCard
        nodes_info = []
        for uid, card in adjacent_nodes.items():
            node_info = {
                "uid": uid,
                "name": card.name,
                "type": card.type_key,
                "description": card.description,
                "capabilities": list(card.capabilities) if card.capabilities else [],
                "skills_summary": self._summarize_skills(card.skills)
            }
            nodes_info.append(node_info)
        
        return {
            "adjacent_count": len(adjacent_nodes),
            "nodes": nodes_info
        }
    
    def _summarize_skills(self, skills: Dict[str, Any]) -> Dict[str, int]:
        """Summarize skills by counting items in each category."""
        summary = {}
        for skill_type, skill_data in skills.items():
            if isinstance(skill_data, list):
                summary[skill_type] = len(skill_data)
            elif isinstance(skill_data, dict):
                # For dict skills, count keys
                summary[skill_type] = len(skill_data)
            else:
                summary[skill_type] = 1
        return summary
