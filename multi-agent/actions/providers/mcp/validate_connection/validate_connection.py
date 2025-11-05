import asyncio
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
from actions.common.base_action import BaseAction
from actions.common.action_models import BaseActionInput, BaseActionOutput, ActionType
from elements.providers.mcp_server_client.mcp_server_client import McpServerClient
from elements.providers.mcp_server_client.identifiers import Identifier
from core.enums import ResourceCategory


# Input/Output models for this action
class ValidateConnectionInput(BaseActionInput):
    """Input for MCP connection validation"""
    endpoint: HttpUrl


class ValidateConnectionOutput(BaseActionOutput):
    """Output for MCP connection validation"""
    is_reachable: bool = False
    response_time_ms: float = 0.0


class ValidateConnectionAction(BaseAction):
    """
    Validates MCP server connection.
    
    This action can work with any MCP-compatible element or independently.
    Single Responsibility: Only validates connection reachability
    """
    
    uid = "mcp.validate_connection"
    name = "validate_connection"
    description = "Validate that the MCP server endpoint is reachable and responding"
    action_type = ActionType.VALIDATION
    input_schema = ValidateConnectionInput
    output_schema = ValidateConnectionOutput
    version = "1.0.0"
    tags = {"mcp", "validation", "connectivity"}
    elements = {(ResourceCategory.PROVIDER.value, Identifier.TYPE)}
    
    async def execute(self, input_data: ValidateConnectionInput, 
                     context: Optional[Dict[str, Any]] = None) -> ValidateConnectionOutput:
        """
        Execute connection validation with optional context.
        
        Args:
            input_data: Validated connection input
            context: Optional execution context (element configs, etc.)
            
        Returns:
            Validation result with connection status and timing
        """
        start_time = time.time()
        
        try:
            # Create client and test connection
            client = McpServerClient(input_data.endpoint)
            
            async with client:
                # Test connection by listing tools with timeout
                await asyncio.wait_for(client.tools.get_tools(), timeout=10.0)
            
            response_time = (time.time() - start_time) * 1000
            
            return ValidateConnectionOutput(
                success=True,
                message="Connection successful",
                is_reachable=True,
                response_time_ms=response_time
            )
            
        except asyncio.TimeoutError:
            return ValidateConnectionOutput(
                success=False,
                message="Connection timeout - server may be unreachable",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ValidateConnectionOutput(
                success=False,
                message=f"Connection failed: {str(e)}",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
