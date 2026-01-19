"""Channel Bot Installation Validator."""
from typing import Optional, Any, Tuple, Protocol

from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue
from shared.logger import logger


class BotInstallationCheckerPort(Protocol):
    """Port for bot installation checking - implementations injected at runtime."""
    def is_bot_installed_in_channel(self, channel_id: str) -> bool:
        """
        Check whether the app bot user is a member of the specified Slack channel.
        
        Parameters:
            channel_id (str): Slack channel identifier to check membership for.
        
        Returns:
            bool: `True` if the bot user is a member of the channel, `False` otherwise.
        """
        ...


class MembershipUpdaterPort(Protocol):
    """Port for updating membership status - implementations injected at runtime."""
    def update_membership(self, channel_id: str, is_member: bool) -> bool:
        """
        Update cached membership status for a Slack channel.
        
        Parameters:
            channel_id (str): Identifier of the Slack channel whose membership is being updated.
            is_member (bool): `True` if the bot is a member of the channel, `False` otherwise.
        
        Returns:
            bool: `True` if the membership cache/update succeeded, `False` otherwise.
        """
        ...


class ChannelBotInstallationValidator(DataSourceValidator):
    """Validates that the Slack app (bot user) is a member of the provided channel."""
    
    name = "ChannelBotInstallationValidator"
    error_message = "Invite the TAG-001 app user to this channel to enable embedding. Channel: {channel_name}"
    error_message_key = "Channel bot not installed"

    def __init__(
        self,
        bot_checker: BotInstallationCheckerPort,
        membership_updater: MembershipUpdaterPort,
    ) -> None:
        """
        Initialize the validator with the dependencies used to check and persist bot membership.
        
        Parameters:
            bot_checker (BotInstallationCheckerPort): Service used to determine whether the app bot is a member of a given channel.
            membership_updater (MembershipUpdaterPort): Service used to update/cache the bot's membership status for a channel.
        """
        self._bot_checker = bot_checker
        self._membership_updater = membership_updater

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Ensure the Slack app bot user is a member of the specified channel.
        
        Parameters:
            channel_id (str): Channel identifier used to check bot membership. If missing or not a string, validation is not enforced.
            channel_name (str, optional): Human-friendly channel name used in the validation issue message when available.
        
        Returns:
            tuple: `True, None` if the bot is a member, if `channel_id` is missing/invalid, or if an unexpected error occurs; `False` and a ValidationIssue when the bot is not a member.
        """
        channel_id = kwargs.get("channel_id")
        channel_name = kwargs.get("channel_name") or ""

        if not isinstance(channel_id, str) or not channel_id:
            # Without a channel_id we cannot validate; do not block
            return True, None

        try:
            # Always check with Slack API via the checker, regardless of cached is_app_member
            is_member = self._bot_checker.is_bot_installed_in_channel(channel_id)
            # cache result for follow-up update without re-calling the checker
            self._membership_updater.update_membership(channel_id, is_member)
            
            if not is_member:
                return False, self.build_issue(
                    self.error_message.format(channel_name=channel_name or channel_id)
                )

            return True, None
        except Exception as e:
            logger.error(f"ChannelBotInstallationValidator: unexpected error validating {channel_id}: {e}")
            return True, None