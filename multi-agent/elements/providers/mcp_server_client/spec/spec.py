from typing import ClassVar, Type, List
from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import McpProviderConfig
from ..mcp_provider_factory import McpProviderFactory
from ..identifiers import Identifier, META


class McpProviderElementSpec(BaseElementSpec):
    """
    Element specification for MCP Provider.
    
    Provides MCP server connection and management capabilities.
    Note: Actions for MCP operations are now managed independently via the ActionsService.
    """

    category: ClassVar[ResourceCategory] = ResourceCategory.PROVIDER
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = McpProviderConfig
    factory_cls = McpProviderFactory
    tags = META.tags