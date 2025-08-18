from elements.common.base_element_spec import BaseElementSpec
from core.enums import ResourceCategory
from ..config import McpProxyToolConfig
from ..mcp_proxy_factory import McpProxyToolFactory
from ..identifiers import Identifier, META


class McpProxyToolElementSpec(BaseElementSpec):
    """Element specification for MCP Proxy Tool."""

    category = ResourceCategory.TOOL
    type_key = Identifier.TYPE
    name = META.name
    description = META.description
    config_schema = McpProxyToolConfig
    factory_cls = McpProxyToolFactory
    tags = META.tags
