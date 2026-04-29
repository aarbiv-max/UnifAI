"""
Streaming capability mixin for nodes.
Provides streaming functionality via SessionChannel abstraction.
"""
from typing import Any, Mapping, Optional
from mas.core.channels import SessionChannel, CancellationToken, SessionCancelledException


class StreamingCapableMixin:
    """
    Mixin that provides streaming capability to nodes.
    
    Provides:
        - set_streaming_channel(channel): Inject channel before execution
        - set_cancellation_token(token): Inject cancellation token
        - _stream(payload): Emit enriched data (checks cancellation first)
        - is_streaming(): Check if streaming is active
    
    Usage:
        class MyNode(StreamingCapableMixin, BaseNode):
            def run(self, state):
                self._stream({"type": "progress", "value": 50})
                ...
    """
    
    _streaming_channel: Optional[SessionChannel] = None
    _cancellation_token: Optional[CancellationToken] = None
    
    def set_streaming_channel(self, channel: Optional[SessionChannel]) -> None:
        """Inject the streaming channel before execution."""
        self._streaming_channel = channel

    def set_cancellation_token(self, token: Optional[CancellationToken]) -> None:
        """Inject the cancellation token before execution."""
        self._cancellation_token = token

    def _check_cancelled(self) -> None:
        """Check cancellation token and raise if session was cancelled."""
        if self._cancellation_token and self._cancellation_token.is_cancelled():
            session_id = (
                self._streaming_channel.session_id
                if self._streaming_channel
                else "unknown"
            )
            raise SessionCancelledException(session_id)
    
    def _stream(self, payload: Mapping[str, Any]) -> None:
        """
        Emit data to the streaming channel.
        Enriches payload with node metadata if _base_stream_data() is available.
        """
        self._check_cancelled()

        if self._streaming_channel is None:
            return
        if not self._streaming_channel.is_active():
            return
        
        # Enrich with node metadata if available
        enriched: dict[str, Any] = dict(payload)
        if hasattr(self, '_base_stream_data'):
            enriched = {**self._base_stream_data(), **payload}
        
        self._streaming_channel.emit(enriched)
    
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        return (
            self._streaming_channel is not None 
            and self._streaming_channel.is_active()
        )
