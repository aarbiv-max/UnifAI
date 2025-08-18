from abc import ABC, abstractmethod
from graph.step_context import StepContext
from graph.state.graph_state import GraphState
from graph.state.state_view import StateView
from core.types import StreamWriter
from typing import Optional, Any, Mapping, ClassVar
from core.contracts import SupportsStreaming


class BaseNode(SupportsStreaming, ABC):
    """
    • Stores StepContext / uid
    • Provides __call__ with streaming
    • NO domain-specific logic
    """
    READS: ClassVar[set[str]] = set()
    WRITES: ClassVar[set[str]] = set()

    def __init__(self, *, retries: int = 1, **kwargs: Any):
        super().__init__(**kwargs)  # MRO
        self.retries = retries
        self._ctx: Optional[StepContext] = None
        self._stream_writer: Optional[StreamWriter] = None
        self._is_streaming = False

    @abstractmethod
    def run(self, state: StateView) -> StateView:
        ...

    def __call__(self,
                 state: GraphState,
                 config,
                 writer: StreamWriter = None) -> GraphState:
        self._stream_writer = writer
        self._is_streaming = config.get("metadata", {}).get("streaming", False)

        wrapped_state = StateView(state, reads=self.read_channels(), writes=self.write_channels())
        self.run(wrapped_state)
        result = wrapped_state.backing_state

        self._stream({"type": "complete",
                      "state": result})

        return result

    def _base_stream_data(self) -> dict[str, Any]:
        """Core metadata every chunk must carry."""
        return {
            "node": self.uid,
            "display_name": self.display_name,
        }

    def _stream(self, payload: Mapping[str, Any]) -> None:
        """
        Forward a payload to the writer, enriching it with node metadata.

        • Does nothing if no writer is attached
        • Caller’s keys override ours in case of conflict
        • Leaves the original `payload` untouched
        """
        if not self.is_streaming():
            return

        enriched: dict[str, Any] = {**self._base_stream_data(), **payload}
        self._stream_writer(enriched)

    def is_streaming(self) -> bool:
        """
        Check if the node is streaming.
        """
        return self._is_streaming

    def set_context(self, step_ctx: StepContext) -> None:
        """
        Set the step context for this node.
        """
        self._ctx = step_ctx

    @classmethod
    def read_channels(cls) -> set[str]:
        return cls.READS

    @classmethod
    def write_channels(cls) -> set[str]:
        return cls.WRITES

    @property
    def uid(self) -> str:
        return self._ctx.uid

    @property
    def display_name(self) -> str:
        return self._ctx.metadata.display_name
