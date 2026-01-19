"""Slack channel repository port (interface)."""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.slack_channel.model import SlackChannel
from domain.pagination import PaginatedResult


class SlackChannelRepository(ABC):
    """Port for SlackChannel persistence."""

    @abstractmethod
    def find_by_channel_id(self, channel_id: str) -> Optional[SlackChannel]:
        """
        Retrieve the SlackChannel with the given channel ID.
        
        Returns:
            SlackChannel or None: `SlackChannel` if a channel with the specified `channel_id` exists, `None` otherwise.
        """
        ...

    @abstractmethod
    def find_paginated(
        self,
        project_id: str,
        types: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Retrieve channels for a project with pagination and optional filtering.
        
        Parameters:
            project_id: Project identifier to filter channels by.
            types: Optional comma-separated channel types (e.g., "private_channel,public_channel").
            cursor: Optional pagination cursor to continue a previous listing.
            limit: Maximum number of channels to return.
            search: Optional substring to filter channel names.
        
        Returns:
            PaginatedResult[Dict[str, Any]] containing channel documents as dictionaries.
        """
        ...

    @abstractmethod
    def exists_for_project(self, project_id: str) -> bool:
        """
        Determine whether any Slack channels are associated with the given project.
        
        Returns:
            `true` if at least one channel exists for the project, `false` otherwise.
        """
        ...

    @abstractmethod
    def save(self, channel: SlackChannel) -> bool:
        """
        Persist a SlackChannel instance to storage.
        
        Parameters:
            channel (SlackChannel): The SlackChannel to persist.
        
        Returns:
            bool: `true` if the channel was saved successfully, `false` otherwise.
        """
        ...

    @abstractmethod
    def save_many(self, channels: List[SlackChannel]) -> None:
        """
        Persist multiple SlackChannel instances in a single batch operation.
        
        Parameters:
            channels (List[SlackChannel]): The SlackChannel objects to persist. The implementation may perform the saves transactionally or in bulk; callers should not assume individual rollback semantics.
        """
        ...

    @abstractmethod
    def update_membership(self, channel_id: str, is_member: bool, timestamp: float) -> bool:
        """
        Set the membership status for a Slack channel at a specific timestamp.
        
        Parameters:
            channel_id (str): Identifier of the Slack channel to update.
            is_member (bool): Whether the channel should be marked as a member.
            timestamp (float): POSIX timestamp (seconds since epoch) when the membership change occurred.
        
        Returns:
            True if the membership flag was updated, False otherwise.
        """
        ...

    @abstractmethod
    def delete_by_project(self, project_id: str) -> int:
        """
        Delete all SlackChannel records associated with the given project.
        
        Returns:
            int: The number of channels deleted.
        """
        ...