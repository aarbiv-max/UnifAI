import logging
import asyncio
from typing import List, Optional
from pydantic import HttpUrl
from global_utils.utils.util import run_async
from elements.tools.mcp_proxy.mcp_proxy_tool import McpProxyTool
from elements.providers.mcp_server_client.mcp_server_client import McpServerClient


class McpProvider:
    """
    MCP Provider class that creates and manages MCP proxy tools.
    This replaces the client-server approach by directly providing ready-to-use tools.
    """

    def __init__(self, sse_endpoint: HttpUrl, tool_names: Optional[List[str]] = None):
        """
        Initialize the MCP Provider with SSE endpoint and tool names.
        Note: Use create_async() or create_sync() factory methods for full initialization.
        
        Args:
            sse_endpoint: HTTP(S) endpoint that streams SSE events
            tool_names: List of specific tool names to use from the MCP server
        """
        self.sse_endpoint = sse_endpoint
        self.tool_names = tool_names or []
        self._mcp_client = McpServerClient(sse_endpoint=sse_endpoint)
        self._tools: List[McpProxyTool] = []
        self._initialized = False

    async def _initialize_tools(self) -> None:
        """
        Initialize MCP proxy tools for each specified tool name.
        This is the only async method in the class.
        """
        if self._initialized:
            return

        # If no specific tool names provided, get all available tools
        if not self.tool_names:
            async with self._mcp_client:
                available_tools = await self._mcp_client.get_tools()
                self.tool_names = [tool.name for tool in available_tools]

        # Create MCP proxy tools for each tool name concurrently
        tasks = []
        for tool_name in self.tool_names:
            tasks.append(self._create_and_init_tool(tool_name))
        
        # Initialize all tools concurrently for better performance
        self._tools = await asyncio.gather(*tasks)
        self._initialized = True

    async def _create_and_init_tool(self, tool_name: str) -> McpProxyTool:
        """Create and initialize a single tool using the factory method."""
        return await McpProxyTool.create_async(tool_name, self._mcp_client)

    def get_tools(self) -> List[McpProxyTool]:
        """
        Get all MCP proxy tools.
        
        Returns:
            List of McpProxyTool instances
        """
        # Ensure tools are initialized before returning
        if not self._initialized:
            run_async(self._initialize_tools())
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[McpProxyTool]:
        """
        Get a specific tool by name.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            McpProxyTool instance if found, None otherwise
        """
        # Ensure tools are initialized before searching
        if not self._initialized:
            run_async(self._initialize_tools())
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
        run_async(self._initialize_tools())

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

    def __str__(self) -> str:
        return f"McpProvider(endpoint='{self.sse_endpoint}', tools={len(self._tools)})"

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
        Uses run_async internally to handle the async initialization.
        
        Args:
            sse_endpoint: HTTP(S) endpoint that streams SSE events
            tool_names: List of specific tool names to use from the MCP server
            
        Returns:
            Fully initialized McpProvider instance
        """
        return run_async(cls.create_async(sse_endpoint, tool_names))

    def __repr__(self) -> str:
        tool_names_str = ", ".join(self.tool_names) if self.tool_names else "all"
        return (
            f"McpProvider(sse_endpoint='{self.sse_endpoint}', "
            f"tool_names=[{tool_names_str}], initialized={self._initialized})"
        )
