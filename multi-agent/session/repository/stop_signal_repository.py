"""
Abstract repository for stop signal management across workers.

Provides cross-worker communication for stopping running sessions.
Uses MongoDB as a shared signaling mechanism.
"""
from abc import ABC, abstractmethod


class StopSignalRepository(ABC):
    """
    Abstract repository for stop signal management.
    
    Enables cross-worker communication by storing stop signals in a shared
    data store (e.g., MongoDB). When a user requests to stop a session,
    a signal is written. The worker executing the session checks for this
    signal and gracefully stops execution.
    """

    @abstractmethod
    def set_signal(self, session_id: str) -> None:
        """
        Set a stop signal for the given session.
        
        Args:
            session_id: The session to stop
        """
        ...

    @abstractmethod
    def check_signal(self, session_id: str) -> bool:
        """
        Check if a stop signal exists for the session.
        
        Args:
            session_id: The session to check
            
        Returns:
            True if a stop signal exists, False otherwise
        """
        ...

    @abstractmethod
    def clear_signal(self, session_id: str) -> bool:
        """
        Clear the stop signal for a session.
        
        Should be called after the session has been stopped to prevent
        the signal from affecting future executions.
        
        Args:
            session_id: The session whose signal to clear
            
        Returns:
            True if a signal was cleared, False if none existed
        """
        ...

    @abstractmethod
    def clear_all_for_user(self, user_id: str) -> int:
        """
        Clear all stop signals for a user.
        
        Useful for cleanup operations.
        
        Args:
            user_id: The user whose signals to clear
            
        Returns:
            Number of signals cleared
        """
        ...
