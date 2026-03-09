"""
Redis-backed session channel for distributed streaming.

Publishes events to Redis Streams for persistent storage and replay capability.
This decouples the streaming from the HTTP request lifecycle, allowing:
  - Session streams to persist even when the client disconnects
  - Clients to reconnect and replay missed events
  - Cross-worker visibility of session events

Thread Safety:
  - Redis operations are atomic and thread-safe
  - The channel can be used from multiple threads safely

Dual-emit Pattern:
  - Events are emitted to BOTH Redis AND an optional StreamEmitter
  - The StreamEmitter (e.g., LangGraphEmitter) enables HTTP streaming
  - Redis enables persistent storage and reconnection
"""
import json
import time
import logging
from typing import Any, Optional, Union
from redis import Redis
from redis.exceptions import RedisError
from core.channels import SessionChannel, StreamEmitter
from .null_client import NullRedis
from .client_factory import RedisClientFactory

logger = logging.getLogger(__name__)

RedisClient = Union[Redis, NullRedis]

# Default configuration values
DEFAULT_STREAM_MAXLEN = 5000
DEFAULT_STREAM_TTL_SECONDS = 3600


class RedisSessionChannel(SessionChannel):
    """
    Session channel backed by Redis Streams with optional HTTP streaming support.
    
    Each session gets its own Redis Stream for event storage, enabling:
      - Persistent event history
      - Replay from any point (by event ID)
      - Automatic cleanup via TTL and maxlen
    
    When an emitter is provided, events are also forwarded to it for HTTP streaming.
    This enables both immediate HTTP streaming AND persistent Redis storage.
    
    Key Schema:
      - session:stream:{session_id}  - Redis Stream for events
      - session:meta:{session_id}    - Hash for session metadata
      - sessions:active              - Set of currently active session IDs
    
    Usage:
      # Preferred: Use factory method with auto-config (includes emitter)
      channel = RedisSessionChannel.create(session_id, redis_client, emitter)
      
      # Alternative: Direct instantiation
      channel = RedisSessionChannel(session_id, redis_client, emitter=emitter)
    """
    
    def __init__(
        self,
        session_id: str,
        redis_client: RedisClient,
        emitter: Optional[StreamEmitter] = None,
        maxlen: int = DEFAULT_STREAM_MAXLEN,
        ttl_seconds: int = DEFAULT_STREAM_TTL_SECONDS
    ):
        self._session_id = session_id
        self._redis = redis_client
        self._emitter = emitter
        self._maxlen = maxlen
        self._ttl_seconds = ttl_seconds
        self._closed = False
        
        # Key names
        self._stream_key = f"session:stream:{session_id}"
        self._meta_key = f"session:meta:{session_id}"
        self._active_set_key = "sessions:active"
        
        # Initialize session in Redis
        self._initialize_session()
    
    @classmethod
    def create(
        cls,
        session_id: str,
        redis_client: RedisClient,
        emitter: Optional[StreamEmitter] = None
    ) -> "RedisSessionChannel":
        """
        Factory method that creates a channel with config from AppConfig.
        
        Args:
            session_id: The session ID
            redis_client: Redis client for stream storage
            emitter: Optional StreamEmitter for HTTP streaming (e.g., LangGraphEmitter)
        
        Reads redis_stream_maxlen and redis_stream_ttl_seconds from config,
        falling back to defaults if not configured.
        """
        from config.app_config import AppConfig
        
        cfg = AppConfig.get_instance()
        maxlen = getattr(cfg, 'redis_stream_maxlen', DEFAULT_STREAM_MAXLEN)
        ttl_seconds = getattr(cfg, 'redis_stream_ttl_seconds', DEFAULT_STREAM_TTL_SECONDS)
        
        return cls(
            session_id=session_id,
            redis_client=redis_client,
            emitter=emitter,
            maxlen=maxlen,
            ttl_seconds=ttl_seconds
        )
    
    def _initialize_session(self) -> None:
        """Register session as active and set initial metadata."""
        try:
            pipeline = self._redis.pipeline()
            pipeline.sadd(self._active_set_key, self._session_id)
            pipeline.hset(self._meta_key, mapping={
                "status": "running",
                "started_at": str(time.time()),
                "session_id": self._session_id
            })
            pipeline.execute()
            logger.debug(f"Initialized Redis session channel: {self._session_id}")
        except RedisError as e:
            logger.error(f"Failed to initialize session {self._session_id}: {e}")
            raise
    
    @property
    def session_id(self) -> str:
        return self._session_id
    
    def emit(self, data: Any) -> None:
        """
        Emit an event to both Redis Stream and the optional HTTP emitter.
        
        Dual-emit ensures:
          1. HTTP streaming works (via emitter) for immediate client feedback
          2. Redis stores events for reconnection/replay
        
        Events are stored with automatic ordering (Redis-generated IDs)
        and the stream is capped to maxlen entries.
        """
        if self._closed:
            return
        
        # Forward to emitter for HTTP streaming (if available and active)
        if self._emitter and self._emitter.is_active():
            self._emitter.emit(data)
        
        # Store in Redis for persistence/replay
        try:
            event_json = json.dumps(data, default=str)
            self._redis.xadd(
                self._stream_key,
                {"event": event_json, "timestamp": str(time.time())},
                maxlen=self._maxlen,
                approximate=True
            )
        except RedisError as e:
            logger.error(f"Failed to emit event for session {self._session_id}: {e}")
    
    def is_active(self) -> bool:
        """Check if the channel is still active (not closed)."""
        return not self._closed
    
    def close(self) -> None:
        """
        Close the channel and mark the session as completed.
        
        Sets TTL on stream/metadata for automatic cleanup.
        Emits a final 'stream_end' event for subscribers.
        """
        if self._closed:
            return
        
        self._closed = True
        
        try:
            # Emit end signal
            end_event = json.dumps({"type": "stream_end", "timestamp": time.time()})
            self._redis.xadd(
                self._stream_key,
                {"event": end_event, "timestamp": str(time.time())},
                maxlen=self._maxlen,
                approximate=True
            )
            
            # Update metadata and set TTL
            pipeline = self._redis.pipeline()
            pipeline.hset(self._meta_key, mapping={
                "status": "completed",
                "completed_at": str(time.time())
            })
            pipeline.srem(self._active_set_key, self._session_id)
            pipeline.expire(self._stream_key, self._ttl_seconds)
            pipeline.expire(self._meta_key, self._ttl_seconds)
            pipeline.execute()
            
            logger.debug(f"Closed Redis session channel: {self._session_id}")
        except RedisError as e:
            logger.error(f"Failed to close session {self._session_id}: {e}")
    
    def mark_failed(self, error: Optional[str] = None) -> None:
        """Mark the session as failed with optional error message."""
        self._closed = True
        
        try:
            # Emit error event
            error_event = json.dumps({
                "type": "stream_error",
                "error": error or "Unknown error",
                "timestamp": time.time()
            })
            self._redis.xadd(
                self._stream_key,
                {"event": error_event, "timestamp": str(time.time())},
                maxlen=self._maxlen,
                approximate=True
            )
            
            # Update metadata
            pipeline = self._redis.pipeline()
            pipeline.hset(self._meta_key, mapping={
                "status": "failed",
                "failed_at": str(time.time()),
                "error": error or "Unknown error"
            })
            pipeline.srem(self._active_set_key, self._session_id)
            pipeline.expire(self._stream_key, self._ttl_seconds)
            pipeline.expire(self._meta_key, self._ttl_seconds)
            pipeline.execute()
        except RedisError as e:
            logger.error(f"Failed to mark session {self._session_id} as failed: {e}")
    
    def supports_input(self) -> bool:
        """Redis channel supports future HITL capabilities."""
        return True
    
    @staticmethod
    def is_redis_available(redis_client: RedisClient) -> bool:
        """
        Check if a Redis client is available and connected.
        
        Delegates to RedisClientFactory for consistency.
        """
        return RedisClientFactory.is_available(redis_client)
