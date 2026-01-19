"""Infrastructure adapters for Slack bot installation checking.

These adapters implement the BotInstallationCheckerPort and MembershipUpdaterPort
using Slack API and MongoDB storage respectively.
"""
import time
from typing import Any

from shared.logger import logger


class BotInstallationCheckerAdapter:
    """
    Slack API-based bot installation checker.
    
    Checks if the bot is a member of a channel using the Slack conversations.info API.
    """

    def __init__(self, slack_connector: Any) -> None:
        """
        Initialize the adapter with a Slack API connector.
        
        Stores the provided connector on the instance for performing Slack API requests. If None, API checks will be skipped.
        
        Parameters:
            slack_connector (Any): Connector used to call the Slack API (or None to disable API calls).
        """
        self._connector = slack_connector

    def is_bot_installed_in_channel(self, channel_id: str) -> bool:
        """
        Determine whether the bot is a member of the Slack channel identified by channel_id.
        
        Returns False if channel_id is invalid, if no Slack connector is configured, or if the Slack API returns an error or the API call fails.
        
        Parameters:
            channel_id (str): Slack channel ID to check.
        
        Returns:
            bool: True if the bot is a member of the channel, False otherwise.
        """
        if not isinstance(channel_id, str) or not channel_id:
            return False

        if self._connector is not None:
            try:
                resp = self._connector._make_api_request("conversations.info", {"channel": channel_id})
                if resp.get("ok"):
                    channel = (resp.get("channel") or {})
                    is_member = bool(channel.get("is_member"))
                    return is_member
                else:
                    logger.warning(f"BotInstallationCheckerAdapter: Slack API error for {channel_id}: {resp.get('error')}")
            except Exception as e:
                logger.warning(f"BotInstallationCheckerAdapter: conversations.info failed for {channel_id}: {e}")
        else:
            logger.warning("BotInstallationCheckerAdapter: no configured connector; skipping API check")

        return False


class MembershipUpdaterAdapter:
    """
    MongoDB-based membership status updater.
    
    Updates the bot membership flag in the slack_channels collection.
    """

    def __init__(self, storage: Any) -> None:
        """
        Initialize the MembershipUpdaterAdapter with a storage backend for updating Slack channel membership.
        
        Parameters:
            storage (Any): Storage backend exposing `slack_channels.update_membership(channel_id: str, is_member: bool, timestamp: float) -> bool`.
                           The adapter stores this backend as an instance attribute and relies on that method to persist membership changes.
        """
        self._storage = storage

    def update_membership(self, channel_id: str, is_member: bool) -> bool:
        """
        Update the stored membership state for a Slack channel.
        
        Parameters:
            channel_id (str): Slack channel identifier to update.
            is_member (bool): Whether the bot is a member of the channel.
        
        Returns:
            bool: `True` if the storage update succeeded, `False` otherwise.
        """
        try:
            if hasattr(self._storage, "slack_channels") and hasattr(self._storage.slack_channels, "update_membership"):
                return bool(
                    self._storage.slack_channels.update_membership(
                        channel_id=channel_id,
                        is_member=is_member,
                        timestamp=time.time()
                    )
                )
            return False
        except Exception as e:
            logger.warning(f"MembershipUpdaterAdapter: failed to update membership for {channel_id}: {e}")
            return False