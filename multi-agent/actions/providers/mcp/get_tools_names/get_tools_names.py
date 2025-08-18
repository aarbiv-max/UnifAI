from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
from actions.common.base_action import BaseAction
from actions.common.action_models import BaseActionInput, BaseActionOutput, ActionType
from elements.providers.mcp_server_client.mcp_server_client import McpServerClient
from elements.providers.mcp_server_client.identifiers import Identifier
from core.enums import ResourceCategory


# Input/Output models for this action
class GetToolsNamesInput(BaseActionInput):
    """Input for MCP tools discovery"""
    sse_endpoint: HttpUrl


class GetToolsNamesOutput(BaseActionOutput):
    """Output for MCP tools discovery"""
    tool_names: List[str] = []
    total_count: int = 0


class GetToolsNamesAction(BaseAction):
    """
    Discovers available tool names from MCP server.
    
    This action can work with any MCP-compatible element or independently.
    Single Responsibility: Only discovers and returns tool names
    """
    
    uid = "mcp.get_tools_names"
    name = "get_tools_names"
    description = "Retrieve the list of available tool names from the MCP server"
    action_type = ActionType.DISCOVERY
    input_schema = GetToolsNamesInput
    output_schema = GetToolsNamesOutput
    version = "1.0.0"
    tags = {"mcp", "discovery", "tools"}
    elements = {(ResourceCategory.PROVIDER.value, Identifier.TYPE)}
    
    async def execute(self, input_data: GetToolsNamesInput, 
                     context: Optional[Dict[str, Any]] = None) -> GetToolsNamesOutput:
        """
        Execute tools discovery asynchronously.
        
        Args:
            input_data: Validated discovery input
            context: Optional execution context (element configs, etc.)
            
        Returns:
            Discovery result with tool names and count
        """
        try:
            # Create client and discover tools
            client = McpServerClient(input_data.sse_endpoint)
            
            async with client:
                tools = await client.tools.get_tools()
                tool_names = [tool.name for tool in tools]
            
            return GetToolsNamesOutput(
                success=True,
                message=f"Found {len(tool_names)} tools",
                tool_names=tool_names,
                total_count=len(tool_names)
            )
            
        except Exception as e:
            return GetToolsNamesOutput(
                success=False,
                message=f"Failed to retrieve tools: {str(e)}",
                tool_names=[],
                total_count=0
            )
