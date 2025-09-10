import logging
import asyncio
from typing import List, Optional
from pydantic import HttpUrl
from mcp.types import Tool
from global_utils.utils.async_bridge import get_async_bridge
from elements.tools.mcp_proxy.mcp_proxy_tool import McpProxyTool
from elements.providers.mcp_server_client.mcp_server_client import McpServerClient
from .provider_tool_registry import ProviderToolRegistry


class McpProvider:
    """
    MCP Provider for managing tool discovery and creation.
    
    Handles the complete lifecycle of MCP tools from server discovery
    to tool instantiation. Optimizes performance through intelligent
    caching while maintaining thread safety across different execution
    contexts.
    
    The provider uses a single connection during initialization to
    discover and cache all tool metadata, then creates lightweight
    tool instances that use fresh connections for actual execution.
    
    Attributes:
        sse_endpoint: MCP server endpoint URL
        tool_names: List of specific tools to create (None for all)
        tools: List of created MCP proxy tool instances
    """

    def __init__(self, sse_endpoint: HttpUrl, tool_names: Optional[List[str]] = None):
        """
        Initialize MCP provider for the specified server.
        
        Creates a provider instance configured for the given MCP server.
        The provider is not fully initialized until create_async() or
        create_sync() is called to perform tool discovery.
        
        Args:
            sse_endpoint: MCP server endpoint URL for SSE communication
            tool_names: Specific tool names to create (None discovers all)
        """
        self.sse_endpoint = sse_endpoint
        self.tool_names = tool_names or []
        self._tools: List[McpProxyTool] = []
        self._initialized = False
        
        # Provider-level tool registry for caching
        self._tool_registry = ProviderToolRegistry()

    async def _initialize_tools(self) -> None:
        """
        Discover and cache tool metadata from the server.
        
        Establishes a connection to the MCP server, discovers available
        tools, caches their metadata, and creates tool instances. Uses
        a single connection for efficiency while maintaining thread safety
        for subsequent tool usage.
        """
        if self._initialized:
            return

        async with McpServerClient(sse_endpoint=self.sse_endpoint) as mcp_client:
            # Fetch all available tools in one go
            available_tools = await mcp_client.get_tools()
            print(f"Fetched {len(available_tools)} tools from MCP server: {[tool.name for tool in available_tools]}")
            
            # Cache tools in provider registry
            self._tool_registry.cache_tools(available_tools)
            
            # If no specific tool names provided, use all available
            if not self.tool_names:
                self.tool_names = [tool.name for tool in available_tools]

        self._tools = []
        for tool_name in self.tool_names:
            # Get cached tool info
            cached_tool_info = self._tool_registry.get_cached_tool_by_name(tool_name)
            if cached_tool_info:
                # Create tool with pre-cached schema
                tool = McpProxyTool.create_with_cached_schema(
                    tool_name, self.sse_endpoint, cached_tool_info
                )
                self._tools.append(tool)
            else:
                logging.warning(f"Tool '{tool_name}' not found in available tools")
        
        self._initialized = True

    def get_cached_tool_info(self, tool_name: str) -> Optional[Tool]:
        """
        Retrieve cached metadata for a specific tool.
        
        Returns tool information from the local cache without requiring
        a server connection. Useful for schema validation and tool
        introspection after provider initialization.
        
        Args:
            tool_name: Name of the tool to look up
            
        Returns:
            Tool metadata if cached, None if not found or not cached
        """
        return self._tool_registry.get_cached_tool_by_name(tool_name)

    def get_tools(self) -> List[McpProxyTool]:
        """
        Retrieve all available MCP proxy tools.
        
        Returns the complete list of tool instances created by this
        provider. Automatically initializes the provider if not already
        done, discovering tools from the server on first access.
        
        Returns:
            List of McpProxyTool instances ready for execution
        """
        # Ensure tools are initialized before returning
        if not self._initialized:
            with get_async_bridge() as bridge:
                bridge.run(self._initialize_tools())
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[McpProxyTool]:
        """
        Find a specific tool by its name.
        
        Searches the provider's tool collection for a tool with the
        exact specified name. Automatically initializes the provider
        if needed to discover available tools.
        
        Args:
            name: Exact name of the tool to find
            
        Returns:
            McpProxyTool instance if found, None if no match
        """
        # Ensure tools are initialized before searching
        if not self._initialized:
            with get_async_bridge() as bridge:
                bridge.run(self._initialize_tools())
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    def refresh_tools(self) -> None:
        """
        Refresh all tools by reinitializing them.
        """
        self._initialized = False
        self._tools.clear()
        self._tool_registry.clear_cache()
        with get_async_bridge() as bridge:
            bridge.run(self._initialize_tools())

    def clone(self) -> "McpProvider":
        """
        Create a new McpProvider with the same configuration.
        """
        return McpProvider(
            sse_endpoint=self.sse_endpoint,
            tool_names=self.tool_names.copy() if self.tool_names else None
        )

    @property
    def is_initialized(self) -> bool:
        """Check if the provider has been initialized."""
        return self._initialized

    @property
    def tool_count(self) -> int:
        """Get the number of tools in this provider."""
        return len(self._tools)
    
    @property
    def cached_tool_count(self) -> int:
        """Get the number of cached tools in the registry."""
        cached_tools = self._tool_registry.get_cached_tools()
        return len(cached_tools) if cached_tools else 0

    def __str__(self) -> str:
        return f"McpProvider(endpoint='{self.sse_endpoint}', tools={len(self._tools)}, cached={self.cached_tool_count})"

    @classmethod
    async def create_async(cls, sse_endpoint: HttpUrl, tool_names: Optional[List[str]] = None) -> "McpProvider":
        """
        Async factory method for creating a fully initialized McpProvider.
        
        Args:
            sse_endpoint: HTTP(S) endpoint that streams SSE events
            tool_names: List of specific tool names to use from the MCP server
            
        Returns:
            Fully initialized McpProvider instance
        """
        provider = cls(sse_endpoint, tool_names)
        await provider._initialize_tools()
        return provider

    @classmethod
    def create_sync(cls, sse_endpoint: HttpUrl, tool_names: Optional[List[str]] = None) -> "McpProvider":
        """
        Sync factory method for creating a fully initialized McpProvider.
        Uses AsyncBridge internally to handle the async initialization.
        
        Args:
            sse_endpoint: HTTP(S) endpoint that streams SSE events
            tool_names: List of specific tool names to use from the MCP server
        
        Returns:
            Fully initialized McpProvider instance
        """
        with get_async_bridge() as bridge:
            return bridge.run(cls.create_async(sse_endpoint, tool_names))

    def __repr__(self) -> str:
        tool_names_str = ", ".join(self.tool_names) if self.tool_names else "all"
        return (
            f"McpProvider(sse_endpoint='{self.sse_endpoint}', "
            f"tool_names=[{tool_names_str}], initialized={self._initialized})"
        )
