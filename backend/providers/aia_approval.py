"""
Provider for AI transparency user approval operations.
Encapsulates business logic for checking and approving users.
"""
from typing import Dict, Any
from utils.storage.mongo.mongo_helpers import get_mongo_storage
from shared.logger import logger

def check_user_approval_status(username: str) -> Dict[str, Any]:
    """
    Check if a user has approved the AI transparency notice.
    
    Args:
        username: Username of the current user
        
    Returns:
        Dictionary with approval status and username
        
    Raises:
        Exception: If the check operation fails
    """
    try:
        mongo_storage = get_mongo_storage()
        is_approved = mongo_storage.aia_user_approval.is_user_approved(username)
        return {
            "approved": is_approved,
            "username": username
        }
    except Exception as e:
        logger.error(f"Failed to check user approval for {username}: {str(e)}")
        raise

def approve_user_for_aia(username: str) -> Dict[str, Any]:
    """
    Approve a user for AI transparency notice (add to approved list).
    
    Args:
        username: Username of the current user
        
    Returns:
        Dictionary with user information indicating successful approval
        
    Raises:
        Exception: If the approval operation fails
    """
    try:
        mongo_storage = get_mongo_storage()
        result = mongo_storage.aia_user_approval.approve_user(username)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Failed to approve user {username}: {error_msg}")
            raise RuntimeError(f"Failed to approve user: {error_msg}")
        
        return {
            "username": username,
            "approved": True
        }
    except Exception as e:
        logger.error(f"Failed to approve user {username}: {str(e)}")
        raise

