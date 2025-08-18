from typing import Optional
from mcp import ClientSession
from mcp.client.sse import sse_client


class McpConnectionError(Exception):
    """Raised when the SSE connection cannot be established or fails."""


class TransportManager:
    """
    Responsible solely for:
      1) Opening an SSE transport (via mcp.client.sse.sse_client)
      2) Creating a ClientSession over that transport
      3) Disconnecting / cleaning up both the ClientSession and SSE generator

    Usage patterns:

      # 1) Explicit connect / disconnect:
      transport = TransportManager("http://host:8004/sse", sampling_callback=my_cb)
      await transport.connect()
      # ... use transport._session (e.g. call tools) ...
      await transport.disconnect()

      # 2) Using context manager:
      transport = TransportManager("http://host:8004/sse", sampling_callback=my_cb)
      async with transport:
          # Now transport._session is guaranteed to be open
          # ... call tools ...
      # Exiting context → disconnect() automatically called
    """

    def __init__(self, sse_endpoint: str, sampling_callback=None):
        self.sse_endpoint = sse_endpoint
        self.sampling_callback = sampling_callback

        # These are set in connect(), and cleared in disconnect()
        self._transport_context = None  # holds the SSE generator context from sse_client()
        self._read_stream = None  # async iterator from sse_client().__aenter__()
        self._write_stream = None  # writer coroutine from sse_client().__aenter__()
        self._session: Optional[ClientSession] = None

        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """
        True if both:
          - SSE transport is open (i.e. _transport_context is alive)
          - ClientSession was created on top of those streams
        """
        return self._is_connected and (self._session is not None)

    async def connect(self) -> None:
        """
        Open the SSE transport and start a ClientSession. Idempotent if already connected.
        Raises McpConnectionError on failure.
        """
        if self.is_connected:
            return

        # 1) Tear down any half-open remnants (from previous failed attempts)
        await self._safe_cleanup()

        # 2) Create the SSE generator context
        try:
            print("TransportManager: Opening SSE transport to %s", self.sse_endpoint)
            self._transport_context = sse_client(url=self.sse_endpoint)
            self._read_stream, self._write_stream = await self._transport_context.__aenter__()
        except Exception as e:
            self._transport_context = None
            raise McpConnectionError(f"SSE transport failed: {e}") from e

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
            # Tear down SSE if session initialization fails
            try:
                await self._transport_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._transport_context = None
            self._session = None
            raise McpConnectionError(f"ClientSession initialization failed: {e}") from e

        self._is_connected = True
        print("TransportManager: connected successfully to %s", self.sse_endpoint)

    async def disconnect(self) -> None:
        """
        Cleanly close the ClientSession and then the SSE transport.
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
                # AnyIO’s SSE session may raise "cancel scope" if closed from a different task
                print("TransportManager: RuntimeError SSE close error: %s", e)
            except GeneratorExit:
                print("TransportManager: Ignored ClientSession GeneratorExit during close")
            except Exception as e:
                print("TransportManager: Unexpected error closing ClientSession: %s", e)
            finally:
                self._session = None

        # 2) Close SSE generator context if it exists
        if self._transport_context:
            try:
                await self._transport_context.__aexit__(None, None, None)
            except RuntimeError as e:
                # Catch exactly AnyIO’s "cancel scope" error from exiting in wrong task
                print("TransportManager: RuntimeError SSE close error: %s", e)
            except GeneratorExit:
                print("TransportManager: Ignored SSE GeneratorExit during close")
            except Exception as e:
                print("TransportManager: SSE close raised: %s", e)
            finally:
                self._transport_context = None
                self._read_stream = None
                self._write_stream = None

        print("TransportManager: disconnected from %s", self.sse_endpoint)

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

        # 2) If the SSE transport context is still open, close it
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
