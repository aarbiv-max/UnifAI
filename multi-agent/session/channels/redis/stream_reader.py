"""
Redis Stream reader for session event subscription.

Provides utilities for reading from Redis session streams,
including historical replay and real-time blocking reads.
Used by API endpoints to enable GUI reconnection.
"""
import json
import logging
from typing import Any, Optional, Dict, List, Tuple, Union
from redis import Redis
from redis.exceptions import RedisError
from .null_client import NullRedis

logger = logging.getLogger(__name__)

RedisClient = Union[Redis, NullRedis]


class RedisStreamReader:
    """
    Utility class for reading from Redis session streams.
    
    Used by API endpoints to subscribe to session events.
    Provides both historical replay and real-time blocking reads.
    """
    
    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
    
    def is_available(self) -> bool:
        """
        Check if Redis is available and functional.
        
        Returns:
            True if Redis client is connected and responding to commands.
        """
        if self._redis is None:
            return False
        
        if isinstance(self._redis, NullRedis):
            return False
        
        if hasattr(self._redis, 'is_connected'):
            return self._redis.is_connected()
        
        try:
            return self._redis.ping()
        except RedisError:
            return False
    
    def get_stream_key(self, session_id: str) -> str:
        return f"session:stream:{session_id}"
    
    def get_meta_key(self, session_id: str) -> str:
        return f"session:meta:{session_id}"
    
    def read_history(
        self,
        session_id: str,
        from_id: str = "0",
        count: Optional[int] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Read historical events from a session stream.
        
        Args:
            session_id: The session to read from
            from_id: Start reading after this event ID ("0" for beginning)
            count: Maximum number of events to return (None for all)
            
        Returns:
            List of (event_id, event_data) tuples
        """
        stream_key = self.get_stream_key(session_id)
        
        # Use exclusive range if from_id is not "0"
        min_id = f"({from_id}" if from_id != "0" else "-"
        
        try:
            if count:
                events = self._redis.xrange(stream_key, min=min_id, max="+", count=count)
            else:
                events = self._redis.xrange(stream_key, min=min_id, max="+")
            
            if not events:
                return []
            
            return [
                (event_id, json.loads(data.get("event", "{}")))
                for event_id, data in events
            ]
        except RedisError as e:
            logger.error(f"Failed to read history for session {session_id}: {e}")
            return []
    
    def read_blocking(
        self,
        session_id: str,
        last_id: str = "$",
        block_ms: int = 15000
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Block and wait for new events.
        
        Args:
            session_id: The session to read from
            last_id: Read events after this ID ("$" for only new events)
            block_ms: How long to block waiting for events (milliseconds)
            
        Returns:
            List of (event_id, event_data) tuples, empty list on timeout
        """
        stream_key = self.get_stream_key(session_id)
        
        try:
            results = self._redis.xread(
                streams={stream_key: last_id},
                block=block_ms
            )
            
            if not results:
                return []
            
            events = []
            for stream_name, stream_events in results:
                for event_id, data in stream_events:
                    events.append((
                        event_id,
                        json.loads(data.get("event", "{}"))
                    ))
            
            return events
        except RedisError as e:
            logger.error(f"Failed to read blocking for session {session_id}: {e}")
            return []
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata and stream info.
        
        Returns:
            Dict with status, event count, last event ID, etc.
            None if session doesn't exist
        """
        stream_key = self.get_stream_key(session_id)
        meta_key = self.get_meta_key(session_id)
        
        try:
            # Get metadata
            meta = self._redis.hgetall(meta_key)
            if not meta:
                return None
            
            # Get stream info
            try:
                stream_info = self._redis.xinfo_stream(stream_key)
                stream_length = stream_info.get("length", 0)
                last_entry = stream_info.get("last-generated-id", None)
            except RedisError:
                stream_length = 0
                last_entry = None
            
            return {
                "session_id": session_id,
                "status": meta.get("status", "unknown"),
                "started_at": meta.get("started_at"),
                "completed_at": meta.get("completed_at"),
                "failed_at": meta.get("failed_at"),
                "error": meta.get("error"),
                "event_count": stream_length,
                "last_event_id": last_entry,
                "is_active": meta.get("status") == "running"
            }
        except RedisError as e:
            logger.error(f"Failed to get status for session {session_id}: {e}")
            return None
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is currently active (running)."""
        try:
            return self._redis.sismember("sessions:active", session_id)
        except RedisError:
            return False
    
    def list_active_sessions(self) -> List[str]:
        """List all currently active session IDs."""
        try:
            members = self._redis.smembers("sessions:active")
            return list(members) if members else []
        except RedisError as e:
            logger.error(f"Failed to list active sessions: {e}")
            return []
