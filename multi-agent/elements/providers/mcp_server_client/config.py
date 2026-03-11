from typing import Literal, List, Optional
from .identifiers import Identifier
from pydantic import Field, HttpUrl
from elements.providers.common.base_config import ProviderBaseConfig
from core.field_hints import ActionHint, HintType, SelectionType, SecretHint
from .transport.enums import McpTransportType


class McpProviderConfig(ProviderBaseConfig):
    """
    Connects to a Model-Context-Protocol service via SSE or Streamable HTTP transport.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    transport_type: McpTransportType = Field(
        default=McpTransportType.STREAMABLE_HTTP,
        description="Transport protocol to use for MCP server communication (sse or streamable http)"
    )
    mcp_url: HttpUrl = Field(
        description="MCP server endpoint URL",
        json_schema_extra=ActionHint(
            action_uid="mcp.validate_connection",
            hint_type=HintType.VALIDATE,
            field_mapping="is_reachable",
            dependencies={
                "bearer_token": "bearer_token",
                "transport_type": "transport_type",
            }
        ).to_hints()
    )
    bearer_token: Optional[str] = Field(
        default=None,
        description="Bearer token for MCP server authentication (sent as 'Authorization: Bearer <token>' header)",
        json_schema_extra=SecretHint(reason="API credentials should be masked").to_hints()
    )
    tool_names: Optional[List[str]] = Field(
        default_factory=list,
        description="List of specific tool names to use from the MCP server",
        json_schema_extra=ActionHint(
            action_uid="mcp.get_tools_names",
            hint_type=HintType.POPULATE,
            selection_type=SelectionType.MANUAL,
            field_mapping="tool_names",
            multi_select=True,
            dependencies={
                "mcp_url": "mcp_url",
                "bearer_token": "bearer_token",
                "transport_type": "transport_type",
            }
        ).to_hints()
    )
