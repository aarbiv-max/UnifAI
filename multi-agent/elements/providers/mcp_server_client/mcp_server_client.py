import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import HttpUrl
from yarl import URL
from mcp.types import Tool, CallToolResult, CreateMessageRequestParams, CreateMessageResult, TextContent
import anyio

from .transport_manager import TransportManager, McpConnectionError
from .tool_registry import ToolRegistry, McpToolError

logger = logging.getLogger(__name__)


class McpProxyToolError(Exception):
    """Any error that occurs while proxying to an MCP tool."""
    pass


class McpServerClient:
    """
    A high‐level façade that ties together:
      - TransportManager (open/close SSE + ClientSession)
      - HealthChecker   (ping logic + automatic reconnect)
      - ToolRegistry    (list/get/call tools + minimal JSON‐schema validation)

    Now with internal locking and reference counting so that multiple
    `async with same_client:` blocks can share one SSE connection.
    """

    def __init__(
            self,
            sse_endpoint: HttpUrl,
    ):
        base = URL(str(sse_endpoint))
        self.sse_endpoint = str(base if base.path.endswith("/sse") else base / "sse")

        # TransportManager handles the low‐level SSE + ClientSession.
        self.transport = TransportManager(
            self.sse_endpoint,
            sampling_callback=self._default_sampling_callback
        )

        # ToolRegistry covers list/get/call operations, using the same transport & health.
        self.tools = ToolRegistry(
            transport=self.transport
        )
        # ─── New fields for reference counting & locking ───
        # How many active “users” currently inside an async‐with block
        self._refcount = 0
        # Ensure that connect/disconnect and refcount adjustments are atomic
        # Using anyio.Lock for cross-loop compatibility
        self._lock = anyio.Lock()

    async def _default_sampling_callback(
            self, message: CreateMessageRequestParams
    ) -> CreateMessageResult:
        """
        Default fallback if MCP server ever requests a sampling callback.
        """
        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="Default response"),
            model="unknown",
            stopReason="endTurn"
        )

    @property
    def is_connected(self) -> bool:
        """Shortcut to transport.is_connected."""
        return self.transport.is_connected

    async def connect(self) -> None:
        """
        Explicitly open the transport & session. Normally you only need
        to do this if you plan to call get_tools() or call_tool() immediately—
        but each of those methods will auto‐connect via health.ensure_connected().
        """
        try:
            await self.transport.connect()
        except McpConnectionError as e:
            raise McpConnectionError(f"McpServerClient.connect() failed: {e}")

    async def disconnect(self) -> None:
        """
        Explicitly disconnect the transport & session. Typically called only when
        the last “user” exits. Use caution—if you call this manually while others
        still expect the connection, they may be disrupted.
        """
        await self.transport.disconnect()

    async def get_tools(self, refresh: bool = False) -> List[Tool]:
        """
        Return a list of all available tools (possibly cached). If `refresh=True`,
        forces a fresh fetch from the server.
        """
        try:
            return await self.tools.get_tools(refresh=refresh)
        except McpToolError as e:
            raise McpToolError(f"McpServerClient.get_tools() failed: {e}")

    async def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """
        Return the Tool object for a given name, or None if not found.
        """
        try:
            return await self.tools.get_tool_by_name(name)
        except McpToolError as e:
            raise McpToolError(f"McpServerClient.get_tool_by_name() failed: {e}")

    async def call_tool(
            self,
            tool_name: str,
            arguments: Dict[str, Any]
    ) -> CallToolResult:
        """
        Proxy a call to the MCP server:
          1) Ensure connected & healthy
          2) Validate `required` fields
          3) Invoke session.call_tool(...)
          4) Return the raw CallToolResult
        Raises McpToolError if something goes wrong.
        """
        try:
            return await self.tools.call_tool(tool_name, arguments)
        except McpToolError as e:
            raise McpToolError(f"McpServerClient.call_tool('{tool_name}') failed: {e}")

    async def __aenter__(self):
        """
        When entering `async with client:`, we:
          1) Acquire the lock
          2) If this is the very first entry (refcount == 0), actually connect
          3) Increment refcount
          4) Release the lock
        """
        async with self._lock:
            if self._refcount == 0:
                # Nobody’s connected yet → open the SSE + session
                await self.transport.connect()
            self._refcount += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        When exiting an `async with client:` block, we:
          1) Acquire the lock
          2) Decrement refcount
          3) If refcount has dropped to 0, disconnect
          4) Release the lock
        """
        async with self._lock:
            self._refcount -= 1
            # Only the last exiting context actually tears down the connection
            if self._refcount == 0:
                await self.transport.disconnect()

    def clone(self) -> "McpServerClient":
        """
        Create a new McpServerClient with the same configuration *and*
        copy over any already‐fetched tool list (so clones start “warm”).
        """
        new_client = McpServerClient(
            sse_endpoint=self.sse_endpoint
        )

        # Copy over the ToolRegistry cache, if any:
        try:
            new_client.tools._tools_cache = (
                list(self.tools._tools_cache)
                if self.tools._tools_cache is not None
                else None
            )
        except AttributeError:
            # If `_tools_cache` doesn’t exist or is None, ignore.
            pass

        return new_client
