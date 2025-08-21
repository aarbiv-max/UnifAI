from elements.nodes.common.base_config import NodeBaseConfig
from pydantic import Field
from typing import Optional, List, Literal
from .identifiers import Identifier
from core.ref.models import LLMRef, RetrieverRef, ToolRef, ProviderRef


class CustomAgentNodeConfig(NodeBaseConfig):
    """
    Custom agent node with full override capabilities.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    llm: LLMRef = Field(description="LLM Ref UID to use")
    retriever: Optional[RetrieverRef] = Field(None, description="Retriever key to use")
    tools: Optional[List[ToolRef]] = Field(default_factory=list, description="List of tool keys")
    provider: Optional[ProviderRef] = Field(default=None, description="MCP Provider Ref")
    system_message: str = Field("", description="Custom system prompt")
