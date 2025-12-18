"""
MongoDB-based cache for statistics overview data.
Provides shared cache across all Gunicorn workers.
"""
import pymongo
from pymongo.collection import Collection
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import time
import uuid


class MongoStatisticsCache:
    """
    MongoDB-based cache for statistics overview results.
    Shared across all Gunicorn workers to prevent duplicate expensive queries.
    """

    def __init__(
        self,
        collection: Collection,
        default_ttl: int = 300
    ):
        """
        Initialize MongoDB cache.

        Args:
            collection: MongoDB collection to use for caching (reuses existing connection)
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self._col: Collection = collection
        
        # Create indexes for efficient cache lookups
        try:
            self._col.create_index([("cache_key", pymongo.ASCENDING)], unique=True)
            self._col.create_index("expires_at", expireAfterSeconds=0)
        except Exception:
            # Indexes might already exist or creation failed, continue without indexes
            pass
        
        self._default_ttl = default_ttl
        self._lock_timeout = 120  # Lock expires after 120 seconds (handles crashes, allows long computations)
        self._lock_grace_period = 10  # Grace period: don't acquire lock if expired < 10 seconds ago
        self._lock_wait_interval = 0.1  # Wait 100ms between retries
        self._lock_max_wait = 30  # Maximum 30 seconds to wait for lock

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value by key.
        Ignores "computing" markers and only returns actual cached data.

        Args:
            cache_key: Cache key (e.g., "overview:all")

        Returns:
            Cached data dict or None if not found/expired/computing
        """
        try:
            doc = self._col.find_one({"cache_key": cache_key})
            if not doc:
                return None
            
            # Skip "computing" markers
            if doc.get("_computing"):
                return None
            
            # Check if expired
            expires_at = doc.get("expires_at")
            if expires_at and datetime.now(timezone.utc) > expires_at:
                # Expired, delete and return None
                self._col.delete_one({"cache_key": cache_key})
                return None
            
            # Return cached data
            return doc.get("data")
        except Exception:
            # If cache fails, return None (graceful degradation)
            return None
    
    def acquire_compute_lock(self, cache_key: str) -> bool:
        """
        Atomically acquire a lock for computing cache value.
        Only one request can acquire the lock at a time.
        Respects grace period to prevent acquiring recently expired locks.

        Args:
            cache_key: Cache key to lock

        Returns:
            True if lock acquired, False if another request is already computing
        """
        try:
            now = datetime.now(timezone.utc)
            grace_period_start = now - timedelta(seconds=self._lock_grace_period)
            lock_expires_at = now + timedelta(seconds=self._lock_timeout)
            lock_id = str(uuid.uuid4())
            
            # Check if there's an active lock first
            existing = self._col.find_one({
                "cache_key": cache_key,
                "_computing": True,
                "_lock_expires_at": {"$gt": now}
            })
            
            if existing:
                # Lock is already held by another request
                return False
            
            # Check for recently expired locks (grace period)
            # If lock expired less than grace_period ago, don't acquire it
            # (The original request might still be computing)
            recently_expired = self._col.find_one({
                "cache_key": cache_key,
                "_computing": True,
                "_lock_expires_at": {
                    "$gte": grace_period_start,
                    "$lt": now
                }
            })
            
            if recently_expired:
                # Lock expired recently - might still be computing, don't acquire
                return False
            
            # Try to acquire lock atomically
            # Only succeeds if no active lock exists and lock expired before grace period
            result = self._col.find_one_and_update(
                {
                    "$or": [
                        {"cache_key": cache_key, "_computing": {"$exists": False}},
                        {"cache_key": cache_key, "_lock_expires_at": {"$lt": grace_period_start}}
                    ]
                },
                {
                    "$set": {
                        "cache_key": cache_key,
                        "_computing": True,
                        "_lock_acquired_at": now,
                        "_lock_expires_at": lock_expires_at,
                        "_lock_id": lock_id,
                        "_lock_last_heartbeat": now
                    }
                },
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER
            )
            
            # Verify we actually got the lock (check lock_id matches)
            if result and result.get("_lock_id") == lock_id:
                return True
            
            return False
        except Exception:
            # If lock acquisition fails, assume another request has it
            return False
    
    def extend_lock_heartbeat(self, cache_key: str) -> bool:
        """
        Extend the lock expiration time (heartbeat mechanism).
        Call this periodically during long computations to prevent lock expiration.

        Args:
            cache_key: Cache key to extend lock for

        Returns:
            True if lock was extended, False if lock doesn't exist or expired
        """
        try:
            now = datetime.now(timezone.utc)
            new_expires_at = now + timedelta(seconds=self._lock_timeout)
            
            # Only extend if lock exists and hasn't expired
            result = self._col.update_one(
                {
                    "cache_key": cache_key,
                    "_computing": True,
                    "_lock_expires_at": {"$gt": now}
                },
                {
                    "$set": {
                        "_lock_expires_at": new_expires_at,
                        "_lock_last_heartbeat": now
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception:
            return False
    
    def release_compute_lock(self, cache_key: str) -> None:
        """
        Release the compute lock for a cache key.

        Args:
            cache_key: Cache key to unlock
        """
        try:
            self._col.update_one(
                {"cache_key": cache_key},
                {"$unset": {"_computing": "", "_lock_acquired_at": "", "_lock_expires_at": "", "_lock_id": ""}}
            )
        except Exception:
            # If lock release fails, it will expire automatically
            pass
    
    def wait_for_cache(self, cache_key: str, max_wait: float = None) -> Optional[Dict[str, Any]]:
        """
        Wait for another request to finish computing and return cached result.
        
        Args:
            cache_key: Cache key to wait for
            max_wait: Maximum time to wait in seconds (defaults to self._lock_max_wait)
        
        Returns:
            Cached data if available, None if timeout or still computing
        """
        if max_wait is None:
            max_wait = self._lock_max_wait
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if result is now cached
            cached_data = self.get(cache_key)
            if cached_data:
                return cached_data
            
            # Check if lock expired (computing request may have crashed)
            # Only try to acquire if lock expired before grace period
            try:
                now = datetime.now(timezone.utc)
                grace_period_start = now - timedelta(seconds=self._lock_grace_period)
                doc = self._col.find_one({"cache_key": cache_key})
                if doc and doc.get("_computing"):
                    lock_expires = doc.get("_lock_expires_at")
                    if lock_expires:
                        # Only try to acquire if lock expired before grace period
                        # (If expired recently, original request might still be computing)
                        if lock_expires < grace_period_start:
                            if self.acquire_compute_lock(cache_key):
                                return None  # We got the lock, caller should compute
            except Exception:
                pass
            
            # Wait before retrying
            time.sleep(self._lock_wait_interval)
        
        # Timeout reached
        return None

    def set(self, cache_key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Set cached value with TTL.

        Args:
            cache_key: Cache key (e.g., "overview:all")
            data: Data to cache (must be JSON-serializable)
            ttl: Time to live in seconds (uses default if None)
        """
        try:
            ttl_seconds = ttl if ttl is not None else self._default_ttl
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            
            doc = {
                "cache_key": cache_key,
                "data": data,
                "expires_at": expires_at,
                "cached_at": datetime.now(timezone.utc)
            }
            
            # Upsert: insert or update if exists
            self._col.replace_one(
                {"cache_key": cache_key},
                doc,
                upsert=True
            )
        except Exception:
            # If cache write fails, silently continue (graceful degradation)
            pass


