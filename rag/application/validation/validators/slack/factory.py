"""Slack validator factory."""
from typing import List

from domain.validation.port import DataSourceValidator
from .channel_bot_installation_validator import ChannelBotInstallationValidator


class SlackValidators:
    """Constructs the Slack validators pipeline."""

    def __init__(self, channel_bot_validator: ChannelBotInstallationValidator) -> None:
        """
        Initialize the SlackValidators factory with a channel bot installation validator.
        
        Parameters:
            channel_bot_validator (ChannelBotInstallationValidator): Validator responsible for validating Slack channel bot installations; stored for use when creating the validators pipeline.
        """
        self._channel_bot_validator = channel_bot_validator

    def create_validators(self) -> List[DataSourceValidator]:
        """
        Create the Slack validators pipeline.
        
        Returns:
            validators (List[DataSourceValidator]): A list containing the channel bot installation validator used for Slack validation.
        """
        return [self._channel_bot_validator]