"""
MongoDB-backed stop signal repository for cross-worker signaling.

Follows the same pattern as MongoSessionRepository.
"""
import pymongo
from pymongo.collection import Collection
from datetime import datetime
from typing import List
from .stop_signal_repository import StopSignalRepository


class MongoStopSignalRepository(StopSignalRepository):
    """
    MongoDB implementation of StopSignalRepository.
    
    Stores stop signals in a MongoDB collection with TTL for automatic cleanup.
    Enables cross-worker communication for stopping running sessions.
    """

    def __init__(
        self,
        mongodb_port: str = "27017",
        mongodb_ip: str = "localhost",
        db_name: str = "UnifAI",
        collection_name: str = "stop_signals",
    ):
        """
        Initialize MongoDB connection.
        
        Follows the same pattern as MongoSessionRepository.
        
        Args:
            mongodb_port: MongoDB port
            mongodb_ip: MongoDB IP address
            db_name: Database name
            collection_name: Collection name for stop signals
        """
        # Connect - same pattern as MongoSessionRepository
        mongo_uri = f"mongodb://{mongodb_ip}:{mongodb_port}/"
        client = pymongo.MongoClient(mongo_uri)
        db = client[db_name]
        self._col: Collection = db[collection_name]
        
        # Create indexes
        self._col.create_index("session_id", unique=True)
        # TTL index for automatic cleanup (5 minutes = 300 seconds)
        # Orphaned signals will be auto-deleted if execution crashes
        self._col.create_index("created_at", expireAfterSeconds=300)

    def set_signal(self, session_id: str) -> None:
        """
        Set a stop signal for the given session.
        
        Uses upsert to handle duplicate signals gracefully.
        """
        self._col.replace_one(
            {"session_id": session_id},
            {
                "session_id": session_id,
                "created_at": datetime.utcnow()
            },
            upsert=True
        )

    def check_signal(self, session_id: str) -> bool:
        """
        Fast existence check for stop signal.
        
        Uses count_documents with limit=1 for performance.
        """
        return self._col.count_documents({"session_id": session_id}, limit=1) == 1

    def clear_signal(self, session_id: str) -> bool:
        """
        Clear the stop signal for a session.
        
        Returns True if a signal was actually deleted.
        """
        result = self._col.delete_one({"session_id": session_id})
        return result.deleted_count > 0

    def clear_all_for_user(self, user_id: str) -> int:
        """
        Clear all stop signals for a user.
        
        Note: Current implementation stores only session_id, not user_id.
        This method is provided for interface completeness but would require
        schema changes to fully implement.
        """
        # Would need user_id in the signal document to implement
        # For now, return 0 as this is not commonly needed
        return 0
