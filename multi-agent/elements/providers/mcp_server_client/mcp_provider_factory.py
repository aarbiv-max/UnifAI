from typing import Any
from elements.common.base_factory import BaseFactory
from elements.common.exceptions import PluginConfigurationError
from .config import McpProviderConfig
from .mcp_provider import McpProvider
from .identifiers import Identifier


class McpProviderFactory(BaseFactory[McpProviderConfig, McpProvider]):
    """
    Factory for creating MCP Provider instances from McpProviderConfig.
    """

    def accepts(self, cfg: McpProviderConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: McpProviderConfig, **kwargs: Any) -> McpProvider:
        """
        Instantiate an McpProvider using validated config values.

        :param cfg: Fully‐validated McpProviderConfig
        :raises PluginConfigurationError: if instantiation fails
        """
        try:
            # Use the clean sync factory method which handles async internally
            return McpProvider.create_sync(
                endpoint=cfg.endpoint,
                tool_names=cfg.tool_names
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"McpProvider.create() failed: {e}",
                cfg.dict()
            ) from e

    async def create_async(self, cfg: McpProviderConfig, **kwargs: Any) -> McpProvider:
        """
        Async version of create() for better performance when called from async context.

        :param cfg: Fully‐validated McpProviderConfig
        :raises PluginConfigurationError: if instantiation fails
        """
        try:
            # Use the async factory method directly for better performance
            return await McpProvider.create_async(
                endpoint=cfg.endpoint,
                tool_names=cfg.tool_names
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"McpProvider.create_async() failed: {e}",
                cfg.dict()
            ) from e