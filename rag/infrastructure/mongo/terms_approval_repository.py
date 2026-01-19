"""MongoDB adapter for TermsApprovalRepository port."""
from typing import Optional
from datetime import datetime

from pymongo.collection import Collection

from domain.user.terms_approval.model import TermsApproval
from domain.user.terms_approval.repository import TermsApprovalRepository
from shared.logger import logger


class MongoTermsApprovalRepository(TermsApprovalRepository):
    """MongoDB implementation of the TermsApprovalRepository port."""

    def __init__(self, collection: Collection):
        """
        Initialize the repository with a MongoDB collection and ensure a unique index on the username field.
        
        Parameters:
            collection (Collection): MongoDB collection used to persist TermsApproval documents; a unique index on the "username" field is created if not already present.
        """
        self._col = collection
        self._col.create_index("username", unique=True)

    def is_user_approved(self, username: str) -> bool:
        """
        Determine whether a user has an approval record for the AI transparency notice.
        
        Parameters:
            username (str): Username to check.
        
        Returns:
            `true` if an approval document exists for the user, `false` otherwise (also `false` if an error occurs while accessing the repository).
        """
        try:
            doc = self._col.find_one({"username": username})
            return doc is not None
        except Exception as e:
            logger.error(f"Error checking user approval for {username}: {e}")
            return False

    def record_approval(self, username: str) -> TermsApproval:
        """
        Create or update the terms approval record for the given user using the current UTC time.
        
        Parameters:
            username (str): The user's username (unique identifier) whose approval is being recorded.
        
        Returns:
            TermsApproval: The approval record containing `username`, `approved_at` set to the current UTC time, and `created_at` set to the current UTC time.
        """
        now = datetime.utcnow()
        self._col.update_one(
            {"username": username},
            {
                "$set": {"approved_at": now},
                "$setOnInsert": {"username": username, "created_at": now}
            },
            upsert=True,
        )
        return TermsApproval(username=username, approved_at=now, created_at=now)

    def find_by_username(self, username: str) -> Optional[TermsApproval]:
        """
        Retrieve the terms approval record for the given username.
        
        Returns:
            TermsApproval if a record exists for the specified username, `None` otherwise (including when a lookup error occurs).
        """
        try:
            doc = self._col.find_one({"username": username}, {"_id": 0})
            return TermsApproval.from_dict(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting user approval for {username}: {e}")
            return None