"""Channel Restriction Checker - AIA-Issue-011 compliance.

This module checks if Slack channels should be restricted from being
saved/ingested into UnifAI based on AIA compliance requirements.

Restricted channel categories:
- ERG (Employee Resource Group) channels
- Events channels
- HR-sensitive channels
- Channels with external members
- Private/DM channels
"""
from typing import List, Optional

from shared.logger import logger


class ChannelRestrictionChecker:
    """Checks if Slack channels are restricted per AIA-Issue-011."""

    RESTRICTED_PREFIXES: List[str] = [
        "erg-",
        "event-",
        "events-",
        "hr-",
        "people-",
        "confidential-",
    ]

    RESTRICTED_SUFFIXES: List[str] = [
        "-erg",
        "-event",
        "-events",
        "-hr",
        "-confidential",
    ]

    RESTRICTED_KEYWORDS: List[str] = [
        "human-resources",
        "employee-relations",
        "performance-review",
    ]

    @classmethod
    def is_restricted(
        cls,
        channel_name: str,
        is_private: bool = False,
        is_ext_shared: bool = False,
    ) -> bool:
        """
        Check if a channel is restricted from being saved/ingested.

        Args:
            channel_name: The name of the channel
            is_private: Whether it's a private channel
            is_ext_shared: Whether the channel has external members

        Returns:
            True if channel is RESTRICTED (should NOT be saved)
            False if channel is ALLOWED (can be saved)
        """
        reason = cls.get_restriction_reason(channel_name, is_private, is_ext_shared)
        if reason:
            logger.info(f"Channel '{channel_name}' is restricted: {reason}")
            return True
        return False

    @classmethod
    def get_restriction_reason(
        cls,
        channel_name: str,
        is_private: bool = False,
        is_ext_shared: bool = False,
    ) -> Optional[str]:
        """
        Get the reason why a channel is restricted, if any.

        Args:
            channel_name: The name of the channel
            is_private: Whether it's a private channel
            is_ext_shared: Whether the channel has external members

        Returns:
            Restriction reason string if restricted, None if allowed
        """
        name = channel_name.lower()

        # Rule 1: Block private channels (AIA Reviewer Note 1/27)
        if is_private:
            return "Private channels are not allowed"

        # Rule 2: Block channels with external members
        if is_ext_shared:
            return "Channels with external members are not allowed"

        # Rule 3: Block by prefix
        for prefix in cls.RESTRICTED_PREFIXES:
            if name.startswith(prefix):
                return f"Channel name starts with restricted prefix '{prefix}'"

        # Rule 4: Block by suffix
        for suffix in cls.RESTRICTED_SUFFIXES:
            if name.endswith(suffix):
                return f"Channel name ends with restricted suffix '{suffix}'"

        # Rule 5: Block by keyword
        for keyword in cls.RESTRICTED_KEYWORDS:
            if keyword in name:
                return f"Channel name contains restricted keyword '{keyword}'"

        return None
