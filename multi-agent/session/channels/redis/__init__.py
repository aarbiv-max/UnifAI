"""
Redis-based session streaming components.

This module provides Redis-backed streaming infrastructure for session events:
  - RedisSessionChannel: Channel for emitting session events to Redis Streams
  - RedisStreamReader: Utility for reading/subscribing to session streams
  - RedisClientFactory: Factory for creating Redis connections with fallback
  - NullRedis: Null object pattern for graceful degradation
"""
from .channel import RedisSessionChannel
from .stream_reader import RedisStreamReader
from .client_factory import RedisClientFactory, RedisClient
from .null_client import NullRedis, NullPipeline

__all__ = [
    "RedisSessionChannel",
    "RedisStreamReader", 
    "RedisClientFactory",
    "RedisClient",
    "NullRedis",
    "NullPipeline"
]
