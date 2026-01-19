"""TermsApproval repository port (interface)."""
from abc import ABC, abstractmethod
from typing import Optional

from domain.user.terms_approval.model import TermsApproval


class TermsApprovalRepository(ABC):
    """Port for TermsApproval persistence."""

    @abstractmethod
    def is_user_approved(self, username: str) -> bool:
        """
        Return whether the specified user has approved the AI transparency notice.
        
        Parameters:
            username (str): The user's unique username.
        
        Returns:
            bool: True if the user has approved the AI transparency notice, False otherwise.
        """
        ...

    @abstractmethod
    def record_approval(self, username: str) -> TermsApproval:
        """
        Record that the given user approved the AI transparency notice.
        
        Parameters:
        	username (str): Username of the user who approved the terms.
        
        Returns:
        	TermsApproval: The created or updated TermsApproval instance for the user.
        """
        ...

    @abstractmethod
    def find_by_username(self, username: str) -> Optional[TermsApproval]:
        """
        Retrieve the TermsApproval record for a given username.
        
        Parameters:
            username (str): Username identifying the user whose approval record to retrieve.
        
        Returns:
            Optional[TermsApproval]: The user's TermsApproval instance if found, otherwise None.
        """
        ...