from typing import Any, Dict, Optional
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

    def _build_headers(self, bearer_token: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Build HTTP headers from bearer token if provided.
        
        Args:
            bearer_token: Optional bearer token for authentication
            
        Returns:
            Headers dict with Authorization header, or None if no token
        """
        if bearer_token:
            return {"Authorization": f"Bearer {bearer_token}"}
        return None

    def create(self, cfg: McpProviderConfig, **kwargs: Any) -> McpProvider:
        """
        Instantiate an McpProvider using validated config values.

        :param cfg: Fully‐validated McpProviderConfig
        :raises PluginConfigurationError: if instantiation fails
        """
        try:
            # Build headers from bearer_token if provided
            headers = self._build_headers(cfg.bearer_token)
            
            # Use the clean sync factory method which handles async internally
            return McpProvider.create_sync(
                sse_endpoint=cfg.sse_endpoint,
                tool_names=cfg.tool_names,
                headers=headers,
                transport_type=cfg.transport_type,
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
            # Build headers from bearer_token if provided
            headers = self._build_headers(cfg.bearer_token)
            
            # Use the async factory method directly for better performance
            return await McpProvider.create_async(
                sse_endpoint=cfg.sse_endpoint,
                tool_names=cfg.tool_names,
                headers=headers,
                transport_type=cfg.transport_type,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"McpProvider.create_async() failed: {e}",
                cfg.dict()
            ) from e