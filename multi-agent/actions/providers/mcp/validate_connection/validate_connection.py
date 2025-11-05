import asyncio
import time
import json
import logging
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, HttpUrl, Field
from actions.common.base_action import BaseAction
from actions.common.action_models import BaseActionInput, BaseActionOutput, ActionType
from elements.providers.mcp_server_client.mcp_server_client import McpServerClient
from elements.providers.mcp_server_client.identifiers import Identifier
from core.enums import ResourceCategory

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


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
        
        logger.info(f"Validating MCP connection: endpoint={input_data.sse_endpoint}, transport_type={input_data.transport_type}")
        
        # Handle HTTP transport type validation
        if input_data.transport_type == "http":
            return await self._validate_http_connection(input_data.sse_endpoint, start_time)
        
        # Handle SSE transport type validation (original behavior)
        try:
            logger.info(f"Validating SSE connection to: {input_data.sse_endpoint}")
            # Create client and test connection
            client = McpServerClient(input_data.endpoint)
            
            async with client:
                # Test connection by listing tools with timeout
                await asyncio.wait_for(client.tools.get_tools(), timeout=10.0)
            
            response_time = (time.time() - start_time) * 1000
            
            logger.info(f"SSE connection validation successful")
            return ValidateConnectionOutput(
                success=True,
                message="Connection successful",
                is_reachable=True,
                response_time_ms=response_time
            )
            
        except asyncio.TimeoutError:
            logger.error(f"SSE connection validation timeout")
            return ValidateConnectionOutput(
                success=False,
                message="Connection timeout - server may be unreachable",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(f"SSE connection validation failed: {e}", exc_info=True)
            return ValidateConnectionOutput(
                success=False,
                message=f"Connection failed: {str(e)}",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _validate_http_connection(self, endpoint: HttpUrl, start_time: float) -> ValidateConnectionOutput:
        """
        Validate HTTP transport type connection.
        
        For HTTP transport, we expect a specific error response indicating
        the server is an HTTP endpoint (not SSE). The expected error is:
        {"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
        
        Args:
            endpoint: HTTP endpoint URL
            start_time: Validation start time
            
        Returns:
            Validation result with connection status
        """
        if not HTTPX_AVAILABLE:
            return ValidateConnectionOutput(
                success=False,
                message="httpx library is required for HTTP transport validation",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Ensure endpoint URL ends with /mcp if it doesn't already
            endpoint_str = str(endpoint)
            if not endpoint_str.endswith('/mcp') and '/mcp' not in endpoint_str:
                # Append /mcp if it's not already in the path
                endpoint_str = endpoint_str.rstrip('/') + '/mcp'
            
            logger.info(f"Validating HTTP connection to: {endpoint_str}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Make a GET request to the endpoint
                response = await client.get(endpoint_str)
                
                response_time = (time.time() - start_time) * 1000
                
                logger.info(f"HTTP validation response: status={response.status_code}, headers={dict(response.headers)}")
                
                # Get response text (may contain trailing % or whitespace)
                response_text = response.text.strip().rstrip('%').strip()
                
                # Check if we got the expected error response indicating HTTP endpoint
                try:
                    response_json = json.loads(response_text)
                    logger.info(f"Parsed JSON response: {response_json}")
                    
                    # Check for the specific error format that indicates HTTP endpoint
                    if (response_json.get("jsonrpc") == "2.0" and 
                        "error" in response_json and 
                        response_json.get("error", {}).get("code") == -32600 and
                        "text/event-stream" in str(response_json.get("error", {}).get("message", ""))):
                        logger.info("HTTP endpoint validation successful - received expected error response")
                        return ValidateConnectionOutput(
                            success=True,
                            message="HTTP endpoint is reachable (HTTP transport confirmed)",
                            is_reachable=True,
                            response_time_ms=response_time
                        )
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse JSON response: {e}, response text: {response_text[:200]}")
                    # If response is not JSON or doesn't match expected format,
                    # check if we got a valid HTTP response (status < 500)
                    if response.status_code < 500:
                        return ValidateConnectionOutput(
                            success=True,
                            message=f"HTTP endpoint is reachable (status: {response.status_code})",
                            is_reachable=True,
                            response_time_ms=response_time
                        )
                
                # If we got a different response, still consider it reachable if status < 500
                if response.status_code < 500:
                    return ValidateConnectionOutput(
                        success=True,
                        message=f"HTTP endpoint is reachable (status: {response.status_code})",
                        is_reachable=True,
                        response_time_ms=response_time
                    )
                else:
                    return ValidateConnectionOutput(
                        success=False,
                        message=f"HTTP endpoint returned error status: {response.status_code}",
                        is_reachable=False,
                        response_time_ms=response_time
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"HTTP validation timeout for {endpoint_str}")
            return ValidateConnectionOutput(
                success=False,
                message="Connection timeout - HTTP server may be unreachable",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(f"HTTP validation error for {endpoint_str}: {e}", exc_info=True)
            return ValidateConnectionOutput(
                success=False,
                message=f"HTTP connection failed: {str(e)}",
                is_reachable=False,
                response_time_ms=(time.time() - start_time) * 1000
            )
