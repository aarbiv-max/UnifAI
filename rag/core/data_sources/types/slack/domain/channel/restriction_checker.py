"""Channel Restriction Checker - AIA-Issue-011 compliance.

This module checks if Slack channels should be restricted from being
saved/ingested into UnifAI based on AIA compliance requirements.

Restriction rules (prefixes, suffixes, keywords) are fetched from
the platform-backend via HTTP.  The backend owns the defaults —
RAG has no hardcoded fallback values.

Restricted channel categories:
- ERG (Employee Resource Group) channels
- Events channels
- HR-sensitive channels
- Channels with external members
- Private/DM channels
"""
from typing import Any, Callable, Dict, List, Optional

from shared.logger import logger

_EMPTY_RULES: Dict[str, List[str]] = {
    "restricted_prefixes": [],
    "restricted_suffixes": [],
    "restricted_keywords": [],
}


class ChannelRestrictionChecker:
    """Checks if Slack channels are restricted per AIA-Issue-011.

    Rules are fetched from the platform-backend via the supplied
    ``rules_reader`` callable.  Call ``refresh()`` before a batch
    operation (e.g. channel fetch) so the checker picks up any
    admin changes since last refresh.
    """

    def __init__(self, rules_reader: Callable[[], Optional[Dict[str, Any]]]):
        """
        Args:
            rules_reader: A callable that returns the rules dict
                          (keys: restricted_prefixes, restricted_suffixes,
                          restricted_keywords) or None if the backend
                          is unreachable.
        """
        self._rules_reader = rules_reader
        self._rules: Dict[str, List[str]] = dict(_EMPTY_RULES)
        self.refresh()

    def refresh(self) -> None:
        """Reload rules from the platform-backend."""
        try:
            result = self._rules_reader()
            if result:
                self._rules = {
                    "restricted_prefixes": result.get("restricted_prefixes", []),
                    "restricted_suffixes": result.get("restricted_suffixes", []),
                    "restricted_keywords": result.get("restricted_keywords", []),
                }
                logger.info("Channel restriction rules loaded from platform-backend")
            else:
                logger.warning(
                    "Platform-backend returned no restriction rules; "
                    "no channels will be restricted by name rules"
                )
                self._rules = dict(_EMPTY_RULES)
        except Exception:
            logger.exception("Failed to load restriction rules; keeping previous rules")

    # ────────────────────────── public API ────────────────────────────────

    def is_restricted(
        self,
        channel_name: str,
        is_private: bool = False,
        is_ext_shared: bool = False,
    ) -> bool:
        """
        Check if a channel is restricted from being saved/ingested.

        Returns:
            True if channel is RESTRICTED (should NOT be saved)
            False if channel is ALLOWED (can be saved)
        """
        reason = self.get_restriction_reason(channel_name, is_private, is_ext_shared)
        if reason:
            logger.info(f"Channel '{channel_name}' is restricted: {reason}")
            return True
        return False

    def get_restriction_reason(
        self,
        channel_name: str,
        is_private: bool = False,
        is_ext_shared: bool = False,
    ) -> Optional[str]:
        """
        Get the reason why a channel is restricted, if any.

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
        for prefix in self._rules["restricted_prefixes"]:
            if name.startswith(prefix):
                return f"Channel name starts with restricted prefix '{prefix}'"

        # Rule 4: Block by suffix
        for suffix in self._rules["restricted_suffixes"]:
            if name.endswith(suffix):
                return f"Channel name ends with restricted suffix '{suffix}'"

        # Rule 5: Block by keyword
        for keyword in self._rules["restricted_keywords"]:
            if keyword in name:
                return f"Channel name contains restricted keyword '{keyword}'"

        return None
