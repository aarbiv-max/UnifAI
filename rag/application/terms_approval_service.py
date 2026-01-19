"""Terms approval application service."""
from typing import Dict, Any

from domain.user.terms_approval.repository import TermsApprovalRepository
from shared.logger import logger


class TermsApprovalService:
    """Application service for AI transparency terms approval operations."""

    def __init__(self, approval_repo: TermsApprovalRepository):
        """
        Initialize the service with a repository for terms approval operations.
        
        Parameters:
            approval_repo (TermsApprovalRepository): Repository used to check and record users' AI transparency terms approvals.
        """
        self._repo = approval_repo

    def check_approval_status(self, username: str) -> Dict[str, Any]:
        """
        Determine whether the specified user has approved the AI transparency notice.
        
        Returns:
            dict: A dictionary with keys:
                - "approved": `True` if the user has approved the notice, `False` otherwise.
                - "username": the provided `username`.
        """
        is_approved = self._repo.is_user_approved(username)
        return {
            "approved": is_approved,
            "username": username
        }

    def record_approval(self, username: str) -> Dict[str, Any]:
        """
        Record that the specified user has approved the AI transparency notice.
        
        Parameters:
            username (str): The identifier of the user who approved the notice.
        
        Returns:
            Dict[str, Any]: A dictionary containing `"username"` set to the recorded username and `"approved"` set to `True`.
        """
        approval = self._repo.record_approval(username)
        logger.info(f"Recorded terms approval for user: {username}")
        return {
            "username": approval.username,
            "approved": True
        }