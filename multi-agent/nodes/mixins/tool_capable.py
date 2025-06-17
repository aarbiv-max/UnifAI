import asyncio
from typing import (
    Any, Dict, List, Optional,
    Callable, TypeVar, Generic
)
from core.contracts import SupportsStreaming
from llms.chat.message import ChatMessage, ToolCall, Role
from tools.base_tool import BaseTool
from global_utils.utils.util import run_async, validate_arguments

T = TypeVar("T", bound=SupportsStreaming)


class ToolCapableMixin(Generic[T]):
    """
    Mixin for tool-equipped agents.

    Responsibilities:
      1. Enforce streaming protocol (_stream + is_streaming).
      2. Register tools into a name→instance map.
      3. Extract ToolCall objects from assistant messages.
      4. Invoke each tool (async or sync) and wrap results as ChatMessage(role=TOOL).
      5. Stream each tool result via self._stream().
      6. Provide invoke_tools() for ad-hoc use.
      7. Provide _execute_tool_cycle() which:
         - Runs chat→invoke_tools→feed back for up to max_rounds.
         - Streams lifecycle events: cycle_start, assistant_complete, tool_result, cycle_end.
         - Returns the final ChatMessage from the assistant.
    """

    def __init_subclass__(cls) -> None:
        # DIP: ensure host implements SupportsStreaming
        if not issubclass(cls, SupportsStreaming):
            raise TypeError(
                f"{cls.__name__} requires streaming support (_stream + is_streaming)."
            )
        super().__init_subclass__()

    def __init__(self, *, tools: List[BaseTool], **kwargs: Any):
        """
        :param tools: List of BaseTool instances for this agent.
        """
        super().__init__(**kwargs)
        # SRP: only one job—manage the tool registry
        self._tools: Dict[str, BaseTool] = {tool.name: tool for tool in tools}

    @property
    def tools(self) -> List[BaseTool]:
        """Expose tools as a simple list."""
        return list(self._tools.values())

    def _extract_tool_calls(self, msg: ChatMessage) -> List[ToolCall]:
        return msg.tool_calls or []

    async def _ainvoke_tool(self: T, tc: ToolCall) -> ChatMessage:
        """Async-invoke a single tool and stream its result if active."""
        tool = self._tools.get(tc.name)
        if not tool:
            raise ValueError(f"No tool registered under name '{tc.name}'")

        if self.is_streaming():
            self._stream({
                "type": "tool_calling",
                "tool": tc.name,
                "call_id": tc.tool_call_id,
                "args": tc.args
            })

        # Validate & coerce arguments if schema is attached
        args = tc.args

        if getattr(tool, "args_schema", None):
            validate_arguments(schema=tool.get_args_schema_json(), args=args)

        # Invoke—prefer async interface if available
        if asyncio.iscoroutinefunction(tool.arun):
            result = await tool.arun(**args)
        else:
            result = await asyncio.to_thread(tool.run, **args)

        # Stream raw tool output chunk
        if self.is_streaming():
            self._stream({
                "type": "tool_result",
                "tool": tc.name,
                "call_id": tc.tool_call_id,
                "output": result
            })

        return ChatMessage(
            role=Role.TOOL,
            content=str(result),
            tool_call_id=tc.tool_call_id
        )

    async def _ainvoke_all(self, msg: ChatMessage):
        """Invoke all ToolCalls in parallel."""
        calls = self._extract_tool_calls(msg)
        tasks = [self._ainvoke_tool(tc) for tc in calls]
        return await asyncio.gather(*tasks)

    def invoke_tools(self, msg: ChatMessage) -> List[ChatMessage]:
        """
        Sync entrypoint: returns a list of ChatMessages(role=TOOL) for any tool calls.
        """
        if msg.role != Role.ASSISTANT or not msg.tool_calls:
            return []
        return run_async(self._ainvoke_all(msg))

    def _execute_tool_cycle(
            self: T,
            initial_history: List[ChatMessage],
            chat_function: Callable[[List[ChatMessage]], ChatMessage],
            max_rounds: int = 20
    ) -> ChatMessage:
        """
        Runs the “LLM → tool invokes → feed back → repeat” loop up to max_rounds.

        :param initial_history: starting list of ChatMessages
        :param chat_function:   a method like self._chat
        :param max_rounds:      how many iterations to allow
        :returns: the final assistant ChatMessage
        """
        history = initial_history.copy()
        assistant: Optional[ChatMessage] = None

        # Stream cycle start
        if self.is_streaming():
            self._stream({"type": "tool_cycle_start"})

        for _ in range(max_rounds):
            # Ask the LLM (streams internally if enabled)
            assistant = chat_function(history)
            history.append(assistant)

            # Invoke any requested tools
            tool_msgs = self.invoke_tools(assistant)
            if not tool_msgs:
                break

            history.extend(tool_msgs)

        if assistant is None:
            raise RuntimeError("LLM did not produce any response within the tool cycle.")

        return assistant
