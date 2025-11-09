"""
Tool for getting detailed node information.
"""

from typing import Dict, Any, Callable
from pydantic import BaseModel, Field
from elements.tools.common.base_tool import BaseTool
from elements.nodes.common.agent.constants import ToolNames


class GetNodeCardArgs(BaseModel):
    """Arguments for getting a specific node's card."""
    uid: str = Field(..., description="UID of the node to inspect")


class GetNodeCardTool(BaseTool):
    """Get detailed information about a specific node."""
    
    name = ToolNames.TOPOLOGY_GET_NODE_CARD
    description = "Get detailed capability and skill information for a specific adjacent node"
    args_schema = GetNodeCardArgs
    
    def __init__(self, get_adjacent_nodes: Callable[[], Dict[str, Any]]):
        """
        Initialize with adjacency accessor.
        
        Args:
            get_adjacent_nodes: Function to get adjacent nodes dict
        """
        self._get_adjacent_nodes = get_adjacent_nodes
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Get specific node card."""
        args = GetNodeCardArgs(**kwargs)
        adjacent_nodes = self._get_adjacent_nodes()
        
        if args.uid not in adjacent_nodes:
            return {
                "found": False,
                "error": f"Node {args.uid} is not adjacent or does not exist"
            }
        
        card = adjacent_nodes.get_card(args.uid)
        
        # Extract detailed information
        node_details = {
            "found": True,
            "uid": args.uid,
            "name": card.name,
            "type": card.type_key,
            "description": card.description,
            "capabilities": list(card.capabilities) if card.capabilities else [],
            "reads_channels": list(card.reads) if card.reads else [],
            "writes_channels": list(card.writes) if card.writes else [],
            "skills": self._extract_skills(card.skills)
        }
        
        return node_details
    
    def _extract_skills(self, skills: Dict[str, Any]) -> Dict[str, Any]:
        """Extract skills in a structured format."""
        extracted = {}
        
        for skill_type, skill_data in skills.items():
            if isinstance(skill_data, list):
                # Extract tool/retriever names and descriptions
                extracted[skill_type] = [
                    {
                        "name": item.get("name", "Unknown"),
                        "description": item.get("description", "No description")
                    }
                    for item in skill_data
                    if isinstance(item, dict) and "name" in item
                ]
            elif isinstance(skill_data, dict) and "name" in skill_data:
                # Single skill item
                extracted[skill_type] = {
                    "name": skill_data["name"],
                    "description": skill_data.get("description", "No description")
                }
            else:
                # Other skill data
                extracted[skill_type] = skill_data
        
        return extracted
