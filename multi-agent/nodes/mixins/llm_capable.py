from llms.chat.message import ChatMessage, Role
from typing import Any, TypeVar, Generic, List
from core.contracts import SupportsStreaming
from llms.base_llm import BaseLLM
from tools.base_tool import BaseTool

# -----------------------------------------------------------------------------
# Type variable bound to the minimal "SupportsStreaming" Protocol.
# TSupportStream represents any class that implements the streaming interface:
#  - |_stream(payload: Mapping[str, Any]) -> None
#  - |is_streaming() -> bool
# This ensures static type checkers know `self` has streaming capability.
# -----------------------------------------------------------------------------
TSupportStream = TypeVar("TSupportStream", bound=SupportsStreaming)


class LlmCapableMixin(Generic[TSupportStream]):
    """
    Mixin: Adds LLM-chat capability that leverages existing streaming support.

    Generic[TSupportStream]:
        - Declares that `self` must implement the SupportsStreaming protocol.
        - Enables static analyzers to recognize ._stream() and .is_streaming().

    Responsibilities:
      1. Enforce at subclass-definition that the host class implements streaming.
      2. Initialize LLM-related attributes (`llm`, `system_message`, `retries`).
      3. Provide `_chat()` which:
         - Uses `is_streaming()` / `_stream()` if streaming is available.
         - Falls back to synchronous `llm.chat()` otherwise.

    Requirements on `self` (from SupportsStreaming Protocol):
      - `is_streaming() -> bool`
      - `_stream(payload: Mapping[str, Any]) -> None`
    """

    def __init_subclass__(cls) -> None:
        """
        At subclass definition time, ensure the concrete class implements
        the streaming protocol so that `_chat()` can safely call
        `self._stream()` and `self.is_streaming()`.
        """
        if not issubclass(cls, SupportsStreaming):
            raise TypeError(
                f"{cls.__name__} requires streaming support (_stream + is_streaming)."
            )
        super().__init_subclass__()

    def __init__(
            self,
            *,
            llm: BaseLLM,
            system_message: str = "",
            retries: int = 1,
            **kwargs: Any,
    ):
        """
        Initialize the LLM mixin.

        :param llm:            Object providing `.stream()` and `.chat()`.
        :param system_message: Optional system prompt for the LLM.
        :param retries:        Minimum number of retries for LLM calls.
        """
        super().__init__(**kwargs)  # cooperative MRO
        self.llm = llm
        self.system_message = system_message
        self.retries = max(1, retries)

    def _llm_stream(
            self: TSupportStream,
            messages: list[ChatMessage],
            *,
            event_type: str = "llm_token",
    ) -> ChatMessage:
        """
        Consume `BaseLLM.stream()` which yields either:
            • str  – incremental token
            • ChatMessage – ONE final assistant message (may include tool_calls)

        Behaviour
        ---------
        • Forward each token via `self._stream(...)` when streaming is enabled.
        • Upon receiving ChatMessage:
            ↳ emit an optional “msg_complete” event then *return* it.
        • If no ChatMessage occurs, return a ChatMessage built from tokens.
        """
        accumulated_text = ""
        assistant_msg: ChatMessage | None = None

        for chunk in self.llm.stream(messages):
            # ---------- Token path ----------------------------------------
            if isinstance(chunk, str):
                accumulated_text += chunk
                if self.is_streaming():
                    self._stream({"type": event_type, "chunk": chunk})
                continue

            # ---------- Aggregated assistant (tool call) ------------------
            if isinstance(chunk, ChatMessage):
                assistant_msg = chunk
                break
            else:
                # Unexpected object -> surface immediately
                raise TypeError(
                    f"BaseLLM.stream returned unsupported chunk type: {type(chunk)}"
                )

        # ---------- Return value to caller -------------------------------
        if assistant_msg:
            return assistant_msg  # tool_call reply

        # Plain-text reply case
        return ChatMessage(role=Role.ASSISTANT, content=accumulated_text)

    def _llm_sync_chat(self, messages: list[ChatMessage]) -> ChatMessage:
        """ Synchronous chat with the LLM for a list of ChatMessage."""
        return self.llm.chat(messages)

    def _chat(
            self: TSupportStream,
            messages: list[ChatMessage]) -> ChatMessage:
        """
        Send a list of ChatMessage to the LLM.

        - If streaming is active, forward each chunk via `self._stream()`.
        - Otherwise, return the full response from `llm.chat()`.

        :param messages:   List of ChatMessage (role + content).
        :param event_type: Identifier for streaming events.
        :returns:          The complete generated response.
        """
        if self.is_streaming():
            return self._llm_stream(messages)
        return self._llm_sync_chat(messages)

    def _bind_tools(self, tools: List[BaseTool]) -> None:
        self.llm.bind_tools(tools)
