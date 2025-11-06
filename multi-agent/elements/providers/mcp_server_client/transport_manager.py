from typing import Optional, Dict
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class McpConnectionError(Exception):
    """Raised when the HTTP connection cannot be established or fails."""


class TransportManager:
    """
    Responsible solely for:
      1) Opening a Streamable HTTP transport (via mcp.client.streamable_http.streamablehttp_client)
      2) Creating a ClientSession over that transport
      3) Disconnecting / cleaning up both the ClientSession and HTTP connection

    Usage patterns:

      # 1) Explicit connect / disconnect:
      transport = TransportManager("http://host:8004/mcp", sampling_callback=my_cb)
      await transport.connect()
      # ... use transport._session (e.g. call tools) ...
      await transport.disconnect()

      # 2) Using context manager:
      transport = TransportManager("http://host:8004/mcp", sampling_callback=my_cb)
      async with transport:
          # Now transport._session is guaranteed to be open
          # ... call tools ...
      # Exiting context → disconnect() automatically called
    """

    def __init__(
        self,
        endpoint: str,
        sampling_callback=None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.endpoint = endpoint
        self.sampling_callback = sampling_callback
        self.headers = headers or {}

        # These are set in connect(), and cleared in disconnect()
        self._transport_context = None  # holds the HTTP transport context from streamablehttp_client()
        self._read_stream = None  # async iterator from streamablehttp_client().__aenter__()
        self._write_stream = None  # writer coroutine from streamablehttp_client().__aenter__()
        self._session: Optional[ClientSession] = None

        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """
        True if both:
          - HTTP transport is open (i.e. _transport_context is alive)
          - ClientSession was created on top of those streams
        """
        return self._is_connected and (self._session is not None)

    async def connect(self) -> None:
        """
        Open the Streamable HTTP transport and start a ClientSession. Idempotent if already connected.
        Raises McpConnectionError on failure.
        """
        if self.is_connected:
            return

        # 1) Tear down any half-open remnants (from previous failed attempts)
        await self._safe_cleanup()

        # 2) Create the Streamable HTTP context
        try:
            # TODO: Replace with proper logging when logging system is implemented
            # print("TransportManager: Opening Streamable HTTP transport to %s", self.endpoint)
            self._transport_context = streamablehttp_client(
                url=self.endpoint,
                headers=self.headers
            )
            # Note: streamablehttp_client returns 3 values (read, write, and additional context)
            self._read_stream, self._write_stream, _ = await self._transport_context.__aenter__()
        except Exception as e:
            self._transport_context = None
            raise McpConnectionError(f"HTTP transport failed: {e}") from e

        # 3) Build and initialize the ClientSession over that transport
        try:
            self._session = ClientSession(
                self._read_stream,
                self._write_stream,
                sampling_callback=self.sampling_callback
            )
            await self._session.__aenter__()
            await self._session.initialize()
        except Exception as e:
            # Tear down HTTP transport if session initialization fails
            try:
                await self._transport_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._transport_context = None
            self._session = None
            raise McpConnectionError(f"ClientSession initialization failed: {e}") from e

        self._is_connected = True
        # TODO: Replace with proper logging when logging system is implemented
        # print("TransportManager: connected successfully to %s", self.endpoint)

    async def disconnect(self) -> None:
        """
        Cleanly close the ClientSession and then the HTTP transport.
        If not connected, this is a no-op.
        """
        if not self.is_connected:
            return

        # Immediately mark disconnected to prevent re-entry races
        self._is_connected = False

        # 1) Close ClientSession if it exists
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except RuntimeError as e:
                # AnyIO's HTTP session may raise "cancel scope" if closed from a different task
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: RuntimeError HTTP close error: %s", e)
                pass
            except GeneratorExit:
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: Ignored ClientSession GeneratorExit during close")
                pass
            except Exception as e:
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: Unexpected error closing ClientSession: %s", e)
                pass
            finally:
                self._session = None

        # 2) Close HTTP transport context if it exists
        if self._transport_context:
            try:
                await self._transport_context.__aexit__(None, None, None)
            except RuntimeError as e:
                # Catch exactly AnyIO's "cancel scope" error from exiting in wrong task
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: RuntimeError HTTP close error: %s", e)
                pass
            except GeneratorExit:
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: Ignored HTTP GeneratorExit during close")
                pass
            except Exception as e:
                # TODO: Replace with proper logging when logging system is implemented
                # print("TransportManager: HTTP close raised: %s", e)
                pass
            finally:
                self._transport_context = None
                self._read_stream = None
                self._write_stream = None

        # TODO: Replace with proper logging when logging system is implemented
        # print("TransportManager: disconnected from %s", self.endpoint)

    async def _safe_cleanup(self) -> None:
        """
        If a previous session or transport is still open, tear it down quietly.
        Used at the start of connect() to avoid leaving half-open resources.
        """
        # 1) If a ClientSession is still alive, close it
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None

        # 2) If the HTTP transport context is still open, close it
        if self._transport_context:
            try:
                await self._transport_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._transport_context = None
            self._read_stream = None
            self._write_stream = None

    # Allow `async with transport:` to connect() / disconnect() automatically
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()
