from typing import Optional, Type, Any, Dict
from pydantic import BaseModel
from global_utils.utils.util import run_async, validate_arguments
from providers.mcp.mcp_server_client import McpServerClient
from .base_tool import BaseTool


class McpProxyToolError(Exception):
    """Exception for MCP proxy tool errors"""
    pass


class McpProxyTool(BaseTool):
    """
    A proxy tool that forwards calls to MCP server tools through a shared McpServerClient.
    Each `async with self.mcp_client:` block increments an internal reference count,
    ensuring that parallel calls do not disconnect each other prematurely.
    """

    def __init__(
            self,
            mcp_tool_name: str,
            mcp_client: McpServerClient,
            custom_name: Optional[str] = None,
            custom_description: Optional[str] = None
    ):
        self.mcp_tool_name = mcp_tool_name
        self.mcp_client = mcp_client
        self._tool_info = None
        self._schema_initialized = False

        # Call BaseTool.__init__ with placeholder schema; we’ll overwrite once real info arrives.
        super().__init__(
            name=custom_name or mcp_tool_name,
            description=custom_description or f"MCP proxy for {mcp_tool_name}",
            args_schema=None
        )

        # Fire off a one-time background task to fetch metadata
        run_async(self._ensure_tool_info())

    async def _ensure_tool_info(self) -> None:
        """
        Fetch the tool’s metadata (description + inputSchema) exactly once.
        We use the shared client, but wrap it in `async with` so that
        connect()/disconnect() are governed by the internal refcount.
        """
        if self._tool_info is not None:
            return

        # Enter the shared client’s context (refcount goes from 0→1, so a real connect() happens).
        async with self.mcp_client:
            tool_info = await self.mcp_client.get_tool_by_name(self.mcp_tool_name)

        if not tool_info:
            # If the tool isn’t found, list all available tools for error context
            async with self.mcp_client:
                available = await self.mcp_client.get_tools()
            raise McpProxyToolError(
                f"MCP tool '{self.mcp_tool_name}' not found. Available tools: {available}"
            )

        # Cache the fetched metadata
        self._tool_info = tool_info
        self.description = tool_info.description
        self.args_schema = tool_info.inputSchema
        self._schema_initialized = True

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Synchronous wrapper—only for use when no event loop is running.
        Otherwise, call `await arun(...)` directly.
        """
        try:
            return run_async(self.arun(*args, **kwargs))
        except Exception as e:
            raise McpProxyToolError(
                f"Synchronous execution failed for '{self.mcp_tool_name}': {e}"
            )

    async def arun(self, *args: Any, **kwargs: Any) -> Any:
        """
        Asynchronous entry point. Steps:
          1) Ensure schema is loaded (only once).
          2) Validate + prepare arguments via Pydantic model.
          3) Enter the shared client context (increments refcount; calls actual connect() only if refcount was 0).
          4) call call_tool(...)
          5) Exit the context (decrements refcount; calls actual disconnect() only when it reaches 0).
          6) Return the extracted result.
        """
        # 1) Fetch schema once if not already
        if not self._schema_initialized:
            await self._ensure_tool_info()

        # 2) Validate + prune arguments
        mcp_args = self._prepare_arguments(kwargs)

        # 3) Use the shared client for exactly one call. Parallel calls will share the same connection.
        async with self.mcp_client:
            try:
                result = await self.mcp_client.call_tool(self.mcp_tool_name, mcp_args)
            except Exception as e:
                raise McpProxyToolError(f"Failed to call '{self.mcp_tool_name}': {e}")

        # 4) Return the most relevant piece of the result
        return self._extract_result_content(result)

    def _prepare_arguments(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate args against JSON schema.
        """
        if not kwargs or not self.args_schema:
            return kwargs or {}

        validate_arguments(schema=self.get_args_schema_json(), args=kwargs)
        return kwargs

    def _extract_result_content(self, result) -> Any:
        """
        Take whatever `CallToolResult` returned and pick out the most relevant piece.
        Typically MCP returns a `.content` list of TextContent or DataContent objects.
        """
        try:
            if hasattr(result, "content") and result.content:
                if isinstance(result.content, list) and len(result.content) > 0:
                    first = result.content[0]
                    if hasattr(first, "text"):
                        return first.text
                    if hasattr(first, "data"):
                        return first.data
                    return str(first)
                return str(result.content)
            return str(result)
        except Exception:
            return str(result)

    def get_args_schema_json(self) -> Dict[str, Any]:
        """
        Return the raw JSON schema that MCP provided for this tool.
        """
        return self.args_schema

    def get_args_schema_model(self) -> Optional[Type[BaseModel]]:
        """
        Dynamically build a Pydantic model from the MCP JSON schema
        so we can perform argument validation in Python.
        """
        if not self.args_schema:
            return None
        return json_schema_model(self.args_schema, self.name)

    async def refresh_schema(self) -> None:
        """
        Discard the cached schema & description, then re‐fetch them from MCP.
        """
        self._tool_info = None
        self._schema_initialized = False
        self.args_schema = None
        await self._ensure_tool_info()

    async def health_check(self) -> bool:
        """
        Quickly verify that:
          1) a new context enter reconnects if needed
          2) the remote tool still exists
        """
        try:
            async with self.mcp_client:
                info = await self.mcp_client.get_tool_by_name(self.mcp_tool_name)
            return info is not None
        except Exception:
            return False

    def __str__(self) -> str:
        return f"McpProxyTool(name='{self.name}', mcp_tool='{self.mcp_tool_name}')"

    def __repr__(self) -> str:
        desc = (self.description[:50] + "...") if self.description else "No description"
        return (
            f"McpProxyTool(name='{self.name}', mcp_tool_name='{self.mcp_tool_name}', "
            f"description='{desc}', connected={self.mcp_client.is_connected})"
        )
