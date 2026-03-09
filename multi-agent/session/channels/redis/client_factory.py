"""
Redis client factory for session streaming.

Handles Redis connection creation with graceful fallback to NullRedis
when Redis is unavailable.
"""
import logging
from typing import Union
from redis import Redis
from .null_client import NullRedis

logger = logging.getLogger(__name__)

RedisClient = Union[Redis, NullRedis]


class RedisClientFactory:
    """
    Factory for creating Redis client connections.
    
    Provides graceful degradation - returns NullRedis when
    connection fails, allowing the system to continue without
    streaming capabilities.
    """
    
    @staticmethod
    def create(
        host: str = "0.0.0.0",
        port: int = 6379,
        db: int = 0,
        password: str = "",
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5
    ) -> RedisClient:
        """
        Create a Redis client connection.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password (empty string for no auth)
            socket_connect_timeout: Connection timeout in seconds
            socket_timeout: Socket timeout in seconds
            
        Returns:
            Redis client if connection succeeds, NullRedis otherwise
        """
        try:
            client = Redis(
                host=host,
                port=port,
                db=db,
                password=password if password else None,
                decode_responses=True,
                socket_connect_timeout=socket_connect_timeout,
                socket_timeout=socket_timeout
            )
            # Test connection
            client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis at {host}:{port}: {e}. "
                          "Session streaming will use fallback mode.")
            return NullRedis()
    
    @staticmethod
    def create_from_config(cfg) -> RedisClient:
        """
        Create Redis client from AppConfig.
        
        Args:
            cfg: AppConfig instance with redis_* attributes
            
        Returns:
            Redis client if connection succeeds, NullRedis otherwise
        """
        return RedisClientFactory.create(
            host=cfg.redis_ip,
            port=int(cfg.redis_port),
            db=cfg.redis_db,
            password=cfg.redis_password
        )
    
    @staticmethod
    def is_available(client: RedisClient) -> bool:
        """
        Check if a Redis client is available and connected.
        
        Args:
            client: Redis or NullRedis instance
            
        Returns:
            True if client is a real Redis connection that responds to ping
        """
        if client is None:
            return False
        
        # Check for NullRedis
        if isinstance(client, NullRedis):
            return False
        
        if hasattr(client, 'is_connected'):
            return client.is_connected()
        
        # Real Redis client - try ping
        try:
            return client.ping()
        except Exception:
            return False
